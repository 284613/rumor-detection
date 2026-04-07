#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微博谣言数据清洗与标注脚本
功能：
1. 去除HTML标签、特殊符号、链接等噪声
2. 使用jieba提取关键词
3. 添加谣言类型和立场倾向标注
"""

import json
import re
import jieba
import jieba.analyse
from datetime import datetime

# ============ 配置 ============
INPUT_FILE = r"E:\rumor_detection\data\weibo_rumors.json"  # 源数据文件
OUTPUT_FILE = r"E:\rumor_detection\data\cleaned_rumors.json"  # 输出文件

# ============ 清洗函数 ============
def clean_text(text):
    """清洗文本：去除HTML标签、特殊符号、链接等"""
    if not text:
        return ""
    
    # 1. 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 2. 去除链接 (http/https/www开头)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    
    # 3. 去除@用户名
    text = re.sub(r'@[\w\u4e00-\u9fff]+', '', text)
    
    # 4. 去除#话题# (保留话题内容但去除符号)
    text = re.sub(r'#([^#]+)#', r'\1', text)
    
    # 5. 去除特殊符号（保留中文、英文、数字）
    # 只保留中文、英文、数字和常用标点
    text = re.sub(r'[^\w\s\u4e00-\u9fff。，、！？；：""''（）【】《》…—\s]', '', text)
    
    # 6. 去除多余空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_keywords(text, topK=5):
    """使用jieba提取关键词"""
    if not text or len(text) < 2:
        return []
    
    # 使用TF-IDF提取关键词
    keywords = jieba.analyse.extract_tags(text, topK=topK, withWeight=False)
    return keywords


def infer_rumor_type(content, keyword):
    """基于内容推断谣言类型"""
    # 这是一个简单的规则推断，实际需要人工标注
    # 可以基于关键词和内容特征进行简单分类
    
    # 负面关键词倾向于是假谣言
    fake_indicators = ['谣言', '假新闻', '造假', '伪造', '造谣', '假消息', '假的']
    # 正面/辟谣关键词倾向于真
    true_indicators = ['辟谣', '真相', '真的', '事实', '官方', '证实']
    
    content_lower = content.lower()
    keyword_lower = keyword.lower()
    
    # 检查关键词
    for indicator in true_indicators:
        if indicator in keyword_lower or indicator in content_lower:
            return "真"  # 辟谣类信息说明事实为真
    
    for indicator in fake_indicators:
        if indicator in keyword_lower or indicator in content_lower:
            return "假"  # 明确提到谣言/假新闻
    
    # 默认返回"未证实"
    return "未证实"


def infer_stance(content, keyword):
    """基于内容推断立场倾向"""
    # 简单的规则推断
    
    support_indicators = ['支持', '相信', '真的', '事实', '证实', '客观', '正确']
    oppose_indicators = ['反对', '质疑', '假的', '谣言', '造谣', '假新闻', '欺骗', '虚伪']
    
    content_lower = content.lower()
    keyword_lower = keyword.lower()
    
    support_count = sum(1 for i in support_indicators if i in content_lower or i in keyword_lower)
    oppose_count = sum(1 for i in oppose_indicators if i in content_lower or i in keyword_lower)
    
    if support_count > oppose_count:
        return "支持"
    elif oppose_count > support_count:
        return "反对"
    else:
        return "中立"


def process_data():
    """处理数据主函数"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始处理数据...")
    
    # 1. 读取原始数据
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 读取源数据: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 共读取 {len(raw_data)} 条数据")
    
    # 2. 清洗和标注
    cleaned_data = []
    for i, item in enumerate(raw_data):
        original_content = item.get('content', '')
        keyword = item.get('keyword', '')
        
        # 清洗文本
        cleaned_content = clean_text(original_content)
        
        # 提取关键词
        keywords = extract_keywords(cleaned_content)
        
        # 推断标注
        rumor_type = infer_rumor_type(cleaned_content, keyword)
        stance = infer_stance(cleaned_content, keyword)
        
        # 构建清洗后的数据
        cleaned_item = {
            "原始内容": original_content,
            "清洗后内容": cleaned_content,
            "关键词": keywords,
            "谣言类型": rumor_type,
            "立场倾向": stance,
            "原始关键词": keyword  # 保留原始keyword字段
        }
        
        cleaned_data.append(cleaned_item)
        
        if (i + 1) % 10 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 已处理 {i + 1}/{len(raw_data)} 条")
    
    # 3. 保存结果
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 保存清洗后的数据: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    # 4. 统计信息
    rumor_types = {}
    stances = {}
    for item in cleaned_data:
        rt = item['谣言类型']
        st = item['立场倾向']
        rumor_types[rt] = rumor_types.get(rt, 0) + 1
        stances[st] = stances.get(st, 0) + 1
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ========== 处理完成 ==========")
    print(f"总数据量: {len(cleaned_data)} 条")
    print(f"\n谣言类型分布:")
    for rt, count in rumor_types.items():
        print(f"  - {rt}: {count} 条")
    print(f"\n立场倾向分布:")
    for st, count in stances.items():
        print(f"  - {st}: {count} 条")
    print(f"\n输出文件: {OUTPUT_FILE}")
    
    return cleaned_data


if __name__ == "__main__":
    process_data()
