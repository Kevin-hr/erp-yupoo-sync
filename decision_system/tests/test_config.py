import pytest
from decision_system import config

def test_max_hops_default():
    assert config.MAX_HOPS == 5

def test_llm_timeout_default():
    assert config.LLM_TIMEOUT == 120.0

def test_negative_roi_keywords_not_empty():
    assert len(config.NEGATIVE_ROI_KEYWORDS) > 0
    assert "免费" in config.NEGATIVE_ROI_KEYWORDS

