# 社交媒体恶意谣言识别系统 - 运行说明

## 📋 系统概述

本系统是基于 Streamlit 框架开发的 Web 演示应用，用于社交媒体谣言检测功能的中期检查演示。

## 🛠️ 环境要求

- Python 3.8 或更高版本
- Streamlit 框架

## 📦 依赖安装

在运行应用之前，请先安装必要的依赖：

```bash
pip install streamlit
```

## 🚀 运行方式

### 方式一：直接运行

在终端中进入项目目录并运行：

```bash
streamlit run E:\rumor_detection\app\streamlit_app.py
```

或使用绝对路径：

```bash
streamlit run "E:/rumor_detection/app/streamlit_app.py"
```

### 方式二：指定端口运行

如果需要指定端口（例如 8501）：

```bash
streamlit run E:\rumor_detection\app\streamlit_app.py --server.port 8501
```

## 📖 使用说明

1. **启动应用**：运行上述命令后，浏览器会自动打开 http://localhost:8501
2. **输入文本**：在文本框中输入待检测的社交媒体文本
3. **快速测试**：点击上方的示例按钮快速填充测试文本
4. **点击检测**：点击"开始检测"按钮进行分析
5. **查看结果**：系统会显示检测结果（谣言/真实信息）和置信度

## 🔧 注意事项

- 本系统使用模拟的基于关键词规则的检测器，仅供演示参考
- 实际项目中可将 `predict_rumor()` 函数替换为真实的机器学习/深度学习模型进行推理
- 确保系统已安装中文字体支持（如遇到中文显示问题）

## 📁 文件结构

```
E:\rumor_detection\
└── app\
    ├── streamlit_app.py    # 主应用代码
    └── README.md           # 运行说明（本文件）
```

## 📞 演示功能

- ✅ 文本输入区域
- ✅ 检测按钮
- ✅ 结果显示（谣言/真实信息 + 置信度）
- ✅ 示例文本（3个快速测试案例）
- ✅ 简洁美观的中文界面
