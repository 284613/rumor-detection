"""
谣言数据增强脚本
使用LLM进行文本重写和立场改写
"""

import json
import random

# 尝试导入OpenAI，如果不可用则使用模拟模式
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI库不可用，将使用模拟数据进行演示")

# 读取原始数据
def load_data(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# 保存增强后的数据
def save_data(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 立场改写的映射关系
# 当改变立场时，谣言类型也可能需要相应调整
STANCE_MAPPING = {
    "支持": ["反对", "中立"],
    "反对": ["支持", "中立"],
    "中立": ["支持", "反对"]
}

# 文本重写示例模板（模拟LLM生成的不同表达方式）
REWRITE_TEMPLATES = [
    "关于{content}，我有不同的看法",
    "刚看到{content}，来聊聊",
    "大家{content}，怎么看？",
    "转发一下：{content}",
    "最新消息：{content}",
    "来说说{content}这件事",
]

def generate_rewrite_variants(original_text, count=2):
    """生成文本重写变体"""
    variants = []
    templates_used = random.sample(REWRITE_TEMPLATES, min(count, len(REWRITE_TEMPLATES)))
    
    for template in templates_used:
        # 简单替换，实际使用时LLM会更好地重写
        variant = template.replace("{content}", original_text[:min(len(original_text), 30)])
        if variant != original_text:
            variants.append(variant)
    
    return variants[:count]

def generate_stance_variants(original_text, original_stance, original_label, count=2):
    """生成立场改写变体"""
    variants = []
    possible_stances = STANCE_MAPPING.get(original_stance, ["支持", "反对", "中立"])
    selected_stances = random.sample(possible_stances, min(count, len(possible_stances)))
    
    stance_prefixes = {
        "支持": ["支持！", "确实如此，", "同意，"],
        "反对": ["反对！", "其实不然，", "不同意，"],
        "中立": ["客观来说，", "据观察，", "中立看待，"]
    }
    
    for stance in selected_stances:
        prefix = random.choice(stance_prefixes.get(stance, [""]))
        variant = prefix + original_text
        variants.append({
            "text": variant,
            "stance": stance
        })
    
    return variants[:count]

def augment_with_llm(client, original_text, original_label, original_stance):
    """使用LLM进行数据增强"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个数据增强专家，擅长将文本进行改写，生成语义相似但表达不同的版本。请生成2-3个变体，包括：1) 文本重写（不同表达方式）2) 立场改写（支持/反对/中立不同立场）。"
                },
                {
                    "role": "user",
                    "content": f"原始文本：{original_text}\n原始标注：{original_label}\n原始立场：{original_stance}\n\n请生成增强变体，输出JSON格式："
                }
            ],
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM调用失败: {e}")
        return None

def main():
    input_file = r"E:\rumor_detection\data\cleaned_rumors.json"
    output_file = r"E:\rumor_detection\data\augmented_rumors.json"
    
    # 加载数据
    print(f"正在读取原始数据: {input_file}")
    original_data = load_data(input_file)
    print(f"共读取 {len(original_data)} 条原始数据")
    
    # 初始化OpenAI客户端（如果可用）
    client = None
    use_llm = False
    
    if OPENAI_AVAILABLE:
        # 尝试使用环境变量中的API key
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                # 测试API连接
                client.models.list()
                use_llm = True
                print("已连接到OpenAI API")
            except Exception as e:
                print(f"API连接测试失败: {e}")
                print("将使用模拟数据进行演示")
        else:
            print("未找到OPENAI_API_KEY环境变量，将使用模拟数据进行演示")
    
    # 增强数据
    augmented_data = []
    
    for idx, item in enumerate(original_data):
        original_text = item.get("清洗后内容", item.get("原始内容", ""))
        original_label = item.get("谣言类型", "真")
        original_stance = item.get("立场倾向", "中立")
        
        # 为每条数据生成2-3个变体
        num_variants = random.randint(2, 3)
        
        # 文本重写变体
        rewrite_count = num_variants // 2
        if use_llm and client:
            # 使用LLM生成重写变体
            llm_result = augment_with_llm(client, original_text, original_label, original_stance)
            if llm_result:
                # 解析LLM结果（简化处理）
                pass
        else:
            # 使用模拟方式生成重写变体
            rewrite_variants = generate_rewrite_variants(original_text, rewrite_count)
            for variant_text in rewrite_variants:
                augmented_data.append({
                    "original": original_text,
                    "augmented": variant_text,
                    "augmentation_type": "rewrite",
                    "original_label": original_label,
                    "augmented_label": original_label  # 文本重写不改变标签
                })
        
        # 立场改写变体
        stance_count = num_variants - rewrite_count
        stance_variants = generate_stance_variants(original_text, original_stance, original_label, stance_count)
        for variant in stance_variants:
            augmented_data.append({
                "original": original_text,
                "augmented": variant["text"],
                "augmentation_type": "stance",
                "original_label": original_label,
                "augmented_label": original_label  # 立场改变可能需要人工审核，这里保持原标签
            })
        
        print(f"已完成第 {idx+1}/{len(original_data)} 条数据的增强")
    
    # 保存结果
    print(f"\n正在保存增强后的数据到: {output_file}")
    save_data(augmented_data, output_file)
    print(f"增强完成！共生成 {len(augmented_data)} 条增强数据")
    
    # 打印统计信息
    rewrite_count = sum(1 for item in augmented_data if item["augmentation_type"] == "rewrite")
    stance_count = sum(1 for item in augmented_data if item["augmentation_type"] == "stance")
    print(f"\n统计：")
    print(f"  - 文本重写变体: {rewrite_count} 条")
    print(f"  - 立场改写变体: {stance_count} 条")
    print(f"  - 总计: {len(augmented_data)} 条")

if __name__ == "__main__":
    main()
