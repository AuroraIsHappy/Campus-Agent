"""Deterministic Demo A turn function for offline demos and API tests."""
from __future__ import annotations

import dataclasses
import json

from campus.demo_a.role_turns import persist_role
from campus.odyssey.orchestrator import TurnOutcome
from campus.runtime.ports import APPROVE, VERDICT_KEY


def make_offline_turn(run_dir: str, ctx: dict):
    def turn(profile, task):
        role = profile.get("role") or task.assignee or ""
        brief = ctx["brief"]
        topic = brief.topic or "校园低碳实践"
        region = brief.region or "本地高校社区"
        targets = [
            {
                "name": f"{region}青年志愿服务中心",
                "visit_reason": f"了解{topic}的社区组织与志愿服务经验",
                "contact_source": "offline-demo",
                "url": "https://example.com/youth-service",
                "score": 0.91,
            },
            {
                "name": f"{region}生态文明教育基地",
                "visit_reason": f"观察{topic}的展示、讲解与实践活动设计",
                "contact_source": "offline-demo",
                "url": "https://example.com/eco-education",
                "score": 0.88,
            },
            {
                "name": f"{region}街道社会实践办公室",
                "visit_reason": f"对接{topic}调研中的安全、审批和群众访谈安排",
                "contact_source": "offline-demo",
                "url": "https://example.com/community-office",
                "score": 0.85,
            },
        ]
        if role == "planner":
            summary = (
                f"# {topic}社会实践计划\n\n"
                "- Research: 明确调研问题与样本格式\n"
                "- Verify: 核验参访对象与公开联系方式\n"
                "- Rank: 按匹配度、安全性、可达性排序\n"
                "- Write: 生成策划案、预算、时间表、安全预案\n"
                "- Review: 人工确认后再外联\n"
                "- Email: 仅生成草稿，不自动发送\n"
            )
            meta = {}
        elif role == "researcher":
            summary = "```json\n" + json.dumps(targets, ensure_ascii=False) + "\n```"
            meta = {"payload": targets}
        elif role == "source_verifier":
            verified = [{**t, "verified": True, "evidence": "offline demo source"} for t in targets]
            summary = "```json\n" + json.dumps(verified, ensure_ascii=False) + "\n```"
            meta = {"payload": verified}
        elif role == "source_ranker":
            summary = "```json\n" + json.dumps(targets, ensure_ascii=False) + "\n```"
            meta = {"payload": targets}
        elif role == "writer":
            summary = (
                f"# {topic}社会实践策划案\n\n"
                f"## 背景与目标\n围绕{region}开展{topic}调研，形成可执行的参访与访谈成果。\n\n"
                "## 参访对象\n" + "\n".join(f"- {t['name']}：{t['visit_reason']}" for t in targets) + "\n\n"
                "## 时间表\n- 第1天：行前培训与资料整理\n- 第2天：集中参访与访谈\n- 第3天：复盘、成稿与展示\n\n"
                "## 预算\n- 交通费：300元\n- 餐饮费：240元\n- 材料费：120元\n\n"
                "## 安全预案\n统一集合签到，保留紧急联系人，不进行未确认地点的单独行动。\n"
            )
            meta = {}
        elif role == "email":
            summary = "\n\n".join(
                f"致 {t['name']}：\n您好，我们计划开展{topic}社会实践，希望预约一次交流参访。"
                for t in targets
            )
            meta = {}
        else:
            summary = "APPROVE\noffline demo checks passed."
            meta = {VERDICT_KEY: APPROVE}
        out = TurnOutcome(summary=summary, metadata=meta, tokens=max(1, len(summary) // 4))
        persist_role(role, out, ctx, run_dir)
        return out
    return turn
