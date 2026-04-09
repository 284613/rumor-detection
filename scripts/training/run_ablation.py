# -*- coding: utf-8 -*-
"""
消融实验脚本
四组对比实验：
  A - 完整传播树 + 无增强
  B - 极早期截断 + 无增强
  C - 极早期截断 + LLM增强 + beta=0.3
  D - 极早期截断 + LLM增强 + beta=0.0
"""

import os
os.environ['CUDA_LAUNCH_BLOCKING'] = "1"
os.environ['TORCH_CUDA_ALLOC_CONF'] = "max_split_size_mb:128"

import sys
import json
import csv
import time
import random
import re
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Tuple, Dict, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── 路径修正：让 Python 找到 models/ 和 utils/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from models.multi_task import (
    MultiTaskModel, SimpleMultiTaskModel,
    compute_virtual_stance_loss, ALPHA, BETA
)
from utils.early_stage_simulator import batch_process_dataset

# ──────────────────────── 固定超参 ────────────────────────
SEED       = 42
EPOCHS     = 5     # 增至 5，防止欠拟合
BATCH_SIZE = 2     # RTX 3060 6GB；降低以避免 OOM
EARLY_STOP_PATIENCE = 2  # val acc 连续 N epoch 不提升则停止
LR         = 1e-5

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

DATA_DIR  = os.path.join(PROJECT_ROOT, 'data')
MODEL_DIR = os.path.join(PROJECT_ROOT, 'models')

# 继承 train_bert.py 的 Config 基本路径
BERT_MODEL  = os.path.join(MODEL_DIR, 'bert_base_chinese')
MAX_LEN     = 100  # 降低 MAX_LEN 以节省显存
HIDDEN_DIM  = 256
DROPOUT     = 0.3
TASK_WEIGHTS = (1.0, ALPHA)   # rumor : stance

# 消融数据文件路径 — 使用 CED 数据（含 text/label/children）
CED_FULL_PATH         = os.path.join(DATA_DIR, 'ced_full.json')
CED_EARLY_PATH        = os.path.join(DATA_DIR, 'ced_early.json')
CED_EARLY_AUG_PATH    = os.path.join(DATA_DIR, 'ced_early_augmented.json')
AUG_QWEN_PATH         = os.path.join(DATA_DIR, 'augmented_qwen.json')
EARLY_REAL_PATH       = os.path.join(DATA_DIR, 'ablation_early_real.json')
EARLY_AUGMENTED_PATH  = os.path.join(DATA_DIR, 'ablation_early_augmented.json')

RESULTS_JSON = os.path.join(DATA_DIR, 'ablation_results.json')
RESULTS_CSV  = os.path.join(DATA_DIR, 'ablation_results.csv')

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ─────────────────────────── 中文数据加载（复用 train_bert.py 逻辑）────────────────────────

