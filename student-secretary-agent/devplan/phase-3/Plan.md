# Phase 3 — Demo A：策划案 + 外联对象 + 邮件草稿（"多角色对抗长程任务跑通 + 不发送 B1 + awaiting_human"）

> 执行者：自主会话（用户授权后离开）。**工作目录 = 主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-3`（off `phase-2` @ `21cb3d0`）。**
> 上游：[ACHITECHURE.md](../../ACHITECHURE.md) §4.2/§5、[IMPLEMENT.md](../../IMPLEMENT.md) §Phase 3、[ACCEPTENCE_TESTS.md](../../ACCEPTENCE_TESTS.md) §1 + S-NOHALLU。

## 0. 目标与范围（= /goal）
**目标**：用 Phase 2 的 Odyssey 编排器 + Supervisor + 角色，**填上真实 LLM `turn_fn` 接缝**，跑通 Demo A——用户给策划案样本 → 写社会实践策划案 + 找 ≥3 外联对象 + 生成邮件**复制粘贴文本（不发送，B1）**，全程进 `awaiting_human`。

### IN（本期做）
- `campus/runtime/llm_turn.py`：可复用真实 `turn_fn(profile, task) -> TurnOutcome`（泛化 Demo C `ask_llm`，经 `hermes_cli.oneshot.run_oneshot`）。
- `campus/profiles/email.yaml` + `loader.py` `ROLES` 加 `email`（第 10 角色，B1 纯文本，`toolset: []`）。
- `campus/runtime/hermes_kanban.py`：加 `escalate(task_id, reason)`（`awaiting_human` 真实持久化，A-F4）。
- `campus/demo_a/`：`sample_extractor` / `role_turns`（按 role 分派产物）/ `renderers`（docx/xlsx/pptx 纯渲染）/ `checkers`（A-Q1/Q3/Q4）/ `source_check`（A-Q2 HTTP200+语义）/ `verification_writer`（A-Q5）/ `pipeline`（DAG+两处 debate+escalate）/ `_llm`+`types`。
- `run_demo_a.py`：CLI 驱动（镜像 `run_demo_c.py`），真实 LLM 跑，产物落 `~/.campus/runs/<ts>/`。
- `tests/runtime/test_llm_turn.py` + `tests/demo_a/{test_core,test_full_e2e}.py`。

### OUT（不在本期）
- 真实邮箱发送（B1 只生成文本；发送留 human 确认后的后续）。
- 网关推送 awaiting_human 到 QQ/飞书（S-MOBILE，Phase 5）；本期只到状态机 `awaiting_human`。
- 记忆 L4 / Meta-Agent L5（Phase 4）。

## 1. 依赖（已就绪）
- Phase 2 全绿（44 tests / 92%）：Orchestrator + Supervisor 四闸门 + DAG + `KanbanPort`/`InMemoryKanban`/`HermesKanbanAdapter` + 9 角色 profile ✓。
- `make_profile_spawn_fn(loader, turn_fn, cost)` 接缝已就绪（`orchestrator.py:83-99`），`turn_fn(profile, task) -> TurnOutcome` 是注入点。
- Demo C `ask_llm`/`extract_json`（`campus/demo_c/_llm.py`）+ run-dir 产物范式（`campus/demo_c/orchestrator.py`）✓。
- 主仓 `.venv`（hermes-agent==0.18.0, cli-anything-hub==0.4.0, pyyaml, coverage）✓；需补 `python-docx`/`python-pptx`/`openpyxl`。
- `~/.campus/routing.yaml` + `~/.hermes/.env`（GLM key）✓。

## 2. 架构（接缝填充 + Demo A 业务层，复用 Phase 2 引擎）
```
campus/runtime/llm_turn.py      # 真实 turn_fn：profile→run_oneshot→TurnOutcome(summary,metadata{verdict},tokens)
campus/runtime/hermes_kanban.py # +escalate(task_id, reason) 持久化 awaiting_human
campus/profiles/email.yaml      # 第 10 角色（B1 纯文本）
campus/profiles/loader.py       # ROLES += "email"
campus/demo_a/
├── _llm.py            # 角色提示词构建 + 输出 JSON schema（克隆 demo_c 习惯）
├── types.py           # OutreachTarget / ProposalSection / SampleSpec dataclass
├── sample_extractor.py# 从样本抽栏目/语气/约束（纯解析优先）
├── role_turns.py      # make_demo_a_turn(loader,run_dir)->turn_fn；按 role 分派产物写入
├── renderers.py       # to_docx/to_xlsx/to_pptx/to_pdf(若 soffice) 纯渲染器
├── checkers.py        # A-Q1 格式贴合 / A-Q3 预算时间安全正则 / A-Q4 地理合理性
├── source_check.py    # A-Q2 urllib HEAD→HTTP200 + LLM-judge 语义匹配
├── verification_writer.py # A-Q5 辩论双方主张落 Verification.md
└── pipeline.py        # 建 5-checkpoint DAG + 两处 run_debate + 末尾 escalate
run_demo_a.py          # CLI 驱动（真实 LLM）
tests/runtime/test_llm_turn.py
tests/demo_a/{test_core,test_full_e2e}.py
```
**关键取舍**：`turn_fn(profile, task)` 不收 workspace_path（`orchestrator.py:92`）→ 角色产物经**闭包捕获 run_dir** 写入；底层 LLM 调用全部委托可复用 `llm_turn`。Campus 只写差异化，引擎/闸门/DAG 全复用 Phase 2。

## 3. Demo A DAG（每个角色一条 Kanban 任务，`parents` 串；对抗对用 `create_adversarial_pair` + `run_debate`）
```
Planner(抽样本栏目/语气 + Plan.md) →[debate Critic]→ Researcher(web 候选+URL)
  → SourceVerifier(HTTP200+语义) → SourceRanker(≥3) → Writer(策划案+预算/时间/安全)
  →[debate Reviewer]→ Email(每对象 1 段, B1) → escalate(awaiting_human)
