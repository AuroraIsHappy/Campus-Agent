"""Demo B: scan lectures -> knowledge graph -> resources -> review plan + quiz.

Phase 5 backend. Mirrors the campus/demo_c + campus/demo_a structure. All LLM,
network, and filesystem-heavy work goes through injectable seams so the test
suite is deterministic (no Hermes / no model / no network). See
``devplan/phase-5/Plan.md``.
"""
