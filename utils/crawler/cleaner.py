# -*- coding: utf-8 -*-
"""
微博数据清洗模块
使用jieba进行中文分词和文本清洗
"""

import re
import os
import json
from typing import List, Dict, Optional, Tuple

# 尝试导入jieba，如果未安装则提供替代方案
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("警告: jieba未安装，文本清洗功能将受限。请运行: pip install jieba")


# ============================================
# 噪声字符正则表达式
# ============================================

# HTML标签正则
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

# URL链接正则
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
)

# 微博@用户正则
MENTION_PATTERN = re.compile(r'@[\w\u4e00-\u9fa5]+')

# 微博话题正则
TOPIC_PATTERN = re.compile(r'#[\w\u4e00-\u9fa5]+#')

# 表情符号正则（如[哈哈]、[泪]等）
EMOJI_PATTERN = re.compile(r'\[[\w\u4e00-\u9fa5]+\]')

# 特殊符号正则（保留中文、英文、数字）
SPECIAL_CHARS_PATTERN = re.compile(r'[^\w\s\u4e00-\u9fa5]')

# 空白字符正则
WHITESPACE_PATTERN = re.compile(r'\s+')

# 转发标记正则
RETWEET_PATTERN = re.compile(r'//@[\w\u4e00-\u9fa5]+:.*')

# 赞转评数字正则（如赞[100] 转[20]评[5]）
DIGIT_PATTERN = re.compile(r'赞\[\d+\]\s*转\[\d+\]\s*评\[\d+\]')


def init_jieba(user_dict_path: Optional[str] = None):
    """
    初始化jieba分词器
    
    Args:
        user_dict_path: 用户自定义词典路径（可选）
    """
    if JIEBA_AVAILABLE:
        if user_dict_path and os.path.exists(user_dict_path):
            jieba.load_userdict(user_dict_path)
        # 添加网络流行词
        jieba.add_word('微博辟谣')
        jieba.add_word('谣言')
        jieba.add_word('辟谣')
        jieba.add_word('假新闻')
        jieba.add_word('真新闻')


def clean_text(text: str, remove_emoji: bool = True, remove_topic: bool = True) -> str:
    """
    清洗文本内容
    
    Args:
        text: 原始文本
        remove_emoji: 是否移除表情符号
        remove_topic: 是否移除话题标签
    
    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    
    # 转换为字符串（处理可能的None）
    text = str(text)
    
    # 1. 移除HTML标签
    text = HTML_TAG_PATTERN.sub('', text)
    
    # 2. 移除URL链接
    text = URL_PATTERN.sub('', text)
    
    # 3. 移除@提及
    text = MENTION_PATTERN.sub('', text)
    
    # 4. 移除话题标签（可选）
    if remove_topic:
        text = TOPIC_PATTERN.sub('', text)
    
    # 5. 移除表情符号（可选）
    if remove_emoji:
        text = EMOJI_PATTERN.sub('', text)
    
    # 6. 移除转发标记和内容
    text = RETWEET_PATTERN.sub('', text)
    
    # 7. 移除赞转评数字
    text = DIGIT_PATTERN.sub('', text)
    
    # 8. 移除多余空白字符
    text = WHITESPACE_PATTERN.sub(' ', text)
    
    # 9. 去除首尾空白
    text = text.strip()
    
    return text


def tokenize(text: str, use_jieba: bool = True) -> List[str]:
    """
    分词处理
    
    Args:
        text: 输入文本
        use_jieba: 是否使用jieba分词
    
    Returns:
        分词后的词列表
    """
    if not text:
        return []
    
    text = clean_text(text)
    
    if not text:
        return []
    
    if JIEBA_AVAILABLE and use_jieba:
        # 使用jieba分词
        words = list(jieba.cut(text))
        # 过滤空字符串和纯空白
        words = [w for w in words if w.strip()]
        return words
    else:
        # 简单按空格分词
        return text.split()


def extract_keywords(text: str, topk: int = 10) -> List[Tuple[str, float]]:
    """
    提取关键词（使用TF-IDF权重）
    
    Args:
        text: 输入文本
        topk: 返回前k个关键词
    
    Returns:
        [(关键词, 权重), ...]
    """
    if not text or not JIEBA_AVAILABLE:
        return []
    
    try:
        import jieba.analyse
        # 使用TF-IDF算法提取关键词
        keywords = jieba.analyse.extract_tags(text, topK=topk, withWeight=True)
        return keywords
    except Exception as e:
        print(f"关键词提取失败: {e}")
        return []


def clean_weibo_data(weibo_item: Dict, add_keywords: bool = True) -> Dict:
    """
    清洗单条微博数据
    
    Args:
        weibo_item: 原始微博数据字典
        add_keywords: 是否添加关键词字段
    
    Returns:
        清洗后的微博数据字典
    """
    cleaned = {
        "status_id": weibo_item.get("id", weibo_item.get("status_id", "")),
        "mid": weibo_item.get("mid", ""),
        "text": weibo_item.get("text", weibo_item.get("content", "")),
        "text_cleaned": "",
        "text_keywords": [],
        "created_at": weibo_item.get("created_at", ""),
        "source": weibo_item.get("source", ""),
        "user_id": weibo_item.get("user", {}).get("id", "") if isinstance(weibo_item.get("user"), dict) else "",
        "user_name": weibo_item.get("user", {}).get("screen_name", "") if isinstance(weibo_item.get("user"), dict) else "",
        "reposts_count": weibo_item.get("reposts_count", 0),
        "comments_count": weibo_item.get("comments_count", 0),
        "attitudes_count": weibo_item.get("attitudes_count", 0),
        "parent_id": weibo_item.get("parent_id", ""),
        # 标注字段
        "rumor_type": "",  # 真/假/未证实
        "stance": "",       # 支持/反对/中立
    }
    
    # 清洗文本
    cleaned["text_cleaned"] = clean_text(cleaned["text"])
    
    # 提取关键词
    if add_keywords:
        keywords = extract_keywords(cleaned["text_cleaned"])
        cleaned["text_keywords"] = [k[0] for k in keywords]
    
    return cleaned


def clean_batch_data(data_list: List[Dict], add_keywords: bool = True) -> List[Dict]:
    """
    批量清洗微博数据
    
    Args:
        data_list: 原始微博数据列表
        add_keywords: 是否添加关键词字段
    
    Returns:
        清洗后的微博数据列表
    """
    if JIEBA_AVAILABLE:
        init_jieba()
    
    return [clean_weibo_data(item, add_keywords) for item in data_list]


def save_cleaned_data(data: List[Dict], output_path: str, format: str = "json"):
    """
    保存清洗后的数据
    
    Args:
        data: 清洗后的数据
        output_path: 输出文件路径
        format: 输出格式 (json/csv)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if format == "json":
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif format == "csv":
        import csv
        if data:
            keys = data[0].keys()
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
    
    print(f"数据已保存至: {output_path}")


