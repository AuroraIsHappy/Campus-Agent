# Phase 3 Status（自主执行进度 — cron 读这个续跑）

> 主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-3`（off `phase-2` @ `21cb3d0`）。worktree 损坏勿用。
> 续跑：从未完成的第一个 ⏳ 开始；每完成一项标 ✅ + 贴证据指针。红线条见 Plan.md §7。

## 进度
- ✅ T0 环境：phase-3 分支建好；Plan/Status/Verification 三件套建好。
- ✅ T1 email 角色（`campus/profiles/email.yaml` + `loader.py` ROLES）— profiles 10 passed。
- ✅ T2 `campus/runtime/llm_turn.py`（真实 turn_fn + extract_json 修 bug）— 16 passed。
- ✅ T3 `campus/runtime/hermes_kanban.py` `escalate`（result 列持久化）— e2e 2 passed。
- ✅ T4 `campus/demo_a/sample_extractor.py`
- ✅ T5 `campus/demo_a/role_turns.py`（按 role 分派产物 + ctx 线程）
- ✅ T6 `campus/demo_a/renderers.py`（docx/xlsx/pptx 纯渲染，装了 python-docx/pptx/openpyxl）
- ✅ T7 `campus/demo_a/checkers.py`（A-Q1/Q3/Q4 + A-Q2 verify_urls）
- ✅ T8 Verification 落档（并入 `pipeline.py::_write_verification`，A-Q5）
- ✅ T9 `campus/demo_a/pipeline.py`（DAG + 两处 run_debate + escalate）— 确定性 e2e 22 passed。
- ✅ T10 `run_demo_a.py` + 真实 GLM 跑 ×2（awaiting_human + 不发送 已证；校准项见 Verification）。
- ✅ T11 `tests/demo_a/{test_core,test_full_e2e}.py` + 覆盖率 91%（所有文件 ≥80%）+ Verification 收尾。

## 最终结果（2026-07-08）
- **84 tests passed**（Phase 2 的 55 + Phase 3 新增 29），覆盖率 91%，所有文件 ≥80%。
- 确定性 e2e 全绿：A-F1..F4 + A-Q1..Q5 结构化断言通过（DAG/辩论/email 段数/awaiting_human/不发送/检查器/Verification）。
- 真实 GLM 跑：端到端到 awaiting_human + 不发送 + 闸门生效；3 个校准项（toolsets 未绑/JSON 解析不稳/completeness 措辞）留 Phase 5。
- 命令：`cd student-secretary-agent && .venv/Scripts/python.exe -m pytest tests/ -q`

## 阻塞 / 决策日志
- 2026-07-08：开干。三个架构决策用户拍板（确定性 e2e+手动真实跑 / Campus 纯渲染器 / run_oneshot+HTTP 检查）。
- 2026-07-08：GateGuard 每新文件首写必拦，陈述事实 + 重试即过（沿用 phase-2）。
- 2026-07-08：`escalate` 发现 tasks 表无 metadata 列 → 改写 `result` JSON 列（merge 既有）。
- 2026-07-08：`extract_json` 修 bug（`[{...}]` 被吞成内层 dict）→ 改"最早 opener 类型优先"。
- 2026-07-08：真实跑暴露 email 段数计数 bug（按空行切多段）→ 改 target-name 锚定。
- 2026-07-08：真实跑确认 `run_oneshot(toolsets=exa/...)` 在本机未绑（harness 未装）→ 角色走纯参数知识（决策 3 降级路径生效）；联网检索/验证留 Phase 5 装 harness。
- 2026-07-08：补依赖 python-docx/python-pptx/openpyxl（venv 里有 pip 26.1.2 + uv 0.10.7）。
