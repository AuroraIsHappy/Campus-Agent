# Vendored Skills

This directory contains third-party Hermes/Agent Skills that Campus-Agent ships
as built-in capabilities for offline onboarding and demos.

## Included

- Research: `academic-search`, `read-arxiv-paper`, `academic-researcher`,
  `academic-research-skills`
- Web access: `web-access`
- Notes / knowledge: `notion-api`, `baoyu-translate`
- Meta skills: `find-skills`, `skill-creator`

## Policy

- Keep Campus-owned skills at `skills/<name>/`.
- Keep third-party skills under `skills/vendor/<name>/` so provenance,
  licensing, and upgrade boundaries stay clear.
- Do not vendor skills that were blocked by security audit, could not be
  fetched from upstream, or carry license terms that prohibit copying or
  distribution.
- A future installer should either add this vendor directory to
  `skills.external_dirs`, or copy selected entries into the user's Hermes home
  skills directory.

## Not Included

- `docx`, `pptx`, `xlsx`, and `pdf` are installed on this development machine
  but are not vendored because their local skill packages declare proprietary
  terms that prohibit extraction, copying, and distribution.

## Current Source

These skills were copied from the local Hermes install:

`C:/Users/Lenovo/AppData/Local/hermes/skills/`

The install status and upstream URLs are tracked in `../SKILL_LIST.md`.
