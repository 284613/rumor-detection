# -*- coding: utf-8 -*-
"""优化版谣言检测模型训练 (已修复虚高与数据泄露)"""
import os
import sys
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from collections import Counter
import numpy as np
import pandas as pd
import jieba
import random
from sklearn.metrics import classification_report  # 新增：用于详细评估

# 设置随机种子
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("\n" + "="*60)
print("        优化版谣言检测模型训练 (严格评估版)")
print("="*60)
print(f"\nGPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

# ============ 配置 =============
EPOCHS = 15
BATCH_SIZE = 32
LEARNING_RATE = 0.0005
VOCAB_SIZE = 15000
EMBED_DIM = 256
HIDDEN_DIM = 128
DROPOUT = 0.3
LOSS_WEIGHT_RUMOR = 1.0
LOSS_WEIGHT_STANCE = 0.5

def sample_2to1_rumor_real(texts, rumor_labels, stance_labels):
    """采样使谣言:真实数据为2:1比例,保持三个数组对齐"""
    paired = [(t, r, s) for t, r, s in zip(texts, rumor_labels, stance_labels)]
    rumor_pairs = [p for p in paired if p[1] == 0]
    real_pairs = [p for p in paired if p[1] == 1]
    num_rumor = len(rumor_pairs)
    num_real = len(real_pairs)
    if num_real == 0:
        return texts, rumor_labels, stance_labels
    target_real = num_real
    target_rumor = min(num_rumor, target_real * 2)
    sampled_rumor = random.sample(rumor_pairs, min(target_rumor, len(rumor_pairs)))
    sampled = sampled_rumor + real_pairs
    random.shuffle(sampled)
    if sampled:
        return zip(*sampled)
    return [], [], []

# ============ [1/6] 数据加载 =============
print("\n[1/6] 加载数据...")
raw_texts = []
raw_rumor_labels = []
raw_stance_labels =[]

# 1. weibo1_rumor
try:
    df = pd.read_csv("E:/rumor_detection/data/weibo1_rumor.tsv", sep='\t', header=None, names=['label', 'text'])
    for _, row in df.iterrows():
        text = str(row['text']).strip()
        if len(text) > 5:
            raw_texts.append(text)
            label = int(row['label'])
            raw_rumor_labels.append(0 if label == 0 else 1)  # 0=谣言, 1=真实
            raw_stance_labels.append(1)  # 中立
except Exception as e:
    print(f"  weibo1_rumor加载失败: {e}")

# 3. processed_crawled
try:
    with open("E:/rumor_detection/data/processed_crawled.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        text = item.get('content', '').strip()
        if text and len(text) > 5:
            raw_texts.append(text)
            label = item.get('label', '未分类')
            raw_rumor_labels.append(1 if label in ['辟谣', '真实'] else 0)
            stance = item.get('stance', '中立')
            stance_map = {'支持': 0, '反对': 1, '中立': 2}
            raw_stance_labels.append(stance_map.get(stance, 2))
except Exception as e:
    print(f"  processed_crawled加载失败: {e}")

# 4. 清华微博谣言数据集
try:
    with open("E:/rumor_detection/data/Chinese_Rumor_Dataset/rumors_v170613.json", 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    item = json.loads(line)
                    text = item.get('rumorText', '').strip()
                    if text and len(text) > 5:
                        raw_texts.append(text)
                        raw_rumor_labels.append(0)  # 谣言
                        raw_stance_labels.append(2)  # 中立
                except json.JSONDecodeError:
                    continue
except Exception as e:
    print(f"  清华微博谣言数据集加载失败: {e}")

# 5. augmented_qwen
try:
    with open("E:/rumor_detection/data/augmented_qwen.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        text = str(item.get('augmented', item.get('original', ''))).strip()
        label_str = item.get('label', '')
        if text and len(text) > 5 and label_str:
            raw_texts.append(text)
            raw_rumor_labels.append(1 if label_str in ['真', 'true'] else 0)
            raw_stance_labels.append(2)
except Exception as e:
    print(f"  加载augmented_qwen失败: {e}")

print(f"  合并后原始数据量: {len(raw_texts)} 条")

# 6. 清华 CED_Dataset (包含极度珍贵的 1849 条非谣言数据)
try:
    ced_base_dir = "E:/rumor_detection/data/Chinese_Rumor_Dataset/CED_Dataset"
    orig_dir = os.path.join(ced_base_dir, "original-microblog")
    rumor_dir = os.path.join(ced_base_dir, "rumor-repost")
    non_rumor_dir = os.path.join(ced_base_dir, "non-rumor-repost")

    ced_count_1 = 0 # 记录非谣言
    ced_count_0 = 0 # 记录谣言

    # 1. 先通过文件夹列表，获取谣言和非谣言的 ID 集合 (去除扩展名)
    # 因为有可能里面是文件，也有可能是子文件夹，所以统一用 split('.')[0] 提取核心ID
    rumor_ids = set([name.split('.')[0] for name in os.listdir(rumor_dir)]) if os.path.exists(rumor_dir) else set()
    non_rumor_ids = set([name.split('.')[0] for name in os.listdir(non_rumor_dir)]) if os.path.exists(non_rumor_dir) else set()

    # 2. 遍历原文文件夹，读取文本并打标签
    if os.path.exists(orig_dir):
        for filename in os.listdir(orig_dir):
            if not filename.endswith('.json'): 
                continue
            
            file_id = filename.split('.')[0]
            filepath = os.path.join(orig_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    content = json.load(f)
                    # 提取原文内容
                    text = content.get('text', '').strip()
                    
                    if text and len(text) > 5:
                        # 3. 匹配ID，判断是真实还是谣言
                        if file_id in non_rumor_ids:
                            raw_texts.append(text)
                            raw_rumor_labels.append(1)  # 1=真实/非谣言
                            raw_stance_labels.append(2) # 默认中立
                            ced_count_1 += 1
                        elif file_id in rumor_ids:
                            raw_texts.append(text)
                            raw_rumor_labels.append(0)  # 0=谣言
                            raw_stance_labels.append(2)
                            ced_count_0 += 1
                except json.JSONDecodeError:
                    continue
                    
    print(f"  CED_Dataset 加载成功: 补充真实新闻(1) {ced_count_1} 条, 补充谣言(0) {ced_count_0} 条")
except Exception as e:
    print(f"  CED_Dataset 加载失败: {e}")
# ============ 替换原来的 [2/6] =============
print("\n[2/6] 数据清洗...")
unique_texts = set()
dedup_data =[]
for t, r, s in zip(raw_texts, raw_rumor_labels, raw_stance_labels):
    if t not in unique_texts:
        unique_texts.add(t)
        dedup_data.append((t, r, s))

# 不做 1:1 删减，保留全部！
all_texts = [x[0] for x in dedup_data]
all_rumor_labels =[x[1] for x in dedup_data]
all_stance_labels = [x[2] for x in dedup_data]

num_rumors = sum(1 for r in all_rumor_labels if r == 0)
num_truths = sum(1 for r in all_rumor_labels if r == 1)
print(f"  保留所有去重数据 -> 谣言: {num_rumors}, 真实: {num_truths}")

# 2:1 谣言:真实 采样
print("\n[2.5/6] 2:1 谣言:真实 采样...")
all_texts, all_rumor_labels, all_stance_labels = sample_2to1_rumor_real(all_texts, all_rumor_labels, all_stance_labels)
sampled_rumors = sum(1 for r in all_rumor_labels if r == 0)
sampled_truths = sum(1 for r in all_rumor_labels if r == 1)
print(f"  采样后数据: {len(all_texts)} 条")
print(f"  采样后标签分布 -> 谣言: {sampled_rumors}, 真实: {sampled_truths}")
print(f"  谣言:真实 = {sampled_rumors}:{sampled_truths} = {sampled_rumors/sampled_truths:.2f}:1")

# ============ [3/6] 数据预处理与防泄露划分 =============
print("\n[3/6] 划分数据集与构建词表...")

# 1. 划分数据集 (先划分，再建词表！)
indices = np.random.permutation(len(all_texts))
train_size = int(0.85 * len(all_texts))
train_idx, val_idx = indices[:train_size], indices[train_size:]

train_texts = [all_texts[i] for i in train_idx]
val_texts = [all_texts[i] for i in val_idx]

train_r_labels = [all_rumor_labels[i] for i in train_idx]
val_r_labels = [all_rumor_labels[i] for i in val_idx]

train_s_labels = [all_stance_labels[i] for i in train_idx]
val_s_labels = [all_stance_labels[i] for i in val_idx]

# 2. 分词与构建词表 (严格限制只用训练集)
def tokenize(text):
    return list(jieba.cut(text))

word_counts = Counter()
for text in train_texts:  # 修复泄露：这里换成 train_texts
    word_counts.update(tokenize(text))

vocab = {"<PAD>": 0, "<UNK>": 1}
for word, _ in word_counts.most_common(VOCAB_SIZE - 2):
    vocab[word] = len(vocab)
print(f"  严格基于训练集构建的词汇表大小: {len(vocab)}")

def text_to_indices(text, max_len=100):
    words = tokenize(text)[:max_len]
    indices =[vocab.get(w, vocab["<UNK>"]) for w in words]
    if len(indices) < max_len:
        indices += [vocab["<PAD>"]] * (max_len - len(indices))
    return indices

class RumorDataset(Dataset):
    def __init__(self, texts, rumor_labels, stance_labels):
        self.texts = [text_to_indices(t) for t in texts]
        self.rumor_labels = rumor_labels
        self.stance_labels = stance_labels
    
    def __len__(self):
        return len(self.rumor_labels)
    
    def __getitem__(self, idx):
        return (torch.tensor(self.texts[idx]), 
                torch.tensor(self.rumor_labels[idx]),
                torch.tensor(self.stance_labels[idx]))

train_dataset = RumorDataset(train_texts, train_r_labels, train_s_labels)
val_dataset = RumorDataset(val_texts, val_r_labels, val_s_labels)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)

print(f"  训练集: {len(train_dataset)} 条 | 验证集: {len(val_dataset)} 条")

# ============ [4/6] 创建模型 (修复硬编码) =============
print("\n[4/6] 创建模型...")

class TextCNNMultiTask(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, num_rumor_classes=2, num_stance_classes=3, dropout=0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, hidden_dim, kernel_size=k) for k in [2, 3, 4, 5]
        ])
        
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.attention = nn.Linear(hidden_dim * 2, 1)
        self.dropout = nn.Dropout(dropout)
        
        # 动态计算拼接维度 (修复硬编码 Bug)
        combined_dim = hidden_dim * len(self.convs) + hidden_dim * 2
        
        self.rumor_fc = nn.Sequential(
            nn.Linear(combined_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_rumor_classes)
        )
        
        self.stance_fc = nn.Sequential(
            nn.Linear(combined_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_stance_classes)
        )
    
    def forward(self, x):
        x_emb = self.embedding(x)
        x_cnn = x_emb.permute(0, 2, 1)
        
        cnn_features =[]
        for conv in self.convs:
            c = torch.relu(conv(x_cnn))
            c = torch.max_pool1d(c, c.size(2)).squeeze(2)
            cnn_features.append(c)
        cnn_out = torch.cat(cnn_features, dim=1)
        
        gru_out, _ = self.gru(x_emb)
        attn_weights = torch.softmax(self.attention(gru_out), dim=1)
        gru_attn = torch.sum(attn_weights * gru_out, dim=1)
        
        combined = torch.cat([cnn_out, gru_attn], dim=1)
        rumor_out = self.rumor_fc(combined)
        stance_out = self.stance_fc(combined)
        
        return rumor_out, stance_out

model = TextCNNMultiTask(len(vocab), EMBED_DIM, HIDDEN_DIM, dropout=DROPOUT).to(DEVICE)
print(f"  参数量: {sum(p.numel() for p in model.parameters()):,}")

# ============ 替换原来的 [5/6] 损失函数部分 =============
# ============ [5/6] 训练与评估 =============
print("\n[5/6] 开始训练...")

# 1. 计算加权损失权重 (应对 3万谣言 vs 700真新闻 的极端不平衡)
train_rumors_cnt = sum(1 for r in train_r_labels if r == 0)
train_truths_cnt = sum(1 for r in train_r_labels if r == 1)
total_train_samples = train_rumors_cnt + train_truths_cnt

# 权重公式: 总样本数 / (2 * 该类别样本数)
weight_0 = total_train_samples / (2.0 * max(train_rumors_cnt, 1))
weight_1 = total_train_samples / (2.0 * max(train_truths_cnt, 1))
class_weights = torch.tensor([weight_0, weight_1], dtype=torch.float).to(DEVICE)

print(f"  启动加权损失惩罚! 谣言权重: {weight_0:.4f}, 真实样本权重: {weight_1:.4f}")

# 2. 定义损失函数、优化器和学习率调度器
rumor_criterion = nn.CrossEntropyLoss(weight=class_weights)
stance_criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=2, factor=0.5)

# 3. 初始化最佳记录变量（修复 NameError 报错的关键！！！）
best_rumor_acc = 0
best_epoch = 0

# 4. 开始 Epoch 循环
for epoch in range(EPOCHS):
    model.train()
    train_loss = 0
    
    for texts, r_labels, s_labels in train_loader:
        texts, r_labels, s_labels = texts.to(DEVICE), r_labels.to(DEVICE), s_labels.to(DEVICE)
        
        optimizer.zero_grad()
        rumor_out, stance_out = model(texts)
        
        # 计算带权重的损失
        loss = (LOSS_WEIGHT_RUMOR * rumor_criterion(rumor_out, r_labels) + 
                LOSS_WEIGHT_STANCE * stance_criterion(stance_out, s_labels))
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        train_loss += loss.item()
    
    # === 验证与详细评估 ===
    model.eval()
    val_rumor_targets = []
    val_rumor_preds =[]
    
    with torch.no_grad():
        for texts, r_labels, s_labels in val_loader:
            texts, r_labels, s_labels = texts.to(DEVICE), r_labels.to(DEVICE), s_labels.to(DEVICE)
            rumor_out, stance_out = model(texts)
            
            _, rumor_pred = torch.max(rumor_out, 1)
            val_rumor_targets.extend(r_labels.cpu().numpy())
            val_rumor_preds.extend(rumor_pred.cpu().numpy())
    
    # 打印详细指标
    print(f"\n[{epoch+1}/{EPOCHS}] Train Loss: {train_loss/len(train_loader):.4f}")
    
    # 这里处理可能存在的类别确实问题(防止某一批次全是同一个标签报错)
    labels_present = list(set(val_rumor_targets + val_rumor_preds))
    target_names = ["谣言(0)", "真实(1)"]
    report = classification_report(val_rumor_targets, val_rumor_preds, 
                                   labels=[0, 1], target_names=target_names, output_dict=True, zero_division=0)
    
    acc = report['accuracy']
    f1_rumor = report['谣言(0)']['f1-score']
    f1_truth = report['真实(1)']['f1-score']
    
    print(f"  Acc: {acc*100:.2f}% | 谣言 F1: {f1_rumor:.4f} | 真实新闻 F1: {f1_truth:.4f}")
    
    scheduler.step(acc)
    
    # 保存最佳模型
    if acc > best_rumor_acc:
        best_rumor_acc = acc
        best_epoch = epoch + 1
        os.makedirs("E:/rumor_detection/models", exist_ok=True)
        torch.save({
            'model_state_dict': model.state_dict(),
            'accuracy': best_rumor_acc,
            'model_type': 'CNN_GRU_Attention'
        }, "E:/rumor_detection/models/CNN_GRU_Attention.pth")
        print(f"  🌟 已保存最佳模型 (Acc: {acc*100:.2f}%)")
# ============ [6/6] 结果总结 =============
print("\n" + "="*60)
print(f"训练结束! 最佳模型出现在第 {best_epoch} 轮")
print(f"真实的(挤水分后)验证集准确率: {best_rumor_acc*100:.2f}%")
print("="*60)

# 读取详细分类报告输出在控制台
model.load_state_dict(torch.load("E:/rumor_detection/models/CNN_GRU_Attention.pth")['model_state_dict'])
model.eval()
final_targets, final_preds = [],[]
with torch.no_grad():
    for texts, r_labels, _ in val_loader:
        texts = texts.to(DEVICE)
        rumor_out, _ = model(texts)
        _, rumor_pred = torch.max(rumor_out, 1)
        final_targets.extend(r_labels.cpu().numpy())
        final_preds.extend(rumor_pred.cpu().numpy())

print("\n=== 最终最佳模型详细评估报告 ===")
print(classification_report(final_targets, final_preds, target_names=["谣言(0)", "真实(1)"]))