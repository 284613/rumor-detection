#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多平台谣言爬虫
支持平台：微博、知乎、抖音
功能：爬取各平台辟谣相关内容
"""

import json
import random
import time
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RumorItem:
    """统一的谣言数据格式"""
    platform: str           # 平台名称
    content: str            # 内容
    title: str              # 标题
    author: str             # 作者/发布者
    publish_time: str       # 发布时间
    url: str                # 原文链接
    like_count: int         # 点赞数
    comment_count: int      # 评论数
    share_count: int        # 分享数
    crawled_time: str       # 爬取时间
    tags: List[str]         # 标签
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AntiCrawlingStrategy:
    """反爬策略管理器"""
    
    def __init__(self):
        # User-Agent池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        ]
        
        # 请求间隔范围(秒)
        self.min_delay = 2
        self.max_delay = 5
        
        # 最大重试次数
        self.max_retries = 3
        
        # 上次请求时间
        self.last_request_time = 0
        
    def get_headers(self) -> Dict:
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    def random_delay(self):
        """随机延迟，模拟人类行为"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # 确保最小间隔
        if elapsed < self.min_delay:
            sleep_time = random.uniform(self.min_delay, self.max_delay)
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        
    def get_retry_delay(self, attempt: int) -> float:
        """获取重试延迟(指数退避)"""
        return random.uniform(1, 3) * (2 ** attempt)


class WeiboCrawler:
    """微博辟谣内容爬虫"""
    
    # 辟谣账号列表
    RUMOR_ACCOUNTS = [
        {"name": "微博辟谣", "id": "1663072941"},
        {"name": "捉谣记", "id": "5870828039"},
        {"name": "腾讯较真", "id": "2641151057"},
    ]
    
    def __init__(self, anti_strategy: AntiCrawlingStrategy):
        self.anti_strategy = anti_strategy
        self.session = None
        self.data: List[RumorItem] = []
        
    def _init_session(self):
        """初始化请求会话"""
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update(self.anti_strategy.get_headers())
        except ImportError:
            logger.warning("requests库未安装，将使用模拟数据")
            
    def crawl(self, max_pages: int = 5) -> List[RumorItem]:
        """
        爬取微博辟谣内容
        
        Args:
            max_pages: 最大爬取页数
            
        Returns:
            谣言内容列表
        """
        logger.info("开始爬取微博辟谣内容...")
        self._init_session()
        
        # 注意：真实爬取需要登录Cookie和复杂的反爬绕过
        # 此处为框架实现，实际使用需要配置有效的Cookie
        
        for account in self.RUMOR_ACCOUNTS:
            logger.info(f"正在爬取 @{account['name']} 的内容...")
            
            # 模拟爬取过程
            items = self._crawl_account(account, max_pages)
            self.data.extend(items)
            
            # 避免请求过快
            self.anti_strategy.random_delay()
        
        logger.info(f"微博爬取完成，共获取 {len(self.data)} 条内容")
        return self.data
    
    def _crawl_account(self, account: Dict, max_pages: int) -> List[RumorItem]:
        """
        爬取单个账号的内容
        
        注意：微博API限制严格，真实爬取需要:
        1. 登录后的Cookie
        2. 可能需要使用移动端API
        3. 或者使用微博SDK
        """
        items = []
        
        # 模拟数据（实际使用需替换为真实API调用）
        # 真实微博移动端API: https://m.weibo.cn/api/container/getIndex
        mock_contents = [
            {
                "content": "【科普】关于最近流传的XX谣言，我们来澄清一下...",
                "title": "近期热门谣言澄清"
            },
            {
                "content": "【辟谣】网传XX事件为不实信息，请大家不要信谣传谣",
                "title": "不实信息警示"
            },
            {
                "content": "【真相】揭秘XX谣言背后的真相，原来是这样...",
                "title": "谣言真相大揭秘"
            }
        ]
        
        for i, mock in enumerate(mock_contents[:max_pages]):
            # 实际爬取时，这里应该调用微博API
            # 示例API调用:
            # url = f"https://m.weibo.cn/api/container/getIndex?uid={account['id']}&containerid=107603{account['id']}&page={i+1}"
            
            item = RumorItem(
                platform="微博",
                content=mock["content"],
                title=mock["title"],
                author=account["name"],
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url=f"https://weibo.com/u/{account['id']}",
                like_count=random.randint(100, 10000),
                comment_count=random.randint(10, 1000),
                share_count=random.randint(5, 500),
                crawled_time=datetime.now().isoformat(),
                tags=["辟谣", "微博", account["name"]]
            )
            items.append(item)
            
        return items


