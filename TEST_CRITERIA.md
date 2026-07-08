# 测试标准 — GOAL.md 本意落地自检

每阶段完成后对照本文件逐项打勾。模拟用户一天的端到端流程见末尾。

## 阶段1 — 聊天后端 /agent/chat
- [x] `POST /agent/chat` 返回自然语言 `reply`（非 run 元数据），含人格风格
- [x] 多轮上下文：`conversation_id` 贯穿，历史能注入 prompt
- [x] 人格生效：default/feynman/lu_xun 回复语气不同（真机验证三种风格分明）
- [x] LLM 不可用时回退到 `format_reply` 模板，不报错
- [x] `GET /agent/conversations` 列出会话；`GET /agent/conversations/{id}` 取单会话历史
- [x] 澄清流程：信息不足时返回 `needs_clarify` + `clarify_options`

## 阶段2 — 讲义管线
- [x] 模糊路径："桌面上那个数据结构讲义"→ glob 候选→单候选直解析/多候选需确认
- [x] 自动确认：多候选返回 `needs_clarify`，用户确认后带 `confirmed_path` 重跑
- [x] 思维导图：生成 `mindmap.md`(嵌套列表) + `mindmap.mmd`(mermaid) + `mindmap.json`(树)
- [x] Notion 导出：`export_notion=true` 时 KG+计划+思维导图写入 Notion 页面（多 block）
- [x] 单文件路径不再返回空（extract_dir 增加文件分支）

## 阶段3 — Zotero 真实 API
- [x] `GET /notes/zotero/status` 用 `.hermes/.env` 真实凭证返回连通状态
- [x] `POST /notes/zotero/sync` 真实把论文存入用户 Zotero 库（真机验证，key JB49DGB5）
- [x] `GET /notes/zotero/search` 能检索用户库（取到 3 条）
- [x] 未配置时返回 `not configured`，不报错

## 阶段4 — 日历同步
- [x] 复习计划生成后 `sync_calendar=local` 写入本地 calendar.json（38 事件）
- [x] `sync_calendar=feishu` 调飞书日历 API 创建事件（tenant_access_token 真机验证）
- [x] RRULE 本地(DAILY/WEEKLY)→RFC5545 映射正确
- [x] 同 title+date 去重幂等（二次运行 38→38）

## 阶段5 — 定时 quiz 推送 + 问答闭环 + 自定义定时任务
- [x] 调度器到 `CAMPUS_QUIZ_PUSH_TIME`(默认09:00) 触发 `quiz_daily`→推送飞书/QQ
- [x] 推送的 quiz 携带 question_id+review_node_id，存为 pending session
- [x] 用户在飞书/QQ 回复答案→检测 pending session→LLM 评分→推进艾宾浩斯曲线→推送反馈
- [x] quiz 评分走 LLM 语义评分（真机验证 91/70 分），LLM 不可用回退
- [x] 自定义定时任务：`POST /jobs` 注册 `daily 08:00`/`weekly 0 20:00`/`once <iso>` 规则
- [x] 调度器到点触发 job→推送自定义文案到指定频道→幂等去重
- [x] 聊天"每天8点提醒我背单词"→解析→注册 job→回复确认

## 阶段6 — 前端重构
- [x] 默认主面板=聊天对话框（飞书式气泡，user/assistant，回车发送，加载态）
- [x] 助手气泡渲染 markdown + 可点击产物 + 检索证据 url
- [x] 侧边栏：秘书(chat)/日历/任务/记忆/人格/设置/新手引导（无 learning/research/life/club/career 模块导航）
- [x] 任务页顶部搜索框：实时过滤 title/body/domain/status，点结果展开详情
- [x] 配色：背景更偏黄(#fdf6e3)，卡片微暖白(#fffef9)
- [x] 字体：Plus Jakarta Sans 正文，更精致
- [x] 日历/人格/任务/记忆为只读查看型（非填表单）
- [x] `npm run build` 通过（35 模块）

## 阶段7 — 贯穿串联
- [x] 英文模糊需求(machine learning/exam/review)能走长程路径
- [x] "考试/复习计划"意图→真实复习计划器+同步日历
- [x] tasks.json 中文 UTF-8 正常（stores.py 已用 ensure_ascii=False）
- [x] `pytest` 无新增失败（120 passed，3 failed 均为预存 lxml 环境）

## 阶段8 — 模拟用户一天（端到端）
- [x] ① 09:00 收到 quiz 推送（调度器 _maybe_daily_quiz + quiz_session）
- [x] ② 聊天"总结桌面上那个数据结构讲义"→确认→KG+思维导图+复习计划→导出Notion+同步日历
- [x] ③ 聊天 Notion 问答（/notes/notion/list）
- [x] ④ 聊天"下周机器学习考试帮我安排复习"→排程→同步飞书&本地日历
- [x] ⑤ 聊天"找几篇 RLHF 论文存到 Zotero"（真机 create_items JB49DGB5）
- [x] ⑥ 聊天"帮我找学 Linux 的 GitHub 项目和公开课"→url+证据（真机费曼风格回复）
- [x] ⑦ 飞书回 quiz 答案→LLM 评分→艾宾浩斯更新（quiz_session 闭环验证）
- [x] ⑧ 聊天"每天8点提醒我背单词"→注册定时任务
