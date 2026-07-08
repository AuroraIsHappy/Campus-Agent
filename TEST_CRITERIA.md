# 测试标准 — GOAL.md 本意落地自检

每阶段完成后对照本文件逐项打勾。模拟用户一天的端到端流程见末尾。

## 阶段1 — 聊天后端 /agent/chat
- [ ] `POST /agent/chat` 返回自然语言 `reply`（非 run 元数据），含人格风格
- [ ] 多轮上下文：`conversation_id` 贯穿，历史能注入 prompt
- [ ] 人格生效：default/feynman/lu_xun 回复语气不同
- [ ] LLM 不可用时回退到 `format_reply` 模板，不报错
- [ ] `GET /agent/conversations` 列出会话；`GET /agent/conversations/{id}` 取单会话历史
- [ ] 澄清流程：信息不足时返回 `needs_clarify` + `clarify_options`

## 阶段2 — 讲义管线
- [ ] 模糊路径："桌面上那个数据结构讲义"→ glob 候选→单候选直解析/多候选需确认
- [ ] 自动确认：多候选返回 `needs_clarify`，用户确认后带 `confirmed_path` 重跑
- [ ] 思维导图：生成 `mindmap.md`(嵌套列表) + `mindmap.mmd`(mermaid) + `mindmap.json`(树)
- [ ] Notion 导出：`export_notion=true` 时 KG+计划+思维导图写入 Notion 页面（多 block）
- [ ] 单文件路径不再返回空（extract_dir 增加文件分支）

## 阶段3 — Zotero 真实 API
- [ ] `GET /notes/zotero/status` 用 `.hermes/.env` 真实凭证返回连通状态
- [ ] `POST /notes/zotero/sync` 真实把论文存入用户 Zotero 库（真机验证）
- [ ] `GET /notes/zotero/search` 能检索用户库
- [ ] 未配置时返回 `not configured`，不报错

## 阶段4 — 日历同步
- [ ] 复习计划生成后 `sync_calendar=local` 写入本地 calendar.json
- [ ] `sync_calendar=feishu` 调飞书日历 API 创建事件（tenant_access_token 流程）
- [ ] RRULE 本地(DAILY/WEEKLY)→RFC5545 映射正确
- [ ] 同 title+date 去重幂等
- [ ] 未配置飞书凭证时回退仅本地，不报错

## 阶段5 — 定时 quiz 推送 + 问答闭环 + 自定义定时任务
- [ ] 调度器到 `CAMPUS_QUIZ_PUSH_TIME`(默认09:00) 触发 `quiz_daily`→推送飞书/QQ
- [ ] 推送的 quiz 携带 question_id+review_node_id，存为 pending session
- [ ] 用户在飞书/QQ 回复答案→检测 pending session→LLM 评分→推进艾宾浩斯曲线→推送反馈
- [ ] quiz 评分走 LLM 语义评分（非长度启发式），LLM 不可用回退
- [ ] 自定义定时任务：`POST /jobs` 注册 `daily 08:00`/`weekly 0 20:00`/`once <iso>` 规则
- [ ] 调度器到点触发 job→推送自定义文案到指定频道→幂等去重
- [ ] 聊天"每天8点提醒我背单词"→解析→注册 job→回复确认

## 阶段6 — 前端重构
- [ ] 默认主面板=聊天对话框（飞书式气泡，user/assistant，回车发送，加载态）
- [ ] 助手气泡渲染 markdown + 可点击产物 + 思维导图递归树 + 检索证据 url
- [ ] 侧边栏：秘书(chat)/日历/任务/记忆/人格/设置/新手引导（无 learning/research/life/club/career 模块导航）
- [ ] 任务页顶部搜索框：实时过滤 title/body/domain/status，点结果展开详情
- [ ] 配色：背景更偏黄(#fdf6e3)，卡片微暖白(#fffef9)
- [ ] 字体：Plus Jakarta Sans 正文，更精致
- [ ] 日历/人格/任务/记忆为只读查看型（非填表单）
- [ ] `npm run build` 通过

## 阶段7 — 贯穿串联
- [ ] 英文模糊需求(machine learning/exam/review)能走长程路径
- [ ] "考试/复习计划"意图→真实复习计划器+同步日历
- [ ] tasks.json 中文不再 GBK 损坏（ensure_ascii=False）
- [ ] `pytest` 无新增失败

## 阶段8 — 模拟用户一天（端到端）
- [ ] ① 09:00 收到 quiz 推送（飞书/QQ）
- [ ] ② 聊天"总结桌面上那个数据结构讲义"→确认→KG+思维导图+复习计划→导出Notion+同步日历
- [ ] ③ 聊天"我 Notion 里关于线性代数的笔记"
- [ ] ④ 聊天"下周机器学习考试帮我安排复习"→排程→同步飞书&本地日历
- [ ] ⑤ 聊天"找几篇 RLHF 论文存到 Zotero"（真机）
- [ ] ⑥ 聊天"帮我找学 Linux 的 GitHub 项目和公开课"→url+证据
- [ ] ⑦ 飞书回 quiz 答案→LLM 评分→艾宾浩斯更新
- [ ] ⑧ 聊天"每天8点提醒我背单词"→注册定时任务
