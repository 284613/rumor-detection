# 多平台谣言爬虫 - 使用说明

## 文件位置

- 爬虫代码: `E:\rumor_detection\utils\crawler\multi_platform_crawler.py`
- 输出数据: `E:\rumor_detection\data\crawled_multi_platform.json`

## 环境配置

### 1. 安装依赖

```bash
pip install -r E:\rumor_detection\utils\crawler\requirements.txt
```

### 2. Python版本

- Python 3.8+
- 推荐 Python 3.10+

## 使用方法

### 方法1: 运行完整爬取（爬取所有平台）

```python
from multi_platform_crawler import MultiPlatformCrawler

# 创建爬虫实例
crawler = MultiPlatformCrawler(output_dir="E:\\rumor_detection\\data")

# 爬取所有平台
stats = crawler.crawl_all(
    weibo_pages=3,        # 微博每账号最大页数
    zhihu_per_topic=5,     # 知乎每话题最大数量
    douyin_per_keyword=5   # 抖音每关键词最大数量
)

print(stats)
```

### 方法2: 单独爬取某个平台

```python
# 只爬取微博
weibo_data = crawler.crawl_weibo(max_pages=5)

# 只爬取知乎
zhihu_data = crawler.crawl_zhihu(max_per_topic=10)

# 只爬取抖音
douyin_data = crawler.crawl_douyin(max_per_keyword=10)
```

### 方法3: 从命令行运行

```bash
python E:\rumor_detection\utils\crawler\multi_platform_crawler.py
```

## 数据输出格式

数据保存为JSON格式，包含以下字段：

```json
{
  "platform": "微博/知乎/抖音",
  "content": "内容正文",
  "title": "标题",
  "author": "作者/发布者",
  "publish_time": "发布时间",
  "url": "原文链接",
  "like_count": "点赞数",
  "comment_count": "评论数",
  "share_count": "分享数",
  "crawled_time": "爬取时间",
  "tags": ["标签列表"]
}
```

## 支持的平台

### 微博
- @微博辟谣
- @捉谣记
- @腾讯较真

### 知乎
- 搜索话题: 辟谣、谣言粉碎机、真相、假新闻、科普

### 抖音
- 搜索关键词: 辟谣、谣言、假消息、真相、科普

## 反爬策略

代码内置以下反爬策略：

1. **User-Agent轮换**: 随机选择浏览器标识
2. **请求间隔**: 2-5秒随机延迟
3. **请求头伪装**: 模拟真实浏览器请求
4. **指数退避重试**: 请求失败时自动重试

## ⚠️ 重要说明

### 关于真实爬取

当前代码为**框架实现**，使用模拟数据进行演示。要实现真实爬取，需要：

#### 微博
- 需要登录Cookie
- 建议使用微博移动端API (`m.weibo.cn`)
- 可能需要处理验证码

#### 知乎
- 需要登录Cookie
- 知乎API需要token
- 建议使用知乎App API

#### 抖音
- 反爬最严格
- 需要设备指纹
- 需要签名算法(X-Gorgon, X-Bogus)
- 建议使用抖音开放平台API

### 建议方案

1. **使用Selenium/Playwright**: 模拟真实浏览器操作
2. **使用代理IP池**: 避免IP被封
3. **使用打码平台**: 处理验证码
4. **官方API**: 申请各平台开发者账号获取API权限

## 示例: 扩展真实爬取

```python
class WeiboCrawler:
    def _crawl_account(self, account: Dict, max_pages: int) -> List[RumorItem]:
        # 真实API调用示例
        import requests
        
        url = f"https://m.weibo.cn/api/container/getIndex"
        params = {
            "uid": account["id"],
            "containerid": f"107603{account['id']}",
            "page": 1
        }
        
        # 需要先设置Cookie
        cookies = {"SUB": "your_weibo_cookie_here"}
        
        response = self.session.get(url, params=params, cookies=cookies)
        data = response.json()
        
        # 解析数据...
        # return items
```

## 常见问题

### Q: 为什么爬取不到真实数据?
A: 当前版本是框架，需要配置登录Cookie或使用官方API才能获取真实数据。

### Q: 如何提高爬取速度?
A: 可以增加并发数，但建议设置合理的请求间隔以避免被封禁。

### Q: 数据如何存储?
A: 默认保存为JSON文件，可根据需要修改为数据库存储。
