# -*- coding: utf-8 -*-
"""
基于LLM（千问API）的数据增强模块
支持多种增强策略
"""

import os
import json
import time
import random
import requests
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============ 千问API配置 =============
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-turbo")
# ====================================


class QwenLLMClient:
    """千问LLM客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-turbo"):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.model = model
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    def chat(self, prompt: str, system_prompt: str = "你是一个专业的文本处理助手。",
             temperature: float = 0.8, max_tokens: int = 2000) -> Optional[str]:
        """发送聊天请求"""
        if not self.api_key:
            print("[ERROR] 请先设置 DASHSCOPE_API_KEY 环境变量")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=data, timeout=120)
            result = response.json()
            
            if response.status_code == 200 and "output" in result:
                return result["output"]["text"]
            else:
                print(f"[ERROR] {response.status_code}: {result}")
                return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None


class DataAugmenter:
    """数据增强器"""
    
    def __init__(self, client: QwenLLMClient):
        self.client = client
    
    def paraphrase(self, text: str, num_variants: int = 5) -> List[str]:
        """文本改写 - 生成同义表述"""
        prompt = f"""请将以下文本改写成{num_variants}种不同的表达方式，保持语义核心不变。

原文：{text}

请直接输出{num_variants}条，每条一行，不要编号。"""
        
        result = self.client.chat(prompt)
        if not result:
            return []
        
        variants = []
        for line in result.strip().split("\n"):
            line = line.strip().strip("0123456789.。 ").strip("- ").strip("* ").strip("• ")
            if line and len(line) > 5:
                variants.append(line)
        
        return variants[:num_variants]
    
    def change_stance(self, text: str) -> Dict[str, str]:
        """改变立场 - 支持/反对/中立"""
        prompt = f"""请将以下文本改写成三种不同立场的版本。

原文：{text}

请按以下格式输出（每条一行）：
支持：<支持立场的版本>
反对：<反对立场的版本>
中立：<中立立场的版本>"""
        
        result = self.client.chat(prompt)
        if not result:
            return {}
        
        stances = {}
        for line in result.strip().split("\n"):
            line = line.strip()
            if any(line.startswith(s) for s in ["支持", "反对", "中立"]):
                if "：" in line:
                    parts = line.split("：", 1)
                    if len(parts) == 2:
                        stance_name = parts[0]
                        content = parts[1].strip()
                        if len(content) > 5:
                            stances[stance_name] = content
        
        return stances
    
    def expand_context(self, text: str) -> List[str]:
        """扩展上下文 - 添加背景信息"""
        prompt = f"""请为以下文本添加3种不同的背景上下文信息，使其成为更完整的事件描述。

原文：{text}

请按以下格式输出：
背景1：<添加背景1>
背景2：<添加背景2>
背景3：<添加背景3>"""
        
        result = self.client.chat(prompt)
        if not result:
            return []
        
        contexts = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if "：" in line:
                parts = line.split("：", 1)
                if len(parts) == 2:
                    content = parts[1].strip()
                    if len(content) > 5:
                        contexts.append(content)
        
        return contexts
    
    def generate_counter_argument(self, text: str) -> Dict[str, str]:
        """生成反驳观点"""
        prompt = f"""请为以下文本生成反驳论点和赞同论点。

原文：{text}

