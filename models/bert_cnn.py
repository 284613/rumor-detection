# -*- coding: utf-8 -*-
"""
BERT + CNN 模型
使用BERT作为编码器，CNN进行多尺度卷积特征提取
支持Condition条件融合
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple


class CNNFeatureExtractor(nn.Module):
    """
    CNN特征提取器
    使用多尺度卷积核提取不同粒度的特征
    """
    
    def __init__(self, 
                 input_dim: int, 
                 num_filters: int = 256,
                 filter_sizes: Tuple[int, ...] = (2, 3, 4, 5),
                 dropout: float = 0.3):
        super(CNNFeatureExtractor, self).__init__()
        
        self.input_dim = input_dim
        self.num_filters = num_filters
        self.filter_sizes = filter_sizes
        
        # 多尺度卷积层
        self.convs = nn.ModuleList([
            nn.Conv1d(input_dim, num_filters, fs) 
            for fs in filter_sizes
        ])
        
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: 输入 (batch_size, seq_len, input_dim)
            
        Returns:
            output: 多尺度卷积特征 (batch_size, num_filters * len(filter_sizes))
        """
        # 转换为 (batch_size, input_dim, seq_len)
        x = x.transpose(1, 2)
        
        # 多尺度卷积
        conv_outputs = []
        for conv in self.convs:
            c = F.relu(conv(x))  # (batch_size, num_filters, seq_len - fs + 1)
            c = F.max_pool1d(c, c.size(2)).squeeze(2)  # (batch_size, num_filters)
            conv_outputs.append(c)
        
        # 拼接
        output = torch.cat(conv_outputs, dim=1)  # (batch_size, num_filters * len(filter_sizes))
        output = self.dropout(output)
        
        return output


