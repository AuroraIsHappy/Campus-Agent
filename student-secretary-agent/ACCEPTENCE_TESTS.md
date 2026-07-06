# Campus-Agent 验收标准

> 配套：[ACHITECHURE.md](./ACHITECHURE.md) · [IMPLEMENT.md](./IMPLEMENT.md)
> 命名沿用现有文件名 `ACCEPTENCE_TESTS.md`（原文拼写）。本文定义每个 Demo 与系统质量的**可验证**验收项。

## 0. 验收原则

每条验收必须**可验证**（能跑出 pass/fail），分三类：
- **功能验收（F）**：行为发生了。
- **质量验收（Q）**：交付物达到质量门槛（核心：无幻觉、格式贴合、来源可靠）。
- **系统验收（S）**：非功能（上手、恢复、记忆、移动、人格、成本）。

自动化策略（对齐 CLI-Anything）：
- 角色 agent / 引擎逻辑 → `tests/<sub>/test_core.py`（单元，mock LLM）。
- 端到端 Demo → `tests/<demo>/test_full_e2e.py`（真跑，不优雅跳过；断言产物结构 + 质量门槛）。
- 质量门槛中"无幻觉/格式贴合"用 LLM-as-judge（Opus）+ 规则双校验，judge prompt 固化在测试里。

---

## 1. Demo A — 社会实践策划案 + 外联对象 + 邮件

**输入**：用户转发一份微信策划案样本（文字/截图/文档）+ 简述（主题、地区、时间窗）。

| ID | 类型 | 验收项 | 验证方式 |
|---|---|---|---|
| A-F1 | 功能 | 生成策划案文档（LibreOffice/PDF） | 产物存在 + 可打开 |
| A-F2 | 功能 | 产出 ≥3 个外联对象候选，每个含名称、参访理由、联系方式来源 | JSON 字段齐全 |
| A-F3 | 功能 | 生成外联邮件**复制粘贴文本**（每对象 1 段，不接入邮箱，B1） | 文本段数 == 对象数；无自动发送 |
| A-F4 | 功能 | 全程不自动发送；进入 `awaiting_human` 等确认 | 状态机断言 |
| A-Q1 | 质量 | 策划案**格式贴合样本**（栏目、语气、结构） | LLM-judge 相似度 ≥ 阈值 + 栏目覆盖率 |
| A-Q2 | 质量 | **无虚构事实**：所有机构/地点/政策/联系人可溯源到真实网页 | SourceVerifier 证据链接可达（HTTP 200 + 语义匹配） |
| A-Q3 | 质量 | 策划案含预算、时间表、安全预案三段 | 规则正则 + judge |
| A-Q4 | 质量 | 日期安排符合地理关系（不出现一天跨两远地） | 规则校验 |
| A-Q5 | 质量 | Planner↔Critic、Writer↔Reviewer 辩论记录落 `Verification.md` | 文件存在 + 含双方主张 |

---

## 2. Demo B — 讲义复习计划 + 每日 quiz

**输入**：用户指定路径（`~/Courses/.../lectures`）或绑定学校网络学堂 URL + 考试日期。

| ID | 类型 | 验收项 | 验证方式 |
|---|---|---|---|
| B-F1 | 功能 | 扫描 PDF/PPT/MD/DOCX 并抽取文本 | 抽取率 ≥ 阈值 / 文件数 |
| B-F2 | 功能 | 生成知识图谱（章节/概念/公式/题型/重点） | 结构化 JSON 校验 |
| B-F3 | 功能 | 检索外部资源（GitHub/课程主页/题库/syllabus） | 候选数 ≥ N |
| B-F4 | 功能 | 读日历空闲，生成期末复习计划（每天内容+练习+错题+quiz） | 计划覆盖到考试日 |
| B-F5 | 功能 | cron 每晚出 quiz 并推送 | 触发记录 + 推送送达 |
| B-F6 | 功能 | 次日按答题情况调整计划 | 计划 diff 非空且方向正确 |
| B-Q1 | 质量 | 资源可靠性过滤生效（年份、是否大学课程、主题匹配） | SourceRanker 打分可解释 |
| B-Q2 | 质量 | quiz 题目与当天内容相关、答案正确 | judge 抽检 ≥ 阈值 |
| B-Q3 | 质量 | 计划量与可用时间匹配（不超排） | 总时长 ≤ 空闲时长 |

