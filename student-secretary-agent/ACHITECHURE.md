# Campus-Agent 产品架构

> 配套文档：[GOAL.md](./GOAL.md) · [REUSE_MAP.md](./REUSE_MAP.md) · [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) · [IMPLEMENT.md](./IMPLEMENT.md) · [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md)

## 0. TL;DR（一句话架构）

**Hermes 当内核（锁版本），CLI-Anything 当工具带，长程任务直接复用 Hermes 内置 Kanban（重大发现，省掉最重的自研），Claude "dreams" 当记忆压缩范式**。Campus 层 = **Odyssey（Kanban 薄封装 + Supervisor 对抗闸门）** + **增强记忆** + **Meta-Agent** + **人格层** + **定制前端**。

---

## 1. 设计原则

1. **复用优先，自研聚焦**：能用 Hermes/CLI-Anything 解决的，绝不重写。自研只投向三处——长程任务质量、非 CS 用户上手、记忆个性化。
2. **薄封装 + 插件化，最小化 fork**：优先以 *Hermes 插件 / skill / 依赖* 形式集成，**不 fork Hermes 内核**。仅当确需改变 agent 主循环行为时，才在最小边界内 vendor 单个模块（参见 §8 待确认决策）。
3. **任务即文件夹**（borrow SWE-harness）：每个长程任务一个工作区，强制 `Plan.md / Status.md / Verification.md / DecisionLog.md / Artifacts/`，可中断、可恢复、可审计。
4. **对抗式质量闸门**（GAN-style）：开工前 Planner↔Critic 辩论计划，收工前 Writer↔Reviewer 辩论交付物；事实类任务必须经 SourceVerifier，禁止幻觉。
5. **AI-native 但人始终在环**：对外发送（邮件、消息、日历）一律 human-in-the-loop 确认后才执行。
6. **模型路由用户可配、控成本**：**不绑定任何厂商**。用户自带 provider key（OpenAI / Anthropic / GLM 智谱 / DeepSeek / Qwen 通义 / 本地模型 …），在路由配置里把**角色→模型**映射好，由 Hermes 的 provider 抽象落地。默认按角色分档（重推理配强模型、子 agent 配便宜模型）只为控成本，**绝不强制某家**——中国用户全程走 GLM/DeepSeek/Qwen 完全可行。

---

## 2. 复用决策总览（Reuse Map）

| 能力域 | 来源 | 复用方式 | 我们要做的 |
|---|---|---|---|
| Agent 主循环 / 工具调用 / MCP / 委派 / cron / skills | **Hermes** | 依赖 + 插件 | 几乎不动，仅写 Campus 插件 |
| 多渠道消息入口（微信/企微/飞书/钉钉/Telegram/邮件…） | **Hermes gateway** | 直接用 | 选型 + 配置 + 校园场景适配 |
| 桌面 GUI / Web Dashboard / TUI | **Hermes apps/web/ui-tui** | 定制皮肤 | 重做视觉、新手引导、人格配置 |
| 结构化记忆存储 + 检索（FTS5） | **Hermes memory** + 8 backend | 依赖 | 加多层结构 + 向量检索 + Ebbinghaus |
| 主动压缩 / 总结 / 遗忘 | **Claude "dreams"** 范式 | 借思路实现 | 写压缩/遗忘 cron job |
| 长程任务状态保持与恢复（event-stream / 任务工作区 / 恢复） | **OpenHands**（openhands-sdk 思路） | 借架构，**不依赖其仓库** | 自研 Odyssey 引擎 |
| 长程任务多智能体编排（含非 SWE 改进） | OpenHands 思路 + 自研 | 借 + 自研 | 角色 agent + DAG + 对抗对 |
| GUI 软件工具化（PPT/文档填写/PDF/笔记/参考文献…） | **CLI-Anything** | pip 依赖 `cli-anything-hub` | 直接用 60+ 已有 harness |
| 新工具封装（微信/网络学堂/知乎/小红书等校园/中文工具） | CLI-Anything 7 阶段 SOP | 用其生成器 | 按需封装，不承诺稳定抓取 |
| Meta-Agent（找 skills / 验证 / 编排 / 免配置） | 自研 | — | 全新，对标 GOAL 的"像注册微信" |

> ⚠️ **关于 OpenHands**：其仓库正在迁移，agent 核心已抽到 `openhands-sdk` PyPI 包，仓内 `Plan/Status/Verification` 代码标注为 "LEGACY V0，2026-04 移除"。**因此我们只借鉴其事件流/任务工作区/沙箱架构思想，绝不 fork 或硬依赖该仓库**，避免追一个移动靶。

