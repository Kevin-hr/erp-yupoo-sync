import pytest
import sys
from pathlib import Path

# Add project root to sys.path for imports
sys.path.append(str(Path(__file__).parent.parent))

@pytest.fixture
def sample_trivial_input():
    return "要不要今天中午吃什么"

@pytest.fixture
def sample_reversible_input():
    return "要不要换一个新商家的商品"

@pytest.fixture
def sample_major_input():
    return "要不要给这个100万粉网红送价值5000的货"

@pytest.fixture
def sample_innovative_input():
    return "要不要做一个全新类目的独立站"

@pytest.fixture
def sample_roi_negative_input():
    return "要不要免费送鞋给这个0粉丝网红"
