"""L5 Meta-Agent unit tests (P4-MA1..MA5). Pure stdlib; no Hermes / no LLM / no network."""
from __future__ import annotations

import pytest

from campus.meta_agent.meta_agent import LONG_DAG, MetaAgent
from campus.meta_agent.onboarding import OnboardingWizard, recommend_skills
from campus.meta_agent.routing import (
    ALL_ROLES, HEAVY_ROLES, generate_routing, validate_routing, write_routing,
)
from campus.meta_agent.skill_discovery import SkillRegistry, reliability_score
from campus.meta_agent.skill_pack import SKILL_PACK_COUNT_MIN, build_manifest, load_skill_pack
from campus.meta_agent.types import (
    NON_ANTHROPIC_PROVIDERS, RoutingConfig, SkillEntry, UserProfile,
)
from campus.profiles.loader import ProfileLoader


# --- P4-MA1 skill pack --------------------------------------------------------

def test_skill_pack_has_100_plus_and_valid():
    pack = load_skill_pack()
    assert len(pack) >= SKILL_PACK_COUNT_MIN >= 100
    sources = {e.source for e in pack}
    assert sources == {"hermes", "cli_anything", "campus"}
    for e in pack:
        assert e.name and e.source in sources and e.category
        assert 0.0 <= e.reliability() <= 1.0


def test_skill_pack_reliability_by_source():
    pack = {e.name: e for e in build_manifest()}
    # campus + hermes are installed -> full reliability; cli_anything is not -> lower
    assert pack["research_web"].reliability() == pytest.approx(1.0)
    assert pack["memory"].reliability() == pytest.approx(1.0)
    cli = next(e for e in pack.values() if e.source == "cli_anything")
    assert cli.installed is False
    assert cli.reliability() == pytest.approx(0.5)   # maintained(0.3)+source(0.2)


# --- P4-MA2 skill discovery ---------------------------------------------------

def test_discovery_ranks_and_picks_mode():
    reg = SkillRegistry()
    # exact category match dominates
    best = reg.best("复习计划")
    assert best is not None and best.name == "exam_plan"
    top = reg.discover("research", k=3)
    assert top and top[0][0].name == "research_web"
    # mode selection
    assert reg.pick_mode(reg.best("research")) == "direct"               # installed
    cli_entry = SkillEntry(name="x", source="cli_anything", installed=False)
    assert reg.pick_mode(cli_entry) == "install_or_compose"
    assert reliability_score(cli_entry) == cli_entry.reliability()


def test_discovery_empty_need_returns_nothing():
    reg = SkillRegistry()
    assert reg.discover("") == []
    assert reg.search("") == []
    assert reg.best("zzz nosuchskilltoken") is None


# --- P4-MA3 routing (S-MODELCONFIG) -------------------------------------------

def _profile_with(providers):
    return UserProfile(provider_keys={p: "set" for p in providers})


def test_generate_routing_uses_non_anthropic_provider_and_tiers():
    cfg = generate_routing(_profile_with(["glm", "deepseek"]))
    assert cfg.has_non_anthropic_provider
    # default provider resolved to a known non-Anthropic alias
    assert cfg.default["provider"] in NON_ANTHROPIC_PROVIDERS
    # every registered role mapped; heavy roles get the strong model
    assert set(cfg.roles) == set(ALL_ROLES)
    for heavy in HEAVY_ROLES:
        assert cfg.roles[heavy]["model"] != cfg.roles["sub_agent"]["model"]


def test_routing_write_and_loader_readback(tmp_path):
    cfg = generate_routing(_profile_with(["glm"]))
    assert validate_routing(cfg) == []                       # valid
    path = write_routing(cfg, str(tmp_path / "routing.yaml"))
    # the produced YAML is consumable by the existing ProfileLoader (S-MODELCONFIG: editable)
    loader = ProfileLoader(routing_path=path)
    provider, model = loader.resolve("planner")
    assert provider in NON_ANTHROPIC_PROVIDERS
    assert model


def test_validate_routing_rejects_anthropic_only():
    cfg = RoutingConfig(schema=1, default={"provider": "anthropic", "model": "claude"},
                        roles={"planner": {"provider": "anthropic", "model": "claude"}})
    problems = validate_routing(cfg)
    assert any("non-Anthropic" in p for p in problems)


def test_validate_routing_rejects_missing_fields():
    cfg = RoutingConfig(schema=1, default={"provider": "", "model": ""}, roles={})
    assert validate_routing(cfg) != []


# --- P4-MA4 onboarding --------------------------------------------------------

def _canned(answers):
    return lambda q: answers.get(q, "")


