const pptxgen = require("pptxgenjs");

// ============================================================
// 配色方案: Ocean Gradient (学术/技术主题)
// ============================================================
const C = {
  navy:     "1B3A6B",
  midBlue:  "2D6A8F",
  teal:     "0D7F8C",
  ice:      "A8D0E6",
  light:    "E8F4F8",
  white:    "FFFFFF",
  dark:     "1A1A2E",
  gray:     "64748B",
  accent:   "E85D04",
  green:    "2D6A4F",
};

let pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "毕业设计中期汇报";
pres.author = "谣言检测项目组";

// ============================================================
// 动画辅助函数
// ============================================================
function fadeIn(delay = 0) {
  return { animation: { type: "fadeIn", duration: 0.5, delay: delay } };
}
function flyIn(direction, delay = 0) {
  let xFrom = 0, yFrom = 0;
  if (direction === "left") xFrom = -1;
  if (direction === "right") xFrom = 1;
  if (direction === "up") yFrom = 0.5;
  if (direction === "down") yFrom = -0.5;
  return { animation: { type: "fly", direction: direction, duration: 0.5, delay: delay, xFrom, yFrom } };
}
function zoomIn(delay = 0) {
  return { animation: { type: "zoomIn", duration: 0.4, delay: delay } };
}
function wipeIn(direction, delay = 0) {
  return { animation: { type: "wipe", direction: direction, duration: 0.5, delay: delay } };
}
function slideIn(direction, delay = 0) {
  return { animation: { type: "slide", direction: direction, duration: 0.5, delay: delay } };
}

// ============================================================
// 辅助函数
// ============================================================
function addFooter(slide, pageNum, total) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.35, w: 10, h: 0.275,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText(`${pageNum} / ${total}`, {
    x: 9.2, y: 5.35, w: 0.7, h: 0.275,
    fontSize: 9, color: C.white, align: "center", valign: "middle"
  });
  slide.addText("社交媒体恶意谣言识别研究与实现", {
    x: 0.3, y: 5.35, w: 5, h: 0.275,
    fontSize: 9, color: C.ice, align: "left", valign: "middle"
  });
}

function addSectionTag(slide, label) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 0.7,
    fill: { color: C.accent }, line: { color: C.accent }
  });
  slide.addText(label, {
    x: 0.22, y: 0, w: 2, h: 0.7,
    fontSize: 10, color: C.gray, valign: "middle", margin: 0
  });
}

// ============================================================
// Slide 1: 封面
// ============================================================
{
  let slide = pres.addSlide();
  slide.background = { color: C.navy };

  // 装饰块
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.5, y: 0, w: 3.5, h: 5.625,
    fill: { color: C.midBlue, transparency: 40 },
    ...flyIn("right", 0.2)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 1.5, w: 6.2, h: 0.04,
    fill: { color: C.accent },
    ...wipeIn("right", 0.4)
  });
  slide.addText("毕业设计中期汇报", {
    x: 0.5, y: 1.65, w: 9, h: 0.7,
    fontSize: 14, color: C.ice, fontFace: "Microsoft YaHei",
    ...fadeIn(0.5)
  });
  slide.addText("社交媒体恶意谣言识别\n研究与实现", {
    x: 0.5, y: 2.3, w: 9, h: 1.2,
    fontSize: 36, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    ...flyIn("up", 0.6)
  });
  slide.addText("基于深度学习的中文微博谣言检测系统", {
    x: 0.5, y: 3.6, w: 6, h: 0.5,
    fontSize: 14, color: C.ice, fontFace: "Microsoft YaHei",
    ...fadeIn(0.8)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 8.2, y: 4.2, w: 1.2, h: 1.2,
    fill: { color: C.teal, transparency: 50 },
    ...zoomIn(1.0)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7.5, y: 4.5, w: 0.8, h: 0.8,
    fill: { color: C.accent, transparency: 60 },
    ...zoomIn(1.2)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.5, w: 10, h: 0.125,
    fill: { color: C.accent },
    ...wipeIn("left", 1.0)
  });

  slide.addNotes(`【汇报开场 — 约30秒】
- 问候各位评审老师
- 自我介绍
- 主题："我的毕设研究社交媒体谣言的自动检测"
- 直接翻下一页`);
}

// ============================================================
// Slide 2: 目录导航
// ============================================================
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 3.2, h: 5.625,
    fill: { color: C.navy },
    ...flyIn("left", 0)
  });
  slide.addText("CONTENTS", {
    x: 0.3, y: 0.5, w: 2.6, h: 0.4,
    fontSize: 11, color: C.ice, charSpacing: 4,
    ...fadeIn(0.2)
  });
  slide.addText("汇报\n大纲", {
    x: 0.3, y: 0.95, w: 2.6, h: 1.0,
    fontSize: 30, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    ...fadeIn(0.3)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 2.2, y: 4.3, w: 0.7, h: 0.7,
    fill: { color: C.teal, transparency: 60 },
    ...zoomIn(0.8)
  });

  const items = [
    { num: "01", title: "研究内容介绍" },
    { num: "02", title: "中期工作进展" },
    { num: "03", title: "存在问题与解决方案" },
    { num: "04", title: "下一步工作计划" },
  ];

  items.forEach((item, i) => {
    let y = 0.5 + i * 1.15;
    slide.addText(item.num, {
      x: 3.5, y: y, w: 0.7, h: 0.7,
      fontSize: 24, bold: true, color: C.accent,
      fontFace: "Georgia", valign: "middle", margin: 0,
      ...flyIn("right", 0.4 + i * 0.1)
    });
    slide.addText(item.title, {
      x: 4.3, y: y, w: 5, h: 0.7,
      fontSize: 18, color: C.dark, fontFace: "Microsoft YaHei",
      valign: "middle", margin: 0,
      ...fadeIn(0.5 + i * 0.1)
    });
    if (i < items.length - 1) {
      slide.addShape(pres.shapes.LINE, {
        x: 3.5, y: y + 0.9, w: 5.5, h: 0,
        line: { color: C.ice, width: 0.5 },
        ...fadeIn(0.6 + i * 0.1)
      });
    }
  });

  addFooter(slide, 2, 17);

  slide.addNotes(`【目录页 — 约10秒】
- 快速展示四个章节
- 一句话："我将从四个方面汇报"
- 直接翻页`);
}

// ============================================================
// 模块一：研究内容介绍
// ============================================================

