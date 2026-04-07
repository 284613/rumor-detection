# -*- coding: utf-8 -*-
"""
传播树构建模块 - 基于NetworkX构建微博谣言传播结构
用于双分支融合模型的传播树特征提取
"""

import networkx as nx
import numpy as np
from typing import List, Tuple, Dict, Optional, Any


class PropagationTreeBuilder:
    """微博谣言传播树构建器"""
    
    def __init__(self, directed: bool = True):
        """
        初始化传播树构建器
        
        Args:
            directed: 是否为有向图，默认为True（微博转发是有向的）
        """
        self.directed = directed
        self.graph = nx.DiGraph() if directed else nx.Graph()
        self.root_node = None  # 传播源节点（原始谣言发布者）
        
    def add_edge(self, status_id: str, parent_id: str) -> None:
        """
        添加转发关系边
        
        Args:
            status_id: 当前微博ID（转发者）
            parent_id: 父微博ID（被转发者/源头）
        """
        if not self.graph.has_edge(parent_id, status_id):
            self.graph.add_edge(parent_id, status_id)
    
    def build_tree(self, edges: List[Tuple[str, str]], root: Optional[str] = None) -> None:
        """
        从边列表构建传播树
        
        Args:
            edges: 边列表，格式为 [(parent_id, child_id), ...]
            root: 传播树根节点ID（可选，如果无法自动识别可指定）
        """
        self.graph.clear()
        
        # 添加所有边
        for parent_id, child_id in edges:
            self.graph.add_edge(parent_id, child_id)
        
        # 自动识别根节点（入度为0的节点）
        if root is not None:
            self.root_node = root
        else:
            self.root_node = self._identify_root()
    
    def _identify_root(self) -> Optional[str]:
        """
        自动识别传播树根节点
        
        Returns:
            根节点ID，如果没有根节点则返回None
        """
        if self.graph.number_of_nodes() == 0:
            return None
        
        # 在有向图中，找入度为0的节点（没有父节点的节点）
        if self.directed:
            in_degrees = dict(self.graph.in_degree())
            roots = [node for node, degree in in_degrees.items() if degree == 0]
            return roots[0] if roots else None
        else:
            # 无向图返回第一个节点
            return list(self.graph.nodes())[0] if self.graph.number_of_nodes() > 0 else None
    
    def get_adjacency_matrix(self) -> np.ndarray:
        """
        获取邻接矩阵
        
        Returns:
            numpy数组形式的邻接矩阵
        """
        if self.graph.number_of_nodes() == 0:
            return np.array([])
        
        # 获取节点列表（按索引排序保证一致性）
        nodes = sorted(self.graph.nodes())
        return nx.to_numpy_array(self.graph, nodelist=nodes)
    
    def get_adjacency_dict(self) -> Dict[str, List[str]]:
        """
        获取邻接表字典格式
        
        Returns:
            邻接表字典 {node: [children]}
        """
        adjacency = {}
        for node in self.graph.nodes():
            if self.directed:
                adjacency[node] = list(self.graph.successors(node))
            else:
                adjacency[node] = list(self.graph.neighbors(node))
        return adjacency
    
    def get_tree_features(self) -> Dict[str, Any]:
        """
        提取树结构特征
        
        Returns:
            包含各项特征的字典
        """
        features = {}
        
        # 基本统计信息
        features['num_nodes'] = self.graph.number_of_nodes()
        features['num_edges'] = self.graph.number_of_edges()
        
        if self.graph.number_of_nodes() == 0:
            features['depth'] = 0
            features['max_width'] = 0
            features['avg_branching_factor'] = 0.0
            features['leaf_nodes'] = []
            features['num_leaf_nodes'] = 0
            features['num_internal_nodes'] = 0
            return features
        
        # 叶子节点（无子节点的节点）
        if self.directed:
            leaf_nodes = [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]
        else:
            leaf_nodes = [n for n in self.graph.nodes() if self.graph.degree(n) == 1]
        features['leaf_nodes'] = leaf_nodes
        features['num_leaf_nodes'] = len(leaf_nodes)
        
        # 内部节点（有子节点的节点）
        internal_nodes = [n for n in self.graph.nodes() if self.graph.out_degree(n) > 0]
        features['num_internal_nodes'] = len(internal_nodes)
        
        # 计算树深度（从根到最深叶子的路径长度）
        if self.root_node:
            try:
                # 使用最短路径计算深度
                max_depth = 0
                depths = nx.single_source_shortest_path_length(self.graph, self.root_node)
                max_depth = max(depths.values()) if depths else 0
                features['depth'] = max_depth
            except nx.NetworkXError:
                features['depth'] = 0
        else:
            features['depth'] = 0
        
        # 计算每层宽度
        if self.root_node and self.directed:
            width_per_level = self._calculate_level_widths()
            features['width_per_level'] = width_per_level
            features['max_width'] = max(width_per_level) if width_per_level else 0
        else:
            features['max_width'] = 0
            features['width_per_level'] = []
        
        # 平均分支因子
        if len(internal_nodes) > 0:
            branching_factors = []
            for node in internal_nodes:
                if self.directed:
                    branching_factors.append(self.graph.out_degree(node))
                else:
                    branching_factors.append(self.graph.degree(node) - 1)  # 减去父节点连接
            features['avg_branching_factor'] = np.mean(branching_factors) if branching_factors else 0.0
        else:
            features['avg_branching_factor'] = 0.0
        
        # 度分布统计
        if self.directed:
            in_degrees = [d for n, d in self.graph.in_degree()]
            out_degrees = [d for n, d in self.graph.out_degree()]
            features['in_degree_mean'] = np.mean(in_degrees) if in_degrees else 0.0
            features['in_degree_std'] = np.std(in_degrees) if in_degrees else 0.0
            features['out_degree_mean'] = np.mean(out_degrees) if out_degrees else 0.0
            features['out_degree_std'] = np.std(out_degrees) if out_degrees else 0.0
        else:
            degrees = [d for n, d in self.graph.degree()]
            features['degree_mean'] = np.mean(degrees) if degrees else 0.0
            features['degree_std'] = np.std(degrees) if degrees else 0.0
        
        return features
    
    def _calculate_level_widths(self) -> List[int]:
        """
        计算每层的节点数量（宽度）
        
        Returns:
            每层节点数的列表
        """
        if not self.root_node or self.graph.number_of_nodes() == 0:
            return []
        
        try:
            # BFS计算每层节点
            levels = {}
            nx.single_source_shortest_path_length(self.graph, self.root_node, cutoff=None)
            
            # 重新用BFS分层
            from collections import deque
            queue = deque([(self.root_node, 0)])
            visited = {self.root_node}
            level_widths = []
            current_level = 0
            current_level_count = 0
            
            while queue:
                node, level = queue.popleft()
                
                if level > current_level:
                    level_widths.append(current_level_count)
                    current_level = level
                    current_level_count = 0
                
                current_level_count += 1
                
                # 获取子节点
                children = list(self.graph.successors(node)) if self.directed else list(self.graph.neighbors(node))
                for child in children:
                    if child not in visited:
                        visited.add(child)
                        queue.append((child, level + 1))
            
            # 添加最后一层
            if current_level_count > 0:
                level_widths.append(current_level_count)
            
            return level_widths
        except nx.NetworkXError:
            return []
    
    def to_nested_list(self) -> List[List[str]]:
        """
        转换为嵌套列表格式（适合模型输入）
        
        Returns:
            嵌套列表，每层一个列表包含该层所有节点ID
        """
        if not self.root_node or self.graph.number_of_nodes() == 0:
            return []
        
        try:
            from collections import deque
            
            # BFS分层
            levels = []
            queue = deque([(self.root_node, 0)])
            visited = {self.root_node}
            
            while queue:
                node, level = queue.popleft()
                
                if level >= len(levels):
                    levels.append([])
                
                levels[level].append(node)
                
                # 获取子节点
                children = list(self.graph.successors(node)) if self.directed else list(self.graph.neighbors(node))
                for child in children:
                    if child not in visited:
                        visited.add(child)
                        queue.append((child, level + 1))
            
            return levels
        except nx.NetworkXError:
            return []
    
    def get_subtree_size(self, node: str) -> int:
        """
        获取指定节点的子树大小
        
        Args:
            node: 节点ID
            
        Returns:
            子树中的节点数量（包括自身）
        """
        if node not in self.graph:
            return 0
        
        try:
            if self.directed:
                successors = nx.descendants(self.graph, node)
                return len(successors) + 1  # 加上自身
            else:
                # 无向图使用可达节点
                successors = nx.descendants(self.graph, node)
                return len(successors) + 1
        except nx.NetworkXError:
            return 1
    
    def get_node_depth(self, node: str) -> int:
        """
        获取指定节点的深度（从根节点开始的层数）
        
        Args:
            node: 节点ID
            
        Returns:
            节点深度，根节点为0
        """
        if not self.root_node or node not in self.graph:
            return -1
        
        try:
            if self.directed:
                length = nx.shortest_path_length(self.graph, self.root_node, node)
            else:
                length = nx.shortest_path_length(self.graph, self.root_node, node)
            return length
        except nx.NetworkXError:
            return -1
    
    def get_path_to_root(self, node: str) -> List[str]:
        """
        获取从指定节点到根节点的路径
        
        Args:
            node: 节点ID
            
        Returns:
            路径节点列表 [node, ..., root]
        """
        if not self.root_node or node not in self.graph:
            return []
        
        try:
            if self.directed:
                path = nx.shortest_path(self.graph, node, self.root_node)
            else:
                path = nx.shortest_path(self.graph, node, self.root_node)
            return list(reversed(path))
        except nx.NetworkXError:
            return []
    
    def visualize_tree(self) -> str:
        """
        生成树结构的文本可视化
        
        Returns:
            树结构的文本表示
        """
        if self.graph.number_of_nodes() == 0:
            return "Empty Tree"
        
        lines = []
        nested = self.to_nested_list()
        
        for level_idx, nodes in enumerate(nested):
            indent = "  " * level_idx
            lines.append(f"{indent}Level {level_idx}: {nodes}")
        
        return "\n".join(lines)
    
    def export_for_model(self) -> Dict[str, Any]:
        """
        导出适合模型输入的完整数据
        
        Returns:
            包含邻接矩阵和特征的字典
        """
        return {
            'adjacency_matrix': self.get_adjacency_matrix(),
            'features': self.get_tree_features(),
            'nested_list': self.to_nested_list(),
            'root': self.root_node,
            'num_nodes': self.graph.number_of_nodes()
        }


