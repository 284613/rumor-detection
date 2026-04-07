# 数据集说明 (Dataset Documentation)

本项目的数据存放在 `data/` 目录下（由于文件体积较大，原始数据未上传至 GitHub）。以下是数据结构的详细说明：

## 1. 目录结构
```text
data/
├── Chinese_Rumor_Dataset/      # 清华中文谣言数据集 (~3万条)
├── ChineseRumorDataset-main/   # 综合中文谣言数据集 (CHEF, COVID19等)
├── pheme-rnr-dataset/         # PHEME 突发事件谣言数据集 (英文)
├── rumor_detection_acl2017/    # Twitter15/16 数据集 (包含传播树结构)
├── processed_crawled.json      # 爬取并经过预处理的微博数据
├── weibo1_rumor.tsv            # 基础微博谣言数据集
├── augmented_qwen.json         # 使用千问 LLM 增强后的数据集
└── propagation_trees.json      # 提取的社交媒体传播树结构数据 (大型文件)
```

## 2. 核心数据格式示例

### 微博预处理数据 (`processed_crawled.json`)
```json
[
  {
    "content": "微博正文内容...",
    "label": "辟谣",
    "stance": "支持",
    "source": "新浪微博",
    "timestamp": "2024-04-07"
  }
]
```

### 传播树数据 (`propagation_trees.json`)
包含推文之间的转发关系，用于构建图模型或树模型：
- **Root**: 原始发布内容
- **Children**: 转发/评论内容及用户关系

## 3. 如何获取数据
- **微博数据**: 通过 `scripts/process_crawled.py` 处理爬虫获取。
- **增强数据**: 通过 `scripts/augment_test_data.py` 调用大模型生成。
- **公开数据集**: 请参考 `docs/dataset-resources.md` 中的链接进行下载。
