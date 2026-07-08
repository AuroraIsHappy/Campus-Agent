"""Auto-learn: review user corrections daily, update/create skills or preferences.

Phase 8 Step 4. The flow:
  1. User submits a correction on a run output (POST /agent/runs/{id}/correction)
  2. CorrectionStore records it
  3. Daily (or manual trigger), run_auto_learn:
     a. Pulls unprocessed corrections
     b. Clusters by domain + similarity
     c. LLM classifies each cluster: preference / skill-defect / fact
     d. preference → write to PREFERENCES memory layer
     e. skill-defect → create/update a SKILL.md
     f. fact → write to KNOWLEDGE memory layer
  4. LearnReport persisted as an artifact

Reuses: scheduler thread (daily hook), PREFERENCES/KNOWLEDGE layers (JsonFileStore),
registry.py filesystem scanner (auto-discovers new skill dirs), ask_llm for analysis.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from campus.runtime.paths import state_dir
from campus.runtime.stores import ArtifactStore, RunStore

__all__ = ["CorrectionStore", "Correction", "AutoLearner", "LearnReport",
           "SkillCreator"]


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


@dataclass
class Correction:
    run_id: str
    domain: str
    original: str
    corrected: str
    reason: str = ""
    ts: int = 0
    processed: bool = False
    id: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "run_id": self.run_id, "domain": self.domain,
                "original": self.original, "corrected": self.corrected,
                "reason": self.reason, "ts": self.ts, "processed": self.processed}


class CorrectionStore:
    """Persisted JSON store for user corrections on run outputs."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(state_dir(), "corrections.json")

    def add(self, *, run_id: str, domain: str, original: str,
            corrected: str, reason: str = "") -> Correction:
        corrections = self.list()
        now = int(time.time())
        c = Correction(
            id=f"corr_{now}_{len(corrections)}",
            run_id=run_id, domain=domain, original=original,
            corrected=corrected, reason=reason, ts=now)
        corrections.append(c.to_dict())
        _write_json(self.path, corrections)
        return c

    def list(self, include_processed: bool = True) -> list[dict]:
        data = _read_json(self.path, [])
        if not include_processed:
            return [c for c in data if not c.get("processed")]
        return data

    def unprocessed(self) -> list[Correction]:
        return [Correction(**c) for c in self.list(include_processed=False)]

    def mark_processed(self, correction_ids: list[str]) -> None:
        corrections = self.list()
        ids = set(correction_ids)
        for c in corrections:
            if c.get("id") in ids:
                c["processed"] = True
        _write_json(self.path, corrections)

    def count(self) -> int:
        return len(self.list())


@dataclass
class LearnReport:
    ok: bool = True
    processed: int = 0
    preferences_written: int = 0
    skills_created: int = 0
    skills_updated: int = 0
    knowledge_written: int = 0
    details: list[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "processed": self.processed,
                "preferences_written": self.preferences_written,
                "skills_created": self.skills_created,
                "skills_updated": self.skills_updated,
                "knowledge_written": self.knowledge_written,
                "details": self.details, "error": self.error}


