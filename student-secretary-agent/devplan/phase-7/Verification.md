# Phase 7 — Verification

> Verification run: Phase 8 Step 0 (Phase 7 close-out). All evidence collected on branch `phase8`.

## V7-1: Foundation Stores write Plan/Status/Verification/run_result.json + manifest

**Command:**
```
python -m pytest tests/api/test_core.py::test_default_agent_run_writes_foundation_stores -v
```
**Result:** PASSED. A `/agent/run` call creates a run record; the run directory contains `Plan.md`, `Status.md`, `Verification.md`, `run_result.json`, and `artifact_manifest.json`. `RunStore.update` records status + artifacts + result.

## V7-2: All five domains complete a task in local fallback (no external key)

**Command:**
```
python -m pytest tests/api/test_core.py::test_phase7_domain_routes_local_fallback -v
```
**Result:** PASSED. One test exercises every Phase 7 route:
- learning: flashcards (3 cards + review nodes seeded), deadlines, dashboard, quiz run (2Q), quiz grade
- research: idea digest (note_path), github trending (items), format check (items)
- life: health record, health list, travel plan, campus guide
- club: meeting minutes, recruiting copy, email draft
- career: job search, save job, list jobs, interview plan, **interview practice**, **interview reflect**, **export_status**

## V7-3: Ebbinghaus review nodes + daily quiz (deepened sub-item)

**Command:**
```
python -m pytest tests/api/test_core.py::test_ebbinghaus_daily_quiz_and_review_nodes -v
```
**Result:** PASSED.
- `POST /learning/flashcards` (count=3) → `review_nodes == 3` seeded into TaskStore with `reps_correct=0`, `due_ts` = now + 1 day (interval 1).
- `POST /learning/quiz/daily` (topic=OS) → `total_review_nodes >= 3`, questions have `review_node_id`.
- `POST /learning/quiz/grade` with `review_node_id` → `ebbinghaus_advanced == True`; the node's `reps_correct` increments and `due_ts` moves to now + 3 days.
- Second `quiz/daily` still produces questions (other nodes still due).

## V7-4: Interview practice + reflection (deepened sub-item)

**Route:** `POST /career/interview/practice`
**Result:** Returns `score`, `rubric` (4 STAR criteria), `model_answer_outline` (4 STAR sections), `follow_ups` (2), `improvement_cues`. Verified in `test_phase7_domain_routes_local_fallback`.

**Route:** `POST /career/interview/reflect`
**Result:** Writes reflection to `interview_reflections.json` under CAMPUS_HOME; returns `reflections_total >= 1`.

## V7-5: Document export status (deepened sub-item)

**Route:** `GET /club/export_status`
**Result:** Returns per-format availability for `docx` (python-docx), `pptx` (python-pptx), `xlsx` (openpyxl), `pdf` (reportlab). On this machine: docx/pptx/xlsx available (in requirements.txt), pdf optional. `any_available == True`.

## V7-6: Settings aggregates readiness

**Route:** `GET /settings/status`
**Result:** Returns `llm` (real_llm_status auto), `skills` (audit), `notion` (status), `mobile` (feishu/qq env check), `providers` (github/search env check), `campus_home`, `version`, `branch`. Local fallback not blocked when keys absent.

## V7-7: Full test suite

**Command:**
```
python -m pytest -q
```
**Result:** **277 passed** (276 baseline + 1 new Ebbinghaus test). No failures, no errors.

## V7-8: Frontend typecheck

**Command:** `npm run typecheck` (in `frontend/`)
**Result:** PASSED (0 errors).

## Acceptance Criteria — Final Sign-off

All six Phase 7 acceptance criteria (Plan.md lines 337-349) are met. Phase 7 is **closed**.
