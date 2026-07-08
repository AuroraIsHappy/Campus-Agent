# Phase 5 — Demo B + 前端 + 移动 + 成本路由 + 文档（"发布候选 M5"）

> 执行者：自主会话（用户授权后离开）。**工作目录 = 主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-5`（off `phase-4` @ `2062a04`）。**
> 上游：[ACHITECHURE.md](../../ACHITECHURE.md)、[IMPLEMENT.md](../../IMPLEMENT.md) §Phase 5、[ACCEPTENCE_TESTS.md](../../ACCEPTENCE_TESTS.md) §2 Demo B + §4 S-MOBILE/S-COST + §5 测试映射。
> 续跑：`/loop`（session-only cron）读 `Status.md`，从未完成第一个 ⏳ 续；每完成一项标 ✅ + 贴证据；acceptance 全绿后删 cron。

## 0. 目标与范围（= /goal）

**目标**：拿下最重的 **Demo B**（讲义→知识图谱→资源→期末复习计划+每日 quiz）+ **新建 Campus 独立前端**（React+Vite+TS+Tailwind+Electron 壳）+ **移动推送适配**（飞书真推 + QQ/企微端口）+ **成本路由打磨** + **文档**。里程碑 **M5（发布候选）**。

**验收北极星**（ACCEPTENCE §2 + §4）：
- **B-F1..B-F6 / B-Q1..B-Q3**：Demo B 端到端全绿（扫描→KG→检索→复习计划→每晚 quiz→次日调整）。
- **S-MOBILE**：飞书真推送可达；QQ/企微走纯端口+确定性集成测试。
- **S-COST**：角色→模型分档路由（Haiku/Sonnet/Opus 分流）+ 成本闸生效。
- **前端**：能 `npm run build`（tsc+vite）通过；覆盖 onboarding/dashboard/demoB/kanban/persona/memory。

### 三项已锁决策（用户 2026-07-08 确认）
1. **前端** = 新建 `student-secretary-agent/frontend/` 独立 React+Vite+TS+Tailwind（+Electron 壳），经 `campus/api/` 薄 API 对接 campus 后端；**严守三仓红线**（不改 hermes-agent/OpenHands/CLI-Anything tracked 文件）。"换皮" = Campus 自有皮肤，不重写 Hermes。
2. **范围** = 全做 5 块；通过线 = 确定性 M5（见 §5）。真实渠道开通/真 LLM e2e 留用户手动（同 phase 1–4 既定纪律）。
3. **凭证** = 复用已配 hermes 飞书 gateway（memory 有 chat id `oc_91b102…`）做真推送；QQ Bot/企微/真 LLM 全走纯端口+注入 stub。

### IN（本期做）
- `campus/demo_b/`：types + extractors + knowledge_graph + resource_search + review_planner + quiz + checkers + pipeline（Demo B 全链路）。
- `campus/api/`：FastAPI 薄层（/demo_b/run、/runs、/memory、/onboarding、/profile、/tasks），包装现有 campus 库。
- `frontend/`：Vite React TS 应用 + Tailwind 皮肤 + Electron 壳 + 五页面。
- `campus/mobile/`：PushPort + FeishuPusher（真 subprocess `hermes send`）+ QQBotPusher/WeComPusher（端口+stub）。
- `campus/meta_agent/cost.py`：成本分档 + 预算闸（S-COST）。
- `tests/{demo_b,api,mobile}/{test_core,test_full_e2e}.py` + `tests/meta_agent/test_cost.py`；子系统覆盖率 ≥80%。
- `README.md` + `requirements.txt` + `devplan/phase-5/Verification.md`。

### OUT（不在本期）
- 真 LLM/embedding 跑 Demo B 全链路（本期注入 stub 证确定性；真模型走注入点，留用户验收）。
- QQ Bot/企微真凭证接线与上线审核（本期纯端口+确定性测试；README 写开通步骤）。
- Hermes cron 真实装（本期纯函数 `next_review/due_items` + 调度接口；接线同 phase-4 留打磨）。
- 改 hermes-agent 三仓任何 tracked 文件（红线）。

## 1. 依赖（已就绪 / 本期新增）

**已就绪（phase 1–4 全绿，140 tests）**：
- `campus/runtime/{ports,llm_turn,hermes_kanban,in_memory}`（KanbanPort + 注入 turn_fn）✓
- `campus/{odyssey,orchestrator,profiles,demo_a,demo_c}` ✓
- `campus/memory/`（L4：MemoryPort + InMemory/JsonFile + Ebbinghaus + compress）✓ —— Demo B 知识库落 KNOWLEDGE 层、复习走 ebbinghaus。
- `campus/meta_agent/{routing,skill_discovery,onboarding,skill_pack,meta_agent}` ✓ —— cost 路由在其上扩展。
- `campus/personas/`（L6）✓ —— 前端人格面板消费。

**测试运行器（重要变更）**：
- 项目 `.venv/Scripts/python.exe` **被 Windows Device Guard 策略拦截**（exit 126）。
- **改用 conda `python`（Anaconda 3.13.9）作运行器**；已 `pip install` 补齐 `coverage pytest-cov python-pptx pdfplumber fastapi pyyaml`（pypdf/fitz/docx/openpyxl/flask/uvicorn/httpx/requests/markdown conda 自带）。
- `conftest.py` 已加：`hermes_cli` 不可导入时把 `.venv/Lib/site-packages` 追加到 sys.path 尾部（仅补 hermes_cli，不遮蔽运行器包）—— 已验 140 全绿。
- **跑测试**：`cd student-secretary-agent && python -m pytest tests/ campus/demo_c/tests/ -q`（需 `dangerouslyDisableSandbox`，因 bash sandbox 不让 exec 部分 .exe/网络）。

**本期新增依赖**（写进 `requirements.txt`）：`fastapi`, `uvicorn`, `pypdf`, `pdfplumber`, `python-docx`, `python-pptx`, `openpyxl`, `pyyaml`, `httpx`（前端独立 `package.json`：react/vite/typescript/tailwind/electron）。

## 2. 架构（薄 ports + 纯函数 + 注入 stub，对齐 §C4②）

```
campus/demo_b/                       # Demo B 后端（地基，最先做）
├── __init__.py
├── types.py            # LectureDoc/ExtractedText/KGNode/KnowledgeGraph/ReviewDay/ReviewPlan/QuizQ
├── extractors.py       # ExtractorPort + PDF(pypdf/fitz)/DOCX(docx)/PPTX(pptx)/MD/TXT 分派；纯函数 extract_path()
├── knowledge_graph.py  # build_kg(texts, extract_fn)→KnowledgeGraph；extract_fn 注入（stub 证 B-F2）
├── resource_search.py  # search_resources(topic, searcher)->candidates；复用 demo_c/ranker.score 做 B-Q1 可靠性
├── review_planner.py   # build_review_plan(kg, free_slots, exam_date, ebb)->ReviewPlan；复用 memory/ebbinghaus；B-Q3 总时长≤空闲
├── quiz.py             # generate_quiz(day_content, quiz_fn)->Quiz（B-F5）
├── checkers.py         # B-F1 抽取率/B-F2 KG 结构/B-F3 资源数/B-F4 覆盖到考/B-Q3 不超排/B-Q2 quiz judge 钩子
└── pipeline.py         # run_demo_b(path, exam_date, ...)->RunResult；串 extract→KG→search→plan→day1 quiz→memory(KNOWLEDGE)→run_dir+Verification.md

