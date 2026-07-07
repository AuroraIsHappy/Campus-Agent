# Phase 4 — 增强记忆 L4 + Meta-Agent L5 + 人格 L6（"专属秘书 + 5 分钟上手"）

> 执行者：自主会话（用户授权后离开 / 睡觉）。**工作目录 = 主仓 `C:/Users/Lenovo/Desktop/your_secretary/`，分支 `phase-4`（off `phase-3` @ `9d76eae`）。**
> 上游：[ACHITECHURE.md](../../ACHITECHURE.md) §4.3(L4)/§4.4(L5)/§4.6(L6)、[IMPLEMENT.md](../../IMPLEMENT.md) §Phase 4、[ACCEPTENCE_TESTS.md](../../ACCEPTENCE_TESTS.md) §4 S-MEMORY/S-ONBOARD/S-MODELCONFIG/S-PERSONA + §5 测试映射。
> 续跑：cron 读 `Status.md`，从未完成第一个 ⏳ 续；每完成一项标 ✅ + 贴证据。

## 0. 目标与范围（= /goal）

**目标**：把"好用"升级为"专属秘书"——**多层结构化记忆（跨 session 召回）+ 非 CS 用户 5 分钟 onboarding + 角色→模型路由可配 + 人格层**。里程碑 **M4（个性化 + 低门槛上手）**。

**验收北极星**（IMPLEMENT.md 退出标准 + ACCEPTENCE S-*）：
- **S-MEMORY**：跨 session 记忆召回——新 session 记得用户专业/在学课程/机构库。
- **S-ONBOARD**：非 CS 用户 5 分钟完成 onboarding 并跑通一个 Demo（确定性 e2e 证流程可达）。
- **S-MODELCONFIG**：`routing.yaml` 可编辑 + 至少一家**非 Anthropic** provider 可跑通。
- **S-PERSONA**：人格风格一致（费曼/鲁迅/默认）。

### IN（本期做）
- `campus/memory/`（L4）：多层 schema + ports + InMemory/JsonFile 双实现 + 向量(HashEmbedder)+FTS 双通道召回 + Ebbinghaus 复习引擎 + 压缩/遗忘。
- `campus/personas/`（L6）：费曼/鲁迅/默认人格 + apply 风格注入。
- `campus/meta_agent/`（L5）：onboarding 向导 + routing 生成/校验 + skill pack(≥100) + skill 发现/可靠性评分 + Meta-Agent 编排（classify/recommend/build_dag）。
- `tests/{memory,personas,meta_agent}/{test_core,test_full_e2e}.py`，子系统覆盖率 ≥80%。

### OUT（不在本期）
- 真实 embedding API 接入（本期用确定性 HashEmbedder 证双通道；真模型走 EmbedderPort 注入，留打磨）。
- 真实 cron 实装到 Hermes（本期纯函数 `next_review/due_items` + 调度器接口；接线留 Phase 5）。
- 前端 onboarding UI（L7，Phase 5）；本期是后端流程 + CLI/确定性 e2e。

## 1. 依赖（已就绪）
- Phase 3 全绿（84 tests / 91%）：`campus/runtime/{ports,llm_turn,hermes_kanban,in_memory}`、`campus/{odyssey,orchestrator,profiles,demo_a,demo_c}` ✓。
- 复用模式：`KanbanPort` Protocol + `InMemoryKanban`（ports.py 范式）；`demo_c/_llm.py::extract_json/ask_llm`（onboarding/LLM 接缝）；`profiles/loader.py::resolve(role)`（routing 已消费）。
- `~/.campus/routing.yaml`（schema 1，已存在，loader 已读）+ `~/.hermes/.env`（GLM key）✓。
- 主仓 `.venv`（hermes-agent==0.18.0, pyyaml, coverage, python-docx/pptx/openpyxl）✓；本期**无新依赖**（纯 stdlib + pyyaml）。

