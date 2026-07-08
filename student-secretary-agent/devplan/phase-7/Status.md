# Phase 7 — Status

## Milestone

**GOAL 功能闭环 Sprint — 本地产品闭环达成。** 无外部 key 时,前端 + API 可在学习、科研、生活、社团实践、职业每个域完成至少一个任务,产物写入 `CAMPUS_HOME`。

## Workstream Completion

| # | Workstream | Status | Evidence |
|---|---|---|---|
| 1 | Unified Agent Entry (`POST /agent/run`, `GET /agent/runs[/{id}]`) | ✅ | `server.py:_default_agent_run` + deterministic `_classify_agent_message`; routes registered; `test_default_agent_run_writes_foundation_stores` |
| 2 | Foundation Stores (RunStore / ArtifactStore / TaskStore) | ✅ | `campus/runtime/stores.py`; every workflow writes Plan/Status/Verification/run_result.json + artifact manifest; `/runs` `/tasks` `/memory` default backends upgraded |
| 3 | Learning Closure (flashcards / deadlines / quiz run+grade / dashboard / Ebbinghaus daily-tick) | ✅ | `phase7.py:flashcards/add_deadline/list_deadlines/quiz_run/quiz_grade/quiz_daily/advance_review_node`; flashcards seed Ebbinghaus review nodes; grade advances curve; `POST /learning/quiz/daily` |
| 4 | Research Completion (idea / github trending / format check) | ✅ | `phase7.py:research_idea/github_trending/format_check`; existing topic refresh + Notion sync retained |
| 5 | Life / Club / Career Completion | ✅ | life: health/travel/campus_guide + calendar/anniversaries/daily_log; club: meeting_minutes/recruiting_copy/email_draft + export_status; career: jobs search/save + interview_plan/practice/reflect |
| 6 | Frontend Productization (10+ workspace views) | ✅ | `App.tsx` NAV: Dashboard/Secretary/Learning/Research/Life/Club/Career/Tasks/Memory/Settings; `pages.tsx` 933 lines |
| 7 | Settings & Release Polish (`/settings/status`) | ✅ | aggregates LLM/skills/Notion/mobile/providers readiness |

## Deepened Sub-items (Phase 7 plan, originally deferred — closed in Phase 8 Step 0)

| Sub-item | Status | Evidence |
|---|---|---|
| Ebbinghaus forgetting curve (1/3/7/16/35d intervals) | ✅ | `phase7.py:_ebbinghaus_due` + `_seed_review_nodes`; flashcards seed review nodes into TaskStore with `reps_correct/last_ts/due_ts` metadata |
| daily-tick → quiz from due review nodes | ✅ | `phase7.py:quiz_daily` + `POST /learning/quiz/daily`; `test_ebbinghaus_daily_quiz_and_review_nodes` |
| quiz grade advances Ebbinghaus curve | ✅ | `phase7.py:advance_review_node` wired into `quiz_grade` via `review_node_id` |
| Document export status (docx/pptx/xlsx/pdf) | ✅ | `phase7.py:export_status` + `GET /club/export_status`; checks python-docx/python-pptx/openpyxl/reportlab availability |
| Interview question practice + reflection notes | ✅ | `POST /career/interview/practice` (scored rubric + model outline + follow-ups) + `POST /career/interview/reflect` (reflection log) |

## Test Results

- `tests/api/test_core.py`: **23 passed** (was 22; +1 Ebbinghaus daily quiz test)
- Full suite: **277 passed** (was 276; +1)
- Frontend: `npm run typecheck` passes

## Acceptance Criteria Check

- [x] A non-key local run can open frontend and complete ≥1 task in each domain (learning/research/life/club/career) — verified by `test_phase7_domain_routes_local_fallback`
- [x] Every task creates a run record and artifacts under `CAMPUS_HOME` — `test_default_agent_run_writes_foundation_stores`
- [x] `/agent/run` routes broad natural-language requests without users knowing internal Demo names — `_classify_agent_message` covers all 5 domains + general
- [x] `/settings/status` reports missing external keys but does not block local fallback — `_default_settings_status`
- [x] `tests/api/test_core.py` and new core tests pass — 23 passed
- [x] Frontend typecheck/build passes

## Known Limitations (deferred by design)

- Real LLM / mobile push / Notion / GitHub-search real e2e are adapter-only this phase; real-key verification is Phase 8.
- Phase 7 workflows are deterministic templates; real LLM driving is Phase 8 Step 3.
- Multi-agent orchestrator is wired only via `/demo_a/run` (club domain); general `/agent/run` → MetaAgent → DAG execution is Phase 8 Step 1.
