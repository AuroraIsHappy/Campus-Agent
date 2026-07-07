"""L6 Persona tests (P4-P1/P2, S-PERSONA). Pure stdlib."""
from __future__ import annotations

from campus.personas.builtins import BUILTIN_PERSONAS, get_persona
from campus.personas.loader import apply_to_prompt, available_names, select
from campus.personas.types import Persona


def test_three_builtins_present_and_well_formed():
    assert set(BUILTIN_PERSONAS) >= {"default", "feynman", "lu_xun"}
    for p in BUILTIN_PERSONAS.values():
        assert isinstance(p, Persona)
        assert p.style_prompt.strip()
        assert p.label.strip()


def test_get_persona_falls_back_to_default():
    assert get_persona("feynman").name == "feynman"
    assert get_persona("nope").name == "default"


def test_select_case_insensitive_and_custom_override():
    assert select("FEYNMAN").name == "feynman"
    assert select("  Lu_Xun ").name == "lu_xun"
    assert select("unknown").name == "default"
    custom = Persona(name="custom", label="自", style_prompt="x", markers=("x",))
    assert select("custom", personas={"custom": custom}).name == "custom"


def test_available_names_sorted_and_complete():
    names = available_names()
    assert names == sorted(names)
    assert {"default", "feynman", "lu_xun"} <= set(names)


def test_apply_to_prompt_includes_base_and_style():
    base = "你是学生秘书。"
    out = apply_to_prompt(select("feynman"), base)
    assert base in out
    assert "[persona: feynman]" in out
    assert "费曼" in out                       # style header carries the label vibe
    assert any(m in out for m in select("feynman").markers)


def test_persona_styles_are_distinguishable_s_persona():
    """S-PERSONA: applied styles carry distinct, detectable markers (judge-able)."""
    base = "你是学生秘书。"
    feyn = apply_to_prompt(select("feynman"), base)
    luxun = apply_to_prompt(select("lu_xun"), base)
    default = apply_to_prompt(select("default"), base)

    # each carries its own tag
    assert "[persona: feynman]" in feyn
    assert "[persona: lu_xun]" in luxun
    assert "[persona: default]" in default

    # feynman marker present, a lu_xun-only marker absent in feynman output
    assert "类比" in feyn
    assert "犀利" in luxun
    assert "犀利" not in feyn
    assert "类比" not in luxun


def test_apply_preserves_examples():
    p = select("feynman")
    out = apply_to_prompt(p, "base")
    assert "示例语气" in out
    for ex in p.examples:
        assert ex in out