## 2. 架构（薄 ports + 纯函数 + 双实现，对齐 §C4②）
```
campus/memory/                # L4
├── __init__.py
├── types.py          # MemoryRecord / MemoryLayer 常量 / Recall / MemoryError
├── ports.py          # MemoryPort / EmbedderPort / RetrieverPort Protocol（纯，无三方依赖）
├── embedding.py      # HashEmbedder（确定性，locale 稳定）+ cosine_sim + rank
├── in_memory.py      # InMemoryStore(MemoryPort)：FTS(关键词)+vector(cosine) 双通道召回
├── json_store.py     # JsonFileStore(MemoryPort)：持久化 ~/.campus/memory.json（跨 session）
├── ebbinghaus.py     # next_review(history,now)/due_items/schedule（纯遗忘曲线）
└── compress.py       # compress(old,summarizer)->sediment + prune(retention_window)（注入 summarizer）

campus/personas/              # L6
├── __init__.py
├── types.py          # Persona dataclass（name/style_prompt/examples）
├── builtins.py       # feynman / lu_xun / default（风格指令 + 语气示例）
└── loader.py         # load_builtins / select(name) / apply_to_prompt(persona, base)

campus/meta_agent/            # L5
├── __init__.py
├── types.py          # UserProfile / SkillEntry / RoutingConfig / ClassifyDecision
├── skill_pack.py     # 内置 manifest（>=100 skill，标 source/installed/maintained）+ loader
├── skill_discovery.py# SkillRegistry + discover(need)->ranked + reliability_score + pick_mode
├── routing.py        # generate_routing(profile,providers)->dict / write_routing(path) / validate_routing
├── onboarding.py     # OnboardingWizard(ask=fn)->UserProfile（NL 采集身份/专业/人格/provider key）
└── meta_agent.py     # classify(task) short|long / recommend_skills / build_dag（串 memory+routing+discovery）

tests/
├── memory/{test_core,test_full_e2e}.py
├── personas/test_core.py
└── meta_agent/{test_core,test_full_e2e}.py
```

**关键取舍**：
- **纯 ports 优先**：memory/personas 全部纯 stdlib，单测无需 Hermes/网络。Embedder/Summarizer/ask 都是注入点，确定性测试注入 stub。
- **双通道召回可降级**：向量（HashEmbedder，确定性）+ FTS（关键词）。无 embedding 模型时退化为纯 FTS（双通道保留，证接口）。
- **跨 session 用 JsonFileStore 证**：InMemoryStore 证逻辑，JsonFileStore（落 `~/.campus/memory.json`，temp file 测）证 S-MEMORY 真持久化。
- **routing 复用现有**：loader.resolve 已读 routing.yaml；本期补 **生成器+校验器**（S-MODELCONFIG：可写可校验，至少一家非 Anthropic）。
- **skill pack 诚实标注**：manifest 每条带 `installed/maintained`，可靠性评分据此——是"目录"非"已装二进制"。

## 3. 数据模型要点
- `MemoryRecord`：`id, layer(PREFERENCES/TASK_LOG/TASK_BOARD/KNOWLEDGE/DAILY_LOG), key, content, metadata, created_at(ts int), embedding?`。
- `MemoryPort`：`remember(layer,key,content,metadata)->id`、`recall(query,layers=(),k=5,mode='hybrid')->list[Recall]`、`get(layer,key)`、`list_layer(layer)`、`forget(id)`、`all()`。
- `EmbedderPort`：`embed(text)->list[float]`、`dim:int`。
- `Ebbinghaus`：间隔序列 `[(1,'d'),(3,'d'),(7,'d'),(16,'d'),(35,'d')]`（SM-2 简化）；`next_review(reps, last_ts, now_ts)->due_ts`；`due_items(items, now_ts)`。
- `UserProfile`：`identity, major, year, persona, provider_keys:dict, recommended_skills, constraints`。
- `RoutingConfig`：`schema, default{provider,model}, roles{role:{provider,model}}`（兼容现有 routing.yaml）。
- `SkillEntry`：`name, source(hemes|cli_anything|campus), category, installed:bool, maintained:bool, description`。
- `Persona`：`name, style_prompt, examples:list[str]`；`apply_to_prompt` 把 style_prompt 注入 base system prompt。

## 4. 关键设计决策
1. **确定性优先**（沿用 phase-3 决策 1）：所有 LLM/embedding/网络走注入点；`test_*` 注入 stub，无 Hermes/无网/无真模型。真模型跑留 CLI/打磨。
2. **HashEmbedder 确定性**：`dim=128`，分词后 hash→桶累加 ±1，L2 归一化。同文本同向量（无 Math.random / 不依赖 Date）。cosine 召回可复现。
3. **Ebbinghaus 纯函数**：不触 cron；`schedule(items, now)->[(item,due_ts)]` 给上层落 cron 用。可测：连续答对间隔翻倍、答错归零。
4. **compress 不幻觉**：summarizer 是注入的纯函数（默认=`取 metadata.summary 否则截断 content`）；不调真 LLM 摘要（留打磨）。prune 按 `retention_window` 删旧，保留 `pinned`。
5. **routing 不绑厂商**：generator 从 `provider_keys` 推默认（任意一家非 Anthropic 即满足 S-MODELCONFIG）；validator 校 schema + provider 非空 + model 非空。
6. **onboarding 可测**：`OnboardingWizard(ask=lambda q: canned[q])` 全流程产 UserProfile；确定性 e2e 证 5-min 流程可达（S-ONBOARD 自动化部分）。

