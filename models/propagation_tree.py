# -*- coding: utf-8 -*-
"""
多关系传播树模块 - 基于Tree-LSTM处理树结构
支持多种关系类型：转发、评论、引用
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Optional, Dict
import numpy as np


class TreeLSTMCell(nn.Module):
    """
    Tree-LSTM单元 (Child-Sum Tree-LSTM)
    参考: Tai et al. "Improved Semantic Representations From Tree-Structured Long Short-Term Memory Networks"
    
    与标准LSTM的区别：
    - 使用子节点的隐藏状态之和来更新父节点
    - 考虑了树结构的递归性质
    """
    
    def __init__(self, input_dim: int, hidden_dim: int):
        super(TreeLSTMCell, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # 输入门 (Input Gate)
        self.i_u = nn.Linear(input_dim, hidden_dim)
        # 遗忘门 (Forget Gate) - 对应子节点
        self.f_u = nn.Linear(hidden_dim, hidden_dim)
        # 输出门 (Output Gate)
        self.o_u = nn.Linear(input_dim, hidden_dim)
        # 候选细胞状态 (Candidate Cell State)
        self.u_u = nn.Linear(input_dim, hidden_dim)
        
        # 初始化权重
        self.reset_parameters()
    
    def reset_parameters(self):
        """初始化参数"""
        for name, param in self.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.1)
    
    def forward(self, 
                input_vec: torch.Tensor, 
                child_h: torch.Tensor, 
                child_c: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            input_vec: 当前节点的输入向量 (batch_size, input_dim)
            child_h: 子节点的隐藏状态 (batch_size, num_children, hidden_dim)
            child_c: 子节点的细胞状态 (batch_size, num_children, hidden_dim)
            
        Returns:
            h: 新的隐藏状态 (batch_size, hidden_dim)
            c: 新的细胞状态 (batch_size, hidden_dim)
        """
        batch_size = input_vec.size(0)
        
        # 如果没有子节点，使用零向量
        if child_h.size(1) == 0:
            child_h_sum = torch.zeros(batch_size, self.hidden_dim, device=input_vec.device)
            child_c_sum = torch.zeros(batch_size, self.hidden_dim, device=input_vec.device)
        else:
            # 子节点隐藏状态之和 (Child-Sum)
            child_h_sum = torch.sum(child_h, dim=1)  # (batch_size, hidden_dim)
            child_c_sum = torch.sum(child_c, dim=1)  # (batch_size, hidden_dim)
        
        # 计算门控
        i = torch.sigmoid(self.i_u(input_vec) + self.f_u(child_h_sum))
        o = torch.sigmoid(self.o_u(input_vec))
        u = torch.tanh(self.u_u(input_vec))
        
        # 细胞状态
        c = i * u + child_c_sum  # (batch_size, hidden_dim)
        
        # 隐藏状态
        h = o * torch.tanh(c)
        
        return h, c