---

## 3. 分层架构

```
┌──────────────────────────────────────────────────────────────────┐
│  L7 Interface  │  桌面 GUI(Electron 定制) · 移动聊天(gateway) · Web │
├──────────────────────────────────────────────────────────────────┤
│  L6 Persona     │  费曼 / 鲁迅 / 用户自定义 —— 风格与语气层          │
├──────────────────────────────────────────────────────────────────┤
│  L5 Meta-Agent  │  上手引导 · skill 发现 · 自动配置 · 模式选择       │
├──────────────────────────────────────────────────────────────────┤
│  L4 Memory      │  多层结构化记忆 · 检索 · Ebbinghaus · 压缩/遗忘   │
├──────────────────────────────────────────────────────────────────┤
│  L3 Orchestration │ 角色 agent · 工作流 DAG · 对抗对(Planner↔Critic)│
├──────────────────────────────────────────────────────────────────┤
│  L2 Odyssey 任务引擎 │ 任务工作区 · 状态机 · checkpoint · 恢复 · 闸门│
├──────────────────────────────────────────────────────────────────┤
│  L1 Tool Belt   │  CLI-Anything(cli-hub) + 校园/中文工具封装        │
├──────────────────────────────────────────────────────────────────┤
│  L0 Runtime Kernel │  Hermes Agent(主循环/工具/MCP/委派/cron/gateway)│
└──────────────────────────────────────────────────────────────────┘
```

| 层 | 职责 | 来源 | 构建/复用 |
|---|---|---|---|
| L0 Kernel | agent 主循环、工具调用、MCP、子智能体委派、cron、消息网关、session 搜索 | Hermes | 依赖，不动 |
| L1 Tool Belt | 把 GUI 软件变成 `--json` CLI；web 搜索、笔记、文献、办公、PPT | CLI-Anything + 自封 | pip 依赖 + 按需封装 |
| L2 Odyssey | 长程任务的工作区/状态/恢复/对抗闸门 | 自研（借 OpenHands） | **核心自研** |
| L3 Orchestration | 角色 agent 分工、DAG、对抗辩论、源可靠性验证 | 自研（借 OpenHands） | **核心自研** |
| L4 Memory | 多层记忆、检索、遗忘曲线复习、压缩/遗忘 | Hermes + Claude dreams | 增强 |
| L5 Meta-Agent | 免配置上手、skill 发现与可靠性验证、工作流编排 | 自研 | **核心自研** |
| L6 Persona | 回复人格 | 自研 | 新建 |
| L7 Interface | 桌面/移动/Web | Hermes 前端 | 定制皮肤 + 引导 |

---

## 4. 核心子系统详解

### 4.1 Odyssey 长程任务引擎（L2）= Hermes Kanban 薄封装

**目标**：让一句模糊需求端到端、可中断、可恢复、可审计地跑完，并交付质量可靠的成果。

**任务工作区约定**（每个长程任务一个目录）：

```
~/.campus/tasks/<task-id>/
├── Plan.md            # 计划：目标、拆解、checkpoint、acceptance criteria、validation 命令
├── Status.md          # 状态：当前阶段、已完成 checkpoint、阻塞、下一步
├── Verification.md    # 验证：每个交付物的校验记录、对抗辩论结论、源可靠性证据
├── DecisionLog.md     # 决策记录：关键路径选择与理由（可追溯）
├── EventLog.jsonl     # 事件流：append-only，agent 每次 action/observation/handoff
├── Memory.md          # 本任务沉淀的结构化记忆（结束后并入 L4）
└── Artifacts/         # 产出物：策划案、邮件草稿、复习计划、quiz 等
```

**状态机**：`intake → planning → debate(plan) → executing → verify(debate) → awaiting_human → delivered → archived`。

- **intake**：Meta-Agent 分类（短任务直接走 Hermes，长任务进 Odyssey）。
- **planning**：Planner 产出 `Plan.md`（含 checkpoint + acceptance + validation 命令）。
- **debate(plan)**：Critic 对抗审查计划（可行性、覆盖度、风险），不过则回 planning。
- **executing**：按 DAG 调度角色 agent，每个 checkpoint 落 `Status.md` + `EventLog.jsonl`。
- **verify(debate)**：Reviewer 对交付物做格式/事实/预算/时间/安全预案检查；事实类强制走 SourceVerifier。
- **awaiting_human**：对外发送类操作暂停等用户确认。
- **delivered/archived**：交付、记忆沉淀、写每日秘书日志。

