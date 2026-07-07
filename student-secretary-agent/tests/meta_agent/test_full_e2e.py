"""L5 end-to-end (P4-MA6): a non-CS user onboards in one session; a fresh session
remembers them. Deterministically demonstrates S-ONBOARD + S-MEMORY + S-MODELCONFIG +
S-PERSONA. No Hermes / no LLM / no network — ask/embed/summarize are stubs.
"""
from __future__ import annotations

from campus.memory.json_store import JsonFileStore
from campus.meta_agent.meta_agent import MetaAgent
from campus.meta_agent.onboarding import OnboardingWizard
from campus.meta_agent.routing import generate_routing, validate_routing, write_routing
from campus.meta_agent.skill_discovery import SkillRegistry
from campus.memory.types import PREFERENCES
from campus.personas.loader import apply_to_prompt, select
from campus.profiles.loader import ProfileLoader


_ANSWERS = {
    "你的身份是？（例如：大二学生）": "大一新生",
    "你的专业是？": "社会学",
    "你的年级或入学年份？（可留空）": "2025",
    "想要哪种秘书风格？默认 / 费曼 / 鲁迅": "鲁迅",
    "你有哪些模型 API key？逗号分隔：glm / deepseek / qwen / openai": "glm",
}


def _canned(answers):
    return lambda q: answers.get(q, "")


def test_non_cs_onboarding_then_cross_session_recall(tmp_path):
    # --- session 1: onboard a non-CS user ---
    profile = OnboardingWizard(_canned(_ANSWERS)).run()
    assert "社会" in profile.major
    assert profile.persona == "lu_xun"
    assert profile.has_non_anthropic_provider

    # persist the onboarding outcome as long-term preferences (what onboarding would save)
    mem_path = str(tmp_path / "memory.json")
    store = JsonFileStore(path=mem_path)
    store.remember(PREFERENCES, "identity", profile.identity)
    store.remember(PREFERENCES, "major", f"专业：{profile.major}")
    store.remember(PREFERENCES, "persona", profile.persona)
    store.remember(PREFERENCES, "skills", ", ".join(profile.recommended_skills))

    # generate + validate + write vendor-neutral routing (S-MODELCONFIG)
    cfg = generate_routing(profile)
    assert validate_routing(cfg) == []
    routing_path = write_routing(cfg, str(tmp_path / "routing.yaml"))

    # Meta-Agent recommends skills + classifies a long task + builds a DAG
    meta = MetaAgent(skill_registry=SkillRegistry(), memory=store)
    recs = meta.recommend_skills("社会学 田野 调研报告", k=5)
    assert recs, "must recommend some skills for the need"
    decision = meta.classify("帮我做一份社会学田野调研报告并排日程")
    assert decision.kind == "long"
    dag = meta.build_dag(decision)
    assert len(dag) == 8
    # acyclic check
    seen = set()
    for node in dag:
        for p in node["parents"]:
            assert p in seen
        seen.add(node["role"])

    # persona overlay carries a detectable style (S-PERSONA)
    persona_prompt = apply_to_prompt(select(profile.persona), "你是学生秘书。")
    assert "[persona: lu_xun]" in persona_prompt and "犀利" in persona_prompt

    # --- session 2: brand-new memory instance remembers the user (S-MEMORY) ---
    store2 = JsonFileStore(path=mem_path)
    assert "社会" in store2.get(PREFERENCES, "major").content
    assert store2.get(PREFERENCES, "persona").content == "lu_xun"
    hits = store2.recall("专业")
    assert hits and any("社会" in h.record.content for h in hits)

    # routing written in session 1 is consumable by the runtime loader in session 2
    provider, model = ProfileLoader(routing_path=routing_path).resolve("planner")
    assert provider != "anthropic"
    assert model