class SkillCreator:
    """Create or update SKILL.md files under the campus skills directory.

    New skills are written to ``<repo>/skills/<name>/SKILL.md``; the existing
    ``registry.py`` filesystem scanner auto-discovers them (no registration code
    needed). Updates append correction-derived instructions to an existing file.
    """

    def __init__(self, skills_dir: Optional[str] = None) -> None:
        if skills_dir is None:
            # default: <repo>/skills/ (campus-authored tier)
            repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.skills_dir = os.path.join(repo, "skills")
        else:
            self.skills_dir = skills_dir

    def _skill_path(self, name: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower())[:40]
        return os.path.join(self.skills_dir, safe, "SKILL.md")

    def create_or_update(self, *, name: str, trigger: str, instructions: str,
                         examples: list[str] = None) -> dict:
        """Create a new SKILL.md or append instructions to an existing one.

        Returns {created: bool, path: str, name: str}.
        """
        path = self._skill_path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        created = not os.path.exists(path)
        ts = time.strftime("%Y-%m-%d %H:%M")
        block = f"""
## Auto-learned ({ts})

**Trigger**: {trigger}

**Instructions**:
{instructions}
"""
        if examples:
            block += "\n**Examples**:\n" + "\n".join(f"- {e}" for e in examples) + "\n"

        if created:
            content = f"""---
name: {name}
description: {trigger}
---

# {name}

Auto-created by the auto-learn system from user corrections.
{block}
"""
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            content += block

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"created": created, "path": path, "name": name}

    def list_skills(self) -> list[str]:
        if not os.path.isdir(self.skills_dir):
            return []
        return sorted(d for d in os.listdir(self.skills_dir)
                      if os.path.isfile(os.path.join(self.skills_dir, d, "SKILL.md")))


