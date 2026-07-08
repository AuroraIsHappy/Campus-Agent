"""Demo B full e2e: run_demo_b end-to-end with deterministic stubs (no network/LLM)."""
import os
import sys
import tempfile

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from campus.demo_b import pipeline as P
from campus.demo_b.types import ExtractedText
from campus.demo_b import extractors as X
from campus.memory.types import KNOWLEDGE


def _seed(tmp):
    files = {
        "lec1.md": "# Chapter 1: Process Scheduling\n- FCFS\n- Round Robin\n- MLFQ",
        "lec2.txt": "# Chapter 2: Memory\n- paging\n- segmentation\n- virtual memory",
        "ignore.xyz": "not a lecture",  # unsupported -> skipped, not counted
    }
    for name, body in files.items():
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
            f.write(body)


def test_run_demo_b_e2e_green():
    tmp = tempfile.mkdtemp()
    _seed(tmp)
    run_dir = os.path.join(tmp, "run")
    r = P.run_demo_b(tmp, "2026-08-15", free_minutes=300, start_date="2026-08-01",
                    run_dir=run_dir)
    assert r.ok, f"expected ok, checks={[c.name + ':' + str(c.passed) for c in r.checks]}"
    assert r.kg_nodes >= 2
    assert r.resource_count >= 3                  # B-F3
    assert r.plan_days == 15                      # 08-01 .. 08-15 inclusive
    assert r.extraction_rate == 1.0               # both .md + .txt succeeded
    for art in ("kg.json", "plan.md", "quiz_day1.json", "Verification.md", "run_result.json"):
        assert os.path.exists(os.path.join(run_dir, art)), art
    assert all(c.passed for c in r.checks)
    ver = open(os.path.join(run_dir, "Verification.md"), encoding="utf-8").read()
    assert "PASS" in ver and "B-F1" in ver and "B-Q3" in ver


def test_run_demo_b_injectable_extractors():
    """Full pipeline with a fake extractor table (no real files needed at all)."""
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "fake.pdf"), "w", encoding="utf-8") as f:
        f.write("binary-placeholder")  # not real PDF; fake extractor ignores content
    fake = {"pdf": lambda p: ExtractedText(doc=X.lecture_doc(p),
            text="# Chapter X\n- alpha\n- beta", ok=True)}
    r = P.run_demo_b(tmp, "2026-08-10", free_minutes=120, start_date="2026-08-05",
                    extractors=fake, run_dir=os.path.join(tmp, "run"))
    assert r.ok and r.kg_nodes >= 2


def test_run_demo_b_records_memory():
    """KG sediments into the KNOWLEDGE layer (cross-session S-MEMORY seam)."""
    from campus.memory.in_memory import InMemoryStore
    mem = InMemoryStore()
    tmp = tempfile.mkdtemp()
    _seed(tmp)
    P.run_demo_b(tmp, "2026-08-15", free_minutes=300, start_date="2026-08-01",
                memory=mem, run_dir=os.path.join(tmp, "run"))
    recs = mem.list_layer(KNOWLEDGE)
    assert len(recs) >= 2                         # KG nodes -> KNOWLEDGE layer