请按以下格式输出：
赞同：<赞同论点>
反驳：<反驳论点>"""
        
        result = self.client.chat(prompt)
        if not result:
            return {}
        
        arguments = {}
        for line in result.strip().split("\n"):
            line = line.strip()
            if "：" in line:
                parts = line.split("：", 1)
                if len(parts) == 2:
                    arg_type = parts[0]
                    content = parts[1].strip()
                    if len(content) > 5:
                        arguments[arg_type] = content
        
        return arguments
    
    def augment_sample(self, sample: Dict, augmentation_types: List[str] = None) -> List[Dict]:
        """
        对单个样本进行增强
        
        Args:
            sample: 原始样本 {'text': ..., 'label': ..., 'stance': ...}
            augmentation_types: 增强类型列表
            
        Returns:
            增强后的样本列表
        """
        if augmentation_types is None:
            augmentation_types = ['paraphrase', 'stance']
        
        text = sample.get('text', sample.get('original', ''))
        if not text:
            return []
        
        augmented_samples = []
        
        for aug_type in augmentation_types:
            try:
                if aug_type == 'paraphrase':
                    variants = self.paraphrase(text, num_variants=3)
                    for variant in variants:
                        augmented_samples.append({
                            'original': text,
                            'augmented': variant,
                            'augmentation_type': 'paraphrase',
                            'label': sample.get('label', 'unknown'),
                            'stance': sample.get('stance', '中立'),
                            'source': 'qwen'
                        })
                
                elif aug_type == 'stance':
                    stances = self.change_stance(text)
                    for stance_name, stance_text in stances.items():
                        augmented_samples.append({
                            'original': text,
                            'augmented': stance_text,
                            'augmentation_type': 'stance_change',
                            'stance': stance_name,
                            'label': sample.get('label', 'unknown'),
                            'source': 'qwen'
                        })
                
                elif aug_type == 'context':
                    contexts = self.expand_context(text)
                    for ctx in contexts:
                        augmented_samples.append({
                            'original': text,
                            'augmented': ctx,
                            'augmentation_type': 'context_expansion',
                            'label': sample.get('label', 'unknown'),
                            'stance': sample.get('stance', '中立'),
                            'source': 'qwen'
                        })
                
                elif aug_type == 'argument':
                    arguments = self.generate_counter_argument(text)
                    for arg_type, arg_text in arguments.items():
                        augmented_samples.append({
                            'original': text,
                            'augmented': arg_text,
                            'augmentation_type': f'{arg_type}_argument',
                            'label': sample.get('label', 'unknown'),
                            'stance': sample.get('stance', '中立'),
                            'source': 'qwen'
                        })
                
                # 避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[ERROR] {aug_type} augmentation failed: {e}")
                continue
        
        return augmented_samples


def augment_dataset(input_file: str, 
                   output_file: str,
                   augmentation_types: List[str] = None,
                   max_samples: Optional[int] = None,
                   api_key: Optional[str] = None):
    """
    增强数据集
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        augmentation_types: 增强类型
        max_samples: 最大样本数
        api_key: 千问API密钥
    """
    if not DASHSCOPE_API_KEY and not api_key:
        print("[ERROR] 请先设置千问API密钥:")
        print('   set DASHSCOPE_API_KEY=your_api_key')
        print("\n获取API密钥: https://dashscope.console.aliyun.com/")
        return
    
    print(f"[INFO] 千问模型: {QWEN_MODEL}")
    
    # 读取数据
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"[ERROR] 输入文件不存在: {input_file}")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict):
        data = list(data.values())
    
    print(f"[INFO] 读取 {len(data)} 条数据")
    
    if max_samples:
        data = data[:max_samples]
    
    # 创建客户端
    client = QwenLLMClient(api_key=api_key)
    augmenter = DataAugmenter(client)
    
    all_results = []
    
    # 处理每个样本
    for i, item in enumerate(data):
        print(f"\n[{i+1}/{len(data)}] 原始文本: {str(item)[:50]}...")
        
        # 确保有text字段
        text = item.get('text') or item.get('清洗后内容') or item.get('content', '')
        if not text:
            continue
        
        sample = {
            'text': text,
            'label': item.get('label', item.get('谣言类型', 'unknown')),
            'stance': item.get('stance', '中立')
        }
        
        # 执行增强
        augmented = augmenter.augment_sample(sample, augmentation_types)
        all_results.extend(augmented)
        
        print(f"   -> 生成了 {len(augmented)} 条增强数据")
    
    print(f"\n[RESULT] 共生成 {len(all_results)} 条增强数据")
    
    # 保存
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"[SAVED] {output_path}")
    
    return all_results


# ==================== 便捷函数 ====================

def quick_augment(text: str, api_key: Optional[str] = None) -> Dict[str, List[str]]:
    """
    快速增强单条文本
    
    Args:
        text: 待增强文本
        api_key: API密钥
        
    Returns:
        包含各种增强结果的字典
    """
    if not DASHSCOPE_API_KEY and not api_key:
        print("[ERROR] 请先设置 DASHSCOPE_API_KEY")
        return {}
    
    client = QwenLLMClient(api_key=api_key)
    augmenter = DataAugmenter(client)
    
    results = {}
    
    # 改写
    print("-> 文本改写中...")
    results['paraphrase'] = augmenter.paraphrase(text, num_variants=3)
    
    # 立场改变
    print("-> 立场改变中...")
    results['stance'] = augmenter.change_stance(text)
    
    # 扩展上下文
    print("-> 扩展上下文中...")
    results['context'] = augmenter.expand_context(text)
    
    return results


# ==================== 测试 ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="基于LLM的数据增强")
    parser.add_argument('--input', type=str, 
                       default="E:/rumor_detection/data/cleaned_rumors.json",
                       help='输入文件')
    parser.add_argument('--output', type=str,
                       default="E:/rumor_detection/data/augmented_data.json",
                       help='输出文件')
    parser.add_argument('--max_samples', type=int, default=None,
                       help='最大样本数')
    parser.add_argument('--types', nargs='+', 
                       default=['paraphrase', 'stance'],
                       help='增强类型')
    
    args = parser.parse_args()
    
    # 检查API密钥
    if not DASHSCOPE_API_KEY:
        print("[WARNING] DASHSCOPE_API_KEY 未设置")
        print("请运行:")
        print('   set DASHSCOPE_API_KEY=your_api_key')
        print("\n使用演示模式...")
        
        # 演示
        demo_text = "这个新闻说某地发现了新的病毒变种，可能会导致大规模传播。"
        print(f"\n演示文本: {demo_text}")
        print("\n[功能说明]")
        print("- paraphrase: 文本改写")
        print("- stance: 立场改变")
        print("- context: 扩展上下文")
        print("- argument: 生成反驳/赞同论点")
    else:
        augment_dataset(
            input_file=args.input,
            output_file=args.output,
            augmentation_types=args.types,
            max_samples=args.max_samples
        )
