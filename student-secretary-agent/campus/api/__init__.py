"""Campus HTTP API (Phase 5): a thin FastAPI layer the frontend consumes.

Wraps the existing campus libraries (demo_b pipeline, memory, onboarding,
kanban) behind a small REST surface. The frontend never talks to Hermes
internals directly -- only this API -- so Hermes can be upgraded without
touching the skin (architecture §C4② / red line: do not modify vendored repos).

Backends are injectable (``create_app(backends=...)``) so the TestClient test
suite is fully deterministic (no Hermes / no network / no real model).
"""
