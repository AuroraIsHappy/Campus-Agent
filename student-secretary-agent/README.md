# Campus-Agent

> 本科生的专属秘书：5 分钟配置，电脑端 GUI + 移动端聊天。课内、社团、科研、生活全覆盖。
> 三大亮点：**最小上手成本**（美观前端 + 内置 100+ skills + 新手引导）· **长程自动化**（多智能体对抗式 计划-执行-验证）· **持久化个性化**（多层结构化记忆 + 定时提醒）。

配套路标：[ACHITECHURE.md](./ACHITECHURE.md)（架构）· [IMPLEMENT.md](./IMPLEMENT.md)（分阶段路线图）· [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md)（验收）· [GOAL.md](./GOAL.md)。

---

## 快速上手

### 0. 5 分钟本地 demo（推荐）

这条路径优先保证“能打开前端、能跑出真实产物”。默认使用离线 demo 模式，不需要真实 LLM；如果 `hermes_cli` 和 provider key 可用，前端会在“Demo 中心”显示 real readiness。

```powershell
cd C:\Users\Lenovo\Desktop\your_secretary\student-secretary-agent
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1
```

打开：

- 前端：`http://127.0.0.1:5173`
- API 健康检查：`http://127.0.0.1:8000/health`

服务启动后可跑一键冒烟：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_demo.ps1
```

冒烟会验证：`/health`、`/settings/status`、`/agent/run`、Demo A/C offline、科研主题刷新、本地 Markdown 笔记同步、学习 flashcards、生活健康/旅行、社团邮件草稿、职业面试计划。运行产物默认写入仓库内 `.campus-demo/`，不会污染用户主目录。

### 1. Python 环境（重要）

项目自带的 `.venv/Scripts/python.exe` 在受 **Windows Device Guard** 策略保护的机器上会被拦截（exit 126）。**请改用系统/Anaconda Python 3.10+**：

```bash
cd student-secretary-agent
python -m pip install -r requirements.txt   # 用你的系统/conda python
```

> `conftest.py` 已自动处理：当 `hermes_cli` 不可导入时，把 `.venv/Lib/site-packages` 追加到 `sys.path` 尾部（仅补 hermes，不遮蔽你的包）。

### 2. 跑测试

```bash
python -m pytest tests/ campus/demo_c/tests/ -q
# 覆盖率（phase-5 新模块，每文件 ≥80%）：
python -m pytest tests/ campus/demo_c/tests/ \
  --cov=campus.demo_b --cov=campus.api --cov=campus.mobile --cov=campus.meta_agent.cost \
  --cov-report=term-missing -q
```

### 3. 跑 Demo B（讲义 → 复习计划 + quiz）

```bash
# 启动 API（前端消费）。注意：模块级 app 默认不启后台提醒循环。
python -m uvicorn campus.api.server:app --port 8000

# 或直接跑 pipeline（产物落 ~/.campus/runs/demo_b-<ts>/）
python -c "from campus.demo_b.pipeline import run_demo_b; r=run_demo_b('<讲义目录>', '2026-08-15', free_minutes=300, start_date='2026-08-01'); print(r.ok, r.kg_nodes, r.plan_days)"
```

### 3b. 跑生活功能（日程 / 生日纪念日 / 每日秘书日志，Phase 6）

```bash
# 方式一：带后台提醒循环的 API（每 60s 自动检查到期并推送）
python -c "import uvicorn; from campus.api.server import create_app; app=create_app(with_scheduler=True); uvicorn.run(app, port=8000)"

# 方式二：不开循环，手动触发一次「今日提醒 + 秘书日志」
python -c "from campus.life.engine import run_daily; from campus.memory.json_store import JsonFileStore; r=run_daily(memory=JsonFileStore()); print('reminders_sent:', r.reminders_sent, '| log:', r.log.date if r.log else None)"

