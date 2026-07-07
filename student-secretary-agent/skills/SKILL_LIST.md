# Campus Skill 接入清单

> **接入机制**：Hermes 原生兼容 agentskills.io，`hermes skills install <identifier-or-URL>` 一条装上（落 `~/.hermes/skills/`，不入 git）；自写 campus skill 放本目录，经 `~/.hermes/config.yaml` 的 `skills.external_dirs` 挂载（入 git，curator-exempt）。发现 = 纯目录扫描，drop 进去 + `hermes reload-skills` 即可用。完整计划见 `~/.claude/plans/skill-skill-list-md-goal-md-skill-fizzy-cray.md`。

## 接入进度（2026-07-07，Wave 2+3 + html-ppt 安装后复核）
| wave | skill | 状态 |
|---|---|---|
| 0 | find-skills | ✅ installed |
| 0 | skill-creator | ✅ installed |
| 0 | mcp-builder | ⛔ Hermes 安全扫描判 dangerous（误报但硬封），跳过待人工 vet |
| 0 | campus-demo-c（自写，本目录） | ✅ external_dirs 挂载，`-s` 加载验证通过（V1-8 关） |
| 1 | docx, pptx, xlsx, pdf | ✅ installed（`skills list` 复核：4 个均 enabled） |
| 1 | html-ppt | ⛔ dangerous verdict（283 findings，含 `traversal` 主题 HTML `href` 重写），`--force` 不绕过；即此前 `skills list` 缺失之因 |
| 2 | academic-search | ✅ installed |
| 2 | read-arxiv-paper | ✅ installed |
| 2 | firecrawl | ❌ Could not fetch from any source（短 id + full URL 均失败，上游不可达） |
| 2 | academic-researcher | ✅ installed |
| 2 | academic-research-skills | ✅ installed（SAFE，多文件：py + data + skill-card） |
| 2 | parallel-deep-research | ⛔ caution verdict + 2 findings（含 `privilege_escalation` `Bash(parallel-cli:*)`），BLOCKED，未 --force |
| 2 | web-access | ✅ installed（firecrawl ❌ 后接管文档/网页抓取，CDP proxy） |
| 3 | baoyu-translate | ✅ installed（references + TS scripts） |
| 3 | notion-api | ✅ installed（block-types / filters / property references） |
| 3 | obsidian-vault | ❌ Could not fetch from any source（短 id + full URL 均失败，上游不可达） |
| 3 | travel-planner | ⛔ dangerous verdict（persistence：自动改 `~/.claude/settings.json`），`--force` 不绕过 |
| 3 | graphify | ⛔ dangerous verdict（17 findings，含 `supply_chain` pip-install），`--force` 不绕过 |
| — | tsinghua-learn | ⏸ deferred（第③类自定义，需学校 + 登录） |

> **本批小结（Wave 2+3：7 ✅ / 3 ⛔ / 2 ❌；另 html-ppt Wave1 ⛔）**：研究栈实装 academic-search / read-arxiv-paper / academic-researcher / academic-research-skills（4）；web-access 替代失败的 firecrawl；知识/生活实装 baoyu-translate / notion-api。⛔ 四项（html-ppt / parallel-deep-research / travel-planner / graphify）被 Hermes 安全扫描封（3 个 dangerous 硬封 + 1 个 caution 可 --force 但未绕），均未 --force。❌ 两项（firecrawl / obsidian-vault）上游 skills.sh 条目不可达，留人工复查或换源。

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

