# -*- coding: utf-8 -*-
import json
import numpy as np
from collections import Counter
import sys

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

def fleiss_kappa(data_matrix):
    """
    计算Fleiss' Kappa系数
    data_matrix: numpy数组，每行是一个样本，每列是每个类别的标注数量
    """
    n_subjects, n_categories = data_matrix.shape
    n_raters = int(data_matrix.sum(axis=1)[0])
    
    if n_raters <= 1:
        return 0, 0, 0
    
    # 计算每个样本的标注比例
    P_i = (np.sum(data_matrix ** 2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
    
    # 计算观察到的一致性
    P_bar = np.mean(P_i)
    
    # 计算期望一致性
    p_j = np.sum(data_matrix, axis=0) / (n_subjects * n_raters)
    P_e = np.sum(p_j ** 2)
    
    # 计算Kappa
    if P_e == 1:
        return 1.0, P_bar, P_e
    
    if P_bar > 1:
        P_bar = 1.0
        
    kappa = (P_bar - P_e) / (1 - P_e)
    
    return kappa, P_bar, P_e

def prepare_rumor_type_matrix(originals_dict):
    """准备谣言类型的标注矩阵"""
    categories = ['真', '假', '未证实']
    cat_to_idx = {cat: i for i, cat in enumerate(categories)}
    
    matrix = []
    for orig, items in originals_dict.items():
        counts = [0] * len(categories)
        for item in items:
            label = item['label']
            if label in cat_to_idx:
                counts[cat_to_idx[label]] += 1
        matrix.append(counts)
    
    return np.array(matrix)

def prepare_stance_matrix(originals_dict):
    """准备立场倾向的标注矩阵"""
    categories = ['支持', '反对', '中立']
    cat_to_idx = {cat: i for i, cat in enumerate(categories)}
    
    matrix = []
    for orig, items in originals_dict.items():
        counts = [0] * len(categories)
        for item in items:
            stance = item.get('stance')
            if stance and stance in cat_to_idx:
                counts[cat_to_idx[stance]] += 1
        matrix.append(counts)
    
    return np.array(matrix)

# 加载数据
with open(r'E:\rumor_detection\data\augmented_qwen.json', encoding='utf-8') as f:
    data = json.load(f)

# 按原始内容分组
originals = {}
for item in data:
    orig = item['original']
    if orig not in originals:
        originals[orig] = []
    originals[orig].append(item)

print(f"总样本数: {len(originals)}")
print(f"总标注数: {len(data)}")

# 1. 计算谣言类型的Fleiss' Kappa
rumor_matrix = prepare_rumor_type_matrix(originals)
print(f"\n谣言类型标注矩阵形状: {rumor_matrix.shape}")

rater_counts = rumor_matrix.sum(axis=1)
print(f"每个样本的标注数范围: {rater_counts.min()} - {rater_counts.max()}")

# 只保留有多个标注者的样本进行Kappa计算
valid_rows = rater_counts > 1
rumor_matrix_valid = rumor_matrix[valid_rows]
print(f"有效样本数(标注数>1): {rumor_matrix_valid.shape[0]}")

kappa_rumor = 0
P_bar_rumor = 0
P_e_rumor = 0

if rumor_matrix_valid.shape[0] > 0:
    kappa_rumor, P_bar_rumor, P_e_rumor = fleiss_kappa(rumor_matrix_valid)
    print(f"\n=== 谣言类型 Fleiss' Kappa ===")
    print(f"Kappa值: {kappa_rumor:.4f}")
    print(f"观察到的一致性(P̄): {P_bar_rumor:.4f}")
    print(f"期望一致性(P_e): {P_e_rumor:.4f}")

# 2. 计算立场倾向的Fleiss' Kappa
stance_matrix = prepare_stance_matrix(originals)
print(f"\n立场倾向标注矩阵形状: {stance_matrix.shape}")

stance_rater_counts = stance_matrix.sum(axis=1)
valid_stance_rows = stance_rater_counts > 1
stance_matrix_valid = stance_matrix[valid_stance_rows]
print(f"有多个立场标注的样本数: {stance_matrix_valid.shape[0]}")

kappa_stance = 0
P_bar_stance = 0
P_e_stance = 0

if stance_matrix_valid.shape[0] > 0:
    kappa_stance, P_bar_stance, P_e_stance = fleiss_kappa(stance_matrix_valid)
    print(f"\n=== 立场倾向 Fleiss' Kappa ===")
    print(f"Kappa值: {kappa_stance:.4f}")
    print(f"观察到的一致性(P̄): {P_bar_stance:.4f}")
    print(f"期望一致性(P_e): {P_e_stance:.4f}")

# 3. 综合解读
def interpret_kappa(kappa):
    if kappa < 0:
        return "比随机更差"
    elif kappa < 0.20:
        return "轻微一致 (Slight)"
    elif kappa < 0.40:
        return "一般一致 (Fair)"
    elif kappa < 0.60:
        return "中等一致 (Moderate)"
    elif kappa < 0.80:
        return "较高一致 (Substantial)"
    else:
        return "几乎完美一致 (Almost Perfect)"

print(f"\n=== 综合解读 ===")
print(f"谣言类型一致性: {interpret_kappa(kappa_rumor)}")
print(f"立场倾向一致性: {interpret_kappa(kappa_stance)}")

# 4. 筛选高质量数据
# 根据谣言类型多数标注比例筛选
# 高质量标准：谣言类型多数标注占比 >= 70%
RUMOR_CONSISTENCY_THRESHOLD = 0.7

high_quality_samples = []
low_quality_samples = []

for orig, items in originals.items():
    # 统计谣言类型标注
    rumor_labels = [item['label'] for item in items]
    rumor_counts = Counter(rumor_labels)
    
    # 统计立场标注
    stances = [item.get('stance') for item in items if item.get('stance')]
    stance_counts = Counter(stances)
    
    total_annotations = len(items)
    
    # 谣言类型一致性: 多数标注的比例
    if total_annotations > 0:
        max_rumor_count = max(rumor_counts.values())
        rumor_consistency = max_rumor_count / total_annotations
    else:
        rumor_consistency = 0
    
    # 根据谣言类型一致性筛选
    if rumor_consistency >= RUMOR_CONSISTENCY_THRESHOLD:
        high_quality_samples.append({
            'original': orig,
            'consistency': rumor_consistency,
            'rumor_distribution': dict(rumor_counts),
            'total_annotations': total_annotations
        })
    else:
        low_quality_samples.append({
            'original': orig,
            'consistency': rumor_consistency,
            'rumor_distribution': dict(rumor_counts),
            'total_annotations': total_annotations
        })

print(f"\n=== 数据筛选结果 (谣言类型一致性阈值: {RUMOR_CONSISTENCY_THRESHOLD}) ===")
print(f"高质量样本数: {len(high_quality_samples)}")
print(f"低质量样本数: {len(low_quality_samples)}")

# 5. 生成结果JSON
# 使用谣言类型Kappa作为主要指标
overall_kappa = kappa_rumor

result = {
    "kappa_score": round(overall_kappa, 4),
    "kappa_rumor_type": round(kappa_rumor, 4),
    "kappa_stance": round(kappa_stance, 4),
    "interpretation": interpret_kappa(overall_kappa),
    "total_samples": len(originals),
    "high_quality_samples": len(high_quality_samples),
    "low_quality_samples": len(low_quality_samples),
    "details": {
        "rumor_type": {
            "kappa": round(kappa_rumor, 4),
            "interpretation": interpret_kappa(kappa_rumor),
            "P_bar": round(P_bar_rumor, 4) if P_bar_rumor != 0 else 0,
            "P_e": round(P_e_rumor, 4) if P_e_rumor != 0 else 0,
            "categories": ["真", "假", "未证实"],
            "distribution": dict(Counter(item['label'] for item in data))
        },
        "stance": {
            "kappa": round(kappa_stance, 4),
            "interpretation": interpret_kappa(kappa_stance),
            "P_bar": round(P_bar_stance, 4) if P_bar_stance != 0 else 0,
            "P_e": round(P_e_stance, 4) if P_e_stance != 0 else 0,
            "categories": ["支持", "反对", "中立"],
            "distribution": dict(Counter(item.get('stance') for item in data if item.get('stance')))
        },
        "threshold": RUMOR_CONSISTENCY_THRESHOLD
    },
    "high_quality_samples_detail": high_quality_samples,
    "low_quality_samples_detail": low_quality_samples
}

# 保存结果
with open(r'E:\rumor_detection\data\quality_control.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存到: E:\\rumor_detection\\data\\quality_control.json")

# 打印摘要
print(f"\n=== 最终结果 ===")
print(json.dumps({
    "kappa_score": result["kappa_score"],
    "interpretation": result["interpretation"],
    "total_samples": result["total_samples"],
    "high_quality_samples": result["high_quality_samples"],
    "low_quality_samples": result["low_quality_samples"]
}, ensure_ascii=False, indent=2))