# ==================== 便捷函数 ====================

def build_propagation_tree_from_weibo(weibo_data: List[Dict], 
                                       source_field: str = 'parent_id',
                                       target_field: str = 'status_id') -> PropagationTreeBuilder:
    """
    从微博数据构建传播树
    
    Args:
        weibo_data: 微博数据列表，每条包含source和target字段
        source_field: 源节点字段名
        target_field: 目标节点字段名
        
    Returns:
        PropagationTreeBuilder实例
    """
    builder = PropagationTreeBuilder(directed=True)
    
    edges = []
    for item in weibo_data:
        if source_field in item and target_field in item:
            parent = str(item[source_field])
            child = str(item[target_field])
            if parent and child and parent != child:
                edges.append((parent, child))
    
    builder.build_tree(edges)
    return builder


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试用例
    print("=" * 50)
    print("传播树构建模块测试")
    print("=" * 50)
    
    # 创建测试数据：模拟微博转发关系
    # 节点0是源头，节点1转发0，节点2转发1，节点3转发1，节点4转发2...
    test_edges = [
        ('0', '1'),  # 1转发0
        ('1', '2'),  # 2转发1
        ('1', '3'),  # 3转发1
        ('2', '4'),  # 4转发2
        ('2', '5'),  # 5转发2
        ('3', '6'),  # 6转发3
    ]
    
    # 初始化构建器
    builder = PropagationTreeBuilder(directed=True)
    
    # 构建传播树
    builder.build_tree(test_edges, root='0')
    
    print(f"\n1. 传播树基本信息:")
    print(f"   节点数: {builder.graph.number_of_nodes()}")
    print(f"   边数: {builder.graph.number_of_edges()}")
    print(f"   根节点: {builder.root_node}")
    
    # 获取邻接矩阵
    print(f"\n2. 邻接矩阵:")
    adj_matrix = builder.get_adjacency_matrix()
    print(f"   形状: {adj_matrix.shape}")
    print(f"   矩阵:\n{adj_matrix}")
    
    # 获取树特征
    print(f"\n3. 树结构特征:")
    features = builder.get_tree_features()
    for key, value in features.items():
        print(f"   {key}: {value}")
    
    # 转换为嵌套列表
    print(f"\n4. 嵌套列表格式（层级结构）:")
    nested = builder.to_nested_list()
    for level, nodes in enumerate(nested):
        print(f"   Level {level}: {nodes}")
    
    # 导出模型输入格式
    print(f"\n5. 模型输入格式:")
    model_data = builder.export_for_model()
    print(f"   num_nodes: {model_data['num_nodes']}")
    print(f"   root: {model_data['root']}")
    print(f"   adjacency_matrix shape: {model_data['adjacency_matrix'].shape}")
    
    # 文本可视化
    print(f"\n6. 树结构可视化:")
    print(builder.visualize_tree())
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)
