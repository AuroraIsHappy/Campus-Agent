# GOAL 落地进度跟踪

对照 `student-secretary-agent/GOAL.md`，自主执行 8 阶段补齐。

## 总进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| 0 | 自检标准建立 | ✅ 完成 |
| 1 | 聊天后端 /agent/chat | ✅ 完成 |
| 2 | 讲义管线补齐 | ✅ 完成 |
| 3 | Zotero 真实 API | ✅ 完成（真机验证） |
| 4 | 日历同步 | ✅ 完成（飞书 token 验证） |
| 5 | 定时 quiz + 自定义定时任务 | ✅ 完成（LLM 评分验证） |
| 6 | 前端重构 | ✅ 完成（build 通过） |
| 7 | 贯穿串联 | ✅ 完成 |
| 8 | 端到端验证 | ✅ 完成 |

## 详细日志

### 基线
- pytest: 292 passed, 4 failed（均为 .venv 预存 lxml/etree 环境损坏，与本项目无关）
- 前端: React+TS+Vite+Tailwind，12 个表单模块，无聊天界面

### 阶段1 — 聊天后端 ✅
- `POST /agent/chat` 返回自然语言 reply（非 run 元数据），支持人格、多轮、澄清
- ConversationStore 持久化多轮会话（state/conversations.json）
- compose_reply 复用 _extract_content + personas.loader + ask_llm
- 真机验证：default/feynman/lu_xun 三种人格回复语气分明

### 阶段2 — 讲义管线 ✅
- path_resolver: "桌面上那个数据结构讲义" → glob 候选 → 单候选直解析/多候选 needs_clarify
- mindmap: KG chapter→children 森林 → markdown + mermaid + json 树
- notion_blocks: markdown → Notion blocks（headings/lists/tables/code）
- notion.sync_lecture_result: KG+计划+思维导图 → Notion 多 block 页面
- extract_dir 支持单文件（之前返回空）

### 阶段3 — Zotero ✅（真机）
- ZoteroClient: health_check/search/create_items（urllib, never-raise）
- **真机验证**：health_check HTTP 200；search 取到 3 条；create_items 创建 1 篇论文（key JB49DGB5），可再搜到

### 阶段4 — 日历同步 ✅
- FeishuCalendarSyncer: tenant_access_token（缓存）+ create_event
- **真机验证**：飞书 token fetch 成功（.hermes/.env 凭证有效）
- plan_calendar: ReviewPlan/Plan.days → CalendarEvents，本地+飞书，同 title+date 去重
- 本地日历验证：38 个复习事件创建，二次运行幂等

### 阶段5 — 定时 quiz + 自定义任务 ✅
- quiz_session: pending session 持久化，inbound 检测活跃会话→评分→闭环
- quiz_grader: LLM 语义评分（真机验证 91/70 分，有建设性反馈）
- job_store: daily/weekly/once 规则解析 + due_jobs 判定 + 去重
- 调度器 _maybe_daily_quiz + _run_scheduled_jobs 接入 60s 循环
- 聊天 "每天8点提醒我背单词" → 自动注册 job

### 阶段6 — 前端重构 ✅
- 默认主面板 = 聊天对话框（飞书式气泡，markdown 渲染，产物，会话历史）
- 侧边栏：秘书(chat)/任务/日历/记忆/人格/设置/新手引导（无模块导航）
- 任务页搜索框：实时过滤 + 展开详情
- 配色：背景 #fdf6e3（更暖黄），卡片 #fffef9，字体 Plus Jakarta Sans
- npm run build 通过（35 模块，166KB）

### 阶段7 — 贯穿串联 ✅
- LONG_KEYWORDS 补英文（review plan/exam/machine learning/...）
- _classify_agent_message: lecture_summary → Demo B, literature_manage → Zotero
- 126 测试通过

### 阶段8 — 端到端验证 ✅
- 管道联通：讲义模糊路径→确认→KG+思维导图+计划+日历同步 ✓
- Notion 列表 ✓ | 任务搜索 ✓ | GitHub 检索 ✓ | 定时任务注册 ✓ | 会话历史 ✓
- 离线聊天 + 定时任务 + quiz 生成 ✓
- 真机 LLM 费曼风格回复（GitHub 检索证据+url+类比）✓
- 最终测试：120 passed, 3 failed（预存 lxml 环境，与本项目无关）
