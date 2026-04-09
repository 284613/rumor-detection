# CLAUDE.md — 谣言检测毕业设计项目

> 本文件供 Claude Code 快速理解项目背景，避免重复解释。读完即可开始工作。

---

## 项目一句话定位

基于"极早期冷启动场景"的谣言检测系统。核心创新：用 LLM（Qwen API）生成**多立场虚拟回复**，补全传播树在谣言爆发初期（≤3条真实回复）的结构稀疏问题，再送入 Tree-LSTM 进行分类。

## 虚拟节点生成技术说明 (LLM Generation)

### 1. 技术来源与数据来源
- **核心模型**: **MiniMax-M2.5-highspeed** (由于 Qwen 额度耗尽，已全面切换至 MiniMax)。
- **接口协议**: Anthropic 兼容模式 (Base URL: `api.minimaxi.com/anthropic`)。
- **原始数据集**: **CED_Dataset** (综合中文谣言数据集)。
- **生成规模**: 对 CED 3387 棵树进行增强，共生成 **19,410** 个虚拟节点（跳过空文本6条，API失败146条，已缓存268条）。

### 2. 生成策略 (Prompt Design)
- **模拟角色**: `社交媒体用户行为模拟器`。
- **输入数据**: 仅输入微博原帖（root）内容。
- **立场平衡**: 强制要求生成 `[2*支持, 2*反对, 2*中立]` 的均衡立场组合，以补足谣言爆发前夕真实评论在立场上的分布缺失。
- **结构化输出**: 严格输出 JSON 格式，包含 `comments` 列表，确保能无缝挂载至 `PropagationTree`。

### 3. 数据可靠性保障
- **磁盘缓存**: 采用 `data/.aug_cache/` MD5 缓存机制（Key 为 `微博内容` 的哈希），支持断点续传。
- **自动校验**: 脚本内置立场集合校验（必须包含三类立场），校验失败会自动重试。
- **信号衰减**: 在 `RelationAwareTreeLSTMCell` 中对所有来自 MiniMax 的虚拟节点应用 **0.7** 的隐状态衰减系数。

---

## 目录结构（只列关键文件）

```
E:\rumor_detection\
├── CLAUDE.md                        # 本文件
│
├── models/
│   ├── propagation_tree.py          # ★ 核心：MultiRelationPropagationTree + Tree-LSTM
│   │                                #   RelationAwareTreeLSTMCell 已加 virtual_mask 衰减(0.7)
│   ├── bert_cnn.py                  # BERT+CNN 文本编码器
│   ├── multi_task.py                # 多任务学习框架（谣言分类 + 立场检测）
│   │                                #   含 ALPHA/BETA 常量、compute_virtual_stance_loss()
│   └── best_optimized_model.pth     # 当前最佳权重（CNN+GRU+Attention，87.60%）
│
├── utils/
│   ├── propagation_tree.py          # PropagationTreeBuilder（NetworkX）
│   ├── data_augmentation.py         # LLMDataAugmenter，含 change_stance()
│   ├── early_stage_simulator.py     # ★ 极早期截断 + 虚拟节点挂载 + batch_process_dataset()
│   └── crawler/cleaner.py           # 微博数据清洗
│
├── scripts/
│   ├── augment_test_data.py         # ★ MiniMax 多立场增强主脚本（含断点续跑、磁盘缓存）
│   ├── build_ced_propagation.py     # ★ 从 CED_Dataset 构建三份传播树数据集
│   ├── prepare_test_data.py         # 数据集划分（85/7/8）
│   └── training/
│       ├── train_bert.py            # BERT 多任务训练（当前主力）
│       ├── run_ablation.py          # ★ 消融实验脚本（A/B/C/D 四组对比）
│       ├── train_cnn_gru_attention.py  # CNN+GRU+Attention（87.60%，最佳权重来源）
│       └── train_textcnn.py         # TextCNN 基线（73%）
│
├── data/
│   ├── processed_crawled.json       # 主数据（见格式A）
│   ├── weibo1_rumor.tsv             # 基础训练集（Label\tContent）
│   ├── propagation_trees.json       # 传播树（见格式C）
│   ├── augmented_qwen.json          # LLM增强输出（见格式D），当前31条（processed_crawled用）
│   ├── ced_full.json                # ★ CED完整传播树（3387条，avg 227条转发/树）
│   ├── ced_early.json               # ★ CED极早期截断（前3条转发）
│   ├── ced_early_augmented.json     # ★ CED极早期 + virtual_children（19410个虚拟节点，已完成）
│   ├── ablation_early_real.json     # 消融实验B用（早期截断，无虚拟节点，展开行格式）
│   ├── ablation_early_augmented.json # 消融实验C/D用（含虚拟节点）
│   ├── ablation_results.json        # 消融实验结果（四组跑完后生成）
│   ├── ablation_results.csv         # 同上，CSV格式
│   └── .aug_cache/                  # Qwen API 磁盘缓存（自动生成，已gitignore）
│
├── app/
│   └── streamlit_app.py             # 演示系统入口（含 @st.cache_data 文件缓存）
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
  "virtual_children": [
    {"id": "v_0", "text": "...", "time": "0.3h", "stance": "支持",  "is_virtual": true},
    {"id": "v_1", "text": "...", "time": "0.5h", "stance": "反对",  "is_virtual": true},
    {"id": "v_2", "text": "...", "time": "0.8h", "stance": "中立",  "is_virtual": true},
    {"id": "v_3", "text": "...", "time": "1.1h", "stance": "支持",  "is_virtual": true},
    {"id": "v_4", "text": "...", "time": "1.4h", "stance": "反对",  "is_virtual": true},
    {"id": "v_5", "text": "...", "time": "1.7h", "stance": "中立",  "is_virtual": true}
  ]
}
```

