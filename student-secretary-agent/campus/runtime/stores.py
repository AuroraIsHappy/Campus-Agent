"""Local JSON stores for Phase 7 run/task/artifact persistence."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from campus.runtime.paths import runs_dir, state_dir


def _read_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _now() -> int:
    return int(time.time())


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


@dataclass
class RunRecord:
    id: str
    message: str = ""
    intent: str = ""
    domain: str = ""
    selected_workflow: str = ""
    status: str = "running"
    run_dir: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0


class RunStore:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(state_dir(), "runs.json")

    def create(self, *, message: str = "", intent: str = "", domain: str = "",
               selected_workflow: str = "", context: Optional[dict[str, Any]] = None,
               status: str = "running", run_id: Optional[str] = None,
               run_dir: Optional[str] = None) -> RunRecord:
        rid = run_id or new_run_id()
        now = _now()
        rec = RunRecord(
            id=rid,
            message=message,
            intent=intent,
            domain=domain,
            selected_workflow=selected_workflow,
            status=status,
            run_dir=run_dir or os.path.join(runs_dir(), rid),
            context=context or {},
            created_at=now,
            updated_at=now,
        )
        os.makedirs(rec.run_dir, exist_ok=True)
        data = self._all_map()
        data[rid] = asdict(rec)
        self._save_map(data)
        return rec

    def update(self, run_id: str, **fields) -> Optional[RunRecord]:
        data = self._all_map()
        raw = data.get(run_id)
        if raw is None:
            return None
        raw.update(fields)
        raw["updated_at"] = _now()
        data[run_id] = raw
        self._save_map(data)
        return RunRecord(**raw)

    def get(self, run_id: str) -> Optional[RunRecord]:
        raw = self._all_map().get(run_id)
        return RunRecord(**raw) if raw else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        records = list(self._all_map().values())
        records.sort(key=lambda r: r.get("updated_at", 0), reverse=True)
        return records[:limit]

    def _all_map(self) -> dict[str, dict[str, Any]]:
        data = _read_json(self.path, {})
        return data if isinstance(data, dict) else {}

    def _save_map(self, data: dict[str, dict[str, Any]]) -> None:
        _write_json(self.path, data)


class ArtifactStore:
    def __init__(self, run_store: Optional[RunStore] = None) -> None:
        self.run_store = run_store or RunStore()

    def run_dir(self, run_id: str) -> str:
        rec = self.run_store.get(run_id)
        if rec:
            return rec.run_dir
        return os.path.join(runs_dir(), run_id)

    def write_text(self, run_id: str, name: str, text: str,
                   kind: str = "document") -> dict[str, Any]:
        base = self.run_dir(run_id)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return self._record(run_id, name, path, kind)

    def write_json(self, run_id: str, name: str, data,
                   kind: str = "json") -> dict[str, Any]:
        return self.write_text(run_id, name, json.dumps(data, ensure_ascii=False, indent=2), kind)

    def import_paths(self, run_id: str, paths: list[str]) -> list[dict[str, Any]]:
        out = []
        for path in paths:
            if not path:
                continue
            out.append(self._record(run_id, os.path.basename(path), path, _kind_for(path)))
        return out

    def list(self, run_id: str) -> list[dict[str, Any]]:
        path = os.path.join(self.run_dir(run_id), "artifact_manifest.json")
        data = _read_json(path, {"artifacts": []})
        artifacts = data.get("artifacts", []) if isinstance(data, dict) else []
        if os.path.exists(path) and not any(a.get("path") == path for a in artifacts):
            artifacts = artifacts + [{
                "name": "artifact_manifest.json",
                "path": path,
                "kind": "manifest",
                "created_at": int(os.path.getmtime(path)),
            }]
        return artifacts

    def _record(self, run_id: str, name: str, path: str, kind: str) -> dict[str, Any]:
        item = {"name": name, "path": path, "kind": kind, "created_at": _now()}
        manifest_path = os.path.join(self.run_dir(run_id), "artifact_manifest.json")
        manifest = _read_json(manifest_path, {"run_id": run_id, "artifacts": []})
        artifacts = manifest.get("artifacts", [])
        artifacts = [a for a in artifacts if a.get("path") != path]
        artifacts.append(item)
        manifest = {"run_id": run_id, "artifacts": artifacts}
        _write_json(manifest_path, manifest)
        rec = self.run_store.get(run_id)
        if rec:
            self.run_store.update(run_id, artifacts=artifacts)
        return item


class TaskStore:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(state_dir(), "tasks.json")

    def create(self, *, title: str, body: str = "", status: str = "todo",
               domain: str = "", run_id: str = "", due: str = "",
               metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        tasks = self.list()
        now = _now()
        item = {
            "id": f"task_{now}_{uuid.uuid4().hex[:8]}",
            "title": title,
            "body": body,
            "status": status,
            "domain": domain,
            "run_id": run_id,
            "due": due,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }
        tasks.append(item)
        _write_json(self.path, tasks)
        return item

    def list(self) -> list[dict[str, Any]]:
        data = _read_json(self.path, [])
        return data if isinstance(data, list) else []


def _kind_for(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".md", ".txt"}:
        return "document"
    if ext == ".json":
        return "json"
    return "file"
