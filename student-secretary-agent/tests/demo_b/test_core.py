"""Unit tests for Demo B deterministic cores (no LLM / no network / real tiny files)."""
import os
import sys
import tempfile

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.demo_b.types import (
    KGNode, KGEdge, KnowledgeGraph, ReviewDay, ReviewPlan, Quiz, QuizQ,
    CheckResult, to_dict,
)
from campus.demo_b import extractors as X
from campus.demo_b import types as T


# ---------------- types ----------------

def test_kgnode_kind_validation():
    n = KGNode(id="c1", kind="concept", title="Pointers")
    assert n.kind == "concept"
    raised = False
    try:
        KGNode(id="x", kind="bogus", title="t")
    except ValueError:
        raised = True
    assert raised


def test_kgnode_requires_title():
    raised = False
    try:
        KGNode(id="x", kind="chapter", title="")
    except ValueError:
        raised = True
    assert raised


def test_kg_valid_edges_filters_dangling():
    g = KnowledgeGraph(
        nodes=[KGNode(id="a", kind="concept", title="A"),
               KGNode(id="b", kind="concept", title="B")],
        edges=[KGEdge(src="a", dst="b", rel="prereq"),
               KGEdge(src="a", dst="zzz", rel="prereq")],  # dangling dst
    )
    assert g.node_ids == {"a", "b"}
    assert len(g.valid_edges()) == 1
    assert g.valid_edges()[0].dst == "b"


def test_reviewplan_within_budget():
    plan = ReviewPlan(exam_date="2026-08-01", free_minutes=60, days=[
        ReviewDay(n=1, date="2026-07-30", est_minutes=20),
        ReviewDay(n=2, date="2026-07-31", est_minutes=25),
    ])
    assert plan.total_minutes == 45
    assert plan.within_budget is True
    plan.days.append(ReviewDay(n=3, date="2026-08-01", est_minutes=30))
    assert plan.total_minutes == 75
    assert plan.within_budget is False  # B-Q3 over budget


def test_to_dict_roundtrip():
    q = Quiz(day=1, topic="x", questions=[QuizQ(q="q", answer="a")])
    d = to_dict(q)
    assert d["day"] == 1 and d["questions"][0]["q"] == "q"


# ---------------- extractors (B-F1) ----------------

def _write(tmp, name, body):
    p = os.path.join(tmp, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


def test_extract_txt_ok():
    tmp = tempfile.mkdtemp()
    p = _write(tmp, "lec1.txt", "Chapter 1: intro to pointers.\nKey idea: addresses.")
    r = X.extract_path(p)
    assert r.ok and "pointers" in r.text
    assert r.doc.ext == "txt" and r.doc.size_bytes > 0
    assert r.chars == len(r.text)


def test_extract_md_ok():
    tmp = tempfile.mkdtemp()
    p = _write(tmp, "notes.md", "# Trees\n- BFS\n- DFS")
    r = X.extract_path(p)
    assert r.ok and "Trees" in r.text


def test_unsupported_ext_not_ok():
    tmp = tempfile.mkdtemp()
    p = _write(tmp, "image.xyz", "whatever")
    r = X.extract_path(p)
    assert r.ok is False
    assert "unsupported" in r.error


def test_missing_file_not_ok():
    r = X.extract_path(os.path.join(tempfile.gettempdir(), "no_such_demo_b_file.txt"))
    assert r.ok is False


def test_extract_dir_and_rate():
    tmp = tempfile.mkdtemp()
    _write(tmp, "a.txt", "alpha content here")
    _write(tmp, "sub/b.md", "beta markdown body")
    _write(tmp, "skip.xyz", "ignored")          # unsupported -> not counted
    results = X.extract_dir(tmp)
    assert len(results) == 2                      # only .txt + .md
    rate, ok = X.extraction_rate(results)
    assert rate == 1.0 and ok is True             # both succeeded


def test_extraction_rate_empty_is_zero():
    rate, ok = X.extraction_rate([])
    assert rate == 0.0 and ok is False


def test_extraction_rate_at_minimum():
    hand = [
        T.ExtractedText(doc=X.lecture_doc("a.txt"), text="ok", ok=True),
        T.ExtractedText(doc=X.lecture_doc("b.txt"), text="", ok=False, error="e"),
    ]
    rate, ok = X.extraction_rate(hand, minimum=0.5)
    assert rate == 0.5 and ok is True  # exactly at minimum passes


def test_extractors_injectable_fake():
    """B-F1 seam: tests can inject a fake extractor table (no real libs)."""
    fake = {"pdf": lambda p: T.ExtractedText(doc=X.lecture_doc(p), text="FAKE PDF TEXT", ok=True)}
    r = X.extract_path("whatever.pdf", extractors=fake)
    assert r.ok and r.text == "FAKE PDF TEXT"
