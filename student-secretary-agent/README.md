# Campus-Agent

> 本科生的专属秘书：5 分钟配置，电脑端 GUI + 移动端聊天。课内、社团、科研、生活全覆盖。
>
> 三大亮点：**最小上手成本**（美观前端 + 内置 skills + 新手引导）· **长程自动化**（多智能体对抗式 计划-执行-验证）· **持久化个性化**（多层结构化记忆 + 定时提醒）。

**前端地址**：`http://localhost:5173`（开发模式）· `http://localhost:8000`（生产模式，前端 + API 同源）

配套文档：[GOAL.md](./GOAL.md)（目标）· [ACHITECHURE.md](./ACHITECHURE.md)（架构）· [IMPLEMENT.md](./IMPLEMENT.md)（路线图）

---

## 功能一览

### 💬 聊天优先（飞书式对话）

主界面是一个**聊天对话框**——像用飞书/微信一样，直接输入任何需求，agent 端到端处理，返回自然语言回复。不需要找模块、填表单。

- **人格风格**：可选默认秘书 / 费曼（启发式类比）/ 鲁迅（犀利简洁），回复语气随你选
- **多轮上下文**：会话历史持久化，agent 记得你之前说过什么
- **模糊需求**：说"总结桌面上那个数据结构讲义"——agent 自动找文件、多候选时跟你确认
- **侧边栏查看**：日历、任务（带搜索框）、记忆、人格设置——都是只读查看型，不是填表单

### 📚 学习

| 功能 | 说明 |
|---|---|
| **自动总结课程讲义** | 模糊路径 → 自动确认 → 知识图谱 → 复习思维导图 → 导出 Notion |
| **复习计划自动排程** | "下周机器学习考试帮我安排复习" → 按艾宾浩斯曲线排日程 → 同步飞书 & 本地日历 |
| **每日 quiz** | 基于艾宾浩斯遗忘曲线，到点自动推送 quiz 到飞书/QQ → 你回复答案 → LLM 语义评分 → 更新复习曲线 |
| **GitHub / 公开课检索** | 真实 GitHub API + LLM 检索，返回带 ⭐ 数、推荐理由、URL 的结果 |
| **flashcard 生成** | 从学习材料生成带间隔重复的卡片 |
| **课程 deadline 追踪** | 自动记录并提醒 |

### 🔬 科研

| 功能 | 说明 |
|---|---|
| **Zotero 文献管理** | 真实 Zotero API：找论文 → 一键存入你的 Zotero 库 → 检索库内文献 |
| **模糊 idea 文献调研** | 一句话描述 → LLM 检索 + Tavily 网络搜索 → 推荐论文 |
| **专题论文跟踪** | 添加跟踪主题，定期刷新最新论文 |
| **GitHub 热门项目跟踪** | 真实 GitHub Trending API |
| **期刊/会议格式检查** | 按目标会议格式检查稿件 |

### 📅 生活 & 定时任务

| 功能 | 说明 |
|---|---|
| **日程管理** | 本地日历 + 飞书日历双向同步 |
| **自定义定时任务** | "每天8点提醒我背单词" → 自动解析 → 注册定时推送 → 到点飞书/QQ 提醒 |
| **生日/纪念日提醒** | 提前一天 + 当天双提醒 |
| **每日秘书日志** | 自动汇总今日日程、任务、提醒 |
| **健康管理 / 旅行计划 / 校园办事导航** | 一句话触发 |

### 🏘 社团 / 💼 职业

活动策划案、会议纪要、招新文案、邮件草稿、实习岗位检索、面试计划+模拟练习——都在聊天里说一句即可。

---

## 亮点实现方式

### 1. 聊天对话如何生成自然语言回复

```
用户消息 → /agent/chat
  ├─ _default_agent_run()     # 跑 agent（路由到 demo_b/c/phase7/meta_agent）
  ├─ _extract_content()       # 从结构化结果提取产物内容
  ├─ personas.loader.apply_to_prompt()  # 注入人格风格
  ├─ ask_llm()                # GLM 把结构化结果编排成自然语言
  └─ ConversationStore.append()  # 持久化多轮会话
```

LLM 不可用时自动回退到模板回复，保证离线也能用。

### 2. 讲义管线（模糊路径 → 知识图谱 → 思维导图 → Notion）

```
"总结桌面上那个数据结构讲义"
  → path_resolver: glob ~/Desktop 下 pdf/docx/pptx/md → token 打分
  → 单候选直解析 / 多候选 needs_clarify → 用户确认
  → extract_dir: 提取文本（PDF/DOCX/PPTX/MD/TXT）
  → build_kg: 生成知识图谱（chapter→concept 公式 问题类型）
  → build_mindmap: KG → 嵌套 Markdown + Mermaid mindmap + JSON 树
  → build_review_plan: 按考试日期 + 空闲时间排复习日程
  → sync_lecture_result: KG+计划+思维导图 → Notion 多 block 页面
  → sync_plan_to_calendar: 复习日程 → 本地日历 + 飞书日历
```

