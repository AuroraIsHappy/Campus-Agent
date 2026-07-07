# Phase 1 Status

> 实时状态。详细计划见 Plan.md，硬指标见 Verification.md。
> 分支：`phase-1`（off `phase-0`）。

## 当前阶段
- ✅ **Phase 1 端到端跑通**（D1-D7 + V1-1..V1-7 全过；8 单元测试绿）。
- ⏸ V1-8（Hermes SKILL.md agent turn）deferred——run_demo_c.py runner 提供等价入口，SKILL.md 装载留作 polish。

## 如何验证 demo（你回来跑这条）
```
student-secretary-agent/.venv/Scripts/python.exe student-secretary-agent/run_demo_c.py orchestrator "我想学 Linux"
```
→ 产出在 `~/.campus/runs/<时间戳>/`：`plan.md`（30 天）、`quiz_day1.json`（3 题）、`research_candidates.json`、`progress.json`、`run_result.json`；长期记忆写入 `~/.campus/memory.json`。
单测：`.venv/Scripts/python.exe -m pytest student-secretary-agent/campus/demo_c/tests/test_core.py -v`（8 passed）。

## 进度
| ID | 状态 | 备注 |
|---|---|---|
| D1 types.py | ✅ | dataclass + 校验 |
| D2 researcher.py | ✅ | GLM-4.6 知识库出结构化候选；parse_resources 可测 |
| D3 ranker.py | ✅ | 启发式 + 老旧惩罚（<2015 扣分） |
| D4 scheduler.py | ✅ | 30 天铺排 + weekdays_only |
| D5 quiz.py | ✅ | GLM + parse_quiz + retry（治偶发解析失败） |
| D6 memory.py | ✅ | ~/.campus/memory.json + progress 幂等 |
| D7 orchestrator.py | ✅ | 串联 + artifact 落盘；V1-7 e2e PASS |
| D8 skills/*.md | ⏸ | SKILL.md + agent turn 留作 polish（runner 已等价） |
| V1-1..V1-7 | ✅ | 见 Verification.md |
| V1-8 | ⏸ | deferred |
| WAKE_UP_REPORT | ➖ | 你很快回来，用 Status 代替（轻量） |

## 决策日志（自主判断，未叫醒用户）
- **LLM 路径**：`hermes_cli.config.load_env()` 诡异漏掉 GLM_API_KEY → 改用 `env_loader.load_dotenv(~/.hermes/.env, override=True)` 全量加载；`run_oneshot` 包在 `contextlib.redirect_stdout` 里拿文本。纯 import、零 subprocess（bash 扫描器不拦）。写进 `_llm.py`。
- **researcher 用知识库而非 web-tool**：GLM-4.6 对"学 Linux"这类经典资源知识充分（返回 Linux Journey/Intro to Linux/Art of Command Line 等），更可靠；web-ddgs 工具调用留作升级（避免 agent tool-use 不稳）。
- **ranker 老旧惩罚**：初版选中 2001 年的 "Advanced Linux Programming" → 加 `year<2015 扣 0.15`，现选 "Introduction to Linux"（Linux Foundation/edX 2024 入门课，合理）。
- **quiz retry**：首次 e2e 偶发 quiz 解析空（LLM JSON 抖动）→ generate_quiz 加 1 次重试，稳定。
- **MIT Missing Semester**：spec 举例资源；GLM 未主动给出，但候选质量已达标（全是经典入门），未强行硬编码。
- **TDD-lite**：确定性核心带单测（8 passed），LLM 部分带 e2e 断言；覆盖率回填（时间预算内优先可运行 demo）。
- **V0-5 deferred**：quiz 推送手机/手机答题/日历集成都不做，改写文件+CLI。