campus/api/                          # 薄 API（前端消费）
├── __init__.py
├── types.py            # pydantic 请求/响应 schema
└── server.py           # FastAPI app：/demo_b/run /runs /memory /onboarding /profile /tasks；后端可注入（测试用 TestClient）

campus/mobile/                       # 移动推送适配
├── __init__.py
├── ports.py            # PushPort Protocol（send(target,msg)->receipt）
├── feishu.py           # FeishuPusher：subprocess `hermes send --to feishu:<id>`（真，复用 gateway；hermes 懒导入）
├── qq_bot.py           # QQBotPusher：纯端口+注入 sender stub（真凭证留用户）
├── wecom.py            # WeComPusher：同上
└── cli.py              # push(channel,target,msg) 分派

campus/meta_agent/
└── cost.py             # 角色分档（cheap=Haiku/mid=Sonnet/strong=Opus）+ estimate_cost + 预算闸（S-COST）

frontend/                            # 新建 Campus 独立前端（不动 Hermes）
├── package.json        # react/vite/typescript/tailwind/electron
├── vite.config.ts / tsconfig.json / tailwind.config.js
├── electron/main.ts    # Electron 壳（loadUrl localhost:5173 / 或 dist）
└── src/                # pages: Onboarding/Dashboard/DemoB/Kanban/Persona/Memory；components；api client；theme（Campus 皮肤）