```

## 4. 关键设计决策
- **turn_fn 泛化**：`llm_turn(profile, task)` 读 `profile["system_prompt"/"model"/"provider"/"toolset"]` + `task.body`，`run_oneshot` 捕获 stdout，`parse_role_output(raw, role)`——闸门角色（critic/reviewer）抽 `verdict` 进 metadata；其余内容当 summary + 抽 JSON payload 进 metadata。token 优先 run_oneshot usage，否则 char/4。
- **产物闭包**：`make_demo_a_turn(loader, run_dir)` 按 `profile["role"]` 分派（researcher→`outreach_candidates.json`、writer→`proposal.md`、email→`emails.txt`）。
- **B1 不发送**：Email 角色只产文本；pipeline 末尾 `escalate` 进 `awaiting_human`，**全程无 SMTP/gateway send 调用**。
- **A-Q2 不幻觉**：Researcher 经 web toolset 拿真实 URL；`source_check` urllib HEAD 验 HTTP200，不可达→flag→Reviewer reject，**绝不编造**。
- **确定性 e2e**：`test_full_e2e.py` 注入假 turn_fn（canned 结构化输出）+ InMemoryKanban，断言 DAG/辩论/email 段数/awaiting_human/产物；真实 LLM 跑交 `run_demo_a.py`。

## 5. 完成测试标准（Definition of Done，对齐 IMPLEMENT.md 退出标准 + ACCEPTENCE §1）
| ID | 文件 | 验证项 | 通过判据 |
|---|---|---|---|
| P3-T1 | tests/profiles | email 角色注册 | `ROLES` 含 email；11 角色 profile schema 合法；`test_profiles` 全绿 |
| P3-T2 | tests/runtime/test_llm_turn | 真实 turn_fn | mock run_oneshot：researcher→summary+JSON metadata；reviewer→metadata.verdict=approve；token 计入 |
| P3-T3 | tests/odyssey e2e 扩展 | escalate 持久化 | 真实 Hermes DB：escalate 后 SQL `status='awaiting_human'` |
| P3-A-F1 | tests/demo_a | 策划案文档 | `.docx` 生成 + 渲染器回读；产物存在+可打开 |
| P3-A-F2 | tests/demo_a | ≥3 外联对象 | outreach JSON 字段齐全（名称/参访理由/联系方式来源） |
| P3-A-F3 | tests/demo_a | 邮件复制粘贴文本 | `emails.txt` 段数==对象数；无 send 调用（B1） |
| P3-A-F4 | tests/demo_a | awaiting_human | 终态 `status=awaiting_human`；全程不自动发送 |
| P3-A-Q1 | tests/demo_a | 格式贴合 | 栏目覆盖率规则 pass |
| P3-A-Q2 | tests/demo_a | 无虚构 | `source_check` HTTP200+语义规则 pass |
| P3-A-Q3 | tests/demo_a | 预算/时间/安全 | 正则三段齐 |
| P3-A-Q4 | tests/demo_a | 地理合理性 | 日期不跨两远地 |
| P3-A-Q5 | tests/demo_a | 辩论落档 | `Verification.md` 存在 + 含 Planner↔Critic/Writer↔Reviewer 双方主张 |
| 覆盖率 | `--cov` | campus.demo_a+runtime.llm_turn | **≥80%** |

**退出标准（IMPLEMENT.md）**：见 ACCEPTENCE_TESTS.md §Demo A 全绿（A-F*/A-Q*）。

## 6. 构建顺序（TDD，渐进）
T1 email 角色 → T2 llm_turn（含 run_oneshot toolset spike）→ T3 escalate → T4 sample_extractor → T5 role_turns → T6 renderers → T7 checkers+source_check → T8 verification_writer → T9 pipeline → T10 run_demo_a + 真实跑 → T11 tests + 覆盖率 + Verification 收尾。

## 7. harness 注意（沿用 phase-2）
- **工作在主仓**（分支 phase-3）；worktree 损坏勿用。
- **Write 工具**：每新文件 GateGuard 要陈述事实（importers/API/data/原话指令），重试即过。
- **bash**：扫描器拒 `python -c` / `|` 管道 / heredoc——用 Write 工具写文件。跑测试用绝对 venv python。
- **跑测试**：`student-secretary-agent/.venv/Scripts/python.exe -m pytest student-secretary-agent/tests/ -q`。
- **恢复网**：session-only cron（idle 触发）读 `Status.md` 续跑。
- **红线**：不 push remote、不改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件、别关终端、不用 `--dangerously-skip-permissions`。
