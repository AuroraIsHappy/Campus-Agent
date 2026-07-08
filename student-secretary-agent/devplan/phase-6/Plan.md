# Phase 6 Plan — 生活基础（Phase 1.5 补完）

> 补齐 IMPLEMENT.md 原规划的 Phase 1.5（被早期阶段跳过）：日程管理 + 生日/纪念日提醒 + 每日秘书日志。
> 这是 GOAL.md 三大卖点之一「状态持久化与个性化」的高频触点。
> 配套：[Status.md](./Status.md) · [Verification.md](./Verification.md)

## 0. 目标（/goal）

把校园秘书从「只会跑学术 Demo」升级为「记得你生日、管你的日程、每晚给你写小结」的真秘书。

三个子功能，复用已有地基（MemoryPort / push / onboarding）：

| 子功能 | 输入 | 输出 |
|---|---|---|
| **日程管理** | 用户添加事件（课表/会议/待办） | 本地日历（`~/.campus/calendar.json`），可查/可改/可按时间窗列出 |
| **生日/纪念日提醒** | onboarding 采集 + 随时添加 | 双触发（提前 1 天 + 当天）→ push 推送 |
| **每日秘书日志** | 当日事件 + 任务 + 提醒 | 汇总成 `SecretaryLog`，落 `DAILY_LOG` 记忆层（跨 session 可查）|

## 1. 设计原则（沿用 phase 1-5 范式）

1. **纯函数 + 注入 stub**：LLM / 推送 / 时钟全走注入点，测试零网零模型（同 demo_a/b、mobile、meta_agent）。
2. **复用优先**：
   - 存储 → 已有 `MemoryPort`（`PREFERENCES` / `DAILY_LOG` 层，DAILY_LOG 早已定义但无人用）。
   - 推送 → 已有 `campus.mobile.cli.push`。
   - 身份 → 扩到已有 `UserProfile`，新字段默认空，不破坏旧构造。
3. **薄 ports**：`campus/life/` 只依赖 `MemoryPort` / `PushPort` Protocol，不直接 import 具体后端。
4. **本地日历**：`~/.campus/calendar.json`，纯 JSON，零外部依赖；后续可加飞书/ICS 适配器（留接缝，不在本期）。
5. **时钟注入**：所有 `now` 走参数，纯函数内不直接调 `datetime.now()`（同 `ebbinghaus` 范式）。

## 2. 数据模型（campus/life/types.py）

```
CalendarEvent:  id, title, start (ISO), end (ISO), rrule (None|"DAILY"|"WEEKLY"),
                location="", note="", created_at
Anniversary:    id, name, date (MM-DD), kind ("birthday"|"anniversary"), note=""
Reminder:       event_id, due_at (epoch), message, kind ("event"|"anniversary")
SecretaryLog:   date (YYYY-MM-DD), summary, entries[], tomorrow[], created_at
```

纯 dataclass + `to_dict()` / `from_dict()`，无第三方依赖。

## 3. 关键设计决策

1. **RRULE 简化**：只实现 DAILY / WEEKLY（覆盖课表场景），不引 `dateutil`；其它规则标 `unsupported` 不崩（存原值，展开时跳过）。
2. **双触发**：`due_anniversaries(today, days_ahead)` 调用两次（`days_ahead=1` 和 `0`），按 id 去重。
3. **跨年**：生日按 MM-DD 匹配，忽略年份；next occurrence = `(this_year, M, D)` 若已过则 `(next_year, M, D)`。
4. **后台循环可关**：测试环境 `CAMPUS_DISABLE_SCHEDULER=1` 或 `create_app(start_scheduler=False)`，保证确定性。
5. **推送幂等**：同一 reminder 当天只发一次（`MemoryPort` 记 `sent:<date>:<id>` 去重键）。
6. **`MemoryPort` 用作生日存储**：生日/纪念日写 `PREFERENCES` 层（key=`anniv:<id>`）；秘书日志写 `DAILY_LOG` 层（key=日期）。日历事件单独落 `calendar.json`（结构化、频繁增删，比记忆层合适）。

## 4. 完成测试标准（Definition of Done）

| ID | 文件 | 验证项 | 通过判据 |
|---|---|---|---|
| L-CAL1 | tests/life/test_core | 日历 CRUD | add→list→update→delete；时间窗过滤命中 |
| L-CAL2 | tests/life/test_core | RRULE 展开 | WEEKLY 事件在 7 天窗内出 7 实例；DAILY 出 7；invalid 跳过不崩 |
| L-ANN1 | tests/life/test_core | 双触发 | days_ahead=1 命中明天生日；=0 命中今天；去重 |
| L-ANN2 | tests/life/test_core | 跨年 | 今年已过的生日 → next occurrence 落次年 |
| L-REM1 | tests/life/test_core | check_due | 聚合 calendar + anniv 到期项 |
| L-REM2 | tests/life/test_core | send_due | 注入 push_fn → receipts；幂等（同 id 当天不发两次） |
| L-LOG1 | tests/life/test_core | 秘书日志 | build_log 汇总事件+任务；write→get 走注入 MemoryPort |
| L-ENG1 | tests/life/test_core | run_daily | 注入 stub：提醒被发送 + 日志被写 DAILY_LOG |
| L-E2E | tests/life/test_full_e2e | 全链路 | 建事件+生日 → run_daily → push 被调 + DAILY_LOG 有记录 |
| L-OBD1 | tests/meta_agent/test_core | onboarding | birthday 采集 + to_public_dict 导出；旧用例无回归 |
| L-API1 | tests/api/test_core | 新路由 | /calendar /anniversaries /daily_log 200 + schema；循环关闭态不干扰 |
| L-FE | frontend/ | 前端 | `npm run build` 0 错；LifePage 三区块齐 |
| COV | `--cov=campus.life` | 覆盖率 | **每文件 ≥80%** |
| BASE | 全量 | 回归 | 现有 206 + 新增全绿（无回归）|

**退出标准**：L-* 全绿 + FE build 通过 + 覆盖率每文件 ≥80% + 回归无 → **M6（生活基础）达成**。

## 5. 构建顺序（TDD 渐进；RED→GREEN 每步）

1. **分支 + 三件套文档**（本文件 + Status + Verification 占位）。
2. **types**（dataclass，先定型）。
3. **calendar_store**（+ test）→ **anniversaries**（+ test）→ **reminders**（+ test）→ **secretary_log**（+ test）→ **engine**（+ test）。
4. **test_full_e2e**（全链路 stub）。
5. **onboarding 扩字段**（+ 补回归 test）。
6. **API 路由 + 后台循环**（+ 扩 test_core）。
7. **前端 LifePage + api.ts + App.tsx**（`npm run build` 绿）。
8. **全量回归 + 覆盖率 + Verification 落档**。

## 6. 不做（明确划线）

- 真实飞书 / ICS 日历同步（留适配器接缝，后续 phase）。
- onboarding 自动推荐 skill 逻辑变更（只加字段，不动 recommend）。
- 真实推送 e2e（沿用项目纪律：注入 stub 测试，真渠道留手动验收）。
- 复杂 RRULE（MONTHLY/UNTIL/COUNT 等，标 unsupported 不崩即可）。
