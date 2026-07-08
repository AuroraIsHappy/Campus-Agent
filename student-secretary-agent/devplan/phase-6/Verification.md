# Phase 6 Verification

> 退出标准见 [Plan.md §4](./Plan.md)。运行器 = system python 3.14（+ conftest 补 hermes_cli）。

## 基线回归
- ✅ **268 passed**（phase-5 的 206 + phase-6 新增 62：life 53 + api 6 + meta_agent 3），无回归。

## L-* 验收证据

### 日历（campus/life/calendar_store.py）— L-CAL1/CAL2
- [x] **L-CAL1 CRUD**：`tests/life/test_core.py` — add 自动分配 `evt-N` + 持久化；update 合并 patch 并保留未触字段；delete 返回 bool；list 无窗口原样返回。**16 passed**。
- [x] **L-CAL2 RRULE 展开**：DAILY 7 天窗出 7 实例；WEEKLY 7 周窗出 7；start 早于窗口时按整步跳进（Jul 查 Jan-daily 出 3 实例）；unsupported rrule（MONTHLY）降级为单次不崩；list 窗口展开+排序+end 时长保持（Jul8 周实例 end=09:40）。`calendar_store.py` **96%**。

### 生日/纪念日（campus/life/anniversaries.py）— L-ANN1/ANN2
- [x] **L-ANN1 双触发**：`due_anniversaries(days_ahead=0)` 命中今天；`=1` 命中明天（heads-up）；去重由 engine 的 check_due 处理。
- [x] **L-ANN2 跨年**：今年已过 → next_occurrence 落次年；Feb-29 非闰年 → Feb-28；坏日期安全跳过不抛。`anniversaries.py` **90%**。

### 提醒（campus/life/reminders.py）— L-REM1/REM2
- [x] **L-REM1 check_due**：聚合今日事件 + 生日/纪念日（today-of + 明日 heads-up），kind 标注 EVENT/BIRTHDAY/ANNIVERSARY。
- [x] **L-REM2 send_due**：注入 push_fn → 每个 reminder 一次调用返回 receipt；**幂等**（同 id 同天第二次跳过）；新一天 dedup key 变化 → 重发。`reminders.py` **98%**。

### 秘书日志（campus/life/secretary_log.py）— L-LOG1
- [x] **L-LOG1**：build_log 汇总事件+任务+触发的纪念日提醒；write→get 走注入 MemoryPort（InMemoryStore）往返一致；recent_logs 按日期倒序 + 过滤非 daily: 键；to_markdown 三段式（标题/今日/明日）。`secretary_log.py` **95%**。

### 编排引擎（campus/life/engine.py）— L-ENG1
- [x] **L-ENG1 run_daily**：注入 stub → 读今日事件 + 全部纪念日 → 算到期 → 推送（幂等）→ 构建并写 DAILY_LOG；tasks 折入日志 entries；write_log=False 时只预览不落盘；today=None 默认 date.today() 不崩。`engine.py` **100%**。

### 全链路（tests/life/test_full_e2e.py）— L-E2E
- [x] **L-E2E**：建周课表 + 今日生日 → run_daily → 断言 push 被调（含「高数课」「小明」）+ DAILY_LOG 有记录且含两者；第二次同日 tick 幂等不重发；write_log=False 不落盘；push_fn=None 走默认 cli 不崩（无事件时）。

### onboarding 扩展（L-OBD1）
- [x] **L-OBD1**：`tests/meta_agent/test_core.py` — birthday 采集（"7月9日"→"07-09" 归一化）；`_normalize_birthday` 覆盖 MM-DD/M-D/YYYY-MM-DD/中文/空/垃圾；to_public_dict 导出 birthday+anniversaries；旧构造路径（无新字段）向后兼容。**16 passed**（13 原有 + 3 新增），无回归。

### API 路由 + 后台循环（L-API1）
- [x] **L-API1**：`tests/api/test_core.py` — `/calendar` GET/POST/DELETE、`/anniversaries` GET/POST、`/daily_log` GET、`/daily_log/run` POST 全 200 + schema 合法（注入真实 life 库 + InMemoryStore + 临时 calendar）；life 后端为 None 时路由优雅降级（空 shape 不 500）；`start_scheduler`/`stop_scheduler` 启停线程干净；`with_scheduler=True` 启动、模块级 app 默认不启。**14 passed**（8 原有 + 6 新增）。

### 前端（L-FE）
- [x] **L-FE**：`npm run build` **0 错**（tsc + vite build；33 modules；css 12.75kB + js 157.69kB；917ms）。LifePage 三区块（日程表单+列表 / 生日纪念日表单+列表 / 秘书日志+手动触发）；App.tsx 加「生活」导航项。

## 覆盖率（campus.life）
```
Name                            Stmts   Miss  Cover
campus\life\__init__.py             4      0   100%
campus\life\anniversaries.py       96     10    90%
campus\life\calendar_store.py     126      5    96%
campus\life\engine.py              33      0   100%
campus\life\reminders.py           56      1    98%
campus\life\secretary_log.py       59      3    95%
campus\life\types.py               78      2    97%
TOTAL                             452     21    95%
```
- [x] **COV**：每文件 **≥90%**（最低 anniversaries 90%，远超 80% 门槛）。
- [x] **BASE**：全量 **268 passed**，0 回归。

## M6 结论
- [x] 所有 L-* 验收项绿 → **M6（生活基础）达成**。
- 三个生活功能端到端可跑：CLI（`python -c "from campus.life import run_daily; ..."`）、API（`uvicorn campus.api.server:app`）、前端（LifePage）。
- 真实推送 / 真实飞书日历同步为后续 phase（留有适配器接缝，见 Plan §6）。
