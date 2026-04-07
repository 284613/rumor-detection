# -*- coding: utf-8 -*-
"""
先进谣言检测模型训练脚本 (严格评估与抗不平衡版)
支持：
- 多任务学习（谣言分类 + 立场检测）
- 传播树特征输入
- BERT + CNN模型
- 更大的中文预训练模型
"""

import os
os.environ['CUDA_LAUNCH_BLOCKING'] = "1"
os.environ['TORCH_CUDA_ALLOC_CONF'] = "max_split_size_mb:128"
import sys
import json
import re
import random
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from collections import Counter
from typing import List, Tuple, Dict, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report  # [新增] 用于输出真实检测能力 F1

# Fix Windows GBK encoding for stdout
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入模型 (假设你的模型文件已存在)
from models.propagation_tree import MultiRelationPropagationTree, SimplePropagationEncoder
from models.bert_cnn import BERTCNNModel, SimpleBERTCNNModel, ConditionFusion
from models.multi_task import MultiTaskModel, SimpleMultiTaskModel, MultiTaskLoss, MultiTaskTrainer

# 设置随机种子保证可复现
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

# ==================== 配置 ====================

class Config:
    """训练配置"""
    DATA_DIR = r"E:\rumor_detection\data"
    MODEL_DIR = r"E:\rumor_detection\models"
    MODEL_PATH = os.path.join(MODEL_DIR, "BERT_MultiTask.pth")

    MODEL_TYPE = "bert"
    BERT_MODEL = r"E:\rumor_detection\models\bert_base_chinese"
    
    MAX_LEN = 128
    EMBED_DIM = 256
    HIDDEN_DIM = 256
    DROPOUT = 0.3
    BATCH_SIZE = 4
    EPOCHS = 8
    LEARNING_RATE = 1e-5
    
    USE_MULTI_TASK = True
    TASK_WEIGHTS = (1.0, 0.8)
    LOSS_TYPE = "uncertainty"
    
    USE_PROPAGATION_TREE = True
    PROPAGATION_DIM = 256
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# ==================== 数据处理 ====================

RUMOR_LABEL_MAP = {
    'true': 0, 'false': 1, 'unverified': 0, 'non-rumor': 0,
    'rumours': 1, 'non-rumours': 0,
    '真': 0, '假': 1,
}

STANCE_LABEL_MAP = {
    'support': 0, 'supporting': 0,
    'deny': 1, 'denying': 1,
    'neutral': 2, 'unverified': 2,
    '中立': 2, '支持': 0, '反对': 1,
}

def clean_text(text: str) -> str:
    """清洗文本"""
    if not text: return ""
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

class Vocabulary:
    """词汇表"""
    def __init__(self, max_vocab_size=30000):
        self.max_vocab_size = max_vocab_size
        self.word2idx = {'<PAD>': 0, '<UNK>': 1}
        self.idx2word = {0: '<PAD>', 1: '<UNK>'}
        self.word_count = Counter()
    
    def build_vocab(self, texts: List[str]):
        for text in texts:
            self.word_count.update(text.lower().split())
        for word, _ in self.word_count.most_common(self.max_vocab_size - 2):
            idx = len(self.word2idx)
            self.word2idx[word] = idx
            self.idx2word[idx] = word
    
    def encode(self, text: str, max_len: int) -> List[int]:
        words = text.lower().split()
        indices = [self.word2idx.get(w, 1) for w in words][:max_len]
        return indices + [0] * (max_len - len(indices))


