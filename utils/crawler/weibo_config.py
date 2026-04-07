# -*- coding: utf-8 -*-
"""
微博爬虫配置文件
包含Cookie、User-Agent、反爬策略等配置
"""

# ============================================
# 浏览器配置
# ============================================

# User-Agent池 - 建议定期更新
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ============================================
# 微博Cookie配置
# ============================================
# Cookie已保存在 weibo_cookies.json 文件中
# 爬虫会自动读取该文件

# 如果需要手动配置，请填入完整的Cookie字符串
# 获取方法：浏览器登录微博 -> F12 -> Application -> Cookies -> weibo.com

# ============================================
# 爬虫行为配置
# ============================================

# 请求间隔（秒）- 避免被反爬，增加间隔更安全
REQUEST_DELAY = {
    "min": 5,
    "max": 10
}

# 单次请求最大重试次数
MAX_RETRIES = 3

# 页面加载超时（秒）
PAGE_TIMEOUT = 30

# 滚动加载次数（热门话题需要滚动加载更多）
SCROLL_TIMES = 3

# 每次滚动等待时间（秒）
SCROLL_WAIT = 2

# ============================================
# 数据存储配置
# ============================================

# 输出目录
OUTPUT_DIR = "E:\\rumor_detection\\data"

# 输出文件格式
OUTPUT_FORMAT = "json"  # json 或 csv

# ============================================
# 微博URL配置
# ============================================

# 热门话题榜
HOT_TOPICS_URL = "https://weibo.com/ajax/side/hotSearch"

# 辟谣账号主页
RUMOR_DENIAL_ACCOUNT = "https://weibo.com/u/1938327413"  # @微博辟谣

# 辟谣内容搜索
RUMOR_SEARCH_URL = "https://weibo.com/ajax/statuses/mymblog"

# ============================================
# 标注体系配置
# ============================================

# 谣言类型
RUMOR_TYPES = {
    "真": "truth",
    "假": "fake", 
    "未证实": "unverified"
}

# 立场倾向
STANCE_TYPES = {
    "支持": "support",
    "反对": "oppose",
    "中立": "neutral"
}

# ============================================
# 反爬策略配置
# ============================================

# 启用随机User-Agent
USE_RANDOM_UA = True

# 启用随机请求间隔
USE_RANDOM_DELAY = True

# 启用代理（可选）
USE_PROXY = False
PROXY_LIST = [
    # "http://proxy1:port",
    # "http://proxy2:port",
]

# Selenium WebDriver配置
WEBDRIVER_OPTIONS = {
    "headless": True,  # 默认无头模式
    "disable_images": True,  # 禁用图片加速爬取
    "window_size": (1920, 1080),
    "page_load_strategy": "normal"
}

# ============================================
# Playwright配置（可选）
# ============================================

PLAYWRIGHT_CONFIG = {
    "headless": True,  # 默认无头模式
    "slow_mo": 100,  # 毫秒 - 减少延迟加快爬取
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": USER_AGENTS[0]
}
