"""JSONL append-only decision logging"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
import decision_system.config as config

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
    log_file = config.LOG_FILE
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
