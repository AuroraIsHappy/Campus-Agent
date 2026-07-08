# Phase 8 交付报告 — Campus-Agent v0.8.0

> 上线冲刺完成。本报告覆盖代码实现、功能描述、落地状态与手动测试方式。

## 一、总览

从 Phase 7 的「本地产品闭环」升级到「可分发的开源自托管」。10 个 Step 全部完成,296 个确定性测试通过,6 个真实 LLM 集成测试验证通过(真实 GLM key),前端 typecheck 0 错误,tag `v0.8.0`。

**关键约束已解决**:`hermes-agent` 不在 PyPI,官方方式是 `git clone` + `uv pip install .`。Dockerfile 照此构建(多阶段:clone hermes → 装 campus → 构建前端 → 运行)。

---

## 二、代码实现与功能描述

### Step 0 — Phase 7 收尾
- **Ebbinghaus 遗忘曲线**:`campus/phase7.py` 的 `_ebbinghaus_due` / `_seed_review_nodes` / `quiz_daily` / `advance_review_node`。flashcard 生成时自动种入复习节点(1/3/7/16/35 天间隔),`POST /learning/quiz/daily` 从到期节点生成 quiz,`quiz_grade` 通过 `review_node_id` 推进曲线。
- **文档导出状态**:`GET /club/export_status` 报告 docx/pptx/xlsx/pdf 库可用性。
- **面试练习/反思**:`POST /career/interview/practice`(STAR 评分 + 模型答案大纲 + 追问)+ `POST /career/interview/reflect`(反思日志)。
- **文档**:`devplan/phase-7/Status.md` + `Verification.md`。

### Step 1 — Multi-agent 接线
- **MetaRunner**(`campus/meta_agent/runner.py`):`MetaAgent.classify` → `build_dag` → `Orchestrator.create_task` → `Supervisor.run_debate`。长程任务走 8 角色 DAG(Planner↔Critic / Writer↔Reviewer 对抗辩论),短任务走单节点。
- **`/agent/run` 接入**:real/auto + 长程 → MetaRunner 多智能体;offline 保持关键词路由(向后兼容)。
- **Onboarding 接线**:`/onboarding` 调用真实 `OnboardingWizard`,生成 profile 写入 PREFERENCES 记忆。
- **Memory 注入**:`build_role_prompt` 接受 `memory_snippet`,角色生成时看到用户偏好/历史。

### Step 2 — Memory 分层检索
- **统一 store**:修复 `demo_c/memory.py` 与 `JsonFileStore` 的 `~/.campus/memory.json` 冲突(不同 schema 互相覆盖)——demo_c 现委托 L4 PREFERENCES 层。
- **分层检索策略**(`campus/memory/recall_strategy.py`):
  - PREFERENCES:全量注入(小、高价值)
  - TASK_LOG:按 task_id scope 再 relevance 排序
  - KNOWLEDGE:RRF top-k
  - DAILY_LOG:按日期 recent N
  - TASK_BOARD:结构化(不注入 prompt)
- **RRF 融合**:替换 FTS+vector 原始求和为 Reciprocal Rank Fusion(1/(k+rank))。
- **Recency decay**:30 天半衰期 + pinned boost(x1.5) + min-score 阈值。
- **Token 预算打包**:pinned 优先,填满 budget,低优先级截断。
- **Nightly compress cron**:`_maybe_compress_memory` 每日一次,沉淀旧 TASK_LOG/DAILY_LOG 到 PREFERENCES,prune 90 天以上。

### Step 3 — 真实 LLM 端到端
- **`campus/runtime/workflow_llm.py`**:五域(learning/research/life/club/career)LLM prompt 模板,请求结构化 JSON 输出。
- **phase7 mode 透传**:flashcards/quiz/github_trending/meeting_minutes/recruiting_copy/email_draft/travel_plan/interview_plan 全部接受 `mode` 参数,real/auto 走 LLM,失败降级到确定性模板。
- **Integration 测试**:`tests/integration/test_real_llm_workflows.py`(`@pytest.mark.integration`,默认 skip)。

### Step 4 — Auto-learn
- **CorrectionStore**(`campus/meta_agent/auto_learn.py`):持久化 JSON 存储 user corrections。
- **SkillCreator**:在 `skills/<name>/SKILL.md` 创建/更新 skill(符合 Hermes 格式,registry 自动发现)。
- **AutoLearner**:回顾 correction → 按域聚类 → LLM 分类(preference/skill-defect/fact)→ 写入 PREFERENCES 记忆或创建 skill 或写入 KNOWLEDGE。offline 有启发式 fallback。
- **API**:`POST /agent/runs/{id}/correction`、`GET /agent/corrections`、`POST /admin/auto-learn`、`GET /agent/skills`。
- **Nightly job**:`_maybe_auto_learn` 每日一次(day-dedup guard)。