// Slide 3: 章节页 - 研究内容介绍
{
  let slide = pres.addSlide();
  slide.background = { color: C.midBlue };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 2.2, w: 0.12, h: 1.2,
    fill: { color: C.accent },
    ...slideIn("left", 0)
  });
  slide.addText("01", {
    x: 0.4, y: 1.6, w: 1.5, h: 0.7,
    fontSize: 48, bold: true, color: C.white, fontFace: "Georgia", margin: 0,
    ...fadeIn(0.2)
  });
  slide.addText("研究内容介绍", {
    x: 0.4, y: 2.3, w: 8, h: 0.9,
    fontSize: 36, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    ...flyIn("up", 0.4)
  });
  slide.addText("RESEARCH INTRODUCTION", {
    x: 0.4, y: 3.1, w: 6, h: 0.4,
    fontSize: 11, color: C.ice, charSpacing: 3,
    ...fadeIn(0.6)
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 8.0, y: 3.8, w: 1.5, h: 1.5,
    fill: { color: C.teal, transparency: 50 },
    ...zoomIn(0.8)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7.3, y: 4.2, w: 0.9, h: 0.9,
    fill: { color: C.accent, transparency: 50 },
    ...zoomIn(1.0)
  });

  addFooter(slide, 3, 17);

  slide.addNotes(`【章节页 — 约5秒】
- "第一部分，研究内容介绍"
- 停顿，翻下一页`);
}

// Slide 4: 研究背景
{
  let slide = pres.addSlide();
  slide.background = { color: C.light };

  addSectionTag(slide, "研究背景");
  slide.addText("研究背景", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 左侧：问题
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.4, w: 4.4, h: 3.7,
    fill: { color: C.white },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
    ...flyIn("left", 0.3)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.4, w: 4.4, h: 0.5,
    fill: { color: C.accent },
    ...fadeIn(0.4)
  });
  slide.addText("社会问题", {
    x: 0.5, y: 1.45, w: 4, h: 0.4,
    fontSize: 14, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.5)
  });

  const problems = [
    "社交媒体谣言传播速度极快",
    "虚假信息严重危害社会秩序",
    "传统人工审核效率低下",
    "谣言变体多，难以全面识别"
  ];
  let problemItems = problems.map((t, j) => ({
    text: t,
    options: { bullet: true, breakLine: j < problems.length - 1, ...fadeIn(0.6 + j * 0.1) }
  }));
  slide.addText(problemItems, {
    x: 0.5, y: 2.1, w: 4.1, h: 2.8,
    fontSize: 12, color: C.dark, fontFace: "Microsoft YaHei",
    paraSpaceAfter: 10, valign: "top"
  });

  // 右侧：研究意义
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.0, y: 1.4, w: 4.65, h: 3.7,
    fill: { color: C.white },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
    ...flyIn("right", 0.4)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.0, y: 1.4, w: 4.65, h: 0.5,
    fill: { color: C.teal },
    ...fadeIn(0.5)
  });
  slide.addText("研究意义", {
    x: 5.15, y: 1.45, w: 4.3, h: 0.4,
    fontSize: 14, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.6)
  });

  const significance = [
    "NLP领域的热门研究方向",
    "深度学习技术持续突破",
    "助力平台内容审核自动化",
    "为舆情监控提供技术支撑"
  ];
  let sigItems = significance.map((t, j) => ({
    text: t,
    options: { bullet: true, breakLine: j < significance.length - 1, ...fadeIn(0.7 + j * 0.1) }
  }));
  slide.addText(sigItems, {
    x: 5.15, y: 2.1, w: 4.3, h: 2.8,
    fontSize: 12, color: C.dark, fontFace: "Microsoft YaHei",
    paraSpaceAfter: 10, valign: "top"
  });

  addFooter(slide, 4, 17);

  slide.addNotes(`【研究背景 — 约1分钟】
左侧问题（指着念）：
- 谣言传播快、危害大
- 人工审核效率低

右侧意义：
- NLP前沿问题
- 深度学习突破
- 应用价值广泛

【时间】约1分钟，快速过`);
}

// Slide 5: 研究目标
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "研究目标");
  slide.addText("研究目标", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 核心目标
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.4, w: 9.3, h: 0.7,
    fill: { color: C.navy },
    ...flyIn("left", 0.3)
  });
  slide.addText("核心目标：设计与实现基于深度学习的社交媒体谣言自动识别系统", {
    x: 0.5, y: 1.4, w: 9, h: 0.7,
    fontSize: 14, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    valign: "middle", margin: 0,
    ...fadeIn(0.5)
  });

  // 四个子目标
  const tasks = [
    { num: "T1", title: "数据采集与增强", desc: "采集公开数据集与微博数据，构建'谣言类型-立场倾向'二级标注体系，LLM生成对抗样本" },
    { num: "T2", title: "双分支融合模型", desc: "文本主导型基线模型 + '文本语义-多关系传播树'双分支融合架构" },
    { num: "T3", title: "预训练协同微调", desc: "采用'预训练-协同微调'模式训练，优化模型性能" },
    { num: "T4", title: "原型系统开发", desc: "开发轻量级原型系统，实现检测与结果可视化" },
  ];

  tasks.forEach((task, i) => {
    let row = Math.floor(i / 2);
    let col = i % 2;
    let x = 0.35 + col * 4.7;
    let y = 2.6 + row * 1.35;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 4.5, h: 1.15,
      fill: { color: C.light },
      ...flyIn("up", 0.5 + i * 0.12)
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: y, w: 0.08, h: 1.15,
      fill: { color: C.teal },
      ...fadeIn(0.6 + i * 0.12)
    });
    slide.addText(task.num, {
      x: x + 0.18, y: y + 0.1, w: 0.5, h: 0.4,
      fontSize: 14, bold: true, color: C.accent, fontFace: "Georgia", margin: 0,
      ...fadeIn(0.6 + i * 0.12)
    });
    slide.addText(task.title, {
      x: x + 0.7, y: y + 0.1, w: 3.6, h: 0.4,
      fontSize: 13, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.7 + i * 0.12)
    });
    slide.addText(task.desc, {
      x: x + 0.7, y: y + 0.55, w: 3.6, h: 0.5,
      fontSize: 10, color: C.gray, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.8 + i * 0.12)
    });
  });

  addFooter(slide, 5, 17);

  slide.addNotes(`【研究目标 — 约1分钟】
核心目标（指着深色条）："构建谣言自动识别系统"

四个子目标：
- T1数据：采集公开数据集+微博爬虫，LLM增强数据
- T2模型：文本语义+传播树双分支融合
- T3训练：预训练-协同微调模式
- T4系统：轻量级原型系统+可视化

【可能被问】双分支融合优势？→ "结合文本语义与传播结构信息"
【时间】约1分钟`);
}

