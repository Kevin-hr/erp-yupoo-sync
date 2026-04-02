---
phase: 01-foundation-router
plan: 01
type: execute
wave: 0
depends_on: []
files_modified: []
autonomous: false
requirements:
  - CORE-01
  - CORE-02
  - CORE-03
  - CORE-04
  - INFRA-01
  - INFRA-02
  - INFRA-03
  - META-01
  - META-02
must_haves:
  truths:
    - "User can input a decision scenario and receive a scene type classification within 2 seconds"
    - "Router correctly identifies the main conflict (主要矛盾) from user-described scenario"
    - "Trivial/reversible decisions return a fast recommendation without invoking full agent chain"
    - "ROI-negative scenarios are blocked at router level before any agent chain executes"
    - "Circuit breaker triggers and returns circuit_open error after 5 agent hops"
  artifacts:
    - path: "decision_system/types.py"
      provides: "Centralized type system with Pydantic 2.x"
      exports: "SceneType, MainConflict, AgentSpec, RouterResult, ROIStatus"
    - path: "decision_system/config.py"
      provides: "Configuration constants"
      exports: "MAX_HOPS, LLM_TIMEOUT, NEGATIVE_ROI_KEYWORDS, LOG_FILE"
    - path: "decision_system/router.py"
      provides: "Decision router with ROI guard and scene classification"
      exports: "DecisionRouter, check_roi"
    - path: "decision_system/circuit_breaker.py"
      provides: "Circuit breaker (max hops counter)"
      exports: "CircuitBreaker"
    - path: "decision_system/logging_utils.py"
      provides: "JSONL append-only decision logging"
      exports: "log_decision"
    - path: "decision_system/cli.py"
      provides: "CLI interface (全中文输出)"
      exports: "run_cli"
    - path: "decision_system/__main__.py"
      provides: "Entry point: python -m decision_system"
    - path: "decision_system/workflow.py"
      provides: "Workflow orchestrator with sequential dispatch mode"
      exports: "DecisionWorkflow, dispatch_agents"
  key_links:
    - from: "decision_system/router.py"
      to: "decision_system/types.py"
      via: "import SceneType, ROIStatus, RouterResult"
      pattern: "from types import|from .types import"
    - from: "decision_system/router.py"
      to: "decision_system/config.py"
      via: "import NEGATIVE_ROI_KEYWORDS, MAX_HOPS, LLM_TIMEOUT"
      pattern: "from config import"
    - from: "decision_system/cli.py"
      to: "decision_system/router.py"
      via: "import DecisionRouter"
      pattern: "from router import"
    - from: "decision_system/logging_utils.py"
      to: "decision_system/config.py"
      via: "import LOG_FILE"
      pattern: "from config import LOG_FILE"
    - from: "decision_system/workflow.py"
      to: "decision_system/router.py"
      via: "import DecisionRouter"
      pattern: "from router import"
    - from: "decision_system/workflow.py"
      to: "decision_system/circuit_breaker.py"
      via: "import CircuitBreaker"
      pattern: "from circuit_breaker import"
---

<objective>
Build foundational type system, decision router with ROI guard and circuit breaker, and CLI entry point for the decision cognition system. This phase establishes the core dispatch contract all subsequent agents depend on.
</objective>

<context>
**Locked Decisions (NON-NEGOTIABLE):**
- types.py 集中管理，含 SceneType, MainConflict, AgentSpec
- ROI 红线: Router 第一步检查 ROI，为负直接 block
- 2分钟 SLA: httpx timeout=120.0
- 主要矛盾: Keyword pattern matching (不引入 LLM 推理)
- 熔断: Max hops = 5 (硬编码)
- CLI: `python -m decision_system "决策描述"`
- 全中文输出，JSON dataclass 输出
- Graceful degradation，单个 Agent 失败降级
- JSONL 文件日志
- Workflow: sequential dispatch only (Phase 4 adds parallel)

**Stack:**
- httpx 0.28.1 confirmed installed
- Pydantic 2.x NOT installed — must `pip install pydantic>=2.0`
- pytest 9.0.2 confirmed installed
- Python 3.14.3

**Existing code to extend:**
- `C:\Users\Administrator\.claude\skills\decision-cognition-skill\agents\router.py` — proven keyword patterns for scene classification and conflict extraction
- `C:\Users\Administrator\.claude\skills\decision-cognition-skill\workflow.py` — agent dispatch patterns (sequential reference, parallel is Phase 4)
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 0: Test infrastructure (Wave 0)</name>
  <files>decision_system/tests/conftest.py, decision_system/tests/pytest.ini, decision_system/tests/test_types.py, decision_system/tests/test_config.py, decision_system/tests/test_router.py, decision_system/tests/test_circuit_breaker.py, decision_system/tests/test_cli.py, decision_system/tests/test_logging.py, decision_system/__init__.py, decision_system/tests/__init__.py</files>
  <action>
