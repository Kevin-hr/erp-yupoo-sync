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
