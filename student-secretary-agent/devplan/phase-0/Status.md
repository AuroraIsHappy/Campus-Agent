# Phase 0 Status（live tracker — 自主夜间执行）

> **Goal**：跑通 V0-1..6（见 Verification.md），证明 Odyssey 建在 Hermes Kanban 上可工作 + 可崩溃恢复。
> 这是给"醒来的我/用户"看的状态文件。每完成/阻塞一步就更新。

## 当前阶段
- 进行中：V0-3（kill→resume，最关键）
- ✅ 已完成：V0-1、V0-2

## 进度
| ID | 状态 | 备注 |
|---|---|---|
| setup | ✅ | phase-0 分支 + py3.13.12 venv；密钥移到 ~/.hermes/.env；.env.example 已清空 |
| V0-1 Hermes 安装 | ✅ | hermes-agent==0.18.0 via uv pip；`hermes --version`=v0.18.0；updater 仅手动 |
| V0-2 Kanban roundtrip | ✅ | att2 通过：assignee="default" → task `t_0ce2a4ec` status=done；spike exit 0。详见 Verification.md |
| V0-3 kill→恢复 | ⏳ | 最关键 |
| V0-4 CLI-Anything | ⏳ | |
| V0-5 QQ+飞书 | ⏳ | 密钥已就位 |
| V0-6 GLM 路由 | ⏳ | 密钥已就位 |

## 决策日志（自主判断记录在此，不叫醒用户）
- V0-2 att2 ✅：assignee="default" 重跑 `spike_kanban.py`，exit 0。create `t_0ce2a4ec` → dispatch_once(spawn_fn=inline_spawn) → worker claimed+complete → 行 status=done。证据见 Verification.md V0-2。（附注：旧 att1 残留 `t_2675603e`(tester/ready) 仍在 board，无害；`result` 列为 None，summary 落 metadata 而非 result 列；`task_runs` 表无 `run_id` 列，V0-3 需先查其真实 schema。）
- V0-2 att1：assignee="tester" → dispatch 判 `skipped_nonspawnable`（hermes 的 assignee 必须是真实 profile，`profile_exists()` 为真）。`hermes profile list` 显示有 `default` profile（model 未设，gateway stopped）。**已改 spike_kanban.py 用 assignee="default"，下个会话直接重跑。**
- V0-1：系统 Python 3.14 不兼容 Hermes (`<3.14`) → 用 uv 装 3.13.12 venv（`student-secretary-agent/.venv`）。`hermes-agent==0.18.0` 装好，`hermes --version` = v0.18.0。
- 密钥已移 `~/.hermes/.env`（GLM/QQ/飞书，gitignored）；`.env.example` 已清空。⚠️ 醒后 rotate 三把 key。
- **会话切换**：用户当前窗口切不到 bypass，要新开窗口继续。新窗口会加载 `.claude/settings.local.json` 里已加宽的 allowlist（uv/python/git/venv/pytest 等已允许）。session-only cron `9fcaf40b` 会随旧会话消亡，新会话需重新挂。

## 阻塞 / 转后备
- （无）

## 安全提醒
- 醒后 rotate GLM/QQ/飞书 三把 key（曾被明文写进 .env.example + 读进 transcript）。
