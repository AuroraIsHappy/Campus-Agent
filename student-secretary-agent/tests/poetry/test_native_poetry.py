import json

from fastapi.testclient import TestClient
from unittest.mock import patch

from campus.api.server import create_app
from campus.poetry.service import PoetryService, is_poetry_intent


def test_native_service_creation_version_and_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPUS_POETRY_MOCK", "1")
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("深夜回宿舍，便利店的灯还亮着，门口有雨水。")
    assert session["status"] == "ready"
    poem = service.compose(session["id"])
    assert "灯" in poem["content"] and poem["version"] == 1
    revised = service.revise(session["id"], poem["content"], "更克制")
    assert revised["version"] == 2
    final = service.finalize(session["id"], revised["content"], accept_medium=True)
    assert final["finalized"] is True
    assert service.get_session(session["id"])["status"] == "finalized"


def test_short_observation_asks_once(tmp_path):
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("回家了")
    assert session["status"] == "collecting"
    assert session["messages"][-1]["role"] == "assistant"
    assert service.add_message(session["id"], "门锁转动的声音")["status"] == "ready"


def test_document_validation_and_deduplication(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPUS_HOME", str(tmp_path))
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    first = service.ingest_document("notes.md", "一盏灯。".encode())
    second = service.ingest_document("notes.md", "一盏灯。".encode())
    assert first["status"] == "ready" and second["deduplicated"] is True
    try:
        service.ingest_document("bad.exe", b"x")
        assert False, "unsupported documents must fail"
    except ValueError as exc:
        assert "仅支持" in str(exc)


def test_unified_chat_explicit_and_auto_routing(tmp_path, monkeypatch):
    monkeypatch.setenv("CAMPUS_HOME", str(tmp_path))
    monkeypatch.setenv("CAMPUS_POETRY_MOCK", "true")
    client = TestClient(create_app(with_scheduler=False))
    first = client.post("/agent/chat", json={"message": "深夜回宿舍，便利店的灯还亮着", "agent": "poetry"}).json()
    assert first["active_agent"] == "poetry" and first["workflow_id"]
    composed = client.post("/agent/chat", json={"message": "开始创作", "agent": "poetry",
        "workflow_id": first["workflow_id"], "conversation_id": first["conversation_id"], "action": "compose"}).json()
    assert composed["canvas"]["type"] == "poem" and composed["workflow_status"] == "review"
    restored = client.get(f"/agent/conversations/{first['conversation_id']}").json()
    assert restored["active_agent"] == "poetry" and restored["canvas"]["type"] == "poem"
    assert is_poetry_intent("把今天的雨写成一首诗") is True


# ---- real-LLM path (no CAMPUS_POETRY_MOCK) ----------------------------------
# Regression guard: ``_compose_with_llm`` must unpack the (text, rc) tuple that
# ``ask_llm`` returns. Previously it bound the whole tuple to ``raw`` and passed
# it to ``extract_json`` (which expects a str), raising AttributeError that the
# broad ``except Exception:`` swallowed → silent fallback to the local template,
# so the model output was discarded every turn. These tests patch ``ask_llm``
# directly (no key, no hermes_cli) and assert the LLM poem actually propagates.

_POEM_JSON = {
    "title": "便利店之后",
    "content": "灯还亮着\n我没有赶路",
    "themes": ["夜晚"],
    "images": ["灯"],
    "notes": "保留具体物件。",
}
_REVISED_JSON = {
    "title": "便利店之后",
    "content": "灯还亮着，更克制",
    "themes": ["夜晚"],
    "images": ["灯"],
    "notes": "更克制。",
}


def _llm_return(payload: dict) -> tuple[str, int]:
    """Wrap a dict as ask_llm's (captured_stdout, exit_code) return value."""
    return (json.dumps(payload, ensure_ascii=False), 0)


def test_compose_uses_llm_output_not_local_template(tmp_path, monkeypatch):
    monkeypatch.delenv("CAMPUS_POETRY_MOCK", raising=False)
    monkeypatch.setenv("CAMPUS_POETRY_REQUIRE_LLM", "1")  # forbid silent fallback
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("深夜回宿舍，便利店的灯还亮着，门口有雨水。")

    with patch("campus.runtime.llm_turn.ask_llm", return_value=_llm_return(_POEM_JSON)):
        poem = service.compose(session["id"])

    assert poem["title"] == _POEM_JSON["title"]
    assert poem["content"] == _POEM_JSON["content"]
    assert poem["version"] == 1
    assert poem["inspiration"]["notes"] == "保留具体物件。"
    # the LLM text must not be the local template's signature line
    assert "没有催我赶路" not in poem["content"]


def test_revise_uses_llm_output_and_versions_increment(tmp_path, monkeypatch):
    monkeypatch.delenv("CAMPUS_POETRY_MOCK", raising=False)
    monkeypatch.setenv("CAMPUS_POETRY_REQUIRE_LLM", "1")
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("深夜回宿舍，便利店的灯还亮着，门口有雨水。")

    with patch("campus.runtime.llm_turn.ask_llm", return_value=_llm_return(_POEM_JSON)):
        service.compose(session["id"])
    with patch("campus.runtime.llm_turn.ask_llm", return_value=_llm_return(_REVISED_JSON)):
        revised = service.revise(session["id"], None, "更克制")

    assert revised["content"] == _REVISED_JSON["content"]
    assert revised["version"] == 2


def test_compose_extracts_json_from_markdown_fenced_output(tmp_path, monkeypatch):
    """LLMs often wrap JSON in ```json fences; extract_json must still recover it."""
    monkeypatch.delenv("CAMPUS_POETRY_MOCK", raising=False)
    monkeypatch.setenv("CAMPUS_POETRY_REQUIRE_LLM", "1")
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("深夜回宿舍，便利店的灯还亮着，门口有雨水。")
    fenced = "前缀说明。\n```json\n" + json.dumps(_POEM_JSON, ensure_ascii=False) + "\n```\n后缀。"

    with patch("campus.runtime.llm_turn.ask_llm", return_value=(fenced, 0)):
        poem = service.compose(session["id"])

    assert poem["content"] == _POEM_JSON["content"]


def test_compose_falls_back_to_local_when_llm_returns_unparseable(tmp_path, monkeypatch):
    """If the model returns no JSON, the service falls back to the local composer.

    Without CAMPUS_POETRY_REQUIRE_LLM, an unparseable LLM reply must not raise —
    it yields the deterministic local poem so the user still gets something.
    """
    monkeypatch.delenv("CAMPUS_POETRY_MOCK", raising=False)
    monkeypatch.delenv("CAMPUS_POETRY_REQUIRE_LLM", raising=False)
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("深夜回宿舍，便利店的灯还亮着，门口有雨水。")

    with patch("campus.runtime.llm_turn.ask_llm", return_value=("模型没返回 JSON。", 0)):
        poem = service.compose(session["id"])

    # local composer signature: anchor (images[0]="雨") + the fixed refrain line
    assert "没有催我赶路" in poem["content"]
    assert poem["title"] == "雨之后"  # anchor "雨" + "之后"


def test_compose_requires_llm_raises_when_ask_llm_raises(tmp_path, monkeypatch):
    """CAMPUS_POETRY_REQUIRE_LLM=1 surfaces an LLM connection failure instead of
    silently masking it with the local template. The flag re-raises only when the
    ``try`` block actually raises (e.g. ask_llm connection error); an unparseable
    but non-raising reply still falls back (covered by the test above).
    """
    monkeypatch.delenv("CAMPUS_POETRY_MOCK", raising=False)
    monkeypatch.setenv("CAMPUS_POETRY_REQUIRE_LLM", "1")
    service = PoetryService(str(tmp_path / "poetry.sqlite3"))
    session = service.create_session("深夜回宿舍，便利店的灯还亮着，门口有雨水。")

    def _boom(*a, **k):
        raise ConnectionError("model endpoint unreachable")

    with patch("campus.runtime.llm_turn.ask_llm", side_effect=_boom):
        try:
            service.compose(session["id"])
        except RuntimeError as exc:
            assert "LLM" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when ask_llm raises and CAMPUS_POETRY_REQUIRE_LLM=1")

