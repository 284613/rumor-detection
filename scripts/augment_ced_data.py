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

MINIMAX_API_KEY  = "sk-cp-OPqmVseIS1d8iyidChRRrL86O8mvfSRntORrdE56ZGRwdQpL_6m7QNfSlo7hM54JSzLUNUz6sbWs-9-gloxNw_C5dPzdStn2e6Y7p36B6m-z-03Hwadgd6c"
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_MODEL    = "MiniMax-M2.5-highspeed"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
INPUT_FILE   = DATA_DIR / "ced_early.json"
OUTPUT_FILE  = DATA_DIR / "ced_early_augmented.json"
CACHE_DIR    = DATA_DIR / ".aug_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MULTI_STANCE_PROMPT = """你是社交媒体用户行为模拟器。
给定以下微博帖子，请模拟6条普通网民对该信息真实性的评论，严格按JSON输出，不要任何多余文字。
立场是对帖子所述信息的可信度判断：
- "支持"：认为该信息可信、转发扩散
- "反对"：质疑该信息的真实性、认为是谣言
- "中立"：持观望态度、不确定真假

要求：支持2条、反对2条、中立2条，立场必须均衡。

微博内容：{content}

输出格式（只输出JSON，不要其他任何文字）：
{{"comments": [
  {{"stance": "支持", "text": "...", "time": "0.3h"}},
  {{"stance": "反对", "text": "...", "time": "0.5h"}},
  {{"stance": "中立", "text": "...", "time": "0.8h"}},
  {{"stance": "支持", "text": "...", "time": "1.1h"}},
  {{"stance": "反对", "text": "...", "time": "1.4h"}},
  {{"stance": "中立", "text": "...", "time": "1.7h"}}
]}}"""

# 模型拒绝回答时的常见特征词（用于快速检测，避免白费重试）
_REFUSAL_MARKERS = [
    "无法完成", "无法满足", "我不能", "我无法", "不应生成", "违反", "请理解",
    "抱歉", "无法协助", "不会生成", "不能模拟", "无法帮助",
    "I'm sorry", "I cannot", "I can't", "I apologize", "not able to",
]

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

# 关键：ANTHROPIC_API_KEY 必须与 api_key 参数一致，SDK 用此做认证头
client = anthropic.Anthropic(
    base_url=MINIMAX_BASE_URL,
    api_key=MINIMAX_API_KEY,
)

def call_minimax(content: str, max_retries: int = 4):
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
                system=(
                    "你是谣言检测学术研究项目的数据标注助手。"
                    "你的任务是为给定的微博帖子生成模拟评论，用于训练谣言检测模型。"
                    "这是纯粹的学术研究目的，模拟评论代表不同用户对信息真实性的判断，"
                    "不代表对任何事件的道德立场。请严格按JSON格式输出，不要任何其他文字。"
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(b.text for b in response.content if b.type == "text").strip()

            # 空响应 = 可能是速率限制，应该重试
            if not raw:
                raise ValueError("空响应（可能是速率限制）")

            # 中文内容拒绝 = 真正的内容安全过滤，直接放弃
            if any(m in raw for m in _REFUSAL_MARKERS):
                print(f"  [内容拒绝] {repr(raw[:120])}")
                return None  # 不重试

            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start == -1 or end == 0:
                print(f"  [raw response] {repr(raw[:300])}")
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
                time.sleep(3 * (attempt + 1))  # 递增退避: 3s, 6s

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
        augmented = sum(1 for t in result.values() if t.get("virtual_children"))
        empty     = sum(1 for t in result.values() if "virtual_children" in t and not t.get("virtual_children"))
        print(f"已增强: {augmented} 棵，待重试: {empty} 棵，继续增量处理...")

    done = 0
    skipped = 0
    failed  = 0

    for idx, (root_id, tree) in enumerate(trees.items()):
        # 已处理（virtual_children 非空）则跳过；空列表说明之前失败，需重试
        if root_id in result and result[root_id].get("virtual_children"):
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

        time.sleep(1.0)  # 限流：1秒/请求，防止速率限制

    total_virt = sum(len(t.get("virtual_children", [])) for t in result.values())
    print(f"\n完成！{len(result)} 棵树，共 {total_virt} 个虚拟节点")
    print(f"  跳过（空文本）: {skipped}  API 失败: {failed}  已缓存跳过: {done}")
    print(f"  输出: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
