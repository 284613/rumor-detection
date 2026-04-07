"""
谣言检测模型评估脚本
加载训练好的模型并在验证集上评估
"""

import os
import json
import re
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from collections import Counter
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

# 配置参数
class Config:
    DATA_DIR = r"E:\rumor_detection\data"
    VAL_DATA = os.path.join(DATA_DIR, "augmented_qwen.json")
    MODEL_PATH = r"E:\rumor_detection\models\best_model.pth"
    MAX_LEN = 128
    BATCH_SIZE = 32
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def clean_text(text):
    """清洗文本"""
    if not text:
        return ""
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class Vocabulary:
    """词汇表"""
    def __init__(self, word2idx, idx2word):
        self.word2idx = word2idx
        self.idx2word = idx2word
        self.pad_idx = 0
        self.unk_idx = 1
    
    def text_to_indices(self, text, max_len):
        """将文本转换为索引"""
        words = text.lower().split()
        indices = [self.word2idx.get(word, self.unk_idx) for word in words]
        
        if len(indices) >= max_len:
            indices = indices[:max_len]
        else:
            indices = indices + [self.pad_idx] * (max_len - len(indices))
        
        return indices


class RumorDataset(Dataset):
    """谣言检测数据集"""
    def __init__(self, texts, labels, vocab, max_len):
        self.texts = texts
        self.labels = labels
        self.vocab = vocab
        self.max_len = max_len
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        indices = self.vocab.text_to_indices(text, self.max_len)
        
        return torch.tensor(indices, dtype=torch.long), torch.tensor(label, dtype=torch.long)


class TextCNN(nn.Module):
    """TextCNN模型"""
    def __init__(self, vocab_size, embed_dim, num_filters, filter_sizes, num_classes, dropout=0.5):
        super(TextCNN, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, num_filters, fs) for fs in filter_sizes
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(num_filters * len(filter_sizes), num_classes)
    
    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)
        
        conv_outputs = []
        for conv in self.convs:
            c = F.relu(conv(x))
            c = F.max_pool1d(c, c.size(2)).squeeze(2)
            conv_outputs.append(c)
        
        x = torch.cat(conv_outputs, dim=1)
        x = self.dropout(x)
        x = self.fc(x)
        
        return x


def load_chinese_data(json_path):
    """加载中文验证数据"""
    texts = []
    labels = []
    
    if not os.path.exists(json_path):
        return texts, labels
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    LABEL_MAP = {
        '真': 0, '假': 1, 'true': 0, 'false': 1,
    }
    
    for item in data:
        text = item.get('augmented', item.get('original', ''))
        label_str = item.get('label', '')
        
        if text and label_str in LABEL_MAP:
            text = clean_text(text)
            if text:
                texts.append(text)
                labels.append(LABEL_MAP[label_str])
    
    return texts, labels


def load_model(model_path, device):
    """加载模型"""
    checkpoint = torch.load(model_path, map_location=device)
    
    vocab = Vocabulary(
        word2idx=checkpoint['vocab'].word2idx,
        idx2word=checkpoint['vocab'].idx2word
    )
    
    config = checkpoint['config']
    
    model = TextCNN(
        vocab_size=config['vocab_size'],
        embed_dim=config['embed_dim'],
        num_filters=config['num_filters'],
        filter_sizes=config['filter_sizes'],
        num_classes=config['num_classes'],
        dropout=config['dropout']
    )
    
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    return model, vocab


def evaluate(model, dataloader, device):
    """评估模型"""
    model.eval()
    
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for texts, labels in dataloader:
            texts = texts.to(device)
            
            outputs = model(texts)
            probs = F.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs, 1)
            
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs[:, 1].cpu().numpy())  # 谣言的概率
    
    return np.array(all_preds), np.array(all_labels), np.array(all_probs)


def print_evaluation_report(y_true, y_pred, y_prob):
    """打印评估报告"""
    print("\n" + "=" * 60)
    print("谣言检测模型评估报告")
    print("=" * 60)
    
    # 总体准确率
    accuracy = accuracy_score(y_true, y_pred)
    print(f"\n【总体准确率】: {accuracy:.4f} ({accuracy*100:.2f}%)")
    
    # 分类报告
    print("\n【详细分类报告】:")
    target_names = ['非谣言 (0)', '谣言 (1)']
    report = classification_report(y_true, y_pred, target_names=target_names, digits=4)
    print(report)
    
    # 混淆矩阵
    print("\n【混淆矩阵】:")
    cm = confusion_matrix(y_true, y_pred)
    print(f"              预测非谣言  预测谣言")
    print(f"实际非谣言      {cm[0][0]:5d}     {cm[0][1]:5d}")
    print(f"实际谣言        {cm[1][0]:5d}     {cm[1][1]:5d}")
    
    # 精确率、召回率、F1
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')
    print(f"\n【加权平均指标】:")
    print(f"  精确率 (Precision): {precision:.4f}")
    print(f"  召回率 (Recall): {recall:.4f}")
    print(f"  F1分数 (F1-Score): {f1:.4f}")
    
    # 各类指标
    print("\n【各类别详细指标】:")
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, average=None)
    classes = ['非谣言', '谣言']
    for i, cls in enumerate(classes):
        print(f"  {cls}:")
        print(f"    精确率: {precision[i]:.4f}")
        print(f"    召回率: {recall[i]:.4f}")
        print(f"    F1分数: {f1[i]:.4f}")
        print(f"    样本数: {support[i]}")
    
    print("\n" + "=" * 60)
    
    return {
        'accuracy': accuracy,
        'precision': precision.tolist(),
        'recall': recall.tolist(),
        'f1': f1.tolist(),
        'confusion_matrix': cm.tolist()
    }


def main():
    print("=" * 60)
    print("谣言检测模型评估")
    print("=" * 60)
    
    config = Config()
    
    # 加载验证数据
    print("\n[1/3] 加载验证数据...")
    val_texts, val_labels = load_chinese_data(config.VAL_DATA)
    print(f"  验证数据: {len(val_texts)} 条")
    
    # 统计标签分布
    label_counts = Counter(val_labels)
    print(f"  标签分布: 谣言={label_counts[1]}, 非谣言={label_counts[0]}")
    
    # 加载模型
    print("\n[2/3] 加载模型...")
    model, vocab = load_model(config.MODEL_PATH, config.DEVICE)
    print(f"  模型设备: {config.DEVICE}")
    print(f"  词汇表大小: {len(vocab.word2idx)}")
    
    # 创建数据加载器
    val_dataset = RumorDataset(val_texts, val_labels, vocab, config.MAX_LEN)
    val_loader = DataLoader(val_dataset, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0)
    
    # 评估
    print("\n[3/3] 评估模型...")
    y_pred, y_true, y_prob = evaluate(model, val_loader, config.DEVICE)
    
    # 打印评估报告
    results = print_evaluation_report(y_true, y_pred, y_prob)
    
    # 保存评估结果
    results_path = os.path.join(os.path.dirname(config.MODEL_PATH), 'evaluation_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n评估结果已保存至: {results_path}")
    
    print("\n评估完成！")


if __name__ == "__main__":
    main()
