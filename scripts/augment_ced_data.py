# -*- coding: utf-8 -*-
"""
CED 传播树多立场虚拟回复增强脚本
使用 Qwen API 对 ced_full.json 生成含 virtual_children 的增强数据
输出格式：也保存到 augmented_qwen.json，与现有条目合并
"""
import os
import json
import time
import hashlib
import requests
from pathlib import Path

import anthropic

# MiniMax Token Plan 配置
# 请将 your_minimax_token_plan_key 替换为你的实际 API Key
MINIMAX_API_KEY = "your_minimax_token_plan_key"
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5-highspeed"

client = anthropic.Anthropic(
    base_url=MINIMAX_BASE_URL,
    api_key=MINIMAX_API_KEY
)

DATA_DIR = Path("E:/rumor_detection/data")
INPUT_FILE = DATA_DIR / "ced_full.json"
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


def call_minimax(content: str, max_retries: int = 2):
    """调用 MiniMax API，返回解析后的 comments 列表，失败返回 None"""
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
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw = ""
            for block in response.content:
                if block.type == "text":
                    raw += block.text
            
            raw = raw.strip()

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
                time.sleep(2)

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
    print("CED 数据 Qwen 多立场虚拟回复增强")
    print("=" * 60)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        ced_data = json.load(f)
    print(f"CED 原始数据: {len(ced_data)} 条")

    # 如果已有输出文件，加载已完成的条目
    results = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_contents = {r.get("original", "")[:50] for r in results}
        print(f"已完成: {len(results)} 条，继续增量处理")
    else:
        done_contents = set()

    added_count = 0
    # 我们只对 CED 数据中的前 100 条进行增强，以便快速看到效果（全量 3387 条耗时太久）
    # 实际运行可以根据需要放开限制
    TARGET_COUNT = 100 
    
    for idx, (root_id, item) in enumerate(ced_data.items()):
        content = item.get("text", "").strip()
        if not content or len(content) < 10:
            continue
        if content[:50] in done_contents:
            continue

        if added_count >= TARGET_COUNT:
            print(f"已达到目标数量 ({TARGET_COUNT})，停止。")
            break

        print(f"[{added_count+1}/{TARGET_COUNT}] 处理 CED [{root_id}]: {content[:40]}...")
        comments = call_minimax(content)

        if comments is None:
            print("  跳过（API失败）")
            continue

        virtual_children = build_virtual_children(comments)
        
        # 转换 label: CED 1=谣言, 0=非谣言；augmented_qwen 格式用 '辟谣'/'真实'/'虚假'
        label_raw = item.get("label", 0)
        label_str = "虚假" if label_raw == 1 else "真实"

        results.append({
            "original": content,
            "augmented": content,
            "augmentation_type": "multi_stance_llm",
            "label": label_str,
            "stance": "mixed",
            "source": "qwen_virtual_replies",
            "original_label": label_str,
            "virtual_children": virtual_children
        })

        added_count += 1

        # 每条保存一次
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)

    print(f"\n完成！目前共 {len(results)} 条，保存至: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
