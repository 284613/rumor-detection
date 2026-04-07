# -*- coding: utf-8 -*-
"""本地数据增强模块 - 使用规则方法"""
import json
import random
import re
from pathlib import Path

# 同义词词典
SYNONYMS = {
    "谣言": ["假消息", "不实信息", "虚假信息", "传言"],
    "辟谣": ["澄清", "真相", "证实", "官方回应"],
    "假": ["虚假", "不实", "伪造"],
    "真": ["真实", "确实", "属实"],
    "支持": ["赞同", "认同", "认可"],
    "反对": ["不认同", "质疑", "否定"],
    "认为": ["觉得", "感觉", "相信"],
    "可能": ["也许", "大概", "或许"],
    "应该": ["应当", "需要", "必须"],
    "很多": ["大量", "众多", "许多"],
    "说": ["表示", "指出", "称"],
}

# 立场关键词
STANCE_KEYWORDS = {
    "support": ["支持", "赞同", "认同", "相信", "确实", "属实", "真的"],
    "oppose": ["反对", "质疑", "不信", "假的", "谣言", "欺骗"],
    "neutral": ["可能", "也许", "不确定", "观望", "看看"]
}

def synonym_replace(text, n=1):
    """同义词替换"""
    words = text.split()
    for _ in range(n):
        idx = random.randint(0, len(words)-1)
        word = words[idx]
        if word in SYNONYMS:
            words[idx] = random.choice(SYNONYMS[word])
    return " ".join(words)

def insert_phrase(text):
    """插入常用短语"""
    phrases = ["实际上", "事实上", "客观来说", "一般来说", "通常情况下"]
    sentences = text.split("。")
    if len(sentences) > 1:
        idx = random.randint(1, len(sentences)-1)
        sentences[idx] = random.choice(phrases) + "，" + sentences[idx]
    return "。".join(sentences)

def change_voice(text):
    """改变句式（主动-被动）"""
    # 简单的主动转被动
    patterns = [
        (r"(\w+)证实了", "被\\1证实"),
        (r"(\w+)说", "根据\\1的说法"),
        (r"(\w+)认为", "\\1的看法是"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text

def split_sentence(text):
    """拆分长句"""
    # 将长句拆分为短句
    sentences = text.split("。")
    new_sentences = []
    for s in sentences:
        if len(s) > 20 and "，" in s:
            parts = s.split("，")
            new_sentences.extend(parts)
        else:
            new_sentences.append(s)
    return "。".join(new_sentences)

def detect_stance(text):
    """检测立场"""
    text_lower = text.lower()
    stance_scores = {"support": 0, "oppose": 0, "neutral": 0}
    
    for keyword in STANCE_KEYWORDS["support"]:
        if keyword in text_lower:
            stance_scores["support"] += 1
    for keyword in STANCE_KEYWORDS["oppose"]:
        if keyword in text_lower:
            stance_scores["oppose"] += 1
    for keyword in STANCE_KEYWORDS["neutral"]:
        if keyword in text_lower:
            stance_scores["neutral"] += 1
    
    max_score = max(stance_scores.values())
    if max_score == 0:
        return "neutral"
    return max(stance_scores, key=stance_scores.get)

def augment_text(text, num_augmentations=2):
    """增强单条文本"""
    augmented = []
    methods = [synonym_replace, insert_phrase, change_voice, split_sentence]
    
    for _ in range(num_augmentations):
        method = random.choice(methods)
        aug_text = method(text)
        if aug_text != text:
            augmented.append(aug_text)
    
    return augmented

def main():
    # 读取清洗后的数据
    input_file = Path("E:/rumor_detection/data/cleaned_rumors.json")
    output_file = Path("E:/rumor_detection/data/augmented_rumors.json")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"[INFO] 读取 {len(data)} 条原始数据")
    
    augmented_data = []
    
    for item in data:
        original_content = item.get("清洗后内容", item.get("content", ""))
        if not original_content:
            continue
            
        # 原始数据
        augmented_data.append({
            "original": original_content,
            "augmented": original_content,
            "augmentation_type": "original",
            "original_label": item.get("谣言类型", "unknown"),
            "augmented_label": item.get("谣言类型", "unknown"),
            "stance": detect_stance(original_content)
        })
        
        # 同义词替换增强
        for i in range(2):
            aug = synonym_replace(original_content, n=random.randint(1, 3))
            if aug != original_content:
                augmented_data.append({
                    "original": original_content,
                    "augmented": aug,
                    "augmentation_type": "synonym",
                    "original_label": item.get("谣言类型", "unknown"),
                    "augmented_label": item.get("谣言类型", "unknown"),
                    "stance": detect_stance(aug)
                })
        
        # 句式变化增强
        aug = change_voice(original_content)
        if aug != original_content:
            augmented_data.append({
                "original": original_content,
                "augmented": aug,
                "augmentation_type": "voice_change",
                "original_label": item.get("谣言类型", "unknown"),
                "augmented_label": item.get("谣言类型", "unknown"),
                "stance": detect_stance(aug)
            })
        
        # 拆分句子增强
        aug = split_sentence(original_content)
        if aug != original_content:
            augmented_data.append({
                "original": original_content,
                "augmented": aug,
                "augmentation_type": "split",
                "original_label": item.get("谣言类型", "unknown"),
                "augmented_label": item.get("谣言类型", "unknown"),
                "stance": detect_stance(aug)
            })
    
    print(f"[INFO] 增强后共 {len(augmented_data)} 条数据")
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(augmented_data, f, ensure_ascii=False, indent=2)
    
    print(f"[SAVED] {output_file}")
    
    # 统计
    print("\n[统计]")
    types = {}
    for item in augmented_data:
        t = item["augmentation_type"]
        types[t] = types.get(t, 0) + 1
    for k, v in types.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