class AutoLearner:
    """Review corrections, classify via LLM, write to memory or skills.

    Usage::
        learner = AutoLearner()
        report = learner.run()  # processes all unprocessed corrections
    """

    def __init__(self, *, corrections: Optional[CorrectionStore] = None,
                 skill_creator: Optional[SkillCreator] = None) -> None:
        self.corrections = corrections or CorrectionStore()
        self.skill_creator = skill_creator or SkillCreator()

    def run(self, *, use_llm: bool = True) -> LearnReport:
        """Process all unprocessed corrections. Returns a LearnReport."""
        report = LearnReport()
        unprocessed = self.corrections.unprocessed()
        if not unprocessed:
            report.ok = True
            return report

        # cluster by domain
        clusters: dict[str, list[Correction]] = {}
        for c in unprocessed:
            clusters.setdefault(c.domain or "general", []).append(c)

        processed_ids: list[str] = []
        for domain, corrections in clusters.items():
            try:
                result = self._process_cluster(domain, corrections, use_llm=use_llm)
                report.processed += len(corrections)
                report.preferences_written += result.get("preferences_written", 0)
                report.skills_created += result.get("skills_created", 0)
                report.skills_updated += result.get("skills_updated", 0)
                report.knowledge_written += result.get("knowledge_written", 0)
                report.details.append({"domain": domain, "count": len(corrections), **result})
                processed_ids.extend(c.id for c in corrections)
            except Exception as e:
                report.details.append({"domain": domain, "error": str(e)})

        self.corrections.mark_processed(processed_ids)
        self._persist_report(report)
        return report

    def _process_cluster(self, domain: str, corrections: list[Correction],
                         *, use_llm: bool) -> dict:
        """Classify a cluster and write the derived learning."""
        result = {"preferences_written": 0, "skills_created": 0,
                  "skills_updated": 0, "knowledge_written": 0}

        # build a summary of corrections for LLM analysis
        summary_parts = []
        for c in corrections:
            summary_parts.append(
                f"- 原始输出: {c.original[:200]}\n  用户修正: {c.corrected[:200]}\n  原因: {c.reason}")
        summary = "\n".join(summary_parts)

        classification = None
        if use_llm:
            classification = self._llm_classify(domain, summary)

        if classification is None:
            # offline fallback: simple heuristic — if multiple corrections in same domain, it's a skill defect
            if len(corrections) >= 2:
                classification = {"type": "skill", "name": f"{domain}-corrections",
                                  "instructions": "基于用户多次修正,需改进此领域输出质量。"}
            else:
                classification = {"type": "preference", "content": corrections[0].corrected[:500]}

        ctype = classification.get("type", "preference")
        if ctype == "preference":
            self._write_preference(domain, classification, corrections)
            result["preferences_written"] += 1
        elif ctype == "skill":
            created = self._write_skill(classification, corrections)
            if created:
                result["skills_created"] += 1
            else:
                result["skills_updated"] += 1
        elif ctype == "fact":
            self._write_knowledge(domain, classification, corrections)
            result["knowledge_written"] += 1

        return result

    def _llm_classify(self, domain: str, summary: str) -> Optional[dict]:
        """Ask the LLM to classify a correction cluster."""
        try:
            from campus.runtime.llm_turn import ask_llm, extract_json
            from campus.runtime.llm_config import require_real_llm
            real, _ = require_real_llm("real")
            if not real:
                return None
            prompt = (
                f"你是学习分析助手。分析以下用户对「{domain}」领域 agent 输出的修正,判断属于哪类:\n"
                f"- preference: 用户个人偏好/习惯(应写入偏好记忆)\n"
                f"- skill: agent 能力缺陷,反复出错(应创建/更新 skill)\n"
                f"- fact: 一次性事实纠正(应写入知识记忆)\n\n"
                f"修正记录:\n{summary}\n\n"
                f"返回 JSON: {{\"type\": \"preference|skill|fact\", "
                f"\"name\": \"skill名称(如type=skill)\", "
                f"\"content\": \"要记住的偏好/知识\", "
                f"\"instructions\": \"skill指令(如type=skill)\", "
                f"\"examples\": [\"示例1\"]}}")
            raw, rc = ask_llm(prompt, model="glm-4.6", provider="zai")
            if rc != 0 or not raw:
                return None
            parsed = extract_json(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _write_preference(self, domain: str, classification: dict,
                          corrections: list[Correction]) -> None:
        from campus.memory.json_store import JsonFileStore
        from campus.memory.types import PREFERENCES
        store = JsonFileStore()
        content = classification.get("content") or corrections[0].corrected[:500]
        store.remember(layer=PREFERENCES, key=f"auto_pref:{domain}",
                       content=content,
                       metadata={"domain": domain, "source": "auto_learn",
                                 "correction_count": len(corrections),
                                 "derived_at": int(time.time())})

    def _write_knowledge(self, domain: str, classification: dict,
                         corrections: list[Correction]) -> None:
        from campus.memory.json_store import JsonFileStore
        from campus.memory.types import KNOWLEDGE
        store = JsonFileStore()
        content = classification.get("content") or corrections[0].corrected[:500]
        store.remember(layer=KNOWLEDGE, key=f"auto_fact:{domain}",
                       content=content,
                       metadata={"domain": domain, "source": "auto_learn",
                                 "correction_count": len(corrections)})

    def _write_skill(self, classification: dict,
                     corrections: list[Correction]) -> bool:
        """Create or update a skill. Returns True if created (False if updated)."""
        name = classification.get("name") or f"corrections-{int(time.time())}"
        trigger = classification.get("content") or corrections[0].reason or "用户修正"
        instructions = classification.get("instructions") or "根据用户修正改进输出质量。"
        examples = classification.get("examples") or [c.corrected[:100] for c in corrections[:3]]
        result = self.skill_creator.create_or_update(
            name=name, trigger=trigger, instructions=instructions, examples=examples)
        return result["created"]

    def _persist_report(self, report: LearnReport) -> None:
        """Write the learn report as a run artifact."""
        try:
            runs = RunStore()
            artifacts = ArtifactStore(runs)
            rec = runs.create(message="auto-learn daily review",
                              intent="auto_learn", domain="meta",
                              selected_workflow="auto_learn", status="done")
            artifacts.write_text(rec.id, "LearnReport.md",
                                 f"# Auto-Learn Report\n\n"
                                 f"- processed: {report.processed}\n"
                                 f"- preferences written: {report.preferences_written}\n"
                                 f"- skills created: {report.skills_created}\n"
                                 f"- skills updated: {report.skills_updated}\n"
                                 f"- knowledge written: {report.knowledge_written}\n")
            artifacts.write_json(rec.id, "learn_report.json", report.to_dict())
            runs.update(rec.id, status="done", result=report.to_dict())
        except Exception:
            pass  # never let report persistence fail the learn cycle