// ============================================================
// Slide 6: 研究内容详解（技术路线）
// ============================================================
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "研究内容");
  slide.addText("研究内容与技术路线", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 技术路线流程
  const steps = [
    { num: "1", title: "数据采集", desc: "公开数据集+微博爬虫" },
    { num: "2", title: "二级标注", desc: "谣言类型+立场倾向" },
    { num: "3", title: "LLM增强", desc: "生成对抗样本" },
    { num: "4", title: "双分支模型", desc: "文本+传播树融合" },
    { num: "5", title: "协同微调", desc: "预训练-微调" },
    { num: "6", title: "原型系统", desc: "检测+可视化" },
  ];

  steps.forEach((step, i) => {
    let x = 0.35 + i * 1.55;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.4, w: 1.4, h: 1.6,
      fill: { color: C.light },
      ...flyIn("up", 0.3 + i * 0.08)
    });
    slide.addShape(pres.shapes.OVAL, {
      x: x + 0.45, y: 1.5, w: 0.5, h: 0.5,
      fill: { color: C.teal },
      ...zoomIn(0.5 + i * 0.08)
    });
    slide.addText(step.num, {
      x: x + 0.45, y: 1.5, w: 0.5, h: 0.5,
      fontSize: 14, bold: true, color: C.white, fontFace: "Georgia",
      align: "center", valign: "middle", margin: 0,
    });
    slide.addText(step.title, {
      x: x + 0.05, y: 2.1, w: 1.3, h: 0.35,
      fontSize: 10, bold: true, color: C.navy, fontFace: "Microsoft YaHei",
      align: "center", margin: 0,
    });
    slide.addText(step.desc, {
      x: x + 0.05, y: 2.45, w: 1.3, h: 0.45,
      fontSize: 8, color: C.gray, fontFace: "Microsoft YaHei",
      align: "center", margin: 0,
    });

    if (i < steps.length - 1) {
      slide.addText("→", {
        x: x + 1.3, y: 1.9, w: 0.3, h: 0.5,
        fontSize: 14, color: C.teal, align: "center", valign: "middle",
      });
    }
  });

  // 关键方法说明
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 3.2, w: 9.3, h: 2.1,
    fill: { color: C.light },
    ...flyIn("left", 0.4)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 3.2, w: 9.3, h: 0.45,
    fill: { color: C.navy },
    ...fadeIn(0.6)
  });
  slide.addText("关键技术方法", {
    x: 0.5, y: 3.22, w: 9, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
  });

  const methods = [
    { title: "多维度特征融合", desc: "结合文本语义、立场倾向、传播结构等多维度特征" },
    { title: "神经多任务学习", desc: "谣言分类+立场判断+情感极性协同检测" },
    { title: "预训练-微调模式", desc: "BERT预训练+任务特定微调，优化中文适配" },
  ];

  methods.forEach((m, i) => {
    slide.addText(m.title, {
      x: 0.5 + i * 3.1, y: 3.75, w: 2.9, h: 0.35,
      fontSize: 11, bold: true, color: C.accent, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.7 + i * 0.1)
    });
    slide.addText(m.desc, {
      x: 0.5 + i * 3.1, y: 4.15, w: 2.9, h: 0.9,
      fontSize: 10, color: C.dark, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.8 + i * 0.1)
    });
  });

  addFooter(slide, 6, 17);

  slide.addNotes(`【研究内容与技术路线 — 约1分钟】
指着流程图：
1. 数据采集：公开数据集+微博爬虫
2. 二级标注：谣言类型+立场倾向
3. LLM增强：生成对抗样本
4. 双分支模型：文本+传播树融合
5. 协同微调：预训练-微调
6. 原型系统：检测+可视化

关键方法：
- 多维度特征融合
- 神经多任务学习
- 预训练-微调模式

【时间】约1分钟`);
}

// ============================================================
// Slide 7: 模型架构对比
// ============================================================
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "模型架构");
  slide.addText("模型架构对比", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 三模型对比
  const models = [
    {
      name: "TextCNN",
      type: "Baseline",
      features: ["多尺度卷积", "词向量表示", "轻量级"],
      accuracy: "98.83%",
      color: C.gray
    },
    {
      name: "CNN+GRU+Attention",
      type: "主模型",
      features: ["CNN特征提取", "GRU时序建模", "Attention融合", "双任务输出"],
      accuracy: "98.87%",
      color: C.teal
    },
    {
      name: "BERT",
      type: "预训练模型",
      features: ["BERT预训练", "中文适配", "通用语义", "微调下游"],
      accuracy: "97.53%",
      color: C.midBlue
    },
  ];

  models.forEach((m, i) => {
    let x = 0.35 + i * 3.15;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.35, w: 2.95, h: 3.8,
      fill: { color: C.light },
      ...flyIn("up", 0.3 + i * 0.12)
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.35, w: 2.95, h: 0.5,
      fill: { color: m.color },
      ...fadeIn(0.4 + i * 0.12)
    });
    slide.addText(m.name, {
      x: x, y: 1.35, w: 2.95, h: 0.5,
      fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei",
      align: "center", valign: "middle", margin: 0,
    });
    slide.addText(m.type, {
      x: x + 0.1, y: 1.95, w: 2.75, h: 0.3,
      fontSize: 10, color: m.color, fontFace: "Microsoft YaHei",
      align: "center", margin: 0,
    });

    // 准确率
    slide.addText(m.accuracy, {
      x: x + 0.1, y: 2.3, w: 2.75, h: 0.5,
      fontSize: 24, bold: true, color: C.accent, fontFace: "Georgia",
      align: "center", valign: "middle",
      ...zoomIn(0.5 + i * 0.12)
    });
    slide.addText("验证准确率", {
      x: x + 0.1, y: 2.8, w: 2.75, h: 0.25,
      fontSize: 8, color: C.gray, fontFace: "Microsoft YaHei",
      align: "center", margin: 0,
    });

    // 特点
    m.features.forEach((f, j) => {
      slide.addText("• " + f, {
        x: x + 0.15, y: 3.15 + j * 0.4, w: 2.65, h: 0.35,
        fontSize: 10, color: C.dark, fontFace: "Microsoft YaHei",
        margin: 0,
      });
    });
  });

  // 底部结论
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 5.0, w: 9.3, h: 0.45,
    fill: { color: C.navy },
    ...flyIn("left", 0.8)
  });
  slide.addText("结论：CNN+GRU+Attention 在准确率和效率上表现最佳，选择作为主模型", {
    x: 0.5, y: 5.0, w: 9, h: 0.45,
    fontSize: 11, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    valign: "middle", margin: 0,
  });

  addFooter(slide, 7, 17);

  slide.addNotes(`【模型架构对比 — 约1分钟】
三个模型对比：

TextCNN (Baseline):
- 准确率: 98.83%
- 特点：多尺度卷积，轻量级

CNN+GRU+Attention (主模型):
- 准确率: 98.87% (最高)
- 特点：CNN+GRU+Attention双任务

BERT:
- 准确率: 97.53%
- 特点：预训练模型，中文适配

结论：选择CNN+GRU+Attention作为主模型
【时间】约1分钟`);
}