### Step 5 — 移动端真实推送
- **QQ Bot API**(`campus/mobile/qq_bot_api.py`):OAuth access_token + 发消息到 channel/group。`QQBotPusher` 默认 sender 自动使用(env 配置时)。**已用真实 key 验证 auth 通过**。
- **Feishu 健康自检**:`campus/mobile/feishu.py:health_check()` 报告 config + hermes binary readiness。
- **`/settings/status`**:mobile 部分从 env bool 升级为真实健康检查(feishu/qq 各自 ok/auth/offline)。

### Step 6 — Notion + 搜索 provider
- **Notion 兼容**:`NOTION_INTEGRATION_TOKEN`(官方 env 名)+ `NOTION_DATABASE_ID`。`list_notes()` 双向(查 Notion database,fallback 到本地 Markdown)。`GET /notes/notion/list`。
- **搜索 provider**(`campus/research/search_providers.py`):Tavily web search(`TAVILY_API_KEY`)+ GitHub Search API(`GITHUB_TOKEN`,按 stars 排序)。`github_trending` real 模式优先用 GitHub API。**已验证返回真实仓库**(NousResearch/hermes-agent 211k★)。

### Step 7 — 可分发包
- **Dockerfile**(多阶段):hermes clone+build → campus deps → frontend build → runtime。HEALTHCHECK + VOLUME + EXPOSE。
- **docker-compose.yml**:campus 服务 + volume + env_file + healthcheck。
- **`.env.example`**:全部 env 变量文档化(全部可选)。
- **跨平台脚本**:`scripts/start.sh`(Linux/macOS)+ 修好的 `start_demo.ps1`(去掉 `D:\Anaconda` 硬编码)。
- **生产前端**:`server.py` mount `frontend/dist` 为 StaticFiles(html=True)。
- **CORS**:`CAMPUS_CORS_ORIGINS` 可配。
- **Logging**:`logging.basicConfig` + 关键路径打日志。
- **`/docs` prod 关闭**:`CAMPUS_ENV=prod` 时禁用 Swagger/Redoc。
- **`/health` 升级**:readiness check(CAMPUS_HOME 可写探测)。
- **CI**:`.github/workflows/ci.yml`(pytest + ruff + typecheck)。

### Step 8 — 真实任务验收
- 8 项真实任务全部通过(见 `Verification.md`)。
- S-* 系统验收逐条核验(10/10 ✅)。
- M5 发布门槛达成。

### Step 9 — Agent 名称 + 前端美化
- **`/agent/name` API**:`GET`/`POST`,持久化到 `state/agent_config.json`。
- **App.tsx**:分组导航(概览/任务域/系统/引导)+ section header + 动态 agent 名称 + gradient avatar + max-width 内容容器 + shadow on active nav。
- **SettingsPage**:agent 名称编辑器 + auto-learn 手动触发面板 + 移动健康详情(✅/⚪/⚠️ per channel)。
- **api.ts**:新增 interviewPractice/interviewReflect/quizDaily/exportStatus/submitCorrection/listCorrections/triggerAutoLearn/listAutoSkills/getAgentName/setAgentName/notionList。

---

## 三、测试统计

| 套件 | 数量 | 状态 |
|---|---|---|
| 默认(deterministic) | 296 passed | ✅ |
| Integration(real GLM) | 6(默认 deselected) | ✅ verified |
| 前端 typecheck | 0 errors | ✅ |
| 真实任务验证 | 8 tasks | ✅ all passed |

---

## 四、手动测试方式

### 方式 1:Docker(推荐,生产用)

```bash
cd student-secretary-agent
cp .env.example .env          # 填入你的 key(全部可选)
docker compose up -d           # 构建并启动
# 打开 http://localhost:8000
# 健康检查:curl http://localhost:8000/health
```

### 方式 2:本地开发(Windows)

```powershell
cd student-secretary-agent
# 1. 装 Python 依赖
python -m pip install -r requirements.txt
# 2. 装 hermes-agent(不在 PyPI)
git clone https://github.com/NousResearch/hermes-agent.git ../hermes-agent
cd ../hermes-agent && pip install -e . && cd ../student-secretary-agent
# 3. 配 key(可选,不配走离线)
# 把 GLM_API_KEY 等写入 ~/.hermes/.env
# 4. 启动
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo.ps1
# 前端: http://127.0.0.1:5173  API: http://127.0.0.1:8000
```

