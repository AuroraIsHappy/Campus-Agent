# Campus-Agent 实现路径

> 配套：[ACHITECHURE.md](./ACHITECHURE.md)（架构） · [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md)（验收）。本文给出从 0 到三个 Demo 全跑通的**分阶段路线图**。
> 假设已采纳架构 §8 的推荐：Hermes 依赖+插件（不 fork）、Demo 顺序 C→A→B、前端定制 Hermes 皮肤。

## 0. 实现策略总览

- **复用纪律**：每个能力先问"Hermes/CLI-Anything 有没有"，再决定写。Campus 层只写差异化部分。
- **测试纪律**（对齐 CLI-Anything）：每个子系统有 `test_core.py`（单元）+ `test_full_e2e.py`（真跑），不优雅跳过。子系统覆盖率 ≥80%。
- **任务即文件夹**：开发本身也用 Odyssey 约定——每个 Phase 一个 `devplan/phase-N/` 目录，含 Plan/Status/Verification。
- **模型路由（用户可配，不绑厂商）**：onboarding 采集用户已有 provider key（GLM/DeepSeek/Qwen/OpenAI/Anthropic/本地），生成**角色→模型**映射；默认重推理角色配强模型、子 agent 配便宜模型，纯为控成本，不强求某家。
- **分支策略**：`main` 受护；每 Phase 一个 `phase/N-xxx` 分支，子系统合并前过 code-reviewer + python-reviewer。

---

## Phase 0 — 地基与验证 spike（~1 周）

**目标**：跑通 Hermes，证明三层可拼装；敲定 §8 的 3 个决策；落最终架构。

**任务清单**：
- [ ] 本地跑起 Hermes（`hermes setup` → CLI/TUI 可对话），接入一个模型 provider。
- [ ] `pip install cli-anything-hub`，装一个 harness（如 `cli-anything-libreoffice` 或 `exa`），从 Hermes 工具层 subprocess 调通 `--json`。
- [ ] 阅读 `openhands-sdk` 的 `Event` / `AgentController` / event-store 抽象（**只读思路**），确定 Odyssey 状态机/恢复的最小实现方式。
- [ ] 写一个最小 Hermes skill + 委派，验证「主 agent 起 1 个子 agent 并拿回结果」——这是 Odyssey 的底层原语。
- [ ] 验证 Hermes gateway 主渠道收发：**QQ Bot**（q.qq.com 注册 AppID/Secret，官方 API、群@可用）；再验一个二级渠道（**飞书** 或 企微 WeCom）；个人微信（iLink）仅验私聊。
- [ ] 采集/配置用户模型 provider key（至少一家非 Anthropic，如 GLM/DeepSeek），验证 Hermes provider 抽象可按角色指派模型。
- [ ] 决策敲定：fork 边界、Demo 顺序、前端策略；更新 ACHITECHURE.md §8。

**退出标准（Exit）**：
- Hermes 本地可对话；1 个 CLI-Anything 工具被 agent 成功调用并解析 JSON。
- 一份 `<repo>/devplan/phase-0/Verification.md` 记录三个 spike 的证据截图/日志。
- §8 三项决策确认签字。

**里程碑 M0**：内核+工具带+委派原语三件套可用。

---

## Phase 1 — MVP：Demo C 端到端（~2 周）

**目标**：用**vanilla Hermes + 少量 skill**（暂不上 Odyssey）把 Demo C 跑通，验证「模糊目标→找资源→排期→每日 quiz」主链路。

> Demo C：用户说想学 Linux → Agent 搜公开资源 → 发现 MIT Missing Semester → 安排 30 天碎片时间计划 + 每日 quiz。

**任务清单**：
- [ ] Researcher skill：调 `exa` CLI / browser 搜公开 web、GitHub、MIT OCW；产出候选资源列表（JSON）。
- [ ] SourceRanker skill：按适合度/年份/权威性打分，输出推荐 + 理由（解释为何选 MIT Missing Semester）。
- [ ] Scheduler skill：读日历空闲，生成 30 天每晚 20 分钟计划（Markdown）。
- [ ] 每日 quiz：用 Hermes `cron` 每晚触发，基于当天内容生成 quiz 并推送（gateway）。
- [ ] 答题反馈：次日根据答题调整计划（简单版：错题加重，对题跳级）。
- [ ] 记忆：把"用户在学 Linux"写入长期偏好；计划进度写任务日志。

