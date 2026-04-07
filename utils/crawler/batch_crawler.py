# -*- coding: utf-8 -*-
"""
微博批量辟谣账户爬虫
支持同时爬取多个微博辟谣账户的数据
"""

import os
import json
import time
import random
import requests
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入配置
from weibo_config import (
    USER_AGENTS, REQUEST_DELAY, MAX_RETRIES,
    PAGE_TIMEOUT, RUMOR_SEARCH_URL, OUTPUT_DIR
)

# 导入清洗模块
from cleaner import clean_text, extract_keywords


# ============================================
# 辟谣账户配置
# ============================================

# 辟谣账户列表（账户名称 -> 用户ID映射）
# 可以通过微博搜索获取用户ID，或使用用户主页URL中的数字ID
RUMOR_ACCOUNTS = {
    "微博辟谣": "1938327413",      # @微博辟谣
    "捉谣记": "5871625870",         # @捉谣记
    "腾讯较真": "5813490884",        # @腾讯较真
    "人民网辟谣": "6094576843",      # @人民网辟谣
    "丁香医生": "2117432085",       # @丁香医生
}

# 可扩展的辟谣账户列表（备用）
EXTRA_ACCOUNTS = {
    "中国互联网联合辟谣平台": "7573658324",
    "谣言过滤器": "5871977443",
}


# ============================================
# 工具函数
# ============================================

def load_weibo_cookies() -> Dict:
    """从文件加载微博Cookie"""
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    if cookie_file.exists():
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        return {'Cookie': '; '.join([f"{c['name']}={c['value']}" for c in cookies])}
    return {}


def get_random_ua() -> str:
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)


def get_random_delay() -> float:
    """获取随机请求间隔"""
    return random.uniform(REQUEST_DELAY["min"], REQUEST_DELAY["max"])


# ============================================
# 批量爬虫类
# ============================================