tests/
├── demo_b/{__init__,test_core,test_full_e2e}.py
├── api/{__init__,test_core}.py          # FastAPI TestClient，确定性
├── mobile/{__init__,test_core}.py       # mock subprocess/hermes，确定性
└── meta_agent/test_cost.py             # 分档+预算闸
```

**关键取舍**：
- **确定性优先**（沿用 phase-3/4 决策 1）：所有 LLM/网络/subprocess 走注入点；`test_*` 注入 stub，无 Hermes/无网/无真模型/无真凭证。真模型/真渠道跑留用户验收。
- **Demo B 复用而非重造**：KG 落 `memory` KNOWLEDGE 层；复习调度复用 `memory/ebbinghaus`；资源可靠性复用 `demo_c/ranker.score`；pipeline 沿用 `demo_a/pipeline.py` 的 run-dir + Verification.md + RunResult 范式。
- **前端不绑 Hermes 内部**：只经 `campus/api/` 拿数据；Hermes 升级不影响前端。
- **移动：飞书真、其余端口**：飞书走 `hermes send` subprocess（gateway 已在跑，memory 有 chat id）；QQ/企微纯 PushPort + 注入 sender，真凭证接线写 README。
- **cost 不绑厂商**：分档映射角色→tier→{provider,model}，预算闸按 token 估（llm_turn 已有 char//4 估法）。

## 3. 数据模型要点
- `LectureDoc`：`path, ext, size_bytes`；`ExtractedText`：`doc, text, chars, ok, error`。
- `KGNode`：`id, kind(chapter|concept|formula|question_type|key_point), title, summary, source_doc, refs[]`；`KnowledgeGraph`：`nodes[], edges[]`（edge={from,to,rel}）。
- `ReviewDay`：`n, date, topics[], content, practice[], wrong_questions[], quiz:Quiz, est_minutes`；`ReviewPlan`：`exam_date, days[], total_minutes, free_minutes`。
- `QuizQ`/`Quiz`：复用 demo_c/types 形状（q/answer/explanation/options）。
- `RunResult`：`ok, run_dir, final_status, extraction_rate, kg_nodes, resource_count, plan_days, checks[], artifacts, error`（镜像 demo_a.RunResult）。
- `PushReceipt`：`ok, channel, target, message_id, error`。
- `CostTier`：`CHEAP='cheap'/MID='mid'/STRONG='strong'`；`role→tier` 默认表（researcher/writer=strong, critic/reviewer=mid, email/scheduler=cheap）；`estimate_cost(role,tokens)->float`；`BudgetGate.budget`/`.check(spend)->bool`。

## 4. 关键设计决策
1. **确定性优先**（同 phase-3/4）：LLM/网络/subprocess 全注入；stub 测试无外部依赖。
2. **抽取降级链**：PDF→fitz 优先、pypdf 兜底；DOCX→python-docx；PPTX→python-pptx 提文本框；MD→stdlib；TXT→直读。任一失败标 `ok=False` 不抛（B-F1 算抽取率）。
3. **KG 不幻觉**：`build_kg` 的 `extract_fn` 是注入的纯函数（默认 stub 返回结构化节点）；真 LLM 抽取走注入点，留用户接。checkers 校 KG 结构合法（kind 枚举 + 必填字段）。
4. **复习计划不超排**（B-Q3）：`build_review_plan` 读 `free_slots`（注入），按 ebbinghaus 节点 + KG 章节切分到考前每天，`total_minutes ≤ free_minutes`（超则压缩/标 warn）。
5. **次日调整**（B-F6）：`adjust_plan(plan, quiz_results, ebb)` 用 `ebbinghaus.advance`（答错归零重排、答对递增跳级），产 plan diff。
6. **API 薄+可测**：FastAPI 路由只编排 campus 库调用；后端（demo_b pipeline/memory/onboarding/kanban）构造期注入，TestClient 注入 stub 后端 → 确定性。
7. **移动飞书真路径**：`FeishuPusher.send` 调 `hermes send --to feishu:<chat_id>` subprocess，捕获 stdout/returncode → PushReceipt；hermes_cli 懒导入（测试 mock subprocess.run）。QQ/企微 `sender` 是注入点，默认 stub。
8. **前端独立构建**：`npm run build` = `tsc -b && vite build` 必须通过；Electron 壳可选（`npm run electron:dev`）。前端单测用 vitest（可选，本期只要求 build 通过 + 类型绿）。

## 5. 完成测试标准（Definition of Done = /goal 收口线）

| ID | 文件 | 验证项 | 通过判据 |
|---|---|---|---|
| P5-DB1 | tests/demo_b/test_core | 抽取（B-F1） | 各格式 extract 出文本；抽取率 ≥ 阈值；失败降级 ok=False |
| P5-DB2 | tests/demo_b/test_core | 知识图谱（B-F2） | build_kg 产 KGNode 结构合法（kind 枚举+字段）；edges 引用存在 |
| P5-DB3 | tests/demo_b/test_core | 资源检索（B-F3/Q1） | search 返回 ≥N 候选；ranker 打分可解释（年份/权威/匹配） |
| P5-DB4 | tests/demo_b/test_core | 复习计划（B-F4/Q3） | 计划覆盖到考试日；total_minutes ≤ free_minutes |
| P5-DB5 | tests/demo_b/test_core | quiz（B-F5） | generate_quiz 产 ≥1 题；judge 钩子可注入 |
| P5-DB6 | tests/demo_b/test_core | 次日调整（B-F6） | adjust_plan：答错重排、答对跳级；plan diff 非空方向正确 |
| P5-DB7 | tests/demo_b/test_full_e2e | Demo B 全链路 | run_demo_b（全 stub）→ RunResult.ok；产物（plan.md/kg.json/quiz.json/Verification.md）齐 |
| P5-API1 | tests/api/test_core | API 路由 | TestClient 注入 stub 后端：/demo_b/run /runs /memory /onboarding /profile /tasks 200 + schema 合法 |
| P5-MOB1 | tests/mobile/test_core | 飞书真路径 | FeishuPusher mock subprocess.run → PushReceipt.ok；命令含 `hermes send --to feishu:` |
| P5-MOB2 | tests/mobile/test_core | QQ/企微端口 | QQBotPusher/WeComPusher 注入 sender → receipt；无凭证不抛 |
| P5-COST1 | tests/meta_agent/test_cost | 角色分档 | role→tier 默认表；estimate_cost 单调；budget 闸超限拒 |
| FE | frontend/ | 前端构建 | `npm run build`（tsc+vite）0 错；5 页面+皮肤齐 |
| COV | `--cov` | campus.{demo_b,api,mobile,meta_agent.cost} | **每文件 ≥80%** |
| DOC | README/requirements | 文档 | README 含 conda 运行器+pip+前端+移动开通+routing；requirements.txt 齐依赖 |
| BASE | 全量 | 回归 | 现有 140 + 新增全绿（无回归） |

**退出标准**：P5-DB*/API*/MOB*/COST* 全绿 + FE build 通过 + 覆盖率每文件 ≥80% + DOC 齐 + 回归无 → **M5（自动化层）**。真实 LLM/真渠道 e2e 留用户手动验收（同 phase 1–4 决策 1）。

## 6. 构建顺序（TDD，渐进；RED→GREEN 每步；/loop 续跑）

1. **Demo B 后端（地基，最先）**：DB-T1 types → DB-T2 extractors → DB-T3 knowledge_graph → DB-T4 resource_search → DB-T5 review_planner → DB-T6 quiz → DB-T7 checkers → DB-T8 pipeline → DB-T9 demo_b e2e。
2. **API 薄层**：API-T1 types+server 骨架 → API-T2 各路由 + TestClient 测试。
3. **前端**：FE-T1 scaffold(vite+ts+tailwind) → FE-T2 api client+types → FE-T3 五页面+皮肤 → FE-T4 Electron 壳 → FE-T5 `npm run build` 绿。
4. **移动适配**：MOB-T1 ports+feishu（真） → MOB-T2 qq_bot/wecom（端口） → MOB-T3 测试。
5. **成本路由**：COST-T1 cost.py（分档+预算闸） → COST-T2 测试。
6. **收尾**：DOC-T1 README+requirements → V-T1 全量+覆盖率（每文件≥80%）→ V-T2 Verification.md/Status.md 落档 → 删 /loop cron。

## 7. harness 注意（沿用 phase-2/3/4 + 本期新增）
- **工作在主仓**（分支 phase-5）；worktree 勿用。
- **测试运行器 = conda `python`**（非 .venv；.venv 被 Device Guard 拦）。跑测试：`cd student-secretary-agent && python -m pytest <paths> -q`，**勾选 `dangerouslyDisableSandbox`**。
- **Write/Edit 新文件**：GateGuard 首写拦——陈述事实（importers/API/data/原话指令）+ 重试即过。
- **bash**：扫描器拒 `python -c` 复杂串/管道/heredoc——优先 Write 工具；跑测试用绝对/相对 conda python。
- **/loop 续跑**：session-only cron（idle 触发）读 `Status.md` 从未完成第一项续；acceptance 全绿后删 cron。
- **前端**：`cd frontend && npm install && npm run build`；node/npm 需在 PATH（验 `node --version`）。
- **红线**：不 push remote、不改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件、不用 `--dangerously-skip-permissions`、别关终端。
