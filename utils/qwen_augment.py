# -*- coding: utf-8 -*-
"""千问(Qwen) LLM数据增强模块"""
import json
import os
import time
import requests
from pathlib import Path

# ============ 千问API配置 =============
# 设置方式: set DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-turbo")
# ====================================

class QwenClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
    def chat(self, prompt, system_prompt="你是一个专业的文本处理助手。"):
        """发送千问API请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": QWEN_MODEL,
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "temperature": 0.8,
                "max_tokens": 1000
            }
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=data, timeout=60)
            result = response.json()
            
            if response.status_code == 200 and "output" in result:
                return result["output"]["text"]
            else:
                print(f"[ERROR] {response.status_code}: {result}")
                return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None

def rewrite_prompt(text):
    return f"""请将以下文本改写成5种不同的表达方式，保持语义核心不变。

原文：{text}

请直接输出5条，每条一行，不要编号。"""

def stance_prompt(text):
    return f"""请将以下文本改写成3种不同立场的版本。

原文：{text}

请按以下格式输出（每条一行）：
支持：<支持立场的版本>
反对：<反对立场的版本>
中立：<中立立场的版本>"""

def main():
    if not DASHSCOPE_API_KEY:
        print("[ERROR] 请先设置千问API密钥:")
        print('   set DASHSCOPE_API_KEY=your_api_key')
        print("\n获取API密钥: https://dashscope.console.aliyun.com/")
        return
    
    print(f"[INFO] 千问模型: {QWEN_MODEL}")
    
    # 读取数据
    input_file = Path("E:/rumor_detection/data/cleaned_rumors.json")
    output_file = Path("E:/rumor_detection/data/augmented_qwen.json")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"[INFO] 读取 {len(data)} 条数据")
    
    client = QwenClient()
    all_results = []
    
    # 处理全部数据
    for i, item in enumerate(data):
        content = item.get("清洗后内容", item.get("content", ""))
        if not content:
            continue
            
        print(f"\n[{i+1}] 原文: {content[:40]}...")
        
        # 文本重写
        print("   -> 文本重写中...")
        result = client.chat(rewrite_prompt(content))
        if result:
            for line in result.strip().split("\n"):
                line = line.strip().strip("0123456789.。 ")
                if line and len(line) > 5:
                    all_results.append({
                        "original": content,
                        "augmented": line,
                        "augmentation_type": "rewrite",
                        "label": item.get("谣言类型", "unknown"),
                        "source": "qwen"
                    })
        time.sleep(1)
        
        # 立场改写
        print("   -> 立场改写中...")
        result = client.chat(stance_prompt(content))
        if result:
            for line in result.strip().split("\n"):
                line = line.strip()
                if line.startswith(("支持", "反对", "中立")) and "：" in line:
                    parts = line.split("：", 1)
                    if len(parts) == 2:
                        stance, text = parts
                        if len(text) > 5:
                            all_results.append({
                                "original": content,
                                "augmented": text,
                                "augmentation_type": "stance",
                                "stance": stance,
                                "label": item.get("谣言类型", "unknown"),
                                "source": "qwen"
                            })
        time.sleep(1)
    
    print(f"\n[RESULT] 共生成 {len(all_results)} 条增强数据")
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"[SAVED] {output_file}")

if __name__ == "__main__":
    main()