## Goal
Create all test infrastructure before any implementation. Stubs ensure Wave 1 executors can verify incrementally.

## Files to create

### decision_system/tests/pytest.ini
```
[pytest]
addopts = -v --tb=short
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### decision_system/tests/conftest.py
Shared fixtures:
- `router_instance` — returns DecisionRouter()
- `sample_trivial_input` — "要不要今天中午吃什么"
- `sample_reversible_input` — "要不要换一个新商家的商品"
- `sample_major_input` — "要不要给这个100万粉网红送价值5000的货"
- `sample_innovative_input` — "要不要做一个全新类目的独立站"
- `sample_roi_negative_input` — "要不要免费送鞋给这个0粉丝网红"

### decision_system/tests/test_types.py
Stubs (will be filled by Task 1):
- `test_scene_type_enum` — asserts SceneType has TRIVIAL, REVERSIBLE, MAJOR, INNOVATIVE, EMOTIONAL, BLOCKED
- `test_main_conflict_frozen` — asserts MainConflict is frozen after creation
- `test_router_result_has_fields` — asserts RouterResult has all required fields

### decision_system/tests/test_config.py
Stubs:
- `test_max_hops_default` — asserts MAX_HOPS == 5
- `test_llm_timeout_default` — asserts LLM_TIMEOUT == 120.0
- `test_negative_roi_keywords_not_empty` — asserts NEGATIVE_ROI_KEYWORDS is non-empty list

### decision_system/tests/test_router.py
Stubs:
- `test_scene_classification` — classify trivial scenario, assert type is TRIVIAL or REVERSIBLE
- `test_main_conflict_extraction` — input with "钱" keyword, assert main_conflict contains "资源"
- `test_roi_negative_blocked` — input "免费送鞋", assert roi_blocked=True or scenario_type==BLOCKED
- `test_fast_path_for_trivial` — trivial input, assert response returned without LLM call

### decision_system/tests/test_circuit_breaker.py
Stubs:
- `test_max_hops_5` — record 5 hops, assert check() returns True (tripped)
- `test_circuit_open_error` — after trip, assert get_error() has error=="circuit_open"

### decision_system/tests/test_cli.py
Stubs:
- `test_cli_module_imports` — assert `python -m decision_system` imports without error
- `test_cli_help_flag` — run with --help, assert returncode==0

### decision_system/tests/test_logging.py
Stubs:
- `test_log_decision_append` — call log_decision, assert line appended to log file
- `test_log_file_jsonl_format` — assert each line is valid JSON

### Python path setup
Create decision_system/__init__.py as empty package marker.
Create decision_system/tests/__init__.py.

## Verify
`pytest decision_system/tests/test_types.py decision_system/tests/test_config.py -v` — all pass (stubs return pass until real code exists)
</action>
  <verify>
    <automated>pytest decision_system/tests/ -v --collect-only</automated>
  </verify>
  <done>
    pytest collects 14+ test stubs across 6 test files; conftest.py provides all shared fixtures
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 1: types.py + config.py foundation</name>
  <files>decision_system/types.py, decision_system/config.py</files>
  <action>
## Goal
Create centralized type system with Pydantic 2.x validation and configuration constants.

## types.py

Create `decision_system/types.py` with these Pydantic 2.x models:

```python
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
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
    RISK = "risk"           # 风险类矛盾
    CHOICE = "choice"       # 选择类矛盾
    GROWTH = "growth"       # 发展类矛盾

class MainConflict(BaseModel):
    """主要矛盾 — frozen to prevent mutation"""
    model_config = ConfigDict(frozen=True)

    conflict: str
    category: ConflictCategory

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
    main_conflict: str
    complexity: str  # low/medium/high
    emotion_state: str  # stable/volatile
    options_clear: bool
    recommended_agents: List[str]
    reason: str
    key_questions: List[str]
    hop_count: int = 0
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

class ROIStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"
```

## config.py

Create `decision_system/config.py`:

```python
from pathlib import Path

# Circuit breaker
MAX_HOPS: int = 5

# LLM timeout (2-minute SLA)
LLM_TIMEOUT: float = 120.0