class RumorDataset(Dataset):
    """谣言检测数据集"""
    def __init__(self, texts, labels, stance_labels=None, vocab=None, max_len=128, tokenizer=None):
        self.texts = texts
        self.labels = labels
        self.stance_labels = stance_labels
        self.vocab = vocab
        self.max_len = max_len
        self.tokenizer = tokenizer

        # 预计算所有tokenized数据，避免在__getitem__中重复tokenize
        print(f"    预计算tokenization...")
        self.input_ids_list = []
        self.attention_mask_list = []
        for i, text in enumerate(texts):
            if tokenizer:
                encoded = tokenizer(
                    text,
                    padding='max_length',
                    truncation=True,
                    max_length=max_len,
                    return_tensors='pt'
                )
                self.input_ids_list.append(encoded['input_ids'].squeeze(0))
                self.attention_mask_list.append(encoded['attention_mask'].squeeze(0))
            elif vocab:
                enc = vocab.encode(text, max_len)
                self.input_ids_list.append(torch.tensor(enc, dtype=torch.long))
                self.attention_mask_list.append(torch.tensor([1 if i != 0 else 0 for i in enc], dtype=torch.long))
            else:
                enc = [ord(c) % 1000 for c in text[:max_len]]
                enc += [0] * (max_len - len(enc))
                self.input_ids_list.append(torch.tensor(enc, dtype=torch.long))
                self.attention_mask_list.append(torch.tensor([1 if i != 0 else 0 for i in enc], dtype=torch.long))
            if (i + 1) % 2000 == 0:
                print(f"    已处理 {i+1}/{len(texts)} 条")
        print(f"    Tokenization完成")

    def __len__(self): return len(self.texts)

    def __getitem__(self, idx):
        res = {
            'input_ids': self.input_ids_list[idx],
            'attention_mask': self.attention_mask_list[idx],
            'rumor_labels': torch.tensor(self.labels[idx], dtype=torch.long),
        }
        if self.stance_labels is not None:
            res['stance_labels'] = torch.tensor(self.stance_labels[idx], dtype=torch.long)
        return res


