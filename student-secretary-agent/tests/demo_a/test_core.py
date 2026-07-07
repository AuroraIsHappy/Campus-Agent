"""P3 L1 unit tests for campus/demo_a pure logic (no LLM, no network).

Covers sample_extractor (A-Q1 column/tone), checkers (A-Q1/Q3/Q4 + A-Q2 with an
injected opener), role_turns pure helpers, and renderers (importorskip the libs).
"""
import os

import pytest

from campus.demo_a import checkers, role_turns, sample_extractor
from campus.demo_a.types import OutreachTarget, SampleSpec


# --- sample_extractor (A-Q1 input) ------------------------------------------

def test_extract_columns_markdown_and_chinese_markers():
    text = ("# 策划案\n## 活动背景\n一、活动目的\n二、预算\n"
            "1. 时间安排\n【安全预案】")
    spec = sample_extractor.extract_sample(text)
    for col in ("策划案", "活动背景", "活动目的", "预算", "时间安排", "安全预案"):
        assert col in spec.columns, spec.columns


def test_detect_tone_keywords():
    assert sample_extractor.detect_tone("本策划案语气正式、学术") == "formal"
    assert sample_extractor.detect_tone("轻松活泼的口吻") == "casual"


def test_extract_sample_default_tone_is_formal():
    spec = sample_extractor.extract_sample("plain text without tone markers")
    assert spec.tone == "formal"


# --- checkers (A-Q1/Q3/Q4/Q2) -----------------------------------------------

def test_check_completeness_all_three_present():
    r = checkers.check_completeness("# x\n## 预算\n## 时间表\n## 安全预案\n")
    assert r.passed, r.detail


def test_check_completeness_missing_safety():
    r = checkers.check_completeness("预算 100\n时间表: day1")
    assert not r.passed
    assert "safety" in r.detail


def test_format_adherence_meets_threshold():
    spec = SampleSpec(columns=["活动背景", "预算", "时间表", "安全预案"])
    proposal = "活动背景 ... 预算 ... 时间表 ..."  # 3/4 = 75% >= 60%
    assert checkers.check_format_adherence(proposal, spec).passed


def test_format_adherence_below_threshold_fails():
    spec = SampleSpec(columns=["a", "b", "c", "d", "e"])
    assert not checkers.check_format_adherence("a", spec).passed  # 1/5 = 20%


def test_format_adherence_no_columns_passes():
    assert checkers.check_format_adherence("anything", SampleSpec()).passed


def test_geographic_plausibility_single_city_ok():
    proposal = "## 时间表\n- 7月10日 北京航天博物馆\n- 7月11日 中国科技馆\n"
    assert checkers.check_geographic_plausibility(proposal).passed


def test_geographic_plausibility_two_cities_one_day_fails():
    proposal = "7月10日 早上北京，晚上上海\n"
    assert not checkers.check_geographic_plausibility(proposal).passed


def test_verify_urls_reachable_with_injected_opener():
    targets = [OutreachTarget(name="A", url="https://a.example.com"),
               OutreachTarget(name="B", url="https://b.example.com")]
    res = checkers.verify_urls(targets, opener=lambda u, t: 200)
    assert len(res) == 2 and all(v["reachable"] for v in res)


def test_verify_urls_unreachable_is_flagged_not_fabricated():
    res = checkers.verify_urls([{"name": "X", "url": "https://x"}],
                               opener=lambda u, t: 0)
    assert res[0]["reachable"] is False
    assert res[0]["status"] == 0


# --- role_turns pure helpers ------------------------------------------------

def test_coerce_targets_normalizes_and_filters():
    payload = [
        {"name": "MIT", "visit_reason": "x", "contact_source": "web",
         "url": "https://mit.edu", "score": "9"},
        {"name": "   "}, {"foo": "bar"}, "not-a-dict",
    ]
    out = role_turns.coerce_targets(payload)
    assert len(out) == 1
    assert out[0].name == "MIT"
    assert out[0].url == "https://mit.edu"
    assert out[0].score == 9.0


def test_md_outline_extracts_sections_and_bullets():
    md = "# 策划案\n## 预算\n- 交通费\n- 餐饮费\n## 时间表\n- day1\n"
    outline = role_turns.md_outline(md)
    assert outline[0][0] == "预算"
    assert outline[0][1] == ["交通费", "餐饮费"]


def test_budget_rows_under_section_with_fallback():
    md = "# 策划案\n## 预算\n- 交通费\n- 餐饮费\n## 时间表\n"
    assert role_turns.budget_rows(md) == [{"item": "交通费"}, {"item": "餐饮费"}]
    fallback = role_turns.budget_rows("nothing here")
    assert fallback and "item" in fallback[0]


def test_persist_role_writer_updates_ctx_and_writes_md(tmp_path):
    from campus.odyssey.orchestrator import TurnOutcome
    ctx = {}
    out = TurnOutcome(
        summary="# 策划案\n## 预算\n- 交通费\n## 时间表\n- d1\n## 安全预案\nx",
        metadata={})
    arts = role_turns.persist_role("writer", out, ctx, str(tmp_path))
    assert os.path.join(str(tmp_path), "proposal.md") in arts
    assert ctx["proposal"].startswith("# 策划案")


def test_persist_role_researcher_writes_json_and_ctx(tmp_path):
    from campus.odyssey.orchestrator import TurnOutcome
    ctx = {}
    out = TurnOutcome(summary="x",
                      metadata={"payload": [{"name": "A", "url": "https://a"}]})
    role_turns.persist_role("researcher", out, ctx, str(tmp_path))
    assert ctx["candidates"][0]["name"] == "A"
    assert os.path.exists(os.path.join(str(tmp_path), "outreach_candidates.json"))


# --- renderers (only when python-docx / openpyxl are installed) --------------

def test_to_docx_roundtrip(tmp_path):
    docx = pytest.importorskip("docx")
    from campus.demo_a import renderers
    p = str(tmp_path / "out.docx")
    renderers.to_docx("# Title\n## Sub\n- a\npara\n", p)
    doc = docx.Document(p)
    text = "\n".join(par.text for par in doc.paragraphs)
    assert "Title" in text and "para" in text


def test_to_xlsx_roundtrip(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from campus.demo_a import renderers
    p = str(tmp_path / "b.xlsx")
    renderers.to_xlsx([{"item": "交通费", "amount": 100}, {"item": "餐饮费", "amount": 50}], p)
    wb = openpyxl.load_workbook(p)
    assert wb.active.max_row == 3  # header + 2 rows
