# 谣言检测数据集资源汇总

## 1. Weibo微博谣言数据集

### Weibo-2016
- **名称**：Weibo-2016 谣言数据集
- **来源**：清华大学 THUNLP 实验室
- **下载链接**：https://github.com/thunlp/Chinese-Rumor-Dataset
- **获取方式**：GitHub 直接下载
- **数据规模**：
  - 谣言：约 2,300 条
  - 真相：约 2,350 条
- **字段说明**：
  - `content`：微博内容
  - `label`：标签（0=真相，1=谣言）
  - `comments`：评论列表
  - `reposts`：转发列表

### Weibo-2018
- **名称**：Weibo-2018 谣言数据集
- **来源**：相关学术研究（NAACL 2018 论文）
- **下载链接**：https://www.dropbox.com/s/7ewzdrbelpmrnxu/rumor_data.zip
- **获取方式**：Dropbox 直接下载（部分镜像站也有备份）
- **数据规模**：
  - 涵盖 2012-2016 年微博数据
  - 谣言：约 4,488 条
  - 真相：约 4,488 条
- **字段说明**：
  - `text`：微博文本
  - `label`：标签（0=真相，1=谣言）
  - `user_id`：发布用户 ID
  - `time`：发布时间
  - `comments`：评论信息
  - `reposts`：转发信息

---

## 2. Twitter数据集（PHEME）
- **名称**：PHEME 谣言数据集
- **来源**：PHEME 项目（欧盟 FP7 资助）
- **下载链接**：https://figshare.com/articles/dataset/PHEME_dataset_of_rumours_and_non-rumours/4010619
- **获取方式**：Figshare 平台直接下载
- **数据规模**：
  - 涵盖 9 个突发事件（如 Charlie Hebdo 枪击案、德国之翼空难等）
  - 谣言推文：约 5,802 条
  - 非谣言推文：约 4,043 条
- **字段说明**：
  - `text`：推文内容
  - `label`：标签（rumour/non-rumour）
  - `user`：用户信息
  - `created_at`：发布时间
  - `thread_structure`：对话线程结构信息
  - `reactions`：其他用户反应

---

## 3. 其他相关数据集

### 中文谣言检测相关数据集
- **今日头条谣言数据集**
  - 名称：今日头条谣言/真相数据集
  - 来源：天池开放平台（部分竞赛提供）
  - 获取方式：需手动申请或参加相关竞赛获取
  - 数据规模：约 10 万条

- **知乎谣言数据集**
  - 名称：知乎谣言检测数据集
  - 来源：GitHub 开源项目（部分研究者整理）
  - 下载链接：https://github.com/HelloJocelynLu/Chinese_Rumor_Dataset
  - 获取方式：GitHub 直接下载
  - 数据规模：约 3 万条

### 假新闻检测数据集
- **FakeNewsNet**
  - 名称：FakeNewsNet 假新闻数据集
  - 来源：加州大学洛杉矶分校（UCLA）
  - 下载链接：https://github.com/KaiDMML/FakeNewsNet
  - 获取方式：GitHub 直接下载（需配合 API 获取完整内容）
  - 数据规模：包含政治和娱乐类假新闻及真相，约 2 万条

- **LIAR**
  - 名称：LIAR 假新闻检测数据集
  - 来源：加州大学圣塔芭芭拉分校（UCSB）
  - 下载链接**：https://www.cs.ucsb.edu/~william/data/liar_dataset.zip
  - 获取方式**：直接下载
  - 数据规模**：约 12,800 条带可信度评级的声明

---

## 说明
- **直接下载**：标注有 GitHub/Figshare/Dropbox 链接的数据集可直接下载
- **手动获取**：部分竞赛或平台提供的数据集需要手动申请或参与竞赛获取