STANCE_LABEL_MAP = {
    'support': 0, 'supporting': 0, 'deny': 1, 'denying': 1,
    'neutral': 2, 'unverified': 2,
    '支持': 0, '反对': 1, '中立': 2,
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _load_full_chinese_data() -> Tuple[List[str], List[int], List[int], List[bool]]:
    """加载 CED 完整传播树数据（实验 A），展开为行格式，is_virtual 全为 False"""
    return _load_ced_tree_file(CED_FULL_PATH)


def _ced_label_to_int(label_raw) -> int:
    """CED label 转换：1=谣言→0, 0=非谣言→1（与 evaluate target_names 一致：谣言(0), 真实(1)）"""
    LABEL_MAP = {
        1: 0, 0: 1,               # CED 数字格式
        '1': 0, '0': 1,           # 字符串格式
        '辟谣': 0, '虚假': 0, '未证实': 0, '谣言': 0,
        '真实': 1,
    }
    return LABEL_MAP.get(label_raw, 0)


def _load_ced_tree_file(path: str) -> Tuple[List[str], List[int], List[int], List[bool]]:
    """加载 CED 嵌套树格式文件，展开为行格式"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    texts, labels, stances, is_virtual = [], [], [], []
    seen = set()

    for root_id, tree in data.items():
        lbl = _ced_label_to_int(tree.get('label', ''))

        def _flatten(node, is_virt=False):
            t = clean_text(node.get('text', ''))
            if t and len(t) > 5 and t not in seen:
                seen.add(t)
                texts.append(t)
                labels.append(lbl)
                stances.append(STANCE_LABEL_MAP.get(node.get('stance', '中立'), 2))
                is_virtual.append(is_virt)
            for child in node.get('children', []):
                _flatten(child, child.get('is_virtual', False))
            for child in node.get('virtual_children', []):
                _flatten(child, True)

        _flatten(tree)

    return texts, labels, stances, is_virtual


def _load_ablation_file(path: str) -> Tuple[List[str], List[int], List[int], List[bool]]:
    """加载 ablation_early_*.json（行格式），提取 text/label/stance/is_virtual"""
    with open(path, 'r', encoding='utf-8') as f:
        records = json.load(f)

    texts, labels, stances, is_virtual = [], [], [], []
    seen = set()
    for r in records:
        t = clean_text(r.get('text', ''))
        if not t or len(t) <= 5:
            continue
        if t in seen:
            continue
        seen.add(t)
        lbl = _ced_label_to_int(r.get('label', ''))
        stance = STANCE_LABEL_MAP.get(r.get('stance', '中立'), 2)
        texts.append(t)
        labels.append(lbl)
        stances.append(stance)
        is_virtual.append(bool(r.get('is_virtual', False)))

    return texts, labels, stances, is_virtual


def load_data(data_mode: str):
    """
    data_mode:
      'full'            - 完整中文数据
      'early_real'      - 极早期截断，无虚拟节点
      'early_augmented' - 极早期截断 + 虚拟节点
    """
    if data_mode == 'full':
        return _load_full_chinese_data()
    elif data_mode == 'early_real':
        return _load_ced_tree_file(CED_EARLY_PATH)
    elif data_mode == 'early_augmented':
        return _load_ced_tree_file(CED_EARLY_AUG_PATH)
    else:
        raise ValueError(f"未知 data_mode: {data_mode}")


def _ensure_ablation_files():
    """若消融数据文件不存在，则先生成"""
    if not os.path.exists(EARLY_REAL_PATH) or not os.path.exists(EARLY_AUGMENTED_PATH):
        print("[数据准备] 消融数据文件缺失，正在生成...")
        if not os.path.exists(PROP_TREES_PATH):
            raise FileNotFoundError(
                f"缺少传播树文件: {PROP_TREES_PATH}\n"
                "请先运行数据预处理生成 propagation_trees.json"
            )
        batch_process_dataset(
            propagation_trees_path=PROP_TREES_PATH,
            augmented_qwen_path=AUG_QWEN_PATH,
            output_early_real=EARLY_REAL_PATH,
            output_early_augmented=EARLY_AUGMENTED_PATH,
        )
        print("[数据准备] 消融数据文件生成完毕")


# ─────────────────────────── Dataset ────────────────────────

class AblationDataset(Dataset):
    def __init__(self,
                 texts: List[str],
                 labels: List[int],
                 stances: List[int],
                 is_virtual: List[bool],
                 tokenizer,
                 max_len: int = 128):
        self.labels = labels
        self.stances = stances
        self.is_virtual = is_virtual

        print(f"    预计算 tokenization ({len(texts)} 条)...")
        self.input_ids_list = []
        self.attn_mask_list = []
        for i, text in enumerate(texts):
            enc = tokenizer(
                text,
                padding='max_length',
                truncation=True,
                max_length=max_len,
                return_tensors='pt'
            )
            self.input_ids_list.append(enc['input_ids'].squeeze(0))
            self.attn_mask_list.append(enc['attention_mask'].squeeze(0))
            if (i + 1) % 2000 == 0:
                print(f"    已处理 {i+1}/{len(texts)} 条")
        print("    Tokenization 完成")

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            'input_ids':    self.input_ids_list[idx],
            'attention_mask': self.attn_mask_list[idx],
            'rumor_labels': torch.tensor(self.labels[idx], dtype=torch.long),
            'stance_labels': torch.tensor(self.stances[idx], dtype=torch.long),
            'is_virtual':   torch.tensor(self.is_virtual[idx], dtype=torch.bool),
        }


# ─────────────────────────── 训练 / 评估 ────────────────────────

def train_one_epoch(model, loader, optimizer, device, class_weights, beta: float):
    model.train()
    torch.backends.cudnn.enabled = False
    criterion_rumor  = nn.CrossEntropyLoss(weight=class_weights)
    criterion_stance = nn.CrossEntropyLoss()

    total_loss = 0.0
    correct = 0
    total   = 0

    n_batches = len(loader)
    for step, batch in enumerate(loader):
        if step % 100 == 0:
            print(f"\r    batch {step}/{n_batches}  loss={total_loss/max(step,1):.4f}", end='', flush=True)
        input_ids    = batch['input_ids'].to(device)
        attn_mask    = batch['attention_mask'].to(device)
        rumor_labels = batch['rumor_labels'].to(device)
        stance_labels = batch['stance_labels'].to(device)
        is_virtual   = batch['is_virtual'].to(device)

        outputs = model(input_ids, attn_mask, task='both')
        loss_r  = criterion_rumor(outputs['rumor_logits'], rumor_labels)

        # stance loss 仅对虚拟节点计算（CED 真实节点无 stance 标注）
        loss_vs = compute_virtual_stance_loss(
            outputs['stance_logits'], stance_labels, is_virtual, criterion_stance
        )

        loss = TASK_WEIGHTS[0] * loss_r + beta * loss_vs

        if torch.isnan(loss):
            optimizer.zero_grad()
            continue

        optimizer.zero_grad()
        loss.backward()

        # 梯度裁剪
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += loss.item()
        preds = torch.argmax(outputs['rumor_logits'], dim=1)
        correct += (preds == rumor_labels).sum().item()
        total   += rumor_labels.size(0)

    print(flush=True)  # 换行
    return total_loss / max(len(loader), 1), correct / max(total, 1)


def evaluate(model, loader, device) -> Dict:
    model.eval()
    all_preds, all_labels = [], []
    all_stance_preds, all_stance_labels = [], []

    with torch.no_grad():
        for batch in loader:
            input_ids    = batch['input_ids'].to(device)
            attn_mask    = batch['attention_mask'].to(device)
            rumor_labels = batch['rumor_labels'].to(device)
            stance_labels = batch['stance_labels'].to(device)

            outputs = model(input_ids, attn_mask, task='both')
            r_preds = torch.argmax(outputs['rumor_logits'], dim=1)
            s_preds = torch.argmax(outputs['stance_logits'], dim=1)

            all_preds.extend(r_preds.cpu().numpy())
            all_labels.extend(rumor_labels.cpu().numpy())
            all_stance_preds.extend(s_preds.cpu().numpy())
            all_stance_labels.extend(stance_labels.cpu().numpy())

    r_report = classification_report(
        all_labels, all_preds,
        labels=[0, 1], target_names=['谣言(0)', '真实(1)'],
        output_dict=True, zero_division=0
    )
    s_report = classification_report(
        all_stance_labels, all_stance_preds,
        labels=[0, 1, 2], target_names=['支持', '反对', '中立'],
        output_dict=True, zero_division=0
    )

    return {
        'accuracy':     r_report['accuracy'],
        'f1_rumor':     r_report.get('谣言(0)', {}).get('f1-score', 0.0),
        'f1_real':      r_report.get('真实(1)', {}).get('f1-score', 0.0),
        'stance_macro_f1': s_report.get('macro avg', {}).get('f1-score', 0.0),
    }


# ─────────────────────────── 单组实验 ────────────────────────

def run_one_experiment(
    exp_id: str,
    description: str,
    data_mode: str,
    beta: float,
) -> Dict:
    print(f"\n{'='*60}")
    print(f"===== 实验{exp_id}: {description} =====")
    print(f"  data_mode={data_mode}  beta={beta}")
    print('='*60)

    t0 = time.time()

    # 1. 加载数据
    texts, labels, stances, is_virtual = load_data(data_mode)
    from collections import Counter
    label_dist = Counter(labels)
    print(f"  数据总量: {len(texts)} 条  虚拟节点: {sum(is_virtual)}  标签分布: 谣言(0)={label_dist.get(0,0)} 真实(1)={label_dist.get(1,0)}")

    # 2. 划分
    train_t, val_t, train_l, val_l, train_s, val_s, train_v, val_v = train_test_split(
        texts, labels, stances, is_virtual,
        test_size=0.15, random_state=SEED,
        stratify=labels
    )
    print(f"  训练: {len(train_t)}  验证: {len(val_t)}")

    # 3. Tokenizer
    from transformers import BertTokenizer
    tokenizer = BertTokenizer.from_pretrained(BERT_MODEL)

    # 4. Dataset / DataLoader
    bs = BATCH_SIZE
    try:
        train_ds = AblationDataset(train_t, train_l, train_s, train_v, tokenizer, MAX_LEN)
        train_loader = DataLoader(train_ds, batch_size=bs, shuffle=True)
        # 触发一次以检测 OOM
        _ = next(iter(train_loader))
    except RuntimeError as e:
        if 'out of memory' in str(e).lower() and bs > 2:
            print(f"  [OOM] batch_size={bs} -> 回退到 2")
            bs = 2
            torch.cuda.empty_cache()
            train_loader = DataLoader(train_ds, batch_size=bs, shuffle=True)
        else:
            raise

    val_ds = AblationDataset(val_t, val_l, val_s, val_v, tokenizer, MAX_LEN)
    val_loader = DataLoader(val_ds, batch_size=bs)

    # 5. 模型
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    try:
        model = MultiTaskModel(
            bert_model_name=BERT_MODEL,
            hidden_dim=HIDDEN_DIM,
            rumor_classes=2,
            stance_classes=3,
            dropout=DROPOUT,
        ).to(DEVICE)
    except Exception as e:
        print(f"  [警告] MultiTaskModel 加载失败: {e}，回退至 SimpleMultiTaskModel")
        model = SimpleMultiTaskModel(
            vocab_size=21128,
            embed_dim=256,
            hidden_dim=HIDDEN_DIM,
            rumor_classes=2,
            stance_classes=3,
            num_encoder_layers=4,
            num_heads=8,
            dropout=DROPOUT,
        ).to(DEVICE)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)

    # 类别权重
    n0 = sum(1 for l in train_l if l == 0)
    n1 = sum(1 for l in train_l if l == 1)
    w0 = len(train_l) / (2.0 * max(n0, 1))
    w1 = len(train_l) / (2.0 * max(n1, 1))
    class_weights = torch.tensor([w0, w1], dtype=torch.float).to(DEVICE)

    # 6. 训练
    best_acc = 0.0
    best_metrics = {}
    no_improve = 0

    for epoch in range(EPOCHS):
        tr_loss, tr_acc = train_one_epoch(model, train_loader, optimizer, DEVICE, class_weights, beta)
        val_metrics = evaluate(model, val_loader, DEVICE)

        print(f"  Epoch [{epoch+1}/{EPOCHS}]  "
              f"loss={tr_loss:.4f}  train_acc={tr_acc*100:.1f}%  "
              f"val_acc={val_metrics['accuracy']*100:.2f}%  "
              f"F1谣言={val_metrics['f1_rumor']:.4f}  "
              f"F1真实={val_metrics['f1_real']:.4f}  "
              f"Stance-F1={val_metrics['stance_macro_f1']:.4f}", flush=True)

        if val_metrics['accuracy'] > best_acc:
            best_acc = val_metrics['accuracy']
            best_metrics = val_metrics.copy()
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= EARLY_STOP_PATIENCE:
                print(f"  [Early Stop] val_acc 连续 {EARLY_STOP_PATIENCE} epoch 未提升，提前终止")
                break

    elapsed = time.time() - t0
    best_metrics['elapsed_sec'] = round(elapsed, 1)
    best_metrics['exp_id']      = exp_id
    best_metrics['description'] = description
    best_metrics['data_mode']   = data_mode
    best_metrics['beta']        = beta

    print(f"\n  [实验{exp_id}] 最佳 Acc={best_acc*100:.2f}%  "
          f"F1谣言={best_metrics['f1_rumor']:.4f}  "
          f"F1真实={best_metrics['f1_real']:.4f}  "
          f"Stance-F1={best_metrics['stance_macro_f1']:.4f}  "
          f"用时={elapsed:.0f}s")
    return best_metrics


# ─────────────────────────── 结果输出 ────────────────────────

def print_markdown_table(results: List[Dict]):
    header = "| 实验 | 描述 | data_mode | beta | Acc(%) | F1-谣言 | F1-真实 | Stance F1 | 用时(s) |"
    sep    = "|------|------|-----------|------|--------|---------|---------|-----------|---------|"
    print("\n" + "=" * 80)
    print("消融实验结果汇总")
    print("=" * 80)
    print(header)
    print(sep)
    for r in results:
        print(
            f"| {r['exp_id']} "
            f"| {r['description']} "
            f"| {r['data_mode']} "
            f"| {r['beta']} "
            f"| {r['accuracy']*100:.2f} "
            f"| {r['f1_rumor']:.4f} "
            f"| {r['f1_real']:.4f} "
            f"| {r['stance_macro_f1']:.4f} "
            f"| {r['elapsed_sec']} |"
        )
    print()


def save_results(results: List[Dict]):
    with open(RESULTS_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"JSON 已保存: {RESULTS_JSON}")

    fieldnames = ['exp_id', 'description', 'data_mode', 'beta',
                  'accuracy', 'f1_rumor', 'f1_real', 'stance_macro_f1', 'elapsed_sec']
    with open(RESULTS_CSV, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    print(f"CSV 已保存: {RESULTS_CSV}")


# ─────────────────────────── 主入口 ────────────────────────

EXPERIMENTS = [
     {
        'exp_id':      'A',
        'description': '完整传播树 + 无增强',
        'data_mode':   'full',
       'beta':        0.0,
    },
    {
        'exp_id':      'B',
        'description': '极早期截断 + 无增强',
        'data_mode':   'early_real',
        'beta':        0.0,
    },
    {
        'exp_id':      'C',
        'description': '极早期截断 + LLM增强 + β=0.3',
        'data_mode':   'early_augmented',
        'beta':        0.3,
    },
    {
        'exp_id':      'D',
        'description': '极早期截断 + LLM增强 + β=0',
        'data_mode':   'early_augmented',
        'beta':        0.0,
    },
]


def main():
    print("=" * 60)
    print("消融实验  |  四组对比")
    print(f"EPOCHS={EPOCHS}  BATCH_SIZE={BATCH_SIZE}  SEED={SEED}  DEVICE={DEVICE}")
    print("=" * 60)

    all_results = []
    for exp in EXPERIMENTS:
        result = run_one_experiment(**exp)
        all_results.append(result)

    print_markdown_table(all_results)
    save_results(all_results)


if __name__ == '__main__':
    main()
