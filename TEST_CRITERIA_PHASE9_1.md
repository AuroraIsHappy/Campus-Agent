# 通过标准 — Phase 9.1（PREFERENCES 注入 + LLM 强制 + README 补全）

## 任务1：PREFERENCES 每轮注入 + 定时维护

### 设计
当前 `_try_recall_memory` 用 RRF 检索 + token 预算打包，PREFERENCES 只是"可能被检索到"。
改为：PREFERENCES 层**每轮全量注入** prompt（因为它是用户长期偏好，量小且高价值），不走检索打分。

### 通过标准
- [ ] 新增 `load_preferences_block(memory) -> str`：全量读取 PREFERENCES 层，格式化为简洁 prompt 段
- [ ] `compose_reply` 调用 `load_preferences_block` **直接注入**（不经过 recall_layered 打分）
- [ ] `_default_agent_chat` 把 preferences_block 传入 compose_reply
- [ ] 调度器新增 `_maybe_maintain_preferences()`：每日定时清理过期/重复 PREFERENCES，保持状态新鲜
- [ ] PREFERENCES 注入有大小上限（如 2000 字符），超出截断并标注
- [ ] 验证：聊天回复中体现用户偏好（人格/专业/onboarding 信息）

## 任务2：去掉离线兜底，LLM 强制

### 设计
当前多处有 `if not real: 回退模板`。改为：LLM 未接入时**直接报错**，不留"不接 LLM 也能跑"的路径。

### 通过标准
- [ ] `/agent/chat` 在 LLM 未就绪时返回明确错误：`{"ok": false, "error": "LLM 未接入，请配置 GLM_API_KEY..."}`，不回退模板
- [ ] `compose_reply` 移除 `format_reply` 模板回退分支；LLM 不可用时抛异常或返回错误
- [ ] `_default_agent_run` / 各 demo pipeline 的 offline 分支保留（测试用），但聊天端点不走 offline
- [ ] 前端 Chat 组件在收到 `ok=false` 时显示错误提示（红色），引导用户配置 LLM
- [ ] `_maybe_daily_quiz` / quiz_grader 等定时任务：LLM 不可用时跳过并记日志，不静默回退
- [ ] 确定性测试仍能跑（测试注入 mock LLM，不受影响）

## 任务3：README 补 meta-agent + memory 机制

### 通过标准
- [ ] README 新增 "Meta-Agent" 章节：说明实现（分类→路由→Odyssey DAG→对抗辩论→验证）和功能
- [ ] README 新增 "Memory 多层机制" 章节：每层的存入/更新/检索规则
  - PREFERENCES：onboarding 写入 + auto-learn 更新 + 每轮全量注入 + 定时清理
  - TASK_LOG：agent run 写入 + nightly compress 沉积
  - KNOWLEDGE：demo_b KG 节点写入
  - DAILY_LOG：run_daily 写入 + 90 天保留
- [ ] README 更新启动说明：强调 LLM 必须接入