class ZhihuCrawler:
    """知乎辟谣内容爬虫"""
    
    # 辟谣相关话题
    RUMOR_TOPICS = [
        "辟谣",
        "谣言粉碎机",
        "真相",
        "假新闻",
        "科普"
    ]
    
    def __init__(self, anti_strategy: AntiCrawlingStrategy):
        self.anti_strategy = anti_strategy
        self.session = None
        self.data: List[RumorItem] = []
        
    def _init_session(self):
        """初始化请求会话"""
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update(self.anti_strategy.get_headers())
        except ImportError:
            logger.warning("requests库未安装，将使用模拟数据")
            
    def crawl(self, max_per_topic: int = 10) -> List[RumorItem]:
        """
        爬取知乎辟谣内容
        
        Args:
            max_per_topic: 每个话题最大爬取数量
            
        Returns:
            谣言内容列表
        """
        logger.info("开始爬取知乎辟谣内容...")
        self._init_session()
        
        for topic in self.RUMOR_TOPICS:
            logger.info(f"正在搜索话题: {topic}...")
            
            # 实际爬取时调用知乎搜索API
            # 知乎搜索API: https://www.zhihu.com/api/v4/search_v3
            
            items = self._search_topic(topic, max_per_topic)
            self.data.extend(items)
            
            self.anti_strategy.random_delay()
        
        logger.info(f"知乎爬取完成，共获取 {len(self.data)} 条内容")
        return self.data
    
    def _search_topic(self, topic: str, max_count: int) -> List[RumorItem]:
        """
        搜索特定话题
        
        注意：知乎反爬较严格，真实爬取需要:
        1. 登录Cookie
        2. 知乎API可能需要token
        3. 建议使用知乎App API
        """
        items = []
        
        # 模拟数据
        mock_contents = [
            {
                "content": "【辟谣】关于XX的真相是...请大家理性看待",
                "title": "XX谣言澄清",
                "author": "知乎辟谣达人"
            },
            {
                "content": "深度剖析：为什么XX谣言会广泛传播",
                "title": "谣言传播心理分析",
                "author": "心理学研究者"
            }
        ]
        
        for mock in mock_contents[:max_count]:
            item = RumorItem(
                platform="知乎",
                content=mock["content"],
                title=mock["title"],
                author=mock["author"],
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url=f"https://www.zhihu.com/search?q={topic}",
                like_count=random.randint(50, 5000),
                comment_count=random.randint(10, 500),
                share_count=random.randint(5, 200),
                crawled_time=datetime.now().isoformat(),
                tags=["辟谣", "知乎", topic]
            )
            items.append(item)
            
        return items


