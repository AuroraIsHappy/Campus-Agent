# Phase 2 — Odyssey 编排器 + Supervisor + 角色（"空壳多角色任务跑完 + kill/resume + 闸门生效"）

> 执行者：自主会话（用户授权后离开）。**工作目录 = 主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-2`（off `phase-1`）。**
> ⚠️ `.trees/.trees/phase_2` worktree 已损坏/空（bash 仅见 `_probe_env.py`）——**不要在 worktree 里干活**。Read/Write 工具解析到主仓；bash 已能访问主仓（acceptEdits）。
> 上游：[ACHITECHURE.md](../../ACHITECHURE.md) §4.1/§4.2、[IMPLEMENT.md](../../IMPLEMENT.md) §Phase 2、[ACCEPTENCE_TESTS.md](../../ACCEPTENCE_TESTS.md) §5 + S-SUPERVISOR。

## 0. 目标与范围（= /goal）
**目标**：在 Hermes Kanban 上写**薄编排器 + Supervisor + 注册角色 profile**。引擎（状态机/恢复/DAG/交接）由 Kanban 提供，不自研（架构 §4.1 实现取向）。

### IN（本期做）
- `campus/runtime/`：`KanbanPort` 薄接口 + 纯模型 + `InMemoryKanban`（测试假）+ `HermesKanbanAdapter`（运行时包 hermes_cli.kanban_db）。
- `campus/odyssey/orchestrator.py`：`create_task(assignee, parents, goal_mode=True)` + `dispatch_once(spawn_fn)`。
- `campus/orchestrator/dag.py`：DAG 拓扑校验 + 对抗对（`parents` 串，`metadata.verdict` 回环/放行）。
- `campus/odyssey/supervisor.py`：轮次上限 / 死锁空转打断（升级 `awaiting_human`）/ 对话协议 / 成本闸。
- `campus/profiles/*.yaml`（9 角色）+ `loader.py`（解析 routing.yaml）。
- Kanban roundtrip + kill→resume **落成正式代码**（adapter + e2e 测试，复刻 V0-3 spike 证据）。

### OUT（不在本期）
- Demo A/B/C 的业务逻辑（Phase 3/5）；真实 LLM agent turn（profile 只注册 + 提供 spawn_fn 接缝，turn_fn 测试用假）；记忆 L4 / Meta-Agent L5（Phase 4）。

## 1. 依赖（已就绪）
- V0-2/V0-3 Kanban roundtrip + kill→resume 已验证（`campus/odyssey/spike_*.py`）。
- 主仓 `.venv`（py3.13.12, hermes-agent==0.18.0, pytest 8.4.2, pyyaml）✓。
- `~/.campus/routing.yaml`（V0-6，角色→{provider,model}，默认 glm-4.6 / sub_agent glm-4.5-air）✓。
- hermes_cli.kanban_db 真实 API 已 introspect（见 §3）。

## 2. 架构（port/adapter，对齐 C4②）

```
campus/runtime/
├── ports.py          # KanbanPort Protocol + 纯模型(Task/TaskStatus/DispatchBuckets/Verdict)
├── in_memory.py      # InMemoryKanban(KanbanPort)：测试假，含 DAG 就绪 + crash/reclaim/respawn
└── hermes_kanban.py  # HermesKanbanAdapter(KanbanPort)：包 hermes_cli.kanban_db
campus/odyssey/
├── orchestrator.py   # create_task/dispatch_once（只依赖 KanbanPort）
└── supervisor.py     # 四闸门（纯逻辑 + KanbanPort）
campus/orchestrator/
└── dag.py            # DAG 拓扑校验 + 对抗对 verdict 处理
campus/profiles/
├── loader.py         # 加载 yaml + 角色→{provider,model} 解析（routing.yaml 兜底）
└── *.yaml            # 9 角色
tests/
├── odyssey/{test_core,test_supervisor,test_full_e2e}.py
├── orchestrator/test_core.py
└── profiles/test_profiles.py
```

**关键取舍**：Campus 代码**只依赖 `KanbanPort`**，不直接 import hermes 内部 → 单测用 `InMemoryKanban`（无需 hermes 即可跑 ≥80%），真 Hermes roundtrip/kill-resume 走 `HermesKanbanAdapter` 的 e2e 测试。

## 3. Hermes Kanban API（introspect 实测，adapter 对齐）
- `connect(db_path=None, *, board=None) -> sqlite3.Connection`
- `create_task(conn, *, title, body=None, assignee=None, parents=(), priority=0, skills=None, max_retries=None, goal_mode=False, goal_max_turns=None, initial_status='running', workspace_kind='scratch', board=None, ...) -> str`（返回 task_id；**有 parents/goal_mode**）
- `dispatch_once(conn, *, spawn_fn=None, failure_limit=2, stale_timeout_seconds=0, board=None, default_assignee=None, ...) -> DispatchResult`
  - `spawn_fn(task, workspace_path, board)`；返回 pid（外部 worker）或 None（inline 自完成）。
  - `DispatchResult` buckets: reclaimed, promoted, spawned, skipped_unassigned, auto_assigned_default, skipped_nonspawnable, skipped_per_profile_capped, crashed, auto_blocked, timed_out, stale, respawn_guarded, rate_limited, skipped_locked。
- `complete_task(conn, task_id, *, summary=None, metadata=None, result=None, expected_run_id=None) -> bool`
- `detect_crashed_workers(conn) -> list[str]`；`recompute_ready(conn)`；`claim_task(conn, task_id, ...)`
- task 行：id(t_xxxxxxxx)/title/body/assignee/status(ready/running/done/blocked...)/priority/parents/current_run_id/worker_pid/result(summary+metadata)。
- `task_runs(id,task_id,status,outcome∈{crashed,completed,...})`；`task_events(task_id,kind∈{created,claimed,spawned,crashed,completed,...})`。

## 4. 关键设计决策
- **DAG 就绪语义**：子任务（有 `parents`）在所有 parent `done` 前为 `blocked`，全 parent done 后转 `ready`（对抗对靠这个串：Critic 的 parent=Planner task，Planner done 后 Critic 才 ready）。
- **对抗对 verdict**：Critic/Reviewer `complete_task(metadata={'verdict':'approve'|'reject', 'reason':...})`。reject → Supervisor 创建回环子任务（把上游 task 再次入队）；approve → 放行下游。轮次上限兜底。
- **Supervisor 挂 dispatch tick**：每轮 `dispatch_once` 后检视 `DispatchResult` + 各 task metadata，应用四闸门；状态机 `executing ↔ verify(debate) → awaiting_human/delivered`。
- **spawn_fn 接缝**：`make_profile_spawn_fn(loader, turn_fn)` —— 读 task.assignee=角色 → 解析 profile → 调 `turn_fn(role, goal, toolset)` → `complete_task(summary, metadata)`。测试 `turn_fn` 用假（返回固定 verdict）；运行期 `turn_fn` 调 hermes delegate/oneshot（本期不做真实 LLM，留接缝）。
- **kill→resume 正式化**：`HermesKanbanAdapter` + `tests/odyssey/test_full_e2e.py` 在真实 `~/.hermes/kanban.db`（board=`campus-phase2-e2e`）复刻 V0-3：spawn_fn 返回死 pid → tick1 running → tick2 detect_crashed_workers → reclaim → respawn → done（task_runs≥2 含 crashed+completed）。

## 5. 完成测试标准（Definition of Done，对齐 IMPLEMENT.md 退出标准 + ACCEPTENCE §5 + S-SUPERVISOR）
| ID | 文件 | 验证项 | 通过判据 |
|---|---|---|---|
| P2-O1 | tests/odyssey/test_core | orchestrator create→dispatch→complete | InMemoryKanban 上 task `status=done` + metadata 落库 |
| P2-O2 | tests/odyssey/test_core | kill→resume（正式化） | worker 崩溃→reclaim→respawn→done；task_runs≥2 含 crashed+completed |
| P2-S1 | tests/odyssey/test_supervisor | 轮次上限 | 对抗辩论 >max_rounds(=3) 强制放行并标注 |
| P2-S2 | tests/odyssey/test_supervisor | 死锁/空转打断 | 连续 N 轮无新决策 → 升级 awaiting_human |
| P2-S3 | tests/odyssey/test_supervisor | 对话协议 | handoff 必须是 `kanban_complete(summary,metadata)`；非法→拒并标 |
| P2-S4 | tests/odyssey/test_supervisor | 成本闸 | 单任务 token>阈值 → 暂停 |
| P2-D1 | tests/orchestrator/test_core | DAG 拓扑校验 | parents 成环→拒；缺父→拒 |
| P2-D2 | tests/orchestrator/test_core | 对抗对 verdict | Planner↔Critic / Writer↔Reviewer；verdict 决定回环/放行 |
| P2-P1 | tests/profiles/test_profiles | 9 角色 profile 全注册 | 每角色含 system_prompt+toolset+model；schema 合法 |
| P2-P2 | tests/profiles/test_profiles | 模型路由解析 | 角色→{provider,model} 从 routing.yaml 解析；未列角色→default 兜底 |
| P2-E2E | tests/odyssey/test_full_e2e | 真 Hermes roundtrip+kill→resume | HermesKanbanAdapter 在真 kanban.db 跑通；exit 0 |
| 覆盖率 | `--cov` | campus/odyssey+orchestrator+profiles+runtime | **≥80%（supervisor 路径强制）** |

**退出标准（IMPLEMENT.md）**：① 一个空壳多角色任务跑完、被 kill 后 resume、闸门(轮次上限/死锁打断)生效；② supervisor 单测覆盖 ≥80%。

## 6. 构建顺序（TDD 风味：先接口/模型，再实现，再测试，渐进 commit）
T1 ports.py → T2 in_memory.py → T3 hermes_kanban.py → T4 orchestrator+dag → T5 supervisor → T6 profiles+loader → T7 单测全绿 → T8 e2e+coverage → T9 Verification+commit。

## 7. harness 注意（本期实测）
- **工作在主仓**（`/c/Users/Lenovo/Desktop/your_secretary/`，分支 phase-2）；worktree 损坏勿用。
- **Write 工具**：acceptEdits 下可用，目标主仓绝对路径 OK；每新文件 GateGuard 要陈述事实（importers/API/data/原话指令），重试即过。
- **bash**：acceptEdits 下可跑 `python <file>` / `python -m pytest` / 出 worktree 访问主仓；扫描器仍拒 `python -c` / `|` 管道 / heredoc（用 Write 工具写文件，别用 heredoc）。
- **跑测试**：`/c/Users/Lenovo/Desktop/your_secretary/student-secretary-agent/.venv/Scripts/python.exe -m pytest <path> -q`。
- **恢复网**：session-only cron `13,33,53 * * * *`（idle 才触发）读 Status.md 续跑。
- **红线**：不 push remote、不改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件、leave 终端别关、不用 `--dangerously-skip-permissions`。
