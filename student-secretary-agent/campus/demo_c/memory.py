"""Long-term memory + progress for Demo C (local JSON under ~/.campus/)."""
from __future__ import annotations
import os, json, datetime as dt
from typing import Any, Dict

CAMPUS = os.path.expanduser("~/.campus")
MEMORY = os.path.join(CAMPUS, "memory.json")
PROGRESS_DIR = os.path.join(CAMPUS, "progress")


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except Exception:
        return default


def _write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def remember(preference: Dict[str, Any]) -> Dict:
    """Append a free-form preference entry (e.g. {"learning": "linux"})."""
    mem = _read_json(MEMORY, {"preferences": [], "goals": []})
    entry = {"ts": dt.datetime.now().isoformat(timespec="seconds"), **preference}
    mem.setdefault("preferences", []).append(entry)
    _write_json(MEMORY, mem)
    return mem


def set_goal(goal: str) -> Dict:
    mem = _read_json(MEMORY, {"preferences": [], "goals": []})
    if goal not in mem.setdefault("goals", []):
        mem["goals"].append(goal)
    _write_json(MEMORY, mem)
    return mem


def log_progress(goal_slug: str, day: int, status: str, note: str = "") -> Dict:
    """Idempotent per-day progress (re-writing a day overwrites, not duplicates)."""
    path = os.path.join(PROGRESS_DIR, f"{goal_slug}.json")
    prog = _read_json(path, {"goal_slug": goal_slug, "days": {}})
    prog["days"][str(day)] = {
        "status": status, "note": note,
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(path, prog)
    return prog


def show() -> Dict:
    return _read_json(MEMORY, {"preferences": [], "goals": []})


def _main():
    import argparse
    ap = argparse.ArgumentParser(description="Long-term memory + progress for Demo C.")
    ap.add_argument("--remember", metavar="k=v",
                    help="append a preference, e.g. --remember learning=linux")
    ap.add_argument("--show", action="store_true", help="print ~/.campus/memory.json")
    ap.add_argument("--goal", help="register a long-term goal")
    args = ap.parse_args()
    if args.show:
        print(json.dumps(show(), ensure_ascii=False, indent=2))
    elif args.goal:
        print(json.dumps(set_goal(args.goal), ensure_ascii=False, indent=2))
    elif args.remember:
        pref: Dict[str, Any] = {}
        if "=" in args.remember:
            k, v = args.remember.split("=", 1)
            pref[k.strip()] = v.strip()
        else:
            pref["note"] = args.remember
        print(json.dumps(remember(pref), ensure_ascii=False, indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    _main()
