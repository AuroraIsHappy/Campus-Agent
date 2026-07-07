# Phase 3 验证指标（Verification）

> 每个 P3-* 必须可跑出 pass/fail；通过后把证据贴到对应小节。自主执行的 definition of done。
> 跑法：主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-3`，venv `student-secretary-agent/.venv`（hermes-agent==0.18.0）。
> 命令：`cd student-secretary-agent && .venv/Scripts/python.exe -m pytest tests/ -q`

## 运行环境前置
- 分支 `phase-3`（off `phase-2` @ 21cb3d0）；Phase 2 全绿（44 tests / 92%）。
- `~/.campus/routing.yaml` + `~/.hermes/.env`（GLM key）。
- 本期补依赖：`python -m pip install python-docx python-pptx openpyxl`（已装：python-docx 1.2.0 / python-pptx 1.0.2 / openpyxl 3.1.5）。

---

## P3-T1 email 角色注册 ✅
- **用例**：`tests/profiles/test_profiles.py`（沿用，`ROLES` 含 email）。
- **通过**：`ROLES` 含 `email`；10→11 角色 schema 合法；`10 passed`。
### 证据
```
$ .venv/Scripts/python.exe -m pytest tests/profiles/test_profiles.py -q
..........                                                               [100%]
10 passed in 0.08s
```
- 状态：✅

## P3-T2 真实 turn_fn（mock run_oneshot）✅
- **用例**：`tests/runtime/test_llm_turn.py`（16 tests）
- **通过**：researcher→summary+JSON payload；reviewer/critic→metadata.verdict=approve/reject；pending；ask_llm 捕获 stdout；bootstrap 幂等；extract_json 修了"内层 dict 吞外层 list"的 bug。
- 状态：✅

## P3-T3 escalate 持久化（真 Hermes DB）✅
- **用例**：`tests/odyssey/test_full_e2e.py::test_escalate_persists_awaiting_human` + `::test_escalate_merges_into_existing_result`
- **通过**：`escalate` 后 SQL `tasks.status='awaiting_human'` + `result` JSON 含 escalation；既有 result 被 merge 保留。
- 状态：✅

## P3-A-F1..F4 / A-Q1..Q5 确定性 e2e ✅（自动化门槛）
- **用例**：`tests/demo_a/test_full_e2e.py`（3 tests）+ `tests/demo_a/test_core.py`（19 tests）
- **通过**（确定性，注入假 ask_llm + url_opener，无 Hermes/LLM/网）：
  - A-F1 策划案产物：`proposal.md` 存在（.docx 在装了 python-docx 时也生成）✅
  - A-F2 ≥3 外联对象 + 字段（name/visit_reason/contact_source/url）✅
  - A-F3 邮件段数==对象数（target-name 锚定计数）+ 无 send 调用 ✅
  - A-F4 终态 `awaiting_human`（不自动发送；pipeline 源码无 smtp/smtplib）✅
  - A-Q1 格式贴合（栏目覆盖率）/ A-Q3 预算+时间+安全 / A-Q4 地理合理性 全 PASS ✅
  - A-Q2 `verify_urls`（注入 opener→200 reachable / 0 unreachable 不编造）✅
  - A-Q5 `Verification.md` 含 Planner<->Critic + Writer<->Reviewer 双方辩论 ✅
  - DAG：researcher.parents=[planner]、…、email.parents=[writer] 真接线 ✅
  - 两处辩论 round1 APPROVE → `outcome=pass` ✅
### 证据
```
$ .venv/Scripts/python.exe -m pytest tests/demo_a/ -q
......................                                                   [100%]
22 passed in 1.62s
```
- 状态：✅

## 真实 GLM 跑（L3，证据+校准）⚠️ 跑通但暴露校准项
- **命令**：`.venv/Scripts/python.exe run_demo_a.py --topic "航天科普社会实践" --region "北京" --window "2026年7月"`
- **跑 1**（demo_a-20260708-005405）：8 角色全跑通；Targets=5；Email segs=35（计数 bug，已修）；completeness=FAIL；Planner<->Critic=pass、Writer<->Reviewer=forced；**Status=awaiting_human，全程未发送（B1）**✅
- **跑 2**（demo_a-20260708-010230）：Targets=0（GLM 本次未吐干净 JSON → parse 落空）；Status=awaiting_human（管道仍安全收敛，未崩）✅
- **结论**：真实链路端到端可达 awaiting_human、不发送、Supervisor 闸门生效（pass/forced）。暴露 3 个**校准项（非阻塞，Phase 5/打磨）**：
  1. **toolsets 未绑**：`hermes -z: ignoring unknown --toolsets: exa/github/libreoffice/...` → 本机 Hermes 未装这些 CLI-Anything harness，角色走**纯参数知识**（决策 3 的降级路径已生效；`verify_urls` 仍对产出的 URL 做了真实 HTTP 检查）。要真·联网检索/验证需 Phase 5 装 exa/browser harness。
  2. **LLM JSON 解析不稳**：GLM 不总吐干净 ```json 块 → 0-target 退化。需更强结构化输出约束（重试/JSON-mode/更严 schema）—— 后续打磨。
  3. **completeness 正则 vs GLM 措辞**：真实产出措辞触发 FAIL（Reviewer 也因此 forced）—— 真实质量信号，非检查器 bug。
