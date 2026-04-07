# -*- coding: utf-8 -*-
"""
知乎爬虫配置文件
包含爬虫所需的各种配置参数
"""

# ==================== 基础配置 ====================
# 目标URL
ZHIHU_HOT_URL = "https://www.zhihu.com/hot"
ZHIHU_SEARCH_URL = "https://www.zhihu.com/search"
ZHIHU_QUESTION_URL = "https://www.zhihu.com/question/"

# 输出目录
OUTPUT_DIR = "E:\\rumor_detection\\data"
LOG_DIR = "E:\\rumor_detection\\logs"

# ==================== 爬虫配置 ====================
# 请求间隔（秒），避免被反爬
REQUEST_DELAY_MIN = 2  # 最小间隔
REQUEST_DELAY_MAX = 5  # 最大间隔

# 页面加载超时（秒）
PAGE_LOAD_TIMEOUT = 30

# 浏览器配置
HEADLESS = True  # 无头模式运行
WINDOW_SIZE = (1920, 1080)

# 最大重试次数
MAX_RETRIES = 3

# 每次爬取最多回答数
MAX_ANSWERS_PER_QUESTION = 20

# ==================== 数据标注配置 ====================
# 谣言类型标注
RUMOR_TYPES = {
    "true": "真",
    "false": "假", 
    "unverified": "未证实"
}

# 立场倾向标注
STANCE_TYPES = {
    "support": "支持",
    "oppose": "反对",
    "neutral": "中立"
}

# 辟谣相关关键词（用于搜索筛选）
RUMOR_KEYWORDS = [
    "辟谣", "谣言", "假消息", "不实信息", "虚假",
    "真相", "事实", "证实", "澄清", "Fake News",
    "Misinformation", "Rumors"
]

# ==================== Cookie登录配置 ====================
# 手动填入你的知乎Cookie（可选，用于绕过登录限制）
# 格式: {"name": "cookie_name", "value": "cookie_value"}
COOKIES = []

# 或者使用cookie文件路径
COOKIE_FILE = "E:\\rumor_detection\\utils\\crawler\\zhihu_cookies.json"

# ==================== 数据清洗配置 ====================
# 需要过滤的HTML标签
HTML_TAGS_TO_REMOVE = [
    'script', 'style', 'iframe', 'noscript', 'br', 'hr'
]

# 需要过滤的特殊字符模式
SPECIAL_CHARS_PATTERN = r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]'

# URL正则表达式
URL_PATTERN = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "zhihu_crawler.log"

# ==================== User-Agent ====================
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