**恢复**：进程崩溃/重启后，Kanban 的 TTL/心跳/PID 三重回收自动把 stale 任务重新入队 `ready`，从最近 checkpoint 续跑（Hermes 已实现，无需自研）。

**实现取向（关键取舍，源码已验证）**：Odyssey **建在 Hermes 内置 Kanban 上**（`hermes_cli/kanban_db.py` + `tools/kanban_tools.py`），不自研状态机/恢复。写一个薄编排器：`create_task(assignee=角色, parents=依赖, goal_mode=True)` 建任务，`dispatch_once(spawn_fn=我们的 spawner)` 驱动，worker 调 `kanban_complete(summary, metadata)` 结构化交接。任务工作区文件映射：`Plan.md`→`tasks.body`、`Status.md`→`tasks.status`+`task_events`、`Verification.md`→`tasks.result.metadata`、`EventLog.jsonl`→`task_events`。**不用 `delegate_task`**（非持久，进程死则丢，源码注释原话）。

### 4.2 多智能体编排（L3）

**角色 agent**（每个是一段 Hermes 委派 prompt + 绑定 toolset）：

| 角色 | 职责 | 绑定工具 |
|---|---|---|
| Meta-Agent | 任务分类、skill 发现、模式选择 | memory, skill search |
| Planner | 拆解任务、写 Plan.md | memory, calendar |
| Critic | 对抗审查计划 | — |
| Researcher | 检索地区/主题/政策/机构/资源 | Exa(CLI), browser, GitHub |
| SourceVerifier | 验证目标/联系人/资源真实性、来源可靠性 | browser, Exa |
| SourceRanker | 多资源打分排序（适合度、年份、权威性） | — |
| Writer | 生成策划案/PPT/计划/邮件草稿 | LibreOffice/Obsidian/Zotero(CLI) |
| Reviewer | 格式贴合、事实核查、预算/时间/安全预案 | — |
| Scheduler | 读日历、排期、生成复习计划/quiz | calendar, cron |
| Email/Outreach | 生成外联邮件（仅草稿，等人确认） | email gateway |

**对抗对**：Planner↔Critic（开工前）、Writer↔Reviewer（收工前）= 用 `parents` 串两条 Kanban 任务，Critic/Reviewer 的 `metadata.verdict` 决定回环或放行。辩论结果写 `Verification.md`。

**Supervisor**（`campus/odyssey/supervisor.py`，挂在 dispatch tick，C2）：每个闸门**轮次上限**（如 ≤3 轮，超了强制放行并标注）；**死锁/空转检测**（连续 N 轮无新增决策 → 打断，升级 `awaiting_human`）；**对话协议**（所有 handoff 走 `kanban_complete(summary, metadata)` 结构化格式）；**成本闸**（单任务 token 超阈值 → 暂停问用户）。

**非 SWE 任务的特定改进**（REUSE_MAP 要求）：
- 强制 **SourceVerifier + SourceRanker** 双岗，杜绝幻觉机构名/联系人/资源。
- **格式贴合**：从用户样本（截图/文档）抽取栏目与语气，Reviewer 校验贴合度。
- **人因安全**：邮件/消息/日历写入一律 human-in-the-loop。

### 4.3 记忆系统（L4）

**多层结构**（GOAL.md 定义）：

| 层 | 内容 | 写入时机 | 检索方式 |
|---|---|---|---|
| 用户长期偏好 | 身份、专业、口味、人格选择 | onboarding + 持续 | 注入 session 上下文 |
| 任务日志 | 长程任务 EventLog/DecisionLog | 任务执行 | FTS5 + 任务 id |
| 任务看板 | 进行中/待办/已完成 | Odyssey 状态变更 | 结构化查询 |
| 知识库 | 用户指定网址/讲义/笔记索引 | 用户绑定/扫描 | 向量 + FTS5 |
| 每日秘书日志 | 当天做了什么、明天提醒 | 每日 cron | 日期检索 |

**增强点**：
- 在 Hermes 的 FTS5 之上加 **向量检索**（/embedding + 向量库，或 Honcho/mem0 backend）。
- **Ebbinghaus 复习引擎**：学习类任务的复习节点写入 cron，按遗忘曲线触发每日 quiz。
- **压缩/遗忘**（借 Claude dreams）：后台 cron 对老 EventLog 做摘要、淘汰低价值条目、沉淀为长期偏好/知识。用户可设保留窗口。

