# CLAUDE.md — 谣言检测毕业设计项目

> 本文件供 Claude Code 快速理解项目背景，避免重复解释。读完即可开始工作。

---

## 项目一句话定位

基于"极早期冷启动场景"的谣言检测系统。核心创新：用 LLM（Qwen API）生成**多立场虚拟回复**，补全传播树在谣言爆发初期（≤5条真实回复）的结构稀疏问题，再送入 Tree-LSTM 进行分类。

---

## 目录结构（只列关键文件）

```
E:\rumor_detection\
├── CLAUDE.md                        # 本文件
│
├── models/
│   ├── propagation_tree.py          # ★ 核心：MultiRelationPropagationTree + Tree-LSTM
│   ├── bert_cnn.py                  # BERT+CNN 文本编码器
│   ├── multi_task.py                # 多任务学习框架（谣言分类 + 立场检测）
│   └── best_optimized_model.pth     # 当前最佳权重（CNN+GRU+Attention，87.60%）
│
├── utils/
│   ├── propagation_tree.py          # PropagationTreeBuilder（NetworkX）
│   ├── data_augmentation.py         # LLMDataAugmenter，含 change_stance()
│   ├── early_stage_simulator.py     # ★ 新建：极早期截断 + 虚拟节点挂载
│   └── crawler/cleaner.py           # 微博数据清洗
│
├── scripts/
│   ├── augment_test_data.py         # ★ 改造中：Qwen 多立场增强主脚本
│   ├── prepare_test_data.py         # 数据集划分（85/7/8）
│   └── training/                    # 训练脚本目录
│       ├── train_bert.py            # BERT 多任务训练（当前主力）
│       ├── train_cnn_gru_attention.py  # CNN+GRU+Attention（87.60%，最佳权重来源）
│       └── train_textcnn.py         # TextCNN 基线（73%）
│
├── data/
│   ├── processed_crawled.json       # 主数据（见格式A）
│   ├── weibo1_rumor.tsv             # 基础训练集（Label\tContent）
│   ├── propagation_trees.json       # 传播树（见格式C）
│   ├── augmented_qwen.json          # LLM增强输出（见格式D）
│   └── .aug_cache/                  # Streamlit 缓存目录（自动生成）
│
├── app/
│   └── streamlit_app.py             # 演示系统入口
│
├── train_optimized.py               # 当前主训练脚本
└── evaluate.py                      # 评估脚本
```

---

## 数据格式（完整定义，勿重复询问）

### A. `processed_crawled.json` — 主数据
```json
[{
  "id": "123456789",
  "content": "正文内容",
  "label": "辟谣",        // 枚举: 辟谣 | 真实 | 虚假 | 未证实
  "stance": "支持",       // 枚举: 支持 | 反对 | 中立
  "source": "新浪微博",
  "timestamp": "2024-04-07",
  "user_id": "u123",
  "repost_count": 120
}]
```

### B. `weibo1_rumor.tsv` — 基础训练
```
1\t这是一个虚假消息     // 1=谣言, 0=真实
```

### C. `propagation_trees.json` — 传播树（模型直接消费）
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

### D. `augmented_qwen.json` — LLM增强输出
```json
{
  "original": "原始文本",
  "augmented": "改写文本",
  "augmentation_type": "multi_stance_llm",
  "label": "辟谣",
  "stance": "mixed",
  "source": "qwen_virtual_replies",
  "original_label": "辟谣",
  "virtual_children": [                        // ★ 新增字段
    {"id": "v_0", "text": "...", "time": "0.3h", "stance": "支持",  "is_virtual": true},
    {"id": "v_1", "text": "...", "time": "0.5h", "stance": "反对",  "is_virtual": true},
    {"id": "v_2", "text": "...", "time": "0.8h", "stance": "中立",  "is_virtual": true},
    {"id": "v_3", "text": "...", "time": "1.1h", "stance": "支持",  "is_virtual": true},
    {"id": "v_4", "text": "...", "time": "1.4h", "stance": "反对",  "is_virtual": true},
    {"id": "v_5", "text": "...", "time": "1.7h", "stance": "中立",  "is_virtual": true}
  ]
}
```

---

## 核心模型接口（避免重复查文件）

