"""P2-P1 / P2-P2: 9 role profiles load + role->model routing resolution."""
import pytest

from campus.profiles.loader import ProfileLoader, ROLES

ROUTING = {
    "default": {"provider": "zai", "model": "glm-4.6"},
    "roles": {
        "planner": {"provider": "zai", "model": "glm-4.6"},
        "critic": {"provider": "zai", "model": "glm-4.6"},
        "sub_agent": {"provider": "zai", "model": "glm-4.5-air"},
    },
}


@pytest.fixture
def loader():
    return ProfileLoader(routing=ROUTING)


def test_all_9_roles_loaded(loader):
    allp = loader.load_all()
    for r in ROLES:
        assert r in allp, f"missing role profile: {r}"
    assert len(allp) >= 9


def test_profile_schema(loader):
    for name, prof in loader.load_all().items():
        assert prof.get("system_prompt"), f"{name} missing system_prompt"
        assert isinstance(prof.get("toolset"), list), f"{name} toolset not list"
        assert prof.get("model"), f"{name} missing model"


def test_validate_clean(loader):
    assert loader.validate() == []


def test_routing_resolution_role_listed(loader):
    assert loader.resolve("planner") == ("zai", "glm-4.6")


def test_routing_resolution_sub_agent_cheap(loader):
    # sub_agent -> cheaper model (cost control, architecture §1)
    assert loader.resolve("sub_agent") == ("zai", "glm-4.5-air")


def test_routing_resolution_falls_back_to_default(loader):
    # scheduler not listed in routing.roles -> default model
    assert loader.resolve("scheduler") == ("zai", "glm-4.6")


def test_get_augments_resolved_model(loader):
    p = loader.get("planner")
    assert p["model"] == "glm-4.6"
    assert p["provider"] == "zai"
    assert "system_prompt" in p


def test_unknown_role_uses_default(loader):
    assert loader.resolve("nonexistent_role") == ("zai", "glm-4.6")


def test_load_routing_from_file(tmp_path):
    rf = tmp_path / "routing.yaml"
    rf.write_text(
        "default:\n  provider: zai\n  model: glm-4.6\n"
        "roles:\n  planner:\n    provider: zai\n    model: glm-4.6\n",
        encoding="utf-8")
    loader = ProfileLoader(routing_path=str(rf))
    assert loader.resolve("planner") == ("zai", "glm-4.6")
    assert loader.resolve("scheduler") == ("zai", "glm-4.6")   # default fallback


def test_missing_routing_file_uses_profile_defaults():
    loader = ProfileLoader(routing_path="/nonexistent/routing.yaml")
    # falls back to the planner.yaml own defaults
    assert loader.resolve("planner") == ("zai", "glm-4.6")