### E. `ced_full.json` / `ced_early.json` — CED传播树（build_ced_propagation.py 生成）
```json
{
  "root_id": {
    "text": "原始帖子文本",
    "label": 1,
    "children": [
      {"id": "yBDVSfr2s", "text": "转发内容", "order": 1},
      ...
    ]
  }
}
```
- `label`: 1=谣言, 0=非谣言
- `ced_early.json` 同格式，但 children 最多3条
- `ced_early_augmented.json` 额外含 `"virtual_children": [...]` 字段

### F. 消融实验行格式（`ablation_early_*.json`）
```json
[
  {"root_id": "...", "label": "辟谣", "text": "节点文本", "stance": "中立", "is_virtual": false},
  {"root_id": "...", "label": "辟谣", "text": "虚拟回复", "stance": "支持", "is_virtual": true}
]
```
一条传播树展开为多行，每行一个节点。

---

## 核心模型接口（避免重复查文件）

### `MultiRelationPropagationTree`（`models/propagation_tree.py`）
```python
model = MultiRelationPropagationTree(
    embedding_dim=768,   # BERT输出维度
    hidden_dim=256,
    num_relations=3,     # 0=转发, 1=虚拟节点, 2=引用
    pooling='attention'
)

# tree_structure 格式：
tree_structure = {
    'adjacency': [[child_idx, ...], ...],   # 每个节点的子节点索引列表
    'relation_types': [[rel_id, ...], ...], # 对应关系类型（0=真实, 1=虚拟）
    'root': 0,
    'virtual_flags': [False, True, ...]     # 标记虚拟节点，用于 virtual_mask 权重衰减
}

output = model(node_embeddings, tree_structure, relation_counts)
# node_embeddings: (batch, num_nodes, 768)
# output: (batch, hidden_dim)
# 虚拟节点在 RelationAwareTreeLSTMCell 中乘以衰减系数 0.7
```

### 联合损失函数（`models/multi_task.py`）
```python
ALPHA = 0.5   # 立场损失权重
BETA  = 0.3   # 虚拟节点立场损失权重（消融实验调此值：0, 0.1, 0.3, 0.5）

total_loss = rumor_loss + ALPHA * stance_loss + BETA * virtual_stance_loss
# virtual_stance_loss 仅对 is_virtual=True 的节点计算，其余 mask 掉
# compute_virtual_stance_loss(stance_logits, stance_labels, is_virtual, criterion)
```

---

## CED_Dataset 文件格式（已确认，勿重复探查）

