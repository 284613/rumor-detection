# 数据增强模块使用说明

## 概述

`data_augmentation.py` 提供基于大语言模型的数据增强功能，用于解决谣言检测中的小样本问题。

## 功能特性

1. **文本重写** - 生成语义相同但表达方式不同的变体
2. **立场改写** - 生成支持/反对/中立不同立场的表达
3. **批量增强** - 支持CSV数据集批量处理
4. **错误处理** - 内置重试机制和异常处理

## 依赖安装

```bash
pip install requests pandas
```

## 快速开始

### 1. 基本用法

```python
from data_augmentation import LLMDataAugmenter

# 初始化增强器
augmenter = LLMDataAugmenter(
    api_key="your-api-key",
    model="gpt-3.5-turbo"  # 可选，默认gpt-3.5-turbo
)

# 文本重写
variants = augmenter.rewrite_text("今天天气真好", num_variants=3)
print(variants)

# 立场改写
variants = augmenter.change_stance("这个消息是真的", "oppose")
print(variants)
```

### 2. 批量增强数据集

```python
# 从CSV文件增强
augmented = augmenter.augment_dataset(
    data="data/processed/train.csv",
    augmentation_factor=2,
    output_path="data/processed/augmented_train.csv"
)

# 或直接使用DataFrame
import pandas as pd
data = pd.read_csv("data/processed/train.csv")
augmented = augmenter.augment_dataset(data, augmentation_factor=2)
```

### 3. 使用环境变量

```bash
# 设置环境变量
set OPENAI_API_KEY=your-api-key
set OPENAI_MODEL=gpt-3.5-turbo
```

```python
from data_augmentation import create_augmenter_from_env

augmenter = create_augmenter_from_env()
```

### 4. 使用便捷函数

```python
from data_augmentation import augment_csv

# 一行代码增强CSV
augment_csv(
    input_path="data/processed/train.csv",
    output_path="data/processed/augmented_train.csv",
    augmentation_factor=2,
    api_key="your-api-key"
)
```

## API参考

### LLMDataAugmenter

```python
LLMDataAugmenter(
    api_key: str,              # API密钥
    model: str = "gpt-3.5-turbo",  # 模型名称
    base_url: str = "...",     # API地址
    max_retries: int = 3,      # 最大重试次数
    retry_delay: float = 1.0,  # 重试延迟(秒)
    timeout: int = 60,         # 超时时间(秒)
    temperature: float = 0.8,  # 温度参数
    max_tokens: int = 1000     # 最大token数
)
```

### 方法

- `rewrite_text(text, num_variants=5)` - 文本重写
- `change_stance(text, target_stance)` - 立场改写
- `augment_dataset(data, augmentation_factor=2)` - 批量增强

## 输出格式

增强后的数据与Weibo数据集格式兼容：

| 字段 | 类型 | 说明 |
|------|------|------|
| text | string | 文本内容 |
| label | int | 标签 (0=真实, 1=谣言) |

## 注意事项

1. API调用会产生费用，请合理设置`augmentation_factor`
2. 批量处理时会自动添加延迟，避免API速率限制
3. 建议先用少量数据测试，确认效果后再大规模增强
