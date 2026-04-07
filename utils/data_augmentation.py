# -*- coding: utf-8 -*-
"""
数据增强模块 - 基于大语言模型的数据增强工具

功能：
1. 文本重写：输入样本，生成不同表达方式的版本
2. 立场改写：生成支持/反对/中立不同立场的表达
3. 批量处理：支持数据集批量增强

作者：代码开发专员
日期：2026-03-16
"""

import os
import json
import time
import random
import logging
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

import requests
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AugmentationConfig:
    """增强配置数据类"""
    api_key: str
    model: str = "gpt-3.5-turbo"
    base_url: str = "https://api.openai.com/v1/chat/completions"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 60
    temperature: float = 0.8
    max_tokens: int = 1000


class LLMDataAugmenter:
    """
    基于大语言模型的数据增强器
    
    用于解决小样本问题，通过LLM生成多样化的训练数据变体。
    
    Attributes:
        config: 增强配置
    """
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-3.5-turbo",
        base_url: str = "https://api.openai.com/v1/chat/completions",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 60,
        temperature: float = 0.8,
        max_tokens: int = 1000
    ):
        """
        初始化数据增强器
        
        Args:
            api_key: OpenAI API密钥（或兼容API的密钥）
            model: 模型名称，默认gpt-3.5-turbo
            base_url: API基础URL，默认OpenAI官方API
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时时间（秒）
            temperature: 生成温度，控制随机性
            max_tokens: 最大生成token数
        """
        self.config = AugmentationConfig(
            api_key=api_key,
            model=model,
            base_url=base_url,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.session = requests.Session()
        logger.info(f"LLMDataAugmenter 初始化完成，使用模型: {model}")
    
    def _call_api(self, messages: List[Dict], temperature: Optional[float] = None) -> str:
        """
        调用LLM API（带重试机制）
        
        Args:
            messages: 消息列表
            temperature: 温度参数（可选）
            
        Returns:
            API返回的文本内容
            
        Raises:
            Exception: 所有重试失败后抛出异常
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    self.config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                elif response.status_code == 429:
                    # 速率限制，等待后重试
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"API速率限制，等待 {wait_time}秒后重试...")
                    time.sleep(wait_time)
                    last_error = "Rate limit exceeded"
                    continue
                else:
                    last_error = f"API错误: {response.status_code} - {response.text}"
                    logger.warning(f"API请求失败: {last_error}")
                    
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"API请求超时 (尝试 {attempt + 1}/{self.config.max_retries})")
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.warning(f"API请求异常 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
            
            # 重试前等待
            if attempt < self.config.max_retries - 1:
                wait_time = self.config.retry_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(wait_time)
        
        raise Exception(f"API调用失败，已重试{self.config.max_retries}次: {last_error}")
    
    def rewrite_text(self, text: str, num_variants: int = 5) -> List[str]:
        """
        文本重写：生成指定数量的表达变体
        
        Args:
            text: 输入文本
            num_variants: 要生成的变体数量
            
        Returns:
            文本变体列表
            
        Example:
            >>> augmenter = LLMDataAugmenter(api_key="your-key")
            >>> variants = augmenter.rewrite_text("这是原始文本", num_variants=3)
            >>> print(len(variants))  # 3
        """
        prompt = f"""请将以下文本改写成{d_num_variants}种不同但语义相近的表达方式。
要求：
1. 每种表达方式都要保持原文的核心含义
2. 使用不同的词汇和句式结构
3. 生成的变体要自然流畅，符合中文表达习惯
4. 每种变体用换行符分隔，不要编号

原文：{text}

生成的{num_variants}种变体："""

        messages = [
            {"role": "system", "content": "你是一个专业的文本改写助手，擅长用多种方式表达相同的意思。"},
            {"role": "user", "content": prompt.replace("{num_variants}", str(num_variants))}
        ]
        
        try:
            response = self._call_api(messages)
            # 按行分割并过滤空行
            variants = [line.strip() for line in response.split('\n') if line.strip()]
            
            # 确保返回足够数量的变体
            if len(variants) < num_variants:
                logger.warning(f"仅获得{len(variants)}个变体，少于要求的{num_variants}个")
                variants = variants[:num_variants] if variants else [text]
            
            logger.info(f"成功生成{len(variants)}个文本变体")
            return variants[:num_variants]
            
        except Exception as e:
            logger.error(f"文本重写失败: {e}")
            raise
    
    def change_stance(self, text: str, target_stance: str) -> List[str]:
        """
        立场改写：生成不同立场的表达
        
        Args:
            text: 输入文本
            target_stance: 目标立场
                - "support": 支持
                - "oppose": 反对
                - "neutral": 中立/质疑
            
        Returns:
            给定立场的文本变体列表
            
        Example:
            >>> augmenter = LLMDataAugmenter(api_key="your-key")
            >>> variants = augmenter.change_stance("我认为这是真的", "oppose")
            >>> print(len(variants))  # 至少1个
        """
        stance_names = {
            "support": "支持",
            "oppose": "反对", 
            "neutral": "中立/质疑"
        }
        
        stance_desc = {
            "support": "表达相信、赞同、支持的立场",
            "oppose": "表达怀疑、反对、否定的立场",
            "neutral": "表达中立、质疑、客观分析的立场"
        }
        
        if target_stance not in stance_names:
            raise ValueError(f"无效的立场类型: {target_stance}，支持的有: {list(stance_names.keys())}")
        
        prompt = f"""请将以下文本改写成{stance_names[target_stance]}立场的表达方式。
要求：
1. 保持原文的核心事件或信息不变
2. 改变表达方式和语气，使其符合{target_stance}立场
3. 生成的文本要自然流畅，符合中文表达习惯
4. 生成2-3个不同的改写版本，用换行符分隔

原文：{text}

{target_stance}立场的改写："""

        messages = [
            {"role": "system", "content": f"你是一个专业的文本改写助手，擅长将文本改写成不同立场。立场描述：{stance_desc[target_stance]}"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_api(messages)
            variants = [line.strip() for line in response.split('\n') if line.strip()]
            
            if not variants:
                logger.warning("未获得有效的立场改写结果")
                variants = [text]
            
            logger.info(f"成功生成{len(variants)}个{target_stance}立场变体")
            return variants
            
        except Exception as e:
            logger.error(f"立场改写失败: {e}")
            raise
    
    def augment_dataset(
        self, 
        data: Union[List[Dict], pd.DataFrame, str], 
        augmentation_factor: int = 2,
        output_path: Optional[str] = None,
        include_stance: bool = True
    ) -> pd.DataFrame:
        """
        批量增强数据集
        
        Args:
            data: 输入数据，支持以下格式：
                - List[Dict]: [{"text": "...", "label": 0}, ...]
                - pd.DataFrame: 包含text和label列
                - str: CSV文件路径
            augmentation_factor: 增强倍数，每个样本生成的变体数量
            output_path: 输出文件路径（可选）
            include_stance: 是否包含立场改写
            
        Returns:
            增强后的DataFrame，包含text和label列
            
        Example:
            >>> augmenter = LLMDataAugmenter(api_key="your-key")
            >>> data = [{"text": "这是真实新闻", "label": 0}, {"text": "这是谣言", "label": 1}]
            >>> augmented = augmenter.augment_dataset(data, augmentation_factor=2)
            >>> print(len(augmented))  # 4+
        """
        # 数据预处理
        if isinstance(data, str):
            # 读取CSV文件
            df = pd.read_csv(data)
            logger.info(f"从文件加载数据: {data}, 共{len(df)}条")
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
            logger.info(f"加载DataFrame数据，共{len(df)}条")
        elif isinstance(data, list):
            df = pd.DataFrame(data)
            logger.info(f"加载列表数据，共{len(df)}条")
        else:
            raise ValueError(f"不支持的数据类型: {type(data)}")
        
        # 确保包含必要列
        if 'text' not in df.columns or 'label' not in df.columns:
            raise ValueError("数据必须包含'text'和'label'列")
        
        augmented_data = []
        
        # 记录原始数据
        for _, row in df.iterrows():
            augmented_data.append({
                "text": row['text'],
                "label": row['label'],
                "augmentation_type": "original"
            })
        
        # 增强每个样本
        total = len(df)
        for idx, row in df.iterrows():
            text = row['text']
            label = row['label']
            
            logger.info(f"处理样本 {idx + 1}/{total}: {text[:30]}...")
            
            # 1. 文本重写
            try:
                rewrite_variants = self.rewrite_text(text, num_variants=augmentation_factor)
                for variant in rewrite_variants:
                    augmented_data.append({
                        "text": variant,
                        "label": label,
                        "augmentation_type": "rewrite"
                    })
            except Exception as e:
                logger.error(f"样本{idx}重写失败: {e}")
            
            # 2. 立场改写（可选）
            if include_stance:
                # 根据标签决定是否进行立场改写
                # 0=真实，1=谣言
                target_stances = ["support", "oppose", "neutral"]
                
                for stance in target_stances:
                    try:
                        stance_variants = self.change_stance(text, stance)
                        for variant in stance_variants:
                            augmented_data.append({
                                "text": variant,
                                "label": label,  # 保持原始标签
                                "augmentation_type": f"stance_{stance}"
                            })
                    except Exception as e:
                        logger.error(f"样本{idx}立场改写({stance})失败: {e}")
            
            # 添加延迟，避免API过载
            time.sleep(0.5)
        
        # 创建结果DataFrame
        result_df = pd.DataFrame(augmented_data)
        
        # 输出到文件（可选）
        if output_path:
            result_df.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"增强数据已保存到: {output_path}")
        
        logger.info(f"数据增强完成，原始{len(df)}条 -> 增强后{len(result_df)}条")
        
        # 只返回与原始格式兼容的列
        return result_df[['text', 'label']]
    
    def augment_with_stance_label(
        self,
        data: Union[List[Dict], pd.DataFrame, str],
        output_path: Optional[str] = None
    ) -> pd.DataFrame:
        """
        增强数据集并添加立场标签（用于多任务学习）
        
        生成支持、反对、中立三种立场的变体，并标注立场标签。
        
        Args:
            data: 输入数据
            output_path: 输出文件路径
            
        Returns:
            增强后的DataFrame，包含text, label, stance列
        """
        # 数据预处理
        if isinstance(data, str):
            df = pd.read_csv(data)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"不支持的数据类型: {type(data)}")
        
        if 'text' not in df.columns or 'label' not in df.columns:
            raise ValueError("数据必须包含'text'和'label'列")
        
        augmented_data = []
        
        # 记录原始数据
        for _, row in df.iterrows():
            augmented_data.append({
                "text": row['text'],
                "label": row['label'],
                "stance": "original"
            })
        
        total = len(df)
        for idx, row in df.iterrows():
            text = row['text']
            label = row['label']
            
            logger.info(f"处理样本 {idx + 1}/{total}")
            
            # 为谣言样本生成不同立场
            if label == 1:  # 谣言
                stances = ["support", "oppose", "neutral"]
            else:  # 真实
                stances = ["support", "neutral"]
            
            for stance in stances:
                try:
                    variants = self.change_stance(text, stance)
                    for variant in variants:
                        augmented_data.append({
                            "text": variant,
                            "label": label,
                            "stance": stance
                        })
                except Exception as e:
                    logger.error(f"样本{idx}立场{stance}改写失败: {e}")
            
            time.sleep(0.5)
        
        result_df = pd.DataFrame(augmented_data)
        
        if output_path:
            result_df.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"增强数据已保存到: {output_path}")
        
        return result_df


def create_augmenter_from_env() -> LLMDataAugmenter:
    """
    从环境变量创建增强器
    
    读取以下环境变量：
    - OPENAI_API_KEY: API密钥
    - OPENAI_MODEL: 模型名称（可选，默认gpt-3.5-turbo）
    - OPENAI_BASE_URL: API地址（可选）
    
    Returns:
        LLMDataAugmenter实例
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("未设置环境变量OPENAI_API_KEY")
    
    model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    
    return LLMDataAugmenter(
        api_key=api_key,
        model=model,
        base_url=base_url
    )


# ===== 便捷函数 =====

def rewrite_text(text: str, num_variants: int = 5, **kwargs) -> List[str]:
    """
    便捷函数：文本重写
    
    Args:
        text: 输入文本
        num_variants: 变体数量
        **kwargs: 传递给LLMDataAugmenter的其他参数
        
    Returns:
        文本变体列表
    """
    augmenter = LLMDataAugmenter(**kwargs)
    return augmenter.rewrite_text(text, num_variants)


def augment_csv(
    input_path: str,
    output_path: str,
    augmentation_factor: int = 2,
    api_key: Optional[str] = None,
    model: str = "gpt-3.5-turbo"
) -> pd.DataFrame:
    """
    便捷函数：增强CSV数据集
    
    Args:
        input_path: 输入CSV文件路径
        output_path: 输出CSV文件路径
        augmentation_factor: 增强倍数
        api_key: API密钥（如果未提供则从环境变量读取）
        model: 模型名称
        
    Returns:
        增强后的DataFrame
    """
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("请提供api_key或设置OPENAI_API_KEY环境变量")
    
    augmenter = LLMDataAugmenter(api_key=api_key, model=model)
    return augmenter.augment_dataset(
        data=input_path,
        augmentation_factor=augmentation_factor,
        output_path=output_path
    )


# ===== 使用示例 =====

if __name__ == "__main__":
    # 示例1: 使用API密钥初始化
    # augmenter = LLMDataAugmenter(
    #     api_key="your-api-key-here",
    #     model="gpt-3.5-turbo"
    # )
    
    # 示例2: 文本重写
    # variants = augmenter.rewrite_text("今天天气真好", num_variants=3)
    # print("文本重写结果:", variants)
    
    # 示例3: 立场改写
    # variants = augmenter.change_stance("这个消息是真的", "oppose")
    # print("立场改写结果:", variants)
    
    # 示例4: 批量增强数据集
    # data = [
    #     {"text": "某地发生地震", "label": 1},
    #     {"text": "科学家发现新物种", "label": 0}
    # ]
    # augmented = augmenter.augment_dataset(data, augmentation_factor=2)
    # print(f"增强后数据量: {len(augmented)}")
    # augmented.to_csv("augmented_data.csv", index=False)
    
    # 示例5: 使用环境变量
    # augmenter = create_augmenter_from_env()
    
    print("数据增强模块已加载，请根据需要配置API密钥并调用相应方法。")