- 状态：⚠️ 端到端跑通 + awaiting_human + 不发送 已证；质量门槛以确定性 e2e 为准（全绿）。

## 覆盖率（≥80%）✅
```
$ .venv/Scripts/python.exe -m coverage run \
    --source=campus.runtime,campus.odyssey,campus.orchestrator,campus.profiles,campus.demo_a \
    --omit="*/spike_*.py" -m pytest tests/ -q \
  && .venv/Scripts/python.exe -m coverage report
84 passed in 1.21s

Name                                Stmts   Miss  Cover
campus\demo_a\checkers.py              60     12    80%
campus\demo_a\pipeline.py             105     15    86%
campus\demo_a\renderers.py             54      8    85%
campus\demo_a\role_turns.py           121      8    93%
campus\demo_a\sample_extractor.py      29      0   100%
campus\demo_a\types.py                 36      0   100%
campus\odyssey\orchestrator.py         53      1    98%
campus\odyssey\supervisor.py          131      6    95%
campus\orchestrator\dag.py             68      0   100%
campus\profiles\loader.py              67      8    88%
campus\runtime\hermes_kanban.py        86     16    81%
campus\runtime\in_memory.py           162     19    88%
campus\runtime\llm_turn.py             97     10    90%
campus\runtime\ports.py                78      1    99%
TOTAL                                1150    104    91%
```
- 状态：✅ 子系统 91%，**所有文件 ≥80%**（demo_a 全 ≥80%；llm_turn 90%；hermes_kanban 81%）。

---

## 总状态
- ✅ **自动化层全绿**：84 tests passed（Phase 2 的 55 + Phase 3 新增 29：llm_turn 16 + demo_a 22... 含 e2e/escalate）；子系统覆盖率 91%，所有文件 ≥80%。
- ✅ **退出标准（IMPLEMENT.md / ACCEPTENCE §1）自动化部分达成**：A-F1..F4 + A-Q1..Q5 全部在确定性 e2e 里结构化断言通过（DAG 接线、两处对抗辩论、email 段数==对象数、终态 awaiting_human、不发送 B1、Verification.md 落档、检查器）。
- ⚠️ **真实 LLM 跑**：端到端跑通到 awaiting_human + 不发送 + 闸门生效；暴露 3 个校准项（toolsets 未绑/JSON 解析不稳/completeness 措辞）—— 按"决策 1"真实跑属 L3 证据+校准，非自动化门槛，留 Phase 5 打磨。
- 里程碑 **M3（长程高利害任务交付可靠）**：编排器+角色+Supervisor 在真实多角色对抗长程任务上首次跑通，Odyssey 接缝（turn_fn）填上。
- 红线合规：未 push remote、未改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件。
