# Phase 5 Verification

> 每完成一个 P5-* 验收项，贴证据（命令输出/产物路径/数字）。退出标准见 [Plan.md §5](./Plan.md)。
> 运行器 = conda `python`，`dangerouslyDisableSandbox` 勾选。

## 基线回归
- ✅ 140 passed（phase-4 全量，conda python + conftest 修）。

## P5 验收证据

### Demo B
- [ ] P5-DB1 抽取（B-F1）：`pytest tests/demo_b/test_core.py -k extract` 绿；抽取率 = __
- [ ] P5-DB2 知识图谱（B-F2）：build_kg 节点结构合法；edges 引用存在
- [ ] P5-DB3 资源检索（B-F3/Q1）：候选 ≥N；ranker 打分可解释
- [ ] P5-DB4 复习计划（B-F4/Q3）：覆盖到考；total_minutes ≤ free_minutes
- [ ] P5-DB5 quiz（B-F5）：≥1 题；judge 钩子可注入
- [ ] P5-DB6 次日调整（B-F6）：adjust_plan diff 非空方向正确
- [ ] P5-DB7 demo_b e2e：`pytest tests/demo_b/test_full_e2e.py` 绿；产物 plan.md/kg.json/quiz.json/Verification.md 齐

### API
- [ ] P5-API1：`pytest tests/api/test_core.py` 绿；6 路由 200 + schema 合法

### 前端
- [ ] P5-FE：`cd frontend && npm run build` 0 错；5 页面+皮肤齐

### 移动
- [ ] P5-MOB1 飞书真路径：mock subprocess → receipt.ok；命令含 `hermes send --to feishu:`
- [ ] P5-MOB2 QQ/企微端口：注入 sender → receipt；无凭证不抛

### 成本路由
- [ ] P5-COST1：`pytest tests/meta_agent/test_cost.py` 绿；分档+预算闸

### 覆盖率 & 回归
- [ ] P5-COV：`campus.{demo_b,api,mobile,meta_agent.cost}` 每文件 ≥80%
- [ ] P5-BASE：全量（现有 140 + 新增）全绿

### 文档
- [ ] P5-DOC：README（conda 运行器+pip+前端+移动开通+routing）+ requirements.txt

## M5 结论
- [ ] 所有 P5-* 绿 → M5（自动化层）达成。真实 LLM/真渠道 e2e 留用户手动验收。