def test_onboarding_builds_full_profile():
    answers = {
        "你的身份是？（例如：大二学生）": "大三学生",
        "你的专业是？": "计算机科学",
        "你的年级或入学年份？（可留空）": "2024",
        "想要哪种秘书风格？默认 / 费曼 / 鲁迅": "费曼",
        "你有哪些模型 API key？逗号分隔：glm / deepseek / qwen / openai": "glm, deepseek",
    }
    prof = OnboardingWizard(_canned(answers)).run()
    assert prof.identity == "大三学生"
    assert "计算机" in prof.major
    assert prof.persona == "feynman"
    assert set(prof.provider_keys) == {"zai", "deepseek"}   # glm alias -> zai
    assert prof.has_non_anthropic_provider
    # STEM major -> research/code recommendations
    assert "research_web" in prof.recommended_skills


def test_onboarding_chinese_comma_and_unknown_persona_default():
    answers = {
        "你的身份是？（例如：大二学生）": "大一",
        "你的专业是？": "社会学",
        "你的年级或入学年份？（可留空）": "",
        "想要哪种秘书风格？默认 / 费曼 / 鲁迅": "钢铁侠",
        "你有哪些模型 API key？逗号分隔：glm / deepseek / qwen / openai": "qwen，openai",
    }
    prof = OnboardingWizard(_canned(answers)).run()
    assert prof.persona == "default"                          # unknown -> default
    assert set(prof.provider_keys) == {"qwen", "openai"}
    # non-STEM -> scheduler/email recommendations
    assert "draft_email" in recommend_skills(prof)


def test_onboarding_collects_birthday():
    from campus.meta_agent.onboarding import _normalize_birthday
    answers = {
        "你的身份是？（例如：大二学生）": "大二",
        "你的专业是？": "物理",
        "你的年级或入学年份？（可留空）": "",
        "想要哪种秘书风格？默认 / 费曼 / 鲁迅": "默认",
        "你有哪些模型 API key？逗号分隔：glm / deepseek / qwen / openai": "",
        "你的生日是？（可留空，格式 MM-DD，用于提醒）": "7月9日",
    }
    prof = OnboardingWizard(_canned(answers)).run()
    assert prof.birthday == "07-09"                           # Chinese form normalized
    d = prof.to_public_dict()
    assert d["birthday"] == "07-09"                           # exported (not redacted)
    assert d["anniversaries"] == []                           # default empty, exported


def test_normalize_birthday_variants():
    from campus.meta_agent.onboarding import _normalize_birthday
    assert _normalize_birthday("07-09") == "07-09"
    assert _normalize_birthday("7-9") == "07-09"              # zero-pad
    assert _normalize_birthday("2001-07-09") == "07-09"       # drop year
    assert _normalize_birthday("7月9日") == "07-09"
    assert _normalize_birthday("") == ""                      # blank -> blank
    assert _normalize_birthday("下个月") == ""                # garbage -> blank (safe skip)


def test_userprofile_defaults_backward_compatible():
    # old construction path (no birthday/anniversaries) still works
    p = UserProfile(identity="x")
    assert p.birthday == "" and p.anniversaries == []
    assert "birthday" in p.to_public_dict()


# --- P4-MA5 Meta-Agent --------------------------------------------------------

def test_meta_agent_classify_short_vs_long():
    ma = MetaAgent()
    short = ma.classify("现在几点了？")
    assert short.kind == "short"
    long = ma.classify("帮我写一份暑期社会实践策划案，并找三个外联对象，再起草邮件")
    assert long.kind == "long"
    assert "策划案" in long.reason or "Odyssey" in long.reason


def test_meta_agent_dag_shapes():
    ma = MetaAgent()
    short_dag = ma.build_dag(ma.classify("提醒我明天开会"))
    assert len(short_dag) == 1 and short_dag[0]["role"] == "hermes_direct"
    long_dag = ma.build_dag(ma.classify("做一份复习计划并每日 quiz"))
    assert len(long_dag) == len(LONG_DAG)
    roles = [n["role"] for n in long_dag]
    # planner has no parents; critic/re reviewer debate their upstream roles
    by_role = {n["role"]: n for n in long_dag}
    assert by_role["planner"]["parents"] == ()
    assert by_role["critic"]["parents"] == ("planner",)
    assert by_role["reviewer"]["parents"] == ("writer",)
    # acyclic: every parent references an earlier role
    seen = set()
    for node in long_dag:
        for p in node["parents"]:
            assert p in seen, f"DAG edge to unknown/forward role {p}"
        seen.add(node["role"])


def test_meta_agent_recommend_skills_uses_registry():
    ma = MetaAgent()
    recs = ma.recommend_skills("复习计划", k=3)
    assert "exam_plan" in recs
