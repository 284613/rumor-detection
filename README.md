# 社交媒体恶意谣言识别的研究与实现 (Rumor Detection)

本项目旨在构建一个面向**极早期冷启动场景**的社交媒体谣言检测系统。核心创新：利用 LLM（MiniMax API）生成**多立场虚拟回复**，补全传播树在谣言爆发初期（≤3条真实回复）的结构稀疏问题，结合多任务学习（谣言分类 + 立场检测）提升极早期检测准确率。

## 🚀 核心功能
- **多模型支持**: 集成 TextCNN, CNN+GRU+Attention 以及 BERT+CNN 多任务模型。
- **多任务学习**: 同时进行谣言分类与立场检测（Stance Detection），虚拟节点立场作为辅助监督信号。
- **传播树分析**: 基于 Tree-LSTM 的传播关系树特征提取，支持多关系类型（真实转发/虚拟节点/引用）及虚拟节点衰减（0.7）。
- **LLM 数据增强**: 基于 MiniMax API 生成多立场（支持/反对/中立）虚拟回复，每棵树挂载6条虚拟子节点。
- **消融实验框架**: 四组对比实验（完整树/早期截断/LLM增强/β消融），验证各组件贡献。
- **原型系统**: 提供基于 Streamlit 的可视化交互界面，实现实时检测。

## 📂 项目结构
```text
rumor_detection/
├── app/                # Streamlit 可视化原型系统
├── data/               # 数据集（CED_Dataset、增强数据、消融结果等）
├── docker/             # Docker 部署配置文件
├── docs/               # 项目文档、研究计划与开发日志
├── models/             # 模型定义 (BERT+CNN, Tree-LSTM, 多任务框架) 及权重
├── reports/            # 汇报文档、中期报告及 PPT
├── scripts/            # 核心执行脚本
│   ├── training/       # 训练脚本 (BERT, TextCNN, CNN-GRU-Attn, 消融实验)
│   ├── augment_test_data.py  # MiniMax 多立场虚拟回复增强（processed_crawled 用）
│   ├── augment_ced_data.py   # CED 专用 LLM 增强（生成 ced_early_augmented.json）
│   ├── build_ced_propagation.py # 从 CED_Dataset 构建传播树数据集
│   ├── prepare_test_data.py  # 测试数据划分与准备
│   └── test_all_models.py    # 多模型横向评估对比
├── utils/              # 工具函数 (数据增强、早期模拟器、传播树构建等)
└── requirements.txt    # 项目依赖
```

## 📊 数据集

| 数据集 | 语言 | 规模 | 用途 |
|--------|------|------|------|
| CED_Dataset | 中文 | 3,387棵树 (谣言1538 + 非谣言1849) | 主实验数据，avg 227条转发/树 |
| 清华微博谣言 | 中文 | 31,669 | 辅助训练 |
| PHEME | 英文 | 5,447 | 跨语言对比 |
| Twitter15/16 | 英文 | 2,308 | 跨语言对比 |

详细格式请参考 [data/README.md](./data/README.md)。

## 📈 消融实验结果

> 首轮结果（2026-04-08，Colab，3 epochs）。C/D 存在数据加载问题（虚拟节点=0），待修复后重跑。

| 实验 | 配置 | Acc(%) | F1-谣言 | F1-真实 |
|------|------|--------|---------|---------|
| A | 完整传播树 (baseline) | 98.39 | 0.9918 | 0.6233 |
| B | 极早期截断 (≤3回复) | 79.88 | 0.7866 | 0.8096 |
| C | 早期 + LLM增强 (β=0.3) | 80.03 | 0.7800 | 0.8172 |
| D | 早期 + LLM增强 (β=0) | 78.88 | 0.7675 | 0.8065 |

**待修复**: CED 虚拟节点数据未生成、stance loss 需仅对虚拟节点计算、实验A 需加类别权重平衡。

## 🛠️ 快速上手

### 1. 环境准备
```bash
pip install -r requirements.txt
```

### 2. 数据准备
```bash
# 从 CED_Dataset 构建传播树
python scripts/build_ced_propagation.py

# 对 CED 早期树生成 LLM 虚拟回复（需 MiniMax API Key）
python scripts/augment_ced_data.py
```

### 3. 模型训练
```bash
# BERT+CNN 多任务模型
python scripts/training/train_bert.py

# 消融实验（四组对比）
python scripts/training/run_ablation.py
```

### 4. 运行原型系统
```bash
streamlit run app/streamlit_app.py
```

## 📝 许可证
[MIT License](LICENSE)
