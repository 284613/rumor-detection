# -*- coding: utf-8 -*-
"""处理爬取的微博数据 - 清洗和标注"""
import json
import jieba
import re
from collections import Counter
from pathlib import Path

print("="*60)
print("        爬取数据处理")
print("="*60)

# 加载数据
input_file = Path("E:/rumor_detection/data/crawled_multi_platform.json")
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n[1] 加载数据: {len(data)} 条")

# 数据清洗函数
def clean_text(text):
    """清洗文本"""
    if not text:
        return ""
    
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除URL
    text = re.sub(r'http[s]?://\S+', '', text)
    # 去除@用户
    text = re.sub(r'@[\w]+', '', text)
    # 去除#话题#
    text = re.sub(r'#\S+#', '', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# 分词和关键词提取
def extract_keywords(text):
    """提取关键词"""
    words = jieba.cut(text)
    # 过滤停用词和短词
    stopwords = {'的', '是', '了', '在', '和', '与', '或', '等', '这', '那', '有', '没有', '我', '你', '他', '她', '它', '们'}
    words = [w for w in words if len(w) > 1 and w not in stopwords]
    return words

# 自动标注函数
def auto_label(text):
    """基于关键词自动标注"""
    text_lower = text.lower()
    
    # 谣言关键词
    rumor_keywords = ['谣言', '造谣', '传谣', '假消息', '假新闻', '虚假', '不实', '诈骗', '骗局', '伪造', '假冒']
    # 辟谣关键词
    deny_keywords = ['辟谣', '澄清', '真相', '假', '不实', '谣言', '造谣', '传谣', '官方回应', '证实', '真实']
    
    rumor_score = sum(1 for kw in rumor_keywords if kw in text_lower)
    deny_score = sum(1 for kw in deny_keywords if kw in text_lower)
    
    if deny_score > rumor_score:
        return "辟谣"
    elif rumor_score > deny_score:
        return "谣言"
    else:
        return "未分类"

# 处理每条数据
processed_data = []

for i, item in enumerate(data):
    original_content = item.get('content', '')
    
    # 清洗
    cleaned_content = clean_text(original_content)
    
    if len(cleaned_content) < 5:
        continue
    
    # 提取关键词
    keywords = extract_keywords(cleaned_content)
    
    # 自动标注
    label = auto_label(cleaned_content)
    
    # 立场检测
    stance = "中立"
    if any(w in cleaned_content for w in ['支持', '相信', '认同', '确实', '真的']):
        stance = "支持"
    elif any(w in cleaned_content for w in ['反对', '质疑', '不信', '假的', '谣言']):
        stance = "反对"
    
    processed_data.append({
        "id": i + 1,
        "original": original_content,
        "content": cleaned_content,
        "keywords": keywords[:10],
        "label": label,
        "stance": stance,
        "source": item.get('source', 'weibo_search'),
        "platform": item.get('platform', '微博')
    })

print(f"[2] 清洗完成: {len(processed_data)} 条")

# 统计
labels = Counter([d['label'] for d in processed_data])
stances = Counter([d['stance'] for d in processed_data])

print(f"\n[3] 标注统计")
print(f"  谣言类型:")
for label, count in labels.items():
    print(f"    {label}: {count}")

print(f"  立场倾向:")
for stance, count in stances.items():
    print(f"    {stance}: {count}")

# 保存
output_file = Path("E:/rumor_detection/data/processed_crawled.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(processed_data, f, ensure_ascii=False, indent=2)

print(f"\n[4] 保存完成: {output_file}")

# 显示示例
print(f"\n[5] 示例数据:")
for i, item in enumerate(processed_data[:3]):
    print(f"\n--- {i+1} ---")
    print(f"  内容: {item['content'][:60]}...")
    print(f"  标签: {item['label']}")
    print(f"  立场: {item['stance']}")

print("\n" + "="*60)
print("        处理完成")
print("="*60)
