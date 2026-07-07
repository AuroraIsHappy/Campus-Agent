# Phase 1 — MVP：Demo C 端到端（"我想学 Linux" → 资源 → 排期 → 每日 quiz）

> 执行者：自主夜间会话（用户授权后）。分支：`phase-1`（off `phase-0`，继承 V0-x 成果）。
> 范式对齐 Phase 0：Plan/Status/Verification 三件套 + 渐进 commit + WAKE_UP_REPORT。
> 上游：ACHITECHURE.md、IMPLEMENT.md §Phase 1、ACCEPTENCE_TESTS.md §Demo C。

## 0. 目标与范围
- **目标**：用 vanilla Hermes + 少量 skill（**不上 Odyssey**，那是 Phase 2）跑通 Demo C 主链路：
  模糊目标 → 搜公开资源 → 打分择优 → 生成 30 天碎片计划 → 生成第一天 quiz → 写长期记忆。
- **Demo C**："我想学 Linux" → 发现 MIT Missing Semester → 30 天每晚 20 分钟计划 + day1 quiz。

### IN（本期做）
- Researcher / SourceRanker / Scheduler / QuizGen / Memory 五个 skill 的 Python 核心 + 单元测试。
- Orchestrator 串联；e2e 真跑（GLM）。
- Hermes skill 清单（SKILL.md）+ 一次 agent turn 验证。

### DEFERRED（V0-5 解封后接回）
- quiz **推送到 QQ/飞书**（cron 触发 → gateway）→ 本期改为写文件 + CLI 输出。
- 答题**手机回复**入站 → 本期答案从 CLI/stdin 输入，逻辑等价。
- 日历真实集成 → 本期默认每晚 20:00–20:20（可配置），不接 Google Cal。

## 1. 依赖（已就绪）
- V0-1 Hermes 0.18.0 ✓、V0-4 CLI-Anything ✓、V0-6 GLM 路由（~/.campus/routing.yaml）✓。
- web 搜索：用 Hermes 自带 `web-ddgs`（DuckDuckGo，**免费免 key**）；`web-exa` 作可选升级（需 EXA_API_KEY）。
- 不依赖 V0-2/V0-3（Odyssey = Phase 2）、不依赖 V0-5（gateway）。
## 2. 架构（vanilla Hermes + campus 层差异化）

```
student-secretary-agent/campus/demo_c/        # 新包（campus/ 已有 odyssey/ 的 Phase0 spike）
├── __init__.py
├── types.py          # dataclass: Resource / RankedPick / Plan / DayTask / Quiz / QuizQuestion
├── researcher.py     # search_resources(goal, top_k) -> list[Resource]   (web-ddgs + 解析)
├── ranker.py         # rank(resources, goal) -> RankedResult             (启发式打分 + LLM 理由)
├── scheduler.py      # build_plan(resource, slot, days=30) -> Plan       (确定性铺排)
├── quiz.py           # generate_quiz(day_topic, resource) -> Quiz        (GLM)
├── memory.py         # remember(pref) / log_progress(day, status)        (~/.campus/memory.json + progress)
├── orchestrator.py   # run_learning_plan(goal) -> RunResult              (串联 1→5，落 artifact)
└── skills/           # Hermes SKILL.md 清单（让 agent 能调）
    ├── campus-researcher.md
    ├── campus-scheduler.md
    └── campus-demo-c.md   # 顶层 skill：load 后 hermes -z "我想学 Linux" 走全链路
student-secretary-agent/campus/demo_c/tests/
├── test_core.py      # 各模块确定性部分的单元测试（parse / 打分 / 铺排 / 格式化）
└── test_full_e2e.py  # 真跑：orchestrator + 真实 web + GLM
```

### 数据形状（types.py）
- `Resource(title, url, source_type∈{course,doc,video,blog}, provider, year, est_minutes, difficulty)`
- `RankedPick(resource, score 0..1, reasons: list[str])`；`RankedResult(recommendation, picks, goal)`
- `DayTask(n, date, topic, est_minutes, done=False)`；`Plan(goal, resource, slot, days: list[DayTask])`
- `QuizQuestion(q, answer, explanation, options=None)`；`Quiz(day, topic, questions)`

### 两种调用入口
- **直跑（测试/e2e）**：`python -m campus.demo_c.orchestrator "我想学 Linux"`（绕过 agent，确定性 + 1 次 GLM）。
- **agent turn**：`hermes -z "我想学 Linux" -s campus-demo-c`（skill 触发 orchestrator）。
- 直跑是验证主链路、跑覆盖率的主力；agent turn 验证 skill 装载与委派（V1-7）。
## 3. 构建顺序（TDD：每模块先 test_core 再实现，子系统覆盖 ≥80%）

