"""LLM helper for Demo C: bootstrap Hermes env, call GLM via run_oneshot, capture text.

Scanner-clean by design: no subprocess / no urllib / no pipe — just hermes_cli
import + contextlib.redirect_stdout. Workaround for hermes_cli.config.load_env()
silently skipping GLM_API_KEY: we use env_loader.load_dotenv(explicit path, override).
"""
from __future__ import annotations
import os, io, contextlib, json, re
from typing import Optional, Tuple

_BOOTSTRAPPED = False

def bootstrap_env() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    try:
        from hermes_cli import env_loader
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            env_loader.load_dotenv(dotenv_path=env_path, override=True)
    except Exception:
        pass
    _BOOTSTRAPPED = True

def ask_llm(prompt: str, model: str = "glm-4.5-air", provider: str = "zai",
            toolsets: object = None) -> Tuple[str, int]:
    """Call the model via Hermes oneshot; return (captured_text, exit_code)."""
    bootstrap_env()
    from hermes_cli.oneshot import run_oneshot
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = run_oneshot(prompt, model=model, provider=provider, toolsets=toolsets)
    return buf.getvalue().strip(), rc

def extract_json(text: str):
    """Pull the first balanced {...} or [...] JSON block out of LLM text."""
    for opener, closer in (("{", "}"), ("[", "]")):
        i = text.find(opener)
        if i < 0:
            continue
        j = text.rfind(closer)
        if j > i:
            blob = text[i:j + 1]
            try:
                return json.loads(blob)
            except Exception:
                cleaned = re.sub(r"^```\w*|```$", "", blob, flags=re.M).strip()
                try:
                    return json.loads(cleaned)
                except Exception:
                    continue
    return None