def load_raw_data(file_path: str) -> List[Dict]:
    """
    加载原始数据
    
    Args:
        file_path: 数据文件路径
    
    Returns:
        数据列表
    """
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.endswith('.json'):
            return json.load(f)
        elif file_path.endswith('.csv'):
            import csv
            reader = csv.DictReader(f)
            return list(reader)
    
    return []


# ============================================
# 传播树构建
# ============================================

def build_propagation_tree(status_id: str, parent_id: str, tree_data: Optional[Dict] = None) -> Dict:
    """
    构建单条微博的传播树节点
    
    Args:
        status_id: 当前微博ID
        parent_id: 父微博ID（被转发的原微博ID）
        tree_data: 现有的传播树数据（用于累加）
    
    Returns:
        传播树节点信息
    """
    node = {
        "status_id": status_id,
        "parent_id": parent_id if parent_id else "",
        "is_root": not bool(parent_id),  # 是否为根节点
        "children": [],  # 子节点列表
        "depth": 0,      # 传播深度
        "propagation_path": []  # 传播路径
    }
    
    if tree_data is None:
        tree_data = {}
    
    # 更新树结构
    if status_id not in tree_data:
        tree_data[status_id] = node
    
    # 如果有父节点，更新父子关系
    if parent_id:
        if parent_id in tree_data:
            if status_id not in tree_data[parent_id]["children"]:
                tree_data[parent_id]["children"].append(status_id)
        else:
            # 父节点尚不存在，先创建
            tree_data[parent_id] = {
                "status_id": parent_id,
                "parent_id": "",
                "is_root": True,
                "children": [status_id],
                "depth": 0,
                "propagation_path": []
            }
    
    return node


def build_full_propagation_tree(weibo_list: List[Dict]) -> Dict:
    """
    根据微博列表构建完整的传播树
    
    Args:
        weibo_list: 微博数据列表，每条需包含status_id和parent_id
    
    Returns:
        完整的传播树结构 {status_id: node_info}
    """
    tree = {}
    
    for weibo in weibo_list:
        status_id = str(weibo.get("status_id", ""))
        parent_id = str(weibo.get("parent_id", ""))
        
        if status_id:
            build_propagation_tree(status_id, parent_id, tree)
    
    # 计算每个节点的深度
    def calculate_depth(node_id: str, current_depth: int = 0):
        if node_id not in tree:
            return
        tree[node_id]["depth"] = current_depth
        
        for child_id in tree[node_id]["children"]:
            calculate_depth(child_id, current_depth + 1)
    
    # 从根节点开始计算
    for node_id, node in tree.items():
        if node["is_root"]:
            calculate_depth(node_id, 0)
    
    return tree


def get_propagation_chain(status_id: str, tree: Dict) -> List[str]:
    """
    获取某条微博的完整传播链
    
    Args:
        status_id: 微博ID
        tree: 传播树
    
    Returns:
        从根节点到当前节点的ID列表
    """
    chain = [status_id]
    current_id = status_id
    
    while current_id in tree and tree[current_id]["parent_id"]:
        parent_id = tree[current_id]["parent_id"]
        chain.append(parent_id)
        current_id = parent_id
    
    return list(reversed(chain))


# ============================================
# 辅助函数
# ============================================

def get_text_stats(text: str) -> Dict:
    """
    获取文本统计信息
    
    Args:
        text: 输入文本
    
    Returns:
        统计信息字典
    """
    text_cleaned = clean_text(text)
    words = tokenize(text_cleaned)
    
    return {
        "raw_length": len(text),
        "cleaned_length": len(text_cleaned),
        "word_count": len(words),
        "has_url": bool(URL_PATTERN.search(text)),
        "has_mention": bool(MENTION_PATTERN.search(text)),
        "has_topic": bool(TOPIC_PATTERN.search(text)),
        "has_emoji": bool(EMOJI_PATTERN.search(text))
    }


if __name__ == "__main__":
    # 测试代码
    test_text = "这是测试微博内容，包含链接http://t.cn/xxx和@用户名，还有#话题#以及[哈哈]表情。//@转发用户:原微博内容"
    
    print("原始文本:", test_text)
    print("清洗后:", clean_text(test_text))
    print("分词结果:", tokenize(test_text))
    print("关键词:", extract_keywords(test_text, topk=5))
    print("统计信息:", get_text_stats(test_text))
