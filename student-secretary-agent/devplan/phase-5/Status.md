# Phase 5 Status

> `/loop`（session-only cron）读此文件，从未完成第一个 ⏳ 续。每完成一项：标 ✅ + 贴证据（命令输出/产物路径）。
> 分支 `phase-5`（off `phase-4`）。运行器 = conda `python`（`.venv` 被 Device Guard 拦；详见 [Plan.md](./Plan.md) §1/§7）。
> 通过线 = [Plan.md §5](./Plan.md) DoD 全绿。

## 基线
- ✅ phase-4 全绿：140 passed（conda python + conftest 加 venv site-packages 补 hermes_cli）。
- ✅ conftest.py 已修（hermes_cli 不可导入时追加 `.venv/Lib/site-packages`）。
- ✅ 分支 phase-5 已建。

## 任务（按 Plan §6 构建顺序）

### 1. Demo B 后端（地基）
- ✅ DB-T1 `campus/demo_b/types.py` + `__init__.py`（LectureDoc/ExtractedText/KGNode/KGEdge/KnowledgeGraph/ReviewDay/ReviewPlan/QuizQ/RunResult）
- ✅ DB-T2 `campus/demo_b/extractors.py`（ExtractorPort + PDF/DOCX/PPTX/MD/TXT 降级链）+ `tests/demo_b/test_core.py`（**13 passed**，B-F1 抽取/降级/注入全绿）
- ✅ DB-T3 `campus/demo_b/knowledge_graph.py`（build_kg + default/注入 extract_fn + validate_kg，B-F2）
- ✅ DB-T4 `campus/demo_b/resource_search.py`（复用 demo_c Resource+ranker，B-F3/Q1）
- ✅ DB-T5 `campus/demo_b/review_planner.py`（build_review_plan 不超排 B-Q3 + adjust_plan B-F6，复用 ebbinghaus）
- ✅ DB-T6 `campus/demo_b/quiz.py`（generate_quiz + 注入 quiz_fn，B-F5）
- ✅ DB-T7 `campus/demo_b/checkers.py`（all_checks B-F*/B-Q*）
- ✅ DB-T8 `campus/demo_b/pipeline.py`（run_demo_b 全链路 + run_dir/Verification.md + memory KNOWLEDGE）
- ✅ DB-T9 `tests/demo_b/{test_core,test_full_e2e}.py` → **32 passed**（P5-DB1..DB7 全绿）；全量回归 **172 passed**

### 2. API 薄层 ✅ DONE
- ✅ API-T1 `campus/api/{__init__,types,server}.py`（FastAPI + 注入 Backends）
- ✅ API-T2 路由 /health /demo_b/run /runs /memory /onboarding /profile /tasks /push + `tests/api/test_core.py` → **8 passed**（TestClient 确定性，P5-API1）

### 3. 前端
- ⏳ FE-T1 `frontend/` scaffold（vite+react+ts+tailwind）+ `package.json`
- ⏳ FE-T2 `frontend/src/api/` client + types（对齐 campus/api）
- ⏳ FE-T3 五页面+Campus 皮肤（Onboarding/Dashboard/DemoB/Kanban/Persona/Memory）
- ⏳ FE-T4 `frontend/electron/main.ts` 壳
- ⏳ FE-T5 `npm run build` 0 错（P5-FE）

### 4. 移动适配
- ⏳ MOB-T1 `campus/mobile/{__init__,ports,feishu}.py`（PushPort + FeishuPusher 真 subprocess `hermes send`）
- ⏳ MOB-T2 `campus/mobile/{qq_bot,wecom,cli}.py`（纯端口+注入 sender）
- ⏳ MOB-T3 `tests/mobile/test_core.py` 全绿（P5-MOB1/MOB2）

### 5. 成本路由 ✅ DONE
- ✅ COST-T1 `campus/meta_agent/cost.py`（角色分档 CHEAP/MID/STRONG + DEFAULT_ROLE_TIER + TIER_MULT + tier_for/estimate_cost/route_table + BudgetGate）
- ✅ COST-T2 `tests/meta_agent/test_cost.py` → **8 passed**（P5-COST1 全绿：分档单调、route_table 合并、预算闸超限拒）

### 6. 收尾
- ⏳ DOC-T1 `README.md` + `requirements.txt`
- ⏳ V-T1 全量回归 + 覆盖率每文件 ≥80%（P5-COV + P5-BASE）
- ⏳ V-T2 `Verification.md` 落档 + Status 全 ✅ → 删 /loop cron → M5

## 当前进度指针
**下一步**：MOB-T1（campus/mobile/{__init__,ports,feishu}.py：PushPort + FeishuPusher 真 subprocess `hermes send`）。已完成 Demo B 后端 + 成本路由 + API（3/5 块，**188 passed** 全量）。前端待 ultracode Workflow。
