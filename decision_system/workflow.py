"""Workflow orchestrator — sequential agent dispatch (INFRA-02)"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import decision_system.config as config
from decision_system.router import DecisionRouter
from decision_system.circuit_breaker import CircuitBreaker

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
        self.circuit_breaker = CircuitBreaker(max_hops=config.MAX_HOPS)
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
        Each agent is called in order. If circuit breaker trips mid-stream,
        remaining agents are skipped and circuit_open=True is returned.
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
        Call a single agent by ID (stub).
        """
        return {
            "agent_id": agent_id,
            "status": "stub",
            "conclusion": f"[STUB] {agent_id} called for: {user_input[:50]}..."
        }

    def run(self, user_input: str, roi_value: Optional[float] = None) -> WorkflowResult:
        """
        Full workflow: Router analysis → ROI check → sequential agent dispatch.
        """
        # Step 1: Router analysis
        router_result = self.router.analyze(user_input, roi_value)
        router_dict = router_result.to_json()
        
        # Step 2: ROI guard check (already handled by router analysis return scenario_type == BLOCKED)
        if router_result.roi_blocked or router_dict.get("scenario_type") == "blocked":
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
            result.final_action = "本项目量级较小，可直接执行"

        return result