---

## 3. Demo C — 模糊学习目标 → 高质量计划

**输入**：一句"我想学 Linux"。

| ID | 类型 | 验收项 | 验证方式 |
|---|---|---|---|
| C-F1 | 功能 | 自动澄清目标（必要时 1–2 轮提问） | 对话记录 |
| C-F2 | 功能 | 搜索公开资源并给出推荐（如 MIT Missing Semester） | 候选列表 + 推荐项 |
| C-F3 | 功能 | 给出推荐理由（课程短、覆盖 shell/git/vim/…） | judge 命中要点 |
| C-F4 | 功能 | 生成 30 天碎片时间计划（每晚 ~20min） | 计划天数 + 时长 |
| C-F5 | 功能 | 每天生成任务 + quiz | cron 触发记录 |
| C-Q1 | 质量 | 资源来自权威源（大学课程/官方文档） | SourceRanker 证据 |
| C-Q2 | 质量 | 计划可执行、难度递进 | judge |

---

## 4. 系统质量验收（S）

| ID | 验收项 | 阈值 / 验证 |
|---|---|---|
| S-ONBOARD | 非 CS 用户 5 分钟完成上手并跑通 1 个 Demo | 真人测试计时 ≤ 5min |
| S-RESUME | 长程任务被 kill 后重启可从最近 checkpoint 恢复 | kill 测试 + 状态续跑 |
| S-MEMORY | 跨 session 记忆召回（专业/课程/机构库） | 新 session 问答命中 |
| S-MOBILE | 移动渠道可收需求 + 推提醒 | **QQ Bot**（主）+ 飞书/WeCom（二级，至少一个）收发集成测试通过（官方 API、群可用） |
| S-PERSONA | 人格风格一致（费曼/鲁迅示例回答风格匹配） | judge 风格分 ≥ 阈值 |
| S-COST | 单个长程 Demo 成本可控 | 角色分档路由生效；成本账单 ≤ 预算 |
| S-MODELCONFIG | 用户可自定义角色→模型路由，且至少一家**非 Anthropic** provider 可跑通 | `routing.yaml` 可编辑 + 用 GLM/DeepSeek/Qwen 等跑通一个 Demo |
| S-NOHALLU | 事实类输出零幻觉（强源头） | 全 Demo 的 Q2 类项全绿 |
| S-SUPERVISOR | Supervisor 死锁打断 + 轮次上限 + 对话协议生效 | 构造空转辩论 → 被打断升级 `awaiting_human`；轮次超限强制放行 |
| S-SECURITY | 无硬编码密钥；secret 走环境变量/secret manager | 安全扫描通过 |

---

## 5. 自动化测试映射

| 层 | 测试文件 | 内容 |
|---|---|---|
| L2 Odyssey | `tests/odyssey/test_core.py` | Kanban roundtrip、kill→resume、spawn_fn 接缝 |
| L2 Supervisor | `tests/odyssey/test_supervisor.py` | 轮次上限、死锁打断、对话协议、成本闸 |
| L3 Orchestration | `tests/orchestrator/test_core.py` | DAG 拓扑校验、对抗闸门轮次上限 |
| L4 Memory | `tests/memory/test_core.py` | 多层 schema、向量+FTS5 召回、Ebbinghaus 节点 |
| L5 Meta-Agent | `tests/meta_agent/test_core.py` | skill 发现、可靠性评分、onboarding 流程 |
| Demo A | `tests/demo_a/test_full_e2e.py` | A-F* + A-Q* 全绿 |
| Demo B | `tests/demo_b/test_full_e2e.py` | B-F* + B-Q* 全绿 |
| Demo C | `tests/demo_c/test_full_e2e.py` | C-F* + C-Q* 全绿 |
| 系统 | `tests/system/` | S-* 集成测试 |

**发布门槛（M5）**：三个 Demo 的 e2e 全绿 + S-* 全绿 + 子系统单测覆盖率 ≥80%。
