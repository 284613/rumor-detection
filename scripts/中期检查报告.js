const { Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel } = require('docx');
const fs = require('fs');

const doc = new Document({
    styles: {
        default: { document: { run: { font: "宋体", size: 24 } } },
        paragraphStyles: [
            { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
              run: { size: 36, bold: true, font: "黑体" },
              paragraph: { spacing: { before: 480, after: 240 }, outlineLevel: 0 } },
            { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
              run: { size: 28, bold: true, font: "黑体" },
              paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 1 } },
        ]
    },
    sections: [{
        properties: {
            page: {
                size: { width: 12240, height: 15840 },
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
            }
        },
        children: [
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { after: 600 },
                children: [new TextRun({ text: "社交媒体谣言检测毕业设计中期检查报告", bold: true, size: 48, font: "黑体" })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_1,
                children: [new TextRun("一、 创新特色与核心研究内容")] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("1. 创新点：面向极早期冷启动场景的多立场约束LLM增强机制")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "针对社交媒体谣言爆发初期传播节点极度稀疏、现有图神经网络模型（如 Bi-GCN、RvNN）因缺乏有效拓扑结构而出现\"冷启动\"失效问题，本课题提出了一种更具针对性的多立场约束 LLM 局部路径增强机制。", size: 24 })] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "该方法的核心创新体现在三个层面：其一，专门面向极早期场景（传播深度 ≤ 2 层，真实回复数 ≤ 5 条）设计数据截断与增强流程，打破了传统模型被动等待传播树成型的限制；其二，在 LLM 生成环节引入\"多立场强制约束\"Prompt 工程，要求模型同时输出支持、反对与中立三类预测评论，保证了虚拟节点对真实舆论生态的多样性模拟；其三，将增强后的多关系传播图谱接入联合多任务学习框架，最终实现从\"被动观测\"向\"主动演化预测\"的转变。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("2. 研究现状与发展趋势")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "近年来，社交媒体谣言检测经历了从浅层机器学习向图神经网络的演进。然而，此类模型高度依赖完整的级联传播结构。随着大语言模型的兴起，2024—2026 年的前沿研究开始将 LLM 引入谣言检测。本课题紧跟利用 LLM 生成能力进行数据增强与传播拓扑补全的技术路线（如 LLM-VN, 2026），在其基础上进一步聚焦极早期冷启动场景与多立场生成约束这一尚待深入探索的研究问题，以满足网络治理中\"打早打小\"的现实需求。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_1,
                spacing: { before: 480 },
                children: [new TextRun("二、 目前已完成情况")] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("1. 极早期阶段模拟器与数据增强重构")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "已完成基于 Python 的极早期传播阶段模拟器（Early-Stage Simulator），支持对传播树进行深度和规模的双重截断。同时，重构了数据增强模块，实现了基于磁盘缓存（.aug_cache）的增量处理机制，支持自动校验生成立场的均衡性，大幅提升了数据准备阶段的效率和质量。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("2. 传播树模型层增强")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "在模型架构上，完成了 Relation-Aware Tree-LSTM 核心单元的改造。新版本支持对增强产生的虚拟节点（Virtual Nodes）进行标记与屏蔽，并引入了 0.7 的信号衰减系数，有效平衡了增强数据的引导作用与潜在噪声干扰。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("3. 联合多任务学习框架")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "构建了包含谣言分类与立场检测的联合训练框架。创新性地引入了\"虚拟节点立场损失\"（Virtual Stance Loss），通过设置超参数权重（BETA=0.3）对虚拟生成的传播路径进行结构化约束，显著提升了模型在极早期稀疏拓扑下的检测鲁棒性。目前 BERT 多任务模型在验证集上的准确率已达到稳定水平。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_1,
                spacing: { before: 480 },
                children: [new TextRun("三、 下一阶段计划")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "下一阶段将重点进行多维消融实验，验证多立场均衡性对早期预警准确率的具体贡献。同时，完善 Streamlit 原型系统，引入早期阶段模拟展示功能。最终计划于 6 月份完成毕业论文初稿，重点阐述本方案在冷启动场景下的性能优势。", size: 24 })] }),
        ]
    }]
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("E:\\rumor_detection\\reports\\中期检查报告_最新版.docx", buffer);
    console.log("Updated report generated successfully: reports/中期检查报告_最新版.docx");
});
