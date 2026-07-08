"""Long-term memory + progress for Demo C.

Phase 8 fix: previously wrote a ``{"preferences": [], "goals": []}`` schema to
``~/.campus/memory.json`` — the SAME path as the L4 ``JsonFileStore`` (which uses
``{"records": [...]}``). The two would corrupt each other's file. Now Demo C
memory delegates to the L4 ``JsonFileStore`` (PREFERENCES / KNOWLEDGE layers),
and only the per-goal progress files (``~/.campus/progress/<slug>.json``) remain
Demo-C-specific (no collision — different path).
"""
from __future__ import annotations
import os, json, datetime as dt
from typing import Any, Dict

from campus.runtime.paths import campus_home

CAMPUS = os.path.expanduser("~/.campus")
PROGRESS_DIR = os.path.join(CAMPUS, "progress")


def _progress_dir() -> str:
    """Progress dir follows CAMPUS_HOME (testable via env override)."""
    try:
        return os.path.join(campus_home(), "progress")
    except Exception:
        return PROGRESS_DIR


def _store():
    """Lazy L4 JsonFileStore (avoids touching ~/.campus on import)."""
    from campus.memory.json_store import JsonFileStore
    from campus.memory.types import PREFERENCES
    return JsonFileStore(), PREFERENCES


def remember(preference: Dict[str, Any]) -> Dict:
    """Append a free-form preference entry to the L4 PREFERENCES layer."""
    store, layer = _store()
    content = json.dumps(preference, ensure_ascii=False)
    store.remember(layer=layer, key="demo_c_preference",
                   content=content, metadata=preference)
    # return a shape compatible with the old CLI callers
    return {"ok": True, "preference": preference,
            "preferences_total": len(store.list_layer(layer))}


def set_goal(goal: str) -> Dict:
    """Register a long-term learning goal in the L4 PREFERENCES layer (idempotent)."""
    store, layer = _store()
    # dedup: don't re-add a goal that already exists
    existing = store.list_layer(layer)
    if any(r.key == f"goal:{goal}" for r in existing):
        return {"ok": True, "goal": goal, "already_exists": True}
    store.remember(layer=layer, key=f"goal:{goal}",
                   content=goal, metadata={"kind": "learning_goal"})
    return {"ok": True, "goal": goal}


def log_progress(goal_slug: str, day: int, status: str, note: str = "") -> Dict:
    """Idempotent per-day progress (re-writing a day overwrites, not duplicates).

    Progress files stay under ``~/.campus/progress/`` — no collision with memory.json.
    """
    path = os.path.join(_progress_dir(), f"{goal_slug}.json")
    prog = _read_json(path, {"goal_slug": goal_slug, "days": {}})
    prog["days"][str(day)] = {
        "status": status, "note": note,
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
    }
    _write_json(path, prog)
    return prog


def show() -> Dict:
    """Return all preferences + goals from the L4 store (cross-session)."""
    store, layer = _store()
    records = store.list_layer(layer)
    prefs = [r.metadata for r in records if r.key == "demo_c_preference"]
    goals = [r.content for r in records if r.key.startswith("goal:")]
    return {"preferences": prefs, "goals": goals}


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


def _main():
    import argparse
    ap = argparse.ArgumentParser(description="Long-term memory + progress for Demo C.")
    ap.add_argument("--remember", metavar="k=v",
                    help="append a preference, e.g. --remember learning=linux")
    ap.add_argument("--show", action="store_true", help="print L4 preferences + goals")
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
