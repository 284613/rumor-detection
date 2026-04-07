# -*- coding: utf-8 -*-
"""
极早期冷启动场景模拟器
功能：
1. 截断传播树至极早期（depth≤2, nodes≤5）
2. 将 augmented_qwen.json 中的 virtual_children 挂载到截断后的传播树
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ─────────────────────────── 截断逻辑 ───────────────────────────

def truncate_tree(tree: Dict, max_depth: int = 2, max_nodes: int = 5) -> Dict:
    """
    将传播树截断至极早期状态。

    Args:
        tree: 单条传播树，格式同 propagation_trees.json 的 value：
              {"text": ..., "children": [{"id":..., "text":..., "time":...}, ...]}
        max_depth: 保留的最大深度（根节点为 0）
        max_nodes: 保留的最大节点数（含根节点）

    Returns:
        截断后的树（深拷贝，不修改原数据）
    """
    import copy
    tree = copy.deepcopy(tree)
    node_count = [0]  # 用列表以便在闭包中修改

    def _truncate(node: Dict, depth: int) -> Optional[Dict]:
        if node_count[0] >= max_nodes:
            return None
        node_count[0] += 1

        if depth >= max_depth:
            node["children"] = []
            return node

        kept_children = []
        for child in node.get("children", []):
            if node_count[0] >= max_nodes:
                break
            result = _truncate(child, depth + 1)
            if result is not None:
                kept_children.append(result)

        node["children"] = kept_children
        return node

    return _truncate(tree, 0) or {"text": tree.get("text", ""), "children": []}


# ─────────────────────────── 虚拟节点挂载 ───────────────────────────

def attach_virtual_children(tree: Dict, virtual_children: List[Dict]) -> Dict:
    """
    将虚拟节点作为根节点的直接子节点挂载到截断树上。

    Args:
        tree:             截断后的传播树（dict）
        virtual_children: 来自 augmented_qwen.json 的 virtual_children 列表

    Returns:
        挂载虚拟节点后的树（in-place 修改并返回）
    """
    existing = tree.setdefault("children", [])
    for vc in virtual_children:
        child = {
            "id": vc.get("id", f"v_{len(existing)}"),
            "text": vc.get("text", ""),
            "time": vc.get("time", "0.5h"),
            "stance": vc.get("stance", "中立"),
            "is_virtual": True
        }
        existing.append(child)
    return tree


# ─────────────────────────── 树结构转模型格式 ───────────────────────────

def tree_to_model_input(tree: Dict) -> Tuple[List[str], Dict]:
    """
    将嵌套树结构转换为模型所需的 (texts, tree_structure) 格式。

    texts: 按 BFS 顺序的节点文本列表
    tree_structure: {
        'adjacency':      List[List[int]],   # 子节点索引列表
        'relation_types': List[List[int]],   # 关系类型（0=转发/评论，1=虚拟）
        'root': 0,
        'virtual_flags':  List[bool]         # True = 虚拟节点
    }
    """
    texts: List[str] = []
    adjacency: List[List[int]] = []
    relation_types: List[List[int]] = []
    virtual_flags: List[bool] = []

    # BFS
    queue = [(tree, None)]  # (node, parent_idx)
    while queue:
        node, parent_idx = queue.pop(0)
        idx = len(texts)

        texts.append(node.get("text", ""))
        adjacency.append([])
        relation_types.append([])
        virtual_flags.append(bool(node.get("is_virtual", False)))

        if parent_idx is not None:
            adjacency[parent_idx].append(idx)
            # 虚拟节点用关系类型 1，真实节点用 0
            rel = 1 if node.get("is_virtual", False) else 0
            relation_types[parent_idx].append(rel)

        for child in node.get("children", []):
            queue.append((child, idx))

    tree_structure = {
        "adjacency": adjacency,
        "relation_types": relation_types,
        "root": 0,
        "virtual_flags": virtual_flags
    }
    return texts, tree_structure


# ─────────────────────────── 批量处理入口 ───────────────────────────

def simulate_early_stage(
    propagation_trees_path: str,
    augmented_qwen_path: str,
    max_depth: int = 2,
    max_nodes: int = 5,
) -> List[Dict]:
    """
    读取传播树和增强数据，生成极早期冷启动样本列表。

    每条样本格式：
    {
        "root_id": str,
        "label": str,
        "texts": List[str],
        "tree_structure": dict,   # 含 virtual_flags
    }
    """
    prop_path = Path(propagation_trees_path)
    aug_path = Path(augmented_qwen_path)

    if not prop_path.exists():
        raise FileNotFoundError(f"传播树文件不存在: {prop_path}")
    if not aug_path.exists():
        raise FileNotFoundError(f"增强数据文件不存在: {aug_path}")

    with open(prop_path, "r", encoding="utf-8") as f:
        prop_data = json.load(f)

    with open(aug_path, "r", encoding="utf-8") as f:
        aug_data = json.load(f)

    # 以 original 文本前50字符作为索引键
    aug_index: Dict[str, Dict] = {
        item["original"][:50]: item for item in aug_data
    }

    samples = []
    # 支持 dict 格式和 list 格式
    if isinstance(prop_data, dict):
        items = prop_data.items()
    else:
        items = ((str(i), v) for i, v in enumerate(prop_data))

    for root_id, tree in items:
        # 截断至极早期
        truncated = truncate_tree(tree, max_depth=max_depth, max_nodes=max_nodes)

        # 查找对应的虚拟子节点
        root_text = tree.get("text", "")[:50]
        aug_item = aug_index.get(root_text)
        virtual_children = aug_item.get("virtual_children", []) if aug_item else []
        label = aug_item.get("label", "") if aug_item else ""

        # 挂载虚拟节点
        if virtual_children:
            attach_virtual_children(truncated, virtual_children)

        # 转换为模型输入格式
        texts, tree_structure = tree_to_model_input(truncated)

        samples.append({
            "root_id": root_id,
            "label": label,
            "texts": texts,
            "tree_structure": tree_structure,
        })

    return samples


# ─────────────────────────── 批量生成消融数据集 ───────────────────────────

def batch_process_dataset(
    propagation_trees_path: str,
    augmented_qwen_path: str,
    output_early_real: str,
    output_early_augmented: str,
    max_depth: int = 2,
    max_nodes: int = 5,
) -> None:
    """
    从传播树 + Qwen 增强数据批量生成两个消融实验数据文件。

    output_early_real:       极早期截断，无虚拟节点（实验 B/D 用）
    output_early_augmented:  极早期截断，含虚拟节点（实验 C/D 用）

    每条记录格式：
    {
        "root_id": str,
        "label": str,
        "text": str,         # 节点文本
        "stance": str,       # 立场标签（虚拟节点有）
        "is_virtual": bool
    }
    (一条传播树展开为多条记录：根节点 + 所有子节点)
    """
    prop_path = Path(propagation_trees_path)
    aug_path = Path(augmented_qwen_path)

    if not prop_path.exists():
        raise FileNotFoundError(f"传播树文件不存在: {prop_path}")

    with open(prop_path, "r", encoding="utf-8") as f:
        prop_data = json.load(f)

    aug_index: Dict[str, Dict] = {}
    if aug_path.exists():
        with open(aug_path, "r", encoding="utf-8") as f:
            aug_data = json.load(f)
        aug_index = {item["original"][:50]: item for item in aug_data}

    if isinstance(prop_data, dict):
        items = list(prop_data.items())
    else:
        items = [(str(i), v) for i, v in enumerate(prop_data)]

    real_records: List[Dict] = []
    augmented_records: List[Dict] = []

    for root_id, tree in items:
        root_text = tree.get("text", "")
        aug_item = aug_index.get(root_text[:50])
        # 优先从树本身读取 label，其次从增强数据
        label = tree.get("label", "")
        if not label and aug_item:
            label = aug_item.get("label", "")
        virtual_children = aug_item.get("virtual_children", []) if aug_item else []

        # 截断真实树
        truncated = truncate_tree(tree, max_depth=max_depth, max_nodes=max_nodes)

        # ── early_real：展开截断树的所有节点（无虚拟节点）
        def _flatten(node: Dict, is_virt: bool = False) -> List[Dict]:
            rows = [{
                "root_id": root_id,
                "label": label,
                "text": node.get("text", ""),
                "stance": node.get("stance", "中立"),
                "is_virtual": is_virt,
            }]
            for child in node.get("children", []):
                rows.extend(_flatten(child, child.get("is_virtual", False)))
            return rows

        real_records.extend(_flatten(truncated, False))

        # ── early_augmented：截断树 + 挂载虚拟节点后展开
        aug_tree = attach_virtual_children(truncated, virtual_children)
        augmented_records.extend(_flatten(aug_tree, False))

    with open(output_early_real, "w", encoding="utf-8") as f:
        json.dump(real_records, f, ensure_ascii=False, indent=2)
    print(f"[early_real]       已保存 {len(real_records)} 条 -> {output_early_real}")

    with open(output_early_augmented, "w", encoding="utf-8") as f:
        json.dump(augmented_records, f, ensure_ascii=False, indent=2)
    print(f"[early_augmented]  已保存 {len(augmented_records)} 条 -> {output_early_augmented}")


# ─────────────────────────── 快速测试 ───────────────────────────

if __name__ == "__main__":
    # 单元测试：不依赖真实数据文件
    sample_tree = {
        "text": "某地发生重大事件，伤亡情况不明",
        "children": [
            {"id": "c1", "text": "现场目击者说...", "time": "0.5h", "children": [
                {"id": "c3", "text": "更多细节", "time": "1.0h", "children": [
                    {"id": "c5", "text": "深层回复", "time": "2.0h", "children": []}
                ]}
            ]},
            {"id": "c2", "text": "官方回应", "time": "0.8h", "children": []},
            {"id": "c4", "text": "媒体报道", "time": "1.2h", "children": []},
            {"id": "c6", "text": "网友评论", "time": "1.5h", "children": []},
        ]
    }

    virtual = [
        {"id": "v_0", "text": "支持这个说法", "time": "0.3h", "stance": "支持", "is_virtual": True},
        {"id": "v_1", "text": "我不相信", "time": "0.5h", "stance": "反对", "is_virtual": True},
        {"id": "v_2", "text": "尚待证实", "time": "0.8h", "stance": "中立", "is_virtual": True},
    ]

    print("=== 截断前 ===")
    def count_nodes(t):
        return 1 + sum(count_nodes(c) for c in t.get("children", []))
    print(f"节点数: {count_nodes(sample_tree)}")

    truncated = truncate_tree(sample_tree, max_depth=2, max_nodes=5)
    print(f"\n=== 截断后（depth≤2, nodes≤5）===")
    print(f"节点数: {count_nodes(truncated)}")

    attach_virtual_children(truncated, virtual)
    print(f"\n=== 挂载虚拟节点后 ===")
    print(f"节点数: {count_nodes(truncated)}")

    texts, tree_struct = tree_to_model_input(truncated)
    print(f"\n=== 模型输入 ===")
    print(f"texts ({len(texts)} 条):")
    for i, t in enumerate(texts):
        vf = tree_struct['virtual_flags'][i]
        print(f"  [{i}]{'[V]' if vf else '   '} {t[:30]}")
    print(f"adjacency: {tree_struct['adjacency']}")
    print(f"relation_types: {tree_struct['relation_types']}")
    print(f"virtual_flags: {tree_struct['virtual_flags']}")
    print("\n测试完成！")