class DouyinCrawler:
    """抖音辟谣内容爬虫"""
    
    # 辟谣相关搜索词
    RUMOR_KEYWORDS = [
        "辟谣",
        "谣言",
        "假消息",
        "真相",
        "科普"
    ]
    
    def __init__(self, anti_strategy: AntiCrawlingStrategy):
        self.anti_strategy = anti_strategy
        self.session = None
        self.data: List[RumorItem] = []
        
    def _init_session(self):
        """初始化请求会话"""
        try:
            import requests
            self.session = requests.Session()
            # 抖音需要移动端User-Agent
            mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
            headers = self.anti_strategy.get_headers()
            headers["User-Agent"] = mobile_ua
            self.session.headers.update(headers)
        except ImportError:
            logger.warning("requests库未安装，将使用模拟数据")
            
    def crawl(self, max_per_keyword: int = 10) -> List[RumorItem]:
        """
        爬取抖音辟谣内容
        
        Args:
            max_per_keyword: 每个关键词最大爬取数量
            
        Returns:
            谣言内容列表
        """
        logger.info("开始爬取抖音辟谣内容...")
        self._init_session()
        
        for keyword in self.RUMOR_KEYWORDS:
            logger.info(f"正在搜索关键词: {keyword}...")
            
            items = self._search_keyword(keyword, max_per_keyword)
            self.data.extend(items)
            
            self.anti_strategy.random_delay()
        
        logger.info(f"抖音爬取完成，共获取 {len(self.data)} 条内容")
        return self.data
    
    def _search_keyword(self, keyword: str, max_count: int) -> List[RumorItem]:
        """
        搜索特定关键词
        
        注意：抖音反爬非常严格，真实爬取需要:
        1. 抖音App签名算法
        2. 设备指纹
        3. Cookie/X-Gorgon/X-Bogus等签名
        4. 建议使用抖音开放平台API
        """
        items = []
        
        # 模拟数据
        mock_contents = [
            {
                "content": "【辟谣】XX事件真相是这样的...", 
                "title": "XX谣言澄清视频",
                "author": "抖音辟谣官"
            },
            {
                "content": "网传XX消息不实！点进来告诉你真相",
                "title": "不实消息辟谣",
                "author": "真相只有一个"
            }
        ]
        
        for mock in mock_contents[:max_count]:
            item = RumorItem(
                platform="抖音",
                content=mock["content"],
                title=mock["title"],
                author=mock["author"],
                publish_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url=f"https://www.douyin.com/search/{keyword}",
                like_count=random.randint(1000, 100000),
                comment_count=random.randint(100, 10000),
                share_count=random.randint(50, 5000),
                crawled_time=datetime.now().isoformat(),
                tags=["辟谣", "抖音", keyword]
            )
            items.append(item)
            
        return items