def load_all_chinese_data() -> Tuple[List[str], List[int], List[int]]:
    """[增强版] 加载所有中文数据源并加入 CED_Dataset"""
    raw_texts, raw_labels, raw_stances = [], [],[]

    # 1. weibo1_rumor
    try:
        df = pd.read_csv(r"E:\rumor_detection\data\weibo1_rumor.tsv", sep='\t', header=None)
        for _, row in df.iterrows():
            if len(str(row[1])) > 5:
                raw_texts.append(clean_text(str(row[1])))
                raw_labels.append(0 if int(row[0]) == 0 else 1)
                raw_stances.append(2)
    except: pass

    # 2. processed_crawled
    try:
        with open(r"E:\rumor_detection\data\processed_crawled.json", 'r', encoding='utf-8') as f:
            for item in json.load(f):
                t = item.get('content', '')
                if len(t) > 5:
                    raw_texts.append(clean_text(t))
                    raw_labels.append(1 if item.get('label') in ['辟谣', '真实'] else 0)
                    raw_stances.append(STANCE_LABEL_MAP.get(item.get('stance'), 2))
    except: pass

    # 3. 清华微博谣言数据集 (~3万条谣言)
    try:
        with open(r"E:\rumor_detection\data\Chinese_Rumor_Dataset\rumors_v170613.json", 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        t = json.loads(line).get('rumorText', '')
                        if len(t) > 5:
                            raw_texts.append(clean_text(t))
                            raw_labels.append(0)
                            raw_stances.append(2)
                    except: pass
    except: pass

    # 4. [关键增强] CED_Dataset 非谣言数据补充
    try:
        ced_base = r"E:\rumor_detection\data\Chinese_Rumor_Dataset\CED_Dataset"
        orig_dir = os.path.join(ced_base, "original-microblog")
        non_rumor_ids = set([n.split('.')[0] for n in os.listdir(os.path.join(ced_base, "non-rumor-repost"))]) if os.path.exists(os.path.join(ced_base, "non-rumor-repost")) else set()
        rumor_ids = set([n.split('.')[0] for n in os.listdir(os.path.join(ced_base, "rumor-repost"))]) if os.path.exists(os.path.join(ced_base, "rumor-repost")) else set()
        
        if os.path.exists(orig_dir):
            for filename in os.listdir(orig_dir):
                if not filename.endswith('.json'): continue
                fid = filename.split('.')[0]
                with open(os.path.join(orig_dir, filename), 'r', encoding='utf-8') as f:
                    t = json.load(f).get('text', '')
                    if len(t) > 5:
                        if fid in non_rumor_ids:
                            raw_texts.append(clean_text(t)); raw_labels.append(1); raw_stances.append(2)
                        elif fid in rumor_ids:
                            raw_texts.append(clean_text(t)); raw_labels.append(0); raw_stances.append(2)
    except: pass

    #[核心修复] 文本去重
    unique_texts = set()
    texts, labels, stances = [],[],[]
    for t, l, s in zip(raw_texts, raw_labels, raw_stances):
        if t not in unique_texts:
            unique_texts.add(t)
            texts.append(t)
            labels.append(l)
            stances.append(s)

    return texts, labels, stances


def sample_2to1_rumor_real(texts, labels, stances):
    """采样使谣言:真实数据为2:1比例,保持三个数组对齐"""
    paired = [(t, l, s) for t, l, s in zip(texts, labels, stances)]
    rumor_pairs = [p for p in paired if p[1] == 0]
    real_pairs = [p for p in paired if p[1] == 1]
    num_rumor = len(rumor_pairs)
    num_real = len(real_pairs)
    if num_real == 0:
        return texts, labels, stances
    target_real = num_real
    target_rumor = min(num_rumor, target_real * 2)
    sampled_rumor = random.sample(rumor_pairs, min(target_rumor, len(rumor_pairs)))
    sampled = sampled_rumor + real_pairs
    random.shuffle(sampled)
    if sampled:
        ts, ls, ss = zip(*sampled)
        return list(ts), list(ls), list(ss)
    return texts, labels, stances

# ==================== 训练与评估函数 (引入加权损失) ====================

def train_multi_task(model, dataloader, optimizer, device, task_weights, class_weights):
    """多任务训练 (带类别加权)"""
    model.train()
    # 谣言分类加入类别权重抵抗不平衡
    criterion_rumor = nn.CrossEntropyLoss(weight=class_weights)
    criterion_stance = nn.CrossEntropyLoss()

    total_loss = 0
    rumor_correct, stance_correct, total = 0, 0, 0

    # 禁用cuDNN非确定性操作，避免cuBLAS失败
    torch.backends.cudnn.enabled = False

    for batch in dataloader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch.get('attention_mask', None)
        if attention_mask is not None:
            attention_mask = attention_mask.to(device)
        rumor_labels = batch['rumor_labels'].to(device)
        stance_labels = batch['stance_labels'].to(device)

        outputs = model(input_ids, attention_mask, task='both')

        # 计算损失
        loss_rumor = criterion_rumor(outputs['rumor_logits'], rumor_labels)
        loss_stance = criterion_stance(outputs['stance_logits'], stance_labels)

        # 检查NaN
        if torch.isnan(loss_rumor) or torch.isnan(loss_stance):
            print(f"  [警告] 检测到NaN损失，跳过此batch | loss_rumor={loss_rumor.item():.4f}, loss_stance={loss_stance.item():.4f}")
            print(f"    rumor_logits min={outputs['rumor_logits'].min():.4f}, max={outputs['rumor_logits'].max():.4f}")
            print(f"    stance_logits min={outputs['stance_logits'].min():.4f}, max={outputs['stance_logits'].max():.4f}")
            optimizer.zero_grad()
            continue

        loss = task_weights[0] * loss_rumor + task_weights[1] * loss_stance

        optimizer.zero_grad()
        loss.backward()

        # 检查梯度NaN
        has_nan_grad = False
        for name, param in model.named_parameters():
            if param.grad is not None and torch.isnan(param.grad).any():
                print(f"  [警告] 参数 {name} 的梯度包含NaN，跳过此batch")
                has_nan_grad = True
                break

        if has_nan_grad:
            continue

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        total_loss += loss.item()
        
        rumor_preds = torch.argmax(outputs['rumor_logits'], dim=1)
        stance_preds = torch.argmax(outputs['stance_logits'], dim=1)
        
        rumor_correct += (rumor_preds == rumor_labels).sum().item()
        stance_correct += (stance_preds == stance_labels).sum().item()
        total += rumor_labels.size(0)
    
    return {'loss': total_loss / len(dataloader), 'rumor_acc': rumor_correct / total}

def evaluate_multi_task(model, dataloader, device):
    """多任务评估"""
    model.eval()
    all_rumor_preds, all_rumor_labels = [],[]

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch.get('attention_mask', None)
            if attention_mask is not None:
                attention_mask = attention_mask.to(device)
            rumor_labels = batch['rumor_labels'].to(device)

            outputs = model(input_ids, attention_mask, task='rumor')
            rumor_preds = torch.argmax(outputs['rumor_logits'], dim=1)
            
            all_rumor_preds.extend(rumor_preds.cpu().numpy())
            all_rumor_labels.extend(rumor_labels.cpu().numpy())
    
    # 借用 sklearn 计算 F1
    report = classification_report(all_rumor_labels, all_rumor_preds, labels=[0, 1], target_names=["谣言(0)", "真实(1)"], output_dict=True, zero_division=0)

    return {
        'rumor_acc': report['accuracy'],
        'rumor_f1_0': report.get('谣言(0)', {}).get('f1-score', 0.0),
        'rumor_f1_1': report.get('真实(1)', {}).get('f1-score', 0.0),
        'report_str': classification_report(all_rumor_labels, all_rumor_preds, labels=[0, 1], target_names=["谣言(0)", "真实(1)"], zero_division=0)
    }

# ==================== 主函数 ====================

def main(args):
    print("=" * 60)
    print("🚀 先进谣言检测模型训练 (多任务+BERT版)")
    print("=" * 60)
    
    config = Config()
    config.MODEL_TYPE = args.model_type
    device = config.DEVICE
    os.makedirs(config.MODEL_DIR, exist_ok=True)

    # 清理GPU缓存
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    # ========== [1] 加载与处理数据 ==========
    print("\n[1/6] 加载并清洗数据...")
    texts, labels, stances = load_all_chinese_data()
    
    num_0 = sum(1 for l in labels if l == 0)
    num_1 = sum(1 for l in labels if l == 1)
    print(f"  清洗去重后总计: {len(texts)} 条")
    print(f"  原始标签分布: 谣言(0): {num_0} | 真实新闻(1): {num_1}")

    # 2:1 谣言:真实 采样
    print("\n[1.5/6] 2:1 谣言:真实 采样...")
    texts, labels, stances = sample_2to1_rumor_real(texts, labels, stances)
    sampled_0 = sum(1 for l in labels if l == 0)
    sampled_1 = sum(1 for l in labels if l == 1)
    print(f"  采样后数据: {len(texts)} 条")
    print(f"  采样后标签分布: 谣言(0): {sampled_0} | 真实新闻(1): {sampled_1}")
    print(f"  谣言:真实 = {sampled_0}:{sampled_1} = {sampled_0/sampled_1:.2f}:1")

    train_texts, val_texts, train_labels, val_labels, train_stances, val_stances = train_test_split(
        texts, labels, stances, test_size=0.15, random_state=SEED, stratify=labels
    )
    print(f"  训练集: {len(train_texts)} | 验证集: {len(val_texts)}")
    
    # ========== [2] 构建词汇表 ==========
    print("\n[2/6] 构建词汇表...")
    vocab = None
    tokenizer = None
    if config.MODEL_TYPE == 'simple':
        vocab = Vocabulary(config.MAX_LEN * 2)
        vocab.build_vocab(train_texts)
        print(f"  安全词汇表大小: {len(vocab.word2idx)}")
    else:
        from transformers import BertTokenizer
        tokenizer = BertTokenizer.from_pretrained(config.BERT_MODEL)
        print(f"  使用 BERT Tokenizer (vocab size: {tokenizer.vocab_size})")

    # ========== [3] 创建DataLoader ==========
    print("\n[3/6] 创建数据加载器...")
    train_dataset = RumorDataset(train_texts, train_labels, train_stances, vocab, config.MAX_LEN, tokenizer)
    val_dataset = RumorDataset(val_texts, val_labels, val_stances, vocab, config.MAX_LEN, tokenizer)
    train_loader = DataLoader(train_dataset, batch_size=config.BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config.BATCH_SIZE)

    # ========== [4] 创建模型与类权重 ==========
    print("\n[4/6] 创建模型与加权损失...")

    # 计算抗不平衡加权权重
    train_0 = sum(1 for l in train_labels if l == 0)
    train_1 = sum(1 for l in train_labels if l == 1)
    w0 = len(train_labels) / (2.0 * max(train_0, 1))
    w1 = len(train_labels) / (2.0 * max(train_1, 1))
    class_weights = torch.tensor([w0, w1], dtype=torch.float).to(device)
    print(f"  已启用加权惩罚 -> 谣言(0)权重: {w0:.4f} | 真实(1)权重: {w1:.4f}")

    if config.MODEL_TYPE == 'simple':
        model = SimpleMultiTaskModel(
            vocab_size=len(vocab.word2idx), embed_dim=config.EMBED_DIM, hidden_dim=config.HIDDEN_DIM,
            rumor_classes=2, stance_classes=3, num_encoder_layers=4, num_heads=8, dropout=config.DROPOUT
        )
    else:
        try:
            from transformers import BertModel
            model = MultiTaskModel(
                bert_model_name=config.BERT_MODEL, hidden_dim=config.HIDDEN_DIM,
                rumor_classes=2, stance_classes=3, dropout=config.DROPOUT
            )
        except ImportError:
            print("[警告] transformers未安装，回退至 SimpleMultiTaskModel")
            model = SimpleMultiTaskModel(
                vocab_size=len(vocab.word2idx), embed_dim=config.EMBED_DIM, hidden_dim=config.HIDDEN_DIM,
                rumor_classes=2, stance_classes=3, num_encoder_layers=4, num_heads=8, dropout=config.DROPOUT
            )
    
    model = model.to(device)
    
    # ========== [5] 开始训练 ==========
    print("\n[5/6] 开始训练...")
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.LEARNING_RATE, weight_decay=0.01)
    
    best_rumor_acc = 0
    best_epoch = 0
    best_report = ""
    
    for epoch in range(config.EPOCHS):
        print(f"\n[{epoch+1}/{config.EPOCHS}]")
        
        train_res = train_multi_task(model, train_loader, optimizer, device, config.TASK_WEIGHTS, class_weights)
        val_res = evaluate_multi_task(model, val_loader, device)
        
        print(f"  Train Loss: {train_res['loss']:.4f}")
        print(f"  Val Acc: {val_res['rumor_acc']*100:.2f}% | 谣言 F1: {val_res['rumor_f1_0']:.4f} | 真实新闻 F1: {val_res['rumor_f1_1']:.4f}")
        
        if val_res['rumor_acc'] > best_rumor_acc:
            best_rumor_acc = val_res['rumor_acc']
            best_epoch = epoch + 1
            torch.save({
                'model_state_dict': model.state_dict(),
                'accuracy': best_rumor_acc,
                'model_type': config.MODEL_TYPE
            }, config.MODEL_PATH)
            print(f"  🌟 已保存最佳模型 (Acc: {best_rumor_acc*100:.2f}%)")
            best_report = val_res['report_str']
    
    # ========== [6] 总结 ==========
    print("\n" + "=" * 60)
    print(f"🎉 训练完成！最佳模型出现在第 {best_epoch} 轮")
    print(f"最佳验证集准确率: {best_rumor_acc*100:.2f}%")
    print("\n=== 最佳模型评估报告 ===")
    print(best_report)
    print("=" * 60)

    # [修复跨架构覆盖Bug] 仅对比，不强行覆盖其他网络结构的文件
    compare_path = "E:/rumor_detection/models/CNN_GRU_Attention.pth"
    if os.path.exists(compare_path):
        try:
            old_acc = torch.load(compare_path, map_location='cpu').get('accuracy', 0)
            print(f"\n[模型争霸赛]")
            print(f"  当前 BERT_MultiTask : {best_rumor_acc*100:.2f}%")
            print(f"  历史 CNN_GRU_Attention : {old_acc*100:.2f}%")
        except: pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="先进谣言检测模型训练")
    parser.add_argument('--model_type', type=str, default='bert', choices=['simple', 'bert'])
    args = parser.parse_args()
    main(args)