# ROI thresholds
# BIZ-01: ROI 为负 → block
NEGATIVE_ROI_KEYWORDS: list[str] = [
    "免费", "赠送", "倒贴", "亏本", "无条件",
    "无条件送", "不要钱", "白送"
]

# BIZ-02: 新人首次合作 → Model B 压测
NEW_COLLAB_KEYWORDS: list[str] = [
    "第一次合作", "新人", "首次合作", "没合作过"
]

# JSONL log file
LOG_FILE: Path = Path(__file__).parent.parent / "logs" / "decisions.jsonl"

# LLM config (placeholder — Phase 2+ will set actual provider)
LLM_API_BASE: str = "https://api.openai.com/v1"
LLM_API_KEY: str = ""
LLM_MODEL: str = "gpt-4"
```

## Verify
`pytest decision_system/tests/test_types.py decision_system/tests/test_config.py -v` — all pass
</action>
  <verify>
    <automated>pytest decision_system/tests/test_types.py decision_system/tests/test_config.py -v</automated>
  </verify>
  <done>
    SceneType enum has 6 values; Pydantic validators reject empty conflict; MAX_HOPS=5, LLM_TIMEOUT=120.0, NEGATIVE_ROI_KEYWORDS non-empty
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: router.py + circuit_breaker.py + logging_utils.py + cli.py + __main__.py + workflow.py</name>
  <files>decision_system/router.py, decision_system/circuit_breaker.py, decision_system/logging_utils.py, decision_system/cli.py, decision_system/__main__.py, decision_system/workflow.py</files>
  <action>
## Goal
Build the complete router with all guards (ROI, circuit breaker, timeout) and CLI entry point, plus the sequential-dispatch workflow orchestrator (INFRA-02).

## circuit_breaker.py

```python
"""Simple circuit breaker — max hops counter (not full OPEN/HALF_OPEN state machine)"""
class CircuitBreaker:
    def __init__(self, max_hops: int = 5):
        self.max_hops = max_hops
        self._hop_count = 0

    def record_hop(self) -> None:
        self._hop_count += 1

    def check(self) -> bool:
        """Returns True if circuit should trip (hop limit reached)"""
        return self._hop_count >= self.max_hops

    def get_error(self) -> dict:
        return {
            "error": "circuit_open",
            "message": f"超过最大调用次数({self.max_hops}次)，熔断触发",
            "hops": self._hop_count
        }

    def reset(self) -> None:
        self._hop_count = 0
```

## logging_utils.py

```python
"""JSONL append-only decision logging"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from config import LOG_FILE

def log_decision(
    user_input: str,
    roi_value: Optional[float],
    router_result: dict[str, Any],
    dispatch_result: Optional[dict[str, Any]] = None,
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

## router.py

Create `decision_system/router.py` — extend existing keyword patterns from `decision-cognition-skill/agents/router.py`:

**ROI pre-filter (META-01: 实事求是):**
```python
from config import NEGATIVE_ROI_KEYWORDS
from types import ROIStatus

def check_roi(user_input: str, roi_value: Optional[float] = None) -> tuple[ROIStatus, str]:
    if roi_value is not None:
        if roi_value < 0:
            return ROIStatus.NEGATIVE, f"预期ROI为负: {roi_value}"
        return ROIStatus.POSITIVE, f"ROI={roi_value}"
    for kw in NEGATIVE_ROI_KEYWORDS:
        if kw in user_input:
            return ROIStatus.NEGATIVE, f"检测到ROI负面关键词: {kw}"
    return ROIStatus.UNKNOWN, "无法确定ROI"
```

**Scene classification (CORE-01):** Use existing `_determine_scenario_type()` patterns from router.py lines 245-257 with these types: trivial/reversible/major/innovative/emotional.

**Main conflict extraction (CORE-02, META-02):** Use existing `_extract_main_conflict()` keyword patterns from router.py lines 171-210:
- "钱/资金/预算/成本" → RESOURCE
- "时间/精力/忙" → RESOURCE
- "担心/风险/害怕" → RISK
- "还是/或者/哪个" → CHOICE
- "第一次/新人/没合作过" → GROWTH

**2-minute SLA (CORE-03):**
- Trivial/reversible: `get_fast_recommendation()` returns immediately without LLM call
- Major/innovative: httpx call with `timeout=120.0`

**Circuit breaker (INFRA-03):**
- Increment hop counter before each agent dispatch
- If `circuit_breaker.check()` returns True → return circuit_open error, no further dispatch

**Agent dispatch stub (CORE-04):**
- Return `recommended_agents` list based on scene_type:
  - TRIVIAL/REVERSIBLE: [] (fast path, no agents)
  - MAJOR: ["wise-decider-001", "bias-scanner-001"]
  - INNOVATIVE: ["wise-decider-001", "first-principle-001"]
  - EMOTIONAL: ["bias-scanner-001"]

**Router.analyze() flow:**
1. ROI pre-filter (META-01) — FIRST, before anything else
2. If blocked → return RouterResult with roi_blocked=True, BLOCKED type
3. Scene classification (CORE-01)
4. Main conflict extraction (CORE-02, META-02)
5. Return RouterResult with recommended_agents based on scene type (CORE-04)

## workflow.py (INFRA-02: Sequential dispatch orchestrator)

Create `decision_system/workflow.py` — workflow orchestrator that calls agents sequentially (parallel dispatch is Phase 4):

```python
"""Workflow orchestrator — sequential agent dispatch (INFRA-02)"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from router import DecisionRouter
from circuit_breaker import CircuitBreaker
from config import MAX_HOPS, LLM_TIMEOUT

