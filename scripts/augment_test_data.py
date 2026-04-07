# -*- coding: utf-8 -*-
"""
多立场虚拟回复增强脚本
使用 Qwen API 对 processed_crawled.json 生成含 virtual_children 的增强数据
输出格式：augmented_qwen.json（含 virtual_children 字段）
"""
import os
import json
import time
import hashlib
import requests
from pathlib import Path

API_KEY = "sk-2ddddb50a0f84f01a5b155afb28de024"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DATA_DIR = Path("E:/rumor_detection/data")
INPUT_FILE = DATA_DIR / "processed_crawled.json"
OUTPUT_FILE = DATA_DIR / "augmented_qwen.json"
CACHE_DIR = DATA_DIR / ".aug_cache"
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


def _cache_key(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _load_cache(content: str):
    key = _cache_key(content)
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(content: str, result):
    key = _cache_key(content)
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)


def call_qwen(content: str, max_retries: int = 2):
    """调用 Qwen API，返回解析后的 comments 列表，失败返回 None"""
    cached = _load_cache(content)
    if cached is not None:
        return cached

    prompt = MULTI_STANCE_PROMPT.format(content=content)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.8
    }

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()

            # 提取 JSON 块
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("未找到JSON块")
            parsed = json.loads(raw[start:end])
            comments = parsed.get("comments", [])

            # 校验：三种立场都必须存在
            stances = {c.get("stance") for c in comments}
            required = {"支持", "反对", "中立"}
            if not required.issubset(stances):
                raise ValueError(f"立场不均衡: {stances}")

            _save_cache(content, comments)
            return comments

        except Exception as e:
            print(f"  [attempt {attempt+1}] 失败: {e}")
            if attempt < max_retries:
                time.sleep(1)

    return None


def build_virtual_children(comments: list) -> list:
    """将 comments 列表转换为 virtual_children 格式"""
    children = []
    for i, c in enumerate(comments):
        children.append({
            "id": f"v_{i}",
            "text": c.get("text", ""),
            "time": c.get("time", f"{(i+1)*0.3:.1f}h"),
            "stance": c.get("stance", "中立"),
            "is_virtual": True
        })
    return children


def main():
    print("=" * 60)
    print("Qwen 多立场虚拟回复增强")
    print("=" * 60)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    print(f"原始数据: {len(original_data)} 条")

    # 如果已有输出文件，加载已完成的条目（断点续跑）
    done_ids = set()
    results = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_ids = {r.get("original", "")[:50] for r in results}
        print(f"已完成: {len(results)} 条，继续增量处理")

    for idx, item in enumerate(original_data):
        content = item.get("content", "").strip()
        if not content or len(content) < 10:
            continue
        if content[:50] in done_ids:
            continue

        print(f"[{idx+1}/{len(original_data)}] 处理: {content[:40]}...")
        comments = call_qwen(content)

        if comments is None:
            print("  跳过（API失败）")
            continue

        virtual_children = build_virtual_children(comments)

        results.append({
            "original": content,
            "augmented": content,          # 主文本不变，虚拟节点挂在 children 里
            "augmentation_type": "multi_stance_llm",
            "label": item.get("label", "辟谣"),
            "stance": "mixed",
            "source": "qwen_virtual_replies",
            "original_label": item.get("label", ""),
            "virtual_children": virtual_children
        })

        # 每条保存一次，防止中途崩溃丢数据
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)  # 限流

    print(f"\n完成！共 {len(results)} 条，保存至: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
