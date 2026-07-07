# Phase 4 验证指标（Verification）

> 每个 P4-* 必须可跑出 pass/fail；通过后把证据贴到对应小节。自主执行的 definition of done。
> 跑法：主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-4`，venv `student-secretary-agent/.venv`。
> 命令：`student-secretary-agent/.venv/Scripts/python.exe -m pytest student-secretary-agent/tests/ -q`

## 运行环境前置
- 分支 `phase-4`（off `phase-3` @ 9d76eae）；Phase 3 全绿（84 tests / 91%）。
- 本期**无新依赖**（纯 stdlib + pyyaml，已就绪）。

---

## P4-M1 多层记忆 schema
- **用例**：`tests/memory/test_core.py`
- **通过判据**：InMemoryStore 五层（preferences/task_log/task_board/knowledge/daily_log）分离；remember/recall 按 layer 命中。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-M2 FTS + 向量双通道召回
- **用例**：`tests/memory/test_core.py`
- **通过判据**：关键词召回排序；HashEmbedder cosine 召回；hybrid 合并去重。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-M3 跨 session 记忆召回（S-MEMORY）
- **用例**：`tests/memory/test_full_e2e.py`
- **通过判据**：JsonFileStore 写入 → 新实例从同文件 reload → recall 命中（temp file，确定性）。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-M4 Ebbinghaus 复习节点
- **用例**：`tests/memory/test_core.py`
- **通过判据**：next_review 间隔序列（1/3/7/16/35 d）；due_items@t；答对递增、答错归零。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-M5 压缩 / 遗忘
- **用例**：`tests/memory/test_core.py`
- **通过判据**：老 record→sediment 偏好；retention_window prune；pinned 保留。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-P1/P2 人格层（S-PERSONA）
- **用例**：`tests/personas/test_core.py`
- **通过判据**：feynman/lu_xun/default 存在；apply_to_prompt 注入风格标记（费曼=启发式问句/鲁迅=犀利短句）。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-MA1 skill pack（≥100）
- **用例**：`tests/meta_agent/test_core.py`
- **通过判据**：manifest 载入 ≥100 条；schema 合法（name/source/category/installed/maintained）。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-MA2 skill 发现 + 可靠性
- **用例**：`tests/meta_agent/test_core.py`
- **通过判据**：discover(need) 排序；reliability_score 可解释；pick_mode。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-MA3 模型路由（S-MODELCONFIG）
- **用例**：`tests/meta_agent/test_core.py`
- **通过判据**：generate_routing/write_routing/validate_routing；至少一家**非 Anthropic** provider；写出的 yaml 可被 `ProfileLoader` 读回。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-MA4 onboarding 向导
- **用例**：`tests/meta_agent/test_core.py`
- **通过判据**：OnboardingWizard(ask=canned)→UserProfile（identity/major/persona/provider_keys 齐）。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-MA5 Meta-Agent 编排
- **用例**：`tests/meta_agent/test_core.py`
- **通过判据**：classify short/long；recommend_skills；build_dag（角色 parents 串成 DAG）。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## P4-MA6 端到端（S-ONBOARD + S-MEMORY）
- **用例**：`tests/meta_agent/test_full_e2e.py`
- **通过判据**：非 CS onboarding → UserProfile → routing.yaml → 推荐 skill → 选人格 → 跨 session 召回（确定性，注入 ask/summarizer/embedder stub）。
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

## 覆盖率（每文件 ≥80%）
```
student-secretary-agent/.venv/Scripts/python.exe -m coverage run \
  --source=student-secretary-agent/campus.memory,student-secretary-agent/campus.personas,student-secretary-agent/campus.meta_agent \
  -m pytest student-secretary-agent/tests/ -q \
  && student-secretary-agent/.venv/Scripts/python.exe -m coverage report
```
- 证据：_(待贴)_
- 状态：✅（见下方总状态证据）

---

## 总状态
- ✅ **自动化层全绿**：132 tests passed（Phase 1-3 的 84 + Phase 4 新增 48：memory 27 + personas 7 + meta_agent 14），无回归。
- ✅ **覆盖率**：子系统 96%，**所有新文件 ≥80%**（最低 skill_discovery 83%）。
- ✅ **北极星验收**（确定性 e2e 结构化断言）：
  - **S-MEMORY**：`JsonFileStore` 跨 session 召回（`tests/memory/test_full_e2e.py` + meta_agent e2e session2）。
  - **S-ONBOARD**：`OnboardingWizard` 端到端产 `UserProfile`（meta_agent e2e）。
  - **S-MODELCONFIG**：`generate/validate/write_routing` + `ProfileLoader` 回读 + 至少一家非 Anthropic（zai/deepseek/qwen）。
  - **S-PERSONA**：费曼/鲁迅/默认 `apply_to_prompt` 风格标记可区分。
- ⚠️ **真实 LLM/embedding/cron 接线留 Phase 5**（同 phase-3 决策 1：确定性 e2e 为自动化门槛，真模型跑属校准）。
- 里程碑 **M4（个性化 + 低门槛上手）**：增强记忆 + Meta-Agent + 人格层落地，跨 session 召回与 onboarding 流程自动化达成。

### 证据
```
$ .venv/Scripts/python.exe -m pytest tests/ -q
........................................................................ [ 54%]
............................................................             [100%]
132 passed in 1.40s

$ .venv/Scripts/python.exe -m coverage run --source=campus.memory,campus.personas,campus.meta_agent -m pytest tests/ -q \
  && .venv/Scripts/python.exe -m coverage report
132 passed
Name                                   Stmts   Miss  Cover
campus\memory\compress.py                 35      0   100%
campus\memory\ebbinghaus.py               41      4    90%
campus\memory\embedding.py                53      0   100%
campus\memory\in_memory.py                68      2    97%
campus\memory\json_store.py               57      4    93%
campus\memory\ports.py                    13      0   100%
campus\memory\types.py                    30      0   100%
campus\meta_agent\meta_agent.py           26      0   100%
campus\meta_agent\onboarding.py           39      0   100%
campus\meta_agent\routing.py              62      5    92%
campus\meta_agent\skill_discovery.py      46      8    83%
campus\meta_agent\skill_pack.py           20      0   100%
campus\meta_agent\types.py                60      1    98%
campus\personas\builtins.py               11      1    91%
campus\personas\loader.py                 23      1    96%
campus\personas\types.py                  10      0   100%
TOTAL                                    594     26    96%
```
- 红线合规：未 push remote、未改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件。
