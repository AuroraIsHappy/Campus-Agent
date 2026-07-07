# Campus Skill 接入清单

> **接入机制**：Hermes 原生兼容 agentskills.io，`hermes skills install <identifier-or-URL>` 一条装上（落 `~/.hermes/skills/`，不入 git）；自写 campus skill 放本目录，经 `~/.hermes/config.yaml` 的 `skills.external_dirs` 挂载（入 git，curator-exempt）。发现 = 纯目录扫描，drop 进去 + `hermes reload-skills` 即可用。完整计划见 `~/.claude/plans/skill-skill-list-md-goal-md-skill-fizzy-cray.md`。

## 接入进度（2026-07-07）
| wave | skill | 状态 |
|---|---|---|
| 0 | find-skills | ✅ installed |
| 0 | skill-creator | ✅ installed |
| 0 | mcp-builder | ⛔ Hermes 安全扫描判 dangerous（误报但硬封），跳过待人工 vet |
| 0 | campus-demo-c（自写，本目录） | ✅ external_dirs 挂载，`-s` 加载验证通过（V1-8 关） |
| 1 | docx, pptx, xlsx, pdf | ⏳ 待装 |
| 2 | academic-search, read-arxiv-paper, firecrawl, html-ppt | ⏳ 待装（html-ppt 已有 local） |
| 2 | academic-researcher, academic-research-skills, parallel-deep-research | ⏳ 装后对比精简（5→3） |
| 2 | web-access | ⏳ 与 firecrawl 2 选 1 |
| 3 | obsidian, notion, graphipy, translate, travel-planner | ⏳ 待装 |
| — | tsinghua-learn | ⏸ deferred（第③类自定义，需学校 + 登录） |

> **GOAL.md 缺口**（后续 phase 补）：flashcard 生成 / 邮件草稿收发 / Zotero 文献管理。
> **冗余精简**：研究栈 5→3，web 抓取 2→1。

---

## meta-skills
1. find-skills: https://www.skills.sh/vercel-labs/skills/find-skills
2. skill-creator: https://www.skills.sh/anthropics/skills/skill-creator
3. mcp-builder: https://www.skills.sh/anthropics/skills/mcp-builder

## office-skills
1. pptx: https://www.skills.sh/anthropics/skills/pptx
2. pdf: https://www.skills.sh/anthropics/skills/pdf
3. docx: https://www.skills.sh/anthropics/skills/docx
4. xlsx: https://www.skills.sh/anthropics/skills/xlsx
5. html-ppt: https://www.skills.sh/lewislulu/html-ppt-skill/html-ppt
6. firecrawl: https://www.skills.sh/firecrawl/cli
7. web-access: https://www.skills.sh/eze-is/web-access/web-access
8. parallel-deep-research: https://www.skills.sh/parallel-web/parallel-agent-skills/parallel-deep-research

## learning-skills
1. graphipy: https://github.com/Graphify-Labs/graphify
2. academic-researcher: https://www.skills.sh/shubhamsaboo/awesome-llm-apps/academic-researcher
3. academic-research-skills: https://www.skills.sh/imbad0202/academic-research-skills/
4. academic-search: https://www.skills.sh/claude-office-skills/skills/academic-search
5. translate: https://www.skills.sh/jimliu/baoyu-skills/baoyu-translate
6. read-arxiv-paper: https://www.skills.sh/karpathy/nanochat/read-arxiv-paper
7. notion: https://www.skills.sh/intellectronica/agent-skills/notion-api
8. obsidian: https://www.skills.sh/mattpocock/skills/obsidian-vault

## Entertainment
1. travel-planner:https://www.skills.sh/ailabs-393/ai-labs-claude-skills/travel-planner

## Campus-Learning-Platform
1. 参考https://clawhub.ai/tomuiv/skills/tsinghua-learn的实现方式

