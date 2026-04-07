# -*- coding: utf-8 -*-
"""
构建 CED Dataset 中文传播树数据集

数据格式（确认自实际文件）：
  original-microblog/<idx>_<mid>_<uid>.json
    {"text": "原始帖子文本", "user": {...}, "time": ..., ...}

  rumor-repost/<idx>_<mid>_<uid>.json  /  non-rumor-repost/<idx>_<mid>_<uid>.json
    [
      {"mid": "yC8Kt9U3N", "text": "转发内容", "date": "2012-09-16 15:05:11",
       "uid": "...", "parent": "<父mid或空>", "kids": []},
      ...
    ]

输出：
  data/ced_full.json            — 完整传播树
  data/ced_early.json           — 只保留前3条转发（极早期）
  data/ced_early_augmented.json — 极早期 + 从 augmented_qwen.json 挂载虚拟节点
"""

import os
import sys
import json

# Windows stdout 编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ─────────────────────── 路径配置 ───────────────────────

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR     = os.path.join(PROJECT_ROOT, 'data')
CED_BASE     = os.path.join(DATA_DIR, 'Chinese_Rumor_Dataset', 'CED_Dataset')

RUMOR_REPOST_DIR     = os.path.join(CED_BASE, 'rumor-repost')
NON_RUMOR_REPOST_DIR = os.path.join(CED_BASE, 'non-rumor-repost')
ORIGINAL_DIR         = os.path.join(CED_BASE, 'original-microblog')

OUT_FULL      = os.path.join(DATA_DIR, 'ced_full.json')
OUT_EARLY     = os.path.join(DATA_DIR, 'ced_early.json')
OUT_EARLY_AUG = os.path.join(DATA_DIR, 'ced_early_augmented.json')
AUG_QWEN_PATH = os.path.join(DATA_DIR, 'augmented_qwen.json')

EARLY_K = 3   # 极早期保留的最多转发数

# ─────────────────────── 工具函数 ───────────────────────

def read_json_auto(path: str):
    """自动检测编码读取 JSON 文件，失败返回 None"""
    for enc in ('utf-8', 'utf-8-sig', 'gbk', 'latin-1'):
        try:
            with open(path, 'r', encoding=enc) as f:
                return json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    print(f"  [警告] 无法读取文件（编码/格式错误），跳过: {os.path.basename(path)}")
    return None


def clean_text(text) -> str:
    if not text or not isinstance(text, str):
        return ""
    return text.strip()


# ─────────────────────── 第一步：打印目录树 ───────────────────────

print("=" * 60)
print("CED_Dataset 目录结构")
print("=" * 60)
for dirpath, dirnames, filenames in os.walk(CED_BASE):
    # 跳过 .DS_Store 等隐藏目录
    dirnames[:] = [d for d in dirnames if not d.startswith('.')]
    depth = dirpath.replace(CED_BASE, '').count(os.sep)
    indent = '  ' * depth
    print(f"{indent}{os.path.basename(dirpath)}/")
    if depth < 1:
        sub_indent = '  ' * (depth + 1)
        json_files = [f for f in filenames if f.endswith('.json')]
        if json_files:
            print(f"{sub_indent}[{len(json_files)} 个 .json 文件]  示例: {json_files[0]}")

print()

# 打印任意一个 rumor-repost 文件全部内容
sample_file = None
for f in os.listdir(RUMOR_REPOST_DIR):
    if f.endswith('.json'):
        sample_file = os.path.join(RUMOR_REPOST_DIR, f)
        break

if sample_file:
    print(f"── rumor-repost 示例文件: {os.path.basename(sample_file)}")
    data = read_json_auto(sample_file)
    if data:
        print(f"   类型: {type(data).__name__}  长度: {len(data) if isinstance(data, list) else 'N/A'}")
        print("   全部内容（前5条）：")
        items = data[:5] if isinstance(data, list) else [data]
        print(json.dumps(items, ensure_ascii=False, indent=2))
