"""Runtime checks for real LLM/Hermes execution.

The API uses this module to keep demo mode honest: offline mode is explicit and
deterministic, while real mode fails early with a useful diagnostic instead of
silently falling back to fake output.
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SECRET_NAMES = (
    "OPENAI_API_KEY",
    "GLM_API_KEY",
    "ZAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
)


@dataclass
class LLMStatus:
    ok: bool
    mode: str
    hermes_binary: str = ""
    hermes_importable: bool = False
    hermes_import_error: str = ""
    env_files: list[str] = None
    configured_keys: list[str] = None
    readiness: str = ""
    fixes: list[str] = None
    error: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["env_files"] = data["env_files"] or []
        data["configured_keys"] = data["configured_keys"] or []
        data["fixes"] = data["fixes"] or []
        return data


def hermes_home() -> Path:
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).expanduser()
    if sys.platform.startswith("win") and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return Path.home() / ".hermes"


def _dotenv_keys(path: Path) -> list[str]:
    keys: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            name = s.split("=", 1)[0].strip()
            if name in SECRET_NAMES:
                keys.append(name)
    except Exception:
        return []
    return keys


def _env_files() -> list[Path]:
    candidates = [hermes_home() / ".env", Path.home() / ".hermes" / ".env"]
    out: list[Path] = []
    for p in candidates:
        if p.exists() and p not in out:
            out.append(p)
    return out


def _hermes_import_status() -> tuple[bool, str]:
    try:
        __import__("hermes_cli")
        return True, ""
    except Exception as e:
        return False, str(e)


def real_llm_status(mode: str = "auto") -> dict:
    """Return a secret-safe status dict for the real LLM path."""
    binary = shutil.which("hermes") or ""
    importable, import_error = _hermes_import_status()

    files = _env_files()
    keys = sorted({k for p in files for k in _dotenv_keys(p)} | {k for k in SECRET_NAMES if os.environ.get(k)})
    ok = bool(importable and keys)
    fixes: list[str] = []
    if not importable:
        fixes.append("Use a Python environment that can import hermes_cli, or add .venv/Lib/site-packages to PYTHONPATH.")
    if not keys:
        fixes.append("Configure at least one provider key in Hermes .env, for example GLM_API_KEY.")
    if not binary:
        fixes.append("Optional: add hermes CLI to PATH for shell-based operations; API real mode imports hermes_cli directly.")
    readiness = "ready" if ok else "blocked"
    err = "" if ok else "; ".join(fixes)
    return LLMStatus(
        ok=ok,
        mode=mode,
        hermes_binary=binary,
        hermes_importable=importable,
        hermes_import_error=import_error,
        env_files=[str(p) for p in files],
        configured_keys=keys,
        readiness=readiness,
        fixes=fixes,
        error="" if ok else err,
    ).to_dict()


def resolve_mode(mode: Optional[str]) -> str:
    m = (mode or "offline").strip().lower()
    if m not in {"offline", "real", "auto"}:
        return "offline"
    return m


def require_real_llm(mode: Optional[str]) -> tuple[bool, dict]:
    """Check whether the request may call the real LLM path."""
    m = resolve_mode(mode)
    status = real_llm_status(m)
    if m == "offline":
        return False, status
    if m == "auto":
        return bool(status["ok"]), status
    if not status["ok"]:
        status["error"] = (
            "real LLM mode requested, but Hermes/provider is not ready: "
            + (status.get("error") or "unknown error")
        )
    return True, status
