# Campus-Agent

> 本科生的专属秘书：5 分钟配置，电脑端 GUI + 移动端聊天。课内、社团、科研、生活全覆盖。
> 三大亮点：**最小上手成本**（美观前端 + 内置 100+ skills + 新手引导）· **长程自动化**（多智能体对抗式 计划-执行-验证）· **持久化个性化**（多层结构化记忆 + 定时提醒）。

配套路标：[ACHITECHURE.md](./ACHITECHURE.md)（架构）· [IMPLEMENT.md](./IMPLEMENT.md)（分阶段路线图）· [ACCEPTENCE_TESTS.md](./ACCEPTENCE_TESTS.md)（验收）· [GOAL.md](./GOAL.md)。

---

## 快速上手

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
# 启动 API（前端消费）
python -m uvicorn campus.api.server:app --port 8000

# 或直接跑 pipeline（产物落 ~/.campus/runs/demo_b-<ts>/）
python -c "from campus.demo_b.pipeline import run_demo_b; r=run_demo_b('<讲义目录>', '2026-08-15', free_minutes=300, start_date='2026-08-01'); print(r.ok, r.kg_nodes, r.plan_days)"
```

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

页面：仪表盘 / 新手引导 / 讲义复习(Demo B) / 任务看板 / 人格 / 记忆。前端**只**经 `campus/api` 取数，绝不直连 Hermes 内部——Hermes 可自由升级。

---

## 移动推送（S-MOBILE）

| 渠道 | 状态 | 配置 |
|---|---|---|
| **飞书 Feishu** | ✅ 真路径 | 复用已配的 `hermes send --to feishu:<chat_id>`（gateway 需在跑）。设 `CAMPUS_FEISHU_CHAT_ID=<chat_id>` 或调用时传 target。 |
| QQ Bot | 端口 + 注入 | q.qq.com 申请 AppID/Secret；在 `campus/mobile/qq_bot.py` 注入 `sender`。本期确定性测试覆盖，真凭证接线为手动步骤。 |
| 企业微 WeCom | 端口 + 注入 | 同上，CorpID/Secret/AgentID。 |

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

## 当前状态（Phase 5 / M5 发布候选）

- Demo A / B / C 后端 + 记忆 L4 + Meta-Agent L5 + 人格 L6 + 编排 L2/L3 + API + 移动 + 成本路由 + 前端 全绿。
- 测试：**206 passed**；phase-5 新模块覆盖率 **91%**（每文件 ≥80%）。
- 前端 `npm run build` 0 错。
- 真实 LLM / 真渠道 e2e 为手动验收项（同 phase 1–4 既定纪律）。

更多细节见 [`devplan/phase-5/`](./devplan/phase-5/)（Plan / Status / Verification）。
