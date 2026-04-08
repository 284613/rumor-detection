# -*- coding: utf-8 -*-
"""
CED 极早期传播树 LLM 增强脚本

输入:  data/ced_early.json           （CED 极早期截断，每棵树 ≤3 条真实回复）
输出:  data/ced_early_augmented.json  （同格式，添加 virtual_children 字段）

使用 MiniMax API 对每棵树的根节点文本生成 6 条多立场虚拟回复。
支持断点续跑：已完成的树从磁盘缓存读取，不重复调用 API。

运行：
    MINIMAX_API_KEY=xxx python scripts/augment_ced_data.py
"""
import os
import json
import time
import hashlib
from pathlib import Path

import anthropic

# ──────────────────────── 配置 ────────────────────────

MINIMAX_API_KEY  = os.environ.get("MINIMAX_API_KEY", "your_minimax_token_plan_key")
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_MODEL    = "MiniMax-M2.5-highspeed"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
INPUT_FILE   = DATA_DIR / "ced_early.json"
OUTPUT_FILE  = DATA_DIR / "ced_early_augmented.json"
CACHE_DIR    = DATA_DIR / ".aug_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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

# ──────────────────────── 缓存 ────────────────────────

def _cache_key(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def _load_cache(content: str):
    path = CACHE_DIR / f"{_cache_key(content)}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def _save_cache(content: str, comments: list):
    path = CACHE_DIR / f"{_cache_key(content)}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False)

# ──────────────────────── API 调用 ────────────────────────

client = anthropic.Anthropic(base_url=MINIMAX_BASE_URL, api_key=MINIMAX_API_KEY)

def call_minimax(content: str, max_retries: int = 2):
    """调用 MiniMax API 生成多立场虚拟回复，返回 comments 列表；失败返回 None。"""
    cached = _load_cache(content)
    if cached is not None:
        return cached

    prompt = MULTI_STANCE_PROMPT.format(content=content)

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=MINIMAX_MODEL,
                max_tokens=1000,
                system="你是一个专业的社交媒体行为模拟器，擅长生成不同立场的评论。",
                messages=[{"role": "user", "content": prompt}]
            )
            raw = "".join(b.text for b in response.content if b.type == "text").strip()

            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("未找到 JSON 块")

            parsed   = json.loads(raw[start:end])
            comments = parsed.get("comments", [])

            stances  = {c.get("stance") for c in comments}
            required = {"支持", "反对", "中立"}
            if not required.issubset(stances):
                raise ValueError(f"立场不均衡: {stances}")

            _save_cache(content, comments)
            return comments

        except Exception as e:
            print(f"  [attempt {attempt+1}] 失败: {e}")
            if attempt < max_retries:
                time.sleep(2)

    return None


def build_virtual_children(comments: list) -> list:
    return [
        {
            "id":         f"v_{i}",
            "text":       c.get("text", ""),
            "time":       c.get("time", f"{(i+1)*0.3:.1f}h"),
            "stance":     c.get("stance", "中立"),
            "is_virtual": True,
        }
        for i, c in enumerate(comments)
    ]

# ──────────────────────── 主程序 ────────────────────────

def main():
    print("=" * 60)
    print("CED 极早期传播树 LLM 增强")
    print(f"  输入: {INPUT_FILE}")
    print(f"  输出: {OUTPUT_FILE}")
    print("=" * 60)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        trees: dict = json.load(f)
    print(f"共 {len(trees)} 棵树")

    # 断点续跑：加载已完成的输出
    result: dict = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            result = json.load(f)
        already_done = sum(1 for t in result.values() if "virtual_children" in t)
        print(f"已完成: {already_done} 棵，继续增量处理...")

    done = 0
    skipped = 0
    failed  = 0

    for idx, (root_id, tree) in enumerate(trees.items()):
        # 已处理（有 virtual_children 字段）则跳过
        if root_id in result and "virtual_children" in result[root_id]:
            done += 1
            continue

        content = (tree.get("text") or "").strip()
        if not content or len(content) < 5:
            result[root_id] = {**tree, "virtual_children": []}
            skipped += 1
            continue

        if (idx + 1) % 50 == 0 or idx == 0:
            print(f"[{idx+1}/{len(trees)}] 处理: {content[:50]}...")

        comments = call_minimax(content)

        if comments is None:
            print(f"  [{root_id}] API 失败，写入空 virtual_children")
            result[root_id] = {**tree, "virtual_children": []}
            failed += 1
        else:
            result[root_id] = {**tree, "virtual_children": build_virtual_children(comments)}

        # 每条落盘，断点续跑安全
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        time.sleep(0.3)  # 轻度限流

    total_virt = sum(len(t.get("virtual_children", [])) for t in result.values())
    print(f"\n完成！{len(result)} 棵树，共 {total_virt} 个虚拟节点")
    print(f"  跳过（空文本）: {skipped}  API 失败: {failed}  已缓存跳过: {done}")
    print(f"  输出: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
