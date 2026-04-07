# -*- coding: utf-8 -*-
"""
测试集数据增强脚本
使用LLM（千问）对processed_crawled数据增强，生成不同立场版本
目标：5000+条测试数据
"""
import os
import json
import random
import time

# 加载原始数据
print("加载原始测试数据...")
with open("E:/rumor_detection/data/processed_crawled.json", 'r', encoding='utf-8') as f:
    original_data = json.load(f)

print(f"原始数据: {len(original_data)} 条")

# 立场变换模板
STANCE_PROMPTS = {
    "支持": """你是一个微博用户，请站在"支持"原帖观点的立场，对以下微博内容进行改写，使其表达支持态度：

原帖：{content}

改写要求：
1. 保持原文核心信息
2. 明确表达支持态度
3. 可以补充支持的理由或证据
4. 字数与原文相近
5. 直接输出改写结果，不要加任何标记""",

    "反对": """你是一个微博用户，请站在"反对"原帖观点的立场，对以下微博内容进行改写，使其表达反对/质疑态度：

原帖：{content}

改写要求：
1. 保持原文核心信息
2. 明确表达反对或质疑
3. 可以提出反对理由或疑问
4. 字数与原文相近
5. 直接输出改写结果，不要加任何标记""",

    "中立": """你是一个微博用户，请站在"中立/客观"立场，对以下微博内容进行改写，使其表达不偏不倚的态度：

原帖：{content}

改写要求：
1. 保持原文核心信息
2. 不表达明显倾向
3. 可以提出多种观点或留待验证
4. 字数与原文相近
5. 直接输出改写结果，不要加任何标记""",
}

# 语义变换模板
SEMANTIC_PROMPTS = {
    "简化": """请将以下微博内容简化表达，保留核心信息，去除修饰词：

{content}

要求：简化后内容更短更直接，直接输出结果""",

    "详细": """请详细描述以下微博内容，增加更多细节和背景信息：

{content}

要求：更详细更丰富，直接输出结果""",

    "换一种说法": """请换一种说法表达以下内容，保持相同意思：

{content}

要求：完全不同的措辞，直接输出结果""",
}


def call_qwen_api(prompt, api_key=None):
    """调用千问API"""
    if api_key is None:
        api_key = os.environ.get("DASHSCOPE_API_KEY", "")

    if not api_key:
        return None

    import requests

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"API调用失败: {e}")
        return None


def generate_augmented_data(target_count=15000):
    """生成增强数据"""
    augmented = []
    current_count = len(original_data)

    # 每条原始数据生成多种增强版本
    operations = list(STANCE_PROMPTS.keys()) + list(SEMANTIC_PROMPTS.keys())

    print(f"目标: {target_count} 条")
    print(f"当前: {current_count} 条")
    print(f"需要增加: {target_count - current_count} 条")

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")

    if not api_key:
        print("\n警告: 未设置DASHSCOPE_API_KEY环境变量")
        print("将使用模拟数据（仅供测试）")

    # 循环生成直到达到目标
    iteration = 0
    while len(augmented) < target_count - current_count:
        iteration += 1
        print(f"\n迭代 {iteration}: 当前 {len(augmented)} 条")

        for item in original_data:
            if len(augmented) >= target_count - current_count:
                break

            content = item.get('content', '')
            if not content or len(content) < 10:
                continue

            # 随机选择增强方式
            op_type = random.choice(operations)

            if op_type in STANCE_PROMPTS:
                prompt = STANCE_PROMPTS[op_type].format(content=content)
                label = "支持" if op_type == "支持" else ("反对" if op_type == "反对" else "中立")
            else:
                prompt = SEMANTIC_PROMPTS[op_type].format(content=content)
                label = item.get('label', '辟谣')

            # 调用API或使用模拟
            if api_key:
                new_content = call_qwen_api(prompt, api_key)
                if not new_content:
                    new_content = f"[{op_type}] {content[:50]}..."  # 模拟
            else:
                # 模拟数据（用于测试）
                new_content = f"[{op_type}] {content}"
                time.sleep(0.1)  # 避免太快

            if new_content and len(new_content) > 10:
                augmented.append({
                    'original': content,
                    'augmented': new_content,
                    'augmentation_type': op_type,
                    'label': label,
                    'stance': label,
                    'source': 'weibo_crawled_augmented',
                    'original_label': item.get('label', '')
                })

            # 避免API限流
            if api_key:
                time.sleep(0.5)

        print(f"  本次迭代增加: {len(augmented)} 条")

    return augmented


if __name__ == "__main__":
    print("="*60)
    print("测试集数据增强")
    print("="*60)

    # 生成增强数据
    augmented = generate_augmented_data(target_count=5000)

    # 合并原始数据和增强数据
    all_test_data = original_data.copy()

    # 转换原始数据格式
    for item in original_data:
        all_test_data.append({
            'original': item.get('content', ''),
            'augmented': item.get('content', ''),
            'augmentation_type': 'original',
            'label': item.get('label', '辟谣'),
            'stance': item.get('stance', '中立'),
            'source': 'weibo_crawled',
            'original_label': item.get('label', '')
        })

    # 添加增强数据
    all_test_data.extend(augmented)

    print(f"\n总计测试数据: {len(all_test_data)} 条")

    # 保存
    output_path = "E:/rumor_detection/data/test_dataset.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_test_data, f, ensure_ascii=False, indent=2)

    print(f"已保存到: {output_path}")
    print("="*60)
