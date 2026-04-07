# -*- coding: utf-8 -*-
"""使用Playwright爬取微博辟谣内容"""
import json
import time
from pathlib import Path

def crawl_rumors():
    """爬取辟谣内容"""
    from playwright.sync_api import sync_playwright
    
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    
    print("🚀 启动Playwright浏览器...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        context.add_cookies(cookies)
        
        page = context.new_page()
        
        # 访问辟谣账号主页
        print("📱 访问微博辟谣账号主页...")
        page.goto('https://weibo.com/u/1938327413?is_all=1', timeout=30000)
        
        # 等待内容加载
        print("⏳ 等待内容加载（30秒）...")
        page.wait_for_timeout(30000)
        
        # 获取微博内容
        print("\n📝 提取微博内容...")
        
        items = page.evaluate('''() => {
            const items = document.querySelectorAll('div[node-type="feed_list_item"], div[class*="item"], div[class*="card"]');
            let results = [];
            items.forEach((item) => {
                let text = item.innerText.trim();
                if (text && text.length > 20) {
                    results.push(text);
                }
            });
            return results;
        }''')
        
        print(f"\n✅ 获取到 {len(items)} 条微博内容!")
        
        # 保存到文件
        output_file = Path(__file__).parent.parent / "data" / "weibo_rumors.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        print(f"📁 已保存到: {output_file}")
        
        # 显示前3条
        for i, item in enumerate(items[:3]):
            print(f"\n--- 微博 {i+1} ---")
            print(item[:500] + "..." if len(item) > 500 else item)
        
        print("\n按回车键关闭浏览器...")
        input()
        
        browser.close()
        print("✅ 完成!")


if __name__ == "__main__":
    crawl_rumors()
