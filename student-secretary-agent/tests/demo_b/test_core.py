"""Unit tests for Demo B deterministic cores (no LLM / no network / real tiny files)."""
import os
import sys
import tempfile

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.demo_b.types import (
    KGNode, KGEdge, KnowledgeGraph, ReviewDay, ReviewPlan, Quiz, QuizQ,
    CheckResult, ExtractedText, to_dict,
)
from campus.demo_b import extractors as X
from campus.demo_b import types as T
from campus.demo_b import knowledge_graph as KG
from campus.demo_b import quiz as QZ
from campus.demo_b import resource_search as RS
from campus.demo_b import review_planner as RP
from campus.demo_b import checkers as CK


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


# ---------------- knowledge graph (B-F2) ----------------

def _et(path, text):
    return ExtractedText(doc=X.lecture_doc(path), text=text, ok=True)


def test_build_kg_chapters_and_concepts():
    texts = [_et("a.md", "# Chapter 1: Pointers\n- addresses\n- dereference\n# Chapter 2: Arrays")]
    kg = KG.build_kg(texts)
    kinds = {n.kind for n in kg.nodes}
    assert "chapter" in kinds and "concept" in kinds
    assert len(kg.nodes) >= 3
    assert len(kg.valid_edges()) >= 1          # chapter -> concept links
    assert "a.md" in kg.source_docs


def test_build_kg_skips_failed_extractions():
    texts = [_et("ok.md", "# Topic\n- idea"), ExtractedText(doc=X.lecture_doc("bad.pdf"), ok=False)]
    kg = KG.build_kg(texts)
    assert all(n.source_doc == "ok.md" for n in kg.nodes)


def test_build_kg_injectable_extract_fn():
    def fake(text, src):
        return [KGNode(id="x", kind="formula", title="E=mc^2", source_doc=src)]
    kg = KG.build_kg([_et("a.txt", "anything")], extract_fn=fake)
    assert len(kg.nodes) == 1 and kg.nodes[0].kind == "formula"


def test_validate_kg_clean():
    kg = KG.build_kg([_et("a.md", "# C\n- x\n- y")])
    assert KG.validate_kg(kg) == []


# ---------------- quiz (B-F5) ----------------

def test_generate_quiz_default():
    q = QZ.generate_quiz("Pointers", "addresses\ndereference\nnull", n=2)
    assert q.day == 1 and len(q.questions) == 2
    assert all(qq.answer for qq in q.questions)


def test_generate_quiz_empty_has_placeholder():
    q = QZ.generate_quiz("Topic", "", n=3)
    assert len(q.questions) >= 1


def test_generate_quiz_injectable():
    def fake(topic, content, n):
        return [QuizQ(q="custom?", answer="yes")]
    q = QZ.generate_quiz("t", "c", quiz_fn=fake, n=5)
    assert q.questions[0].q == "custom?"


# ---------------- resource search (B-F3 / B-Q1) ----------------

def test_search_resources_returns_ranked():
    res = RS.search_resources("linux", top_k=3)
    assert len(res) >= 3
    assert all(hasattr(r, "url") for r in res)


def test_search_resources_dedupes():
    def dup(topic):
        from campus.demo_c.types import Resource
        return [Resource(title="a", url="dup"), Resource(title="b", url="dup")]
    res = RS.search_resources("x", searcher=dup)
    assert len(res) == 1


def test_rank_resources_orders_by_reliability():
    from campus.demo_c.types import Resource
    good = Resource(title="linux course", url="u1", source_type="course", year=2024, difficulty="beginner")
    bad = Resource(title="unrelated", url="u2", source_type="blog", year=2010, difficulty="advanced")
    ranked = RS.rank_resources([bad, good], "linux")
    assert ranked[0][0].url == "u1"           # reliable course ranks first (B-Q1)


# ---------------- review planner (B-F4 / B-Q3 / B-F6) ----------------

def _small_kg():
    return KG.build_kg([_et("a.md", "# Chapter 1\n- a\n- b\n# Chapter 2\n- c")])


def test_build_review_plan_covers_and_within_budget():
    kg = _small_kg()
    plan = RP.build_review_plan(kg, exam_date="2026-07-30", free_minutes=120,
                                start_date="2026-07-28", slot_minutes=20)
    assert len(plan.days) == 3                  # 28,29,30 inclusive
    assert plan.days[-1].date == "2026-07-30"
    assert plan.within_budget is True           # B-Q3
    assert plan.total_minutes <= plan.free_minutes


def test_build_review_plan_with_quiz_fn():
    kg = _small_kg()
    plan = RP.build_review_plan(kg, exam_date="2026-07-29", free_minutes=60,
                                start_date="2026-07-28", quiz_fn=QZ.default_quiz_fn)
    assert plan.days[0].quiz is not None and len(plan.days[0].quiz.questions) >= 1


def test_adjust_plan_requeues_wrong_advances_correct():
    kg = _small_kg()
    plan = RP.build_review_plan(kg, exam_date="2026-08-05", free_minutes=200,
                                start_date="2026-08-01")
    # day1 topics: subset; force one wrong (requeue) + mark a later topic correct
    day1_topics = list(plan.days[0].topics)
    wrong_topic = day1_topics[0] if day1_topics else "Chapter 1"
    results = [{"topic": wrong_topic, "correct": False},
               {"topic": "b", "correct": True}]
    new_plan = RP.adjust_plan(plan, results)
    assert wrong_topic in new_plan.days[0].wrong_questions   # B-F6 requeue
    # something changed
    assert new_plan.days[0].topics != plan.days[0].topics or new_plan.days[0].wrong_questions


# ---------------- checkers ----------------

def test_check_extraction_pass_fail():
    good = [_et("a.txt", "x")]
    assert CK.check_extraction(good).passed
    bad = [ExtractedText(doc=X.lecture_doc("a.txt"), ok=False, error="e")]
    assert not CK.check_extraction(bad).passed


def test_check_kg_pass_and_resources():
    kg = _small_kg()
    assert CK.check_kg(kg).passed
    assert CK.check_resources([1, 2, 3]).passed
    assert not CK.check_resources([1]).passed


def test_check_plan_and_quiz():
    plan = RP.build_review_plan(_small_kg(), exam_date="2026-07-30",
                               free_minutes=120, start_date="2026-07-28")
    assert CK.check_plan_covers(plan).passed
    assert CK.check_plan_budget(plan).passed
    qz = QZ.generate_quiz("t", "a\nb")
    assert CK.check_quiz(qz).passed
    assert not CK.check_quiz(None).passed