// ============================================================
// 模块二：中期工作进展
// ============================================================

// Slide 8: 章节页 - 中期工作进展
{
  let slide = pres.addSlide();
  slide.background = { color: C.teal };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 2.2, w: 0.12, h: 1.2,
    fill: { color: C.white },
    ...slideIn("left", 0)
  });
  slide.addText("02", {
    x: 0.4, y: 1.6, w: 1.5, h: 0.7,
    fontSize: 48, bold: true, color: C.white, fontFace: "Georgia", margin: 0,
    ...fadeIn(0.2)
  });
  slide.addText("中期工作进展", {
    x: 0.4, y: 2.3, w: 8, h: 0.9,
    fontSize: 36, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    ...flyIn("up", 0.4)
  });
  slide.addText("PROGRESS SUMMARY", {
    x: 0.4, y: 3.1, w: 6, h: 0.4,
    fontSize: 11, color: C.ice, charSpacing: 3,
    ...fadeIn(0.6)
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 8.0, y: 3.8, w: 1.5, h: 1.5,
    fill: { color: C.navy, transparency: 50 },
    ...zoomIn(0.8)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7.3, y: 4.2, w: 0.9, h: 0.9,
    fill: { color: C.white, transparency: 60 },
    ...zoomIn(1.0)
  });

  addFooter(slide, 8, 17);

  slide.addNotes(`【章节页 — 约5秒】
- "第二部分，中期工作进展"
- 翻页`);
}

// Slide 9: 中期工作进展
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "中期工作进展");
  slide.addText("中期工作进展", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 两大模块卡片 - 左右布局
  const modules = [
    {
      title: "数据采集与处理",
      stats: "38,115条",
      color: C.teal,
      items: [
        "微博爬虫: 6,638条",
        "清华数据集: 31,477条",
        "谣言-立场二级标注体系",
        "LLM辅助标注增强"
      ]
    },
    {
      title: "模型训练与优化",
      stats: "98.87%",
      color: C.navy,
      items: [
        "TextCNN: 98.83%",
        "CNN+GRU+Attention: 98.87%",
        "BERT: 97.53%",
        "多任务联合学习"
      ]
    }
  ];

  modules.forEach((mod, i) => {
    let x = 0.35 + i * 4.7;

    // 卡片背景
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.35, w: 4.5, h: 2.5,
      fill: { color: C.light },
      ...flyIn(i === 0 ? "left" : "right", 0.3 + i * 0.15)
    });

    // 左侧色条
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.35, w: 0.1, h: 2.5,
      fill: { color: mod.color },
      ...fadeIn(0.4 + i * 0.1)
    });

    // 模块标题
    slide.addText(mod.title, {
      x: x + 0.25, y: 1.45, w: 4, h: 0.4,
      fontSize: 15, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.5 + i * 0.1)
    });

    // 大数字
    slide.addText(mod.stats, {
      x: x + 0.25, y: 1.9, w: 4, h: 0.55,
      fontSize: 28, bold: true, color: mod.color, fontFace: "Georgia", margin: 0,
      ...fadeIn(0.55 + i * 0.1)
    });

    // 分隔线
    slide.addShape(pres.shapes.LINE, {
      x: x + 0.25, y: 2.5, w: 4, h: 0,
      line: { color: "E0E0E0", width: 0.5 },
      ...fadeIn(0.6 + i * 0.1)
    });

    // 详细内容
    mod.items.forEach((item, j) => {
      slide.addText("• " + item, {
        x: x + 0.25, y: 2.6 + j * 0.4, w: 4, h: 0.4,
        fontSize: 11, color: C.dark, fontFace: "Microsoft YaHei", margin: 0,
        ...fadeIn(0.65 + i * 0.1 + j * 0.05)
      });
    });
  });

  // 底部总结
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 4.05, w: 9.3, h: 0.55,
    fill: { color: C.navy },
    ...fadeIn(0.8)
  });
  slide.addText("核心成果：基于多任务深度学习的微博谣言检测系统，准确率达98.87%", {
    x: 0.5, y: 4.1, w: 9, h: 0.45,
    fontSize: 13, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    align: "center", valign: "middle", margin: 0,
    ...fadeIn(0.9)
  });

  addFooter(slide, 9, 17);

  slide.addNotes(`【中期工作进展 — 约2分钟】
两大模块进展：

1. 数据采集与处理
   - 微博爬虫采集6,638条数据
   - 整合清华数据集31,477条
   - 建立"谣言类型-立场倾向"二级标注体系
   - 使用LLM辅助标注和增强

2. 模型训练与优化
   - TextCNN: 98.83%
   - CNN+GRU+Attention: 98.87% (最佳)
   - BERT: 97.53%
   - 多任务联合学习谣言分类+立场检测

原型系统开发（进行中）：基于Streamlit开发交互界面，当前使用模拟检测，待集成真实训练模型

【时间】2分钟`);
}

