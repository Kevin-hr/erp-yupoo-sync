import pytest
from decision_system.router import DecisionRouter
from decision_system.types import SceneType

def test_scene_classification(sample_trivial_input):
    router = DecisionRouter()
    res = router.analyze(sample_trivial_input)
    assert res.scenario_type == SceneType.TRIVIAL

def test_main_conflict_extraction(sample_major_input):
    router = DecisionRouter()
    res = router.analyze(sample_major_input)
    assert "资源" in res.main_conflict

def test_roi_negative_blocked(sample_roi_negative_input):
    router = DecisionRouter()
    res = router.analyze(sample_roi_negative_input)
    assert res.roi_blocked is True
    assert res.scenario_type == SceneType.BLOCKED

def test_fast_path_for_trivial(sample_trivial_input):
    router = DecisionRouter()
    res = router.analyze(sample_trivial_input)
    assert len(res.recommended_agents) == 0

