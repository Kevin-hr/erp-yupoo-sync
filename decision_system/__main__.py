"""Entry point: python -m decision_system"""
import sys
from pathlib import Path

# Fix path to allow running as module
if __name__ == "__main__":
    from decision_system.cli import run_cli
    import argparse

    parser = argparse.ArgumentParser(description="决策认知系统 v2.0")
    parser.add_argument("decision", type=str, help="你的决策描述")
    parser.add_argument("--roi", type=float, default=None, help="ROI值（可选）")
    parser.add_argument("--output", choices=["json", "text"], default="text", help="输出格式")
    args = parser.parse_args()
    run_cli(args.decision, args.roi, args.output)
