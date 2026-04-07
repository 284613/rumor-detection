# 项目开发日志 (Project Development Log)

## [2026-04-07] 早期谣言检测与虚拟增强功能升级

### 任务总结：
1. **数据增强重构 (`scripts/augment_test_data.py`)**
   - 实现增量处理与磁盘缓存 (`.aug_cache/`)。
   - 引入 `virtual_children` 字段，支持多立场提示词。
   - 增强了 API 调用的稳定性与均衡性校验。

2. **早期阶段模拟器 (`utils/early_stage_simulator.py`)**
   - **核心功能**: 实现传播树的极早期截断（深度 <= 2，节点 <= 5）。
   - **增强逻辑**: 支持将 LLM 生成的虚拟节点（Virtual Children）挂载至真实传播树。
   - **输出规范**: 统一转换为模型输入格式，并标记 `virtual_flags`。

3. **模型层增强 (`models/propagation_tree.py`)**
   - **虚拟掩码机制**: `RelationAwareTreeLSTMCell` 现在支持 `virtual_mask`。
   - **信号衰减**: 虚拟节点的隐藏状态和细胞状态引入 `0.7` 的衰减系数，降低噪声干扰。

4. **多任务损失优化 (`models/multi_task.py`)**
   - **损失约束**: 新增 `virtual_stance_loss`，专门约束虚拟节点的立场表达。
   - **超参数权重**: 引入 `ALPHA=0.5` (立场权重) 和 `BETA=0.3` (虚拟节点权重)。

5. **演示应用优化 (`app/streamlit_app.py`)**
   - **性能提升**: 引入 `@st.cache_data` 缓存大数据集加载。
   - **体验优化**: 虚拟节点获取实现“内存-磁盘”二级缓存，显著降低答辩演示时的等待时间。

6. **实验数据制备完毕 (Data Preparation)**
   - **增强数据来源**: 核心实验基于 **CED_Dataset (综合中文谣言数据集)**。
   - **增强逻辑**: 对 `ced_early.json` (仅保留前3条真实转发的极早期版本) 进行 LLM 多立场增强。
   - **核心模型切换**: 由于 **Qwen 额度耗尽**，生成任务已全面切换至 **MiniMax-M2.5-highspeed** (海螺 AI 接口)。
   - **增强规模**: 已利用 MiniMax 为 CED 截断后的 **2548** 条样本成功生成了 **15,288** 条虚拟回复节点。
   - **数据产出**:
     - `data/ablation_early_real.json` (源自 CED_Dataset 的早期传播截断)
     - `data/ablation_early_augmented.json` (基于 MiniMax 增强后的对比组)

---
**当前状态**: 所有核心组件已对齐，数据增强与消融实验所需的对照组数据集已全部制备完毕，随时可开展“真实数据+虚拟增强”的对比训练与评估。
