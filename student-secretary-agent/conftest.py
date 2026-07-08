"""Pytest root conftest: make ``campus`` importable for all tests under this dir.

Also makes the vendored ``hermes_cli`` package importable when tests run under a
Python that did not install hermes-agent (e.g. the conda base env used as the
test runner because the project ``.venv`` python.exe is blocked by Windows
Device Guard). The venv's ``site-packages`` is appended (back of sys.path) so it
only fills gaps (hermes_cli) and never shadows the runner's own packages. This
is a no-op when hermes_cli is already importable.
"""
import importlib.util
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if importlib.util.find_spec("hermes_cli") is None:
    _VENV_SITE = os.path.join(_ROOT, ".venv", "Lib", "site-packages")
    if os.path.isdir(_VENV_SITE) and _VENV_SITE not in sys.path:
        sys.path.append(_VENV_SITE)
