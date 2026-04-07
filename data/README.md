# 数据集说明 (Dataset Documentation)

本项目的数据存放在 `data/` 目录下（由于文件体积较大，原始数据未上传至 GitHub）。以下是数据结构的详细说明、字段含义及获取方式。

## 1. 目录结构与下载链接

| 数据集名称 | 说明 | 获取途径 / 下载链接 |
| :--- | :--- | :--- |
| **THU Rumor** | 清华中文谣言数据集 (~3万条) | [GitHub/thunlp](https://github.com/thunlp/Chinese_Rumor_Dataset) |
| **CED Dataset** | 综合中文谣言数据集 (Weibo) | [GitHub/thunlp/CED](https://github.com/thunlp/ChineseRumorDataset) |
| **PHEME** | 突发事件谣言数据集 (5大事件) | [Figshare/PHEME](https://figshare.com/articles/dataset/PHEME_dataset_for_rumour_detection_and_veracity_classification/6392078) |
| **Twitter15/16** | 包含传播树结构的社交数据 | [Ma et al. ACL 2017](https://www.dropbox.com/s/7ew0rlmueoxua90/Rumor.zip?dl=0) |
| **LIAR** | 政治新闻真实性验证数据集 | [PapersWithCode/LIAR](https://paperswithcode.com/dataset/liar) |

## 2. 核心数据格式详解

### A. 微博预处理数据 (`processed_crawled.json`)
这是爬虫获取并经过 `process_crawled.py` 转换后的标准格式：
```json
[
  {
    "id": "123456789",          // 微博唯一ID
    "content": "正文内容...",    // 文本正文
    "label": "辟谣",             // 标签: [辟谣, 真实, 虚假, 未证实]
    "stance": "支持",           // 立场: [支持, 反对, 中立]
    "source": "新浪微博",        // 来源平台
    "timestamp": "2024-04-07",  // 发布时间
    "user_id": "u123",          // 用户ID
    "repost_count": 120         // 转发数
  }
]
```

### B. 基础微博数据集 (`weibo1_rumor.tsv`)
简单的 Tab 分隔格式，用于基础 TextCNN 训练：
- **格式**: `Label \t Content`
- **示例**: `1 \t 这是一个虚假消息的例子` (1=谣言, 0=真实)

### C. 传播树数据 (`propagation_trees.json`)
用于图神经网络（GNN）或传播模型：
```json
{
  "root_id": {
    "text": "初始发布内容",
    "children": [
      {"id": "c1", "text": "转发内容1", "time": "0.5h"},
      {"id": "c2", "text": "转发内容2", "time": "1.2h"}
    ]
  }
}
```

### D. LLM 增强数据 (`augmented_qwen.json`)
由 `augment_test_data.py` 生成，包含语义变换后的版本：
- `original`: 原始文本
- `transformed`: 改写后的文本（支持/反对/中立/简化/详细等）
- `label`: 保持原始标签不变

## 3. 数据准备流程
1. **基础训练**: 使用 `weibo1_rumor.tsv`。
2. **多任务/高级训练**: 使用 `processed_crawled.json`。
3. **传播模型**: 提取 `rumor_detection_acl2017` 中的关系构建 `propagation_trees.json`。
4. **测试集扩充**: 运行 `scripts/augment_test_data.py` 生成 `augmented_qwen.json`。