### 3. 定时 quiz 推送 + 问答闭环

```
调度器（每 60s tick）
  → _maybe_daily_quiz(): 到 CAMPUS_QUIZ_PUSH_TIME (默认 09:00)
  → quiz_daily(): 从艾宾浩斯 due 的复习节点生成题目
  → QuizSessionStore.start(): 暂存 pending 会话
  → mobile.cli.push(): 推送到飞书/QQ

用户在飞书回复答案
  → handle_mobile_command(): 检测 pending quiz 会话
  → quiz_grader.llm_grade(): LLM 语义评分（非长度启发式）
  → advance_review_node(): 更新艾宾浩斯曲线
  → push_reply(): 推送评分反馈 → 关闭会话
```

### 4. Zotero 真实集成

```
"找几篇 RLHF 论文存到 Zotero"
  → research_idea / github_trending: Tavily/GitHub 检索论文
  → ZoteroClient.create_items(): POST /users/<id>/items
  → itemTemplate 映射: title→title, url→url, year→date, abstract→abstractNote
  → 真实存入用户 Zotero 库（已用真实 key 验证）
```

### 5. 自定义定时任务

```
"每天8点提醒我背单词"
  → _try_parse_schedule_intent(): 正则解析时间 + 内容
  → JobStore.add(): 注册 job（rule=daily 08:00）
  → 调度器 _run_scheduled_jobs(): 每 tick 检查 due_jobs
  → 到点 push() → 幂等去重（last_fired 2 分钟窗口）
```

规则语法：`daily 08:00` / `weekly 0 20:00`（周一晚8点）/ `once 2026-07-12T09:00`

### 6. 多智能体对抗机制（长程任务）

长程任务（"帮我策划一个社团招新活动"）自动走 MetaAgent → Odyssey DAG：
- **Planner ↔ Critic** 对抗辩论（计划阶段）
- **Writer ↔ Reviewer** 对抗辩论（产出阶段）
- 每个 milestone 有验证闸门，确保质量

### 7. 多层结构化记忆

```
PREFERENCES  — 用户长期偏好（人格、专业、onboarding）
TASK_LOG     — 任务日志（尤其长程多轮任务）
KNOWLEDGE    — 知识库（讲义 KG 沉积）
DAILY_LOG    — 每日秘书日志
```

生成时自动检索（RRF 融合 + 分层策略 + token 预算打包），nightly 自动压缩。

---

## 安装与启动

### 方式一：Docker 一键启动（推荐，生产用）

```bash
cd student-secretary-agent
cp .env.example .env      # 填入你的 key（全部可选，不填走离线模式）
docker compose up -d       # 构建并启动
```

打开 `http://localhost:8000`（前端 + API 同源）。

> Docker 镜像会自动 clone + 构建 hermes-agent（不在 PyPI，需从 GitHub 安装）。

### 方式二：本地开发启动

#### 1. Python 环境

项目自带的 `.venv/Scripts/python.exe` 包含 hermes_cli（LLM 运行时）。如果你的机器没有 Device Guard 限制，直接用 `.venv` 的 Python：

```bash
cd student-secretary-agent
# 用 .venv 的 python（推荐，含 hermes_cli）
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

> 如果 `.venv` 被 Windows Device Guard 拦截，改用系统 Python 3.10+，但 LLM 功能需要额外安装 hermes-agent。

#### 2. 配置密钥

把你的 API key 配在 `~/.hermes/.env`（Hermes 运行时自动加载）：

```bash
# ~/.hermes/.env
GLM_API_KEY=your_glm_key          # LLM（必配，解锁真实 AI 生成）
NOTION_INTEGRATION_TOKEN=xxx      # Notion 导出（可选）
NOTION_DATABASE_ID=xxx            # Notion 数据库 ID
ZOTERO_USER_ID=xxx                # Zotero 文献管理（可选）
ZOTERO_API_KEY=xxx
GITHUB_TOKEN=xxx                  # GitHub 检索（可选）
TAVILY_API_KEY=xxx                # 网络搜索（可选）
FEISHU_APP_ID=xxx                 # 飞书推送 + 日历（可选）
FEISHU_APP_SECRET=xxx
FEISHU_CALENDAR_ID=xxx            # 飞书日历同步需要
CAMPUS_FEISHU_CHAT_ID=xxx         # 飞书推送目标
QQ_APP_ID=xxx                     # QQ Bot 推送（可选）
QQ_CLIENT_SECRET=xxx
```

> **所有 key 都是可选的**——不配任何 key 也能跑离线模式（模板回复）。配了 GLM key 即解锁真实 AI 生成。

#### 3. 启动后端

```bash
cd student-secretary-agent

