## 主力基座：Hermes Agent
Hermes 已经内置了项目的几项基础能力：长期记忆、工具调用、Web / 浏览器 / 终端 / 文件编辑、MCP、委派子智能体、scheduled tasks、skills、消息平台入口等。它的文档明确支持 memory、delegation、scheduled tasks、cronjob、session search 等工具，并且支持通过 gateway 在 Telegram、Discord、Slack、WhatsApp、Signal、Email、Feishu/Lark、WeCom、Weixin 等渠道运行。Hermes 的 memory 设计有 MEMORY.md 和 USER.md 这类持久记忆文件，会在 session 开始时注入上下文；适合存用户偏好、项目约定、已完成事项、技能和使用习惯。Hermes 支持一次性和周期任务，任务可以绑定 skills、工作目录、不同消息投递目标，并由 gateway daemon 每 60 秒检查任务是否到期。

## 多工具接口：Cli-anything
把没有 API、但大学生经常用的软件或 GUI 工作流，包装成结构化 CLI，让 agent 不用脆弱地盯着 GUI 点按钮。它的项目目标是让“所有软件 agent-native”，通过分析、设计、实现 Click CLI、测试、文档、发布等阶段，把软件变成可被 agent 调用的命令行工具。

## 结构化记忆存储&检索：
借鉴hermes agent

## 主动压缩/总结/遗忘：
借鉴claude code的实现思路https://platform.claude.com/docs/en/managed-agents/dreams

## 长程任务状态保持与恢复：直接复用 Hermes 内置 Kanban（重大发现）
精读 delegate_tool 源码后发现：Hermes 已内置 SQLite 持久化的多智能体任务引擎 **Kanban**（`hermes_cli/kanban_db.py` + `tools/kanban_tools.py`）——命名角色 `assignee`、依赖 DAG `parents`、三种崩溃恢复（TTL / 心跳 / PID 死亡回收）、结构化交接 `kanban_complete(summary, metadata)`、goal-mode 有界循环、外部编排入口 `dispatch_once(conn, spawn_fn)`。**Odyssey 不再自研，只写薄编排器**。注意：`delegate_task` 非持久（进程死则工作全丢，源码注释原话），长程任务不能用。

## 长程任务多智能体编排：Hermes Kanban + 自研 Supervisor
建在 Kanban 上（同上）。角色 agent = Kanban `assignee` profile；对抗对 Planner↔Critic / Writer↔Reviewer 用 `parents` 串；自加 **Supervisor**（轮次上限 + 死锁打断 + 对话协议 + 成本闸）。非 SWE 改进：SourceVerifier 强制源、格式贴合、人因安全（不自动发送）。

## nanobot（评估后未采用）
HKUDS 的轻量 agent（~4k 行，pip 锁版本、无自更新、原生 QQ/微信/飞书、自带 WebUI）。优点正是能解决 Hermes 自更新不稳定。但缺 Kanban 级持久化多智能体引擎，且仍 Alpha。结论：保留 Hermes（用其 Kanban），但借鉴 nanobot 的"pip 锁版本 + 关自更新"思路来消除 Hermes 的不稳定。

## Hermes 安装方式：锁版本（消除不稳定）
不 clone-follow；**pip/uv 锁版本安装 + 关自更新**；Campus 代码只依赖 `campus/runtime/*` 薄接口（不直接 import Hermes 内部）；只跟 tag 不跟 main。详见 plan 的 C4。

## 可借鉴的现成 skill
- 飞书日历：https://www.skills.sh/site/open.feishu.cn/lark-calendar （OAuth via lark-cli，可移植）
- 清华网络学堂：https://clawhub.ai/tomuiv/skills/tsinghua-learn （强耦合清华端点，但"单一认证网关 + 铁律 clean-UI + preview-then-confirm + JSON 模块化脚本"是通用网络学堂集成的黄金模板 → 做成模板 + 每校覆盖层）
- Notion：Hermes 已内置 skill（`skills/productivity/notion/`，token 认证）

# 我们需要优化的：
- 更完善的记忆存储与检索
- 更精细的多智能体分工和工作流（确保更复杂的长程任务的完成质量）
- 更多的内置工具和skills
- meta-agent解决非cs专业学生不懂专业文档、不想手动找/编辑skills和tools的问题
- 更美观、user-friendly的前端设计