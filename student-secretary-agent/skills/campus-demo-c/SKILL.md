---
name: campus-demo-c
description: Turn a fuzzy learning goal (e.g. "我想学 Linux") into a complete study plan — researches free resources, ranks them, builds a progressive N-day plan with real chapter outline, generates a day-1 quiz, and writes long-term memory. Use whenever the user wants to learn something new and needs a structured, low-effort study plan.
version: 0.1.0
license: MIT
---

# Campus Demo C — fuzzy learning goal → structured study plan

When the user gives a vague learning goal (e.g. "我想学 Linux", "学一下 Rust", "我想入门机器学习"), run the Demo C chain end-to-end and report the artifacts. Do NOT hand-write a plan — delegate to the orchestrator below.

## How to run
From the `student-secretary-agent/` directory with the venv activated:
```
python run_demo_c.py orchestrator "<the user's goal>"
```
Options:
- `--days N` (default 30) — plan length
- `--minutes M` (default 20) — per-day slot length
- `--quiz-n K` (default 3) — day-1 quiz question count

Sub-commands (for partial/debug runs): `researcher "<goal>" -n 6`, `scheduler "<title>" --days N [--outline]`, `quiz --topic "..." -n K`, `memory --show`, `memory --remember k=v`.

## What it produces
Artifacts land in `~/.campus/runs/<YYYYMMDD-HHMMSS>/`:
- `run_result.json` — recommendation (title, url, score, reasons) + summary
- `plan.md` — N-day progressive plan (real chapter outline via GLM, not generic "Part N")
- `quiz_day1.json` — day-1 quiz (`[{q, answer, explanation}]`)
- `research_candidates.json` — ranked candidate resources
- `progress.json`
Long-term memory appended to `~/.campus/memory.json` (goal + preference).

## After running
1. Read `run_result.json` and report: the recommended resource (title + score + reasons) and the goal it planned for.
2. Preview `plan.md` (first ~5 days) so the user sees the chapter progression.
3. Show 1 sample quiz question from `quiz_day1.json`.
4. Offer to push the day-1 quiz to the user's Feishu (chat ID on file) for mobile delivery — use `hermes send --to feishu:<chatID> --file <run_dir>/quiz_day1.json` (gateway must be running).

## Notes / limitations
- Researcher uses GLM-4.6's parametric knowledge (not live web); candidate resources are well-known classics but URLs should be spot-checked. For live/verifiable web search, pair with the `firecrawl` or `web-access` skill.
- Models route per `~/.campus/routing.yaml` (GLM / Z.AI). Heavy steps use glm-4.6, quiz uses glm-4.5-air.
- The orchestrator is deterministic except for the LLM steps (researcher, chapter outline, quiz); re-running yields a fresh timestamped run dir.
