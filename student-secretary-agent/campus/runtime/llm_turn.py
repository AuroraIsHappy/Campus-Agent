"""Reusable real LLM turn_fn (Phase 3) -- fills the Phase 2 seam.

Phase 2's ``Orchestrator.make_profile_spawn_fn(loader, turn_fn, cost)`` injects a
``turn_fn(profile, task) -> TurnOutcome``; Phase 2 only faked it. This module is
the real one: it generalizes Demo C's ``ask_llm``/``extract_json``
(``campus/demo_c/_llm.py``) into a profile-driven role turn.

  profile{system_prompt, model, provider, toolset} + task
    -> build_role_prompt -> hermes_cli.oneshot.run_oneshot
    -> parse_role_output -> TurnOutcome(summary, metadata{verdict for gates}, tokens)

Gate roles (critic/reviewer) emit a verdict (approve/reject) into ``metadata`` so
``Supervisor.run_debate`` can route pass/rework. Content roles return the raw
deliverable as ``summary`` plus any embedded JSON block as ``metadata['payload']``.

``ask_llm`` is a module global so unit tests monkeypatch it (no Hermes, no network).
Token count is a char//4 estimate (run_oneshot stdout is model text, not a usage
JSON); sufficient to trip the Supervisor cost gate at a threshold.
"""
from __future__ import annotations
import contextlib
import io
import os
from typing import Any, Optional, Tuple

from campus.odyssey.orchestrator import TurnOutcome
from campus.runtime.ports import APPROVE, PENDING, REJECT, VERDICT_KEY, Task

__all__ = [
    "llm_turn", "build_role_prompt", "parse_role_output",
    "ask_llm", "extract_json", "bootstrap_env", "GATE_ROLES",
]

# Roles whose turn output is an adversarial verdict (architecture §4.2 gates).
GATE_ROLES = {"critic", "reviewer"}

_BOOTSTRAPPED = False


def bootstrap_env() -> None:
    """Load ~/.hermes/.env (GLM key) once; idempotent. Mirrors demo_c/_llm.py."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    try:
        from hermes_cli import env_loader
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            env_loader.load_dotenv(dotenv_path=env_path, override=True)
    except Exception:
        pass
    _BOOTSTRAPPED = True


def ask_llm(prompt: str, model: str = "glm-4.6", provider: str = "zai",
            toolsets: object = None) -> Tuple[str, int]:
    """Call the model via Hermes oneshot; return (captured_text, exit_code).

    Signature/behavior cloned from ``campus/demo_c/_llm.py`` (proven in Phase 1).
    """
    bootstrap_env()
    from hermes_cli.oneshot import run_oneshot
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_oneshot(prompt, model=model, provider=provider, toolsets=toolsets)
    return buf.getvalue().strip(), rc


def extract_json(text: str):
    """Pull the outermost JSON block ({...} or [...]) out of LLM text.

    Picks the type whose opener appears FIRST so a fenced list like ``[{...}]``
    is extracted as a list, not collapsed to its inner dict. (The naive
    "brace-first" variant grabs the inner dict; this fixes that.)
    """
    import json
    import re
    i_brace = text.find("{")
    i_brack = text.find("[")
    candidates = []
    if i_brace >= 0:
        candidates.append((i_brace, "{", "}"))
    if i_brack >= 0:
        candidates.append((i_brack, "[", "]"))
    if not candidates:
        return None
    i, opener, closer = sorted(candidates)[0]
    j = text.rfind(closer)
    if j <= i:
        return None
    blob = text[i:j + 1]
    try:
        return json.loads(blob)
    except Exception:
        cleaned = re.sub(r"^```\w*|```$", "", blob, flags=re.M).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            return None


def build_role_prompt(system_prompt: str, task: Task) -> str:
    """Combine the role's system prompt + the task goal + a role-aware output contract."""
    role = (task.assignee or "").strip()
    body = task.body or ""
    parts = [
        (system_prompt or "").strip(),
        "",
        "=== TASK ===",
        f"title: {task.title}",
        "goal/context:",
        body,
    ]
    if role in GATE_ROLES:
        parts += [
            "",
            "=== OUTPUT CONTRACT ===",
            "First line MUST be exactly APPROVE or REJECT (nothing else on that line).",
            "Then a concise rationale: cite concrete defects to fix (REJECT), or note",
            "coverage of the required checks (APPROVE). Do not rewrite the work.",
        ]
    else:
        parts += [
            "",
            "=== OUTPUT CONTRACT ===",
            "Produce the deliverable for this role. If you return structured data, emit",
            "exactly ONE ```json block (no prose mixed into the JSON).",
        ]
    return "\n".join(parts)


def _detect_verdict(raw: str) -> str:
    """First meaningful line decides; else first keyword; else PENDING."""
    for line in raw.splitlines():
        s = line.strip().strip("`*#: ").upper()
        if not s:
            continue
        first = s.split()[0].rstrip(":.,;!")
        if first == "APPROVE":
            return APPROVE
        if first == "REJECT":
            return REJECT
        break  # first meaningful line did not start with a verdict
    up = raw.upper()
    if "APPROVE" in up:
        return APPROVE
    if "REJECT" in up:
        return REJECT
    return PENDING


def parse_role_output(raw: str, role: str) -> Tuple[str, dict, int]:
    """Turn raw model text into (summary, metadata, tokens).

    Gate roles -> metadata['verdict'] in {approve, reject, pending}.
    Content roles -> metadata['payload'] = embedded JSON if any.
    """
    tokens = max(1, len(raw) // 4)
    if role in GATE_ROLES:
        return raw.strip(), {VERDICT_KEY: _detect_verdict(raw)}, tokens
    payload = extract_json(raw)
    meta: dict[str, Any] = {}
    if payload is not None:
        meta["payload"] = payload
    return raw.strip(), meta, tokens


def llm_turn(profile: dict, task: Task) -> TurnOutcome:
    """The real injected turn_fn: profile + task -> one Hermes oneshot -> TurnOutcome."""
    provider = profile.get("provider") or "zai"
    model = profile.get("model") or "glm-4.6"
    toolset = profile.get("toolset") or None
    system_prompt = profile.get("system_prompt") or ""
    role = profile.get("role") or (task.assignee or "")
    prompt = build_role_prompt(system_prompt, task)
    raw, _rc = ask_llm(prompt, model=model, provider=provider, toolsets=toolset)
    summary, metadata, tokens = parse_role_output(raw, role)
    return TurnOutcome(summary=summary, metadata=metadata, tokens=tokens)
