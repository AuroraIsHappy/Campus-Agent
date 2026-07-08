# Phase 7 — GOAL 功能闭环 Sprint

## Summary

当前已完成：Demo A/C offline 可跑、科研 digest + 本地 Markdown 笔记、前端 Demo 中心、skill vendoring、真实 LLM readiness、启动/冒烟脚本，并已提交 `30d8c23 feat(demo): ship usable campus demo loop`。

Phase 7 的目标是尽快对齐 `GOAL.md`：在不依赖 Notion、移动渠道、GitHub/search provider 等外部 key 的前提下，把代码层面功能基本做全。外部应用本阶段只要求 adapter、readiness、mock/local fallback 和可测试接口；真实 key 后续单独配置和验收。

## Current Gap Against GOAL.md

- **统一入口不足**：目前用户仍需要知道 Demo A/B/C 或具体模块，缺少一句自然语言进入任务的秘书入口。
- **Demo B 与学习功能未完全产品化**：讲义扫描、KG、计划已有基础，但 flashcard、deadline、Ebbinghaus daily quiz、答题反馈调整计划、学习时间排程还未在 API/frontend 形成闭环。
- **记忆与任务状态未贯穿全局**：`/memory`、`/tasks` 默认后端仍偏空；长程任务没有统一 `RunStore/TaskStore/ArtifactStore`。
- **生活/社团/职业功能缺前端与 API 闭环**：日程/纪念日/日志有基础，健康、旅行、校园办事、会议纪要、招新文案、实习岗位、面试计划还未成型。
- **科研仍是 v1 adapter**：已经有 digest/note path，但还需要 idea research、专题跟踪、GitHub 热门项目、会议/期刊格式检查。
- **设置与集成状态分散**：LLM、skills、Notion、移动推送、GitHub/search provider readiness 需要统一到设置页和 `/settings/status`。

## Key Changes

### 1. Unified Agent Entry

- Add `POST /agent/run` for natural-language task creation.
- Add `GET /agent/runs` and `GET /agent/runs/{run_id}` for long-running task status and artifacts.
- Implement deterministic intent routing first; use real LLM only as optional reranker when `mode=real|auto` and readiness is true.
- Route user requests into fixed workflow domains:
  - learning plan / lecture review / flashcards / deadlines
  - social practice / club documents / email drafts
  - research idea / paper tracking / GitHub project tracking / format check
  - life schedule / health / travel / campus guide
  - career jobs / interview plan

### 2. Foundation Stores

- Add a unified local persistence layer under `CAMPUS_HOME`:
  - `RunStore`: run metadata, status, domain, selected workflow, timestamps.
  - `ArtifactStore`: artifact files and manifest.
  - `TaskStore`: user-facing task board and scheduler items.
  - Memory integration: profile, long-term preference, task logs, knowledge snippets.
- Every workflow must write:
  - `Plan.md`
  - `Status.md`
  - `Verification.md`
  - `run_result.json`
  - artifact manifest
- Upgrade default `/tasks`, `/runs`, and `/memory` backends to use the real local stores instead of empty defaults.

### 3. Learning Completion

- Strengthen Demo B as the primary learning workflow:
  - lecture scan
  - knowledge graph
  - resource search/rank
  - review plan
  - day quiz
  - answer grading
  - plan adjustment
- Add:
  - `POST /learning/flashcards`
  - `POST /learning/deadlines`
  - `POST /learning/quiz/run`
  - `POST /learning/quiz/grade`
  - `GET /learning/dashboard`
- Ebbinghaus integration:
  - create review nodes for concepts/flashcards
  - write review tasks into `TaskStore`
  - daily tick can generate quiz from due review nodes
- Frontend learning page should show:
  - lecture review task form
  - generated KG summary
  - plan timeline
  - today quiz
  - flashcards
  - deadlines and due review nodes

### 4. Research Completion

- Extend research module with:
  - `POST /research/idea`
  - `POST /research/github/trending`
  - `POST /research/format/check`
  - existing topic refresh and note sync remain.
- Default behavior:
  - no external key: built-in deterministic provider + vendored skill metadata + local Markdown.
  - key/provider available: adapter may call real search/GitHub/Notion.
- Output shape should always include:
  - `ok`
  - `source_mode`
  - `source_error`
  - `summary`
  - `items` or `papers`
  - `questions`
  - `note_path`
  - `artifacts`
- Frontend research page should cover:
  - idea to paper digest
  - topic tracking
  - GitHub project tracking
  - format/checklist output
  - local note path and Notion readiness.

### 5. Life, Club, Career Completion

- Life:
  - keep calendar, anniversaries, daily log
  - add health record/check-in
  - add travel/entertainment planner
  - add campus process guide
- Club/social practice:
  - keep Demo A social practice
  - add meeting minutes
  - add recruiting copy
  - add generic email draft
  - expose document export status for docx/pptx/xlsx when local skills/libs are available
- Career:
  - add internship search fallback/provider adapter
  - add saved jobs
  - add interview plan
  - add interview question practice and reflection notes.

### 6. Frontend Productization

- Replace demo-heavy navigation with user-facing workspace:
  - Dashboard
  - Secretary / Chat
  - Learning
  - Research
  - Life
  - Club / Practice
  - Career
  - Tasks
  - Memory
  - Settings
- Dashboard should show:
  - today tasks
  - due reminders
  - learning progress
  - latest research updates
  - recent artifacts
  - integration readiness summary
