# Phase 1 验证指标（Verification）

> 每个 V1-x 必须有可跑出 pass/fail 的命令；通过后把证据追加到对应小节。
> 自主执行的 definition of done——不靠主观判断，靠命令结果。
> 跑法统一用脚本路径：`.venv/Scripts/python.exe <path>`（避免 PYTHONPATH 被扫描器拒）。

## 运行环境前置
- 分支：`phase-1`（off phase-0）。venv：`student-secretary-agent/.venv`（py3.13.12）。
- routing.yaml：`~/.campus/routing.yaml`（V0-6，GLM/zai）。web：web-ddgs（免费）。

---

## V1-1 types.py（数据形状）
- **命令**：`.venv/Scripts/python.exe -m pytest campus/demo_c/tests/test_core.py::test_types -v`
- **通过**：dataclass 构造、必填校验、枚举合法性全过。
### 证据
```
（待填）
```
- 状态：⏳

## V1-2 researcher.py（搜索 + 解析）
- **命令**：`.venv/Scripts/python.exe -m campus.demo_c.researcher "linux basics"`（或 `python <path>/researcher.py "linux basics"`）
- **通过**：返回 ≥3 个 Resource，每个含 title/url/source_type/provider/year；test_core 的 `parse_search_results` 用例全过（fixture 不联网）。
- **证据**：候选 JSON 片段 + pytest 输出。
### 证据
```
（待填）
```
- 状态：⏳

## V1-3 ranker.py（打分择优）
- **命令**：`.venv/Scripts/python.exe -m pytest campus/demo_c/tests/test_core.py -k rank -v` + 手跑 `rank()` 看输出
- **通过**：score 单调（启发式可复现）；top pick 带理由（GLM）；fixture 打分顺序确定。
### 证据
```
（待填）
```
- 状态：⏳

## V1-4 scheduler.py（30 天计划）
- **命令**：`.venv/Scripts/python.exe -m campus.demo_c.scheduler "MIT Missing Semester" --days 30`
- **通过**：Plan.days 长度=30；每天有 topic/est_minutes/date；产出 plan.md 可读。
### 证据
```
（待填）
```
- 状态：⏳
## V1-5 quiz.py（每日 quiz 生成）
- **命令**：`.venv/Scripts/python.exe -m campus.demo_c.quiz --topic "shell 基础"` 
- **通过**：Quiz 含 ≥1 QuizQuestion（q + answer + explanation）；test_core 的 `parse_quiz` 解析 LLM 文本为结构通过。
### 证据
```
（待填）
```
- 状态：⏳

## V1-6 memory.py（长期偏好 + 进度）
- **命令**：`.venv/Scripts/python.exe -m campus.demo_c.memory --remember "learning=linux"` 然后 `--show`
- **通过**：写入 ~/.campus/memory.json 后能读回；progress 追加幂等（同 day 重写不重复）。
### 证据
```
（待填）
```
- 状态：⏳

## V1-7 orchestrator.py（端到端，最关键）
- **命令**：`.venv/Scripts/python.exe -m campus.demo_c.orchestrator "我想学 Linux"`
- **通过**：exit 0；在 `~/.campus/runs/<ts>/` 落盘：plan.md（30 天）、quiz_day1.json（≥1 题）、research_candidates.json、progress.json、run_result.json。长期 memory 写入"learning=linux"。
- **证据**：目录 tree + plan.md 头部 + quiz_day1.json 片段。
### 证据
```
（待填）
```
- 状态：⏳

## V1-8 Hermes skill turn（agent 能调起）
- **命令**：`hermes -z "我想学 Linux" -s campus-demo-c`（或 `--skills campus-demo-c`）
- **通过**：agent 起来、调 skill、产出等价 artifact（plan + quiz）。至少证明 skill 被发现并触发 orchestrator。
### 证据
```
（待填）
```
- 状态：⏳

## 覆盖率
- `.venv/Scripts/python.exe -m pytest campus/demo_c/tests/ --cov=campus/demo_c --cov-report=term-missing` → ≥80%。

## 总状态
- V1-1..V1-8 全绿 + 覆盖率 ≥80% = Phase 1 通过；剩余全硬阻塞 = 停 → 写 WAKE_UP_REPORT.md。
- DEFERRED（不计入硬退出标准）：quiz 推送 QQ/飞书、手机答题、真实日历（待 V0-5 解封 / Phase 1.5）。