**退出标准**：
- 一句"我想学 Linux"端到端产出可执行 30 天计划 + 第一天 quiz 实际推送。
- 见 [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md) §Demo C 全部通过。

**里程碑 M1**：第一个可演示Demo；内核链路被真实任务验证。

---

## Phase 1.5 — 生活基础（让产品像真秘书，近乎免费；~1 周）

**目标**：复用已验证的 Kanban + cron + 记忆，铺高频低门槛功能。

**任务清单**：
- [ ] **日程管理**：Kanban 看板（Hermes 已有 kanban 工具）+ 飞书/ICS 日历读写 + cron 提醒。
- [ ] **生日/纪念日提醒**：onboarding 采集 + 记忆，cron 双触发（提前 1 天 + 当天）。
- [ ] **每日秘书日志**：每晚 cron 汇总当天 + 明日待办，推 QQ/飞书。

**退出标准**：三项各跑通；生日提醒双触发实测。

**里程碑 M1.5**：产品有日常高频触点。

---

## Phase 2 — Odyssey 编排器 + Supervisor + 角色（~2 周，原 3 周；引擎已存在省一半）

**目标**：在 Hermes Kanban 上写薄编排器 + Supervisor + 注册角色 profile。**引擎（状态机/恢复/DAG/交接）已由 Kanban 提供，不自研**。

**任务清单**：
- [ ] `campus/odyssey/orchestrator.py`：`create_task(assignee, parents, goal_mode=True)` 建任务 + `dispatch_once(spawn_fn)` 驱动；`spawn_fn` 把 task 行翻译成"起一个绑 profile 的 agent 跑 goal"。
- [ ] **Phase 0 spike 验过的 Kanban roundtrip 落成正式代码**（含 kill→resume）。
- [ ] 角色 profile 全量注册（`campus/profiles/*.yaml`）：Planner / Critic / Researcher / SourceVerifier / SourceRanker / Writer / Reviewer / Scheduler / MetaAgent，各自 system prompt + toolset + model。
- [ ] 对抗对用 `parents` 串：Planner↔Critic（开工前）、Writer↔Reviewer（收工前），`metadata.verdict` 决定回环/放行。
- [ ] `campus/odyssey/supervisor.py`：轮次上限、死锁/空转打断（升级 `awaiting_human`）、对话协议（强制 `kanban_complete(summary, metadata)`）、成本闸。

**退出标准**：
- 一个空壳多角色任务跑完、被 kill 后 resume、闸门轮次上限/死锁打断生效。
- 单测覆盖 supervisor 路径 ≥80%。

**里程碑 M2**：编排器 + Supervisor 可用。

---

## Phase 3 — Demo A：策划案 + 外联对象 + 邮件草稿（~2.5 周）

**目标**：用 Phase 2 的编排器 + 角色 + Supervisor 跑通 Demo A（冲击力最强）。

> Demo A：根据样本策划案格式 → 写社会实践策划案 + 找外联对象 + **生成邮件草稿纯文本（不发送，B1）**。

**任务清单**：
- [ ] 样本抽取：从用户样本（截图/文档）抽栏目与语气（视觉模型槽位；无视觉模型则只吃文字/文档）。
- [ ] Researcher（Exa/browser/GitHub）+ SourceVerifier 验证参访地/外联对象/联系方式真实性。
- [ ] Writer（`cli-anything-libreoffice` / python-pptx）生成策划案 + PPT + 预算表。
- [ ] Reviewer 收工闸门：格式贴合 + 无虚构事实 + 预算/时间/安全预案齐全（不过回 Writer）。
- [ ] Email 角色**生成复制粘贴文本**（不接入邮箱，B1）。
- [ ] human-in-the-loop：`awaiting_human` 确认后才标 delivered。

**退出标准**：见 [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md) §Demo A 全绿。

**里程碑 M3**：长程高利害任务交付可靠。

---

## Phase 4 — 增强记忆 + Meta-Agent（~3 周）

**目标**：把"好用"升级为"专属秘书"——记忆个性化 + 非 CS 用户 5 分钟上手。

