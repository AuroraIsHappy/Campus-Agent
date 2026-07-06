# Phase 0 验证指标（Verification）

> 每个 V0-x 必须有可跑出 pass/fail 的命令；通过后把证据追加到对应小节。
> 这是夜间自主执行的 definition of done——不靠主观判断，靠命令结果。

## 运行环境前置
- 分支：`phase-0`（单 worker，渐进 commit）。
- 密钥：已放 `~/.hermes/.env`（GLM/QQ/飞书）；`.env.example` 已清空。
- 模式：accept-edits + declared allowedPrompts；GateGuard 仍开（自带 facts 处理）。

---

## V0-1 Hermes 锁版本安装
- **命令**：确认 PyPI 包名 → `uv pip install <pkg>==<pin>`（pin = 最新 stable）。PyPI 无 → C4④ vendor submodule。
- **通过**：`hermes --version` 输出 pin 版本；自更新已关；`import hermes` 不报错。
- **证据**：版本号 + 自更新 setting + install 日志。
### 证据
```
（待填）
```
- 状态：⏳

---

## V0-2 Kanban roundtrip
- **命令**：`python -m campus.odyssey.spike_kanban`
- **通过**：`create_task→dispatch_once(spawn_fn)→kanban_complete` 跑通；`~/.hermes/kanban.db` tasks 表有一行 done + metadata。
- **证据**：`SELECT id,assignee,status,result FROM tasks` + spike stdout。
### 证据
```
（待填）
```
- 状态：⏳

---

## V0-3 kill→恢复（Odyssey 成立的硬证据，最关键）
- **命令**：`python -m campus.odyssey.spike_resume`
- **通过**：重启后 task 自动 reclaim 并 done；`task_runs` 有 ≥2 次尝试。
- **证据**：kill 前后 task_runs diff + 最终 status=done。
### 证据
```
（待填）
```
- 状态：⏳

---

## V0-4 CLI-Anything 工具调通
- **命令**：`cli-hub install <one>` → agent 调 `cli-anything-<x> --json`
- **通过**：调用并解析 JSON（≥1 字段命中）。
- **证据**：调用日志 + JSON 片段。
### 证据
```
（待填）
```
- 状态：⏳

---

## V0-5 QQ Bot + 飞书 gateway（密钥已就位）
- **命令**：`hermes gateway`
- **通过**：两渠道各收发一条测试消息。
- **证据**：gateway 日志 + 收发记录。
### 证据
```
（待填）
```
- 状态：⏳

---

## V0-6 模型路由（非 Anthropic，GLM）
- **命令**：写 `~/.campus/routing.yaml` → 跑 trivial agent turn
- **通过**：GLM 完成一轮；`model_override` 按角色生效。
- **证据**：provider 日志 + routing.yaml。
### 证据
```
（待填）
```
- 状态：⏳

---

## 总状态
- V0-1..6 全绿 = 成功；剩余全硬阻塞 = 停 → 写 WAKE_UP_REPORT.md。
