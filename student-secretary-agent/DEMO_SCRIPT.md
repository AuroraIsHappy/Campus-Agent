最终我们需要完成三个典型长程任务的demo

## 当前可演示入口（本地 5 分钟）

```powershell
cd C:\Users\Lenovo\Desktop\your_secretary\student-secretary-agent
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1
```

打开 `http://127.0.0.1:5173`：

- 仪表盘：看 LLM、skills、Notion、最近运行状态。
- Demo 中心：选择 `offline`，运行 Demo A 和 Demo C；选择 `real` 时，如果 Hermes/LLM 未就绪，会显示缺什么。
- 科研笔记：添加主题，刷新 digest，查看论文卡片和 `note_path`，同步本地 Markdown 镜像。

服务启动后验收：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_demo.ps1
```

A. “根据微信里别人发来的策划案格式，自动写社会实践策划案 + 找外联对象 + 写邮件”

可能的流程：

用户把微信内容转发给 agent（上传文字要求/ 截图 / 文档）。
Agent 提取策划案格式、栏目、语气、活动约束。
Research 子智能体检索目标地区、实践主题、政策背景、历史项目、机构名单。并根据机构间位置关系安排合理日期。
Source Verifier 子智能体验证目标参访地、外联对象是否真实、联系方式是否来自可靠页面。
Writer 子智能体生成策划案。
Reviewer 子智能体检查格式是否贴合原策划案、是否有虚构事实、是否有预算 / 时间 / 安全预案缺失。
Email 子智能体生成外联邮件。
用户确认后再发送邮件或加入日历。


B. “学习指定电脑路径下所有讲义 + 搜 GitHub / 网站资源 + 生成期末复习计划”

可能的流程：

用户指定路径：~/Courses/LinearAlgebra/lectures（或自然语言描述“我桌面上的...”）或已经绑定好自己学校网络学堂的url
Agent 自动扫描 PDF / PPT / Markdown / DOCX。
生成课程知识图谱：章节、概念、公式、题型、重点。
自动搜索用户之前指定过的资源路径/ GitHub / 课程主页 / 公开题库 / 往年 syllabus。
判断资源可靠性：是否来自大学课程、是否年份较新、是否和讲义主题匹配。
读取用户日历，找空闲时间。
生成复习计划：每天内容、练习题、错题回顾、quiz。
每晚定时生成当天 quiz。
第二天根据答题情况调整计划。

C. “用户说想学 Linux，Agent 自动搜知乎 / 小红书高赞答案，发现 MIT Missing Semester，安排 30 天碎片时间学习计划”

可能的流程：

先搜索公开 Web、GitHub、MIT OCW、课程主页、YouTube / Bilibili 等可访问资源。
如果用户授权浏览器登录知乎 / 小红书，可以通过浏览器自动化辅助查看，但不要承诺稳定抓取。
让 Source Ranker 判断哪些资源更适合用户。
如果发现 MIT Missing Semester 更适合，就解释理由：课程短、主题覆盖 shell、git、vim、debugging、profiling、security，适合 CS 学生补基础。
读取用户日历，安排 30 天每天晚上 20 分钟。
每天生成任务和 quiz。

这里的产品亮点是：用户随口说一个模糊学习目标，Agent 能自动澄清目标、找高质量资源、压缩成可执行计划，并持续跟进。
