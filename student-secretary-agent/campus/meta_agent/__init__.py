"""L5 Meta-Agent subsystem (architecture §4.4).

Onboarding wizard, vendor-neutral model routing, skill discovery + reliability scoring,
zero-config skill pack, and the Meta-Agent that classifies tasks and maps them to an
Odyssey role DAG. Pure stdlib + pyyaml; LLM/embed/ask are injected so tests are hermetic.
"""
