# -*- coding: utf-8 -*-
"""
社交媒体谣言检测模型训练 (TextCNN 严格评估版)
使用 TextCNN 进行文本分类
支持中文 (jieba分词) 和 多源数据加载
"""

import os
import sys
import json
import time
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from collections import Counter
import jieba
import random
from sklearn.metrics import classification_report, confusion_matrix

# 设置随机种子保证可复现
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

# ============ 配置 =============
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EPOCHS = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001
EMBEDDING_DIM = 256
HIDDEN_DIM = 256
MAX_VOCAB_SIZE = 15000
MAX_SEQ_LEN = 128

print("\n" + "="*60)
print("        社交媒体恶意谣言识别模型训练 (TextCNN)")
print("="*60)
print(f"设备: {DEVICE}")

# ============[1/6] 数据加载 =============
print("\n[1/6] 加载数据集...")

raw_texts = []
raw_labels = []

# 1. 加载 weibo1_rumor.tsv
try:
    path = "E:/rumor_detection/data/weibo1_rumor.tsv"
    if os.path.exists(path):
        df = pd.read_csv(path, sep='\t', header=None, names=['label', 'text'])
        for _, row in df.iterrows():
            text = str(row['text']).strip()
            if len(text) > 5:
                raw_texts.append(text)
                raw_labels.append(1 if int(row['label']) == 1 else 0)
        print(f"  已加载 weibo1: {len(df)} 条")
except Exception as e:
    print(f"  加载weibo1失败: {e}")

# 2. 加载 processed_crawled.json
try:
    path = "E:/rumor_detection/data/processed_crawled.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            text = item.get('content', '').strip()
            if text and len(text) > 5:
                raw_texts.append(text)
                label = item.get('label', '未分类')
                # 统一标签: 1=谣言, 0=真实
                raw_labels.append(1 if label in ['辟谣', '真实'] else 0)
        print(f"  已加载 processed_crawled: {len(data)} 条")
except Exception as e:
    print(f"  加载processed_crawled失败: {e}")

if not raw_texts:
    print("错误: 未找到任何训练数据，请检查路径。")
    sys.exit(1)

# ============[2/6] 数据预处理 =============
print("\n[2/6] 文本分词与词汇表构建...")

def tokenize(text):
    return list(jieba.cut(text))

# 构建词汇表
word_counts = Counter()
tokenized_texts = []
for text in raw_texts:
    tokens = tokenize(text)
    tokenized_texts.append(tokens)
    word_counts.update(tokens)

vocab = {"<PAD>": 0, "<UNK>": 1}
for word, _ in word_counts.most_common(MAX_VOCAB_SIZE - 2):
    vocab[word] = len(vocab)

print(f"  词汇表大小: {len(vocab)}")

# ============[3/6] 数据集定义 =============

class RumorDataset(Dataset):
    def __init__(self, tokenized_texts, labels, vocab, max_len):
        self.data = []
        for tokens, label in zip(tokenized_texts, labels):
            indices = [vocab.get(t, vocab["<UNK>"]) for t in tokens[:max_len]]
            if len(indices) < max_len:
                indices += [vocab["<PAD>"]] * (max_len - len(indices))
            self.data.append((torch.tensor(indices), torch.tensor(label)))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

# 划分训练集和验证集
data_size = len(raw_texts)
indices = list(range(data_size))
random.shuffle(indices)
split = int(data_size * 0.8)

train_indices = indices[:split]
val_indices = indices[split:]

train_dataset = RumorDataset([tokenized_texts[i] for i in train_indices], 
                             [raw_labels[i] for i in train_indices], vocab, MAX_SEQ_LEN)
val_dataset = RumorDataset([tokenized_texts[i] for i in val_indices], 
                           [raw_labels[i] for i in val_indices], vocab, MAX_SEQ_LEN)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)

# ============[4/6] 模型定义 =============

class TextCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_classes=2):
        super(TextCNN, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, hidden_dim, kernel_size=k)
            for k in [2, 3, 4, 5]
        ])
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(hidden_dim * 4, num_classes)

    def forward(self, x):
        # x: [batch, seq_len]
        x = self.embedding(x) # [batch, seq_len, embed]
        x = x.permute(0, 2, 1) # [batch, embed, seq_len]
        
        conv_outputs = []
        for conv in self.convs:
            c = torch.relu(conv(x))
            c = torch.max_pool1d(c, c.size(2)).squeeze(2)
            conv_outputs.append(c)
        
        x = torch.cat(conv_outputs, dim=1)
        x = self.dropout(x)
        x = self.fc(x)
        return x

model = TextCNN(len(vocab), EMBEDDING_DIM, HIDDEN_DIM).to(DEVICE)
optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
criterion = nn.CrossEntropyLoss()

# ============[5/6] 训练循环 =============
print("\n[5/6] 开始训练...")

best_acc = 0
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for x, y in train_loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(x)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    
    # 验证
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in val_loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            outputs = model(x)
            _, predicted = torch.max(outputs.data, 1)
            total += y.size(0)
            correct += (predicted == y).sum().item()
    
    acc = correct / total
    print(f"Epoch [{epoch+1}/{EPOCHS}], Loss: {total_loss/len(train_loader):.4f}, Val Acc: {acc:.4f}")
    
    if acc > best_acc:
        best_acc = acc
        torch.save(model.state_dict(), "E:/rumor_detection/models/TextCNN_Restored.pth")

# ============[6/6] 最终评估 =============
print("\n[6/6] 详细评估报告:")
model.eval()
all_preds = []
all_labels = []
with torch.no_grad():
    for x, y in val_loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        outputs = model(x)
        _, predicted = torch.max(outputs.data, 1)
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(y.cpu().numpy())

print(classification_report(all_labels, all_preds, target_names=['真实', '谣言']))
print(f"最佳模型已保存至: E:/rumor_detection/models/TextCNN_Restored.pth")