- Settings page should show:
  - LLM readiness
  - skill registry and missing core skills
  - Notion readiness
  - mobile readiness
  - GitHub/search provider readiness
  - `CAMPUS_HOME`
  - demo smoke command.

## Public APIs / Data Shapes

### Agent

`POST /agent/run`

```json
{
  "message": "我想学 Linux，帮我安排 30 天计划",
  "mode": "offline|auto|real",
  "context": {}
}
```

Response:

```json
{
  "ok": true,
  "run_id": "run_xxx",
  "intent": "learning_plan",
  "domain": "learning",
  "selected_workflow": "demo_c_learning_plan",
  "status": "done|running|awaiting_human|failed",
  "artifacts": [],
  "error": ""
}
```

`GET /agent/runs`

`GET /agent/runs/{run_id}`

### Learning

- `POST /learning/flashcards`
- `POST /learning/deadlines`
- `GET /learning/deadlines`
- `POST /learning/quiz/run`
- `POST /learning/quiz/grade`
- `GET /learning/dashboard`

### Research

- `POST /research/idea`
- `POST /research/github/trending`
- `POST /research/format/check`
- keep `POST /research/topics`, `GET /research/topics`, `POST /research/topics/{topic_id}/refresh`, `GET /research/runs`.

### Life

- keep `/calendar`, `/anniversaries`, `/daily_log`.
- add:
  - `POST /life/health`
  - `GET /life/health`
  - `POST /life/travel_plan`
  - `GET /life/campus_guide`

### Club / Practice

- keep `/demo_a/run`.
- add:
  - `POST /club/meeting_minutes`
  - `POST /club/recruiting_copy`
  - `POST /club/email_draft`

### Career

- `POST /career/jobs/search`
- `POST /career/jobs/save`
- `GET /career/jobs`
- `POST /career/interview_plan`

### Settings

`GET /settings/status`

Response aggregates:

- LLM readiness
- skills readiness
- Notion readiness
- mobile push readiness
- GitHub/search provider readiness
- `CAMPUS_HOME`
- current app version / branch if available.

## Implementation Order

### Step 1 — Foundation Store Layer

- Implement stores in `campus/runtime` or `campus/storage`.
- Update `/runs`, `/tasks`, `/memory` default backends to use these stores.
- Add store unit tests and default backend smoke test.
- Do not alter external key behavior.

### Step 2 — Agent Router

- Implement deterministic classifier.
- Wire `/agent/run`, `/agent/runs`, `/agent/runs/{run_id}`.
- Route to existing Demo A/C and Demo B pipeline.
- Add frontend Secretary/Chat page.

### Step 3 — Learning Closure

- Add flashcards, deadlines, quiz run/grade, plan adjustment APIs.
- Integrate Ebbinghaus due nodes into local tasks.
- Expand Learning frontend page.
- Extend `scripts/smoke_demo.ps1` to cover learning.

### Step 4 — Research / Life / Club / Career

- Add missing APIs and local fallback implementations.
- Add frontend pages/cards.
- Ensure every action writes artifacts and task logs.

### Step 5 — Settings and Release Polish

- Add `/settings/status`.
- Add Settings frontend page.
- Update README and DEMO_SCRIPT.
- Extend smoke script to hit agent, learning, research, life, club, career, settings.

## Test Plan

### API

- Extend `tests/api/test_core.py` for new route shape and fake backend behavior.
- Add default backend smoke tests with `CAMPUS_HOME=.campus-test`.
- Keep existing Demo A/C offline smoke passing.

### Workflow

- `tests/demo_a/test_full_e2e.py`
  - artifact existence
  - outreach count
  - email draft count
  - `Verification.md`
- `tests/demo_b/test_full_e2e.py`
  - sample lecture directory
  - KG
  - resources
  - plan
  - quiz
  - flashcards
  - adjusted plan
- `tests/demo_c/test_full_e2e.py`
  - fuzzy learning goal
  - resources
  - 30-day plan
  - quiz
  - memory/task records
- `tests/research/test_core.py`
  - idea digest
  - topic refresh
  - GitHub fallback
  - format check
  - note path
- `tests/life/test_core.py`
  - health
  - travel
  - campus guide
- `tests/career/test_core.py`
  - job fallback search
  - save job
  - interview plan

### Frontend

- `npm.cmd run typecheck`
- `npm.cmd run build`
- If Vite/esbuild fails inside sandbox with parent directory permission, rerun build outside sandbox and record it as environment limitation.

### Smoke

Update `scripts/smoke_demo.ps1` to verify:

- `/health`
- `/settings/status`
- `/agent/run`
- Demo A offline
- Demo C offline
- Demo B sample path if fixture exists
- research idea/topic/note
- life health/travel
- club email draft
- career interview plan.

## Acceptance Criteria

- A non-key local run can open frontend and complete at least one task in each domain:
  - learning
  - research
  - life
  - club/practice
  - career
- Every task creates a run record and artifacts under `CAMPUS_HOME`.
- `/agent/run` can route broad natural-language requests without users knowing internal Demo names.
- `/settings/status` clearly reports missing external keys but does not block local fallback workflows.
- `tests/api/test_core.py` and new core tests pass.
- Frontend typecheck/build passes under the known verification procedure.

## Assumptions

- Default mode remains `offline|auto`; `real` mode is opt-in and must return clear diagnostics on failure.
- Notion, mobile push, GitHub/search provider real e2e are deferred until keys are configured.
- Proprietary office skills remain locally installed only; they are not vendored into this repo.
- The root-level untracked `.codex/` remains ignored and should not be committed.