# 推荐：用 .venv Python 启动（含 hermes_cli + 调度器）
./.venv/Scripts/python.exe -c "
import uvicorn
from campus.api.server import create_app
app = create_app(with_scheduler=True)
uvicorn.run(app, host='0.0.0.0', port=8000)
"

# 或用系统 Python（无 LLM 时走离线模式）
python -m uvicorn campus.api.server:app --port 8000
```

后端启动后：
- API：`http://localhost:8000`
- 健康检查：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`（dev 模式）

#### 4. 启动前端

```bash
cd student-secretary-agent/frontend
npm install
npm run dev        # 开发服务器 http://localhost:5173（dev 代理 → :8000）
```

打开 **`http://localhost:5173`** —— 你会看到聊天界面，直接开始对话。

```bash
npm run build      # 生产构建（dist/）
npm run preview    # 预览生产构建
```

> 生产模式下后端会自动 serve `frontend/dist/`，访问 `http://localhost:8000` 即前端 + API 同源。

#### 5. 跑测试

```bash
# 用 .venv Python（hermes_cli 可用时跑完整套件）
./.venv/Scripts/python.exe -m pytest tests/ -q

# 用系统 Python（离线确定性测试，无网络/无 LLM）
python -m pytest tests/ -q
```

---

## 架构

```
campus/
├── conversation/  # 聊天会话存储 + 回复编排（Phase 9）
├── learning/      # quiz 会话 + LLM 评分（Phase 9）
├── demo_b/        # 讲义 → KG → 思维导图 → 复习计划 + quiz
│   └── path_resolver.py  # 模糊路径解析
│   └── mindmap.py        # 思维导图生成
├── demo_c/        # 学习计划 → 30天排程 + day1 quiz
├── notes/         # Notion + Zotero 集成
│   └── zotero.py         # Zotero 真实 API
│   └── notion_blocks.py  # Markdown → Notion blocks
├── life/          # 日历 / 提醒 / 日程 / 定时任务
│   └── feishu_calendar.py  # 飞书日历 API
│   └── plan_calendar.py    # 计划 → 日历同步
│   └── job_store.py        # 自定义定时任务
├── api/           # FastAPI 薄层（前端消费）
├── mobile/        # 推送端口（飞书 + QQ Bot）+ inbound 问答
├── meta_agent/    # onboarding / routing / skill 发现 / 对抗 DAG
├── memory/        # L4 多层记忆 + 向量/FTS 召回 + Ebbinghaus
├── personas/      # 人格（费曼/鲁迅/默认）
├── odyssey/       # 多智能体编排器 + Supervisor
└── runtime/       # LLM 注入 + stores + 配置
frontend/           # React + Vite + TS + Tailwind
├── src/Chat.tsx   # 聊天主界面
├── src/Views.tsx  # 侧边栏查看页（任务/日历/人格/记忆/设置）
└── src/MindMap.tsx # 思维导图渲染
```

**红线**：不修改 `hermes-agent/` 等外部仓库的 tracked 文件；Campus 只依赖公开 skill/plugin/CLI 接口。

---

## 当前状态（Phase 9 — 聊天优先 + 全功能落地）

### Phase 9 新增

- **聊天优先前端**：主面板=飞书式聊天对话框，侧边栏改为查看型（任务/日历/记忆/人格/设置），删除表单模块导航
- **讲义管线**：模糊路径解析 + 自动确认 + 知识图谱 + 复习思维导图 + Notion 多 block 导出 + 日历同步
- **Zotero 真实 API**：论文存入 + 检索（真机验证）
- **飞书日历同步**：tenant_access_token + 事件创建（真机验证）
- **定时 quiz 推送**：调度器到点推送 + LLM 语义评分 + 艾宾浩斯曲线更新闭环
- **自定义定时任务**：聊天一句话注册定时推送（daily/weekly/once）
- **人格回复**：default/feynman/lu_xun 三种风格（首次启用 personas loader）

### 测试

- 确定性套件：**120+ passed**（无网络/无 LLM）
- 真机验证：Zotero create_items、飞书 token fetch、GLM 人格回复、LLM quiz 评分
- 前端：`npm run build` 通过

### 配置

复制 `.env.example` → `.env` 或直接配 `~/.hermes/.env`。所有 key 可选，不配走离线模式。
