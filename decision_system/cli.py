"""CLI interface — 全中文输出 (Chinese Output)"""
import argparse
import json
from typing import Optional

from decision_system.workflow import DecisionWorkflow
from decision_system.types import SceneType, ROIStatus
from decision_system.logging_utils import log_decision

def run_cli(decision: str, roi: Optional[float] = None, output: str = "text") -> None:
    """Run the decision system through CLI"""
    workflow = DecisionWorkflow()
    
    # Run the full workflow
    result = workflow.run(decision, roi)
    
    # Handle Output
    if output == "json":
        print(json.dumps({
            "status": "success",
            "decision": result.final_decision,
            "action": result.final_action,
            "router": result.router_result,
            "agents": result.agent_results,
            "circuit_breaker": result.circuit_error
        }, ensure_ascii=False, indent=2))
    else:
        # Text output (Chinese)
        if result.router_result and result.router_result.get("roi_blocked"):
            print(f"【⚠️ ROI拦截】{result.router_result.get('reason')}")
            print(f"最终建议: {result.final_action}")
            return

        scenario_zh = {
            "trivial": "日常琐事",
            "reversible": "可逆测试",
            "major": "重大决策",
            "innovative": "战略创新",
            "emotional": "情感波动",
            "blocked": "已阻断"
        }.get(result.router_result.get("scenario_type"), "未知")

        print(f"========================================")
        print(f"【场景分类】: {scenario_zh}")
        print(f"【主要矛盾】: {result.router_result.get('main_conflict')}")
        print(f"【分析结论】: {result.final_decision}")
        print(f"【行动建议】: {result.final_action}")
        
        if result.circuit_open:
            print(f"【❌ 熔断触发】: {result.circuit_error.get('message')}")
        
        if result.agent_results:
            print(f"【参与 Agent】: {', '.join([a['agent_id'] for a in result.agent_results])}")
        print(f"========================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="决策认知系统 v2.0")
    parser.add_argument("decision", type=str, help="你的决策描述")
    parser.add_argument("--roi", type=float, default=None, help="ROI值（可选）")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()
    run_cli(args.decision, args.roi, args.output)
