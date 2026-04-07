# -*- coding: utf-8 -*-
"""
多模型测试脚本
测试 TextCNN, CNN+GRU+Attention, BERT 三个模型的性能
"""
import os
import json
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
import jieba
from collections import Counter

# ============ 配置 ============
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 32

print("\n" + "="*60)
print("           多模型测试脚本")
print("="*60)
print(f"设备: {DEVICE}")

# ============ 加载测试集 ============
print("\n[1] 加载测试数据...")

TEST_DATA_PATH = "E:/rumor_detection/data/test_set.json"

# 如果没有独立测试集，从processed_crawled加载
if os.path.exists(TEST_DATA_PATH):
    with open(TEST_DATA_PATH, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    print(f"  从 {TEST_DATA_PATH} 加载")
else:
    # 使用processed_crawled作为测试集
    with open("E:/rumor_detection/data/processed_crawled.json", 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    print(f"  从 processed_crawled.json 加载")

test_texts = [item.get('content', item.get('original', '')) for item in test_data]
test_labels = []
for item in test_data:
    label = item.get('label', '辟谣')
    if label in ['辟谣', '真实', '真', 'true']:
        test_labels.append(1)
    else:
        test_labels.append(0)

print(f"  测试样本数: {len(test_texts)}")

# ============ 数据预处理 ============
def tokenize(text):
    return list(jieba.cut(text))

MAX_SEQ_LEN = 128
MAX_VOCAB_SIZE = 15000

# 构建词汇表
print("\n[2] 构建词汇表...")
all_texts_for_vocab = test_texts  # 用测试集构建词汇表
word_counts = Counter()
for text in all_texts_for_vocab:
    words = tokenize(text)
    word_counts.update(words)

vocab = {"<PAD>": 0, "<UNK>": 1}
for word, _ in word_counts.most_common(MAX_VOCAB_SIZE - 2):
    vocab[word] = len(vocab)
print(f"  词汇表大小: {len(vocab)}")

def text_to_indices(text, max_len=MAX_SEQ_LEN):
    words = tokenize(text)[:max_len]
    indices = [vocab.get(w, vocab["<UNK>"]) for w in words]
    if len(indices) < max_len:
        indices += [vocab["<PAD>"]] * (max_len - len(indices))
    return indices

class RumorDataset(Dataset):
    def __init__(self, texts, labels):
        self.texts = [text_to_indices(t) for t in texts]
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return torch.tensor(self.texts[idx]), torch.tensor(self.labels[idx])

test_dataset = RumorDataset(test_texts, test_labels)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

# ============ 定义模型 ============
import torch.nn as nn

# TextCNN模型
class TextCNN(nn.Module):
    def __init__(self, vocab_size, embedding_dim=256, hidden_dim=256, num_classes=2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embedding_dim, hidden_dim, kernel_size=k) for k in [2, 3, 4, 5]
        ])
        self.dropout = nn.Dropout(0.5)
        self.fc = nn.Linear(hidden_dim * 4, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)
        conv_outputs = []
        for conv in self.convs:
            c = torch.relu(conv(x))
            c = torch.max_pool1d(c, c.size(2)).squeeze(2)
            conv_outputs.append(c)
        x = torch.cat(conv_outputs, dim=1)
        x = self.dropout(x)
        x = self.fc(x)
        return x

# CNN+GRU+Attention模型
class CNN_GRU_Attention(nn.Module):
    def __init__(self, vocab_size, embed_dim=256, hidden_dim=128, num_classes=2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, hidden_dim, kernel_size=k) for k in [2, 3, 4, 5]
        ])
        self.gru = nn.GRU(hidden_dim * 4, hidden_dim, bidirectional=True, batch_first=True)
        self.attention = nn.Linear(hidden_dim * 2, 1)
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)
        conv_outputs = []
        for conv in self.convs:
            c = torch.relu(conv(x))
            c = torch.max_pool1d(c, c.size(2)).squeeze(2)
            conv_outputs.append(c)
        x = torch.cat(conv_outputs, dim=1)
        x = x.unsqueeze(1)
        gru_out, _ = self.gru(x)
        attn_weights = torch.softmax(self.attention(gru_out), dim=1)
        attended = torch.sum(attn_weights * gru_out, dim=1)
        x = self.dropout(attended)
        x = self.fc(x)
        return x

# ============ 测试函数 ============
def test_model(model, test_loader, device):
    model.eval()
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for texts, labels in test_loader:
            texts, labels = texts.to(device), labels.to(device)
            outputs = model(texts)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    accuracy = correct / total
    return accuracy, all_preds, all_labels

# ============ 加载并测试模型 ============
models_to_test = [
    ("TextCNN", "E:/rumor_detection/models/TextCNN.pth"),
    ("CNN+GRU+Attention", "E:/rumor_detection/models/CNN_GRU_Attention.pth"),
    ("BERT_MultiTask", "E:/rumor_detection/models/BERT_MultiTask.pth"),
]

print("\n[3] 测试各模型...")
print("="*60)

results = []
for model_name, model_path in models_to_test:
    print(f"\n测试 {model_name}...")

    if not os.path.exists(model_path):
        print(f"  模型文件不存在: {model_path}")
        continue

    try:
        checkpoint = torch.load(model_path, map_location=DEVICE, weights_only=False)
        print(f"  加载模型: {model_name}")

        if model_name == "TextCNN":
            model = TextCNN(len(vocab)).to(DEVICE)
            model.load_state_dict(checkpoint['model_state_dict'])
        elif model_name == "CNN+GRU+Attention":
            model = CNN_GRU_Attention(len(vocab)).to(DEVICE)
            model.load_state_dict(checkpoint['model_state_dict'])
        elif model_name == "BERT_MultiTask":
            # BERT模型加载较复杂
            print("  BERT模型需要特殊加载，跳过")
            continue

        acc, preds, labels = test_model(model, test_loader, DEVICE)
        print(f"  准确率: {acc*100:.2f}%")
        results.append((model_name, acc))

    except Exception as e:
        print(f"  测试失败: {e}")

# ============ 结果对比 ============
print("\n" + "="*60)
print("           模型性能对比")
print("="*60)
print(f"{'模型':<25} {'准确率':<10}")
print("-"*60)
for name, acc in sorted(results, key=lambda x: x[1], reverse=True):
    print(f"{name:<25} {acc*100:.2f}%")
print("="*60)