**任务清单（记忆 L4）**：
- [ ] 多层记忆 schema：长期偏好 / 任务日志 / 任务看板 / 知识库 / 每日秘书日志，落到 Hermes memory。
- [ ] 向量检索：在 Hermes FTS5 之上加 embedding + 向量库（或切 Honcho/mem0 backend），双通道召回。
- [ ] Ebbinghaus 复习引擎：学习任务的复习节点写 cron，按曲线触发 quiz（反哺 Demo B/C）。
- [ ] 压缩/遗忘 cron（借 Claude dreams）：老 EventLog 摘要 → 沉淀长期偏好/知识；用户可设保留窗口。

**任务清单（Meta-Agent L5）**：
- [ ] onboarding 向导：自然语言采集身份/专业/偏好，自动推荐并装 skill（调 `cli-hub`）。
- [ ] **模型路由配置**：onboarding 询问已有 provider key，生成 `~/.campus/routing.yaml`（角色→{provider,model}），运行期按角色取模型，UI 可改、不绑厂商。
- [ ] skill 发现：用户模糊需求 → 检索可用 skill → 评估可靠性 → 选模式 → 映射到 Odyssey DAG。
- [ ] 零配置包：内置 100+ skill（Hermes skills + CLI-Anything skills + 校园 skill pack），开箱可用。
- [ ] 人格选择（L6）：onboarding 选费曼/鲁迅/自定义，写入长期偏好。

**退出标准**：
- 跨 session 记忆召回：新 session 能记得用户专业/在学课程/机构库。
- 一位非 CS 测试用户 5 分钟内完成 onboarding 并跑通一个 Demo。

**里程碑 M4**：个性化 + 低门槛上手。

---

## Phase 5 — Demo B + 前端 + 打磨（~3 周）

**目标**：拿下最重的 Demo B；前端换皮 + 移动链路；性能与成本打磨。

> Demo B：扫描指定路径讲义 → 知识图谱 → 搜资源 → 期末复习计划 + 每日 quiz。

**任务清单**：
- [ ] 本地文件扫描：PDF/PPT/Markdown/DOCX → 文本抽取（CLI-Anything 或现有库）。
- [ ] 知识图谱生成：章节/概念/公式/题型/重点，结构化存知识库。
- [ ] 资源检索 + 可靠性判断：搜 GitHub/课程主页/公开题库/往年 syllabus，SourceRanker 过滤。
- [ ] 复习计划 + Ebbinghaus quiz：Scheduler 读日历，生成每天内容/练习/错题/quiz，cron 每晚出题，次日调整。
- [ ] 前端：定制 Hermes Electron 皮肤 + 新手引导 + 人格面板 + 任务看板（换皮，不重写）。
- [ ] 移动链路：**QQ Bot**（主）+ **飞书 / 企微 WeCom**（二级）全通（官方 API、群可用）；个人微信（iLink）仅私聊转发+提醒；群场景走 QQ/飞书/企微群 @机器人。
- [ ] 成本打磨：模型路由落地（Haiku/Sonnet/Opus 分流），长文本压缩。
- [ ] 文档：README 上手指南、skill 目录、配置说明。

**退出标准**：
- Demo B 端到端跑通；三个 Demo 全绿（见 [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md)）。
- 非 CS 用户 5 分钟上手、跨 session 记忆稳定、移动推送可达。

**里程碑 M5（发布候选）**：三 Demo + 个性化 + 美观前端 + 移动。

---

## Phase 8 — 上线冲刺（可分发的开源自托管）

**目标**：从 Phase 7 的本地产品闭环升级到「clone 即可跑」的交付级。智能化补全 + 真实集成打通 + 可分发包。

**完成项**：

| Step | 内容 |
|---|---|
| 0 | Phase 7 收尾：Ebbinghaus 曲线 + daily-tick quiz + export_status + interview practice/reflect |
| 1 | Multi-agent 接线：MetaRunner 桥（classify→DAG→Orchestrator+Supervisor），/agent/run real+long 走多智能体 |
| 2 | Memory 分层检索：RRF 融合 + 分层策略 + token 预算 + recency decay + nightly compress；接入生成路径 |
| 3 | 真实 LLM 端到端：五域 workflow_llm prompt + mode 透传 + integration 测试（真实 GLM 验证） |
| 4 | Auto-learn：correction 捕获 + CorrectionStore + SkillCreator + AutoLearner（LLM 分类偏好/skill/事实） |
| 5 | 移动端真实推送：QQ Bot 官方 API（auth 验证通过）+ 飞书健康自检 |
| 6 | Notion + 搜索 provider：Notion 双向 + GitHub API（真实仓库验证）+ Tavily |
| 7 | 可分发包：Dockerfile（hermes clone+build）+ docker-compose + .env.example + CI + 生产前端 |
| 8 | 真实任务验收 + 发布：全域真实任务通过，S-* 核验，tag v0.8.0 |
| 9 | Agent 名称设置 + 前端美化：分层导航 + 动态名称 + 设置页增强 |

