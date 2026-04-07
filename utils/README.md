# 工具目录

本目录用于存放数据清洗、特征提取等工具类脚本。

## 目录结构

```
utils/
├── __init__.py            # 工具包初始化
├── data_preprocessing.py  # 数据预处理工具
├── feature_extraction.py  # 特征提取工具
├── text_cleaner.py        # 文本清洗工具
├── evaluator.py           # 评估工具
└── README.md
```

## 工具说明

### data_preprocessing.py

数据预处理工具：
- 数据加载 (CSV, JSON, TXT)
- 数据清洗
- 数据划分 (训练/验证/测试)
- 数据平衡处理

### feature_extraction.py

特征提取工具：
- TF-IDF特征提取
- 词袋模型特征
- 词嵌入特征
- 情感特征

### text_cleaner.py

文本清洗工具：
- HTML标签去除
- 特殊字符处理
- 中文分词 (Jieba)
- 停用词过滤
- 文本规范化

### evaluator.py

评估工具：
- 评估指标计算
- 混淆矩阵生成
- ROC曲线绘制
- 评估报告生成

## 使用示例

### 数据预处理

```python
from utils.data_preprocessing import load_data, clean_data, split_data

# 加载数据
df = load_data('data/raw/rumor.csv')

# 清洗数据
df = clean_data(df, remove_html=True, remove_emoji=True)

# 划分数据
train_df, val_df, test_df = split_data(df, train_ratio=0.8)
```

### 特征提取

```python
from utils.feature_extraction import extract_tfidf_features

# 提取TF-IDF特征
X_train, vectorizer = extract_tfidf_features(train_texts)
X_test = vectorizer.transform(test_texts)
```

### 文本清洗

```python
from utils.text_cleaner import clean_text, segment_text

# 清洗文本
cleaned = clean_text("这是一条<html>测试</html>新闻")

# 中文分词
segmented = segment_text("这是一条测试新闻")
# 输出: ['这', '是', '一条', '测试', '新闻']
```

## 依赖

工具脚本依赖以下库：
- pandas
- numpy
- jieba
- re (内置)
- sklearn

请确保已安装 `requirements.txt` 中的所有依赖。
