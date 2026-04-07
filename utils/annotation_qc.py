# -*- coding: utf-8 -*-
"""
标注质量控制模块
用于计算多标注者标注一致性，筛选高质量标注数据
"""

import numpy as np


def compute_fleiss_kappa(annotations, num_categories):
    """
    计算Fleiss' Kappa系数
    
    参数:
        annotations: numpy数组，每行是一个样本，每列是一个标注者的标签
                    值为0到(num_categories-1)的整数，表示标注的类别
        num_categories: 类别数量
    
    返回:
        kappa: Fleiss' Kappa系数
            < 0: 没有一致性
            0 ~ 0.2: 轻微一致(slight)
            0.2 ~ 0.4: 一般一致(fair)
            0.4 ~ 0.6: 中等一致(moderate)
            0.6 ~ 0.8: 较高一致(substantial)
            0.8 ~ 1.0: 几乎完全一致(almost perfect)
    """
    n_samples, n_annotators = annotations.shape
    
    # 计算每个样本中每个类别被选择的次数
    # count_matrix[i, j] = 样本i被标注为类别j的次数
    count_matrix = np.zeros((n_samples, num_categories), dtype=int)
    
    for i in range(n_samples):
        for j in range(num_categories):
            count_matrix[i, j] = np.sum(annotations[i, :] == j)
    
    # 计算每个样本的一致性比例 P_i
    # P_i = (1 / (n * (n-1))) * (sum(n_ij^2) - n)
    n = n_annotators
    P_i = np.zeros(n_samples)
    
    for i in range(n_samples):
        sum_squared = np.sum(count_matrix[i, :] ** 2)
        P_i[i] = (sum_squared - n) / (n * (n - 1))
    
    # 计算平均一致性 P_bar
    P_bar = np.mean(P_i)
    
    # 计算每个类别的期望比例 P_j
    # P_j = (1 / (n * N)) * sum(n_ij)
    P_j = np.zeros(num_categories)
    for j in range(num_categories):
        P_j[j] = np.sum(count_matrix[:, j]) / (n * n_samples)
    
    # 计算期望一致性 P_e
    P_e = np.sum(P_j ** 2)
    
    # 计算Kappa系数
    # Kappa = (P_bar - P_e) / (1 - P_e)
    if P_e == 1:
        # 所有标注者都选择同一类别的情况
        kappa = 1.0 if P_bar == 1.0 else 0.0
    else:
        kappa = (P_bar - P_e) / (1 - P_e)
    
    return kappa


def compute_pairwise_agreement(annotations):
    """
    计算两两标注者之间的一致性
    
    参数:
        annotations: numpy数组，每行是一个样本，每列是一个标注者的标签
    
    返回:
        agreement_matrix: n x n 的矩阵
            agreement_matrix[i, j] 表示标注者i和标注者j之间的一致率
    """
    n_samples, n_annotators = annotations.shape
    
    # 初始化一致性矩阵
    agreement_matrix = np.zeros((n_annotators, n_annotators))
    
    # 计算每对标注者之间的一致率
    for i in range(n_annotators):
        for j in range(n_annotators):
            if i == j:
                # 自身一致性为1
                agreement_matrix[i, j] = 1.0
            else:
                # 计算一致率
                agreements = np.sum(annotations[:, i] == annotations[:, j])
                agreement_matrix[i, j] = agreements / n_samples
    
    return agreement_matrix


def compute_pairwise_kappa(annotations, num_categories):
    """
    计算两两标注者之间的Cohen's Kappa系数
    
    参数:
        annotations: numpy数组，每行是一个样本，每列是一个标注者的标签
        num_categories: 类别数量
    
    返回:
        kappa_matrix: n x n 的矩阵
            kappa_matrix[i, j] 表示标注者i和标注者j之间的Kappa系数
    """
    n_samples, n_annotators = annotations.shape
    
    kappa_matrix = np.zeros((n_annotators, n_annotators))
    
    for i in range(n_annotators):
        for j in range(n_annotators):
            if i == j:
                kappa_matrix[i, j] = 1.0
            else:
                # 构建混淆矩阵
                conf_matrix = np.zeros((num_categories, num_categories))
                for k in range(n_samples):
                    label_i = annotations[k, i]
                    label_j = annotations[k, j]
                    conf_matrix[label_i, label_j] += 1
                
                # 计算观察一致性
                po = np.trace(conf_matrix) / n_samples
                
                # 计算期望一致性
                p_row = conf_matrix.sum(axis=1) / n_samples
                p_col = conf_matrix.sum(axis=0) / n_samples
                pe = np.sum(p_row * p_col)
                
                # 计算Kappa
                if pe == 1:
                    kappa_matrix[i, j] = 1.0 if po == 1.0 else 0.0
                else:
                    kappa_matrix[i, j] = (po - pe) / (1 - pe)
    
    return kappa_matrix


