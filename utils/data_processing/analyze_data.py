# -*- coding: utf-8 -*-
import json
from collections import Counter
import sys

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

# 加载数据
with open(r'E:\rumor_detection\data\augmented_qwen.json', encoding='utf-8') as f:
    data = json.load(f)

# 统计每个original有多少个augmented
originals = {}
for item in data:
    orig = item['original']
    if orig not in originals:
        originals[orig] = []
    originals[orig].append(item)

print('唯一原始内容数:', len(originals))
print('总增强数:', len(data))

# 统计每个原始内容被增强的次数
counts = Counter(len(v) for v in originals.values())
print('每个内容的增强次数分布:', dict(counts))

# 查看label分布
labels = [item['label'] for item in data]
print('谣言类型分布:', dict(Counter(labels)))

# 查看stance分布  
stances = [item.get('stance', None) for item in data]
print('立场倾向分布:', dict(Counter(stances)))

# 检查augmentation_type分布
aug_types = [item.get('augmentation_type', None) for item in data]
print('增强类型分布:', dict(Counter(aug_types)))
