# -*- coding: utf-8 -*-
"""
微博爬虫主程序
使用Selenium/Playwright模拟浏览器采集热门话题和辟谣数据
"""

import os
import json
import time
import random
import requests
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

# 导入配置
from weibo_config import (
    USER_AGENTS, REQUEST_DELAY, MAX_RETRIES,
    PAGE_TIMEOUT, SCROLL_TIMES, SCROLL_WAIT, HOT_TOPICS_URL,
    RUMOR_DENIAL_ACCOUNT, RUMOR_SEARCH_URL, OUTPUT_DIR,
    RUMOR_TYPES, STANCE_TYPES, USE_RANDOM_UA, USE_RANDOM_DELAY,
    WEBDRIVER_OPTIONS, PLAYWRIGHT_CONFIG
)

# 导入清洗模块
from cleaner import (
    clean_text, tokenize, extract_keywords, clean_weibo_data,
    clean_batch_data, build_propagation_tree, build_full_propagation_tree,
    save_cleaned_data, init_jieba
)

# 加载Cookie
def load_weibo_cookies():
    """从文件加载微博Cookie"""
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    if cookie_file.exists():
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        return {'Cookie': '; '.join([f"{c['name']}={c['value']}" for c in cookies])}
    return {}

WEIBO_COOKIE = load_weibo_cookies()


# ============================================
# Selenium爬虫类
# ============================================