class BatchCrawler:
    """批量微博辟谣账户爬虫"""
    
    def __init__(self, accounts: List[str] = None):
        """
        初始化批量爬虫
        
        Args:
            accounts: 账户名称列表，如果为None则使用默认的RUMOR_ACCOUNTS
        """
        # 使用传入的账户列表或默认账户
        if accounts is None:
            self.accounts = RUMOR_ACCOUNTS
        else:
            # 将传入的账户名称列表转换为ID映射
            self.accounts = {}
            for acc in accounts:
                if acc in RUMOR_ACCOUNTS:
                    self.accounts[acc] = RUMOR_ACCOUNTS[acc]
                elif acc in EXTRA_ACCOUNTS:
                    self.accounts[acc] = EXTRA_ACCOUNTS[acc]
                else:
                    print(f"警告: 未找到账户 '{acc}' 的配置，将尝试直接使用账户名作为ID")
                    self.accounts[acc] = acc
        
        self.session = requests.Session()
        self.results = []
        self.cookie = load_weibo_cookies()
        
        print(f"\n批量爬虫初始化完成")
        print(f"待爬取账户数量: {len(self.accounts)}")
        print(f"账户列表: {list(self.accounts.keys())}")
    
    def _make_request(self, url: str, params: Dict, account_name: str = "") -> Optional[Dict]:
        """
        发送HTTP请求，带有重试机制
        
        Args:
            url: 请求URL
            params: 请求参数
            account_name: 账户名称（用于日志）
        
        Returns:
            JSON响应数据
        """
        headers = {
            "User-Agent": get_random_ua(),
            "Referer": "https://weibo.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }
        headers.update(self.cookie)
        
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
                    print(f"[{account_name}] 请求被拦截(418)，等待重试... (尝试 {retry + 1}/{MAX_RETRIES})")
                    time.sleep(get_random_delay() * 3)
                elif response.status_code == 403:
                    print(f"[{account_name}] 请求被拒绝(403)，Cookie可能已失效")
                    return None
                else:
                    print(f"[{account_name}] 请求失败: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"[{account_name}] 请求超时 (尝试 {retry + 1}/{MAX_RETRIES})")
            except Exception as e:
                print(f"[{account_name}] 请求异常: {e}")
            
            if retry < MAX_RETRIES - 1:
                time.sleep(get_random_delay())
        
        return None
    
    def _parse_weibo_item(self, item: Dict, account_name: str) -> Dict:
        """
        解析单条微博数据
        
        Args:
            item: 微博原始数据
            account_name: 账户名称
        
        Returns:
            标准化后的微博数据
        """
        # 解析微博正文（处理HTML）
        text_html = item.get("text", "")
        text_raw = clean_text(text_html)
        
        # 构建标准化数据
        weibo_data = {
            "account": account_name,
            "content": text_raw,
            "created_at": item.get("created_at", ""),
            "reposts_count": item.get("reposts_count", 0),
            "comments_count": item.get("comments_count", 0),
            "likes_count": item.get("attitudes_count", 0),
            "status_id": item.get("id", ""),
            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # 额外字段（保留）
            "mid": item.get("mid", ""),
            "source": item.get("source", ""),
            "user_id": item.get("user", {}).get("id", ""),
            "user_name": item.get("user", {}).get("screen_name", ""),
            "keywords": [k[0] for k in extract_keywords(text_raw)][:10] if text_raw else []
        }
        
        return weibo_data
    
    def crawl_account(self, account_name: str, pages: int = 5) -> List[Dict]:
        """
        爬取单个账户的所有微博
        
        Args:
            account_name: 账户名称
            pages: 爬取页数
        
        Returns:
            该账户的微博列表
        """
        account_id = self.accounts.get(account_name, account_name)
        print(f"\n{'='*50}")
        print(f"开始爬取账户: @{account_name} (ID: {account_id})")
        print(f"{'='*50}")
        
        account_weibos = []
        
        try:
            for page in range(1, pages + 1):
                params = {
                    "uid": account_id,
                    "feature": 0,
                    "is_all": 1,
                    "is_search": 0,
                    "visible": 0,
                    "page": page,
                    "page_size": 20,
                    "basetime": int(time.time())
                }
                
                response = self._make_request(RUMOR_SEARCH_URL, params, account_name)
                
                if response and response.get("ok") == 1:
                    data = response.get("data", {}).get("list", [])
                    
                    if not data:
                        print(f"[{account_name}] 第 {page} 页无数据，停止爬取")
                        break
                    
                    for item in data:
                        weibo_data = self._parse_weibo_item(item, account_name)
                        account_weibos.append(weibo_data)
                    
                    print(f"[{account_name}] 第 {page} 页: 获取 {len(data)} 条微博")
                    
                    # 随机延迟，避免被反爬
                    time.sleep(get_random_delay())
                    
                else:
                    error_msg = response.get("msg", "未知错误") if response else "无响应"
                    print(f"[{account_name}] 第 {page} 页请求失败: {error_msg}")
                    # 如果是认证错误或无权限，停止爬取
                    if response and response.get("ok") == 0:
                        if "权限" in str(error_msg) or "认证" in str(error_msg):
                            print(f"[{account_name}] 账户可能需要登录或权限不足")
                            break
        
        except Exception as e:
            print(f"[{account_name}] 爬取过程中出现异常: {e}")
        
        print(f"[{account_name}] 爬取完成，共获取 {len(account_weibos)} 条微博")
        return account_weibos
    
    def crawl_all(self, pages_per_account: int = 5, use_thread: bool = False) -> List[Dict]:
        """
        爬取所有账户的微博
        
        Args:
            pages_per_account: 每个账户爬取的页数
            use_thread: 是否使用多线程爬取
        
        Returns:
            所有账户的微博列表
        """
        print(f"\n{'='*60}")
        print(f"开始批量爬取，共 {len(self.accounts)} 个账户")
        print(f"每个账户爬取 {pages_per_account} 页")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        
        if use_thread:
            # 使用多线程加速爬取
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_account = {
                    executor.submit(self.crawl_account, acc, pages_per_account): acc 
                    for acc in self.accounts.keys()
                }
                
                for future in as_completed(future_to_account):
                    account_name = future_to_account[future]
                    try:
                        weibos = future.result()
                        self.results.extend(weibos)
                    except Exception as e:
                        print(f"[{account_name}] 爬取失败: {e}")
        else:
            # 顺序爬取（更稳定）
            for account_name in self.accounts.keys():
                weibos = self.crawl_account(account_name, pages_per_account)
                self.results.extend(weibos)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"批量爬取完成!")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"总微博数: {len(self.results)} 条")
        print(f"账户数量: {len(self.accounts)} 个")
        print(f"{'='*60}")
        
        return self.results
    
    def save_results(self, filename: str = None) -> str:
        """
        保存爬取结果到JSON文件
        
        Args:
            filename: 输出文件名，如果为None则使用默认文件名
        
        Returns:
            保存的文件路径
        """
        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 生成默认文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crawled_rumors_{timestamp}.json"
        
        # 确保是绝对路径
        if not os.path.isabs(filename):
            filename = os.path.join(OUTPUT_DIR, filename)
        
        # 保存为JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存至: {filename}")
        print(f"共 {len(self.results)} 条数据")
        
        # 打印统计信息
        self._print_statistics()
        
        return filename
    
    def _print_statistics(self):
        """打印统计信息"""
        if not self.results:
            print("无数据可供统计")
            return
        
        # 按账户统计
        account_stats = {}
        for item in self.results:
            acc = item.get("account", "未知")
            if acc not in account_stats:
                account_stats[acc] = {"count": 0, "total_likes": 0, "total_comments": 0, "total_reposts": 0}
            account_stats[acc]["count"] += 1
            account_stats[acc]["total_likes"] += item.get("likes_count", 0)
            account_stats[acc]["total_comments"] += item.get("comments_count", 0)
            account_stats[acc]["total_reposts"] += item.get("reposts_count", 0)
        
        print("\n各账户数据统计:")
        print("-" * 60)
        print(f"{'账户名称':<15} {'微博数':<8} {'点赞':<10} {'评论':<10} {'转发':<10}")
        print("-" * 60)
        
        for acc, stats in sorted(account_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            print(f"{acc:<15} {stats['count']:<8} {stats['total_likes']:<10} {stats['total_comments']:<10} {stats['total_reposts']:<10}")
        
        print("-" * 60)
        
        # 汇总统计
        total_weibos = len(self.results)
        total_likes = sum(item.get("likes_count", 0) for item in self.results)
        total_comments = sum(item.get("comments_count", 0) for item in self.results)
        total_reposts = sum(item.get("reposts_count", 0) for item in self.results)
        
        print(f"{'合计':<15} {total_weibos:<8} {total_likes:<10} {total_comments:<10} {total_reposts:<10}")
        print("=" * 60)
    
    def get_results(self) -> List[Dict]:
        """获取爬取结果"""
        return self.results
    
    def clear_results(self):
        """清空爬取结果"""
        self.results = []


# ============================================
# 便捷函数
# ============================================

def quick_crawl(
    accounts: List[str] = None,
    pages: int = 5,
    output_file: str = None,
    use_thread: bool = False
) -> str:
    """
    快速爬取函数
    
    Args:
        accounts: 账户名称列表，None则使用默认账户
        pages: 每个账户爬取的页数
        output_file: 输出文件名
        use_thread: 是否使用多线程
    
    Returns:
        保存的文件路径
    """
    # 初始化爬虫
    crawler = BatchCrawler(accounts)
    
    # 执行爬取
    crawler.crawl_all(pages_per_account=pages, use_thread=use_thread)
    
    # 保存结果
    return crawler.save_results(output_file)


def crawl_custom_accounts(
    account_ids: Dict[str, str],
    pages: int = 5,
    output_file: str = None
) -> str:
    """
    自定义账户爬取
    
    Args:
        account_ids: 账户名称到ID的映射字典
        pages: 每个账户爬取的页数
        output_file: 输出文件名
    
    Returns:
        保存的文件路径
    """
    crawler = BatchCrawler()
    crawler.accounts = account_ids
    
    crawler.crawl_all(pages_per_account=pages)
    
    return crawler.save_results(output_file)


# ============================================
# 主程序入口
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="微博批量辟谣账户爬虫")
    parser.add_argument("--accounts", "-a", nargs="+", 
                        help="指定要爬取的账户名称（空格分隔）")
    parser.add_argument("--pages", "-p", type=int, default=5,
                        help="每个账户爬取的页数（默认5页）")
    parser.add_argument("--output", "-o", type=str, 
                        default="crawled_rumors.json",
                        help="输出文件名")
    parser.add_argument("--thread", "-t", action="store_true",
                        help="使用多线程加速爬取")
    parser.add_argument("--list-accounts", "-l", action="store_true",
                        help="列出所有可用账户")
    
    args = parser.parse_args()
    
    if args.list_accounts:
        print("\n可用辟谣账户列表:")
        print("-" * 40)
        for name, uid in RUMOR_ACCOUNTS.items():
            print(f"  @{name} (ID: {uid})")
        print("-" * 40)
        for name, uid in EXTRA_ACCOUNTS.items():
            print(f"  @{name} (ID: {uid}) [备用]")
        print()
    
    else:
        # 执行爬取
        output_path = quick_crawl(
            accounts=args.accounts,
            pages=args.pages,
            output_file=args.output,
            use_thread=args.thread
        )
        
        print(f"\n爬取完成！数据已保存至: {output_path}")