print()

# ─────────────────────── 第二步：构建传播树 ───────────────────────

print("=" * 60)
print("构建传播树数据集")
print("=" * 60)

# 构建 original-microblog 文件名索引（basename -> path）
orig_index = {}
for fname in os.listdir(ORIGINAL_DIR):
    if fname.endswith('.json') and not fname.startswith('.'):
        orig_index[fname] = os.path.join(ORIGINAL_DIR, fname)

print(f"original-microblog: {len(orig_index)} 个文件")
print(f"rumor-repost:       {len([f for f in os.listdir(RUMOR_REPOST_DIR) if f.endswith('.json')])} 个文件")
print(f"non-rumor-repost:   {len([f for f in os.listdir(NON_RUMOR_REPOST_DIR) if f.endswith('.json')])} 个文件")
print()

# ─── 遍历两个 repost 目录 ───

def build_tree_from_dir(repost_dir: str, label: int):
    """
    遍历一个 repost 目录，构建 {root_id: tree_dict} 列表。

    Args:
        repost_dir: rumor-repost 或 non-rumor-repost 目录
        label: 1=谣言, 0=非谣言

    Returns:
        trees: dict { filename_stem: tree_entry }
        skip_count: 跳过数
    """
    trees = {}
    skip_count = 0

    for fname in sorted(os.listdir(repost_dir)):
        if not fname.endswith('.json') or fname.startswith('.'):
            continue

        # 查找对应的 original 文件（相同文件名）
        orig_path = orig_index.get(fname)
        if orig_path is None:
            print(f"  [警告] original 文件缺失，跳过: {fname}")
            skip_count += 1
            continue

        orig_data = read_json_auto(orig_path)
        if orig_data is None:
            skip_count += 1
            continue

        root_text = clean_text(orig_data.get('text', ''))
        if not root_text:
            skip_count += 1
            continue

        repost_data = read_json_auto(os.path.join(repost_dir, fname))
        if repost_data is None or not isinstance(repost_data, list):
            skip_count += 1
            continue

        # 过滤有文本的转发，按 date 排序（若有），保留 order
        valid_reposts = []
        for item in repost_data:
            t = clean_text(item.get('text', ''))
            if t:
                valid_reposts.append({
                    'id':   item.get('mid', ''),
                    'text': t,
                    'date': item.get('date', ''),
                })
        # 按时间升序（date 字符串可直接比较）
        valid_reposts.sort(key=lambda x: x['date'])
        # 添加 order 字段
        children = []
        for i, r in enumerate(valid_reposts, 1):
            children.append({
                'id':    r['id'],
                'text':  r['text'],
                'order': i,
            })

        root_id = os.path.splitext(fname)[0]   # 文件名去掉 .json
        trees[root_id] = {
            'text':     root_text,
            'label':    label,
            'children': children,
        }

    return trees, skip_count

print("处理 rumor-repost（label=1）...")
rumor_trees, rumor_skip = build_tree_from_dir(RUMOR_REPOST_DIR, label=1)
print(f"  成功: {len(rumor_trees)}  跳过: {rumor_skip}")

print("处理 non-rumor-repost（label=0）...")
non_rumor_trees, nr_skip = build_tree_from_dir(NON_RUMOR_REPOST_DIR, label=0)
print(f"  成功: {len(non_rumor_trees)}  跳过: {nr_skip}")

all_trees = {}
all_trees.update(rumor_trees)
all_trees.update(non_rumor_trees)
print(f"\n合并后总计: {len(all_trees)} 条")

# ─────────────────────── 生成 ced_full.json ───────────────────────

print("\n[1/3] 保存 ced_full.json ...")
with open(OUT_FULL, 'w', encoding='utf-8') as f:
    json.dump(all_trees, f, ensure_ascii=False, indent=2)
print(f"  已保存: {OUT_FULL}")

# ─────────────────────── 生成 ced_early.json ───────────────────────

