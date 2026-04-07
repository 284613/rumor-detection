# 先进谣言检测模型

本目录包含基于文献的先进谣言检测模型实现。

## 模型架构

### 1. 多关系传播树模块 (`propagation_tree.py`)

**核心特性：**
- **Tree-LSTM**: 使用儿童求和Tree-LSTM (Child-Sum Tree-LSTM) 处理树结构
- **关系感知**: 支持多种关系类型（转发、评论、引用）
- **多池化策略**: 支持根节点、最大池化、平均池化、注意力池化

**组件：**
- `TreeLSTMCell`: 标准Tree-LSTM单元
- `RelationAwareTreeLSTMCell`: 关系感知Tree-LSTM单元
- `PropagationTreeEncoder`: 传播树编码器
- `MultiRelationPropagationTree`: 多关系传播树模型
- `SimplePropagationEncoder`: 简化版传播树编码器（使用图卷积）

### 2. BERT + CNN 模型 (`bert_cnn.py`)

**核心特性：**
- **BERT编码器**: 使用bert-base-chinese进行文本编码
- **多尺度CNN**: 使用多种卷积核大小(2,3,4,5)提取不同粒度特征
- **条件融合**: 支持门控、拼接、双线性、注意力四种融合方式

**组件：**
- `BERTTextEncoder`: BERT文本编码器
- `CNNFeatureExtractor`: 多尺度CNN特征提取器
- `ConditionFusion`: 条件融合模块
- `BERTCNNModel`: BERT+CNN模型

### 3. 多任务学习模型 (`multi_task.py`)

**核心特性：**
- **共享编码层**: 共享BERT/Transformer编码器
- **双任务头**: 谣言分类 + 立场检测
- **联合损失**: 支持加权求和、动态权重、不确定性加权

**组件：**
- `SharedBERTEncoder`: 共享BERT编码器
- `MultiTaskLoss`: 多任务损失函数
- `MultiTaskModel`: 多任务学习模型
- `MultiTaskTrainer`: 多任务训练器

## 训练脚本 (`train_advanced.py`)

### 使用方法

```bash
# 基本用法
python train_advanced.py

# 完整参数
python train_advanced.py \
    --model_type simple \
    --bert_model bert-base-chinese \
    --epochs 10 \
    --batch_size 16 \
    --learning_rate 2e-5 \
    --multi_task
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model_type` | 模型类型 (simple/bert) | simple |
| `--bert_model` | BERT模型名称 | bert-base-chinese |
| `--epochs` | 训练轮数 | 10 |
| `--batch_size` | 批大小 | 16 |
| `--learning_rate` | 学习率 | 2e-5 |
| `--multi_task` | 启用多任务学习 | True |

## 数据增强 (`utils/llm_augment.py`)

使用千问(Qwen) API进行数据增强。

### 增强类型

1. **paraphrase**: 文本改写 - 生成同义表述
2. **stance**: 立场改变 - 支持/反对/中立
3. **context**: 扩展上下文 - 添加背景信息
4. **argument**: 生成反驳/赞同论点

### 使用方法

```bash
# 增强数据集
python -u utils/llm_augment.py \
    --input data/cleaned_rumors.json \
    --output data/augmented_data.json \
    --max_samples 100 \
    --types paraphrase stance
```

### API配置

```bash
# 设置千问API密钥
set DASHSCOPE_API_KEY=your_api_key
```

获取API密钥: https://dashscope.console.aliyun.com/

## 环境依赖

```bash
pip install -r requirements_advanced.txt
```

## 模型输出

训练完成后，模型保存在:
- `models/best_advanced_model.pth`

包含:
- 模型权重
- 词汇表
- 配置信息

## 文献参考

1. Tai, K. S., Socher, R., & Manning, C. D. (2015). Improved semantic representations from tree-structured long short-term memory networks.
2. Ma, J., Gao, W., & Wong, K. F. (2018). Detect rumors in microblogging systems using propagation tree.
3. Zhou, K., Shu, K., & Wang, S. (2020). Beyond news contents: The role of social context for fake news detection.

## 注意事项

1. 使用BERT模型需要较大的GPU显存（建议8GB+）
2. 简单模型可以在CPU上运行
3. 传播树特征需要预先提取
4. 多任务学习通常比单任务有更好的泛化能力