## 5. 完成测试标准（Definition of Done）
| ID | 文件 | 验证项 | 通过判据 |
|---|---|---|---|
| P4-M1 | tests/memory/test_core | 多层 schema | InMemoryStore 五层分离；remember/recall 按 layer 命中 |
| P4-M2 | tests/memory/test_core | FTS+向量双通道 | 关键词召回排序；HashEmbedder cosine 召回；hybrid 合并 |
| P4-M3 | tests/memory/test_full_e2e | 跨 session（S-MEMORY） | JsonFileStore：写→新实例→recall 命中（temp file） |
| P4-M4 | tests/memory/test_core | Ebbinghaus 节点 | next_review 间隔序列；due_items@t；答对递增/答错归零 |
| P4-M5 | tests/memory/test_core | 压缩/遗忘 | 老 record→sediment 偏好；window prune；pinned 保留 |
| P4-P1 | tests/personas/test_core | 人格内置 | feynman/lu_xun/default 存在；apply 注入 style |
| P4-P2 | tests/personas/test_core | S-PERSONA | apply 后 prompt 含风格标记（费曼=启发式/鲁迅=犀利） |
| P4-MA1 | tests/meta_agent/test_core | skill pack | manifest 载入，**>=100** 条，schema 合法，installed/maintained 齐 |
| P4-MA2 | tests/meta_agent/test_core | skill 发现 | discover(need) 排序；reliability_score；pick_mode |
| P4-MA3 | tests/meta_agent/test_core | routing（S-MODELCONFIG） | generate/write/validate；至少一家非 Anthropic provider |
| P4-MA4 | tests/meta_agent/test_core | onboarding | wizard(ask=canned)→UserProfile（identity/major/persona/keys 齐） |
| P4-MA5 | tests/meta_agent/test_core | Meta-Agent | classify short/long；recommend_skills；build_dag（角色 parents 串） |
| P4-MA6 | tests/meta_agent/test_full_e2e | S-ONBOARD+S-MEMORY | 非 CS onboarding→profile→routing→skills→persona→跨 session 召回（确定性） |
| COV | `--cov` | campus.{memory,personas,meta_agent} | **每文件 >=80%** |

**退出标准**：P4-M*/P4-P*/P4-MA* 全绿 + 覆盖率每文件 ≥80% → M4（自动化层）。真实 LLM/embedding/cron 接线留 Phase 5 打磨（同 phase-3 决策 1）。

## 6. 构建顺序（TDD，渐进；RED→GREEN 每步）
1. **memory**：M-T1 types+ports → M-T2 embedding+in_memory(FTS+vector) → M-T3 json_store(跨session) → M-T4 ebbinghaus → M-T5 compress → M-T6 memory e2e。
2. **personas**：P-T1 types+builtins+loader+apply → P-T2 test。
3. **meta_agent**：MA-T1 skill_pack(≥100) → MA-T2 discovery → MA-T3 routing → MA-T4 onboarding → MA-T5 meta_agent → MA-T6 e2e。
4. **收尾**：V-T1 coverage（每文件 ≥80%）→ V-T2 Verification.md/Status.md 落档。

## 7. harness 注意（沿用 phase-2/3）
- **工作在主仓**（分支 phase-4）；worktree 勿用。
- **Write 工具**：每新文件 GateGuard 首写拦——陈述事实（importers/API/data/原话指令）+ 重试即过。
- **bash**：扫描器拒 `python -c` / `|` 管道 / heredoc——用 Write 工具；跑测试用绝对 venv python（`.venv/Scripts/python.exe`）。
- **跑测试**：`git -C <repo> ` 操作；pytest 用 `student-secretary-agent/.venv/Scripts/python.exe -m pytest student-secretary-agent/tests/<sub>/ -q`（从 repo 根，或 cd 进子目录）。
- **/loop 续跑**：session-only cron（idle 触发）读 `Status.md` 续；acceptance 全绿后删 cron。
- **红线**：不 push remote、不改 hermes-agent/OpenHands/CLI-Anything 三仓 tracked 文件、不用 `--dangerously-skip-permissions`、别关终端。