class WeiboSeleniumCrawler:
    """基于Selenium的微博爬虫"""
    
    def __init__(self, use_playwright: bool = False):
        """
        初始化爬虫
        
        Args:
            use_playwright: 是否使用Playwright（默认为Selenium）
        """
        self.use_playwright = use_playwright
        self.driver = None
        self.session = requests.Session()
        self._init_jieba()
    
    def _init_jieba(self):
        """初始化jieba分词"""
        try:
            init_jieba()
            print("jieba分词器初始化成功")
        except Exception as e:
            print(f"jieba初始化失败: {e}")
    
    def _get_random_ua(self) -> str:
        """获取随机User-Agent"""
        return random.choice(USER_AGENTS)
    
    def _get_random_delay(self) -> float:
        """获取随机请求间隔"""
        return random.uniform(REQUEST_DELAY["min"], REQUEST_DELAY["max"])
    
    def _setup_selenium(self):
        """配置Selenium WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            
            if WEBDRIVER_OPTIONS.get("headless"):
                options.add_argument("--headless")
            
            options.add_argument(f'--user-agent={self._get_random_ua()}')
            options.add_argument(f'--window-size={WEBDRIVER_OPTIONS["window_size"][0]},{WEBDRIVER_OPTIONS["window_size"][1]}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            if WEBDRIVER_OPTIONS.get("disable_images"):
                prefs = {"profile.managed_default_content_settings.images": 2}
                options.add_experimental_option("prefs", prefs)
            
            # 创建driver（需确保ChromeDriver已安装）
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(PAGE_TIMEOUT)
            
            # 反自动化检测
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Selenium WebDriver 初始化成功")
            
        except ImportError:
            print("错误: Selenium未安装，请运行: pip install selenium")
            print("或使用requests模式（功能受限）")
            raise
        except Exception as e:
            print(f"Selenium初始化失败: {e}")
            raise
    
    def _setup_playwright(self):
        """配置Playwright"""
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=PLAYWRIGHT_CONFIG.get("headless", True)
            )
            self.context = self.browser.new_context(
                user_agent=PLAYWRIGHT_CONFIG["user_agent"]
            )
            self.page = self.context.new_page()
            
            print("Playwright 初始化成功")
            
        except ImportError:
            print("错误: Playwright未安装，请运行: pip install playwright")
            print("然后运行: playwright install chromium")
            raise
    
    def _requests_get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        使用requests发送GET请求
        
        Args:
            url: 请求URL
            params: 请求参数
        
        Returns:
            JSON响应数据
        """
        headers = {
            "User-Agent": self._get_random_ua(),
            "Referer": "https://weibo.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        headers.update(WEIBO_COOKIE)
        
        for retry in range(MAX_RETRIES):
            try:
                response = self.session.get(
                    url, 
                    params=params, 
                    headers=headers, 
                    timeout=PAGE_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 418:
                    # 被反爬，需要等待更长时间
                    print(f"请求被拦截(418)，等待重试...")
                    time.sleep(self._get_random_delay() * 3)
                else:
                    print(f"请求失败: {response.status_code}")
                    
            except Exception as e:
                print(f"请求异常: {e}")
            
            if retry < MAX_RETRIES - 1:
                time.sleep(self._get_random_delay())
        
        return None
    
    def _scroll_page(self, times: int = SCROLL_TIMES):
        """滚动页面加载更多内容"""
        if not self.driver:
            return
        
        for i in range(times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_WAIT)
            print(f"滚动第 {i+1}/{times} 次")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        print("浏览器已关闭")


# ============================================
# 热门话题爬取
# ============================================

def crawl_hot_topics(max_results: int = 50, use_browser: bool = False) -> List[Dict]:
    """
    爬取微博热门话题
    
    Args:
        max_results: 最大获取数量
        use_browser: 是否使用浏览器模式（Selenium/Playwright）
    
    Returns:
        热门话题列表
    """
    print(f"\n{'='*50}")
    print("开始爬取热门话题...")
    print(f"{'='*50}")
    
    topics = []
    crawler = WeiboSeleniumCrawler()
    
    try:
        if use_browser:
            # 使用浏览器模式
            crawler = WeiboSeleniumCrawler(use_playwright=False)
            crawler._setup_selenium()
            
            # 访问热搜页面
            crawler.driver.get(HOT_TOPICS_URL)
            time.sleep(3)
            crawler._scroll_page(2)
            
            # 解析页面内容（需要根据实际页面结构调整）
            # 此处为示例代码，实际需要根据微博页面结构进行解析
            print("浏览器模式需要根据实际页面结构调整解析逻辑")
            
        else:
            # 使用API模式
            response = crawler._requests_get(HOT_TOPICS_URL)
            
            if response and response.get("ok") == 1:
                data = response.get("data", {}).get("realtime", [])
                
                for item in data[:max_results]:
                    topic = {
                        "rank": item.get("rank", 0),
                        "word": item.get("word", ""),  # 话题词
                        "raw_word": item.get("raw_word", ""),
                        "num": item.get("num", 0),    # 热度值
                        "label": item.get("label_name", ""),  # 标签
                        "icon_url": item.get("icon", ""),
                        "topic_url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        # 标注字段
                        "rumor_type": "",
                        "stance": "",
                        # 清洗后字段
                        "word_cleaned": "",
                        "word_keywords": []
                    }
                    
                    # 清洗话题词
                    topic["word_cleaned"] = clean_text(topic["word"])
                    if topic["word_cleaned"]:
                        topic["word_keywords"] = [k[0] for k in extract_keywords(topic["word_cleaned"])]
                    
                    topics.append(topic)
                
                print(f"成功获取 {len(topics)} 条热门话题")
            else:
                print(f"API请求失败: {response}")
    
    except Exception as e:
        print(f"爬取热门话题失败: {e}")
    
    finally:
        if crawler:
            crawler.close()
    
    return topics


# ============================================
# 辟谣内容爬取
# ============================================

def crawl_rumor_denials(
    max_pages: int = 20,  # 从5页增加到20页
    use_browser: bool = False,
    account_id: str = "5869998085"
) -> List[Dict]:
    """
    爬取微博辟谣内容
    
    Args:
        max_pages: 最大爬取页数
        use_browser: 是否使用浏览器模式
        account_id: 辟谣账号ID（默认@微博辟谣）
    
    Returns:
        辟谣内容列表
    """
    print(f"\n{'='*50}")
    print("开始爬取辟谣内容...")
    print(f"{'='*50}")
    
    denials = []
    crawler = WeiboSeleniumCrawler()
    
    try:
        if use_browser:
            # 浏览器模式
            crawler._setup_selenium()
            
            # 访问辟谣账号主页
            url = f"https://weibo.com/u/{account_id}?is_all=1"
            crawler.driver.get(url)
            time.sleep(5)
            
            # 滚动加载更多内容
            crawler._scroll_page(SCROLL_TIMES)
            
            # 解析页面（需要根据实际结构调整）
            print("浏览器模式需要根据实际页面结构调整解析逻辑")
            
        else:
            # API模式 - 使用用户微博接口
            page = 1
            while page <= max_pages:
                params = {
                    "uid": account_id,
                    "feature": 0,
                    "is_all": 1,
                    "is_search": 0,
                    "visible": 0,
                    "is_all": 1,
                    "page": page,
                    "page_size": 20,
                    "basetime": int(time.time())
                }
                
                response = crawler._requests_get(RUMOR_SEARCH_URL, params)
                
                if response and response.get("ok") == 1:
                    data = response.get("data", {}).get("list", [])
                    
                    if not data:
                        break
                    
                    for item in data:
                        # 解析微博数据
                        text_html = item.get("text", "")
                        text_raw = clean_text(text_html)
                        
                        denial = {
                            "status_id": item.get("id", ""),
                            "mid": item.get("mid", ""),
                            "text_html": text_html,
                            "text_raw": text_raw,
                            "text_keywords": [k[0] for k in extract_keywords(text_raw)],
                            "created_at": item.get("created_at", ""),
                            "source": item.get("source", ""),
                            "reposts_count": item.get("reposts_count", 0),
                            "comments_count": item.get("comments_count", 0),
                            "attitudes_count": item.get("attitudes_count", 0),
                            "user_id": item.get("user", {}).get("id", ""),
                            "user_name": item.get("user", {}).get("screen_name", ""),
                            "user_description": item.get("user", {}).get("description", ""),
                            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            # 标注字段
                            "rumor_type": "",    # 真/假/未证实
                            "stance": "",         # 支持/反对/中立
                            # 传播树字段
                            "parent_id": "",
                            "propagation_depth": 0
                        }
                        
                        # 获取转发微博的原始ID
                        if item.get("retweeted_status"):
                            denial["parent_id"] = item["retweeted_status"].get("id", "")
                        
                        denials.append(denial)
                    
                    print(f"第 {page} 页: 获取 {len(data)} 条微博")
                    page += 1
                    
                    # 随机延迟
                    time.sleep(crawler._get_random_delay())
                    
                else:
                    print(f"第 {page} 页请求失败")
                    break
    
    except Exception as e:
        print(f"爬取辟谣内容失败: {e}")
    
    finally:
        if crawler:
            crawler.close()
    
    print(f"共获取 {len(denials)} 条辟谣内容")
    return denials


# ============================================
# 多账号辟谣爬取
# ============================================

def crawl_multiple_rumor_accounts(
    max_pages_per_account: int = 10,
    use_browser: bool = False
) -> List[Dict]:
    """
    爬取多个辟谣相关账号

    Args:
        max_pages_per_account: 每个账号最大页数
        use_browser: 是否使用浏览器模式

    Returns:
        辟谣内容列表
    """
    # 辟谣相关账号列表
    rumor_accounts = [
        "5869998085",  # 微博辟谣
        "1938327413",  # 辟谣微博
        "5099406805",  # 谣言粉碎机
        "5765561461",  # 中国互联网联合辟谣平台
        "1744386573",  # 头条辟谣
        "2612097985",  # 较真
    ]

    all_denials = []

    print(f"\n{'='*50}")
    print(f"开始多账号辟谣爬取 ({len(rumor_accounts)} 个账号)...")
    print(f"{'='*50}")

    for i, account_id in enumerate(rumor_accounts):
        print(f"\n[{i+1}/{len(rumor_accounts)}] 爬取账号: {account_id}")
        try:
            denials = crawl_rumor_denials(
                max_pages=max_pages_per_account,
                use_browser=use_browser,
                account_id=account_id
            )
            all_denials.extend(denials)
            print(f"  获取 {len(denials)} 条")
        except Exception as e:
            print(f"  账号 {account_id} 爬取失败: {e}")
            continue

    # 去重
    unique_denials = []
    seen_ids = set()
    for d in all_denials:
        if d.get("status_id") and d["status_id"] not in seen_ids:
            seen_ids.add(d["status_id"])
            unique_denials.append(d)

    print(f"\n多账号爬取完成: 共 {len(unique_denials)} 条唯一数据")
    return unique_denials


# ============================================
# 搜索功能
# ============================================

def search_weibo(
    keyword: str, 
    max_results: int = 50,
    search_type: str = "topic"
) -> List[Dict]:
    """
    搜索微博内容
    
    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        search_type: 搜索类型 (topic/user/location)
    
    Returns:
        搜索结果列表
    """
    print(f"\n{'='*50}")
    print(f"搜索微博: {keyword}")
    print(f"{'='*50}")
    
    results = []
    crawler = WeiboSeleniumCrawler()
    
    try:
        # 微博搜索API
        url = "https://weibo.com/ajax/statuses/mymblog"
        params = {
            "key_word": keyword,
            "start": 0,
            "end": max_results,
            "type": search_type
        }
        
        response = crawler._requests_get(url, params)
        
        if response and response.get("ok") == 1:
            data = response.get("data", {}).get("list", [])
            
            for item in data:
                text_html = item.get("text", "")
                text_raw = clean_text(text_html)
                
                result = {
                    "status_id": item.get("id", ""),
                    "text_raw": text_raw,
                    "text_keywords": [k[0] for k in extract_keywords(text_raw)],
                    "created_at": item.get("created_at", ""),
                    "reposts_count": item.get("reposts_count", 0),
                    "comments_count": item.get("comments_count", 0),
                    "attitudes_count": item.get("attitudes_count", 0),
                    "user_name": item.get("user", {}).get("screen_name", ""),
                    "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "rumor_type": "",
                    "stance": "",
                    "parent_id": item.get("retweeted_status", {}).get("id", "") if item.get("retweeted_status") else ""
                }
                
                results.append(result)
            
            print(f"搜索到 {len(results)} 条结果")
        
    except Exception as e:
        print(f"搜索失败: {e}")
    
    finally:
        crawler.close()
    
    return results


# ============================================
# 批量爬取与数据保存
# ============================================

def run_full_crawl(
    topics_count: int = 50,
    denials_pages: int = 5,
    output_base: str = OUTPUT_DIR
):
    """
    运行完整爬取流程
    
    Args:
        topics_count: 热门话题数量
        denials_pages: 辟谣内容页数
        output_base: 输出目录
    """
    print("\n" + "="*60)
    print("微博数据爬取程序")
    print("="*60)
    
    # 创建输出目录
    os.makedirs(output_base, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 爬取热门话题
    topics = crawl_hot_topics(max_results=topics_count)
    
    if topics:
        topics_file = os.path.join(output_base, f"hot_topics_{timestamp}.json")
        save_cleaned_data(topics, topics_file, "json")
    
    # 2. 爬取辟谣内容
    denials = crawl_rumor_denials(max_pages=denials_pages)
    
    if denials:
        denials_file = os.path.join(output_base, f"rumor_denials_{timestamp}.json")
        save_cleaned_data(denials, denials_file, "json")
        
        # 3. 构建传播树
        tree = build_full_propagation_tree(denials)
        tree_file = os.path.join(output_base, f"propagation_tree_{timestamp}.json")
        
        with open(tree_file, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        
        print(f"传播树已保存至: {tree_file}")
    
    # 4. 汇总统计
    print("\n" + "="*60)
    print("爬取完成！统计如下:")
    print(f"  - 热门话题: {len(topics)} 条")
    print(f"  - 辟谣内容: {len(denials)} 条")
    print(f"  - 传播树节点: {len(tree) if 'tree' in dir() else 0} 个")
    print("="*60)
    
    return {
        "topics": topics,
        "denials": denials,
        "tree": tree if 'tree' in dir() else {}
    }


# ============================================
# 手动标注功能
# ============================================

def manual_annotate(data_file: str, output_file: str = None):
    """
    手动标注数据
    
    Args:
        data_file: 数据文件路径
        output_file: 输出文件路径（默认覆盖原文件）
    """
    print("\n" + "="*50)
    print("手动标注模式")
    print("="*50)
    
    # 加载数据
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"共 {len(data)} 条数据待标注")
    print(f"谣言类型: {list(RUMOR_TYPES.keys())}")
    print(f"立场倾向: {list(STANCE_TYPES.keys())}")
    
    output_file = output_file or data_file
    
    for i, item in enumerate(data):
        print(f"\n[{i+1}/{len(data)}]")
        
        # 显示内容摘要
        text_preview = item.get("text_raw", item.get("text_cleaned", ""))[:100]
        print(f"内容: {text_preview}...")
        
        # 获取标注
        rumor = input("谣言类型 (真/假/未证实/跳过回车): ").strip()
        stance = input("立场 (支持/反对/中立/跳过回车): ").strip()
        
        # 更新标注
        if rumor in RUMOR_TYPES:
            item["rumor_type"] = rumor
        if stance in STANCE_TYPES:
            item["stance"] = stance
        
        # 保存进度
        if (i + 1) % 10 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"已自动保存进度")
    
    # 最终保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n标注完成，已保存至: {output_file}")


# ============================================
# 主程序入口
# ============================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="微博数据爬虫")
    parser.add_argument("--mode", "-m", choices=["topics", "denials", "multi_denials", "search", "annotate", "full"],
                        default="full", help="运行模式")
    parser.add_argument("--keyword", "-k", type=str, help="搜索关键词")
    parser.add_argument("--topics-count", "-t", type=int, default=50, help="热门话题数量")
    parser.add_argument("--denials-pages", "-d", type=int, default=20, help="辟谣内容页数")
    parser.add_argument("--output", "-o", type=str, default=OUTPUT_DIR, help="输出目录")
    parser.add_argument("--browser", "-b", action="store_true", help="使用浏览器模式")
    parser.add_argument("--file", "-f", type=str, help="标注模式的数据文件")

    args = parser.parse_args()

    if args.mode == "topics":
        topics = crawl_hot_topics(max_results=args.topics_count, use_browser=args.browser)
        print(f"获取 {len(topics)} 条热门话题")

    elif args.mode == "denials":
        denials = crawl_rumor_denials(max_pages=args.denials_pages, use_browser=args.browser)
        print(f"获取 {len(denials)} 条辟谣内容")

    elif args.mode == "multi_denials":
        denials = crawl_multiple_rumor_accounts(max_pages_per_account=args.denials_pages, use_browser=args.browser)
        print(f"获取 {len(denials)} 条辟谣内容")
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(args.output, f"multi_rumor_denials_{timestamp}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(denials, f, ensure_ascii=False, indent=2)
        print(f"已保存到: {output_file}")

    elif args.mode == "search":
        if not args.keyword:
            print("错误: 搜索模式需要指定 --keyword")
        else:
            results = search_weibo(args.keyword, max_results=50)
            print(f"获取 {len(results)} 条搜索结果")

    elif args.mode == "annotate":
        if not args.file:
            print("错误: 标注模式需要指定 --file")
        else:
            manual_annotate(args.file)

    elif args.mode == "full":
        run_full_crawl(
            topics_count=args.topics_count,
            denials_pages=args.denials_pages,
            output_base=args.output
        )