// Slide 9-1: 数据采集与处理详情
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "中期工作进展");
  slide.addText("数据采集与处理", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 数据来源三列
  const dataSources = [
    {
      title: "微博爬虫采集",
      count: "6,638条",
      items: ["多关键词采集", "谣言/辟谣账号", "实时增量更新", "二级标注体系"]
    },
    {
      title: "公开数据集",
      count: "31,477条",
      items: ["清华微博谣言数据集", "THU_Rumor", "权威标注数据", "高质量基准数据"]
    },
    {
      title: "LLM辅助增强",
      count: "15,000+条",
      items: ["立场变换增强", "语义变换增强", "标签自动标注", "数据质量验证"]
    }
  ];

  dataSources.forEach((src, i) => {
    let x = 0.35 + i * 3.15;

    // 卡片
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.35, w: 3.0, h: 2.6,
      fill: { color: C.light },
      ...flyIn(i === 0 ? "left" : (i === 1 ? "up" : "right"), 0.3 + i * 0.1)
    });

    // 顶部色条
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.35, w: 3.0, h: 0.08,
      fill: { color: i === 0 ? C.teal : (i === 1 ? C.navy : C.accent) },
      ...fadeIn(0.4 + i * 0.1)
    });

    slide.addText(src.title, {
      x: x + 0.15, y: 1.5, w: 2.7, h: 0.35,
      fontSize: 13, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.5 + i * 0.1)
    });

    slide.addText(src.count, {
      x: x + 0.15, y: 1.85, w: 2.7, h: 0.45,
      fontSize: 20, bold: true, color: i === 0 ? C.teal : (i === 1 ? C.navy : C.accent),
      fontFace: "Georgia", margin: 0,
      ...fadeIn(0.55 + i * 0.1)
    });

    src.items.forEach((item, j) => {
      slide.addText("• " + item, {
        x: x + 0.15, y: 2.4 + j * 0.35, w: 2.7, h: 0.35,
        fontSize: 10, color: C.dark, fontFace: "Microsoft YaHei", margin: 0,
        ...fadeIn(0.6 + i * 0.1 + j * 0.05)
      });
    });
  });

  // 标注体系说明
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 4.1, w: 9.3, h: 0.85,
    fill: { color: C.navy },
    ...fadeIn(0.7)
  });
  slide.addText("\"谣言类型 - 立场倾向\"二级标注体系", {
    x: 0.5, y: 4.15, w: 9, h: 0.35,
    fontSize: 13, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.8)
  });
  slide.addText("谣言类型：假谣言 / 真谣言 / 未证实    立场倾向：支持 / 反对 / 中立", {
    x: 0.5, y: 4.5, w: 9, h: 0.35,
    fontSize: 11, color: C.ice, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.85)
  });

  addFooter(slide, 10, 17);
}

// Slide 9-2: 模型训练与优化详情
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "中期工作进展");
  slide.addText("模型训练与优化", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 模型对比表格
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.35, w: 9.3, h: 2.2,
    fill: { color: C.light },
    ...fadeIn(0.3)
  });

  // 表头
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.35, w: 9.3, h: 0.45,
    fill: { color: C.navy }
  });
  slide.addText("模型", {
    x: 0.5, y: 1.38, w: 2.5, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0
  });
  slide.addText("验证准确率", {
    x: 3.0, y: 1.38, w: 1.8, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0
  });
  slide.addText("立场检测", {
    x: 4.8, y: 1.38, w: 1.5, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0
  });
  slide.addText("参数量", {
    x: 6.3, y: 1.38, w: 1.5, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0
  });
  slide.addText("特点", {
    x: 7.8, y: 1.38, w: 1.8, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0
  });

  // 数据行
  const modelRows = [
    { name: "CNN+GRU+Attention", acc: "98.87%", stance: "98.57%", params: "~2.5M", feature: "最佳模型" },
    { name: "TextCNN", acc: "98.83%", stance: "-", params: "~1.2M", feature: "轻量高效" },
    { name: "BERT", acc: "97.53%", stance: "-", params: "~110M", feature: "语义理解强" }
  ];

  modelRows.forEach((row, i) => {
    let y = 1.85 + i * 0.55;
    let bgColor = i % 2 === 0 ? "FFFFFF" : "F5F7FA";

    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.35, y: y, w: 9.3, h: 0.55,
      fill: { color: bgColor }
    });

    slide.addText(row.name, {
      x: 0.5, y: y + 0.1, w: 2.5, h: 0.35,
      fontSize: 11, color: C.dark, fontFace: "Microsoft YaHei", margin: 0
    });
    slide.addText(row.acc, {
      x: 3.0, y: y + 0.1, w: 1.8, h: 0.35,
      fontSize: 11, bold: true, color: C.accent, fontFace: "Georgia", margin: 0
    });
    slide.addText(row.stance, {
      x: 4.8, y: y + 0.1, w: 1.5, h: 0.35,
      fontSize: 11, color: C.dark, fontFace: "Microsoft YaHei", margin: 0
    });
    slide.addText(row.params, {
      x: 6.3, y: y + 0.1, w: 1.5, h: 0.35,
      fontSize: 11, color: C.dark, fontFace: "Microsoft YaHei", margin: 0
    });
    slide.addText(row.feature, {
      x: 7.8, y: y + 0.1, w: 1.8, h: 0.35,
      fontSize: 11, color: C.teal, fontFace: "Microsoft YaHei", margin: 0
    });
  });

  // 多任务学习说明
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 3.7, w: 4.4, h: 1.2,
    fill: { color: C.navy },
    ...fadeIn(0.5)
  });
  slide.addText("多任务联合学习", {
    x: 0.5, y: 3.8, w: 4, h: 0.35,
    fontSize: 13, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.6)
  });
  slide.addText([
    { text: "• 谣言分类 + 立场检测联合训练", options: { breakLine: true } },
    { text: "• 共享表征层，提升泛化能力", options: { breakLine: true } },
    { text: "• 双向任务协同优化" }
  ], {
    x: 0.5, y: 4.15, w: 4, h: 0.7,
    fontSize: 10, color: C.ice, fontFace: "Microsoft YaHei",
    paraSpaceAfter: 3
  });

  // 训练策略
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.9, y: 3.7, w: 4.75, h: 1.2,
    fill: { color: C.teal },
    ...fadeIn(0.55)
  });
  slide.addText("训练策略", {
    x: 5.05, y: 3.8, w: 4.4, h: 0.35,
    fontSize: 13, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.65)
  });
  slide.addText([
    { text: "• 5折交叉验证选最优", options: { breakLine: true } },
    { text: "• Early Stopping防过拟合", options: { breakLine: true } },
    { text: "• 学习率动态调整" }
  ], {
    x: 5.05, y: 4.15, w: 4.4, h: 0.7,
    fontSize: 10, color: C.ice, fontFace: "Microsoft YaHei",
    paraSpaceAfter: 3
  });

  addFooter(slide, 11, 17);
}

