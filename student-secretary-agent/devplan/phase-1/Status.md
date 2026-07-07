# Phase 1 Status

> 实时状态。自主会话每步更新。详细计划见 Plan.md，硬指标见 Verification.md。
> 分支：`phase-1`（off `phase-0`）。

## 当前阶段
- ⏳ 未开始（等用户授权后，自主会话从 D1 起步）。
- V0-5（gateway）在本期 **deferred**（见 Plan.md §0 DEFERRED）；不阻塞 Phase 1。

## 进度
| ID | 状态 | 备注 |
|---|---|---|
| D1 types.py | ⏳ | dataclass：Resource/Plan/Quiz 等 |
| D2 researcher.py | ⏳ | web-ddgs 搜 + parse_search_results |
| D3 ranker.py | ⏳ | 启发式 score + GLM explain |
| D4 scheduler.py | ⏳ | build_plan 30 天铺排 |
| D5 quiz.py | ⏳ | GLM generate + parse_quiz |
| D6 memory.py | ⏳ | ~/.campus/memory.json + progress |
| D7 orchestrator.py | ⏳ | 串联 + artifact 落盘 |
| D8 skills/*.md | ⏳ | Hermes SKILL.md + agent turn |
| V1-1..V1-7 | ⏳ | 见 Verification.md |
| WAKE_UP_REPORT | ⏳ | 收尾 |

## 决策日志（自主判断记录在此，不叫醒用户）
- （自主会话开始后在此记录每条判断）
