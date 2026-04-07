# 社交媒体恶意谣言识别的研究与实现 (Rumor Detection)

本项目旨在构建一个多语言、多任务的社交媒体谣言检测系统，支持中文（新浪微博）和英文（Twitter）数据，集成了传统的深度学习模型与先进的预训练模型。

## 🚀 核心功能
- **多模型支持**: 集成 TextCNN, CNN+GRU+Attention 以及 BERT+CNN 模型。
- **多任务学习**: 同时进行谣言分类与立场检测（Stance Detection）。
- **传播分析**: 支持社交媒体传播关系树（Propagation Tree）特征提取。
- **数据增强**: 内置基于 LLM（通义千问）的数据增强模块，支持语义变换与立场生成。
- **原型系统**: 提供基于 Streamlit 的可视化交互界面，实现实时检测。

## 📂 项目结构
项目经过重构与精简，结构如下：
```text
rumor_detection/
├── app/                # Streamlit 可视化原型系统
├── data/               # 数据集说明与格式示例 (原始大数据不上传)
├── docker/             # Docker 部署配置文件
├── docs/               # 项目文档、研究计划与开发日志
├── models/             # 模型定义 (BERT, TextCNN, GNN等) 及训练好的权重
├── reports/            # 汇报文档、中期报告及 PPT (含归档)
├── scripts/            # 核心执行脚本
│   ├── training/       # 训练脚本 (BERT, TextCNN, CNN-GRU-Attn, 消融实验)
│   ├── augment_test_data_fast.py # 异步提速的虚拟节点生成脚本
│   ├── process_crawled.py    # 原始爬虫数据处理
│   ├── prepare_test_data.py  # 测试数据划分与准备
│   └── test_all_models.py    # 多模型横向评估对比
├── utils/              # 工具函数 (数据增强、爬虫、传播树提取等)
└── requirements.txt    # 项目依赖
```

## 📊 数据集
详细的数据格式与获取方式请参考 [data/README.md](./data/README.md)。
- **主要来源**: THU Rumor, CED Dataset, PHEME, Twitter15/16.
- **标注体系**: 谣言/真实/未证实，以及支持/反对/中立立場。

## 🛠️ 快速上手

### 1. 环境准备
```bash
pip install -r requirements.txt
```

### 2. 模型训练
进入 `scripts/training/` 目录运行对应的训练脚本：
```bash
# 训练先进的 BERT+CNN 多任务模型
python scripts/training/train_bert.py

# 训练轻量级的 TextCNN 模型
python scripts/training/train_textcnn.py
```

### 3. 模型评估
```bash
python scripts/evaluate.py
# 或对比所有模型
python scripts/test_all_models.py
```

### 4. 运行原型系统
```bash
streamlit run app/streamlit_app.py
```

## 📝 许可证
[MIT License](LICENSE)
