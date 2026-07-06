# Phase 0 Status（live tracker — 自主夜间执行）

> **Goal**：跑通 V0-1..6（见 Verification.md），证明 Odyssey 建在 Hermes Kanban 上可工作 + 可崩溃恢复。
> 这是给"醒来的我/用户"看的状态文件。每完成/阻塞一步就更新。

## 当前阶段
- 进行中：V0-1（Hermes 锁版本安装）

## 进度
| ID | 状态 | 备注 |
|---|---|---|
| setup | ✅ | Verification.md + Status.md 已建；密钥已移到 ~/.hermes/.env；.env.example 已清空 |
| V0-1 Hermes 安装 | 🔄 | 查 PyPI 包名 + 最新 stable |
| V0-2 Kanban roundtrip | ⏳ | |
| V0-3 kill→恢复 | ⏳ | 最关键 |
| V0-4 CLI-Anything | ⏳ | |
| V0-5 QQ+飞书 | ⏳ | 密钥已就位 |
| V0-6 GLM 路由 | ⏳ | 密钥已就位 |

## 决策日志（自主判断记录在此，不叫醒用户）
- （进行中填充）

## 阻塞 / 转后备
- （无）

## 安全提醒
- 醒后 rotate GLM/QQ/飞书 三把 key（曾被明文写进 .env.example + 读进 transcript）。
