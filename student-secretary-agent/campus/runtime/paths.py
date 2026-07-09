"""Filesystem locations for Campus runtime state."""
from __future__ import annotations

import os


def campus_home() -> str:
    return os.path.abspath(os.path.expanduser(os.environ.get("CAMPUS_HOME", "~/.campus")))


def runs_dir() -> str:
    return os.path.join(campus_home(), "runs")


def state_dir() -> str:
    return os.path.join(campus_home(), "state")