### 方式 3:本地开发(Linux/macOS)

```bash
cd student-secretary-agent
pip install -r requirements.txt
git clone https://github.com/NousResearch/hermes-agent.git ../hermes-agent
cd ../hermes-agent && pip install -e . && cd ../student-secretary-agent
bash scripts/start.sh
```

### 手动验证清单

```bash
# 1. 健康 + 就绪
curl http://127.0.0.1:8000/health
# 期望: {"ok":true,"ready":true,"version":"0.8.0"}

# 2. 设置状态(看 LLM/mobile/GitHub readiness)
curl http://127.0.0.1:8000/settings/status

# 3. 真实 LLM flashcards(需 GLM key)
curl -X POST http://127.0.0.1:8000/learning/flashcards \
  -H "Content-Type: application/json" \
  -d '{"topic":"操作系统","count":3,"mode":"real"}'
# 期望: source_mode=real_llm, 3 张真实 flashcards

# 4. 真实 GitHub trending(需 GITHUB_TOKEN)
curl -X POST http://127.0.0.1:8000/research/github/trending \
  -H "Content-Type: application/json" \
  -d '{"topic":"LLM agent","mode":"real"}'
# 期望: source_mode=real_github_api, 真实仓库

# 5. Agent 名称
curl -X POST http://127.0.0.1:8000/agent/name \
  -H "Content-Type: application/json" -d '{"name":"小秘"}'
curl http://127.0.0.1:8000/agent/name
# 期望: {"ok":true,"name":"小秘"}

# 6. Auto-learn
curl -X POST http://127.0.0.1:8000/agent/runs/run_1/correction \
  -H "Content-Type: application/json" \
  -d '{"run_id":"run_1","domain":"learning","original":"wrong","corrected":"prefer detailed","reason":"test"}'
curl -X POST "http://127.0.0.1:8000/admin/auto-learn?use_llm=false"
# 期望: processed=1, preferences_written=1

# 7. Ebbinghaus daily quiz
curl -X POST http://127.0.0.1:8000/learning/flashcards \
  -H "Content-Type: application/json" -d '{"topic":"OS","count":3}'
curl -X POST http://127.0.0.1:8000/learning/quiz/daily \
  -H "Content-Type: application/json" -d '{"topic":"OS","count":5}'
# 期望: 从 review nodes 生成 quiz

# 8. 面试练习
curl -X POST http://127.0.0.1:8000/career/interview/practice \
  -H "Content-Type: application/json" \
  -d '{"role":"后端实习生","question":"介绍项目","answer":"做了一个系统"}'
# 期望: score + rubric + improvement_cues

# 9. 跑测试
python -m pytest -q                          # 默认套件(296 passed)
.venv/Scripts/python.exe -m pytest tests/integration/ -m integration -v  # 真实 LLM(需 key)
cd frontend && npm run typecheck             # 前端类型检查
```

### 前端验证

打开 `http://127.0.0.1:5173`(本地)或 `http://localhost:8000`(Docker):
1. 侧边栏:分组导航,顶部显示 agent 名称(可在设置页改名)
2. 仪表盘:profile/task count/run count/LLM/skills/Notion 状态卡片
3. 设置页:agent 名称编辑 + auto-learn 触发 + 移动健康详情(✅/⚪/⚠️)
4. 学习页:flashcards/quiz/deadlines/dashboard(Ebbinghaus review nodes)
5. 科研页:idea digest/GitHub trending/format check/Notion sync
6. 各域功能页:生活/社团/职业全部可用

---

## 五、已知限制(后续迭代)

1. **Hermes FTS5 backend**:当前用 JSON + HashEmbedder(单用户够用);架构愿景是切 Hermes FTS5,留作后续。
2. **Multi-agent 短任务**:short 任务仍走单节点;可扩展为轻量多角色。
3. **Notion database**:需用户手动创建 Notion database 并配 ID(token 已兼容)。
4. **QQ Bot 消息发送**:auth 已验证;实际发消息需 channel/group 在沙箱或上线环境。
5. **真实任务验收的 LLM 成本**:integration 测试默认 skip,手动跑时注意成本。

---

## 六、Git 信息

- 分支:`phase8`(从 `phase7` 切)
- Tag:`v0.8.0`
- 12 个 commit(Step 0-9 + 清理)
- 296 default tests + 6 integration tests + 0 typecheck errors
