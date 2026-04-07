# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

def crawl_with_scrapling():
    from scrapling import Fetcher
    
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    
    cookie_dict = {c['name']: c['value'] for c in cookies if 'name' in c and 'value' in c}
    
    fetcher = Fetcher()
    
    print("[INFO] Crawling rumor account...")
    response = fetcher.get(
        'https://weibo.com/u/1938327413?is_all=1',
        cookies=cookie_dict,
        timeout=30,
        impersonate="chrome"
    )
    
    print(f"[STATUS] {response.status}")
    
    html = response.html_content
    print(f"[HTML length] {len(html)}")
    
    # 保存HTML
    output_file = Path(__file__).parent.parent / "data" / "weibo_rumor_content.html"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[SAVED HTML] {output_file}")
    
    # 提取文本内容
    try:
        # 提取所有文本
        text = response.getall()
        print(f"[TEXT count] {len(text)}")
        
        # 过滤有意义的内容
        meaningful = [t.strip() for t in text if len(t.strip()) > 10]
        print(f"[MEANINGFUL] {len(meaningful)}")
        
        # 保存文本
        txt_output = Path(__file__).parent.parent / "data" / "weibo_rumor_texts.txt"
        with open(txt_output, 'w', encoding='utf-8') as f:
            f.write('\n\n---\n\n'.join(meaningful[:100]))
        print(f"[SAVED TXT] {txt_output}")
        
        # 显示前几条
        for i, t in enumerate(meaningful[:5]):
            print(f"\n--- {i+1} ---")
            print(t[:200])
            
    except Exception as e:
        print(f"[EXTRACT ERROR] {e}")


if __name__ == "__main__":
    crawl_with_scrapling()