def filter_by_kappa(annotations, threshold=0.6):
    """
    根据Kappa阈值筛选高质量标注
    
    参数:
        annotations: numpy数组，每行是一个样本，每列是一个标注者的标签
        threshold: Kappa阈值，默认为0.6
    
    返回:
        high_quality_mask: 布尔数组
            True表示该样本的标注一致性达到阈值
    """
    n_samples, n_annotators = annotations.shape
    
    # 获取类别数量
    num_categories = len(np.unique(annotations))
    
    # 计算每个样本的P_i (一致性比例)
    count_matrix = np.zeros((n_samples, num_categories), dtype=int)
    for i in range(n_samples):
        for j in range(num_categories):
            count_matrix[i, j] = np.sum(annotations[i, :] == j)
    
    n = n_annotators
    P_i = np.zeros(n_samples)
    
    for i in range(n_samples):
        sum_squared = np.sum(count_matrix[i, :] ** 2)
        P_i[i] = (sum_squared - n) / (n * (n - 1))
    
    # 计算每个类别的期望比例 P_j
    P_j = np.zeros(num_categories)
    for j in range(num_categories):
        P_j[j] = np.sum(count_matrix[:, j]) / (n * n_samples)
    
    # 计算期望一致性 P_e
    P_e = np.sum(P_j ** 2)
    
    # 计算每个样本的Kappa值
    if P_e == 1:
        kappa_per_sample = np.where(P_i == 1.0, 1.0, 0.0)
    else:
        kappa_per_sample = (P_i - P_e) / (1 - P_e)
    
    # 筛选高于阈值的样本
    high_quality_mask = kappa_per_sample >= threshold
    
    return high_quality_mask


def get_annotation_statistics(annotations, num_categories):
    """
    获取标注统计信息
    
    参数:
        annotations: numpy数组，每行是一个样本，每列是一个标注者的标签
        num_categories: 类别数量
    
    返回:
        stats: 字典，包含各种统计信息
    """
    n_samples, n_annotators = annotations.shape
    
    # 每个类别被选择的次数
    category_counts = np.zeros(num_categories)
    for j in range(num_categories):
        category_counts[j] = np.sum(annotations == j)
    
    # 每个样本的标注分布
    count_matrix = np.zeros((n_samples, num_categories), dtype=int)
    for i in range(n_samples):
        for j in range(num_categories):
            count_matrix[i, j] = np.sum(annotations[i, :] == j)
    
    # 计算多数投票结果
    majority_vote = np.argmax(count_matrix, axis=1)
    
    # 计算多数投票一致性（多数比例）
    max_counts = np.max(count_matrix, axis=1)
    majority_ratio = max_counts / n_annotators
    
    stats = {
        'n_samples': n_samples,
        'n_annotators': n_annotators,
        'num_categories': num_categories,
        'category_counts': category_counts,
        'category_proportions': category_counts / (n_samples * n_annotators),
        'majority_vote': majority_vote,
        'majority_ratio': majority_ratio,
        'mean_majority_ratio': np.mean(majority_ratio),
    }
    
    return stats


if __name__ == '__main__':
    # 测试代码
    print("=" * 50)
    print("标注质量控制模块测试")
    print("=" * 50)
    
    # 示例1: 简单测试数据
    # 5个样本，3个标注者，2个类别(0和1)
    annotations = np.array([
        [0, 0, 1],  # 样本1: 2个0, 1个1
        [0, 0, 0],  # 样本2: 3个0，完全一致
        [1, 1, 1],  # 样本3: 3个1，完全一致
        [0, 1, 1],  # 样本4: 1个0, 2个1
        [0, 1, 0],  # 样本5: 2个0, 1个1
    ])
    
    num_categories = 2
    
    print("\n测试数据:")
    print(annotations)
    print(f"样本数: {annotations.shape[0]}, 标注者数: {annotations.shape[1]}")
    
    # 计算Fleiss' Kappa
    kappa = compute_fleiss_kappa(annotations, num_categories)
    print(f"\nFleiss' Kappa系数: {kappa:.4f}")
    
    # 计算两两一致性
    agreement = compute_pairwise_agreement(annotations)
    print("\n两两标注者一致率矩阵:")
    print(agreement)
    
    # 计算两两Kappa
    pairwise_kappa = compute_pairwise_kappa(annotations, num_categories)
    print("\n两两标注者Kappa系数矩阵:")
    print(pairwise_kappa)
    
    # 筛选高质量标注
    threshold = 0.6
    high_quality_mask = filter_by_kappa(annotations, threshold)
    print(f"\nKappa阈值{threshold}以上的高质量样本:")
    print(f"高质量样本索引: {np.where(high_quality_mask)[0]}")
    print(f"高质量样本数量: {np.sum(high_quality_mask)}/{len(high_quality_mask)}")
    
    # 获取统计信息
    stats = get_annotation_statistics(annotations, num_categories)
    print("\n标注统计信息:")
    print(f"  各类别数量: {stats['category_counts']}")
    print(f"  各类别比例: {stats['category_proportions']}")
    print(f"  平均多数投票一致率: {stats['mean_majority_ratio']:.4f}")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