**关键发现**：`hermes-agent` 不在 PyPI，官方安装方式是 `git clone` + `uv pip install .`（本地构建）。Dockerfile 照此构建。

**里程碑 M8（上线）**：可分发的开源自托管 + 真实集成 + 智能化补全。

---

## 开发方式：agent + git worktree 并行 vibe-code（A2）

- **每 Phase / Demo 一个 worktree**（`git worktree add` 或 `EnterWorktree`），互不干扰、可并行。
- **本计划可被 plan-orchestrate 消费**：各 Phase 任务清单已是 step 粒度，可对某 Phase 跑 `/ecc:plan-orchestrate` 生成 `/orchestrate custom` 提示词，由 agent 链（tdd-guide + python-reviewer + …）执行。
- **吃自己狗粮**：长程开发任务也走 Kanban 任务工作区（Plan/Status/Verification）。
- **并行示例**：Phase 4c（Demo B / 网络学堂模板）与 Phase 3（Demo A）分两个 worktree 并行。

## C4：Hermes churn 缓解（推荐 ①+②+③）

| 方案 | 做法 | 推荐度 |
|---|---|---|
| **① 锁版本 + 关自更新** | `uv pip install hermes-agent==<pin>`，禁用 self-updater | ⭐⭐⭐ 主方案 |
| **② 接口抽象（ports）** | Campus 代码只依赖 `campus/runtime/*` 薄接口，不直接 import Hermes 内部 | ⭐⭐⭐ 配合 |
| **③ 跟 tag 不跟 main** | 只在 Hermes release/tag 时评估升级 | ⭐⭐⭐ 配合 |
| ④ vendor 锁 commit（submodule） | PyPI 不够时，`hermes-agent/` 作 submodule 钉 tag | ⭐⭐ 备选 |
| ⑤ fork + tag rebase | 仅当必须改核心 | ⭐ 应急 |

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| Hermes god-file（cli.py 760KB）变更伤及依赖 | 中 | 最小 fork 边界；只依赖公开 skill/plugin/delegate API；锁定 Hermes 版本，按节奏升 |
| OpenHands 上游迁移 | 中 | 只借思路，不依赖仓库；关注 `openhands-sdk` 版本 |
| 中文工具（知乎/小红书/网络学堂）无 API、抓取脆弱 | 高 | CLI-Anything 封装 + 浏览器自动化；**对外不承诺稳定抓取** |
| 长程任务 LLM 成本失控 | 中 | 模型路由 + 压缩 + checkpoint 复用缓存 |
| 幻觉（虚构机构/联系人/资源） | 高（信誉） | SourceVerifier + Reviewer 双闸门强制可靠来源 |
| 个人微信（iLink）群消息不可用 | 高 | 主走官方 API 渠道：**QQ Bot / 企微 WeCom**（群可用）；微信仅私聊；iLink 群限制是 Hermes 文档明示 |
| QQ Bot 沙箱→上线 / 群须 @ | 中 | 早期 sandbox 测试；上线走 q.qq.com 审核；群交互统一 @机器人 |
| 多 agent 调度死锁/回环 | 中 | DAG 拓扑校验 + 对抗辩论最大轮次上限 |

---

## 开发规范（摘）

- 每个 Phase 一分支：`phase/N-name`；合并前过 `python-reviewer` + `code-reviewer`。
- 子系统目录结构对齐 [ACHITECHURE.md §6](./ACHITECHURE.md)。
- 测试：`tests/<subsystem>/{test_core.py,test_full_e2e.py}`，对齐 CLI-Anything 风格；CI 跑 lint+unit+e2e。
- 决策变更写 ADR（`docs/adr/`），避免口头漂移。
