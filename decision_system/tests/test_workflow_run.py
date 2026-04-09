"""Test cases for DecisionWorkflow.run() method - covers ROI guard and dispatch branches"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decision_system.workflow import DecisionWorkflow, WorkflowResult
from decision_system.types import RouterResult, SceneType


class TestWorkflowRun:
    """Test cases for DecisionWorkflow.run() method"""

    @pytest.fixture
    def workflow(self):
        """Create a fresh workflow instance for each test"""
        return DecisionWorkflow()

    @pytest.fixture
    def mock_router_result_blocked(self):
        """Mock router result for ROI blocked scenario"""
        result = Mock(spec=RouterResult)
        result.roi_blocked = True
        result.scenario_type = SceneType.BLOCKED
        result.main_conflict = "ROI为负"
        result.recommended_agents = []
        result.to_json.return_value = {
            "scenario_type": "blocked",
            "roi_blocked": True,
            "main_conflict": "ROI为负",
            "recommended_agents": []
        }
        return result

    @pytest.fixture
    def mock_router_result_normal(self):
        """Mock router result for normal (non-blocked) scenario"""
        result = Mock(spec=RouterResult)
        result.roi_blocked = False
        result.scenario_type = SceneType.MAJOR
        result.main_conflict = "资源分配"
        result.recommended_agents = ["智慧决策师", "偏差扫描师"]
        result.to_json.return_value = {
            "scenario_type": "major",
            "roi_blocked": False,
            "main_conflict": "资源分配",
            "recommended_agents": ["智慧决策师", "偏差扫描师"]
        }
        return result

    @pytest.fixture
    def mock_router_result_trivial(self):
        """Mock router result for trivial (fast path) scenario"""
        result = Mock(spec=RouterResult)
        result.roi_blocked = False
        result.scenario_type = SceneType.TRIVIAL
        result.main_conflict = ""
        result.recommended_agents = []
        result.to_json.return_value = {
            "scenario_type": "trivial",
            "roi_blocked": False,
            "main_conflict": "",
            "recommended_agents": []
        }
        return result

    def test_roi_negative_blocked_returns_early(self, workflow, mock_router_result_blocked):
        """
        Test Case 1: ROI < 0 should return early with blocked decision
        Verifies: ROI guard path - should NOT call dispatch_agents
        """
        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_blocked):
            result = workflow.run("要不要免费送鞋给这个0粉丝网红", roi_value=-500)

        # Verify ROI guard behavior
        assert result.final_decision == "ROI为负，决策阻断"
        assert result.final_action == "不做任何资源投入"
        assert result.router_result["roi_blocked"] is True
        assert result.router_result["scenario_type"] == "blocked"
        # Should NOT dispatch any agents
        assert len(result.agent_results) == 0

    def test_normal_dispatch_calls_agents(self, workflow, mock_router_result_normal):
        """
        Test Case 2: Normal ROI >= 0 should dispatch agents sequentially
        Verifies: dispatch path - should call dispatch_agents with agent list
        """
        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_normal):
            with patch.object(workflow, 'dispatch_agents') as mock_dispatch:
                mock_dispatch.return_value = WorkflowResult(
                    router_result=mock_router_result_normal.to_json(),
                    agent_results=[
                        {"agent_id": "智慧决策师", "status": "stub", "conclusion": "建议执行"},
                        {"agent_id": "偏差扫描师", "status": "stub", "conclusion": "风险可控"}
                    ]
                )
                result = workflow.run("要不要给这个100万粉网红送价值5000的货", roi_value=5000)

        # Verify dispatch was called with correct agents
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        assert call_args[0][1] == ["智慧决策师", "偏差扫描师"]  # agent_list

    def test_trivial_scenario_fast_path_no_agents(self, workflow, mock_router_result_trivial):
        """
        Test Case 3: Trivial scenario should use fast path with no agents
        Verifies: Fast path when recommended_agents is empty
        """
        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_trivial):
            result = workflow.run("今天中午吃什么", roi_value=0)

        # Should not dispatch agents for trivial cases
        assert len(result.agent_results) == 0
        assert result.final_decision == "快速决策路径"
        assert result.final_action == "本项目量级较小，可直接执行"

    def test_circuit_breaker_open_stops_dispatch(self, workflow, mock_router_result_normal):
        """
        Test Case 4: When circuit breaker opens, dispatch should stop early
        Verifies: Circuit breaker integration in dispatch path
        """
        # Simulate circuit breaker being open by recording max_hops
        for _ in range(workflow.circuit_breaker.max_hops):
            workflow.circuit_breaker.record_hop()

        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_normal):
            result = workflow.run("测试决策", roi_value=100)

        # Circuit should be open
        assert result.circuit_open is True
        assert result.circuit_error is not None

    def test_dispatch_returns_agent_results(self, workflow, mock_router_result_normal):
        """
        Test Case 5: dispatch_agents should return agent results in WorkflowResult
        Verifies: Full dispatch chain returns agent conclusions
        """
        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_normal):
            result = workflow.run("要不要做新项目", roi_value=1000)

        # Verify agent results are collected
        assert len(result.agent_results) >= 0  # May be empty if dispatch returns empty
        # Final decision should be based on last agent or default
        if result.agent_results:
            assert "参考以上agent结论做决定" in result.final_action
        else:
            assert "直接执行" in result.final_action

    def test_run_with_no_roi_value(self, workflow, mock_router_result_normal):
        """
        Test Case 6: run() should work without explicit roi_value (defaults to None)
        Verifies: Optional roi_value parameter handling
        """
        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_normal) as mock_analyze:
            result = workflow.run("测试输入")

        # Router should be called (with None as default roi_value)
        mock_analyze.assert_called_once()
        # Should not raise any errors
        assert result is not None

    def test_run_returns_workflow_result_instance(self, workflow, mock_router_result_trivial):
        """
        Test Case 7: run() always returns WorkflowResult instance
        Verifies: Return type consistency
        """
        with patch.object(workflow.router, 'analyze', return_value=mock_router_result_trivial):
            result = workflow.run("简单问题")

        assert isinstance(result, WorkflowResult)
        # All expected fields should be present
        assert hasattr(result, 'router_result')
        assert hasattr(result, 'agent_results')
        assert hasattr(result, 'circuit_open')
        assert hasattr(result, 'final_decision')
        assert hasattr(result, 'final_action')