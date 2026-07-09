"""P3-T2: reusable real turn_fn (campus/runtime/llm_turn.py).

Mocks ``ask_llm`` (module global) so no Hermes / no network is needed. Asserts the
gate-role verdict routing (Supervisor.run_debate depends on metadata['verdict'])
and the content-role payload extraction.
"""
import sys
import types

import campus.runtime.llm_turn as lt
from campus.runtime.ports import APPROVE, PENDING, REJECT, VERDICT_KEY, Task


def _task(role: str, body: str = "do X") -> Task:
    return Task(id="t_1", title="demo task", body=body, assignee=role)


def _profile(role: str, toolset=None) -> dict:
    return {
        "role": role,
        "provider": "zai",
        "model": "glm-4.6",
        "toolset": toolset if toolset is not None else [],
        "system_prompt": f"You are the {role}.",
    }


def test_researcher_turn_returns_summary_and_payload(monkeypatch):
    raw = ('Here are candidates.\n'
           '```json\n[{"title": "MIT", "url": "https://mit.edu"}]\n```')
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (raw, 0))
    out = lt.llm_turn(_profile("researcher", ["exa"]), _task("researcher"))
    assert out.summary == raw.strip()
    assert out.metadata["payload"] == [{"title": "MIT", "url": "https://mit.edu"}]
    assert out.tokens >= 1


def test_writer_turn_without_json_has_empty_metadata(monkeypatch):
    raw = "# Proposal\n\n## Budget\n1000 yuan\n"
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (raw, 0))
    out = lt.llm_turn(_profile("writer", ["libreoffice"]), _task("writer"))
    assert out.summary.startswith("# Proposal")
    assert "payload" not in out.metadata  # no JSON block -> no payload


def test_reviewer_approve_sets_verdict(monkeypatch):
    raw = "APPROVE\nThe proposal covers budget, timeline, and safety."
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (raw, 0))
    out = lt.llm_turn(_profile("reviewer"), _task("reviewer"))
    assert out.metadata[VERDICT_KEY] == APPROVE


def test_critic_reject_sets_verdict(monkeypatch):
    raw = "REJECT\nMissing safety plan section."
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (raw, 0))
    out = lt.llm_turn(_profile("critic"), _task("critic"))
    assert out.metadata[VERDICT_KEY] == REJECT


def test_verdict_pending_when_neither(monkeypatch):
    raw = "I cannot decide yet; need more detail."
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (raw, 0))
    out = lt.llm_turn(_profile("reviewer"), _task("reviewer"))
    assert out.metadata[VERDICT_KEY] == PENDING


def test_build_role_prompt_includes_system_body_and_contract():
    t = _task("writer", body="write a proposal about topic X")
    p = lt.build_role_prompt("You are the Writer.", t)
    assert "You are the Writer." in p
    assert "write a proposal about topic X" in p
    assert "OUTPUT CONTRACT" in p


def test_gate_prompt_asks_for_verdict_first_line():
    t = _task("reviewer")
    p = lt.build_role_prompt("You are the Reviewer.", t)
    assert "APPROVE or REJECT" in p


def test_detect_verdict_first_line_wins():
    assert lt._detect_verdict("APPROVE looks good") == APPROVE
    assert lt._detect_verdict("REJECT no budget") == REJECT
    assert lt._detect_verdict("Maybe later") == PENDING


def test_detect_verdict_keyword_fallback():
    # no clean first line -> keyword anywhere
    assert lt._detect_verdict("Overall I approve of this plan.") == APPROVE
    assert lt._detect_verdict("I must reject due to gaps.") == REJECT


def test_token_estimate_scales_with_length(monkeypatch):
    short = "APPROVE\nok"
    long_raw = "APPROVE\n" + ("x" * 4000)
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (short, 0))
    short_tokens = lt.llm_turn(_profile("reviewer"), _task("reviewer")).tokens
    monkeypatch.setattr(lt, "ask_llm", lambda *a, **k: (long_raw, 0))
    long_tokens = lt.llm_turn(_profile("reviewer"), _task("reviewer")).tokens
    assert long_tokens > short_tokens


# --- ask_llm / bootstrap_env / extract_json (exercise the real code paths) ----

def test_ask_llm_captures_stdout_and_returns_rc(monkeypatch):
    """Patch run_oneshot (not ask_llm) so bootstrap_env + ask_llm actually run."""
    hermes_pkg = types.ModuleType("hermes_cli")
    hermes_pkg.__path__ = []
    env_loader = types.ModuleType("hermes_cli.env_loader")
    env_loader.load_dotenv = lambda **k: None
    oneshot = types.ModuleType("hermes_cli.oneshot")

    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_pkg)
    monkeypatch.setitem(sys.modules, "hermes_cli.env_loader", env_loader)
    monkeypatch.setitem(sys.modules, "hermes_cli.oneshot", oneshot)
    monkeypatch.setattr(lt, "_BOOTSTRAPPED", False)

    def _fake_run_oneshot(*a, **k):
        print("CAPTURED_MODEL_OUTPUT")
        return 0

    hermes_pkg.env_loader = env_loader
    hermes_pkg.oneshot = oneshot
    monkeypatch.setattr(oneshot, "run_oneshot", _fake_run_oneshot, raising=False)
    text, rc = lt.ask_llm("hi", model="glm-4.6", provider="zai", toolsets=None)
    assert text == "CAPTURED_MODEL_OUTPUT"
    assert rc == 0


def test_bootstrap_env_is_idempotent():
    lt.bootstrap_env()   # first call (loads ~/.hermes/.env if present)
    lt.bootstrap_env()   # second call is a no-op (idempotent guard)


def test_extract_json_returns_none_when_absent():
    assert lt.extract_json("no json anywhere here") is None


def test_extract_json_strips_code_fence():
    assert lt.extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}


def test_extract_json_picks_outermost_list_over_inner_dict():
    # the bug this guards: [{...}] must extract as a list, not the inner dict
    assert lt.extract_json('see [{"x": 1}] now') == [{"x": 1}]


def test_extract_json_plain_dict():
    assert lt.extract_json('prefix {"k": "v"} suffix') == {"k": "v"}
