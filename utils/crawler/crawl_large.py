# -*- coding: utf-8 -*-
"""大规模微博搜索爬虫 - 增强版"""
import json
import sys
import time
import random
import urllib.parse
from pathlib import Path
import re

sys.stdout.reconfigure(encoding='utf-8')

def load_cookies():
    cookie_file = Path(__file__).parent / "weibo_cookies.json"
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    return {c['name']: c['value'] for c in cookies if 'name' in c and 'value' in c}

def clean_weibo_text(text):
    """清洗微博文本"""
    if not text:
        return ""
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除URL
    text = re.sub(r'http[s]?://\S+', '', text)
    # 去除@用户
    text = re.sub(r'@[\w]+', '', text)
    # 去除表情符号
    text = re.sub(r'\[([^]]+)\]', r'\1', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def search_and_crawl(keywords, cookie_dict, fetcher, max_per_keyword=100):
    """搜索关键词并爬取"""
    all_results = []
    seen_content = set()  # 去重

    for kw in keywords:
        print(f"\n[搜索] {kw}...")
        encoded = urllib.parse.quote(kw)

        # 搜索更多页
        for page in range(1, 11):  # 增加到10页
            url = f"https://s.weibo.com/weibo?q={encoded}&wvr=6&b=1&page={page}"

            try:
                response = fetcher.get(url, cookies=cookie_dict, timeout=30, impersonate="chrome")

                if response.status != 200:
                    break

                html = response.html_content
                if not html or len(html) < 1000:
                    print(f"  页{page}: 内容为空，跳过")
                    break

                # 提取内容 - 多种模式
                patterns = [
                    # 微博内容区域
                    r'<div class="content">.*?<p class="txt">(.*?)</p>',
                    r'"text":"(.*?)"',
                    # 通用匹配
                    r'feed_list_content[^>]*>([^<]+)',
                    r'content_text[^>]*>([^<]+)',
                ]

                page_count = 0
                for pattern in patterns:
                    matches = re.findall(pattern, html, re.DOTALL)
                    for m in matches:
                        text = clean_weibo_text(m)
                        if len(text) > 15 and text not in seen_content:
                            seen_content.add(text)
                            all_results.append({
                                "keyword": kw,
                                "content": text[:500],
                                "source": "weibo_search",
                                "platform": "微博",
                                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            page_count += 1

                print(f"  页{page}: +{page_count} 条")

                # 随机延迟 3-6秒，避免被封
                time.sleep(random.uniform(3, 6))

                if len(all_results) >= max_per_keyword * len(keywords):
                    break

            except Exception as e:
                print(f"  [错误] 页{page}: {e}")
                time.sleep(5)
                continue

        print(f"  [累计] {len(all_results)} 条")

    return all_results

def main():
    from scrapling import Fetcher

    cookie_dict = load_cookies()
    fetcher = Fetcher()

    # 大幅扩展关键词列表 - 涵盖更多话题领域
    keywords = [
        # ===== 谣言/辟谣相关 =====
        "辟谣", "谣言", "假新闻", "假消息", "造谣", "传谣",
        "不实信息", "网络谣言", "虚假信息", "谣言澄清",
        "官方澄清", "真相", "假象", "诈骗", "骗局",

        # ===== 热搜话题 =====
        "热搜", "热门", "头条", "爆料", "曝光",
        "震惊", "紧急", "突发", "重磅", "刚刚",

        # ===== 社会热点 =====
        "疫情", "口罩", "疫苗", "核酸", "隔离",
        "地震", "洪水", "台风", "暴雨", "灾害",
        "车祸", "火灾", "事故", "爆炸", "坍塌",
        "犯罪", "逮捕", "被抓", "逃逸", "自首",
        "维权", "投诉", "曝光台", "举报", "黑幕",

        # ===== 民生相关 =====
        "工资", "养老金", "社保", "医保", "失业",
        "房价", "买房", "租房", "物业", "拆迁",
        "教育", "高考", "中考", "培训", "学费",
        "医疗", "医院", "医生", "看病", "药品",

        # ===== 科技数码 =====
        "手机", "电脑", "华为", "苹果", "小米",
        "5G", "芯片", "系统", "漏洞", "病毒",

        # ===== 财经投资 =====
        "股票", "基金", "理财", "投资", "亏损",
        "诈骗", "非法集资", "跑路", "爆雷", "崩盘",

        # ===== 食品安全 =====
        "食品", "添加剂", "过期", "变质", "有毒",
        "致癌", "农药", "重金属", "污染", "黑心",

        # ===== 明星八卦 =====
        "明星", "网红", "出轨", "离婚", "结婚",
        "吸毒", "嫖娼", "违法犯罪", "封杀", "道歉",

        # ===== 国际关系 =====
        "美国", "中国", "日本", "俄罗斯", "乌克兰",
        "战争", "冲突", "制裁", "外交", "谈判",

        # ===== 健康养生 =====
        "养生", "保健", "偏方", "致癌", "食物相克",
        "减肥", "美容", "整形", "养生", "长寿",
    ]

    print(f"[INFO] 开始大规模搜索，共 {len(keywords)} 个关键词...")
    print(f"[INFO] 每个关键词最多 {100} 条，每页10页")

    results = search_and_crawl(keywords, cookie_dict, fetcher, max_per_keyword=100)

    # 最终去重
    unique_results = []
    seen = set()
    for r in results:
        key = r["content"][:50]
        if key not in seen and len(r["content"]) > 15:
            seen.add(key)
            unique_results.append(r)

    print(f"\n[结果] 共获取 {len(unique_results)} 条数据")

    # 保存
    output = Path(__file__).parent.parent / "data" / "crawled_multi_platform.json"

    # 如果已存在，先合并
    if output.exists():
        with open(output, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        print(f"[合并] 已有 {len(existing_data)} 条数据")

        # 合并并去重
        existing_keys = set(r["content"][:50] for r in existing_data)
        for r in unique_results:
            if r["content"][:50] not in existing_keys:
                existing_data.append(r)
        unique_results = existing_data
        print(f"[合并后] 共 {len(unique_results)} 条数据")

    with open(output, 'w', encoding='utf-8') as f:
        json.dump(unique_results, f, ensure_ascii=False, indent=2)

    print(f"[保存] {output}")

    # 统计
    print(f"\n[统计]")
    print(f"  总数: {len(unique_results)}")

    # 显示示例
    print("\n[示例]")
    for i, r in enumerate(unique_results[:5]):
        print(f"  {i+1}. {r['content'][:60]}...")

if __name__ == "__main__":
    main()
