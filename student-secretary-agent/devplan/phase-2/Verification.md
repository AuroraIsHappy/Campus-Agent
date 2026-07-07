# Phase 2 验证指标（Verification）

> 每个 P2-* 必须可跑出 pass/fail；通过后把证据贴到对应小节。自主执行的 definition of done。
> 跑法：主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-2`，venv `student-secretary-agent/.venv`（py3.13.12, hermes-agent==0.18.0）。
> 命令：`student-secretary-agent/.venv/Scripts/python.exe -m pytest student-secretary-agent/tests/ -q`

## 运行环境前置
- 分支 `phase-2`（off `phase-1`）；worktree `.trees/.trees/phase_2` 损坏，本期在主仓干活。
- `~/.campus/routing.yaml`（V0-6）；hermes_cli.kanban_db API 已 introspect（Plan.md §3）。

---

## P2-O1 orchestrator create→dispatch→complete（InMemoryKanban）
- **用例**：`tests/odyssey/test_core.py::test_roundtrip_create_dispatch_complete`
- **通过**：task `status=done` + `metadata.verdict=approve` + summary 落库。
- 状态：✅

## P2-O2 kill→resume（正式化，复刻 V0-3）
- **用例**：`tests/odyssey/test_core.py::test_kill_then_resume`（InMemoryKanban）+ `tests/odyssey/test_full_e2e.py`（真 Hermes）。
- **通过**：worker 崩溃 → reclaim → respawn → done；`task_runs≥2` 含 `crashed`+`completed`；事件含 `crashed`。
- 状态：✅（InMemory + 真 Hermes 双证据）

## P2-S1 轮次上限
- **用例**：`test_supervisor.py::test_round_limit_under/over` + `test_debate_reject_loops_to_force_pass`。
- **通过**：对抗辩论 >max_rounds 强制放行；gate `metadata.verdict_forced=True`。
- 状态：✅

## P2-S2 死锁/空转打断
- **用例**：`test_supervisor.py::test_deadlock_only_after_idle_rounds/test_deadlock_resets_on_progress` + `test_debate_deadlock_escalates`。
- **通过**：连续 idle_rounds 无新决策 → 升级 `awaiting_human`（task.status=awaiting_human）。
- 状态：✅

## P2-S3 对话协议
- **用例**：`test_supervisor.py::test_handoff_ok/missing_summary/none_summary/gate_missing_verdict` + `test_step_flags_protocol_violation`。
- **通过**：handoff 必须 `kanban_complete(summary, metadata)`；缺 summary / gate 无 verdict → `ProtocolViolationError`。
- 状态：✅

## P2-S4 成本闸
- **用例**：`test_supervisor.py::test_cost_gate_under/over/disabled_when_no_tracker` + `test_step_cost_breach_escalates`。
- **通过**：单任务 token>阈值 → `CostLimitExceeded` + 升级 awaiting_human。
- 状态：✅

## P2-D1 DAG 拓扑校验
- **用例**：`tests/orchestrator/test_core.py::test_topo_order_diamond/test_dag_cycle_rejected/test_dag_self_loop_rejected/test_dag_missing_parent_rejected/test_dag_chain_validates`。
- **通过**：parents 成环（含自环）→ `CyclicDAGError`；缺父 → `MissingParentError`；合法 DAG 给出拓扑序。
- 状态：✅

## P2-D2 对抗对 verdict
- **用例**：`test_core.py::test_adversarial_pair_structure/test_verdict_decision_pass_on_approve/test_verdict_decision_rework_on_reject/test_verdict_decision_pending_when_gate_not_done`。
- **通过**：Writer→Reviewer 用 `parents` 串（gate BLOCKED 直到 upstream done）；`metadata.verdict` approve/reject/pending → pass/rework/pending。
- 状态：✅

## P2-P1 9 角色 profile 全注册
- **用例**：`tests/profiles/test_profiles.py::test_all_9_roles_loaded/test_profile_schema/test_validate_clean`。
- **通过**：planner/critic/researcher/source_verifier/source_ranker/writer/reviewer/scheduler/meta_agent 全注册；各含 system_prompt+toolset+model；schema 校验 0 问题（空 toolset 合法——critic/reviewer/source_ranker 纯推理）。
- 状态：✅

## P2-P2 模型路由解析
- **用例**：`test_profiles.py::test_routing_resolution_role_listed/test_routing_resolution_sub_agent_cheap/test_routing_resolution_falls_back_to_default/test_load_routing_from_file/test_missing_routing_file_uses_profile_defaults`。
- **通过**：角色→{provider,model} 从 routing.yaml 解析；sub_agent→glm-4.5-air（便宜），未列角色→default；routing 文件读取 + 缺文件兜底均覆盖。
- 状态：✅

## P2-E2E 真 Hermes roundtrip + kill→resume
- **用例**：`tests/odyssey/test_full_e2e.py::test_hermes_roundtrip_and_kill_resume`（`HermesKanbanAdapter`，真 `~/.hermes/kanban.db`，board=`campus-phase2-e2e`）。
- **通过**：`1 passed in 0.35s`；tick1 dead-pid→running，tick2 reclaim→respawn→done；task_runs≥2 含 crashed+completed；events 含 crashed+completed。
- 状态：✅

## 覆盖率（supervisor 路径强制 ≥80%）
```
$ .venv/Scripts/python.exe -m coverage run --source=campus.runtime,campus.odyssey,\
    campus.orchestrator,campus.profiles --omit="*/spike_*.py" -m pytest tests/ -q \
  && .venv/Scripts/python.exe -m coverage report -m
44 passed in 0.45s

Name                                          Stmts  Miss  Cover
campus/odyssey/orchestrator.py                   53     1    98%
campus/odyssey/supervisor.py                    131     6    95%   ← 强制 ≥80% 达标
campus/orchestrator/dag.py                       68     0   100%
campus/profiles/loader.py                        67     8    88%
campus/runtime/hermes_kanban.py                  72    14    81%
campus/runtime/in_memory.py                     162    19    88%
campus/runtime/ports.py                          78     2    97%
TOTAL                                          634    50    92%
```
- 注：`spike_kanban.py`/`spike_resume.py`（V0-2/V0-3 Phase 0 一次性 spike）不计入 Phase 2 子系统（`--omit`）；计入会拉低 TOTAL 到 76%，但那不是 Phase 2 代码。
- 状态：✅ 子系统 92%，supervisor 95%。

---

## 总状态
- ✅ **Phase 2 全绿**：P2-O1/O2/S1-S4/D1/D2/P1/P2/E2E 全过；44 单测/e2e 测试通过；子系统覆盖率 92%（supervisor 95%）。
- ✅ **退出标准（IMPLEMENT.md）达成**：①空壳多角色任务跑完（roundtrip + adversarial pair + DAG）+ kill→resume（InMemory + 真 Hermes）+ 闸门（轮次上限/死锁打断/对话协议/成本闸）生效；②supervisor 单测覆盖 ≥80%（95%）。
- 里程碑 **M2**：Odyssey 编排器 + Supervisor 可用。
- commit：`c659686`（phase-2 分支）+ 后续 e2e/coverage/Verification 增量 commit。
- 不 push remote（红线）；未改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件。
