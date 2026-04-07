# -*- coding: utf-8 -*-
"""
知乎爬虫主程序
用于采集热门话题及辟谣相关数据

依赖安装:
    pip install playwright jieba pandas requests
    playwright install chromium

使用说明:
    1. 基本使用:
        from zhihu_crawler import ZhihuCrawler
        crawler = ZhihuCrawler()
        crawler.run()
    
    2. 爬取热门问题:
        questions = crawler.crawl_hot_questions()
        
    3. 爬取问题回答:
        answers = crawler.crawl_answers(question_id)
"""

import json
import os
import random
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

import jieba
import pandas as pd
try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("警告: Playwright未安装，请运行: pip install playwright && playwright install chromium")

import zhihu_config as config


class DataCleaner:
    """数据清洗工具类"""
    
    def __init__(self):
        """初始化数据清洗器"""
        self.url_pattern = re.compile(config.URL_PATTERN)
        self.special_chars_pattern = re.compile(config.SPECIAL_CHARS_PATTERN)
        
    def clean_html_tags(self, text: str) -> str:
        """
        去除HTML标签
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 去除HTML注释
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def remove_urls(self, text: str) -> str:
        """
        去除URL链接
        
        Args:
            text: 原始文本
            
        Returns:
            去除URL后的文本
        """
        if not text:
            return ""
        return self.url_pattern.sub('', text)
    
    def remove_special_chars(self, text: str) -> str:
        """
        去除特殊字符
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 去除控制字符
        text = self.special_chars_pattern.sub('', text)
        
        # 去除常见特殊符号但保留中文标点
        text = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', text)
        
        return text
    
    def tokenize_chinese(self, text: str) -> List[str]:
        """
        使用jieba分词
        
        Args:
            text: 原始文本
            
        Returns:
            分词后的词列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_html_tags(text)
        text = self.remove_urls(text)
        text = self.remove_special_chars(text)
        
        # jieba分词
        words = jieba.lcut(text)
        
        # 过滤停用词和单字符
        stopwords = self._get_stopwords()
        words = [w for w in words if len(w) > 1 and w not in stopwords]
        
        return words
    
    def _get_stopwords(self) -> set:
        """获取停用词表"""
        stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他',
            '她', '它', '们', '什么', '这个', '那个', '怎么', '为什么',
            '可以', '可能', '应该', '但是', '因为', '所以', '如果', '虽然',
            '还', '又', '或者', '并且', '而且', '只是', '不过', '然后'
        }
        return stopwords
    
    def clean_text(self, text: str) -> str:
        """
        完整的数据清洗流程
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 依次执行各项清洗
        text = self.clean_html_tags(text)
        text = self.remove_urls(text)
        text = self.remove_special_chars(text)
        
        return text.strip()
    
    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 原始文本
            top_k: 返回前k个关键词
            
        Returns:
            关键词列表
        """
        words = self.tokenize_chinese(text)
        
        # 词频统计
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 排序取top_k
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_words[:top_k]]


class ZhihuCrawler:
    """知乎爬虫主类"""
    
    def __init__(self, headless: bool = None, use_cookie: bool = True):
        """
        初始化知乎爬虫
        
        Args:
            headless: 是否使用无头模式，默认从配置读取
            use_cookie: 是否使用Cookie登录
        """
        self.headless = headless if headless is not None else config.HEADLESS
        self.use_cookie = use_cookie
        
        # 初始化数据清洗器
        self.cleaner = DataCleaner()
        
        # 初始化浏览器相关变量
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # 设置日志
        self._setup_logging()
        
        # 确保输出目录存在
        self._ensure_directories()
        
    def _setup_logging(self):
        """配置日志"""
        log_dir = Path(config.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format=config.LOG_FORMAT,
            handlers=[
                logging.FileHandler(log_dir / config.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _ensure_directories(self):
        """确保必要的目录存在"""
        Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
        
    def _random_delay(self):
        """随机延时，避免被反爬"""
        delay = random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX)
        time.sleep(delay)
        
    def _init_browser(self):
        """初始化浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright未安装，请先安装: pip install playwright")
            
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent=config.USER_AGENT,
            viewport=config.WINDOW_SIZE
        )
        self.page = self.context.new_page()
        
        # 设置超时
        self.page.set_default_timeout(config.PAGE_LOAD_TIMEOUT * 1000)
        
        self.logger.info("浏览器初始化完成")
        
    def _load_cookies(self):
        """加载Cookie"""
        cookie_file = Path(config.COOKIE_FILE)
        if cookie_file.exists():
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                self.logger.info("Cookie加载成功")
                return True
            except Exception as e:
                self.logger.warning(f"Cookie加载失败: {e}")
        
        # 使用配置文件中的Cookie
        if config.COOKIES:
            try:
                self.context.add_cookies(config.COOKIES)
                self.logger.info("配置文件Cookie加载成功")
                return True
            except Exception as e:
                self.logger.warning(f"配置文件Cookie加载失败: {e}")
                
        return False
    
    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.logger.info("浏览器已关闭")
        
    def _save_cookies(self):
        """保存Cookie供后续使用"""
        try:
            cookies = self.context.cookies()
            cookie_file = Path(config.COOKIE_FILE)
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            self.logger.info(f"Cookie已保存到: {cookie_file}")
        except Exception as e:
            self.logger.warning(f"Cookie保存失败: {e}")
            
    def crawl_hot_questions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        爬取热门问题
        
        Args:
            limit: 最多爬取的问题数量
            
        Returns:
            问题列表，每项包含问题ID、标题、热度等信息
        """
        self.logger.info(f"开始爬取热门问题，限制: {limit}")
        
        try:
            # 访问热门榜单页面
            self.page.goto(config.ZHIHU_HOT_URL)
            self._random_delay()
            
            questions = []
            
            # 等待页面加载
            self.page.wait_for_load_state('networkidle')
            self._random_delay()
            
            # 滚动加载更多内容
            for _ in range(3):
                self.page.mouse.wheel(0, 1000)
                self._random_delay()
            
            # 解析热门问题列表
            # 知乎热门页面的实际结构可能变化，这里使用通用选择器
            hot_items = self.page.query_selector_all('.List-item, .HotItem, [data-za-id]')
            
            for i, item in enumerate(hot_items[:limit]):
                try:
                    question_data = self._parse_hot_item(item)
                    if question_data:
                        questions.append(question_data)
                except Exception as e:
                    self.logger.warning(f"解析第{i+1}个问题时出错: {e}")
                    continue
                    
            self.logger.info(f"成功爬取 {len(questions)} 条热门问题")
            
            # 保存数据
            self._save_questions(questions, "hot_questions")
            
            return questions
            
        except Exception as e:
            self.logger.error(f"爬取热门问题失败: {e}")
            raise
            
    def _parse_hot_item(self, item) -> Optional[Dict[str, Any]]:
        """
        解析热门问题项
        
        Args:
            item: 页面元素
            
        Returns:
            问题数据字典
        """
        try:
            # 尝试多种选择器获取标题和链接
            title_elem = item.query_selector('h2, .HotItem-title, .title, [class*="title"]')
            if not title_elem:
                return None
                
            title = title_elem.inner_text().strip()
            
            # 获取链接
            link_elem = item.query_selector('a[href*="/question/"]')
            if not link_elem:
                link_elem = item.query_selector('a')
                
            href = link_elem.get_attribute('href') if link_elem else ""
            
            # 提取问题ID
            question_id = ""
            if '/question/' in href:
                match = re.search(r'/question/(\d+)', href)
                if match:
                    question_id = match.group(1)
            
            # 获取热度数据
            heat_elem = item.query_selector('[class*="heat"], [class*="metric"], .HotItem-metric')
            heat = heat_elem.inner_text().strip() if heat_elem else ""
            
            return {
                'question_id': question_id,
                'title': self.cleaner.clean_text(title),
                'url': f"https://www.zhihu.com{href}" if href.startswith('/') else href,
                'heat': heat,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'hot'
            }
            
        except Exception as e:
            self.logger.debug(f"解析热门项失败: {e}")
            return None
            
    def crawl_answers(self, question_id: str, max_answers: int = None) -> List[Dict[str, Any]]:
        """
        爬取问题回答
        
        Args:
            question_id: 问题ID
            max_answers: 最大爬取回答数，默认从配置读取
            
        Returns:
            回答列表
        """
        max_answers = max_answers or config.MAX_ANSWERS_PER_QUESTION
        self.logger.info(f"开始爬取问题 {question_id} 的回答，最大: {max_answers}")
        
        try:
            # 访问问题页面
            url = f"{config.ZHIHU_QUESTION_URL}{question_id}"
            self.page.goto(url)
            self._random_delay()
            
            # 等待页面加载
            self.page.wait_for_load_state('networkidle')
            
            # 获取问题信息
            question_info = self._get_question_info()
            
            answers = []
            answer_count = 0
            
            # 持续滚动加载回答
            while answer_count < max_answers:
                # 滚动加载更多回答
                self.page.mouse.wheel(0, 2000)
                self._random_delay()
                
                # 查找回答元素
                answer_items = self.page.query_selector_all('[itemprop="answer"], .AnswerItem, .List-item')
                
                for answer_item in answer_items[answer_count:]:
                    if answer_count >= max_answers:
                        break
                        
                    try:
                        answer_data = self._parse_answer(answer_item, question_id)
                        if answer_data:
                            answers.append(answer_data)
                            answer_count += 1
                    except Exception as e:
                        self.logger.warning(f"解析回答时出错: {e}")
                        continue
                        
                # 检查是否还有更多回答
                has_more = self.page.query_selector('.Pagination, .load-more, [class*="more"]')
                if not has_more and answer_count >= len(answer_items):
                    break
                    
            self.logger.info(f"成功爬取问题 {question_id} 的 {len(answers)} 条回答")
            
            # 保存数据
            self._save_answers(answers, question_id)
            
            # 合并问题信息
            result = {
                'question': question_info,
                'answers': answers,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return answers
            
        except Exception as e:
            self.logger.error(f"爬取问题回答失败: {e}")
            raise
            
    def _get_question_info(self) -> Dict[str, Any]:
        """
        获取问题详情
        
        Returns:
            问题信息字典
        """
        try:
            # 尝试多种选择器
            title_elem = self.page.query_selector('h1, [class*="QuestionHeader"] h1, .Question-title')
            title = title_elem.inner_text().strip() if title_elem else ""
            
            # 获取描述
            desc_elem = self.page.query_selector('[class*="QuestionHeader"] [class*="detail"], .QuestionHeader-detail')
            description = desc_elem.inner_text().strip() if desc_elem else ""
            
            # 获取热度
            heat_elem = self.page.query_selector('[class*="NumberBoard"], [class*="ViewAll"]')
            heat = heat_elem.inner_text().strip() if heat_elem else ""
            
            return {
                'title': self.cleaner.clean_text(title),
                'description': self.cleaner.clean_text(description),
                'heat': heat
            }
            
        except Exception as e:
            self.logger.warning(f"获取问题信息失败: {e}")
            return {}
            
    def _parse_answer(self, answer_item, question_id: str) -> Optional[Dict[str, Any]]:
        """
        解析回答项
        
        Args:
            answer_item: 回答元素
            question_id: 问题ID
            
        Returns:
            回答数据字典
        """
        try:
            # 获取回答内容
            content_elem = answer_item.query_selector(
                '[itemprop="text"], .RichText, [class*="content"], .AnswerItem-content'
            )
            content = content_elem.inner_text().strip() if content_elem else ""
            
            if not content:
                return None
                
            # 获取作者信息
            author_elem = answer_item.query_selector(
                '[class*="Author"], [itemprop="author"], .AnswerItem-author'
            )
            author = author_elem.inner_text().strip() if author_elem else ""
            
            # 获取点赞数
            vote_elem = answer_item.query_selector(
                '[class*="vote"], [class*="like"], .AnswerItem-voteCount'
            )
            votes = vote_elem.inner_text().strip() if vote_elem else "0"
            
            # 提取数字
            votes = re.search(r'(\d+)', votes)
            votes = votes.group(1) if votes else "0"
            
            # 清洗内容
            cleaned_content = self.cleaner.clean_text(content)
            
            # 分词处理
            words = self.cleaner.tokenize_chinese(cleaned_content)
            
            # 关键词提取
            keywords = self.cleaner.extract_keywords(cleaned_content)
            
            return {
                'question_id': question_id,
                'author': self.cleaner.clean_text(author),
                'content': cleaned_content,
                'content_raw': content,
                'votes': int(votes),
                'words': words,
                'keywords': keywords,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            self.logger.debug(f"解析回答失败: {e}")
            return None
            
    def crawl_rumors(self, keywords: List[str] = None, max_per_keyword: int = 20) -> List[Dict[str, Any]]:
        """
        爬取辟谣相关话题
        
        Args:
            keywords: 搜索关键词列表，默认从配置读取
            max_per_keyword: 每个关键词最大爬取数量
            
        Returns:
            辟谣相关数据列表
        """
        keywords = keywords or config.RUMOR_KEYWORDS
        self.logger.info(f"开始爬取辟谣相关话题，关键词: {keywords}")
        
        all_results = []
        
        for keyword in keywords:
            try:
                self.logger.info(f"搜索关键词: {keyword}")
                
                # 访问搜索页面
                search_url = f"{config.ZHIHU_SEARCH_URL}?q={keyword}&type=content"
                self.page.goto(search_url)
                self._random_delay()
                
                # 等待加载
                self.page.wait_for_load_state('networkidle')
                
                # 滚动加载
                for _ in range(2):
                    self.page.mouse.wheel(0, 1000)
                    self._random_delay()
                    
                # 解析搜索结果
                results = self._parse_search_results(keyword, max_per_keyword)
                all_results.extend(results)
                
                self._random_delay()
                
            except Exception as e:
                self.logger.warning(f"搜索关键词 {keyword} 时出错: {e}")
                continue
                
        self.logger.info(f"成功爬取 {len(all_results)} 条辟谣相关数据")
        
        # 保存数据
        self._save_answers(all_results, "rumor_search")
        
        return all_results
        
    def _parse_search_results(self, keyword: str, max_results: int) -> List[Dict[str, Any]]:
        """
        解析搜索结果
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表
        """
        results = []
        
        try:
            # 查找结果项
            result_items = self.page.query_selector_all(
                '.List, .SearchResult, [class*="SearchItem"], .List-item'
            )
            
            for item in result_items[:max_results]:
                try:
                    # 获取标题
                    title_elem = item.query_selector('h2, [class*="title"], a[href*="/question/"]')
                    title = title_elem.inner_text().strip() if title_elem else ""
                    
                    if not title:
                        continue
                        
                    # 获取链接
                    link_elem = item.query_selector('a[href*="/question/"]')
                    href = link_elem.get_attribute('href') if link_elem else ""
                    
                    # 提取问题ID
                    question_id = ""
                    if '/question/' in href:
                        match = re.search(r'/question/(\d+)', href)
                        if match:
                            question_id = match.group(1)
                            
                    # 获取摘要
                    snippet_elem = item.query_selector('[class*="snippet"], [class*="content"], p')
                    snippet = snippet_elem.inner_text().strip() if snippet_elem else ""
                    
                    # 标注辟谣相关
                    rumor_label = self._detect_rumor_label(title + " " + snippet)
                    
                    result = {
                        'keyword': keyword,
                        'question_id': question_id,
                        'title': self.cleaner.clean_text(title),
                        'snippet': self.cleaner.clean_text(snippet),
                        'url': f"https://www.zhihu.com{href}" if href.startswith('/') else href,
                        'rumor_type': rumor_label['type'],
                        'stance': rumor_label['stance'],
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'rumor_search'
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"解析搜索结果失败: {e}")
            
        return results
        
    def _detect_rumor_label(self, text: str) -> Dict[str, str]:
        """
        基于文本内容自动标注谣言类型和立场
        
        Args:
            text: 文本内容
            
        Returns:
            标注结果 {'type': '谣言类型', 'stance': '立场'}
        """
        text = text.lower()
        
        # 谣言类型检测关键词
        true_keywords = ['真的', '属实', '证实', '确实', '真', '真消息']
        false_keywords = ['谣言', '假的', '不实', '虚假', '造谣', '传谣', 'fake', 'false']
        unverified_keywords = ['待核实', '未证实', '不确定', '疑似', '可能']
        
        # 立场检测关键词
        support_keywords = ['支持', '赞成', '认可', '肯定', '应该', '同意']
        oppose_keywords = ['反对', '质疑', '否定', '不应该', '不同意', '批评']
        
        # 检测谣言类型
        if any(kw in text for kw in false_keywords):
            rumor_type = 'false'
        elif any(kw in text for kw in true_keywords):
            rumor_type = 'true'
        else:
            rumor_type = 'unverified'
            
        # 检测立场
        if any(kw in text for kw in support_keywords):
            stance = 'support'
        elif any(kw in text for kw in oppose_keywords):
            stance = 'oppose'
        else:
            stance = 'neutral'
            
        return {
            'type': config.RUMOR_TYPES.get(rumor_type, '未证实'),
            'stance': config.STANCE_TYPES.get(stance, '中立')
        }
        
    def _save_questions(self, questions: List[Dict], prefix: str):
        """保存问题数据"""
        if not questions:
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{timestamp}.json"
        filepath = Path(config.OUTPUT_DIR) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"问题数据已保存到: {filepath}")
        
        # 同时保存为CSV
        csv_file = filepath.with_suffix('.csv')
        df = pd.DataFrame(questions)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        self.logger.info(f"问题数据已保存到: {csv_file}")
        
    def _save_answers(self, answers: List[Dict], question_id: str):
        """保存回答数据"""
        if not answers:
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if question_id == "rumor_search":
            prefix = "rumor_search"
        else:
            prefix = f"answers_{question_id}"
            
        filename = f"{prefix}_{timestamp}.json"
        filepath = Path(config.OUTPUT_DIR) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"回答数据已保存到: {filepath}")
        
        # 同时保存为CSV
        csv_file = filepath.with_suffix('.csv')
        df = pd.DataFrame(answers)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        self.logger.info(f"回答数据已保存到: {csv_file}")
        
    def run(self, crawl_hot: bool = True, crawl_rumors: bool = True):
        """
        运行爬虫
        
        Args:
            crawl_hot: 是否爬取热门问题
            crawl_rumors: 是否爬取辟谣相关
        """
        try:
            self._init_browser()
            
            # 尝试加载Cookie
            if self.use_cookie:
                self._load_cookies()
                
            results = {}
            
            if crawl_hot:
                results['hot_questions'] = self.crawl_hot_questions()
                
            if crawl_rumors:
                results['rumors'] = self.crawl_rumors()
                
            # 保存Cookie
            if self.use_cookie:
                self._save_cookies()
                
            self.logger.info("爬虫运行完成")
            return results
            
        except Exception as e:
            self.logger.error(f"爬虫运行失败: {e}")
            raise
            
        finally:
            self.close()


# ==================== 便捷函数 ====================

def crawl_hot_questions() -> List[Dict[str, Any]]:
    """
    爬取热门问题
    
    Returns:
        热门问题列表
    """
    crawler = ZhihuCrawler()
    try:
        crawler._init_browser()
        crawler._load_cookies()
        questions = crawler.crawl_hot_questions()
        return questions
    finally:
        crawler.close()


def crawl_answers(question_id: str) -> List[Dict[str, Any]]:
    """
    爬取问题回答
    
    Args:
        question_id: 问题ID
        
    Returns:
        回答列表
    """
    crawler = ZhihuCrawler()
    try:
        crawler._init_browser()
        crawler._load_cookies()
        answers = crawler.crawl_answers(question_id)
        return answers
    finally:
        crawler.close()


def crawl_rumors() -> List[Dict[str, Any]]:
    """
    爬取辟谣相关话题
    
    Returns:
        辟谣相关数据列表
    """
    crawler = ZhihuCrawler()
    try:
        crawler._init_browser()
        crawler._load_cookies()
        results = crawler.crawl_rumors()
        return results
    finally:
        crawler.close()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("知乎爬虫 - 使用示例")
    print("=" * 50)
    
    # 示例1: 爬取热门问题
    print("\n[示例1] 爬取热门问题...")
    try:
        hot_questions = crawl_hot_questions()
        print(f"成功爬取 {len(hot_questions)} 条热门问题")
        for q in hot_questions[:3]:
            print(f"  - {q.get('title', '')[:50]}...")
    except Exception as e:
        print(f"爬取热门问题失败: {e}")
        
    # 示例2: 爬取指定问题的回答
    print("\n[示例2] 爬取问题回答...")
    print("  请提供问题ID，例如: crawl_answers('1234567890')")
    
    # 示例3: 爬取辟谣相关
    print("\n[示例3] 爬取辟谣相关数据...")
    try:
        rumors = crawl_rumors()
        print(f"成功爬取 {len(rumors)} 条辟谣相关数据")
    except Exception as e:
        print(f"爬取辟谣数据失败: {e}")
        
    print("\n" + "=" * 50)
    print("完整使用说明请查看代码注释")
    print("=" * 50)
