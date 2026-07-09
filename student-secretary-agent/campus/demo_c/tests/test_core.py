"""Unit tests for Demo C deterministic cores (no LLM / no network)."""
import os, sys, json, tempfile
from datetime import date
PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)
from campus.demo_c.types import Resource
from campus.demo_c import scheduler, ranker, researcher, quiz, memory


def test_types_validation():
    r = Resource(title="t", url="u")
    assert r.source_type == "doc"
    raised = False
    try:
        Resource(title="t", url="u", source_type="bad")
    except ValueError:
        raised = True
    assert raised


def test_scheduler_layout():
    r = Resource(title="X", url="u")
    p = scheduler.build_plan(r, goal="g", days=10, slot_minutes=20)
    assert len(p.days) == 10
    assert p.days[0].n == 1 and p.days[9].n == 10
    assert "X" in p.to_markdown()


def test_scheduler_weekdays_only():
    r = Resource(title="X", url="u")
    p = scheduler.build_plan(r, goal="g", days=5, start_date=date(2026, 7, 4), weekdays_only=True)
    for d in p.days:
        y, m, dd = map(int, d.date.split("-"))
        assert date(y, m, dd).weekday() < 5  # Mon-Fri only


def test_ranker_old_penalty():
    new = Resource(title="Linux", url="u", provider="MIT", year=2024, source_type="course", difficulty="beginner")
    old = Resource(title="Linux", url="u", provider="MIT", year=2001, source_type="doc", difficulty="advanced")
    assert ranker.score(new, "learn linux") > ranker.score(old, "learn linux")


def test_ranker_pick_order():
    a = Resource(title="Linux Course", url="u", provider="MIT", year=2024, source_type="course", difficulty="beginner")
    b = Resource(title="Random Blog", url="u", provider="blog", year=2010, source_type="blog", difficulty="advanced")
    res = ranker.rank([b, a], "learn linux")
    assert res.recommendation.resource.title == "Linux Course"


def test_researcher_parse():
    fixture = "{\"resources\":[{\"title\":\"A\",\"url\":\"http://a\",\"source_type\":\"course\",\"year\":2024,\"difficulty\":\"beginner\"},{\"title\":\"\",\"url\":\"x\"},{\"title\":\"B\",\"url\":\"http://b\",\"source_type\":\"bad\"}]}"
    rs = researcher.parse_resources(fixture)
    assert len(rs) == 2
    assert rs[0].title == "A" and rs[0].source_type == "course"
    assert rs[1].source_type == "doc"  # bad normalized


def test_quiz_parse():
    fixture = "{\"questions\":[{\"q\":\"Q1\",\"answer\":\"A1\",\"explanation\":\"E1\"},{\"q\":\"\",\"answer\":\"x\"}]}"
    q = quiz.parse_quiz(fixture, topic="t")
    assert len(q.questions) == 1
    assert q.questions[0].q == "Q1" and q.questions[0].answer == "A1"


def test_memory_idempotent(monkeypatch=None):
    tmp = tempfile.mkdtemp()
    # Phase 8: demo_c memory now uses CAMPUS_HOME (L4 JsonFileStore), not a
    # module-level MEMORY path. Set CAMPUS_HOME so both memory + progress land in tmp.
    if monkeypatch is not None:
        monkeypatch.setenv("CAMPUS_HOME", tmp)
    else:
        os.environ["CAMPUS_HOME"] = tmp
    try:
        memory.set_goal("linux")
        memory.set_goal("linux")
        assert memory.show()["goals"] == ["linux"]
        memory.log_progress("linux", 1, "done")
        memory.log_progress("linux", 1, "done2")
        prog = json.loads(open(os.path.join(tmp, "progress", "linux.json"), encoding="utf-8").read())
        assert len(prog["days"]) == 1
    finally:
        os.environ.pop("CAMPUS_HOME", None)
