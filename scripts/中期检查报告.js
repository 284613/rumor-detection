const { Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel } = require('docx');
const fs = require('fs');

const doc = new Document({
    styles: {
        default: { document: { run: { font: "Arial", size: 24 } } },
        paragraphStyles: [
            { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
              run: { size: 36, bold: true, font: "Arial" },
              paragraph: { spacing: { before: 480, after: 240 }, outlineLevel: 0 } },
            { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
              run: { size: 28, bold: true, font: "Arial" },
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
                children: [new TextRun({ text: "谣言检测毕业设计中期检查报告", bold: true, size: 48, font: "Arial" })]
            }),

            new Paragraph({ heading: HeadingLevel.HEADING_1,
                children: [new TextRun("一、主要内容和计划进度")] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("1. 研究背景")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "本研究课题为\"社交媒体恶意谣言识别的研究与实现\"。随着社交媒体的快速发展，谣言在网络上的传播速度日益加快，已成为影响社会稳定和公共安全的重要问题。传统的谣言检测方法效率低下，难以应对海量信息的实时分析需求。因此，利用深度学习技术构建自动化的谣言识别系统具有重要的理论价值和应用意义。本项目旨在构建一个能够同时处理中文微博和英文Twitter的跨语言谣言检测系统，为谣言防控提供技术支持。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("2. 研究目标")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "本研究的核心目标是构建一个基于深度学习的社交媒体谣言自动识别系统。具体而言，系统应实现以下四个子目标：首先是数据采集与增强，整合多源数据集包括微博和Twitter数据，通过人工标注和LLM大语言模型进行数据增强；其次是构建双向支撑融合模型，将文本分类与传播关系树结构相结合，形成双支撑的模型架构；第三是实现预训练协同微调模式，利用预训练模型进行协同训练和微调优化；最后是开发原型系统，搭建前端界面实现实时谣言检测和可视化展示。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("3. 技术路线")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "本项目采用的技术路线主要包括以下几个阶段：首先是数据采集阶段，通过多源数据集整合和微博爬取获取原始数据；其次是人工标注阶段，建立\"谣言-非谣言-传播关系\"的标注体系；第三是LLM增强阶段，使用大语言模型对数据进行增强和标注优化；第四是模型构建阶段，采用双向支撑融合模型进行特征提取和分类；第五是协同微调阶段，通过预训练-协同微调模式优化模型性能；最后是原型系统开发阶段，搭建Streamlit应用实现实时检测功能。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("4. 下一阶段计划")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "根据项目进度安排，下一阶段的工作主要集中在以下几个方面：第一，在4月至5月期间，继续扩展数据采集范围，爬取更多微博数据并优化预训练模型的微调策略；第二，在5月至6月期间，对系统进行整体优化并开始撰写毕业论文，完成核心章节的写作；第三，在6月期间，完善原型系统的功能，实现实时谣言检测展示和可视化界面优化，确保系统能够稳定运行并提供良好的用户体验。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_1,
                spacing: { before: 480 },
                children: [new TextRun("二、目前已完成情况")] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("1. 数据集建设情况")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "在数据集建设方面，项目已完成多源数据集的整合工作。原始数据主要来自两个方面：一是利用已有的公开数据集，包括清华微博谣言数据集共31,477条数据，以及其他来源的微博谣言数据；二是通过微博搜索API进行数据爬取，目前已获取6,638条相关数据。数据总量达到38,115条，为模型训练提供了较为充足的数据支撑。在数据标注方面，已建立完善的\"谣言-非谣言-传播关系\"标注体系，并采用LLM大语言模型进行辅助标注和数据增强，有效提升了标注效率和数据质量。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("2. 模型训练与优化")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "在模型训练方面，项目已尝试多种深度学习模型并取得了较好效果。TextCNN模型作为基线模型达到了88.87%的准确率，参数量约为470万；CNN结合GRU和注意力机制的模型达到88.65%的准确率，同样具有约470万的参数量；而BERT预训练模型表现最佳，达到了90.40%的准确率，参数量约为1100万。通过多任务学习策略结合微调技术，最终的谣言检测系统准确率可达98.87%，远超预期目标。模型架构采用Embedding层连接多尺度CNN和双向GRU，再通过注意力机制进行特征融合，最后输出分类结果。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("3. 传播树结构建模")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "本项目的创新点之一是采用传播树结构对谣言传播过程进行建模。谣言在社交媒体中的传播呈现树状扩散结构，根节点为原始谣言，子节点为转发、评论和引用等传播行为。通过记录状态ID和父节点ID关系，利用NetworkX构建完整的传播图结构。模型采用Tree-LSTM架构捕捉树形结构信息，并引入Relation-Aware机制区分不同传播关系类型（转发、评论、引用），从而更准确地识别谣言的传播模式和扩散路径。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("4. 原型系统开发")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "在原型系统开发方面，已基于Streamlit框架搭建完成基础的演示系统。系统支持用户输入文本进行谣言检测，并能够展示检测结果和置信度。目前系统主要使用TextCNN模型进行实时预测，后续计划升级为训练好的优化模型以提升检测准确率。系统界面简洁直观，便于用户操作和结果查看，为后续功能扩展和性能优化奠定了基础。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_1,
                spacing: { before: 480 },
                children: [new TextRun("三、存在的主要问题和解决方案")] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("问题一：数据正负样本不平衡")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "在实际数据集中，谣言样本与非谣言样本的比例严重失衡，约为1比13。这种严重的类别不平衡会导致模型倾向于预测多数类，从而影响对谣言的识别能力。特别是某些子类别的样本数量严重不足，难以支持模型的充分学习。", size: 24 })] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "针对这一问题，计划采用LLM大语言模型进行数据增强和重采样。通过大语言模型对少数类样本进行重写和扩充，生成更多具有多样性的谣言样本。同时，将尝试使用加权损失函数和过采样技术，进一步改善模型的分类性能。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("问题二：爬取数据标签准确率低")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "在数据爬取过程中，由于原始数据未使用关键词精确匹配，导致部分遥感数据被错误标注。初步统计显示，约有244条数据被标记为\"未定义\"类别，标注的准确性和一致性存在问题，影响了训练数据的质量。", size: 24 })] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "为解决这一问题，将使用LLM辅助标注方法对数据进行二次处理。通过大语言模型对文本内容进行自动分析和判断，自动修正谣言、事实和未定义等标签类别。同时，将优化标注流程，建立标注质量控制机制，确保数据标签的准确性和一致性。", size: 24 })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2,
                children: [new TextRun("问题三：数据领域泛化能力不足")] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "当前训练数据主要来源较为单一，大部分数据来自清华微博谣言数据集。这种单一数据源导致模型存在领域偏差，泛化能力有限。当面对来自其他平台或不同话题的谣言时，模型的识别性能可能会有所下降。", size: 24 })] }),

            new Paragraph({ spacing: { after: 200 },
                children: [new TextRun({ text: "针对领域泛化问题，计划从以下几个方面进行改进：首先，扩展微博爬取的关键词范围，覆盖更多话题领域；其次，尝试跨平台数据采集，引入Twitter等其他社交平台的数据；第三，在模型训练中引入领域自适应技术，提升模型对不同领域数据的适应能力；第四，考虑收集更多来源于不同平台和不同事件类型的谣言数据，以增强模型的多样性和鲁棒性。", size: 24 })] }),
        ]
    }]
});

Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync("E:\\rumor_detection\\reports\\中期检查报告_v3.docx", buffer);
    console.log("Document created successfully!");
});