### 4.4 Meta-Agent（L5）

**解决 REUSE_MAP 的痛点**：非 CS 学生不懂 skill/MCP/工作流文档。

- **上手引导**：自然语言配置（"我是大二计算机专业的"），自动推荐并装 skill/tool（调 `cli-hub`）；询问用户已有哪家 provider key，**自动生成角色→模型路由配置**（不绑死任何厂商）。
- **skill 发现与可靠性验证**：用户说模糊目标，Meta-Agent 检索可用 skill、评估可靠性、选合适模式。
- **工作流编排**：把开放需求映射到 Odyssey 角色 DAG；找不到现成 skill 时，自动组合 CLI-Anything 工具。
- **零配置可用**：开箱内置 100+ skill（Hermes skills + CLI-Anything skills + 校园 skill pack），不强制用户手工编辑。

### 4.5 工具与技能层（L1）

- **直接用**：`cli-anything-hub` 注册表 60+（LibreOffice/PPT、Obsidian、Zotero、Exa 搜索、Godot、ComfyUI…）。
- **校园/中文工具按需封装**（用 CLI-Anything 7 阶段 SOP）：微信读取、学校网络学堂、知乎/小红书（仅浏览器自动化辅助，**不承诺稳定抓取**，已在 DEMO C 注明）、课程平台。
- **Skill pack**：agentskills.io 格式，放 `campus/skills/`，Hermes curator 自动加载。

### 4.6 人格层（L6）

- 人格 = 一段 system prompt 风格指令 + 语气示例（费曼式启发、鲁迅式犀利…）。
- 存 `campus/personas/<name>.md`，由 Meta-Agent 在 onboarding 让用户选，写入长期偏好。

### 4.7 接口层（L7）

- **桌面 GUI**：基于 Hermes Electron app 定制皮肤 + 新手引导 + 人格配置面板（**不重写**，换皮）。
- **移动聊天**（分层，onboarding 让用户选主渠道）：
  - **主选：QQ Bot**（官方 API v2，本科生覆盖广；Hermes `gateway/platforms/qqbot/`，支持 C2C/群@/频道，含 markdown/按钮/语音 STT，q.qq.com 注册 AppID/Secret 即用）。
  - **二级：飞书 Feishu / 企业微信 WeCom**（均官方 API、群可用、无封号；Hermes `plugins/platforms/feishu` + `plugins/platforms/wecom`；适合已用这些工具的社团/用户）。
- **个人微信（iLink）仅作私聊兜底**：Hermes `weixin.py` 走 iLink Bot API，**仅私聊可靠、群消息基本收不到**（Hermes 官方文档明示：iLink bot 身份无法进普通微信群、群事件不投递，非我们能绕过）。仅作"私聊转发样本 + 接收提醒"；群场景走 QQ/飞书/企微群 @机器人 或桌面拖入。
- **Web Dashboard**：Hermes `web/`，做任务看板、记忆审计、设置。

---

## 5. 数据流：以 Demo A 为例走一遍

> 需求：根据微信里别人发来的策划案格式，自动写社会实践策划案 + 找外联对象 + 写邮件。

1. **入口**（L7）：用户在微信把策划案转发给 bot，或桌面拖入截图/文档。
2. **分类**（L5）：Meta-Agent 判定为长程任务 → 创建 Odyssey 任务工作区。
3. **planning**（L3 Planner）：抽取样本栏目/语气/约束，产出 `Plan.md`（Research→Verify→Write→Review→Email 五 checkpoint，含 acceptance）。
4. **debate(plan)**（L3 Critic）：审查计划通过。
5. **executing**（L2→L3）：
   - Researcher（Exa/browser/GitHub）检索目标地区、主题、政策、机构名单；按地理关系排日期。
   - SourceVerifier 验证参访地/外联对象真实性 + 联系方式来源可靠性，证据落 `Verification.md`。
   - Writer（LibreOffice/PPT CLI）生成策划案草稿。
   - Reviewer 校验格式贴合 + 无虚构事实 + 预算/时间/安全预案齐全（不过回 Writer）。
   - Email 生成外联邮件草稿。
6. **awaiting_human**：桌面/移动推送，用户确认。
7. **delivered**：发送或加日历；`Memory.md` 沉淀偏好与机构库；每日秘书日志记录。

