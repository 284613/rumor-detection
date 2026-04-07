# -*- coding: utf-8 -*-
import json
import sys
import time
from pathlib import Path
import urllib.parse
import re

sys.stdout.reconfigure(encoding='utf-8')

def load_cookies():
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    return {c['name']: c['value'] for c in cookies if 'name' in c and 'value' in c}

def search_keyword(keyword, cookie_dict, fetcher):
    encoded = urllib.parse.quote(keyword)
    url = f"https://s.weibo.com/weibo?q={encoded}&wvr=6&b=1&page=1"
    
    response = fetcher.get(url, cookies=cookie_dict, timeout=30, impersonate="chrome")
    
    if response.status != 200:
        return []
    
    # 用css选择器获取
    items = response.css('div[action-type="feed_list_item"]')
    
    results = []
    for item in items:
        html_content = item.get()
        # 提取纯文本
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > 30:
            results.append({
                "keyword": keyword,
                "content": text[:500]
            })
    
    return results

def batch_search():
    from scrapling import Fetcher
    
    cookie_dict = load_cookies()
    fetcher = Fetcher()
    
    keywords = ["辟谣", "谣言", "假新闻", "真相", "造谣"]
    all_results = []
    seen = set()
    
    print(f"[INFO] 搜索 {len(keywords)} 个关键词...")
    
    for kw in keywords:
        print(f"[SEARCH] {kw}...", end=" ")
        
        try:
            results = search_keyword(kw, cookie_dict, fetcher)
            print(f"找到 {len(results)} 条")
            
            for r in results:
                key = r["content"][:50]
                if key not in seen:
                    seen.add(key)
                    all_results.append(r)
        except Exception as e:
            print(f"错误: {e}")
        
        time.sleep(2)
    
    print(f"\n[TOTAL] {len(all_results)} 条数据")
    
    output = Path(__file__).parent.parent / "data" / "crawled_rumors.json"
    output.parent.mkdir(exist_ok=True)
    
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"[SAVED] {output}")
    
    for i, r in enumerate(all_results[:5]):
        print(f"\n--- {i+1} [{r['keyword']}] ---")
        print(r['content'][:150])


if __name__ == "__main__":
    batch_search()
