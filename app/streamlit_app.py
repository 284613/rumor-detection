# -*- coding: utf-8 -*-
"""
社交媒体恶意谣言识别系统 - Streamlit演示应用
用于毕业设计中期检查演示
"""

import streamlit as st
import random
import json
import hashlib
from pathlib import Path

CACHE_DIR = Path("E:/rumor_detection/data/.aug_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_data(show_spinner=False)
def load_augmented_cache() -> dict:
    """加载已完成的增强数据缓存，用 original[:50] 作为键"""
    aug_file = Path("E:/rumor_detection/data/augmented_qwen.json")
    if not aug_file.exists():
        return {}
    with open(aug_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {item["original"][:50]: item for item in data}


def get_cached_virtual_children(content: str, aug_cache: dict) -> list:
    """从本地缓存获取虚拟子节点，无需重复调用 API"""
    key = content[:50]
    item = aug_cache.get(key)
    if item:
        return item.get("virtual_children", [])

    # 检查磁盘 .aug_cache/ 目录
    disk_key = hashlib.md5(content.encode("utf-8")).hexdigest()
    disk_file = CACHE_DIR / f"{disk_key}.json"
    if disk_file.exists():
        with open(disk_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 设置页面配置
st.set_page_config(
    page_title="社交媒体恶意谣言识别系统",
    page_icon="🔍",
    layout="centered"
)

# ============================================================
# 模拟谣言检测函数（基于规则）
# 如有实际模型，可替换此函数进行真实推理
# ============================================================
def predict_rumor(text):
    """
    基于关键词规则的模拟谣言检测
    
    说明：
    - 此函数为演示用的模拟检测器
    - 实际项目中可替换为训练好的机器学习/深度学习模型
    - 置信度为随机生成，用于演示效果
    
    参数:
        text: 待检测的文本
    
    返回:
        (预测结果, 置信度)
        - result: "谣言" 或 "真实信息"
        - confidence: 0.0-1.0 之间的置信度值
    """
    
    if not text or len(text.strip()) == 0:
        return "请输入文本", 0.0
    
    # 定义一些常见的谣言关键词模式（演示用）
    rumor_keywords = [
        "震惊", "紧急", "刚刚发生", "惊人消息", "99%的人不知道",
        "必看", "转发扩散", "绝密", "内幕", "真相被掩盖",
        "专家警告", "致癌", "致死", "不要再吃", "骗局"
    ]
    
    truth_keywords = [
        "官方", "新华社", "人民日报", "证实", "根据",
        "数据显示", "研究显示", "专家表示", "统计局"
    ]
    
    # 统计关键词出现次数
    rumor_score = sum(1 for kw in rumor_keywords if kw in text)
    truth_score = sum(1 for kw in truth_keywords if kw in text)
    
    # 根据得分判断，并加入随机性模拟置信度波动
    if rumor_score > truth_score:
        result = "谣言"
        # 置信度在 0.65-0.95 之间，随机波动
        confidence = round(random.uniform(0.65, 0.95), 2)
    elif truth_score > rumor_score:
        result = "真实信息"
        confidence = round(random.uniform(0.60, 0.90), 2)
    else:
        # 无法判断时随机猜测
        result = random.choice(["谣言", "真实信息"])
        confidence = round(random.uniform(0.50, 0.70), 2)
    
    return result, confidence


# ============================================================
# Streamlit 界面构建
# ============================================================

# 页面标题
st.title("🔍 社交媒体恶意谣言识别系统")

# 副标题/描述
st.markdown("---")
st.markdown("### 📝 请输入待检测的社交媒体文本")

# 文本输入区域
text = st.text_area(
    "待检测文本：",
    height=150,
    placeholder="请在此输入需要检测的社交媒体文本内容...",
    label_visibility="collapsed"
)

# ============================================================
# 示例文本区域
# ============================================================
st.markdown("---")
st.markdown("#### 💡 快速测试（点击下方示例文本）")

# 定义示例文本
examples = {
    "示例1（疑似谣言）": "紧急通知！这种食物不能再吃了，99%的人都不知道，专家警告会导致致癌！转发扩散救救家人！",
    "示例2（真实信息）": "根据新华社报道，国家统计局数据显示，今年前三季度GDP同比增长5.2%，经济运行稳中向好。",
    "示例3（疑似谣言）": "震惊！某明星竟然做出这种事，内部消息流出，视频曝光太可怕了！",
}

# 使用列布局展示示例按钮
cols = st.columns(len(examples))
for idx, (label, example_text) in enumerate(examples.items()):
    if cols[idx].button(label, key=f"example_{idx}"):
        # 填充示例文本到输入框（通过session state）
        st.session_state.input_text = example_text
        # 重新运行以更新文本区域
        st.rerun()

# 从session state获取之前选择的示例文本（如果有）
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# 如果用户手动输入了新文本，更新session state
if text:
    st.session_state.input_text = text

# 显示当前输入的文本
if st.session_state.input_text:
    text = st.session_state.input_text

# ============================================================
# 检测按钮与结果显示
# ============================================================
st.markdown("---")

# 检测按钮
if st.button("🚀 开始检测", type="primary", use_container_width=True):
    
    if not text or len(text.strip()) == 0:
        st.warning("⚠️ 请先输入需要检测的文本！")
    else:
        # 执行检测
        result, confidence = predict_rumor(text)
        
        # 显示结果
        st.markdown("### 📊 检测结果")
        
        # 根据结果选择不同的样式
        if result == "谣言":
            st.error(f"🚨 **检测结果：{result}**")
        else:
            st.success(f"✅ **检测结果：{result}**")
        
        # 显示置信度
        st.markdown(f"**置信度：** {confidence * 100:.1f}%")
        
        # 置信度进度条
        st.progress(confidence)
        
        # 显示详细说明
        st.markdown("---")
        st.markdown("#### 📌 说明")
        st.info(
            "本系统基于关键词规则进行模拟检测，仅供演示参考。\n"
            "实际应用中，建议使用经过大量样本训练的机器学习模型进行推理。"
        )

# ============================================================
# 页脚
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "© 2024 社交媒体恶意谣言识别系统 - 毕业设计演示"
    "</div>",
    unsafe_allow_html=True
)