Demo B/C 同理，差异在 Researcher 走本地文件扫描 + 知识图谱、Scheduler 走 Ebbinghaus cron。

---

## 6. 建议的仓库结构

```
your_secretary/                         # 仓库根
├── hermes-agent/        # 上游 clone（作参考/可切 submodule，最终以 pip 依赖）
├── OpenHands/           # 上游 clone（仅参考，不依赖）
├── CLI-Anything/        # 上游 clone（仅参考；运行时走 pip cli-anything-hub）
└── student-secretary-agent/            # Campus-Agent 产品仓
    ├── docs/            # GOAL/REUSE_MAP/DEMO_SCRIPT/本文件/IMPLEMENT/ACCEPTENCE_TESTS
    ├── campus/                          # 我们的代码（Campus 层）
    │   ├── odyssey/                     # L2 长程任务引擎
    │   ├── orchestrator/                # L3 角色 agent + DAG + 对抗
    │   ├── memory/                      # L4 增强（向量/Ebbinghaus/压缩）
    │   ├── meta_agent/                  # L5
    │   ├── personas/                    # L6
    │   └── tools/                       # L1 校园/中文 CLI 封装
    ├── skills/                          # 校园 skill pack（agentskills.io）
    ├── plugins/                         # Hermes 插件（platform/memory/campus）
    ├── ui/                              # Electron/Web 定制皮肤 + 引导
    ├── tests/                           # unit/integration/e2e
    └── pyproject.toml                   # 依赖：hermes-agent, cli-anything-hub
```

---

## 7. 关键技术选型与取舍

| 决策 | 选择 | 理由 |
|---|---|---|
| 主语言 | Python 3.11+ | 与 Hermes/CLI-Anything 一致 |
| 内核 | Hermes（**pip/uv 锁版本 + 关自更新**，不 fork 不 clone-follow） | Kanban 引擎 + 90% 能力；锁版本消除 churn |
| 工具层 | CLI-Anything（pip） | 60+ 现成 + 成熟 SOP |
| 长程任务 | 自研 Odyssey（借 OpenHands 思路） | 上游在迁移，不能硬依赖 |
| 前端 | 定制 Hermes Electron/web | 换皮比重写便宜 10× |
| 移动入口 | Hermes gateway（**主：QQ Bot；二级：飞书/WeCom**） | 官方 API、群可用、无封号；个人微信 iLink 仅私聊 |
| 向量检索 | 加在 Hermes FTS5 之上 | 结构化 + 语义双通道 |
| 模型路由 | **用户可配**，多 provider（GLM/DeepSeek/Qwen/OpenAI/Anthropic/本地）按角色分档 | 不绑厂商 + 控成本 |

---

## 8. 待确认的关键决策（实现前敲定）

> 第 1–3 项待你在进入 Phase 0 前确认（✅ 为我的推荐）；第 4–5 项已按讨论敲定。

1. **Hermes 集成策略** ✅ 推荐「依赖 + 插件，最小化 fork」：Campus 层通过 Hermes 插件/skill/委派实现，Odyssey 先以"编排模式"落地，**不 fork 主循环**。仅当证明无法表达状态机/恢复时，再最小 vendor。
   - 备选：全量 fork——控制力强但与上游同步成本极高（Hermes 有 760KB 的 god-file，每日提交）。
2. **MVP 先跑哪个 Demo** ✅ 推荐顺序 **C → A → B**：C 最简（纯 web 搜索 + 排期 + quiz），验证内核；A 最有冲击力（多角色 + 对抗），验证 Odyssey；B 最重（本地扫描 + 知识图谱），最后。
3. **前端策略** ✅ 推荐「定制 Hermes Electron + web 皮肤 + 新手引导」，不另起前端。
4. **移动渠道分层** ✅ 已按你的意见定：**主选 QQ Bot**（官方 API、群@可用、富媒体、Hermes 一等公民适配器）；**二级 飞书 Feishu / 企业微信 WeCom**（任选其一或都做）；**个人微信（iLink）仅私聊兜底**。理由见 §4.7——iLink 群消息基本不可用是 Hermes 官方文档明示的限制。
5. **模型路由**：非决策项，**已定为用户可配**（不绑厂商，见 §1/§7）；onboarding 采集 provider key 后自动生成角色→模型映射。

确认后即可进入 [IMPLEMENT.md](./IMPLEMENT.md) 的 Phase 0。