// ============================================================
// Slide 12: 传播树结构建模详情（创新点）
// ============================================================
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "中期工作进展");
  slide.addText("创新点：传播树结构建模", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  // 左侧：传播树结构示意
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.35, w: 4.2, h: 3.0,
    fill: { color: C.light },
    ...flyIn("left", 0.3)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.35, w: 4.2, h: 0.45,
    fill: { color: C.teal },
    ...fadeIn(0.4)
  });
  slide.addText("谣言传播树结构示意", {
    x: 0.5, y: 1.38, w: 4, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
  });

  // 树形结构图示
  // 根节点
  slide.addShape(pres.shapes.OVAL, {
    x: 2.0, y: 1.95, w: 0.55, h: 0.55,
    fill: { color: C.accent },
    ...fadeIn(0.5)
  });
  slide.addText("R", {
    x: 2.0, y: 1.95, w: 0.55, h: 0.55,
    fontSize: 14, bold: true, color: C.white, fontFace: "Georgia",
    align: "center", valign: "middle", margin: 0,
  });

  // 连接线
  slide.addShape(pres.shapes.LINE, {
    x: 2.27, y: 2.5, w: -0.6, h: 0.5,
    line: { color: C.gray, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 2.27, y: 2.5, w: 0.6, h: 0.5,
    line: { color: C.gray, width: 1.5 }
  });
  slide.addShape(pres.shapes.LINE, {
    x: 2.27, y: 2.5, w: 0, h: 0.6,
    line: { color: C.gray, width: 1.5 }
  });

  // F节点
  slide.addShape(pres.shapes.OVAL, {
    x: 1.35, y: 2.9, w: 0.45, h: 0.45,
    fill: { color: C.navy }
  });
  slide.addText("F", {
    x: 1.35, y: 2.9, w: 0.45, h: 0.45,
    fontSize: 12, bold: true, color: C.white, fontFace: "Georgia",
    align: "center", valign: "middle", margin: 0,
  });

  // C节点
  slide.addShape(pres.shapes.OVAL, {
    x: 2.55, y: 2.9, w: 0.45, h: 0.45,
    fill: { color: C.midBlue }
  });
  slide.addText("C", {
    x: 2.55, y: 2.9, w: 0.45, h: 0.45,
    fontSize: 12, bold: true, color: C.white, fontFace: "Georgia",
    align: "center", valign: "middle", margin: 0,
  });

  // Q节点
  slide.addShape(pres.shapes.OVAL, {
    x: 3.5, y: 2.9, w: 0.45, h: 0.45,
    fill: { color: C.teal }
  });
  slide.addText("Q", {
    x: 3.5, y: 2.9, w: 0.45, h: 0.45,
    fontSize: 12, bold: true, color: C.white, fontFace: "Georgia",
    align: "center", valign: "middle", margin: 0,
  });

  // 图例
  slide.addText("R: 根节点(谣言)", { x: 0.5, y: 3.5, w: 1.8, h: 0.25, fontSize: 8, color: C.dark, fontFace: "Microsoft YaHei", margin: 0 });
  slide.addText("F: Forward(转发)", { x: 0.5, y: 3.75, w: 1.8, h: 0.25, fontSize: 8, color: C.dark, fontFace: "Microsoft YaHei", margin: 0 });
  slide.addText("C: Comment(评论)", { x: 2.3, y: 3.5, w: 1.8, h: 0.25, fontSize: 8, color: C.dark, fontFace: "Microsoft YaHei", margin: 0 });
  slide.addText("Q: Quote(引用)", { x: 2.3, y: 3.75, w: 1.8, h: 0.25, fontSize: 8, color: C.dark, fontFace: "Microsoft YaHei", margin: 0 });

  // 说明文字
  slide.addText("通过记录status_id和parent_id关系，", { x: 0.5, y: 4.05, w: 4, h: 0.25, fontSize: 9, color: C.gray, fontFace: "Microsoft YaHei", margin: 0 });
  slide.addText("利用NetworkX构建完整传播图结构", { x: 0.5, y: 4.25, w: 4, h: 0.25, fontSize: 9, color: C.gray, fontFace: "Microsoft YaHei", margin: 0 });

  // 右侧：技术要点
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.75, y: 1.35, w: 4.9, h: 3.0,
    fill: { color: C.light },
    ...flyIn("right", 0.4)
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.75, y: 1.35, w: 4.9, h: 0.45,
    fill: { color: C.navy },
    ...fadeIn(0.5)
  });
  slide.addText("关键技术方法", {
    x: 4.9, y: 1.38, w: 4.6, h: 0.4,
    fontSize: 12, bold: true, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
  });

  const techPoints = [
    { title: "Tree-LSTM架构", desc: "利用树状长短期记忆网络，捕捉谣言传播的时序依赖和层级结构信息" },
    { title: "Relation-Aware机制", desc: "区分转发、评论、引用三种传播关系类型，引入关系感知矩阵" },
    { title: "多关系传播树", desc: "构建包含多种关系类型的传播图，保留原始传播路径的结构信息" }
  ];

  techPoints.forEach((tp, i) => {
    let y = 1.95 + i * 0.8;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 4.9, y: y, w: 0.06, h: 0.65,
      fill: { color: C.accent },
      ...fadeIn(0.6 + i * 0.1)
    });
    slide.addText(tp.title, {
      x: 5.05, y: y, w: 4.5, h: 0.3,
      fontSize: 11, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.65 + i * 0.1)
    });
    slide.addText(tp.desc, {
      x: 5.05, y: y + 0.3, w: 4.5, h: 0.4,
      fontSize: 9, color: C.dark, fontFace: "Microsoft YaHei", margin: 0,
      ...fadeIn(0.7 + i * 0.1)
    });
  });

  // 底部：创新意义
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 4.5, w: 9.3, h: 0.7,
    fill: { color: C.navy },
    ...flyIn("left", 0.5)
  });
  slide.addText("创新意义", {
    x: 0.5, y: 4.55, w: 1.2, h: 0.25,
    fontSize: 10, bold: true, color: C.accent, fontFace: "Microsoft YaHei", margin: 0,
  });
  slide.addText("结合传播树结构信息与文本语义特征，实现谣言传播模式识别与扩散路径预测的双重任务", {
    x: 0.5, y: 4.8, w: 9, h: 0.35,
    fontSize: 11, color: C.white, fontFace: "Microsoft YaHei", margin: 0,
  });

  addFooter(slide, 12, 17);
}