### `MultiRelationPropagationTree`（`models/propagation_tree.py`）
```python
model = MultiRelationPropagationTree(
    embedding_dim=768,   # BERT输出维度
    hidden_dim=256,
    num_relations=3,     # 0=转发, 1=评论, 2=引用
    pooling='attention'
)

# tree_structure 格式：
tree_structure = {
    'adjacency': [[child_idx, ...], ...],   # 每个节点的子节点索引列表
    'relation_types': [[rel_id, ...], ...], # 对应关系类型
    'root': 0,
    'virtual_flags': [False, True, ...]     # ★ 新增：标记虚拟节点
}

output = model(node_embeddings, tree_structure, relation_counts)
# node_embeddings: (batch, num_nodes, 768)
# output: (batch, hidden_dim)
```

### 联合损失函数（`models/multi_task.py`）
```python
ALPHA = 0.5   # 立场损失权重
BETA  = 0.3   # 虚拟节点立场损失权重（消融实验调此值：0, 0.1, 0.3, 0.5）

total_loss = rumor_loss + ALPHA * stance_loss + BETA * virtual_stance_loss
# virtual_stance_loss 仅对 is_virtual=True 的节点计算，其余 mask 掉
```

---

## 当前改造任务清单（按优先级）

| # | 文件 | 状态 | 说明 |
|---|------|------|------|
| 1 | `scripts/augment_test_data.py` | 🔴 进行中 | 重构为多立场约束 JSON 输出，输出含 `virtual_children` |
| 2 | `utils/early_stage_simulator.py` | 🔴 新建 | 截断传播树至极早期（depth≤2, nodes≤5），挂载虚拟节点 |
| 3 | `models/propagation_tree.py` | 🟡 改造 | `RelationAwareTreeLSTMCell` 加 `virtual_mask` 权重衰减（系数0.7） |
| 4 | `models/multi_task.py` | 🟡 改造 | 加入 `virtual_stance_loss`，`is_virtual` 字段做 mask |
| 5 | `app/streamlit_app.py` | 🟢 收尾 | 加文件缓存（`data/.aug_cache/`），避免答辩卡顿 |

---

## API 与环境

```python
# Qwen API
API_KEY = "sk-2ddddb50a0f84f01a5b155afb28de024"
BASE_URL = "https://dashscope.aliyuncs.com/..."   # DashScope 接口

# 硬件
GPU = "RTX 3060 Laptop, 6GB VRAM"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 路径（Windows）
PROJECT_ROOT = "E:/rumor_detection"
DATA_DIR     = "E:/rumor_detection/data"
```

---

## Qwen Prompt 规范（核心创新，不要改动格式）

```python
MULTI_STANCE_PROMPT = """你是社交媒体用户行为模拟器。
给定以下微博内容，请生成6条回复，严格按JSON输出，不要任何多余文字。
要求：支持2条、反对2条、中立2条，立场必须均衡。

微博内容：{content}

输出格式：
{{"comments": [
  {{"stance": "支持", "text": "...", "time": "0.3h"}},
  {{"stance": "反对", "text": "...", "time": "0.5h"}},
  {{"stance": "中立", "text": "...", "time": "0.8h"}},
  {{"stance": "支持", "text": "...", "time": "1.1h"}},
  {{"stance": "反对", "text": "...", "time": "1.4h"}},
  {{"stance": "中立", "text": "...", "time": "1.7h"}}
]}}"""

# 校验规则：解析后必须满足 {"支持","反对","中立"} ⊆ set(stances)，否则重试（最多2次）
```

---

## 数据集规模（不要重复统计）

| 数据集 | 语言 | 条数 |
|--------|------|------|
| 清华微博谣言 | 中文 | 31,669 |
| CED_Dataset | 中文 | 3,387 |
| PHEME | 英文 | 5,447 |
| LIAR | 英文 | 12,800 |
| Twitter15/16 | 英文 | 2,308 |
| 爬取微博 | 中文 | 361 |
| **合计** | — | **~56,000** |

---

## 常见注意事项

- `propagation_trees.json` 迭代方式视实际格式而定（可能是 list 也可能是 dict），改代码前先 `print(type(data))` 确认
- 虚拟节点 `is_virtual=True` 字段必须在整个数据流中完整传递，不要在任何中间处理步骤丢失
- Windows 路径用 `os.path.join()` 或 `pathlib.Path`，不要硬编码正斜杠
- Streamlit 缓存目录 `data/.aug_cache/` 已加入 `.gitignore`，不会上传

---

*最后更新：2026-04-07*