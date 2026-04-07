# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path
import urllib.parse
import re

sys.stdout.reconfigure(encoding='utf-8')

def search_rumors():
    from scrapling import Fetcher
    
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    
    cookie_dict = {c['name']: c['value'] for c in cookies if 'name' in c and 'value' in c}
    
    fetcher = Fetcher()
    
    keywords = ["辟谣", "谣言", "假新闻"]
    all_results = []
    
    for keyword in keywords:
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"https://s.weibo.com/weibo?q={encoded_keyword}&wvr=6&b=1"
        
        print(f"\n[SEARCH] {keyword}")
        
        response = fetcher.get(
            search_url,
            cookies=cookie_dict,
            timeout=30,
            impersonate="chrome"
        )
        
        if response.status != 200:
            continue
        
        # 获取完整HTML
        html = response.html_content
        
        # 使用正则提取微博内容 - 查找卡片中的文本
        # 匹配规则: 提取feed_list_content中的文本
        pattern = r'feed_list_content[^>]*>([^<]+)'
        matches = re.findall(pattern, html)
        
        print(f"[MATCHES] {len(matches)} potential matches")
        
        for m in matches:
            # 清理文本
            text = re.sub(r'<[^>]+>', '', m)
            text = text.strip()
            if len(text) > 5:
                all_results.append({
                    "keyword": keyword,
                    "content": text
                })
    
    # 去重
    unique_results = []
    seen = set()
    for r in all_results:
        key = r["content"][:50]
        if key not in seen and len(r["content"]) > 10:
            seen.add(key)
            unique_results.append(r)
    
    print(f"\n[TOTAL] {len(unique_results)} results")
    
    # 保存
    output_file = Path(__file__).parent.parent / "data" / "weibo_rumors.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_results, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {output_file}")
    
    for i, r in enumerate(unique_results[:15]):
        print(f"\n--- {i+1} [{r['keyword']}] ---")
        print(r['content'][:150])


if __name__ == "__main__":
    search_rumors()
