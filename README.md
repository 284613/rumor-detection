# 社交媒体恶意谣言识别研究与实现

## 项目概述

基于深度学习的社交媒体谣言自动识别系统，支持中文微博和英文Twitter。

## 目录结构

```
rumor_detection/
├── docs/               # 项目文档
│   ├── README.md       # 项目总文档
│   ├── task-plan.md    # 任务计划
│   └── PROJECT_LOG.md  # 项目日志
│
├── models/             # 模型定义
│   ├── propagation_tree.py   # 传播树模块
│   ├── bert_cnn.py          # BERT+CNN
│   ├── multi_task.py        # 多任务学习
│   └── best_optimized_model.pth  # 最优模型 (87.6%)
│
├── data/               # 数据目录
│   ├── raw/           # 原始数据集
│   └── processed/      # 处理后的数据
│
├── utils/              # 工具脚本
│   ├── data_augmentation.py  # 数据增强
│   ├── llm_augment.py       # LLM增强
│   └── annotation_qc.py     # 标注质量控制
│
├── app/                # 原型系统
│   └── streamlit_app.py     # Streamlit演示
│
├── scripts/            # 脚本
│   ├── create_midterm_ppt.js  # PPT生成脚本
│   └── train_*.py           # 训练脚本
│
├── reports/            # 汇报材料
│   └── 中期汇报_动画版.pptx   # 最终版PPT
│
├── train_*.py         # 训练脚本（根目录）
├── evaluate.py         # 评估脚本
└── requirements.txt   # 依赖
```

## 已完成模型

| 模型 | 准确率 | 文件 |
|------|--------|------|
| TextCNN | 73% | train_cn.py |
| 多任务BERT | 61.57% | train_advanced.py |
| **CNN+GRU+Attention** | **87.60%** | train_optimized.py |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 训练模型
python train_optimized.py

# 评估
python evaluate.py

# 启动演示
streamlit run app/streamlit_app.py
```

## 核心创新

1. **传播树结构建模** - 利用谣言传播链的树状结构
2. **多关系区分** - 区分转发/评论/引用三种传播关系
3. **多任务学习** - 联合谣言分类与立场检测

## 数据集

- 清华微博谣言数据集 (31,669条)
- CED_Dataset (3,387条)
- PHEME英文数据集 (5,447条)
- LIAR (12,800条)
- 总计: 56,111条中英双语数据
