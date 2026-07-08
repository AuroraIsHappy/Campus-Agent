"""Discover built-in and locally installed skills without importing Hermes."""
from __future__ import annotations

from pathlib import Path

from campus.runtime.llm_config import hermes_home, real_llm_status

CORE_SKILLS = {
    "academic-search",
    "read-arxiv-paper",
    "academic-researcher",
    "web-access",
    "notion-api",
}


def _skill_dirs(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").exists())


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def installed_skills(home: Path | None = None) -> list[str]:
    return _skill_dirs((home or hermes_home()) / "skills")


def vendor_skills(root: Path | None = None) -> list[str]:
    return _skill_dirs((root or repo_root()) / "skills" / "vendor")


def campus_skills(root: Path | None = None) -> list[str]:
    base = (root or repo_root()) / "skills"
    return sorted(
        p.name for p in base.iterdir()
        if p.is_dir() and p.name != "vendor" and (p / "SKILL.md").exists()
    ) if base.exists() else []


def audit(root: Path | None = None) -> dict:
    root = root or repo_root()
    installed = installed_skills()
    vendor = vendor_skills(root)
    campus = campus_skills(root)
    available = set(installed) | set(vendor) | set(campus)
    external = str(root / "skills")
    external_configured = any(Path(p).resolve() == Path(external).resolve()
                              for p in _external_dirs())
    return {
        "ok": True,
        "repo_root": str(root),
        "hermes_home": str(hermes_home()),
        "external_skill_dir": external,
        "external_dirs": _external_dirs(),
        "external_dir_configured": external_configured,
        "installed": installed,
        "vendor": vendor,
        "campus": campus,
        "missing_core": sorted(CORE_SKILLS - available),
        "llm": real_llm_status("auto"),
    }


def _external_dirs() -> list[str]:
    cfg = hermes_home() / "config.yaml"
    out: list[str] = []
    if not cfg.exists():
        return out
    in_block = False
    for raw in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped == "external_dirs:":
            in_block = True
            continue
        if in_block and stripped.startswith("- "):
            out.append(stripped[2:].strip().strip('"').strip("'"))
            continue
        if in_block and stripped and not raw.startswith((" ", "\t", "-")):
            break
    return out