# 方式三：纯 Python 直接操作（不经 API，方便调试）
python -c "
from campus.life import CalendarEvent, Anniversary, BIRTHDAY, calendar_store, anniversaries
from campus.memory.json_store import JsonFileStore
m = JsonFileStore()
calendar_store.add_event(CalendarEvent(id='', title='高数课', start='2026-07-09T08:00', location='教三301', rrule='WEEKLY'))
anniversaries.add_anniversary(m, Anniversary(id='', name='小明', date='07-09', kind=BIRTHDAY))
print('事件:', len(calendar_store.list_events()), '| 生日:', len(anniversaries.list_anniversaries(m)))
print('-> 打开前端「生活」页或 GET http://localhost:8000/calendar 查看')
"
```

> 后台循环调用真实推送（`campus.mobile.cli.push`）需要先配好飞书/QQ 渠道（见下「移动推送」）。未配渠道时推送会返回失败但**不影响秘书日志写入**。

### 4. 前端

```bash
cd frontend
npm install
npm run dev        # 开发服务器 http://localhost:5173 （dev 代理 /api -> :8000）
npm run build      # 产物 dist/ （tsc + vite build，0 错即通过）
npm run preview    # 预览生产构建
```

桌面壳（可选，非默认依赖）：

```bash
npm i -D electron concurrently wait-on
npm run electron:dev
```

页面：仪表盘 / 秘书 / 学习 / 科研 / 生活 / 社团实践 / 职业 / 任务 / 记忆 / 设置 / 新手引导 / Demo 中心。前端**只**经 `campus/api` 取数，绝不直连 Hermes 内部——Hermes 可自由升级。

---

## 移动推送（S-MOBILE）

| 渠道 | 状态 | 配置 |
|---|---|---|
| **飞书 Feishu** | ✅ 真路径 | 复用已配的 `hermes send --to feishu:<chat_id>`（gateway 需在跑）。设 `CAMPUS_FEISHU_CHAT_ID=<chat_id>` 或调用时传 target。 |
| QQ Bot | 端口 + 注入 | q.qq.com 申请 AppID/Secret；在 `campus/mobile/qq_bot.py` 注入 `sender`。本期确定性测试覆盖，真凭证接线为手动步骤。 |

```bash
python -c "from campus.mobile import push; print(push('feishu', None, 'hello from campus'))"
```

---

## 模型路由 & 成本（S-MODELCONFIG / S-COST）

- 角色分档：`campus/meta_agent/cost.py` —— `CHEAP/MID/STRONG`（≈ Haiku/Sonnet/Opus）+ `BudgetGate`（超预算拒）。
- 用户可配：`~/.campus/routing.yaml`（角色 → {provider, model}），不绑厂商；至少一家非 Anthropic provider 可跑通。
- 真实 LLM/embedding 走注入点（`campus/runtime/llm_turn.py`、`campus/memory/embedding.py`），测试期注入 stub，零网零模型。

---

## 架构（薄 ports + 纯函数 + 注入 stub，§C4②）

```
campus/
├── demo_b/      # 讲义扫描→KG→资源→复习计划+quiz（B-F1..F6）
├── api/         # FastAPI 薄层（前端消费）
├── mobile/      # 推送端口（飞书真 + QQ/企微端口）
├── meta_agent/  # onboarding / routing / skill 发现 / cost
├── memory/      # L4 多层记忆 + 向量/FTS 召回 + Ebbinghaus
├── personas/    # L6 人格（费曼/鲁迅/默认）
├── odyssey/     # L2 编排器 + Supervisor
├── orchestrator/# L3 DAG + 对抗闸门
├── profiles/    # 角色 system prompt + toolset + model
└── runtime/     # KanbanPort + 注入 turn_fn（hermes_cli 懒导入）
frontend/        # React+Vite+TS+Tailwind（+可选 Electron）
```

**红线**：不修改 `hermes-agent/`、`OpenHands/`、`CLI-Anything/` 三仓的 tracked 文件；Campus 只依赖公开 skill/plugin/CLI 接口。

---

## 当前状态（Phase 7 本地产品闭环）

- 无外部 key 时，本地 fallback 可完成学习、科研、生活、社团实践、职业每个域至少一个任务。
- `/agent/run` 提供自然语言统一入口，并把 run/task/artifact 写入 `CAMPUS_HOME`。
- `/settings/status` 汇总 LLM、skills、Notion、移动推送、GitHub/search provider readiness。
- Demo A / C offline、科研主题 digest、本地 Markdown 笔记、前端工作区已跑通。
- `/demo/status` 会显示真实 LLM readiness；当前 API real 模式走 `hermes_cli` import 路径，不依赖 `hermes` CLI 是否在 PATH。
- 测试：`tests/api/test_core.py` 当前 **22+ passed**（随 Phase 7 API 覆盖增长）。
- 前端：`npm.cmd run typecheck` 通过；`npm.cmd run build` 在沙箱内会被 esbuild 读目录权限卡住，沙箱外构建通过。
- 移动真渠道、Notion 真同步、GitHub/search live provider 仍按手动配置/验收推进；未配置时不阻塞本地 fallback。

更多细节见 [`devplan/phase-5/`](./devplan/phase-5/)（Plan / Status / Verification）。