class ConditionFusion(nn.Module):
    """
    条件融合模块
    用于将外部条件信息（如传播树特征）融入主模型
    """
    
    def __init__(self, 
                 main_dim: int, 
                 condition_dim: int,
                 output_dim: int,
                 fusion_type: str = 'gated'):
        super(ConditionFusion, self).__init__()
        
        self.main_dim = main_dim
        self.condition_dim = condition_dim
        self.output_dim = output_dim
        self.fusion_type = fusion_type
        
        if fusion_type == 'gated':
            # 门控融合
            self.gate = nn.Sequential(
                nn.Linear(main_dim + condition_dim, output_dim),
                nn.Sigmoid()
            )
            self.transform = nn.Sequential(
                nn.Linear(main_dim + condition_dim, output_dim),
                nn.Tanh()
            )
            
        elif fusion_type == 'concat':
            # 简单拼接后变换
            self.fc = nn.Sequential(
                nn.Linear(main_dim + condition_dim, output_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(output_dim, output_dim)
            )
            
        elif fusion_type == 'bilinear':
            # 双线性融合
            self.W = nn.Linear(main_dim, output_dim, bias=False)
            
        elif fusion_type == 'attention':
            # 注意力融合
            self.attention = nn.MultiheadAttention(
                embed_dim=main_dim,
                num_heads=8,
                dropout=0.1
            )
            self.output_proj = nn.Linear(main_dim, output_dim)
            
        else:
            raise ValueError(f"Unknown fusion type: {fusion_type}")
    
    def forward(self, 
                main_features: torch.Tensor, 
                condition_features: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            main_features: 主特征 (batch_size, main_dim)
            condition_features: 条件特征 (batch_size, condition_dim)
            
        Returns:
            output: 融合后的特征 (batch_size, output_dim)
        """
        if condition_features is None:
            # 无条件特征时，直接线性变换
            return self._transform_main(main_features)
        
        if self.fusion_type == 'gated':
            # 门控融合
            combined = torch.cat([main_features, condition_features], dim=-1)
            gate = self.gate(combined)
            transform = self.transform(combined)
            output = gate * transform
            
        elif self.fusion_type == 'concat':
            # 拼接融合
            combined = torch.cat([main_features, condition_features], dim=-1)
            output = self.fc(combined)
            
        elif self.fusion_type == 'bilinear':
            # 双线性融合
            output = self.W(main_features * condition_features)
            
        elif self.fusion_type == 'attention':
            # 注意力融合
            # 将condition作为key和value，main作为query
            main_features_seq = main_features.unsqueeze(0)  # (1, batch_size, main_dim)
            condition_features_seq = condition_features.unsqueeze(0)  # (1, batch_size, condition_dim)
            
            # 由于维度不同，需要先投影
            condition_proj = F.linear(condition_features_seq, 
                                     torch.eye(self.condition_dim, self.main_dim, device=condition_features.device).unsqueeze(0))
            
            output, _ = self.attention(main_features_seq, condition_proj, condition_proj)
            output = output.squeeze(0)
            output = self.output_proj(output)
            
        else:
            output = main_features
        
        return output
    
    def _transform_main(self, x: torch.Tensor) -> torch.Tensor:
        """无条件时的简单变换"""
        if self.fusion_type == 'gated':
            return torch.tanh(F.linear(x, torch.eye(self.main_dim, self.output_dim, device=x.device).unsqueeze(0).squeeze(0)))
        elif self.fusion_type == 'concat':
            return F.relu(F.linear(x, torch.eye(self.main_dim, self.output_dim, device=x.device).unsqueeze(0).squeeze(0)))
        else:
            return x


class BERTTextEncoder(nn.Module):
    """
    BERT文本编码器
    封装BERT模型的编码功能
    """
    
    def __init__(self, 
                 bert_model_name: str = "bert-base-chinese",
                 hidden_dim: int = 768,
                 freeze_bert: bool = False,
                 pooling_strategy: str = 'cls'):
        """
        Args:
            bert_model_name: BERT模型名称
            hidden_dim: BERT隐藏层维度
            freeze_bert: 是否冻结BERT参数
            pooling_strategy: 池化策略 ('cls', 'mean', 'max')
        """
        super(BERTTextEncoder, self).__init__()
        
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
            
            # 简单的词嵌入作为替代
            self.embedding = nn.Embedding(21128, hidden_dim, padding_idx=0)
            return
        
        # 加载预训练BERT
        self.bert = BertModel.from_pretrained(bert_model_name)
        self.tokenizer = BertTokenizer.from_pretrained(bert_model_name)
        
        # 冻结BERT参数
        if freeze_bert:
            for param in self.bert.parameters():
                param.requires_grad = False
        
        # 投影层（如果hidden_dim不匹配）
        if hidden_dim != 768:
            self.projection = nn.Linear(768, hidden_dim)
        else:
            self.projection = None
    
    def forward(self, 
                input_ids: torch.Tensor, 
                attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            input_ids: 输入ID (batch_size, seq_len)
            attention_mask: 注意力掩码 (batch_size, seq_len)
            
        Returns:
            output: 编码后的特征 (batch_size, hidden_dim)
        """
        if not self.use_transformers:
            # 使用简单嵌入
            output = self.embedding(input_ids)
            if self.pooling_strategy == 'mean':
                output = torch.mean(output, dim=1)
            elif self.pooling_strategy == 'max':
                output = torch.max(output, dim=1)[0]
            else:
                output = output[:, 0, :]  # CLS
            return output
        
        # BERT编码
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        
        # 获取序列表示
        sequence_output = outputs.last_hidden_state  # (batch_size, seq_len, hidden_dim)
        pooled_output = outputs.pooler_output  # (batch_size, hidden_dim)
        
        # 根据池化策略选择输出
        if self.pooling_strategy == 'cls':
            # 使用[CLS] token
            output = pooled_output
        elif self.pooling_strategy == 'mean':
            # 平均池化
            if attention_mask is not None:
                # 考虑padding
                mask_expanded = attention_mask.unsqueeze(-1).expand(sequence_output.size()).float()
                sum_embeddings = torch.sum(sequence_output * mask_expanded, dim=1)
                sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
                output = sum_embeddings / sum_mask
            else:
                output = torch.mean(sequence_output, dim=1)
        elif self.pooling_strategy == 'max':
            # 最大池化
            output = torch.max(sequence_output, dim=1)[0]
        else:
            output = pooled_output
        
        # 投影
        if self.projection is not None:
            output = self.projection(output)
        
        return output
    
    def tokenize(self, texts: list, max_length: int = 128) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        对文本列表进行tokenize
        
        Args:
            texts: 文本列表
            max_length: 最大序列长度
            
        Returns:
            input_ids: 输入ID
            attention_mask: 注意力掩码
        """
        if not self.use_transformers:
            # 简单的tokenize
            encoded = self.embedding.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors='pt'
            )
            return encoded['input_ids'], encoded['attention_mask']
        
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors='pt'
        )
        
        return encoded['input_ids'], encoded['attention_mask']


class BERTCNNModel(nn.Module):
    """
    BERT + CNN 模型
    使用BERT编码文本，CNN提取多尺度特征，支持条件融合
    """
    
    def __init__(self,
                 bert_model_name: str = "bert-base-chinese",
                 hidden_dim: int = 768,
                 cnn_num_filters: int = 256,
                 cnn_filter_sizes: Tuple[int, ...] = (2, 3, 4, 5),
                 num_classes: int = 2,
                 dropout: float = 0.3,
                 use_condition: bool = False,
                 condition_dim: int = 256,
                 fusion_type: str = 'gated'):
        super(BERTCNNModel, self).__init__()
        
        self.bert_model_name = bert_model_name
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.use_condition = use_condition
        
        # BERT编码器
        self.bert_encoder = BERTTextEncoder(
            bert_model_name=bert_model_name,
            hidden_dim=hidden_dim,
            freeze_bert=False,
            pooling_strategy='cls'
        )
        
        # CNN特征提取
        self.cnn_extractor = CNNFeatureExtractor(
            input_dim=hidden_dim,
            num_filters=cnn_num_filters,
            filter_sizes=cnn_filter_sizes,
            dropout=dropout
        )
        
        # 条件融合
        cnn_output_dim = cnn_num_filters * len(cnn_filter_sizes)
        
        if use_condition:
            self.condition_fusion = ConditionFusion(
                main_dim=cnn_output_dim,
                condition_dim=condition_dim,
                output_dim=cnn_output_dim,
                fusion_type=fusion_type
            )
            # 条件编码层
            self.condition_encoder = nn.Sequential(
                nn.Linear(condition_dim, condition_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
        else:
            self.condition_fusion = None
            self.condition_encoder = None
        
        # 分类器
        self.classifier = nn.Sequential(
            nn.Linear(cnn_output_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, 
                input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None,
                condition_features: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            input_ids: 输入ID (batch_size, seq_len)
            attention_mask: 注意力掩码 (batch_size, seq_len)
            condition_features: 条件特征，如传播树特征 (batch_size, condition_dim)
            
        Returns:
            logits: 分类 logits (batch_size, num_classes)
        """
        # BERT编码
        bert_features = self.bert_encoder(input_ids, attention_mask)  # (batch_size, hidden_dim)
        
        # 扩展为序列用于CNN
        bert_features_seq = bert_features.unsqueeze(1)  # (batch_size, 1, hidden_dim)
        
        # CNN特征提取
        cnn_features = self.cnn_extractor(bert_features_seq)  # (batch_size, cnn_output_dim)
        
        # 条件融合
        if self.use_condition and condition_features is not None:
            condition_encoded = self.condition_encoder(condition_features)
            fused_features = self.condition_fusion(cnn_features, condition_encoded)
        else:
            fused_features = cnn_features
        
        # 分类
        logits = self.classifier(fused_features)
        
        return logits
    
    def get_text_features(self,
                         input_ids: torch.Tensor,
                         attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        获取文本特征（用于特征提取）
        """
        bert_features = self.bert_encoder(input_ids, attention_mask)
        return bert_features


class SimpleBERTCNNModel(nn.Module):
    """
    简化版BERT+CNN模型
    用于无GPU或资源受限的情况
    使用随机初始化的BERT层
    """
    
    def __init__(self,
                 vocab_size: int = 21128,
                 hidden_dim: int = 768,
                 num_layers: int = 4,
                 num_heads: int = 12,
                 cnn_num_filters: int = 256,
                 cnn_filter_sizes: Tuple[int, ...] = (2, 3, 4, 5),
                 num_classes: int = 2,
                 dropout: float = 0.3):
        super(SimpleBERTCNNModel, self).__init__()
        
        self.hidden_dim = hidden_dim
        
        # 词嵌入
        self.embedding = nn.Embedding(vocab_size, hidden_dim, padding_idx=0)
        self.position_embedding = nn.PositionalEncoding(hidden_dim)
        
        # Transformer编码器层
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # CNN特征提取
        self.cnn_extractor = CNNFeatureExtractor(
            input_dim=hidden_dim,
            num_filters=cnn_num_filters,
            filter_sizes=cnn_filter_sizes,
            dropout=dropout
        )
        
        # 分类器
        cnn_output_dim = cnn_num_filters * len(cnn_filter_sizes)
        self.classifier = nn.Sequential(
            nn.Linear(cnn_output_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, 
                input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            input_ids: 输入ID (batch_size, seq_len)
            attention_mask: 注意力掩码 (batch_size, seq_len)
            
        Returns:
            logits: 分类 logits (batch_size, num_classes)
        """
        # 词嵌入
        x = self.embedding(input_ids)  # (batch_size, seq_len, hidden_dim)
        
        # 位置编码
        x = self.position_embedding(x)
        
        # Transformer编码
        if attention_mask is not None:
            # 转换为Transformer需要的mask格式
            mask = (attention_mask == 0)  # True for padding
            x = self.transformer_encoder(x, src_key_padding_mask=mask)
        else:
            x = self.transformer_encoder(x)
        
        # CNN特征提取
        cnn_features = self.cnn_extractor(x)  # (batch_size, cnn_output_dim)
        
        # 分类
        logits = self.classifier(cnn_features)
        
        return logits


class PositionalEncoding(nn.Module):
    """位置编码"""
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        # 创建位置编码矩阵
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-torch.log(torch.tensor(10000.0)) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: 输入 (batch_size, seq_len, d_model)
        """
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("BERT + CNN 模型测试")
    print("=" * 60)
    
    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n使用设备: {device}")
    
    # 测试参数
    batch_size = 4
    seq_len = 32
    hidden_dim = 768
    cnn_num_filters = 128
    cnn_filter_sizes = (2, 3, 4, 5)
    num_classes = 2
    
    print(f"\n1. 测试 CNNFeatureExtractor:")
    cnn_extractor = CNNFeatureExtractor(
        input_dim=hidden_dim,
        num_filters=cnn_num_filters,
        filter_sizes=cnn_filter_sizes
    ).to(device)
    
    x = torch.randn(batch_size, seq_len, hidden_dim).to(device)
    output = cnn_extractor(x)
    print(f"   输入形状: {x.shape}")
    print(f"   输出形状: {output.shape}")
    
    print(f"\n2. 测试 ConditionFusion (gated):")
    fusion = ConditionFusion(
        main_dim=512,
        condition_dim=256,
        output_dim=512,
        fusion_type='gated'
    ).to(device)
    
    main_feat = torch.randn(batch_size, 512).to(device)
    condition_feat = torch.randn(batch_size, 256).to(device)
    fused = fusion(main_feat, condition_feat)
    print(f"   主特征: {main_feat.shape}, 条件特征: {condition_feat.shape}")
    print(f"   融合输出: {fused.shape}")
    
    print(f"\n3. 测试 ConditionFusion (concat):")
    fusion_concat = ConditionFusion(
        main_dim=512,
        condition_dim=256,
        output_dim=512,
        fusion_type='concat'
    ).to(device)
    
    fused_concat = fusion_concat(main_feat, condition_feat)
    print(f"   融合输出: {fused_concat.shape}")
    
    print(f"\n4. 测试 SimpleBERTCNNModel:")
    simple_model = SimpleBERTCNNModel(
        vocab_size=21128,
        hidden_dim=hidden_dim,
        num_layers=4,
        num_heads=8,
        cnn_num_filters=cnn_num_filters,
        cnn_filter_sizes=cnn_filter_sizes,
        num_classes=num_classes
    ).to(device)
    
    input_ids = torch.randint(0, 21128, (batch_size, seq_len)).to(device)
    attention_mask = torch.ones(batch_size, seq_len).to(device)
    
    logits = simple_model(input_ids, attention_mask)
    print(f"   输入形状: {input_ids.shape}")
    print(f"   输出logits形状: {logits.shape}")
    
    print(f"\n5. 模型参数量:")
    print(f"   SimpleBERTCNNModel: {sum(p.numel() for p in simple_model.parameters()):,}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