@dataclass
class WorkflowResult:
    """Workflow execution result"""
    router_result: Optional[Dict[str, Any]] = None
    agent_results: List[Dict[str, Any]] = field(default_factory=list)
    circuit_open: bool = False
    circuit_error: Optional[Dict[str, Any]] = None
    final_decision: Optional[str] = None
    final_action: Optional[str] = None

class DecisionWorkflow:
    """
    Workflow orchestrator with sequential dispatch mode.
    Phase 1: sequential only. Phase 4 adds parallel dispatch.
    """

    def __init__(self):
        self.router = DecisionRouter()
        self.circuit_breaker = CircuitBreaker(max_hops=MAX_HOPS)
        self.name = "DecisionWorkflow"
        self.version = "1.0"

    def dispatch_agents(
        self,
        user_input: str,
        agent_list: List[str],
        router_result: Dict[str, Any]
    ) -> WorkflowResult:
        """
        Dispatch agents SEQUENTIALLY (Phase 1 behavior).
        Phase 4 will add parallel dispatch via asyncio.gather.

        Each agent is called in order. If circuit breaker trips mid-stream,
        remaining agents are skipped and circuit_open=True is returned.

        Args:
            user_input: raw user decision description
            agent_list: list of agent IDs from router.recommended_agents
            router_result: already-computed RouterResult dict

        Returns:
            WorkflowResult with agent_results populated in sequence order
        """
        result = WorkflowResult(router_result=router_result)

        for agent_id in agent_list:
            # Check circuit breaker BEFORE each dispatch
            if self.circuit_breaker.check():
                result.circuit_open = True
                result.circuit_error = self.circuit_breaker.get_error()
                return result

            # Record hop
            self.circuit_breaker.record_hop()

            # Call agent (stubbed — Phase 2+ provides real agent implementations)
            agent_result = self._call_agent(agent_id, user_input, router_result)
            result.agent_results.append(agent_result)

        return result

    def _call_agent(
        self,
        agent_id: str,
        user_input: str,
        router_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a single agent by ID.
        Phase 1: returns stub result. Phase 2+ wires real agents.
        """
        # Stub: return placeholder result until Phase 2 agent implementations
        return {
            "agent_id": agent_id,
            "status": "stub",
            "conclusion": f"[STUB] {agent_id} called for: {user_input[:50]}..."
        }

    def run(self, user_input: str) -> WorkflowResult:
        """
        Full workflow: ROI check → router → sequential agent dispatch.

        Args:
            user_input: user decision description

        Returns:
            WorkflowResult
        """
        # Step 1: Router analysis
        router_result = self.router.analyze(user_input)
        router_dict = router_result.to_json() if hasattr(router_result, 'to_json') else {}

        # Step 2: ROI guard (META-01)
        if router_dict.get("roi_blocked"):
            result = WorkflowResult(router_result=router_dict)
            result.final_decision = "ROI为负，决策阻断"
            result.final_action = "不做任何资源投入"
            return result

        # Step 3: Sequential agent dispatch (INFRA-02)
        agent_list = router_dict.get("recommended_agents", [])
        result = self.dispatch_agents(user_input, agent_list, router_dict)

        # Step 4: Simple arbitration (stub — Phase 3+ expands)
        if result.agent_results:
            result.final_decision = result.agent_results[-1].get("conclusion", "已分析")
            result.final_action = "参考以上agent结论做决定"
        else:
            result.final_decision = "快速决策路径"
            result.final_action = "可直接执行"

        return result
```

## cli.py + __main__.py

**cli.py:**
```python
"""CLI interface — 全中文输出"""
import argparse
from typing import Optional
from router import DecisionRouter, check_roi
from types import ROIStatus, SceneType
from logging_utils import log_decision

def run_cli(decision: str, roi: Optional[float] = None, output: str = "text") -> None:
    router = DecisionRouter()

    # ROI pre-filter (META-01)
    roi_status, roi_reason = check_roi(decision, roi)
    if roi_status == ROIStatus.NEGATIVE:
        print(f"【ROI拦截】{roi_reason}")
        log_decision(decision, roi, {"status": "blocked", "reason": roi_reason}, error="roi_negative")
        return

    result = router.analyze(decision)

    # Fast path for trivial/reversible (CORE-03: 2-min SLA)
    if result.scenario_type.value in ["trivial", "reversible"]:
        fast_rec = get_fast_recommendation(result.scenario_type, result.main_conflict)
        print(fast_rec)
        log_decision(decision, roi, result.to_json(), {"fast_path": True})
    else:
        output_str = result.model_dump_json(ensure_ascii=False, exclude_none=True)
        print(output_str)
        log_decision(decision, roi, result.to_json())

def get_fast_recommendation(scenario_type: SceneType, main_conflict: str) -> str:
    if scenario_type == SceneType.TRIVIAL:
        return f"【快速决策】{main_conflict} — 建议: 立即执行，后果可控"
    elif scenario_type == SceneType.REVERSIBLE:
        return f"【可试错】{main_conflict} — 建议: 小范围试点，验证后扩大"
    raise ValueError("get_fast_recommendation only for trivial/reversible")
```

**__main__.py:**
```python
"""Entry point: python -m decision_system"""
from cli import run_cli
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="决策认知系统 v2.0")
    parser.add_argument("decision", type=str, help="你的决策描述")
    parser.add_argument("--roi", type=float, default=None, help="ROI值（可选）")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()
    run_cli(args.decision, args.roi, args.output)
```

## Verify
1. `pytest decision_system/tests/test_router.py decision_system/tests/test_circuit_breaker.py decision_system/tests/test_cli.py decision_system/tests/test_logging.py -v` — all pass
2. `python -m decision_system "要不要今天中午吃什么"` — returns fast recommendation (trivial path)
3. `python -m decision_system "要不要免费送鞋给这个0粉丝网红"` — returns 【ROI拦截】
4. `python -m decision_system --help` — shows usage
5. `python -c "from workflow import DecisionWorkflow, dispatch_agents; w = DecisionWorkflow(); print(w.name, w.version)"` — imports and prints version
</action>
  <verify>
    <automated>pytest decision_system/tests/test_router.py decision_system/tests/test_circuit_breaker.py decision_system/tests/test_cli.py decision_system/tests/test_logging.py -v</automated>
  </verify>
  <done>
    Router classifies scene type, identifies main conflict, blocks ROI-negative, fast path returns within 2s, circuit breaker trips at hop 5, CLI outputs Chinese, decisions logged to JSONL, workflow dispatch_agents() calls agents sequentially
  </done>
</task>

</tasks>

<verification>
## Phase 1 Integration Checks

1. **CORE-01 + CORE-02 + META-02:** `python -m decision_system "我要不要花5000块投这个网红"` — scene_type != BLOCKED, main_conflict extracted
2. **CORE-03 (2-min SLA):** Wall-clock timing of trivial input — < 2000ms
3. **CORE-04:** Major scenario returns recommended_agents list non-empty
4. **INFRA-02:** `dispatch_agents()` calls agents sequentially; parallel dispatch not used
5. **INFRA-03:** After 5 agent dispatch calls, circuit breaker returns circuit_open
6. **INFRA-01:** Pydantic validation rejects empty conflict string
7. **META-01:** ROI-negative input blocked before any agent dispatch
8. **OUT-02:** decisions.jsonl contains appended record after each run
</verification>

<success_criteria>
1. User can input a decision scenario and receive scene type classification (trivial/reversible/major/innovative) within 2 seconds
2. Router correctly identifies main conflict (主要矛盾) via keyword pattern matching
3. Trivial/reversible decisions return fast recommendation without invoking full agent chain
4. ROI-negative scenarios are blocked at router level before agent chain executes
5. Circuit breaker triggers and returns circuit_open error after 5 agent hops
6. Workflow orchestrator (INFRA-02) dispatches agents sequentially via dispatch_agents()
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-router/01-SUMMARY.md` summarizing what was built and referencing test results.
</output>
