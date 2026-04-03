import asyncio
from typing import Optional, List, Dict, Any, Tuple
import decision_system.config as config
from decision_system.types import SceneType, ROIStatus, RouterResult, ConflictCategory


def check_roi(user_input: str, roi_value: Optional[float] = None) -> tuple[ROIStatus, str]:
    """ROI pre-filter (META-01)"""
    if roi_value is not None:
        if roi_value < 0:
            return ROIStatus.NEGATIVE, f"预期ROI为负: {roi_value}"
        return ROIStatus.POSITIVE, f"ROI={roi_value}"
    
    # Keyword based ROI check
    for kw in config.NEGATIVE_ROI_KEYWORDS:
        if kw in user_input:
            return ROIStatus.NEGATIVE, f"检测到ROI负面关键词: {kw}"
    return ROIStatus.UNKNOWN, "无法确定ROI"

class DecisionRouter:
    """Decision router with scene classification and conflict extraction (CORE-01, CORE-02)"""
    
    def __init__(self):
        self.name = "DecisionRouter"

    def analyze(self, user_input: str, roi_value: Optional[float] = None) -> RouterResult:
        """Analyze user input and return routing result"""
        
        # 1. ROI check (FIRST)
        roi_status, roi_reason = check_roi(user_input, roi_value)
        if roi_status == ROIStatus.NEGATIVE:
            return RouterResult(
                scenario_type=SceneType.BLOCKED,
                main_conflict="ROI红线触碰",
                complexity="low",
                emotion_state="stable",
                options_clear=True,
                recommended_agents=[],
                reason=roi_reason,
                key_questions=["ROI为何为负？"],
                roi_blocked=True
            )

        # 2. Scene Classification (CORE-01)
        scene_type = self._determine_scenario_type(user_input)
        
        # 3. Main Conflict Extraction (CORE-02)
        conflict_desc, conflict_cat = self._extract_main_conflict(user_input)
        
        # 4. Recommended Agents (CORE-04)
        agents = self._recommend_agents(scene_type)
        
        return RouterResult(
            scenario_type=scene_type,
            main_conflict=conflict_desc,
            complexity="medium" if scene_type in [SceneType.MAJOR, SceneType.INNOVATIVE] else "low",
            emotion_state="stable", # Placeholder
            options_clear=False if "不知道" in user_input or "?" in user_input else True,
            recommended_agents=agents,
            reason=f"基于关键词匹配识到 {scene_type.value} 场景",
            key_questions=[f"关于 {conflict_desc} 的核心风险点是什么？"]
        )

    def _determine_scenario_type(self, user_input: str) -> SceneType:
        """Keyword-based scene classification"""
        # Trivial
        if any(kw in user_input for kw in ["吃什么", "几点", "哪里买", "天气"]):
            return SceneType.TRIVIAL
        
        # Innovative / Major
        if any(kw in user_input for kw in ["独立站", "全新类目", "大批量", "战略", "千万", "百万"]):
            return SceneType.INNOVATIVE if "全新" in user_input else SceneType.MAJOR
            
        # Reversible
        if any(kw in user_input for kw in ["试试", "测试", "换一个", "样品"]):
            return SceneType.REVERSIBLE
            
        return SceneType.MAJOR # Default to Major for safety

    def _extract_main_conflict(self, user_input: str) -> Tuple[str, ConflictCategory]:
        """Keyword-based conflict extraction"""
        if any(kw in user_input for kw in ["钱", "资金", "预算", "成本", "贵", "价值"]):
            return "资源/资金配置", ConflictCategory.RESOURCE

        if any(kw in user_input for kw in ["担心", "风险", "害怕", "封号"]):
            return "风险控制", ConflictCategory.RISK
        if any(kw in user_input for kw in ["还是", "或者", "两难"]):
            return "方案选择", ConflictCategory.CHOICE
        if any(kw in user_input for kw in ["第一次", "新人", "首次"]):
            return "增长与信任建立", ConflictCategory.GROWTH
            
        return "决策不确定性", ConflictCategory.CHOICE

    def _recommend_agents(self, scene_type: SceneType) -> List[str]:
        """Agent recommendation logic (CORE-04)"""
        if scene_type in [SceneType.TRIVIAL, SceneType.REVERSIBLE]:
            return [] # Fast path
        if scene_type == SceneType.MAJOR:
            return ["wise-decider-001", "bias-scanner-001"]
        if scene_type == SceneType.INNOVATIVE:
            return ["wise-decider-001", "first-principle-001"]
        if scene_type == SceneType.EMOTIONAL:
            return ["bias-scanner-001"]
        return ["wise-decider-001"]
