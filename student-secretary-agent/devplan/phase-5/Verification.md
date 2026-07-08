# Phase 5 Verification

> 运行器 = conda `python`（Anaconda 3.13.9）；`.venv` python 被 Device Guard 拦截，`conftest.py` 自动补 hermes_cli。
> 退出标准见 [Plan.md §5](./Plan.md)。

## 基线回归
- ✅ **206 passed**（phase-1..4 全量 140 + demo_b 38 + cost 8 + api 8 + mobile 12）。
- ✅ phase-5 新模块覆盖率 **91%**，**每文件 ≥80%**（见下）。

## P5 验收证据

### Demo B（campus/demo_b/）
- [x] **P5-DB1 抽取（B-F1）**：`tests/demo_b/test_core.py` — PDF(pypdf)/DOCX(pptx)/MD/TXT 真实抽取 + 降级 ok=False + 注入 fake；`extractors.py` 86%。
- [x] **P5-DB2 知识图谱（B-F2）**：`build_kg` chapters+concepts、edges 引用存在、`validate_kg` 干净；`knowledge_graph.py` 88%。
- [x] **P5-DB3 资源检索（B-F3/Q1）**：`search_resources` 去重 + `rank_resources` 复用 demo_c.ranker（+ fallback 路径覆盖）；`resource_search.py` 91%。
- [x] **P5-DB4 复习计划（B-F4/Q3）**：覆盖到考、`within_budget`、`total ≤ free`；`review_planner.py` 90%。
- [x] **P5-DB5 quiz（B-F5）**：`generate_quiz` 注入 quiz_fn、空内容 placeholder；`quiz.py` 86%。
- [x] **P5-DB6 次日调整（B-F6）**：`adjust_plan` 答错重排（wrong_questions）+ 答对 advance。
- [x] **P5-DB7 demo_b e2e**：`tests/demo_b/test_full_e2e.py` — `run_demo_b` 全 stub → `RunResult.ok`；产物 kg.json/plan.md/quiz_day1.json/Verification.md/run_result.json 齐；memory KNOWLEDGE 记录验证。

### API（campus/api/）
- [x] **P5-API1**：`tests/api/test_core.py` **8 passed** — TestClient 注入 stub 后端，/health /demo_b/run /runs /memory /onboarding /profile /tasks /push 全 200 + schema 合法；`server.py` 81%。

### 前端（frontend/）
- [x] **P5-FE**：`npm run build` **0 错**（tsc + vite build；33 modules；dist css 11.8kB + js 152.5kB；717ms）。6 页面 + Campus 皮肤（indigo-on-slate）+ 可选 Electron 壳。

### 移动（campus/mobile/）
- [x] **P5-MOB1 飞书真路径**：`tests/mobile/test_core.py` — mock subprocess.run → receipt.ok；命令含 `hermes send --to feishu:<id>`；rc!=0 → failure。
- [x] **P5-MOB2 QQ/企微端口**：注入 sender → receipt；无 sender → 确定性 failure（不抛）。`tests/mobile/` **12 passed**；cli/feishu/wecom 84–97%。

### 成本路由（campus/meta_agent/cost.py）
- [x] **P5-COST1**：`tests/meta_agent/test_cost.py` **8 passed** — 角色分档（cheap<mid<strong）、`route_table` 合并 routing.yaml、`BudgetGate` 超限拒 + 边界放行；`cost.py` 100%。

### 覆盖率 & 回归
- [x] **P5-COV**：phase-5 新模块 **91%**，**每文件 ≥80%**（api 81–100 / demo_b 86–100 / mobile 84–100 / cost 100）。
- [x] **P5-BASE**：全量 **206 passed**，0 回归。

### 文档
- [x] **P5-DOC**：`README.md`（conda 运行器 + pip + 前端 + 移动开通 + routing + 架构 + 红线）+ `requirements.txt`（齐依赖）。

## 提交历史（phase-5 分支）
```
0f5c0ee test(phase-5): coverage to >=80%/file
3cbbc5f feat(phase-5): Campus frontend (P5-FE, build green)
ac36770 feat(phase-5): mobile push adapters (S-MOBILE)
d3a7995 feat(phase-5): FastAPI layer (P5-API1)
debe686 feat(phase-5): cost routing + budget gate (S-COST)
bba9f48 feat(phase-5): Demo B backend complete (B-F1..F6)
ade2ff5 feat(phase-5): Demo B foundation (B-F1)
e906e26 chore(phase-5): plan + conftest hermes_cli fallback
```

## M5 结论
- [x] 所有 P5-* 验收项绿 → **M5（自动化层）达成**。
- 真实 LLM / 真渠道 e2e（飞书真发已可配、QQ/企微凭证接线、真模型跑全链路）为用户手动验收项，同 phase 1–4 既定纪律。
