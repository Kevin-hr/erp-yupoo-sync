from decision_system.types import SceneType, MainConflict, ConflictCategory, RouterResult


def test_scene_type_enum():
    assert SceneType.TRIVIAL == "trivial"
    assert SceneType.BLOCKED == "blocked"
    assert len(SceneType) == 6

def test_main_conflict_frozen():
    import pytest
    from pydantic import ValidationError
    mc = MainConflict(conflict="Test", category=ConflictCategory.RESOURCE)
    with pytest.raises(Exception): # Frozen models raise ValidationError or AttributeError on mutation
        mc.conflict = "New"

def test_router_result_has_fields():
    res = RouterResult(
        scenario_type=SceneType.TRIVIAL,
        main_conflict="Test",
        complexity="low",
        emotion_state="stable",
        options_clear=True,
        recommended_agents=[],
        reason="Test",
        key_questions=[]
    )
    assert res.scenario_type == SceneType.TRIVIAL
    assert res.to_json()["scenario_type"] == "trivial"