class MultiPlatformCrawler:
    """
    多平台谣言爬虫主类
    
    支持平台：
    - 微博：@微博辟谣、@捉谣记、@腾讯较真
    - 知乎：搜索"辟谣"相关话题
    - 抖音：搜索"辟谣"相关话题/账号
    """
    
    def __init__(self, output_dir: str = "E:\\rumor_detection\\data"):
        """
        初始化爬虫
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.output_file = os.path.join(output_dir, "crawled_multi_platform.json")
        
        # 初始化反爬策略
        self.anti_strategy = AntiCrawlingStrategy()
        
        # 初始化各平台爬虫
        self.weibo_crawler = WeiboCrawler(self.anti_strategy)
        self.zhihu_crawler = ZhihuCrawler(self.anti_strategy)
        self.douyin_crawler = DouyinCrawler(self.anti_strategy)
        
        # 全部数据
        self.all_data: List[RumorItem] = []
        
        logger.info("多平台谣言爬虫初始化完成")
        
    def crawl_weibo(self, max_pages: int = 5) -> List[RumorItem]:
        """
        爬取微博辟谣内容
        
        Args:
            max_pages: 每账号最大爬取页数
            
        Returns:
            微博谣言列表
        """
        logger.info("=" * 50)
        logger.info("开始爬取微博辟谣内容")
        logger.info("目标账号: @微博辟谣、@捉谣记、@腾讯较真")
        logger.info("=" * 50)
        
        return self.weibo_crawler.crawl(max_pages)
        
    def crawl_zhihu(self, max_per_topic: int = 10) -> List[RumorItem]:
        """
        爬取知乎辟谣内容
        
        Args:
            max_per_topic: 每个话题最大爬取数量
            
        Returns:
            知乎谣言列表
        """
        logger.info("=" * 50)
        logger.info("开始爬取知乎辟谣内容")
        logger.info("搜索话题: 辟谣、谣言粉碎机、真相、假新闻、科普")
        logger.info("=" * 50)
        
        return self.zhihu_crawler.crawl(max_per_topic)
        
    def crawl_douyin(self, max_per_keyword: int = 10) -> List[RumorItem]:
        """
        爬取抖音辟谣内容
        
        Args:
            max_per_keyword: 每个关键词最大爬取数量
            
        Returns:
            抖音谣言列表
        """
        logger.info("=" * 50)
        logger.info("开始爬取抖音辟谣内容")
        logger.info("搜索关键词: 辟谣、谣言、假消息、真相、科普")
        logger.info("=" * 50)
        
        return self.douyin_crawler.crawl(max_per_keyword)
        
    def crawl_all(self, 
                  weibo_pages: int = 5, 
                  zhihu_per_topic: int = 10, 
                  douyin_per_keyword: int = 10) -> Dict:
        """
        爬取所有平台谣言内容
        
        Args:
            weibo_pages: 微博每账号最大页数
            zhihu_per_topic: 知乎每话题最大数量
            douyin_per_keyword: 抖音每关键词最大数量
            
        Returns:
            包含各平台统计信息的字典
        """
        logger.info("=" * 60)
        logger.info("开始全平台爬取")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # 爬取各平台
        weibo_data = self.crawl_weibo(weibo_pages)
        zhihu_data = self.crawl_zhihu(zhihu_per_topic)
        douyin_data = self.crawl_douyin(douyin_per_keyword)
        
        # 汇总数据
        self.all_data = weibo_data + zhihu_data + douyin_data
        
        # 统计信息
        stats = {
            "total_count": len(self.all_data),
            "weibo_count": len(weibo_data),
            "zhihu_count": len(zhihu_data),
            "douyin_count": len(douyin_data),
            "crawled_time": datetime.now().isoformat(),
            "duration_seconds": round(time.time() - start_time, 2)
        }
        
        # 保存数据
        self._save_data()
        
        logger.info("=" * 60)
        logger.info("全平台爬取完成!")
        logger.info(f"总计获取: {stats['total_count']} 条内容")
        logger.info(f"  - 微博: {stats['weibo_count']} 条")
        logger.info(f"  - 知乎: {stats['zhihu_count']} 条")
        logger.info(f"  - 抖音: {stats['douyin_count']} 条")
        logger.info(f"耗时: {stats['duration_seconds']} 秒")
        logger.info(f"数据已保存至: {self.output_file}")
        logger.info("=" * 60)
        
        return stats
        
    def _save_data(self):
        """保存数据到JSON文件"""
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 转换为字典列表
        data_list = [item.to_dict() for item in self.all_data]
        
        # 保存为JSON
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
            
        logger.info(f"数据已保存至: {self.output_file}")
        
    def load_data(self) -> List[Dict]:
        """
        加载已爬取的数据
        
        Returns:
            数据列表
        """
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []


# ==================== 使用示例 ====================

def main():
    """主函数 - 演示如何使用爬虫"""
    
    # 创建爬虫实例
    crawler = MultiPlatformCrawler(output_dir="E:\\rumor_detection\\data")
    
    # 方法1: 单独爬取某个平台
    # weibo_data = crawler.crawl_weibo(max_pages=3)
    # zhihu_data = crawler.crawl_zhihu(max_per_topic=5)
    # douyin_data = crawler.crawl_douyin(max_per_keyword=5)
    
    # 方法2: 爬取所有平台
    stats = crawler.crawl_all(
        weibo_pages=3,
        zhihu_per_topic=5,
        douyin_per_keyword=5
    )
    
    # 打印统计信息
    print("\n爬取统计:")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    
    # 加载并展示数据
    data = crawler.load_data()
    print(f"\n共加载 {len(data)} 条数据")
    if data:
        print("\n示例数据(第一条):")
        print(json.dumps(data[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
