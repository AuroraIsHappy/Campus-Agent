#!/usr/bin/env python3
"""Demo A CLI driver (T10): real-LLM run of the 社会实践策划案 pipeline.

Mirrors run_demo_c.py. Produces artifacts under ~/.campus/runs/demo_a-<ts>/ and
prints the awaiting_human prompt -- decision B1: drafts only, NOTHING is sent.

Usage:
  .venv/Scripts/python.exe run_demo_a.py --sample sample.txt \
      --topic 航天科普 --region 北京 --window "2026年7月"
"""
import argparse
import json
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Demo A: 社会实践策划案 + 外联对象 + 邮件草稿 (drafts only, no send)")
    ap.add_argument("--sample", default="", help="path to a sample proposal (text)")
    ap.add_argument("--topic", default="社会实践", help="activity topic")
    ap.add_argument("--region", default="", help="region/city")
    ap.add_argument("--window", default="", help="time window, e.g. 2026年7月")
    ap.add_argument("--runs-base", default=None, help="override runs dir base")
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from campus.demo_a import pipeline, sample_extractor
    from campus.demo_a.types import Brief, SampleSpec

    sample_text = ""
    if args.sample and os.path.exists(args.sample):
        with open(args.sample, encoding="utf-8") as f:
            sample_text = f.read()
    sample = (sample_extractor.extract_sample(sample_text)
              if sample_text else SampleSpec())

    run_dir = pipeline.new_run_dir(args.runs_base) if args.runs_base else None
    res = pipeline.run_demo_a(
        sample,
        Brief(topic=args.topic, region=args.region, window=args.window),
        run_dir=run_dir)

    print("=" * 60)
    print(f"Run dir : {res.run_dir}")
    print(f"Targets : {res.outreach_count}  | Email segments: {res.email_segments}")
    print(f"Checks  : " + ", ".join(f"{c.name}={'PASS' if c.passed else 'FAIL'}"
                                    for c in res.checks))
    print(f"Debates : " + ", ".join(f"{d['pair']}={d['outcome']}" for d in res.debates))
    print(f"Status  : {res.final_status}")
    print("-> awaiting your confirmation. NOTHING was sent (B1: draft only).")
    print("=" * 60)
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