print(f"\n[2/3] 生成 ced_early.json（前 {EARLY_K} 条转发）...")
early_trees = {}
for root_id, tree in all_trees.items():
    early_trees[root_id] = {
        'text':     tree['text'],
        'label':    tree['label'],
        'children': tree['children'][:EARLY_K],
    }

with open(OUT_EARLY, 'w', encoding='utf-8') as f:
    json.dump(early_trees, f, ensure_ascii=False, indent=2)
print(f"  已保存: {OUT_EARLY}")

# ─────────────────────── 生成 ced_early_augmented.json ───────────────────────

print(f"\n[3/3] 生成 ced_early_augmented.json（挂载虚拟节点）...")

# 加载 augmented_qwen.json
aug_index = {}
if os.path.exists(AUG_QWEN_PATH):
    with open(AUG_QWEN_PATH, 'r', encoding='utf-8') as f:
        aug_data = json.load(f)
    for item in aug_data:
        key = item.get('original', '')[:50]
        if key:
            aug_index[key] = item.get('virtual_children', [])
    print(f"  augmented_qwen.json: {len(aug_index)} 条索引")
else:
    print(f"  [警告] 未找到 {AUG_QWEN_PATH}，将生成无虚拟节点版本")

aug_trees = {}
attach_count = 0

for root_id, tree in early_trees.items():
    root_text = tree['text']
    virtual_children = aug_index.get(root_text[:50], [])

    # 将 virtual_children 转换为统一格式
    virt_nodes = []
    for vc in virtual_children:
        virt_nodes.append({
            'id':         vc.get('id', ''),
            'text':       vc.get('text', ''),
            'order':      vc.get('time', ''),   # 用 time 作为顺序标识
            'stance':     vc.get('stance', '中立'),
            'is_virtual': True,
        })

    aug_trees[root_id] = {
        'text':             root_text,
        'label':            tree['label'],
        'children':         tree['children'],      # 真实早期转发
        'virtual_children': virt_nodes,            # LLM 生成虚拟节点
    }

    if virt_nodes:
        attach_count += 1

with open(OUT_EARLY_AUG, 'w', encoding='utf-8') as f:
    json.dump(aug_trees, f, ensure_ascii=False, indent=2)
print(f"  已保存: {OUT_EARLY_AUG}")

# ─────────────────────── 统计信息 ───────────────────────

print()
print("=" * 60)
print("统计信息")
print("=" * 60)

total = len(all_trees)
rumor_cnt = sum(1 for t in all_trees.values() if t['label'] == 1)
non_rumor_cnt = total - rumor_cnt

print(f"总条数:          {total}")
print(f"谣言(label=1):   {rumor_cnt}  ({rumor_cnt/max(total,1)*100:.1f}%)")
print(f"非谣言(label=0): {non_rumor_cnt}  ({non_rumor_cnt/max(total,1)*100:.1f}%)")

# 平均转发数
full_avg = sum(len(t['children']) for t in all_trees.values()) / max(total, 1)
early_avg = sum(len(t['children']) for t in early_trees.values()) / max(total, 1)
print(f"\nfull  平均转发数: {full_avg:.1f}")
print(f"early 平均转发数: {early_avg:.1f}  (≤{EARLY_K}，截断有效)")

# 有无转发分布
has_children = sum(1 for t in all_trees.values() if t['children'])
print(f"\n有转发记录的条数:  {has_children} / {total} ({has_children/max(total,1)*100:.1f}%)")

print(f"\n成功挂载虚拟节点: {attach_count} / {len(aug_trees)} 条")

print()
print("=" * 60)
print("完成！输出文件：")
print(f"  ced_full.json            ({total} 条)")
print(f"  ced_early.json           ({len(early_trees)} 条，前{EARLY_K}条转发)")
print(f"  ced_early_augmented.json ({len(aug_trees)} 条，含虚拟节点)")
print("=" * 60)