```
data/Chinese_Rumor_Dataset/CED_Dataset/
├── original-microblog/   [3387个json]  {"text": "...", "user": {...}, "time": ...}
├── rumor-repost/         [1538个json]  谣言转发，文件名与 original 一一对应
└── non-rumor-repost/     [1849个json]  非谣言转发

repost 文件格式（list，utf-8编码）：
[{"mid": "yBDVSfr2s", "text": "转发文本", "date": "2012-09-13 08:38:09",
  "uid": "...", "parent": "父mid或空串", "kids": [...空list...]}, ...]
```
- 文件名规律：`{idx}_{weibo_mid}_{user_id}.json`，三目录同名一一对应
- `text` 字段可能为空串（过滤掉）
- 编码统一为 utf-8

---

## 消融实验设计（`scripts/training/run_ablation.py`）

| 实验 | data_mode | beta | 说明 |
|------|-----------|------|------|
| A | `full` | 0.0 | 完整传播树 + 无增强（baseline） |
| B | `early_real` | 0.0 | 极早期截断 + 无增强 |
| C | `early_augmented` | 0.3 | 极早期截断 + LLM增强 |
| D | `early_augmented` | 0.0 | 同C但关闭虚拟损失（消融β） |

运行：`python scripts/training/run_ablation.py`
结果输出：`data/ablation_results.json` + `data/ablation_results.csv`

---

## API 与环境

```python
# MiniMax API (Token Plan)
MINIMAX_MODEL = "MiniMax-M2.5-highspeed"
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"
```
# 硬件
GPU = "RTX 3060 Laptop, 6GB VRAM"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Python
PYTHON_EXE = "C:/Users/28443/AppData/Local/Programs/Python/Python312/python.exe"

# 路径（Windows）
PROJECT_ROOT = "E:/rumor_detection"
DATA_DIR     = "E:/rumor_detection/data"
```

---

## Qwen / MiniMax Prompt 规范（核心创新，不要改动格式）

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
# 结果落盘到 data/.aug_cache/<md5>.json，断点续跑安全
```

---

## 数据集规模（不要重复统计）

| 数据集 | 语言 | 条数 | 说明 |
|--------|------|------|------|
| 清华微博谣言 | 中文 | 31,669 | rumors_v170613.json |
| CED_Dataset | 中文 | 3,387 | 谣言1538 + 非谣言1849，avg 227条转发/树 |
| PHEME | 英文 | 5,447 | |
| LIAR | 英文 | 12,800 | |
| Twitter15/16 | 英文 | 2,308 | |
| 爬取微博 | 中文 | 361 | processed_crawled.json |
| **合计** | — | **~56,000** | |

---

## 常见注意事项 & 最新进展 (2026-04-10)

- **CED 增强已完成**：`ced_early_augmented.json` 含 **19,410** 个虚拟节点（3387棵树，跳过6条空文本，API失败146条，缓存命中268条），可直接用于消融实验 C/D。
- **API 已切换至 MiniMax**：`augment_test_data.py` 使用 `anthropic` SDK + MiniMax Anthropic 兼容接口，不再调 Qwen。`scripts/augment_ced_data.py` 同理。
- **CED 标签映射陷阱**：CED 原始谣言标签为 `1`，真实为 `0`；模型训练中谣言为 `0`，真实为 `1`。`_ced_label_to_int()` 已做显式转换（`1→0, 0→1`），**切勿再次改动**，否则标签全错、准确率异常升至 100%。
- **run_ablation.py 数据源**：已切换为直接读 `ced_full/early/early_augmented.json`（嵌套树格式），不再依赖 `ablation_early_*.json` 行格式文件。
- **消融实验超参**：`BATCH_SIZE=2`（RTX 3060 6GB），`EPOCHS=5`，`EARLY_STOP_PATIENCE=2`，`MAX_LEN=100`。
- `propagation_trees.json` 迭代方式视实际格式而定（可能是 list 也可能是 dict），改代码前先 `print(type(data))` 确认。
- 虚拟节点 `is_virtual=True` 字段必须在整个数据流中完整传递，不要在任何中间处理步骤丢失。
- Windows 路径用 `os.path.join()` 或 `pathlib.Path`，不要硬编码正斜杠。
- Streamlit 缓存目录 `data/.aug_cache/` 已加入 `.gitignore`，不会上传。

---

*最后更新：2026-04-10*
