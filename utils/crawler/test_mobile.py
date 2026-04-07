# -*- coding: utf-8 -*-
import json
import time
import requests
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def load_cookies():
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    return '; '.join([f"{c['name']}={c['value']}" for c in cookies])

def crawl_mobile():
    cookie_str = load_cookies()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'Cookie': cookie_str,
        'Referer': 'https://m.weibo.cn/'
    }
    
    print("[TEST] Checking Cookie...")
    test_url = "https://m.weibo.cn/config/checkcookie"
    resp = requests.get(test_url, headers=headers)
    print(f"[RESULT] {resp.text[:200]}")
    
    print("\n[TOPICS] Getting hot topics...")
    topics_url = "https://m.weibo.cn/feed/topbar"
    resp = requests.get(topics_url, headers=headers)
    print(f"[STATUS] {resp.status_code}")
    data = resp.json()
    print(f"[DATA] {json.dumps(data, ensure_ascii=False)[:500]}")


if __name__ == "__main__":
    crawl_mobile()
