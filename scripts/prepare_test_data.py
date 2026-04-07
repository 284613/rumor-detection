# -*- coding: utf-8 -*-
"""
测试数据准备脚本
1. 从现有数据中划分训练/验证/测试集
2. 对测试数据进行增强（规则+LLM可选）
目标：5000+条测试数据
"""
import os
import json
import random
from collections import Counter

# ============ 配置 =============
TEST_SIZE = 15000  # 目标测试集大小
USE_LLM = False   # 是否使用LLM增强（需要API Key）

print("="*60)
print("测试数据准备")
print("="*60)

# ============ 加载所有数据源 =============
all_texts = []
all_labels = []
all_sources = []

def load_jsonl(path, label=0, source="unknown"):
    """加载JSON Lines格式"""
    texts = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        text = item.get('rumorText', '').strip()
                        if text and len(text) > 10:
                            texts.append({
                                'text': text,
                                'label': label,
                                'source': source
                            })
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"  加载失败 {path}: {e}")
    return texts

def load_json(path, text_key, label_key, source="unknown"):
    """加载JSON格式"""
    items = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                text = item.get(text_key, '').strip()
                label_str = item.get(label_key, '')
                if text and len(text) > 10:
                    label = 0 if label_str in ['谣言', '假', 'false'] else 1
                    items.append({
                        'text': text,
                        'label': label,
                        'source': source
                    })
    except Exception as e:
        print(f"  加载失败 {path}: {e}")
    return items

# 加载清华谣言数据集（主要数据源，~3万条）
print("\n[1] 加载数据源...")
rumors = load_jsonl(
    "E:/rumor_detection/data/Chinese_Rumor_Dataset/rumors_v170613.json",
    label=0,
    source="THU_Rumor"
)
print(f"  清华谣言数据集: {len(rumors)} 条")

# 加载weibo1
weibo1 = load_json(
    "E:/rumor_detection/data/weibo1_rumor.tsv",
    text_key='text' if False else None,
    label_key='label',
    source="weibo1"
)
# TSV格式特殊处理
try:
    import pandas as pd
    df = pd.read_csv("E:/rumor_detection/data/weibo1_rumor.tsv", sep='\t', header=None, names=['label', 'text'])
    weibo1 = []
    for _, row in df.iterrows():
        text = str(row['text'])
        if len(text) > 10:
            weibo1.append({
                'text': text,
                'label': int(row['label']),
                'source': 'weibo1'
            })
    print(f"  weibo1_rumor: {len(weibo1)} 条")
except Exception as e:
    print(f"  weibo1_rumor加载失败: {e}")

# 加载augmented_qwen
aug_qwen = load_json(
    "E:/rumor_detection/data/augmented_qwen.json",
    text_key='augmented',
    label_key='label',
    source="qwen_aug"
)
print(f"  augmented_qwen: {len(aug_qwen)} 条")

# 合并所有数据
all_data = rumors + weibo1 + aug_qwen
print(f"\n总计: {len(all_data)} 条")

# 去除重复
seen = set()
unique_data = []
for item in all_data:
    text_hash = hash(item['text'][:50])
    if text_hash not in seen:
        seen.add(text_hash)
        unique_data.append(item)

print(f"去重后: {len(unique_data)} 条")

# 打乱
random.shuffle(unique_data)

# ============ 划分数据 =============
print("\n[2] 划分数据集...")

# 计算划分点
n = len(unique_data)
train_end = int(n * 0.85)
val_end = int(n * 0.92)

train_data = unique_data[:train_end]
val_data = unique_data[train_end:val_end]
test_data = unique_data[val_end:]

print(f"  训练集: {len(train_data)} 条")
print(f"  验证集: {len(val_data)} 条")
print(f"  测试集: {len(test_data)} 条")

# ============ 测试集增强 =============
current_test_size = len(test_data)
if current_test_size < TEST_SIZE:
    print(f"\n[3] 测试集增强 (目标: {TEST_SIZE})...")

    # 如果不够，从训练集借用一些（带有标签的数据）
    # 或者对现有测试数据进行增强
    augment_factor = (TEST_SIZE // current_test_size) + 1

    # 简单增强：对每条数据生成多个变体
    augmented_test = []
    stance_variations = [
        "支持",
        "反对",
        "中立"
    ]

    for item in test_data:
        # 原始
        augmented_test.append(item.copy())
        augmented_test[-1]['augmentation_type'] = 'original'
        augmented_test[-1]['stance'] = '中立'

        # 简单变换1：同义词替换（模拟）
        words = item['text'].split()
        if len(words) > 5:
            new_text = ' '.join(words[:len(words)//2]) + '...' + words[-1] if len(words) > 3 else item['text']
            augmented_test.append({
                'text': new_text,
                'label': item['label'],
                'source': item['source'] + '_trunc',
                'augmentation_type': 'truncation',
                'stance': '中立'
            })

        # 简单变换2：添加前缀/后缀
        prefixes = ["转发", "听说", "据悉"]
        for prefix in prefixes[:2]:
            if len(augmented_test) >= TEST_SIZE:
                break
            augmented_test.append({
                'text': f"{prefix}：{item['text']}",
                'label': item['label'],
                'source': item['source'] + '_prefix',
                'augmentation_type': 'prefix',
                'stance': '中立'
            })

    test_data = augmented_test[:TEST_SIZE]
    print(f"  增强后测试集: {len(test_data)} 条")

# ============ 保存数据 =============
print("\n[4] 保存数据...")

# 保存训练集
train_path = "E:/rumor_detection/data/train_set.json"
with open(train_path, 'w', encoding='utf-8') as f:
    json.dump(train_data, f, ensure_ascii=False, indent=2)
print(f"  训练集: {train_path}")

# 保存验证集
val_path = "E:/rumor_detection/data/val_set.json"
with open(val_path, 'w', encoding='utf-8') as f:
    json.dump(val_data, f, ensure_ascii=False, indent=2)
print(f"  验证集: {val_path}")

# 保存测试集
test_path = "E:/rumor_detection/data/test_set.json"
with open(test_path, 'w', encoding='utf-8') as f:
    json.dump(test_data, f, ensure_ascii=False, indent=2)
print(f"  测试集: {test_path}")

# 统计
print("\n" + "="*60)
print("数据集统计")
print("="*60)
label_dist = Counter(item['label'] for item in test_data)
print(f"测试集标签分布: 谣言={label_dist[0]}, 真实={label_dist[1]}")
print(f"总计测试样本: {len(test_data)}")
print("="*60)
