# Wave 2 + Wave 3 自动安装 runbook

> 用途：在**新 Claude 窗口**里自动化安装剩余外部 skill。本文件 = 背景文档 + 可粘贴的提示词。
> 由 phase-1 会话于 2026-07-07 生成。

## 背景（状态快照）
- 仓库：`c:\Users\Lenovo\Desktop\your_secretary`，分支 `phase-1`。
- hermes 二进制：`/c/Users/Lenovo/Desktop/your_secretary/student-secretary-agent/.venv/Scripts/hermes.exe`（py3.13.12, hermes-agent 0.18.0）。
- 接入机制：`hermes skills install -y <identifier-or-URL>` → 落 `~/.hermes/skills/`（不入 git）。发现 = 纯目录扫描，无需注册。
- **`GITHUB_TOKEN` 已在 `~/.hermes/.env`**（Wave 1 时写入），hermes 自动加载 → 5000/hr，**不会撞 GitHub 速率限制**。
- 已装（Wave 0/1）：find-skills、skill-creator、docx、pptx、xlsx、pdf、html-ppt、campus-demo-c（自写，external_dirs 挂载）。
- ⛔ `mcp-builder` 已被 Hermes 安全扫描判 "dangerous" 硬封（误报但 `--force` 也不绕过）——**不要重试**。
- ⚠️ 本会话有 2 个 GitHub PAT 暴露在 transcript，装完 skill 后用户会 rotate。
- **GateGuard 钩子开启**：每轮首条 bash、每个文件首次 edit/write 前，需陈述"请求/产出/数据/原文"事实再重试（重试即过）。

## 待装清单（identifier = skills.sh URL 去掉前缀）
**Wave 2 · 科研/搜索**
- `claude-office-skills/skills/academic-search`
- `karpathy/nanochat/read-arxiv-paper`
- `firecrawl/cli`
- `shubhamsaboo/awesome-llm-apps/academic-researcher`（与研究类冗余，装后对比再定去留）
- `imbad0202/academic-research-skills`（冗余，装后对比）
- `parallel-web/parallel-agent-skills/parallel-deep-research`（冗余，装后对比）
- `eze-is/web-access/web-access`（与 firecrawl 2 选 1，都装后对比）

**Wave 3 · 知识库/生活**
- `jimliu/baoyu-skills/baoyu-translate`
- `intellectronica/agent-skills/notion-api`
- `mattpocock/skills/obsidian-vault`
- `ailabs-393/ai-labs-claude-skills/travel-planner`
- `Graphify-Labs/graphify`（⚠️ 原始 GitHub 仓、非 skills.sh；若 install 拉不到就记失败跳过，留人工处理）

## 验收口径
- 每个 skill：`hermes skills install -y <id>`（建议超时 300s；office/大 skill 体积大可能慢）。
- 安装后 `hermes skills list` 出现该名 = ✅。
- **不做** 逐个 `hermes -s <name> -z` 冒烟（控成本），只靠 `skills list` 确认。
- 安全扫描 "dangerous" → SKILL_LIST 标 ⛔，继续下一个，不卡。
- 全部跑完：更新 `student-secretary-agent/skills/SKILL_LIST.md` 顶部进度表 + `git commit`（**仅 SKILL_LIST.md**）。

---

## 📋 提示词（复制下面 --- 之间的整块到新窗口）

---
你在 `c:\Users\Lenovo\Desktop\your_secretary` 仓库（分支 phase-1）。任务：自动化安装剩余 Hermes 外部 skill（Wave 2 + Wave 3），更新清单，提交。先读本目录的 `WAVE_2_3_AUTORUN.md` 与 `SKILL_LIST.md` 获取完整背景。

环境：
- hermes 二进制：`/c/Users/Lenovo/Desktop/your_secretary/student-secretary-agent/.venv/Scripts/hermes.exe`
- `GITHUB_TOKEN` 已在 `~/.hermes/.env`（hermes 自动加载，不会撞 GitHub 速率限制）。
- GateGuard 开启：每轮首条 bash、每文件首次 edit/write 前陈述"请求/产出/数据/原文"事实再重试。

步骤：
1. 依次安装下列 skill（命令模板：`/c/Users/Lenovo/Desktop/your_secretary/student-secretary-agent/.venv/Scripts/hermes.exe skills install -y <id> 2>&1 | tail -8`，timeout 设 300000ms）。
   Wave 2：`claude-office-skills/skills/academic-search`、`karpathy/nanochat/read-arxiv-paper`、`firecrawl/cli`、`shubhamsaboo/awesome-llm-apps/academic-researcher`、`imbad0202/academic-research-skills`、`parallel-web/parallel-agent-skills/parallel-deep-research`、`eze-is/web-access/web-access`
   Wave 3：`jimliu/baoyu-skills/baoyu-translate`、`intellectronica/agent-skills/notion-api`、`mattpocock/skills/obsidian-vault`、`ailabs-393/ai-labs-claude-skills/travel-planner`、`Graphify-Labs/graphify`
2. 每个 skill 判定：输出含 `Installed: <name>` 或文件列表 → ✅；`dangerous verdict`/安全拦截 → ⛔（不可绕过，记录跳过，**勿用 --force**）；fetch error/其他 → ❌ 记原因，继续下一个，不卡死。
3. 全部跑完跑一次 `hermes skills list` 看最终状态。
4. 更新 `student-secretary-agent/skills/SKILL_LIST.md` 顶部"接入进度"表：Wave 2/3 各 skill 标 ✅/⛔/❌。
5. 提交：`git add student-secretary-agent/skills/SKILL_LIST.md && git commit -m "feat(skills): Wave 2+3 install — research + knowledge/life skills" -m "Co-Authored-By: Claude <noreply@anthropic.com>"`。**仅暂存 SKILL_LIST.md**；勿 git add 其他脏文件（`.claude/settings.local.json`、`DEMO_SCRIPT.md`、`__pycache__/*.pyc`、`CLI-Anything/`、`OpenHands/`、`hermes-agent/`）。
6. 最后输出汇总表（skill | wave | 结果 ✅/⛔/❌）。

不要：逐个 `hermes -s <name> -z` 冒烟（成本高）；重试 mcp-builder（已硬封）；改 SKILL_LIST.md 以外的 tracked 文件；push remote。
---
