# -*- coding: utf-8 -*-
"""
多任务学习模型
共享BERT编码层，两个任务头：谣言分类 + 立场检测
联合损失函数
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, Dict
import copy


class MultiTaskLoss(nn.Module):
    """
    多任务损失函数
    支持加权求和、动态权重等方式
    """
    
    def __init__(self, 
                 num_tasks: int = 2,
                 loss_type: str = 'weighted_sum',
                 initial_weights: Optional[Tuple[float, ...]] = None,
                 uncertainty_weighting: bool = False):
        """
        Args:
            num_tasks: 任务数量
            loss_type: 损失类型 ('weighted_sum', 'dynamic_weight', 'uncertainty')
            initial_weights: 初始任务权重
            uncertainty_weighting: 是否使用不确定性加权
        """
        super(MultiTaskLoss, self).__init__()
        
        self.num_tasks = num_tasks
        self.loss_type = loss_type
        
        if loss_type == 'uncertainty' and uncertainty_weighting:
            # 学习不确定性权重
            self.log_vars = nn.Parameter(torch.zeros(num_tasks))
        else:
            self.log_vars = None
        
        if initial_weights is not None:
            self.weights = torch.tensor(initial_weights, dtype=torch.float32)
            if torch.cuda.is_available():
                self.weights = self.weights.cuda()
        else:
            self.weights = torch.ones(num_tasks, dtype=torch.float32)
            if torch.cuda.is_available():
                self.weights = self.weights.cuda()
    
    def forward(self, 
                losses: Tuple[torch.Tensor, ...]) -> Tuple[torch.Tensor, Dict]:
        """
        计算多任务总损失
        
        Args:
            losses: 各任务的损失元组
            
        Returns:
            total_loss: 总损失
            info: 附加信息
        """
        assert len(losses) == self.num_tasks, f"Expected {self.num_tasks} losses, got {len(losses)}"
        
        if self.loss_type == 'weighted_sum':
            # 加权求和
            total_loss = sum(w * loss for w, loss in zip(self.weights, losses))
            info = {'weights': self.weights.cpu().detach().numpy()}
            
        elif self.loss_type == 'dynamic_weight':
            # 动态权重 - 基于损失大小自动调整
            losses_tensor = torch.stack(losses)
            # 归一化权重
            weights = F.softmax(losses_tensor, dim=0)
            self.weights = weights  # 更新权重
            total_loss = sum(w * loss for w, loss in zip(weights, losses))
            info = {'weights': weights.cpu().detach().numpy()}
            
        elif self.loss_type == 'uncertainty':
            # 基于不确定性的加权 (Kendall et al., 2018)
            if self.log_vars is not None:
                # 使用学习的log方差
                precision = torch.exp(-self.log_vars)
                total_loss = sum(precision[i] * losses[i] + self.log_vars[i] 
                                for i in range(self.num_tasks))
                info = {
                    'weights': torch.exp(-self.log_vars).cpu().detach().numpy(),
                    'uncertainties': torch.exp(self.log_vars).cpu().detach().numpy()
                }
            else:
                # 使用固定权重
                total_loss = sum(w * loss for w, loss in zip(self.weights, losses))
                info = {'weights': self.weights.cpu().detach().numpy()}
        else:
            raise ValueError(f"Unknown loss type: {self.loss_type}")
        
        return total_loss, info


class SharedBERTEncoder(nn.Module):
    """
    共享BERT编码器
    用于多任务学习的特征提取
    """
    
    def __init__(self, 
                 bert_model_name: str = "bert-base-chinese",
                 hidden_dim: int = 768,
                 freeze_bert: bool = False,
                 pooling_strategy: str = 'cls'):
        super(SharedBERTEncoder, self).__init__()
        
        self.bert_model_name = bert_model_name
        self.hidden_dim = hidden_dim
        self.pooling_strategy = pooling_strategy
        
        # 尝试导入transformers
        try:
            from transformers import BertModel, BertTokenizer
            self.use_transformers = True
        except ImportError:
            print("[WARNING] transformers库未安装，使用简单编码器代替")
            self.use_transformers = False
            self.embedding = nn.Embedding(21128, hidden_dim, padding_idx=0)
            return
        
        # 加载预训练BERT
        self.bert = BertModel.from_pretrained(bert_model_name)
        self.tokenizer = BertTokenizer.from_pretrained(bert_model_name)
        
        # 冻结BERT参数
        if freeze_bert:
            for param in self.bert.parameters():
                param.requires_grad = False
        
        # 投影层
        if hidden_dim != 768:
            self.projection = nn.Linear(768, hidden_dim)
        else:
            self.projection = None
    
    def forward(self, 
                input_ids: torch.Tensor, 
                attention_mask: Optional[torch.Tensor] = None,
                output_all_layers: bool = False) -> Tuple[torch.Tensor, ...]:
        """
        Args:
            input_ids: 输入ID (batch_size, seq_len)
            attention_mask: 注意力掩码 (batch_size, seq_len)
            output_all_layers: 是否输出所有层
            
        Returns:
            编码后的特征
        """
        if not self.use_transformers:
            output = self.embedding(input_ids)
            if self.pooling_strategy == 'mean':
                output = torch.mean(output, dim=1)
            elif self.pooling_strategy == 'max':
                output = torch.max(output, dim=1)[0]
            else:
                output = output[:, 0, :]
            return (output,)
        
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask,
                           output_hidden_states=output_all_layers)
        
        if output_all_layers:
            # 返回所有层的隐藏状态
            all_layers = outputs.hidden_states  # tuple of (batch_size, seq_len, hidden_dim)
            all_outputs = []
            for layer_output in all_layers:
                if self.pooling_strategy == 'cls':
                    pooled = layer_output[:, 0, :]
                elif self.pooling_strategy == 'mean':
                    pooled = torch.mean(layer_output, dim=1)
                else:
                    pooled = layer_output[:, 0, :]
                
                if self.projection is not None:
                    pooled = self.projection(pooled)
                all_outputs.append(pooled)
            
            return tuple(all_outputs)
        else:
            sequence_output = outputs.last_hidden_state
            pooled_output = outputs.pooler_output
            
            if self.pooling_strategy == 'cls':
                output = pooled_output
            elif self.pooling_strategy == 'mean':
                output = torch.mean(sequence_output, dim=1)
            elif self.pooling_strategy == 'max':
                output = torch.max(sequence_output, dim=1)[0]
            else:
                output = pooled_output
            
            if self.projection is not None:
                output = self.projection(output)
            
            return (output,)
    
    def tokenize(self, texts: list, max_length: int = 128) -> Tuple[torch.Tensor, torch.Tensor]:
        """对文本进行tokenize"""
        if not self.use_transformers:
            return None, None
        
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors='pt'
        )
        
        return encoded['input_ids'], encoded['attention_mask']


class TaskSpecificHead(nn.Module):
    """
    任务特定的头部网络
    """
    
    def __init__(self, 
                 input_dim: int, 
                 output_dim: int,
                 hidden_dim: Optional[int] = None,
                 num_layers: int = 2,
                 dropout: float = 0.3):
        super(TaskSpecificHead, self).__init__()
        
        if hidden_dim is None:
            hidden_dim = input_dim // 2
        
        layers = []
        current_dim = input_dim
        
        for i in range(num_layers):
            next_dim = hidden_dim if i < num_layers - 1 else output_dim
            layers.append(nn.Linear(current_dim, next_dim))
            
            if i < num_layers - 1:
                layers.append(nn.ReLU())
                layers.append(nn.Dropout(dropout))
            
            current_dim = next_dim
        
        self.head = nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(x)


class MultiTaskModel(nn.Module):
    """
    多任务学习模型
    共享BERT编码层，谣言分类 + 立场检测两个任务头
    """
    
    def __init__(self,
                 bert_model_name: str = "bert-base-chinese",
                 hidden_dim: int = 768,
                 rumor_classes: int = 2,  # 谣言分类：非谣言/谣言
                 stance_classes: int = 3,  # 立场检测：支持/反对/中立
                 dropout: float = 0.3,
                 use_propagation_features: bool = False,
                 propagation_feature_dim: int = 256,
                 freeze_bert: bool = False):
        super(MultiTaskModel, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.rumor_classes = rumor_classes
        self.stance_classes = stance_classes
        self.use_propagation_features = use_propagation_features
        
        # 共享BERT编码器
        self.encoder = SharedBERTEncoder(
            bert_model_name=bert_model_name,
            hidden_dim=hidden_dim,
            freeze_bert=freeze_bert,
            pooling_strategy='cls'
        )
        
        # 任务特定的头部
        # 任务1：谣言分类
        self.rumor_head = TaskSpecificHead(
            input_dim=hidden_dim,
            output_dim=rumor_classes,
            hidden_dim=hidden_dim // 2,
            num_layers=2,
            dropout=dropout
        )
        
        # 任务2：立场检测
        self.stance_head = TaskSpecificHead(
            input_dim=hidden_dim,
            output_dim=stance_classes,
            hidden_dim=hidden_dim // 2,
            num_layers=2,
            dropout=dropout
        )
        
        # 传播特征融合（可选）
        if use_propagation_features:
            self.propagation_encoder = nn.Sequential(
                nn.Linear(propagation_feature_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
            
            # 融合后的谣言分类头
            self.rumor_head_with_propagation = TaskSpecificHead(
                input_dim=hidden_dim * 2,  # BERT特征 + 传播特征
                output_dim=rumor_classes,
                hidden_dim=hidden_dim,
                num_layers=2,
                dropout=dropout
            )
    
    def forward(self, 
                input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None,
                propagation_features: Optional[torch.Tensor] = None,
                task: str = 'both') -> Dict[str, torch.Tensor]:
        """
        Args:
            input_ids: 输入ID (batch_size, seq_len)
            attention_mask: 注意力掩码 (batch_size, seq_len)
            propagation_features: 传播树特征 (batch_size, propagation_feature_dim)
            task: 指定任务 ('rumor', 'stance', 'both')
            
        Returns:
            dict: 各任务的logits
        """
        # 共享编码
        encoded = self.encoder(input_ids, attention_mask)
        text_features = encoded[0]  # (batch_size, hidden_dim)
        
        outputs = {}
        
        # 谣言分类
        if task in ['rumor', 'both']:
            if self.use_propagation_features and propagation_features is not None:
                # 融合传播特征
                prop_encoded = self.propagation_encoder(propagation_features)
                combined = torch.cat([text_features, prop_encoded], dim=-1)
                outputs['rumor_logits'] = self.rumor_head_with_propagation(combined)
            else:
                outputs['rumor_logits'] = self.rumor_head(text_features)
        
        # 立场检测
        if task in ['stance', 'both']:
            outputs['stance_logits'] = self.stance_head(text_features)
        
        return outputs
    
    def get_shared_features(self,
                          input_ids: torch.Tensor,
                          attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """获取共享特征表示"""
        encoded = self.encoder(input_ids, attention_mask)
        return encoded[0]


class SimpleMultiTaskModel(nn.Module):
    """
    简化版多任务模型
    不依赖transformers库，使用简单的编码器
    """
    
    def __init__(self,
                 vocab_size: int = 21128,
                 embed_dim: int = 256,
                 hidden_dim: int = 512,
                 rumor_classes: int = 2,
                 stance_classes: int = 3,
                 num_encoder_layers: int = 4,
                 num_heads: int = 8,
                 dropout: float = 0.3):
        super(SimpleMultiTaskModel, self).__init__()
        
        self.hidden_dim = hidden_dim
        
        # 词嵌入 + 位置编码
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.position_encoding = PositionalEncoding(embed_dim, dropout=dropout)
        
        # Transformer编码器
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)
        
        # 投影层
        self.projection = nn.Linear(embed_dim, hidden_dim)
        
        # 任务头
        self.rumor_head = TaskSpecificHead(
            input_dim=hidden_dim,
            output_dim=rumor_classes,
            hidden_dim=hidden_dim // 2,
            num_layers=2,
            dropout=dropout
        )
        
        self.stance_head = TaskSpecificHead(
            input_dim=hidden_dim,
            output_dim=stance_classes,
            hidden_dim=hidden_dim // 2,
            num_layers=2,
            dropout=dropout
        )
    
    def forward(self, 
                input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None,
                task: str = 'both') -> Dict[str, torch.Tensor]:
        """
        Args:
            input_ids: 输入ID (batch_size, seq_len)
            attention_mask: 注意力掩码 (batch_size, seq_len)
            task: 指定任务
            
        Returns:
            各任务的logits
        """
        # 嵌入
        x = self.embedding(input_ids)  # (batch_size, seq_len, embed_dim)
        x = self.position_encoding(x)
        
        # Transformer编码
        if attention_mask is not None:
            mask = (attention_mask == 0)
            x = self.transformer(x, src_key_padding_mask=mask)
        else:
            x = self.transformer(x)
        
        # 池化 - 使用CLS
        x = x[:, 0, :]  # (batch_size, embed_dim)
        
        # 投影
        x = self.projection(x)  # (batch_size, hidden_dim)
        
        outputs = {}
        
        if task in ['rumor', 'both']:
            outputs['rumor_logits'] = self.rumor_head(x)
        
        if task in ['stance', 'both']:
            outputs['stance_logits'] = self.stance_head(x)
        
        return outputs


class PositionalEncoding(nn.Module):
    """位置编码"""
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-torch.log(torch.tensor(10000.0)) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


# ==================== 训练器类 ====================

class MultiTaskTrainer:
    """
    多任务学习训练器
    """
    
    def __init__(self,
                 model: nn.Module,
                 optimizer: torch.optim.Optimizer,
                 device: torch.device,
                 task_weights: Tuple[float, float] = (1.0, 1.0),
                 loss_type: str = 'weighted_sum'):
        
        self.model = model
        self.optimizer = optimizer
        self.device = device
        
        # 多任务损失
        self.criterion = nn.CrossEntropyLoss()
        self.multi_task_loss = MultiTaskLoss(
            num_tasks=2,
            loss_type=loss_type,
            initial_weights=task_weights
        )
    
    def train_epoch(self, dataloader, task='both'):
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        rumor_correct = 0
        stance_correct = 0
        total = 0
        
        for batch in dataloader:
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch.get('attention_mask', None)
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)
            
            rumor_labels = batch['rumor_labels'].to(self.device)
            stance_labels = batch['stance_labels'].to(self.device)
            
            # 前向传播
            outputs = self.model(input_ids, attention_mask, task='both')
            
            # 计算各任务损失
            loss_rumor = self.criterion(outputs['rumor_logits'], rumor_labels)
            loss_stance = self.criterion(outputs['stance_logits'], stance_labels)
            
            # 多任务损失
            total_loss_batch, loss_info = self.multi_task_loss((loss_rumor, loss_stance))
            
            # 反向传播
            self.optimizer.zero_grad()
            total_loss_batch.backward()
            self.optimizer.step()
            
            # 统计
            total_loss += total_loss_batch.item()
            
            rumor_preds = torch.argmax(outputs['rumor_logits'], dim=1)
            stance_preds = torch.argmax(outputs['stance_logits'], dim=1)
            
            rumor_correct += (rumor_preds == rumor_labels).sum().item()
            stance_correct += (stance_preds == stance_labels).sum().item()
            total += rumor_labels.size(0)
        
        avg_loss = total_loss / len(dataloader)
        rumor_acc = rumor_correct / total
        stance_acc = stance_correct / total
        
        return {
            'loss': avg_loss,
            'rumor_acc': rumor_acc,
            'stance_acc': stance_acc,
            'weights': loss_info.get('weights', None)
        }
    
    def evaluate(self, dataloader, task='both'):
        """评估模型"""
        self.model.eval()
        total_loss = 0
        rumor_correct = 0
        stance_correct = 0
        total = 0
        
        all_rumor_preds = []
        all_rumor_labels = []
        all_stance_preds = []
        all_stance_labels = []
        
        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch.get('attention_mask', None)
                if attention_mask is not None:
                    attention_mask = attention_mask.to(self.device)
                
                rumor_labels = batch['rumor_labels'].to(self.device)
                stance_labels = batch['stance_labels'].to(self.device)
                
                outputs = self.model(input_ids, attention_mask, task='both')
                
                loss_rumor = self.criterion(outputs['rumor_logits'], rumor_labels)
                loss_stance = self.criterion(outputs['stance_logits'], stance_labels)
                
                total_loss_batch, _ = self.multi_task_loss((loss_rumor, loss_stance))
                total_loss += total_loss_batch.item()
                
                rumor_preds = torch.argmax(outputs['rumor_logits'], dim=1)
                stance_preds = torch.argmax(outputs['stance_logits'], dim=1)
                
                rumor_correct += (rumor_preds == rumor_labels).sum().item()
                stance_correct += (stance_preds == stance_labels).sum().item()
                total += rumor_labels.size(0)
                
                all_rumor_preds.extend(rumor_preds.cpu().numpy())
                all_rumor_labels.extend(rumor_labels.cpu().numpy())
                all_stance_preds.extend(stance_preds.cpu().numpy())
                all_stance_labels.extend(stance_labels.cpu().numpy())
        
        avg_loss = total_loss / len(dataloader)
        rumor_acc = rumor_correct / total
        stance_acc = stance_correct / total
        
        return {
            'loss': avg_loss,
            'rumor_acc': rumor_acc,
            'stance_acc': stance_acc,
            'rumor_preds': all_rumor_preds,
            'rumor_labels': all_rumor_labels,
            'stance_preds': all_stance_preds,
            'stance_labels': all_stance_labels
        }


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("多任务学习模型测试")
    print("=" * 60)
    
    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")
    
    # 测试参数
    batch_size = 4
    seq_len = 32
    hidden_dim = 512
    rumor_classes = 2
    stance_classes = 3
    
    print(f"\n1. 测试 MultiTaskLoss:")
    loss_fn = MultiTaskLoss(
        num_tasks=2,
        loss_type='uncertainty',
        uncertainty_weighting=True
    ).to(device)
    
    loss1 = torch.tensor(0.5, requires_grad=True).to(device)
    loss2 = torch.tensor(0.8, requires_grad=True).to(device)
    total_loss, info = loss_fn((loss1, loss2))
    print(f"   损失1: {loss1.item()}, 损失2: {loss2.item()}")
    print(f"   总损失: {total_loss.item()}")
    print(f"   信息: {info}")
    
    print(f"\n2. 测试 SimpleMultiTaskModel:")
    model = SimpleMultiTaskModel(
        vocab_size=21128,
        embed_dim=256,
        hidden_dim=hidden_dim,
        rumor_classes=rumor_classes,
        stance_classes=stance_classes,
        num_encoder_layers=4,
        num_heads=8
    ).to(device)
    
    input_ids = torch.randint(0, 21128, (batch_size, seq_len)).to(device)
    attention_mask = torch.ones(batch_size, seq_len).to(device)
    
    outputs = model(input_ids, attention_mask, task='both')
    print(f"   输入形状: {input_ids.shape}")
    print(f"   谣言分类logits: {outputs['rumor_logits'].shape}")
    print(f"   立场检测logits: {outputs['stance_logits'].shape}")
    
    # 计算损失
    rumor_labels = torch.randint(0, rumor_classes, (batch_size,)).to(device)
    stance_labels = torch.randint(0, stance_classes, (batch_size,)).to(device)
    
    criterion = nn.CrossEntropyLoss()
    loss_rumor = criterion(outputs['rumor_logits'], rumor_labels)
    loss_stance = criterion(outputs['stance_logits'], stance_labels)
    print(f"   谣言分类损失: {loss_rumor.item():.4f}")
    print(f"   立场检测损失: {loss_stance.item():.4f}")
    
    print(f"\n3. 模型参数量:")
    print(f"   SimpleMultiTaskModel: {sum(p.numel() for p in model.parameters()):,}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
