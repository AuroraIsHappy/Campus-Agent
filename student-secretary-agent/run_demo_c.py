"""Run any campus.demo_c module CLI from repo root (no cd / no PYTHONPATH).

Usage:
  python.exe run_demo_c.py <module> [args...]
  e.g. python.exe run_demo_c.py scheduler "MIT Missing Semester" --days 5
       python.exe run_demo_c.py orchestrator "我想学 Linux"
"""
import sys, os, importlib
HERE = os.path.dirname(os.path.abspath(__file__))  # student-secretary-agent/
if HERE not in sys.path:
    sys.path.insert(0, HERE)

CMDS = ["scheduler", "researcher", "ranker", "quiz", "memory", "orchestrator"]

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print("usage: run_demo_c.py <" + "|".join(CMDS) + "> [args...]", file=sys.stderr)
        sys.exit(2)
    name = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    mod = importlib.import_module(f"campus.demo_c.{name}")
    if not hasattr(mod, "_main"):
        print(f"module {name} has no _main()", file=sys.stderr); sys.exit(2)
    mod._main()

if __name__ == "__main__":
    main()