class RelationAwareTreeLSTMCell(nn.Module):
    """
    关系感知的Tree-LSTM单元
    支持多种关系类型：转发、评论、引用
    """
    
    def __init__(self, input_dim: int, hidden_dim: int, num_relations: int = 3):
        super(RelationAwareTreeLSTMCell, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_relations = num_relations
        
        # 关系嵌入
        self.relation_embedding = nn.Embedding(num_relations, hidden_dim)
        
        # 输入门 (Input Gate)
        self.i_u = nn.Linear(input_dim + hidden_dim, hidden_dim)
        # 遗忘门 (Forget Gate) - 每个关系类型一个
        self.f_u = nn.ModuleList([
            nn.Linear(hidden_dim, hidden_dim) for _ in range(num_relations)
        ])
        # 输出门 (Output Gate)
        self.o_u = nn.Linear(input_dim + hidden_dim, hidden_dim)
        # 候选细胞状态 (Candidate Cell State)
        self.u_u = nn.Linear(input_dim + hidden_dim, hidden_dim)
        
        # 关系注意力
        self.relation_attention = nn.Linear(hidden_dim, 1)
        
        self.reset_parameters()
    
    def reset_parameters(self):
        for name, param in self.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.1)
    
    def forward(self,
                input_vec: torch.Tensor,
                child_h: torch.Tensor,
                child_c: torch.Tensor,
                relation_ids: Optional[torch.Tensor] = None,
                virtual_mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播

        Args:
            input_vec: 当前节点的输入向量 (batch_size, input_dim)
            child_h: 子节点的隐藏状态 (batch_size, num_children, hidden_dim)
            child_c: 子节点的细胞状态 (batch_size, num_children, hidden_dim)
            relation_ids: 关系类型ID (batch_size, num_children)
            virtual_mask: 虚拟节点掩码 (batch_size, num_children)，True=虚拟节点，权重衰减0.7

        Returns:
            h: 新的隐藏状态 (batch_size, hidden_dim)
            c: 新的细胞状态 (batch_size, hidden_dim)
        """
        VIRTUAL_DECAY = 0.7  # 虚拟节点权重衰减系数

        batch_size = input_vec.size(0)
        num_children = child_h.size(1)

        if num_children == 0:
            # 无子节点时，使用零向量
            child_h_sum = torch.zeros(batch_size, self.hidden_dim, device=input_vec.device)
            child_c_sum = torch.zeros(batch_size, self.hidden_dim, device=input_vec.device)
        else:
            # 如果没有提供关系ID，使用默认关系（转发）
            if relation_ids is None:
                relation_ids = torch.zeros(num_children, dtype=torch.long, device=input_vec.device)
                relation_ids = relation_ids.unsqueeze(0).expand(batch_size, -1)

            # 虚拟节点权重衰减：virtual_mask 中 True 的位置乘以 VIRTUAL_DECAY
            if virtual_mask is not None:
                # virtual_mask: (batch_size, num_children) bool
                decay = torch.where(
                    virtual_mask,
                    torch.full_like(child_h[:, :, 0], VIRTUAL_DECAY),
                    torch.ones_like(child_h[:, :, 0])
                )  # (batch_size, num_children)
                child_h = child_h * decay.unsqueeze(-1)
                child_c = child_c * decay.unsqueeze(-1)

            # 获取关系嵌入
            relation_emb = self.relation_embedding(relation_ids)  # (batch_size, num_children, hidden_dim)

            # 关系感知的注意力加权
            attention_scores = self.relation_attention(relation_emb + child_h)  # (batch_size, num_children, 1)
            attention_weights = F.softmax(attention_scores, dim=1)  # (batch_size, num_children, 1)

            # 加权求和
            child_h_weighted = child_h * attention_weights  # (batch_size, num_children, hidden_dim)
            child_h_sum = torch.sum(child_h_weighted, dim=1)  # (batch_size, hidden_dim)

            # 遗忘门：对不同关系类型使用不同的遗忘门
            child_c_list = []
            for i in range(num_children):
                # 获取当前子节点的关系类型
                rel_id = relation_ids[:, i]  # (batch_size,)

                # 计算遗忘门
                f = torch.zeros(batch_size, self.hidden_dim, device=input_vec.device)
                for r in range(self.num_relations):
                    mask = (rel_id == r)
                    if mask.any():
                        f[mask] = self.f_u[r](child_h[:, i, :])[mask]

                child_c_i = f * child_c[:, i, :]  # (batch_size, hidden_dim)
                child_c_list.append(child_c_i)

            child_c_sum = torch.stack(child_c_list, dim=1).sum(dim=1)  # (batch_size, hidden_dim)
        
        # 拼接输入和子节点信息
        combined = torch.cat([input_vec, child_h_sum], dim=-1)  # (batch_size, input_dim + hidden_dim)
        
        # 计算门控
        i = torch.sigmoid(self.i_u(combined))
        o = torch.sigmoid(self.o_u(combined))
        u = torch.tanh(self.u_u(combined))
        
        # 细胞状态
        c = i * u + child_c_sum
        
        # 隐藏状态
        h = o * torch.tanh(c)
        
        return h, c


class PropagationTreeEncoder(nn.Module):
    """
    传播树编码器
    使用Tree-LSTM编码整个传播树结构
    """
    
    def __init__(self, 
                 input_dim: int, 
                 hidden_dim: int, 
                 num_relations: int = 3,
                 use_relation_aware: bool = True,
                 pooling: str = 'root'):
        """
        Args:
            input_dim: 输入特征维度
            hidden_dim: 隐藏层维度
            num_relations: 关系类型数量
            use_relation_aware: 是否使用关系感知Tree-LSTM
            pooling: 池化方式 ('root', 'max', 'mean', 'attention')
        """
        super(PropagationTreeEncoder, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_relations = num_relations
        self.pooling = pooling
        
        # 选择Tree-LSTM类型
        if use_relation_aware:
            self.tree_lstm = RelationAwareTreeLSTMCell(input_dim, hidden_dim, num_relations)
        else:
            self.tree_lstm = TreeLSTMCell(input_dim, hidden_dim)
        
        # 节点编码层
        self.node_encoder = nn.Linear(input_dim, hidden_dim)
        
        # 池化层
        if pooling == 'attention':
            self.attention = nn.Linear(hidden_dim, 1)
        
        self.reset_parameters()
    
    def reset_parameters(self):
        for name, param in self.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0.1)
    
    def forward(self,
                tree_structure: Dict,
                node_features: torch.Tensor) -> torch.Tensor:
        """
        前向传播

        Args:
            tree_structure: 树结构信息 {
                'adjacency': List[List[int]],       # 邻接表
                'relation_types': List[List[int]],  # 关系类型
                'root': int,                        # 根节点索引
                'virtual_flags': List[bool]         # 可选，虚拟节点标记
            }
            node_features: 节点特征 (batch_size, num_nodes, input_dim)

        Returns:
            output: 编码后的传播特征 (batch_size, hidden_dim)
        """
        batch_size = node_features.size(0)
        num_nodes = node_features.size(1)

        # 编码节点特征
        h = self.node_encoder(node_features)  # (batch_size, num_nodes, hidden_dim)
        c = torch.zeros(batch_size, num_nodes, self.hidden_dim, device=node_features.device)

        # 获取拓扑序（从叶子到根）
        adjacency = tree_structure['adjacency']  # List of lists
        relation_types = tree_structure.get('relation_types', None)
        root = tree_structure.get('root', 0)
        virtual_flags = tree_structure.get('virtual_flags', None)  # List[bool]

        # 构建节点顺序（后序遍历：先处理子节点，再处理父节点）
        node_order = self._post_order(adjacency)

        # 逐步更新每个节点
        for node_idx in node_order:
            # 获取子节点
            children = adjacency[node_idx] if node_idx < len(adjacency) else []

            if len(children) > 0:
                # 收集子节点的隐藏状态和细胞状态
                child_h = h[:, children, :]  # (batch_size, num_children, hidden_dim)
                child_c = c[:, children, :]  # (batch_size, num_children, hidden_dim)

                # 获取关系类型
                if relation_types is not None and node_idx < len(relation_types):
                    rel_ids = torch.tensor(relation_types[node_idx],
                                          dtype=torch.long,
                                          device=node_features.device)
                    rel_ids = rel_ids.unsqueeze(0).expand(batch_size, -1)
                else:
                    rel_ids = None

                # 构建虚拟节点掩码 (batch_size, num_children)
                v_mask = None
                if virtual_flags is not None:
                    child_virtual = [virtual_flags[c_idx] if c_idx < len(virtual_flags) else False
                                     for c_idx in children]
                    v_mask = torch.tensor(child_virtual, dtype=torch.bool,
                                         device=node_features.device)
                    v_mask = v_mask.unsqueeze(0).expand(batch_size, -1)

                # 更新当前节点
                if isinstance(self.tree_lstm, RelationAwareTreeLSTMCell):
                    h[:, node_idx, :], c[:, node_idx, :] = self.tree_lstm(
                        h[:, node_idx, :], child_h, child_c, rel_ids, v_mask
                    )
                else:
                    h[:, node_idx, :], c[:, node_idx, :] = self.tree_lstm(
                        h[:, node_idx, :], child_h, child_c
                    )
        
        # 池化获取最终表示
        if self.pooling == 'root':
            # 使用根节点的特征
            output = h[:, root, :]  # (batch_size, hidden_dim)
        elif self.pooling == 'max':
            # 最大池化
            output = torch.max(h, dim=1)[0]  # (batch_size, hidden_dim)
        elif self.pooling == 'mean':
            # 平均池化
            output = torch.mean(h, dim=1)  # (batch_size, hidden_dim)
        elif self.pooling == 'attention':
            # 注意力池化
            attn_scores = self.attention(h).squeeze(-1)  # (batch_size, num_nodes)
            attn_weights = F.softmax(attn_scores, dim=1)  # (batch_size, num_nodes)
            output = torch.bmm(attn_weights.unsqueeze(1), h).squeeze(1)  # (batch_size, hidden_dim)
        else:
            output = h[:, root, :]
        
        return output
    
    def _post_order(self, adjacency: List[List[int]]) -> List[int]:
        """后序遍历获取节点处理顺序"""
        visited = set()
        order = []
        
        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            children = adjacency[node] if node < len(adjacency) else []
            for child in children:
                dfs(child)
            order.append(node)
        
        # 从根节点开始
        dfs(0)
        return order


class MultiRelationPropagationTree(nn.Module):
    """
    多关系传播树模型
    整合多种关系类型的传播结构特征
    """
    
    # 关系类型枚举
    RELATION_FORWARD = 0    # 转发
    RELATION_COMMENT = 1   # 评论
    RELATION_QUOTE = 2     # 引用
    
    def __init__(self, 
                 embedding_dim: int,
                 hidden_dim: int,
                 num_relations: int = 3,
                 use_relation_aware: bool = True,
                 pooling: str = 'attention'):
        super(MultiRelationPropagationTree, self).__init__()
        
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_relations = num_relations
        
        # 传播树编码器
        self.tree_encoder = PropagationTreeEncoder(
            input_dim=embedding_dim,
            hidden_dim=hidden_dim,
            num_relations=num_relations,
            use_relation_aware=use_relation_aware,
            pooling=pooling
        )
        
        # 关系类型统计层
        self.relation_stats_fc = nn.Linear(num_relations * 3, hidden_dim)
        
        # 输出层
        self.output_fc = nn.Linear(hidden_dim * 2, hidden_dim)
    
    def forward(self, 
                node_embeddings: torch.Tensor,
                tree_structure: Dict,
                relation_counts: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        前向传播
        
        Args:
            node_embeddings: 节点嵌入 (batch_size, num_nodes, embedding_dim)
            tree_structure: 树结构信息
            relation_counts: 关系类型统计 (batch_size, num_relations * 3)
            
        Returns:
            output: 传播特征向量 (batch_size, hidden_dim)
        """
        # Tree-LSTM编码
        tree_features = self.tree_encoder(tree_structure, node_embeddings)  # (batch_size, hidden_dim)
        
        # 关系统计特征
        if relation_counts is not None:
            relation_features = F.relu(self.relation_stats_fc(relation_counts))  # (batch_size, hidden_dim)
            output = torch.cat([tree_features, relation_features], dim=-1)  # (batch_size, hidden_dim * 2)
            output = self.output_fc(output)  # (batch_size, hidden_dim)
        else:
            output = tree_features
        
        return output


class SimplePropagationEncoder(nn.Module):
    """
    简化的传播树编码器（用于快速测试）
    不使用Tree-LSTM，使用图神经网络的方式
    """
    
    def __init__(self, 
                 input_dim: int, 
                 hidden_dim: int,
                 num_layers: int = 2,
                 pooling: str = 'root'):
        super(SimplePropagationEncoder, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.pooling = pooling
        
        # 节点编码
        self.node_encoder = nn.Linear(input_dim, hidden_dim)
        
        # 图卷积层
        self.gc_layers = nn.ModuleList([
            nn.Linear(hidden_dim, hidden_dim) for _ in range(num_layers)
        ])
        
        # 池化
        if pooling == 'attention':
            self.attention = nn.Linear(hidden_dim, 1)
        
        self.dropout = nn.Dropout(0.3)
    
    def forward(self, 
                adjacency_matrix: torch.Tensor,
                node_features: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            adjacency_matrix: 邻接矩阵 (batch_size, num_nodes, num_nodes)
            node_features: 节点特征 (batch_size, num_nodes, input_dim)
            
        Returns:
            output: 编码后的传播特征 (batch_size, hidden_dim)
        """
        batch_size = node_features.size(0)
        num_nodes = node_features.size(1)
        
        # 编码节点
        h = self.node_encoder(node_features)  # (batch_size, num_nodes, hidden_dim)
        
        # 计算度矩阵
        degree = torch.sum(adjacency_matrix, dim=-1) + 1  # (batch_size, num_nodes)
        degree_inv_sqrt = torch.pow(degree, -0.5)  # (batch_size, num_nodes)
        degree_inv_sqrt = degree_inv_sqrt.unsqueeze(-1)  # (batch_size, num_nodes, 1)
        
        # 归一化邻接矩阵
        adj_norm = adjacency_matrix * degree_inv_sqrt * degree_inv_sqrt.transpose(1, 2)
        
        # 图卷积
        for gc_layer in self.gc_layers:
            h_new = torch.bmm(adj_norm, h)  # (batch_size, num_nodes, hidden_dim)
            h_new = gc_layer(h_new)
            h_new = F.relu(h_new)
            h_new = self.dropout(h_new)
            h = h_new + h  # 残差连接
        
        # 池化
        if self.pooling == 'mean':
            output = torch.mean(h, dim=1)
        elif self.pooling == 'max':
            output = torch.max(h, dim=1)[0]
        elif self.pooling == 'attention':
            attn_scores = self.attention(h).squeeze(-1)
            attn_weights = F.softmax(attn_scores, dim=1)
            output = torch.bmm(attn_weights.unsqueeze(1), h).squeeze(1)
        else:
            # 默认取第一个节点（根节点）
            output = h[:, 0, :]
        
        return output


# ==================== 辅助函数 ====================

def create_dummy_propagation_data(batch_size: int = 4, 
                                   max_nodes: int = 20,
                                   embedding_dim: int = 128) -> Tuple[Dict, torch.Tensor, torch.Tensor]:
    """
    创建虚拟的传播树数据用于测试
    
    Returns:
        tree_structure: 树结构字典
        node_embeddings: 节点嵌入
        relation_counts: 关系统计
    """
    num_nodes = np.random.randint(5, max_nodes)
    
    # 随机生成树结构
    adjacency = [[] for _ in range(num_nodes)]
    for i in range(1, num_nodes):
        parent = np.random.randint(0, i)
        adjacency[parent].append(i)
    
    tree_structure = {
        'adjacency': adjacency,
        'relation_types': [[0] * len(adjacency[i]) for i in range(num_nodes)],  # 全部为转发关系
        'root': 0
    }
    
    # 随机节点嵌入
    node_embeddings = torch.randn(batch_size, num_nodes, embedding_dim)
    
    # 随机关系统计
    relation_counts = torch.randn(batch_size, 9)  # 3种关系 * 3种统计量
    
    return tree_structure, node_embeddings, relation_counts


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("多关系传播树模块测试")
    print("=" * 60)
    
    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")
    
    # 测试参数
    batch_size = 4
    num_nodes = 10
    input_dim = 128
    hidden_dim = 256
    num_relations = 3
    
    # 创建测试数据
    tree_structure, node_embeddings, relation_counts = create_dummy_propagation_data(
        batch_size=batch_size,
        max_nodes=num_nodes,
        embedding_dim=input_dim
    )
    
    node_embeddings = node_embeddings.to(device)
    relation_counts = relation_counts.to(device)
    
    print(f"\n1. 测试 RelationAwareTreeLSTMCell:")
    rel_tree_lstm = RelationAwareTreeLSTMCell(input_dim, hidden_dim, num_relations).to(device)
    h = torch.randn(batch_size, input_dim).to(device)
    child_h = torch.randn(batch_size, 3, hidden_dim).to(device)
    child_c = torch.randn(batch_size, 3, hidden_dim).to(device)
    rel_ids = torch.randint(0, num_relations, (batch_size, 3)).to(device)
    
    output_h, output_c = rel_tree_lstm(h, child_h, child_c, rel_ids)
    print(f"   输出形状: h={output_h.shape}, c={output_c.shape}")
    
    print(f"\n2. 测试 PropagationTreeEncoder:")
    encoder = PropagationTreeEncoder(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_relations=num_relations,
        use_relation_aware=True,
        pooling='attention'
    ).to(device)
    
    tree_features = encoder(tree_structure, node_embeddings)
    print(f"   输出形状: {tree_features.shape}")
    
    print(f"\n3. 测试 MultiRelationPropagationTree:")
    model = MultiRelationPropagationTree(
        embedding_dim=input_dim,
        hidden_dim=hidden_dim,
        num_relations=num_relations,
        use_relation_aware=True,
        pooling='attention'
    ).to(device)
    
    output = model(node_embeddings, tree_structure, relation_counts)
    print(f"   输出形状: {output.shape}")
    
    print(f"\n4. 测试 SimplePropagationEncoder:")
    simple_encoder = SimplePropagationEncoder(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_layers=2,
        pooling='attention'
    ).to(device)
    
    # 创建邻接矩阵
    adj_matrix = torch.randn(batch_size, num_nodes, num_nodes)
    adj_matrix = (adj_matrix > 0.5).float()  # 二值化
    
    simple_output = simple_encoder(adj_matrix, node_embeddings)
    print(f"   输出形状: {simple_output.shape}")
    
    # 统计参数数量
    print(f"\n5. 模型参数量:")
    print(f"   MultiRelationPropagationTree: {sum(p.numel() for p in model.parameters()):,}")
    print(f"   SimplePropagationEncoder: {sum(p.numel() for p in simple_encoder.parameters()):,}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