// ============================================================
// 模块三：存在问题与解决方案
// ============================================================

// Slide 13: 章节页 - 存在问题与解决方案
{
  let slide = pres.addSlide();
  slide.background = { color: C.navy };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 2.2, w: 0.12, h: 1.2,
    fill: { color: C.accent },
    ...slideIn("left", 0)
  });
  slide.addText("03", {
    x: 0.4, y: 1.6, w: 1.5, h: 0.7,
    fontSize: 48, bold: true, color: C.white, fontFace: "Georgia", margin: 0,
    ...fadeIn(0.2)
  });
  slide.addText("存在问题与解决方案", {
    x: 0.4, y: 2.3, w: 8, h: 0.9,
    fontSize: 36, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    ...flyIn("up", 0.4)
  });
  slide.addText("PROBLEMS & SOLUTIONS", {
    x: 0.4, y: 3.1, w: 6, h: 0.4,
    fontSize: 11, color: C.ice, charSpacing: 3,
    ...fadeIn(0.6)
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 8.0, y: 3.8, w: 1.5, h: 1.5,
    fill: { color: C.midBlue, transparency: 40 },
    ...zoomIn(0.8)
  });

  addFooter(slide, 13, 17);

  slide.addNotes(`【章节页 — 约5秒】
- "第三部分，存在问题与解决方案"
- 翻页`);
}

// Slide 14: 问题与对策详情
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "问题与对策");
  slide.addText("问题与解决方案", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  const issues = [
    {
      problem: "测试数据量不足",
      cause: "爬取的原始数据仅有6638条，远低于训练数据量，无法充分评估模型在真实场景下的泛化能力",
      solution: "使用LLM对爬取数据进行立场和语义变换增强，目标扩充至15000条测试样本"
    },
    {
      problem: "爬取数据标签不准确",
      cause: "原数据采用关键词匹配进行自动标注，244条标记为'未分类'，标注质量难以保证",
      solution: "引入LLM对内容进行智能判断，自动标注谣言/真实/未证实标签"
    },
    {
      problem: "数据规模与多样性不足",
      cause: "当前训练数据主要来源于清华谣言数据集，领域覆盖单一，多样性不足",
      solution: "扩展微博爬虫关键词，覆盖更多领域；同时引入多语言数据支持"
    }
  ];

  issues.forEach((issue, i) => {
    let y = 1.35 + i * 1.35;

    // 问题卡片
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.35, y: y, w: 9.3, h: 1.2,
      fill: { color: C.light },
      ...flyIn("up", 0.3 + i * 0.15)
    });

    // 问题标题
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.35, y: y, w: 0.08, h: 1.2,
      fill: { color: C.accent },
      ...fadeIn(0.5 + i * 0.15)
    });
    slide.addText("问题", {
      x: 0.55, y: y + 0.08, w: 0.6, h: 0.25,
      fontSize: 9, bold: true, color: C.accent, fontFace: "Microsoft YaHei", margin: 0,
    });
    slide.addText(issue.problem, {
      x: 0.55, y: y + 0.3, w: 3.0, h: 0.35,
      fontSize: 11, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    });

    // 原因
    slide.addText("原因", {
      x: 3.6, y: y + 0.08, w: 0.6, h: 0.25,
      fontSize: 9, bold: true, color: C.gray, fontFace: "Microsoft YaHei", margin: 0,
    });
    slide.addText(issue.cause, {
      x: 3.6, y: y + 0.35, w: 2.7, h: 0.8,
      fontSize: 9, color: C.dark, fontFace: "Microsoft YaHei", margin: 0,
    });

    // 解决方案
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 6.5, y: y + 0.1, w: 0.08, h: 1.0,
      fill: { color: C.green },
      ...fadeIn(0.6 + i * 0.15)
    });
    slide.addText("解决方案", {
      x: 6.7, y: y + 0.08, w: 1.0, h: 0.25,
      fontSize: 9, bold: true, color: C.green, fontFace: "Microsoft YaHei", margin: 0,
    });
    slide.addText(issue.solution, {
      x: 6.7, y: y + 0.35, w: 2.8, h: 0.8,
      fontSize: 9, color: C.dark, fontFace: "Microsoft YaHei", margin: 0,
    });
  });

  addFooter(slide, 14, 17);

  slide.addNotes(`【问题与对策 — 约2分钟】
这是我们目前遇到的真实问题：

1. 测试数据量不足
   现状：爬取仅6638条，远低于训练数据量
   解决：用LLM增强至15000条（已修改脚本）

2. 爬取数据标签不准确
   现状：关键词自动标注，244条'未分类'
   解决：LLM智能判断标签（已修改脚本）

3. 数据规模与多样性不足
   现状：数据来源单一，多样性差
   解决：扩展爬虫关键词，引入多语言数据

【时间】2分钟`);
}

// ============================================================
// 模块四：下一步工作计划
// ============================================================

// Slide 15: 章节页 - 下一步工作计划
{
  let slide = pres.addSlide();
  slide.background = { color: C.midBlue };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 2.2, w: 0.12, h: 1.2,
    fill: { color: C.white },
    ...slideIn("left", 0)
  });
  slide.addText("04", {
    x: 0.4, y: 1.6, w: 1.5, h: 0.7,
    fontSize: 48, bold: true, color: C.white, fontFace: "Georgia", margin: 0,
    ...fadeIn(0.2)
  });
  slide.addText("下一步工作计划", {
    x: 0.4, y: 2.3, w: 8, h: 0.9,
    fontSize: 36, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    ...flyIn("up", 0.4)
  });
  slide.addText("FUTURE WORK PLAN", {
    x: 0.4, y: 3.1, w: 6, h: 0.4,
    fontSize: 11, color: C.ice, charSpacing: 3,
    ...fadeIn(0.6)
  });

  slide.addShape(pres.shapes.OVAL, {
    x: 8.0, y: 3.8, w: 1.5, h: 1.5,
    fill: { color: C.teal, transparency: 40 },
    ...zoomIn(0.8)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7.3, y: 4.2, w: 0.9, h: 0.9,
    fill: { color: C.white, transparency: 60 },
    ...zoomIn(1.0)
  });

  addFooter(slide, 15, 17);

  slide.addNotes(`【章节页 — 约5秒】
- "第四部分，下一步工作计划"
- 翻页`);
}

