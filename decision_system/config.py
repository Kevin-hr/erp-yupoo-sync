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
