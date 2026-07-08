# Phase 6 Status（实时进度 — cron 读此文件续跑）

> 主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-6`（off `main` @ `ccf2221`）。
> 红线见 [Plan.md §4](./Plan.md)。证据见 [Verification.md](./Verification.md)。

## 基线
- ✅ phase-5 全量回归 **206 passed**。
- ✅ `phase-6` 分支已建。

## 进度
- ✅ T0 文档：Plan.md / Status.md / Verification.md 三件套
- ✅ T1 `campus/life/types.py`（CalendarEvent/Anniversary/Reminder/SecretaryLog dataclass）
- ✅ T2 `campus/life/calendar_store.py` + tests（L-CAL1/CAL2，16 passed）— CRUD + DAILY/WEEKLY 展开
- ✅ T3 `campus/life/anniversaries.py` + tests（L-ANN1/ANN2）— 双触发 + 跨年 + Feb29
- ✅ T4 `campus/life/reminders.py` + tests（L-REM1/REM2）— check_due + 幂等 send_due
- ✅ T5 `campus/life/secretary_log.py` + tests（L-LOG1）— DAILY_LOG 层首次被使用
- ✅ T6 `campus/life/engine.py` + tests（L-ENG1）— run_daily 全注入编排
- ✅ T7 `tests/life/test_full_e2e.py`（L-E2E）— 53 passed 全模块
- ✅ T8 onboarding 扩 birthday 字段 + 归一化 + 回归（L-OBD1，16 passed 无回归）
- ✅ T9 API 路由（calendar/anniv/daily_log）+ 后台提醒循环 + 测试（L-API1，14 passed）
- ✅ T10 前端 LifePage + api.ts + App.tsx（L-FE，npm run build 0 错）
- ✅ T11 全量回归 + 覆盖率 + Verification 收尾

## 最终结果（2026-07-08）
- **M6（生活基础）达成**。
- **268 passed**（phase-5 的 206 + phase-6 新增 62），无回归。
- `campus.life` 子系统覆盖率 **95%**，**每文件 ≥90%**（门槛 80%）。
- 前端 `npm run build` 0 错（33 modules）。
- 三个生活功能（日程 / 生日纪念日提醒 / 每日秘书日志）端到端可跑（CLI + API + 前端）。
- 证据详见 [Verification.md](./Verification.md)。

## 跑法
```
cd C:/Users/Lenovo/Desktop/your_secretary
student-secretary-agent/.venv/Scripts/python.exe -m pytest student-secretary-agent/tests/ student-secretary-agent/campus/demo_c/tests/ -q
# 覆盖率：
python -m pytest tests/ campus/demo_c/tests/ --cov=campus.life --cov-report=term-missing -q
# 前端：
cd frontend && npm run build
```

## 阻塞 / 决策日志
- 2026-07-08：开干。沿用 phase-3/4/5 决策「确定性优先」—— 时钟/推送/存储全注入，零网零模型。
- 2026-07-08：日历事件存独立 `~/.campus/calendar.json`（频繁增删+时间窗查询，比 FTS 记忆层合适）；生日/纪念日走 `PREFERENCES` 层；秘书日志走 `DAILY_LOG` 层（该层 phase-4 定义后首次被使用）。
- 2026-07-08：`create_app(start_scheduler=...)` 参数名与模块级 `start_scheduler` 函数冲突（参数遮蔽全局函数 → NoneType not callable）→ 改名 `with_scheduler`。模块级 `app` 默认 `with_scheduler=False`（导入不该启动线程）；生产显式 `create_app(with_scheduler=True)`。
- 2026-07-08：RRULE 只实现 DAILY/WEEKLY（覆盖课表），不引 dateutil；其它规则降级单次不崩。