// Slide 16: 下一步工作计划详情
{
  let slide = pres.addSlide();
  slide.background = { color: C.white };

  addSectionTag(slide, "下一步计划");
  slide.addText("下一步工作安排", {
    x: 0.22, y: 0.75, w: 9, h: 0.55,
    fontSize: 24, bold: true, color: C.navy, fontFace: "Microsoft YaHei", margin: 0,
    ...fadeIn(0.2)
  });

  const phases = [
    {
      phase: "近期",
      color: C.teal,
      items: ["集成传播树模块到主模型", "引入预训练语言模型微调", "开展更多对比实验"]
    },
    {
      phase: "中期",
      color: C.midBlue,
      items: ["系统集成与性能优化", "撰写毕业论文初稿", "整理实验数据与可视化"]
    },
    {
      phase: "后期",
      color: C.navy,
      items: ["完善Streamlit原型系统", "支持实时谣言检测演示", "前端界面美化与交互优化"]
    },
  ];

  phases.forEach((p, i) => {
    let x = 0.35 + i * 3.15;

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 1.4, w: 2.95, h: 0.6,
      fill: { color: p.color },
      ...flyIn("up", 0.3 + i * 0.15)
    });
    slide.addText(p.phase, {
      x: x, y: 1.4, w: 2.95, h: 0.6,
      fontSize: 12, bold: true, color: C.white,
      fontFace: "Microsoft YaHei", align: "center", valign: "middle",
      ...fadeIn(0.5 + i * 0.15)
    });

    slide.addShape(pres.shapes.RECTANGLE, {
      x: x, y: 2.0, w: 2.95, h: 2.5,
      fill: { color: C.light },
      ...flyIn("up", 0.4 + i * 0.15)
    });

    let bulletItems = p.items.map((t, j) => ({
      text: t,
      options: { bullet: true, breakLine: j < p.items.length - 1, ...fadeIn(0.6 + i * 0.15 + j * 0.08) }
    }));
    slide.addText(bulletItems, {
      x: x + 0.12, y: 2.15, w: 2.7, h: 2.2,
      fontSize: 11, color: C.dark, fontFace: "Microsoft YaHei",
      paraSpaceAfter: 8, valign: "top"
    });

    if (i < phases.length - 1) {
      slide.addText("→", {
        x: x + 2.85, y: 1.4, w: 0.4, h: 0.6,
        fontSize: 18, color: C.gray, align: "center", valign: "middle",
        ...fadeIn(0.7 + i * 0.15)
      });
    }
  });

  // 底部目标
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 4.65, w: 9.3, h: 0.6,
    fill: { color: C.navy },
    ...flyIn("left", 0.8)
  });
  slide.addText("目标：在毕业答辩前完成一个完整的谣言检测系统，包含理论研究与原型实现", {
    x: 0.5, y: 4.65, w: 9, h: 0.6,
    fontSize: 11, bold: true, color: C.white,
    fontFace: "Microsoft YaHei", valign: "middle", margin: 0,
    ...fadeIn(1.0)
  });

  addFooter(slide, 16, 17);

  slide.addNotes(`【下一步计划 — 约1分钟】
指着时间轴：
- 近期：集成传播树+预训练模型
- 中期：系统优化+论文撰写
- 后期：完善原型系统+实时演示

总目标：答辩前完成完整系统

【结束语】"以上是我的中期汇报，感谢老师，请批评指正！"`);
}

// ============================================================
// Slide 17: 致谢
// ============================================================
{
  let slide = pres.addSlide();
  slide.background = { color: C.navy };

  // 装饰圆形
  slide.addShape(pres.shapes.OVAL, {
    x: -1, y: -1, w: 3, h: 3,
    fill: { color: C.midBlue, transparency: 60 },
    ...zoomIn(0.5)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 8, y: 4, w: 2.5, h: 2.5,
    fill: { color: C.teal, transparency: 50 },
    ...zoomIn(0.8)
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7, y: 4.5, w: 1.5, h: 1.5,
    fill: { color: C.accent, transparency: 60 },
    ...zoomIn(1.0)
  });

  // 致谢标题
  slide.addText("致谢", {
    x: 0.5, y: 1.8, w: 9, h: 1.0,
    fontSize: 48, bold: true, color: C.white, fontFace: "Microsoft YaHei",
    align: "center", valign: "middle",
    ...fadeIn(0.5)
  });

  // 致谢内容
  slide.addText("感谢各位评审老师的耐心指导与宝贵意见", {
    x: 0.5, y: 3.0, w: 9, h: 0.6,
    fontSize: 18, color: C.ice, fontFace: "Microsoft YaHei",
    align: "center", valign: "middle",
    ...fadeIn(0.8)
  });

  slide.addText("感谢导师的悉心指导与建议", {
    x: 0.5, y: 3.6, w: 9, h: 0.6,
    fontSize: 16, color: C.ice, fontFace: "Microsoft YaHei",
    align: "center", valign: "middle",
    ...fadeIn(1.0)
  });

  slide.addText("感谢同学们的帮助与支持", {
    x: 0.5, y: 4.2, w: 9, h: 0.6,
    fontSize: 16, color: C.ice, fontFace: "Microsoft YaHei",
    align: "center", valign: "middle",
    ...fadeIn(1.2)
  });

  // 底部装饰线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 3, y: 5.2, w: 4, h: 0.04,
    fill: { color: C.accent },
    ...wipeIn("left", 1.5)
  });

  addFooter(slide, 17, 17);

  slide.addNotes(`【致谢 — 约10秒】
- 感谢各位评审老师
- 感谢导师指导
- 感谢同学帮助

【结束语】"谢谢大家！"`);
}

// ============================================================
// 生成文件
// ============================================================
pres.writeFile({ fileName: "E:\\rumor_detection\\中期汇报_v7.pptx" })
  .then(() => console.log("PPT 生成成功！"))
  .catch(err => console.error("生成失败:", err));
