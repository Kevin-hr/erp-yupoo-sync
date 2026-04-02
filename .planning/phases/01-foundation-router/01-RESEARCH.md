# Phase 1: Foundation + Router - Research

**Researched:** 2026-04-02
**Domain:** Decision routing system foundation, Python dataclass type system, LLM timeout patterns
**Confidence:** MEDIUM (WebSearch blocked - training knowledge used; httpx confirmed, Pydantic NOT installed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

| Decision | Value |
|----------|-------|
| Type system | `types.py` 集中管理，含 `SceneType`, `MainConflict`, `AgentSpec` |
| ROI red line | Router 第一步检查 ROI，为负直接 block，不走 Agent 链 |
| 2-minute SLA | Simple timeout 实现 — LLM 调用加 timeout 参数 |
| Main conflict extraction | Keyword pattern matching（保持当前实现，不引入 LLM 推理） |
| Scene type output | JSON dataclass，不输出自然语言描述 |
| Circuit breaker trigger | Max hops = 5（硬编码） |
| Circuit breaker behavior | 超过 5 次 agent 调用后触发熔断，返回 `circuit_open` 错误 |
| CLI interface | 单次命令 `python -m decision_system "你的决策描述"` |
| Output language | 全中文输出 |
| Error strategy | Graceful degradation — 单个 Agent 失败降级，返回部分结果+警告 |
| Log storage | JSONL 文件，每次决策追加到文件 |
| Code organization | `decision_system/` 包，`types.py`, `router.py`, `agents/`, `cli.py` |
| Configuration | `config.py` 存 ROI 阈值（硬编码）和 max_hops（可配置） |
| CLI entry | `__main__.py` 支持 `python -m decision_system` |

### Claude's Discretion

- 具体 Pydantic 验证器实现方式
- CLI 参数解析库选择 (argparse vs click)
- JSONL 日志文件路径配置
- 熔断后的错误恢复策略

### Deferred Ideas (OUT OF SCOPE)

- SQLite 决策日志存储 — Phase 2 或 Phase 4 再考虑，当前用 JSONL
- 自然语言输出 — Phase 2 输出格式化再考虑
- Config 文件化 ROI 阈值 — 当前硬编码，后续按需改为 config

### Existing Code Insights

- `C:\Users\Administrator\.claude\skills\decision-cognition-skill\agents\router.py` — 现有 DecisionRouter 实现，场景分类逻辑、关键词检测、矛盾提取已实现
- `C:\Users\Administrator\.claude\skills\decision-cognition-skill\workflow.py` — 现有 Workflow 类，agent 调用模式和仲裁逻辑
- Patterns to follow: dataclass-based result types, `to_json()` 方法序列化模式, `analyze()` 主入口方法签名
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-01 | Decision Router classifies scenario type (trivial/reversible/major/innovative) and emotion state | Existing router.py lines 245-267 `_determine_scenario_type()`; add Pydantic validation wrapper |
| CORE-02 | Router identifies main conflict (主要矛盾) using 矛盾论 methodology | Existing `_extract_main_conflict()` at router.py lines 171-210; keyword pattern matching confirmed |
| CORE-03 | Router implements 2-minute decision SLA for trivial/reversible scenarios | httpx 0.28.1 available with `timeout=120.0`; trivial/reversible bypass LLM for fast path |
| CORE-04 | Agent orchestration dispatches appropriate agents based on Router classification | `recommended_agents` list from RouterResult drives dispatch; Phase 1 stub, actual agents in Phase 2 |
| INFRA-01 | Python dataclass-based types.py with Pydantic 2.x validation | Pydantic 2.x NOT installed; must add via pip; use `BaseModel` + `model_validator` |
| INFRA-02 | Workflow orchestrator with sequential/parallel execution modes | Phase 1 sequential stub only; parallel execution in Phase 4 |
| INFRA-03 | Circuit breaker — max agent hops limit to prevent infinite loops | Simple counter in Router; max_hops=5 hardcoded per locked decision |
| META-01 | 实事求是 integration — all agents grounded in actual evidence | ROI pre-filter enforces negative-ROI = block; keyword matching = 实事 approach |
| META-02 | 矛盾论 — Router identifies main conflict before agent dispatch | `_extract_main_conflict()` runs before `_recommend_agents()` in existing router.py |
</phase_requirements>

---

## Summary

Phase 1 builds the foundational type system and decision router. The existing `decision-cognition-skill/agents/router.py` provides a proven starting point - keyword-based scene classification, emotion detection, and main conflict extraction are already implemented. Phase 1 extends this by adding Pydantic 2.x validation, ROI pre-filter, 2-minute timeout for LLM calls, and a circuit breaker at max 5 hops.

**Primary recommendation:** Install Pydantic 2.x as first Wave 0 task, then refactor inline types to centralized `types.py` with Pydantic validators. Keep keyword-based conflict extraction (no LLM) per locked decision. Use httpx `timeout=120.0` for the 2-minute SLA.

**Key risk:** Python 3.14.3 is very new (released late 2025); Pydantic compatibility needs verification in Wave 0. httpx 0.28.1 is confirmed installed and works.

---

## Standard Stack

### Core

| Library | Version | Status | Purpose | Why Standard |
|---------|---------|--------|---------|--------------|
| Python | 3.14.3 | CONFIRMED | Runtime | Available in environment |
| Pydantic | 2.x | NOT INSTALLED | Type validation for `types.py` | Required by INFRA-01 |
| httpx | 0.28.1 | CONFIRMED | LLM HTTP calls with timeout | `timeout=120.0` for 2-min SLA |
| pytest | 9.0.2 | CONFIRMED | Unit testing | Available for test infrastructure |
| json | stdlib | Built-in | JSONL file logging | No extra install needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse | stdlib | CLI argument parsing | Single-command CLI; sufficient over click |
| dataclasses | stdlib | Base patterns | AgentResult subclasses (no validation) |
| pathlib | stdlib | File path handling | JSONL log file location |

### Installation Required

```bash
pip install pydantic>=2.0
```

### No New Dependencies Needed

- httpx 0.28.1 already handles 2-minute timeout via `timeout=120.0`
- json (stdlib) handles JSONL logging
- pytest 9.0.2 already available for testing

---

## Architecture Patterns

### Recommended Project Structure

```
decision_system/
├── __init__.py           # Package init, exports DecisionRouter, run_cli
├── __main__.py           # Entry point: python -m decision_system
├── types.py              # Core types: SceneType, MainConflict, AgentSpec, RouterResult, AgentResult
├── router.py             # DecisionRouter with ROI filter, scene classification, hop counter
├── config.py             # ROI thresholds (hardcoded), max_hops=5, LLM_TIMEOUT=120
├── circuit_breaker.py    # CircuitBreaker class (optional, can be inline in router)
├── agents/
│   ├── __init__.py
│   └── stubs.py          # Placeholder Agent classes matching AgentSpec (Phase 2+)
└── logs/
    └── decisions.jsonl   # Append-only decision log
```

### Pattern 1: Pydantic 2.x Validated Types (`types.py`)

**What:** Centralized type definitions with runtime validation using Pydantic 2.x `BaseModel`

**When to use:** Core types: `SceneType`, `MainConflict`, `AgentSpec`, `RouterResult`

**Example:**

```python
# types.py — Source: Pydantic 2.x official patterns (training knowledge)
from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from enum import Enum
from typing import List, Optional

class SceneType(str, Enum):
    TRIVIAL = "trivial"
    REVERSIBLE = "reversible"
    MAJOR = "major"
    INNOVATIVE = "innovative"
    EMOTIONAL = "emotional"
    BLOCKED = "blocked"  # ROI negative

class ConflictCategory(str, Enum):
    RESOURCE = "resource"    # 资源类矛盾
    RISK = "risk"            # 风险类矛盾
    CHOICE = "choice"        # 选择类矛盾
    GROWTH = "growth"        # 发展类矛盾

class MainConflict(BaseModel):
    """主要矛盾 — frozen to prevent mutation"""
    conflict: str
    category: ConflictCategory
    model_config = ConfigDict(frozen=True)

    @field_validator('conflict')
    @classmethod
    def conflict_not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('矛盾描述不能为空')
        return v.strip()

class AgentSpec(BaseModel):
    """Agent规格元数据"""
    agent_id: str
    name: str
    version: str
    capabilities: List[str]

class RouterResult(BaseModel):
    """路由器输出结果"""
    scenario_type: SceneType
    main_conflict: str  # Primary conflict description
    complexity: str  # low/medium/high
    emotion_state: str  # stable/volatile
    options_clear: bool
    recommended_agents: List[str]  # List of agent IDs
    reason: str
    key_questions: List[str]
    hop_count: int = 0  # Circuit breaker tracking
    roi_blocked: bool = False

    def to_json(self) -> dict:
        return {
            "scenario_type": self.scenario_type.value,
            "main_conflict": self.main_conflict,
            "complexity": self.complexity,
            "emotion_state": self.emotion_state,
            "options_clear": self.options_clear,
            "recommended_agents": self.recommended_agents,
            "reason": self.reason,
            "key_questions": self.key_questions,
            "hop_count": self.hop_count,
            "roi_blocked": self.roi_blocked
        }
```

### Pattern 2: ROI Pre-Filter (Router First Step)

**What:** ROI check BEFORE scene classification or agent dispatch

**When to use:** First line of `router.analyze()`, before any other processing

**Example:**

```python
# router.py — based on existing router.py analyze() pattern
from enum import Enum

class ROIStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"

NEGATIVE_ROI_KEYWORDS = [
    "免费", "赠送", "倒贴", "亏本",
    # BIZ-01: ROI negative must block
    # BIZ-02: 新人首次合作 needs Model B压测
]

def check_roi(user_input: str, roi_value: Optional[float] = None) -> tuple[ROIStatus, str]:
    """Returns (status, reason). Negative ROI = immediate block."""
    # Explicit ROI value takes precedence
    if roi_value is not None:
        if roi_value < 0:
            return ROIStatus.NEGATIVE, f"预期ROI为负: {roi_value}"
        return ROIStatus.POSITIVE, f"ROI={roi_value}"

    # Keyword-based fallback
    for kw in NEGATIVE_ROI_KEYWORDS:
        if kw in user_input:
            return ROIStatus.NEGATIVE, f"检测到ROI负面关键词: {kw}"

    return ROIStatus.UNKNOWN, "无法确定ROI"

def analyze(self, user_input: str, roi_value: Optional[float] = None) -> RouterResult:
    # STEP 1: ROI Pre-filter (META-01: 实事求是)
    roi_status, roi_reason = check_roi(user_input, roi_value)
    if roi_status == ROIStatus.NEGATIVE:
        return RouterResult(
            scenario_type=SceneType.BLOCKED,
            main_conflict="ROI为负，止亏",
            # ... return blocked result, no agent dispatch
            roi_blocked=True
        )

    # STEP 2: Scene classification (CORE-01), conflict extraction (CORE-02), etc.
    # ... rest of existing logic
```

### Pattern 3: 2-Minute SLA via httpx Timeout

**What:** LLM calls wrapped with `httpx.Client(timeout=120.0)`

**When to use:** When LLM is actually called (major/innovative scenes); trivial/reversible bypass LLM entirely

**Example:**

```python
# httpx timeout — Source: httpx 0.28.1 confirmed installed
import httpx

LLM_TIMEOUT = 120.0  # 2 minutes in seconds

def call_llm(prompt: str, api_base: str, api_key: str, model: str = "gpt-4") -> str:
    """Call LLM with 2-minute timeout."""
    with httpx.Client(timeout=LLM_TIMEOUT) as client:
        response = client.post(
            f"{api_base}/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return response.json()["choices"][0]["message"]["content"]

# Trivial/reversible fast path — NO LLM call (CORE-03 SLA)
def get_fast_recommendation(scenario_type: SceneType, main_conflict: str) -> str:
    """Return fast recommendation without LLM call. Target: <2 seconds."""
    if scenario_type == SceneType.TRIVIAL:
        return f"【快速决策】{main_conflict} — 建议: 立即执行，后果可控"
    elif scenario_type == SceneType.REVERSIBLE:
        return f"【可试错】{main_conflict} — 建议: 小范围试点，验证后扩大"
    raise ValueError("get_fast_recommendation only for trivial/reversible")
```

### Pattern 4: Circuit Breaker (Max Hops = 5)

**What:** Simple counter prevents infinite agent loops

**When to use:** Before each agent dispatch; tracks `_hop_count`

**Example:**

```python
# router.py — simple counter pattern
class CircuitBreaker:
    def __init__(self, max_hops: int = 5):
        self.max_hops = max_hops
        self._hop_count = 0

    def record_hop(self) -> None:
        self._hop_count += 1

    def check(self) -> bool:
        """Returns True if circuit should trip"""
        return self._hop_count >= self.max_hops

    def get_error(self) -> dict:
        return {
            "error": "circuit_open",
            "message": f"超过最大调用次数({self.max_hops}次)，熔断触发",
            "hops": self._hop_count
        }

class DecisionRouter:
    def __init__(self, max_hops: int = 5):
        self._circuit = CircuitBreaker(max_hops)

    def dispatch_agents(self, agent_ids: List[str], user_input: str) -> DispatchResult:
        results = []
        warnings = []

        for agent_id in agent_ids:
            if self._circuit.check():
                warnings.append("circuit_open")
                break

            try:
                result = self._call_agent(agent_id, user_input)
                results.append(result)
                self._circuit.record_hop()
            except Exception as e:
                warnings.append(f"Agent {agent_id} failed: {str(e)}")
                # Graceful degradation: continue to next agent
                continue

        return DispatchResult(results=results, warnings=warnings)
```

### Pattern 5: JSONL Logging

**What:** Append-only JSON Lines file, one decision per line

**When to use:** After each decision call completes

**Example:**

```python
# logging_utils.py — Source: stdlib json
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

LOG_FILE = Path(__file__).parent.parent / "logs" / "decisions.jsonl"

def log_decision(
    user_input: str,
    roi_value: Optional[float],
    router_result: dict,
    dispatch_result: Optional[dict] = None,
    error: Optional[str] = None
) -> None:
    record = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "roi_value": roi_value,
        "router_result": router_result,
        "dispatch_result": dispatch_result,
        "error": error,
        "version": "1.0"
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

### Anti-Patterns to Avoid

- **Do NOT use `threading.Timer` for timeout** — httpx `timeout=` parameter is cleaner and reliable
- **Do NOT implement OPEN/HALF_OPEN/HALF_OPEN state machine** — max_hops=5 is a simple counter, not a full CB
- **Do NOT use global mutable `_hop_count`** — pass `CircuitBreaker` instance through call chain for testability
- **Do NOT output natural language from Router** — JSON dataclass only per locked decision

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM timeout | Custom threading.Timer wrapper | httpx `timeout=120.0` | httpx 0.28.1 confirmed installed; native timeout is reliable |
| JSONL append | Rotation logic, lock files | `open(mode="a")` + `json.dumps` | Simple enough for Phase 1; rotation in Phase 2+ |
| Input validation (ROI) | Manual `if roi < 0: raise` blocks | Pydantic `model_validator` | Required by INFRA-01; self-documenting schema |
| Circuit breaker | Full CB state machine | Simple counter | max_hops=5 hardcoded; complexity not justified |

**Key insight:** The existing `router.py` already has solid keyword-based classification. Phase 1 wraps it with Pydantic validation, adds ROI pre-filter, timeout, and circuit breaker. Do NOT rewrite the existing classification logic — refactor and extend only.

---

## Common Pitfalls

### Pitfall 1: Pydantic 2.x Not Installed
**What goes wrong:** `ImportError: No module named 'pydantic'` at runtime.
**Why it happens:** Pydantic 2.x NOT in current environment; Phase 1 requires it per INFRA-01.
**How to avoid:** `pip install pydantic>=2.0` is first Wave 0 task. Add to `requirements.txt`.
**Warning signs:** First test run fails with `ModuleNotFoundError`.

### Pitfall 2: Circuit Breaker Not Thread-Safe in Phase 4
**What goes wrong:** Hop counter corrupted in parallel execution.
**Why it happens:** `self._hop_count += 1` is not atomic.
**How to avoid:** Phase 1 is sequential only (per workflow.py). Add `threading.Lock` when Phase 4 adds parallel execution.
**Warning signs:** `hop_count` occasionally exceeds `max_hops` by 2+ in parallel scenarios (Phase 4 problem).

### Pitfall 3: JSONL Corruption on Concurrent Writes
**What goes wrong:** Partial lines written when multiple processes append simultaneously.
**Why it happens:** No file locking on JSONL append.
**How to avoid:** Phase 1 single-user only. Use `fcntl.flock()` (Linux) or file-based lock when Phase 4 goes multi-user.
**Warning signs:** `json.JSONDecodeError` when reading JSONL log.

### Pitfall 4: ROI Filter Missing from Existing Router
**What goes wrong:** Negative-ROI scenarios still dispatch agents — ROI filter not in existing `analyze()`.
**Why it happens:** Existing router.py (line 71) does NOT check ROI; only emotion/complexity/scenario type.
**How to avoid:** Add explicit ROI check as FIRST step of `analyze()` before any other processing.
**Warning signs:** Test `test_roi_negative_blocked` fails — ROI-negative input still returns agents.

---

## Code Examples

### Existing Scene Classification (router.py lines 245-267)

```python
# Source: decision-cognition-skill/agents/router.py — CONFIRMED WORKING
def _determine_scenario_type(self, is_major: bool, is_reversible: bool,
                            emotion: str, options_clear: bool, is_innovative: bool) -> str:
    if emotion == 'volatile':
        return 'emotional'
    if is_innovative or not options_clear:
        return 'innovative'
    if is_reversible and not is_major:
        return 'trivial'
    if not is_reversible and not is_major:
        return 'reversible'
    return 'major'
```

### Existing Main Conflict Extraction (router.py lines 171-210)

```python
# Source: decision-cognition-skill/agents/router.py — CONFIRMED WORKING
def _extract_main_conflict(self, text: str, is_major: bool, is_innovative: bool) -> str:
    conflicts = []
    if any(kw in text for kw in ['钱', '资金', '预算', '成本']):
        conflicts.append("资源有限 vs 目标需求")
    if any(kw in text for kw in ['时间', '精力', '忙', '没时间']):
        conflicts.append("时间/精力不足 vs 任务繁重")
    if any(kw in text for kw in ['担心', '风险', '害怕', '不敢']):
        conflicts.append("追求收益 vs 规避风险")
    if any(kw in text for kw in ['还是', '或者', '哪个']):
        conflicts.append("选项A vs 选项B")
    if is_innovative:
        conflicts.append("方向不明确 vs 需要做出选择")
    if is_major:
        conflicts.append("机会成本 vs 潜在收益")
    if conflicts:
        return conflicts[0]
    return "需要更多信息才能确定主要矛盾"
```

### CLI Entry Point

```python
# __main__.py — adapted from workflow.py main() pattern
import argparse
import sys
from router import DecisionRouter
from types import ROIStatus, check_roi
from logging_utils import log_decision
from config import LLM_TIMEOUT

def main():
    parser = argparse.ArgumentParser(description="决策认知系统 v2.0")
    parser.add_argument("decision", type=str, help="你的决策描述")
    parser.add_argument("--roi", type=float, default=None, help="ROI值（可选）")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()

    router = DecisionRouter()

    # ROI pre-filter first (META-01)
    roi_status, roi_reason = check_roi(args.decision, args.roi)
    if roi_status == ROIStatus.NEGATIVE:
        output = {"status": "blocked", "reason": roi_reason}
        print(f"【ROI拦截】{roi_reason}")
        log_decision(args.decision, args.roi, output, error="roi_negative")
        return

    # Scene classification + dispatch
    result = router.analyze(args.decision)

    # Fast path for trivial/reversible (CORE-03: 2-min SLA)
    if result.scenario_type.value in ["trivial", "reversible"]:
        fast_rec = get_fast_recommendation(result.scenario_type, result.main_conflict)
        print(fast_rec)
        log_decision(args.decision, args.roi, result.to_json(), {"fast_path": True})
    else:
        print(result.model_dump_json(ensure_ascii=False) if hasattr(result, 'model_dump_json') else str(result))
        log_decision(args.decision, args.roi, result.to_json())

if __name__ == "__main__":
    main()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline type definitions in agents | Centralized `types.py` with Pydantic 2.x | Phase 1 | Single source of truth; validation at boundaries |
| No ROI filter in router | ROI pre-filter before any agent dispatch | Phase 1 | Enforces 实事求是 red line; saves agent calls |
| No circuit breaker | Max 5 hops counter | Phase 1 | Prevents infinite agent loops |
| No LLM timeout | httpx `timeout=120.0` | Phase 1 | 2-min SLA guarantee |
| No decision logging | JSONL append-only | Phase 1 | Audit trail for decisions |

**Deprecated/outdated:**
- `pydantic.BaseModel` v1 `class Config` — use `model_config = ConfigDict()` in Pydantic 2.x
- Inline `@dataclass` without validation for core types

---

## Open Questions

1. **Pydantic 2.x Compatibility with Python 3.14.3**
   - What we know: Python 3.14.3 available; Pydantic 2.x NOT installed
   - What's unclear: Actual compatibility test result — Python 3.14 very new (Oct 2025)
   - Recommendation: Wave 0 task: `python -c "import pydantic; print(pydantic.__version__)"` to verify

2. **LLM Provider Selection**
   - What we know: httpx 0.28.1 available; timeout pattern confirmed
   - What's unclear: Which LLM API (OpenAI/Anthropic/MiniMax) — not specified in Phase 1
   - Recommendation: Use `config.LLM_API_BASE` and `config.LLM_API_KEY` env vars; defer provider to Phase 2

3. **Phase 1 Agent Dispatch Stub Scope**
   - What we know: Phase 4 has parallel execution; Phase 1 sequential only
   - What's unclear: How much of INFRA-02 to implement in Phase 1
   - Recommendation: Phase 1 implements sequential `dispatch_agents()` stub; parallel in Phase 4

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (confirmed installed) |
| Config file | `pytest.ini` or `pyproject.toml` (none yet — create in Wave 0) |
| Quick run command | `pytest tests/test_router.py -x -v` |
| Full suite command | `pytest tests/ -x -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CORE-01 | Router classifies scenario_type (trivial/reversible/major/innovative/emotional) | unit | `pytest tests/test_router.py::test_scene_classification -x` | NO |
| CORE-01 | Router detects emotion_state (stable/volatile) | unit | `pytest tests/test_router.py::test_emotion_detection -x` | NO |
| CORE-02 | Router identifies main_conflict via keyword matching | unit | `pytest tests/test_router.py::test_main_conflict_extraction -x` | NO |
| CORE-03 | Trivial/reversible returns fast recommendation (no LLM) | unit | `pytest tests/test_router.py::test_fast_path_sla -x` | NO |
| CORE-03 | LLM call uses timeout=120.0 (mock test) | unit | `pytest tests/test_router.py::test_llm_timeout_mock -x` | NO |
| CORE-04 | Router returns recommended_agents list based on scene type | unit | `pytest tests/test_router.py::test_agent_recommendation -x` | NO |
| INFRA-01 | types.py uses Pydantic 2.x BaseModel | unit | `pytest tests/test_types.py::test_pydantic_validation -x` | NO |
| INFRA-01 | SceneType enum has correct values | unit | `pytest tests/test_types.py::test_scene_type_enum -x` | NO |
| INFRA-03 | Circuit breaker triggers at hop 5 | unit | `pytest tests/test_circuit_breaker.py::test_max_hops -x` | NO |
| INFRA-03 | Circuit breaker returns circuit_open error | unit | `pytest tests/test_circuit_breaker.py::test_circuit_open_error -x` | NO |
| META-01 | ROI negative scenarios blocked before agent chain | unit | `pytest tests/test_router.py::test_roi_negative_blocked -x` | NO |
| META-02 | Main conflict extracted before agent dispatch | unit | `pytest tests/test_router.py::test_conflict_before_dispatch -x` | NO |

### Sampling Rate

- **Per task commit:** `pytest tests/test_router.py -x -v` (fast, under 30 seconds)
- **Per wave merge:** `pytest tests/ -x -v` (full suite)
- **Phase gate:** All tests green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `decision_system/types.py` — INFRA-01, CORE-01
- [ ] `decision_system/router.py` — CORE-01, CORE-02, CORE-03, CORE-04, META-01, META-02
- [ ] `decision_system/config.py` — INFRA-01, INFRA-03
- [ ] `decision_system/circuit_breaker.py` — INFRA-03
- [ ] `decision_system/logging_utils.py` — JSONL logging
- [ ] `decision_system/cli.py` — CLI interface
- [ ] `decision_system/__main__.py` — `python -m decision_system` entry
- [ ] `tests/test_router.py` — CORE-01, CORE-02, CORE-03, CORE-04, META-01, META-02
- [ ] `tests/test_types.py` — INFRA-01
- [ ] `tests/test_circuit_breaker.py` — INFRA-03
- [ ] `tests/conftest.py` — shared fixtures
- [ ] `pytest.ini` — framework config
- [ ] Framework install: `pip install pydantic>=2.0` — Pydantic NOT currently installed

---

## Sources

### Primary (HIGH confidence)
- `decision-cognition-skill/agents/router.py` — Existing router implementation with verified scene classification and conflict extraction logic
- `decision-cognition-skill/workflow.py` — Agent dispatch patterns and result serialization

### Secondary (MEDIUM confidence)
- Pydantic 2.x `BaseModel` patterns — Training knowledge, not verified with Context7 (WebSearch blocked)
- httpx timeout patterns — Training knowledge, httpx 0.28.1 confirmed installed

### Tertiary (LOW confidence)
- Python 3.14.3 library compatibility — Very new version; Pydantic compatibility unverified
- Specific Pydantic 2.x version numbers — Not confirmed via Context7/WebSearch

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — httpx/pytest confirmed installed; Pydantic NOT installed; httpx timeout pattern reliable from training
- Architecture: HIGH — Based on existing working code from router.py and workflow.py
- Pitfalls: MEDIUM — Known Python patterns; Python 3.14 compatibility needs Wave 0 verification

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (30 days; Python 3.14 compatibility needs verification in Wave 0)
**WebSearch status:** BLOCKED — could not verify Pydantic latest version or httpx docs via search
