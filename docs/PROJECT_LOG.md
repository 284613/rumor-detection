# 毕业设计项目完整工作日志

## 项目信息
- **项目位置**: E:\rumor_detection
- **课题**: 社交媒体恶意谣言识别的研究与实现

---

## 一、数据集汇总

### 公开数据集

| 数据集 | 语言 | 数量 | 来源 |
|--------|------|------|------|
| 清华微博谣言数据集 | 中文 | 31,669条 | GitHub THUNLP |
| weibo1_rumor | 中文 | 500条 | 百度飞桨 |
| CED_Dataset | 中文 | 3,387条 | 清华CED |
| PHEME | 英文 | 5,447条 | 欧盟FP7项目 |
| LIAR | 英文 | 12,800条 | UCSB PolitiFact |
| Twitter15/16 | 英文 | 2,308条 | ACL学术数据集 |

### 爬取数据
- 微博搜索爬取: 361条
- 已清洗+标注

### 增强数据
- 千问LLM增强: 248条

---

## 二、模型实现

### 已训练模型

| 模型 | 文件 | 准确率 |
|------|------|--------|
| TextCNN | train_cn.py | 73% |
| 多任务模型 | train_advanced.py | 61.57% |
| **优化CNN+GRU** | train_optimized.py | **87.60%** |

### 模型架构
- Embedding(256) → CNN多尺度 → BiGRU → Attention → 融合 → 多任务输出

---

## 三、关键代码文件

```
E:\rumor_detection\
├── models/
│   ├── propagation_tree.py    # 传播树模块
│   ├── bert_cnn.py           # BERT+CNN
│   └── multi_task.py         # 多任务学习
├── utils/
│   ├── crawler/              # 爬虫
│   ├── data_augmentation.py  # 增强
│   └── annotation_qc.py     # Kappa计算
├── train_optimized.py         # 最佳模型
└── models/best_optimized_model.pth
```

---

## 四、API配置
- 千问API: sk-2ddddb50a0f84f01a5b155afb28de024
- GPU: RTX 3060 Laptop (6GB)

---

## 五、参考文献

1. 杨利君，滕冲. 基于增强的双向树表示的推特谣言立场检测
2. 祖坤琳等. 新浪微博谣言检测研究
3. 胡斗等. 一种基于多关系传播树的谣言检测方法
4. VARSHNEY D. A review on rumor prediction
5. MA J. Detect rumor and stance jointly
6. Noh K. Data Augmentation Using Large Language Models
7. 李峤. 基于机器学习的推特谣言立场分析
8. 王安君. 基于Bert-Condition-CNN的中文微博立场检测

---

*更新时间: 2026-03-16*
