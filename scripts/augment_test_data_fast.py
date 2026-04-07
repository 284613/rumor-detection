# -*- coding: utf-8 -*-
"""
高性能异步数据增强脚本 (MiniMax M2.5-highspeed)
使用 asyncio 并发请求提升 10 倍以上速度
"""
import os
import json
import asyncio
import hashlib
import time
from pathlib import Path
from anthropic import AsyncAnthropic

# MiniMax Token Plan 配置
MINIMAX_API_KEY = "your_minimax_token_plan_key"
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_MODEL = "MiniMax-M2.5-highspeed"

# 并发控制：同时发起 10 个请求
CONCURRENCY_LIMIT = 10
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

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

client = AsyncAnthropic(
    base_url=MINIMAX_BASE_URL,
    api_key=MINIMAX_API_KEY
)

def _cache_key(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def _load_cache(content: str):
    key = _cache_key(content)
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

def _save_cache(content: str, result):
    key = _cache_key(content)
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

async def call_minimax_async(content: str, max_retries: int = 3):
    """异步调用 MiniMax API"""
    cached = _load_cache(content)
    if cached is not None:
        return cached

    async with semaphore:
        for attempt in range(max_retries):
            try:
                response = await client.messages.create(
                    model=MINIMAX_MODEL,
                    max_tokens=800,
                    system="你是一个专业的社交媒体行为模拟器，擅长生成不同立场的评论。",
                    messages=[{"role": "user", "content": MULTI_STANCE_PROMPT.format(content=content)}]
                )
                
                raw = "".join([block.text for block in response.content if block.type == "text"]).strip()
                
                # 提取 JSON
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start == -1 or end == 0:
                    raise ValueError("未找到JSON块")
                
                parsed = json.loads(raw[start:end])
                comments = parsed.get("comments", [])
                
                # 校验立场均衡性
                stances = {c.get("stance") for c in comments}
                if not {"支持", "反对", "中立"}.issubset(stances):
                    raise ValueError(f"立场不均衡: {stances}")
                
                _save_cache(content, comments)
                return comments

            except Exception as e:
                print(f"  ❌ 请求失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1)) # 增加等待时间
                else:
                    return None
    return None

def build_virtual_children(comments: list) -> list:
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

async def main():
    print("🚀 启动极速增强模式 (并发限制: 10)")
    
    if not INPUT_FILE.exists():
        print(f"❌ 找不到输入文件: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    
    results = []
    done_ids = set()
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_ids = {r.get("original", "")[:50] for r in results}
        print(f"✅ 已加载现有进度: {len(results)} 条")

    # 过滤待处理任务
    tasks_to_run = []
    for item in original_data:
        content = item.get("content", "").strip()
        if content and len(content) >= 10 and content[:50] not in done_ids:
            tasks_to_run.append(item)
    
    print(f"📦 待处理任务: {len(tasks_to_run)} 条")
    if not tasks_to_run:
        print("🎉 所有任务已完成！")
        return

    # 限制每轮批处理大小，避免内存占用过大
    BATCH_SIZE = 50
    for i in range(0, len(tasks_to_run), BATCH_SIZE):
        batch = tasks_to_run[i:i+BATCH_SIZE]
        print(f"\n🌊 正在处理批次 {i//BATCH_SIZE + 1} ({i} - {i+len(batch)})...")
        
        # 创建并发任务
        async_tasks = []
        for item in batch:
            content = item.get("content", "")
            async_tasks.append(call_minimax_async(content))
        
        # 并发运行
        batch_results = await asyncio.gather(*async_tasks)
        
        # 合并结果
        new_entries = 0
        for item, comments in zip(batch, batch_results):
            if comments:
                results.append({
                    "original": item.get("content", ""),
                    "augmented": item.get("content", ""),
                    "augmentation_type": "multi_stance_llm_fast",
                    "label": item.get("label", "辟谣"),
                    "stance": "mixed",
                    "source": "minimax_fast",
                    "virtual_children": build_virtual_children(comments)
                })
                new_entries += 1
        
        # 每批保存一次
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 批次完成！新增 {new_entries} 条。总进度: {len(results)} 条")
        
    print("\n✨ 全部增强任务完成！")

if __name__ == "__main__":
    asyncio.run(main())
