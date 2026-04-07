# Testing Patterns

**Analysis Date:** 2026-04-07

## 测试框架 (Test Framework)

### pytest 配置

**版本**: pytest 9.0.2 (来自 `.venv\Lib\site-packages\pytest`)

**配置文件**: `decision_system\tests\pytest.ini`

```ini
[pytest]
addopts = -v --tb=short
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**配置说明**:
| 配置项 | 值 | 说明 |
|--------|-----|------|
| `addopts` | `-v --tb=short` | 详细输出 + 简短 traceback |
| `testpaths` | `tests` | 测试目录 |
| `python_files` | `test_*.py` | 文件名匹配模式 |
| `python_classes` | `Test*` | 类名匹配模式 |
| `python_functions` | `test_*` | 函数名匹配模式 |

---

## 测试文件组织 (Test File Organization)

### 目录结构

```
decision_system/
├── tests/
│   ├── __init__.py
│   ├── pytest.ini
│   ├── conftest.py              # pytest fixtures
│   ├── test_types.py
│   ├── test_config.py
│   ├── test_router.py
│   └── test_circuit_breaker.py
```

### 测试文件命名

| 文件 | 测试目标 | 行数 |
|------|----------|------|
| `test_router.py` | DecisionRouter 类 | 25 |
| `test_types.py` | Pydantic 模型 | 30 |
| `test_config.py` | 配置常量 | 14 |
| `test_circuit_breaker.py` | CircuitBreaker 类 | 18 |

---

## conftest.py Fixtures

```python
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
```

**Fixtures 用途**:
| Fixture | 用途 | 对应 SceneType |
|---------|------|----------------|
| `sample_trivial_input` | 测试琐碎场景 | TRIVIAL |
| `sample_reversible_input` | 测试可逆决策 | REVERSIBLE |
| `sample_major_input` | 测试重大决策 | MAJOR |
| `sample_innovative_input` | 测试创新场景 | INNOVATIVE |
| `sample_roi_negative_input` | 测试 ROI 拦截 | BLOCKED |

---

## 测试结构 (Test Structure)

### test_router.py

```python
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
```

### test_types.py

```python
from decision_system.types import SceneType, MainConflict, ConflictCategory, RouterResult

def test_scene_type_enum():
    assert SceneType.TRIVIAL == "trivial"
    assert SceneType.BLOCKED == "blocked"
    assert len(SceneType) == 6

def test_main_conflict_frozen():
    import pytest
    from pydantic import ValidationError
    mc = MainConflict(conflict="Test", category=ConflictCategory.RESOURCE)
    with pytest.raises(Exception):  # Frozen models raise ValidationError or AttributeError on mutation
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
```

### test_config.py

```python
import pytest
from decision_system import config

def test_max_hops_default():
    assert config.MAX_HOPS == 5

def test_llm_timeout_default():
    assert config.LLM_TIMEOUT == 120.0

def test_negative_roi_keywords_not_empty():
    assert len(config.NEGATIVE_ROI_KEYWORDS) > 0
    assert "免费" in config.NEGATIVE_ROI_KEYWORDS
```

### test_circuit_breaker.py

```python
import pytest
from decision_system.circuit_breaker import CircuitBreaker

def test_max_hops_5():
    cb = CircuitBreaker(max_hops=5)
    for _ in range(5):
        cb.record_hop()
    assert cb.check() is True

def test_circuit_open_error():
    cb = CircuitBreaker(max_hops=5)
    for _ in range(5):
        cb.record_hop()
    err = cb.get_error()
    assert err["error"] == "circuit_open"
    assert "5" in err["message"]
```

---

## Mocking 模式 (Mocking Patterns)

### 测试中未使用 mock 框架

- 未检测到 `unittest.mock`, `pytest-mock`, `faker` 等
- 直接使用真实对象测试
- Fixture 提供测试数据

### Fixture 模式

```python
@pytest.fixture
def sample_major_input():
    return "要不要给这个100万粉网红送价值5000的货"

def test_xxx(sample_major_input):  # 直接注入 fixture
    ...
```

---

## 断言模式 (Assertion Patterns)

### 直接断言

```python
assert res.scenario_type == SceneType.TRIVIAL
assert "资源" in res.main_conflict
assert res.roi_blocked is True
assert len(res.recommended_agents) == 0
```

### 异常断言

```python
def test_main_conflict_frozen():
    with pytest.raises(Exception):  # Frozen models raise ValidationError or AttributeError on mutation
        mc.conflict = "New"