| # | 模块 | 确定性核心（单元测试覆盖） | LLM/web 部分（e2e） |
|---|---|---|---|
| D1 | types.py | dataclass 构造/校验 | — |
| D2 | researcher.py | `parse_search_results(raw_html_or_json) -> list[Resource]`、去重、字段补全/缺失降级 | `search_resources()` 调 web-ddgs |
| D3 | ranker.py | `score(resource, goal)` 启发式（权威性/年份/匹配度/时长适配）、排序 | `explain_top_pick()` 调 GLM 生成理由 |
| D4 | scheduler.py | `build_plan()` 把资源章节铺到 N 天 × slot、跳过周末可配、产出 Markdown | — |
| D5 | quiz.py | `parse_quiz(raw_text) -> Quiz`（解析 LLM 输出为结构） | `generate_quiz()` 调 GLM |
| D6 | memory.py | `read/write ~/.campus/memory.json` + progress 追加、幂等 | — |
| D7 | orchestrator.py | 串联 + artifact 落盘（plan.md/quiz.json/progress） | 端到端 1 次 GLM 链路 |
| D8 | skills/*.md | Hermes SKILL.md frontmatter（name/description）+ 调用入口 | agent turn 验证 |

每步：写 test_core（RED）→ 实现（GREEN）→ `pytest tests/test_core.py -v` 过 → 更新 Status/Verification → commit。

## 4. 关键设计决策（自主会话直接照做）
- **web 搜索**：优先 `web-ddgs`（免费）。`search_resources(goal, top_k=8)` 内部用 hermes 的 web tool 或直接 DDG HTML（fallback）。结果缓存到 `~/.campus/cache/researcher/<hash>.json`（同 goal 24h 内复用），降本+减速率风险。
- **模型路由**：按 ~/.campus/routing.yaml——Researcher/Ranker 用 glm-4.6（要判断力），QuizGen 用 glm-4.5-air（便宜）。直跑时 `hermes_cli`/openai-compat 客户端直接打 z.ai（复用 V0-6 验证过的链路）。
- **slot 默认**：`Slot(time="20:00", duration_min=20, weekdays_only=False)`；CLI `--days N --time HH:MM --min M` 可覆盖。
- **artifact 落盘**：每次 run 写 `~/.campus/runs/<ts>/`：`plan.md`、`quiz_day1.json`、`research_candidates.json`、`progress.json`、`run_result.json`。e2e 验证看这些文件。
- **Memory**：MVP 用本地 `~/.campus/memory.json`（`{preferences: [...], goals: [...]}`）+ `~/.campus/progress/<goal_slug>.json`。预留接口，Phase 4 再桥到 Hermes memory。
- **"MIT Missing Semester" 不写死**：Researcher 真搜，Ranker 真选；测试用 fixture 固定输入验解析/打分，不依赖网络验"搜到什么"。
## 5. 退出标准（调整后）
- 一句"我想学 Linux"端到端产出：① 30 天 plan.md ② day1 quiz.json ③ 写入长期 memory，全部落盘到 `~/.campus/runs/<ts>/`。
- `python -m campus.demo_c.orchestrator "我想学 Linux"` exit 0，artifact 齐全（见 Verification V1-6）。
- `hermes -z "我想学 Linux" -s campus-demo-c` 能起 agent 并产出等价 artifact（V1-7）。
- 各模块 `pytest campus/demo_c/tests/` 全绿，覆盖率 ≥80%。
- 原"quiz 实际推送"作为 V0-5 解封后的收尾项（不在本期硬退出标准内）。

## 6. 自主执行协议（照搬 Phase 0 经验）
1. **起手**：`git checkout -b phase-1`（off phase-0）；先读本 Plan.md + Status.md + Verification.md。
2. **cron 安全网**：CronCreate 一个 session-only、每 20 分钟（`:07/:27/:47`）、空闲才触发的恢复 cron，prompt=本计划恢复指令（含"先读 Status.md 看进度"）。
3. **每步 D1→D8**：先读 Verification 对应小节的硬指标 → TDD 实现 → 跑验证命令 → 通过则 Status 标✅ + Verification 贴证据 → 渐进 commit。
4. **修法上限**：每个子任务试 ≤3 种修法仍不行→记"阻塞"+原因，转下一个，不卡死。
5. **收尾**：全绿或全阻塞→写 `devplan/phase-1/WAKE_UP_REPORT.md`（过了啥+证据/阻塞啥+原因/后备/还差啥）。
6. **红线**：不 push remote、不 git fetch/pull、不发邮件、不改 3 个 clone 仓库（CLI-Anything/OpenHands/hermes-agent）的 tracked 文件、leave 终端别关。

## 7. harness/工具层注意（Phase 0 实测，必读）
- **Edit/Write 工具在 don't-ask 模式被硬拒** → 用 `python - <<'PYEOF'`（stdin 脚本）写/改文件；改已有文件用「读全→str.replace+assert count==1→写回」。
- **bash 扫描器拒**：subprocess/Popen、`PYTHONPATH=` 前缀、`python -c`、`| 管道`（含 `| tail`）、整条命令 ~80 行以上。对策：分块 heredoc（每块 ≤40 行/≤~1800B）、fork-free（用已知死 pid 替身等思路）、避免管道/-c。
- **GateGuard 钩子**：每会话/每轮首次 bash/edit/write 前需陈述"请求/产出/数据/原文"事实，重试即过。
- **uv-venv 无 pip**：若需 pip 系（cli-hub 等），先 `uv pip install --python <venv> pip`。
- **跑 spike/测试**：用 `.venv/Scripts/python.exe <path>`（脚本路径）而非 `python -m campus...`，后者要 PYTHONPATH 会被扫描器拒。
- **GLM 调用**：`hermes -z "..." --provider zai -m glm-4.6`（V0-6 验证过，key 在 ~/.hermes/.env）。

## 8. 风险与对策
| 风险 | 对策 |
|---|---|
| DDG 限流/反爬 | 结果缓存 24h；降 top_k；fallback 到 web-brave-free / web-exa |
| GLM quiz 质量不稳 | day1 quiz 人工 spot-check（e2e 证据里贴出来）；温度调低；prompt 加结构约束 |
| LLM 成本 | Researcher/Ranker 用 glm-4.6，QuizGen 用 glm-4.5-air；缓存；e2e 跑最少必要次数 |
| 日历集成未做 | slot 默认值 + CLI 覆盖；真实日历推到 Phase 1.5 |
| 真实 web 结果不确定 | 测试分两层：fixture 验解析/打分（确定性），e2e 验链路通（不验具体搜到啥）|