```

### 布尔断言

```python
assert cb.check() is True
```

---

## 测试覆盖 (Test Coverage)

### 覆盖范围

| 模块 | 测试文件 | 覆盖内容 |
|------|----------|----------|
| `router.py` | `test_router.py` | 场景分类、冲突提取、ROI 拦截、Agent 推荐 |
| `types.py` | `test_types.py` | 枚举值、Frozen 模型、RouterResult 序列化 |
| `config.py` | `test_config.py` | 配置常量值 |
| `circuit_breaker.py` | `test_circuit_breaker.py` | 熔断逻辑、错误状态 |

### 未测试内容

| 模块/功能 | 状态 |
|-----------|------|
| `sync_pipeline.py` | **未测试** - 浏览器自动化脚本 |
| `YupooExtractor` | **未测试** - 依赖 Yupoo 网站 |
| `MrShopLogin` | **未测试** - 依赖 MrShopPlus |
| `ImageUploader` | **未测试** - 依赖 MrShopPlus |
| `Verifier` | **未测试** - 依赖 MrShopPlus |

---

## CI/CD 配置 (CI/CD Configuration)

### GitHub Workflows

**状态**: 未检测到 `.github/workflows/` 目录

仅有 `.github\RELEASE_TEMPLATE.md` - 发布模板，非 CI/CD 配置

### 运行测试命令

```bash
# 方式1: pytest 自动发现
cd decision_system && pytest

# 方式2: 指定测试路径
cd decision_system && pytest tests/

# 方式3: 带覆盖率
cd decision_system && pytest --cov=decision_system tests/

# 方式4: 带详细输出
cd decision_system && pytest -v --tb=short
```

---

## 手动测试流程 (Manual Testing Procedures)

### sync_pipeline.py 手动测试

```bash
# 全量同步（指定相册）
python scripts/sync_pipeline.py --album-id 231019138

# 模拟运行（不实际修改）
python scripts/sync_pipeline.py --album-id 231019138 --dry-run

# 从第3阶段开始（跳过提取和准备）
python scripts/sync_pipeline.py --album-id 231019138 --step 3 --resume
```

### 截图验证

测试输出位置:
| 类型 | 目录 |
|------|------|
| 日志 | `logs/sync_YYYYMMDD.log` |
| 截图 | `screenshots/verify_HHMMSS.png` |

### 状态文件

```json
// logs/pipeline_state.json
{
  "album_id": "231019138",
  "current_step": 1,
  "image_urls": [],
  "metadata": {},
  "completed_stages": [],
  "error": null
}
```

---

## 质量门禁 (Quality Gates)

### sync_pipeline.py 质量检查

| 检查项 | 说明 | 状态 |
|--------|------|------|
| 登录验证 | 检查 cookies 是否存在或重新登录 | ✅ 有 |
| 截图留证 | 每步操作后截图 | ✅ 有 |
| 错误处理 | try/except + async_retry | ✅ 有 |
| 状态持久化 | PipelineState.save() | ✅ 有 |
| 日志记录 | 分级日志 (INFO/WARNING/ERROR) | ✅ 有 |

### 熔断器 (Circuit Breaker)

```python
# decision_system/circuit_breaker.py
class CircuitBreaker:
    def __init__(self, max_hops: int = 5):
        self.max_hops = max_hops
        self.hop_count = 0
    
    def record_hop(self):
        self.hop_count += 1
    
    def check(self) -> bool:
        return self.hop_count < self.max_hops
    
    def get_error(self) -> dict:
        return {
            "error": "circuit_open",
            "message": f"Max hops ({self.max_hops}) exceeded"
        }
```

---

## 测试数据工厂 (Test Data Factories)

### Fixture 作为测试数据

```python
@pytest.fixture
def sample_major_input():
    return "要不要给这个100万粉网红送价值5000的货"

@pytest.fixture
def sample_roi_negative_input():
    return "要不要免费送鞋给这个0粉丝网红"
```

### Pydantic 模型实例化

```python
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
```

---

## 缺失的测试基础设施 (Missing Test Infrastructure)

| 组件 | 状态 | 建议 |
|------|------|------|
| **覆盖率工具** | 未安装 | 添加 `pytest-cov` |
| **类型检查** | 未配置 | 添加 `mypy` 或 `pyright` |
| **浏览器自动化测试** | 未测试 | Playwright 可用，但无 E2E 测试套件 |
| **mock 框架** | 未安装 | 添加 `pytest-mock` |
| **CI/CD Pipeline** | 不存在 | 创建 `.github/workflows/test.yml` |
| **测试报告** | 无 | 集成 pytest-html |

---

## pytest 缓存

```
decision_system/tests/.pytest_cache/
├── CACHEDIR.TAG
├── README.md
└── v/
    └── cache/
        ├── lastfailed
        └── nodeids
```

---

*Testing analysis: 2026-04-07*
