"""
Data models for LLM interaction analysis.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class PromptComponentType(str, Enum):
    """Prompt 组件类型"""
    SYSTEM = "system"              # 系统指令
    HISTORY = "history"            # 历史对话
    NEW_USER_INPUT = "new_input"   # 新用户输入
    TOOLS = "tools"                # 工具定义
    CONTEXT = "context"            # 上下文（文件、搜索结果等）
    EXAMPLES = "examples"          # Few-shot 示例


class IntentType(str, Enum):
    """用户意图类型"""
    INFORMATION_SEEKING = "information_seeking"
    TASK_EXECUTION = "task_execution"
    CREATIVE_GENERATION = "creative_generation"
    ANALYSIS_REQUEST = "analysis_request"
    CLARIFICATION = "clarification"
    FOLLOW_UP = "follow_up"
    CONTEXT_SETTING = "context_setting"
    REFINEMENT = "refinement"
    VALIDATION = "validation"
    EXPLORATION = "exploration"


class PromptComponent(BaseModel):
    """单个 Prompt 组件"""
    type: PromptComponentType
    content: str
    tokens: int
    role: Optional[str] = None     # user/assistant/system
    timestamp: Optional[str] = None

    # 重复性标记
    is_repeated: bool = False      # 是否在上一轮出现过
    first_seen_turn: Optional[int] = None  # 首次出现的轮次

    # 变化标记
    diff_type: Optional[str] = None  # added/modified/removed/unchanged
    changes: Optional[List[Dict]] = None  # 具体变化内容

    class Config:
        use_enum_values = True


class IntentUnit(BaseModel):
    """表示对话轮次中的单个用户意图单元"""
    intent_type: IntentType
    content: str
    confidence: float
    tokens: int
    keywords: List[str]
    context_dependencies: List[str]  # 对之前轮次/上下文的引用
    metadata: Dict[str, Any]

    def __init__(self, **data):
        super().__init__(**data)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在 0.0 到 1.0 之间，当前为 {self.confidence}")


class TurnIntentAnalysis(BaseModel):
    """对话轮次的完整意图分析"""
    turn_index: int
    intent_units: List[IntentUnit]
    primary_intent: IntentType
    intent_confidence: float
    context_references: List[int]  # 引用的轮次索引
    complexity_score: float  # 0-1 表示轮次复杂度

    @property
    def total_tokens(self) -> int:
        """所有意图单元的总 token 数"""
        return sum(unit.tokens for unit in self.intent_units)

    @property
    def intent_diversity(self) -> float:
        """该轮次中意图多样性（0-1）"""
        if not self.intent_units:
            return 0.0
        unique_intents = len(set(unit.intent_type for unit in self.intent_units))
        return unique_intents / len(self.intent_units)


class PromptStructure(BaseModel):
    """完整 Prompt 结构"""
    turn_index: int
    total_tokens: int
    components: List[PromptComponent]

    # 统计信息
    stats: Dict[str, Any] = Field(default_factory=dict)
    # {
    #   "system_tokens": 100,
    #   "history_tokens": 5000,
    #   "new_tokens": 50,
    #   "repeated_ratio": 0.98,
    #   "unique_tokens": 150
    # }
    intent_analysis: Optional[TurnIntentAnalysis] = None  # 新增意图分析字段


class DiffOperation(str, Enum):
    """差异操作类型"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class TurnDiff(BaseModel):
    """两轮之间的差异"""
    from_turn: int
    to_turn: int

    # 新增的组件
    added_components: List[PromptComponent] = Field(default_factory=list)

    # 删除的组件
    removed_components: List[PromptComponent] = Field(default_factory=list)

    # 修改的组件
    modified_components: List[Dict[str, Any]] = Field(default_factory=list)
    # [{"old": PromptComponent, "new": PromptComponent, "changes": [...]}]

    # 统计
    total_changes: int = 0
    added_tokens: int = 0
    removed_tokens: int = 0
    intent_diff: Optional[Dict[str, Any]] = None  # 新增意图差异字段


class FlowNode(BaseModel):
    """流程图节点"""
    turn_index: int
    node_type: str  # user_input/llm_response/tool_call/error
    summary: str    # 简短摘要（30字以内）
    tokens: int
    cost: float
    duration_ms: Optional[int] = None

    # 状态
    status: str  # success/error/partial
    error: Optional[str] = None
    intent_type: IntentType  # 新增意图类型字段


class FlowEdge(BaseModel):
    """流程图边"""
    from_node: int
    to_node: int
    edge_type: str  # prompt/response/retry/branch
    label: Optional[str] = None


class ConversationFlow(BaseModel):
    """整体对话流程"""
    session_id: str
    nodes: List[FlowNode]
    edges: List[FlowEdge]

    # 宏观统计
    total_turns: int
    total_tokens: int
    total_cost: float
    success_rate: float
    avg_response_time_ms: float
    intent_transitions: Dict[IntentType, Dict[IntentType, int]]  # 新增意图转移矩阵

    def get_intent_transition_probability(self, from_intent: IntentType, to_intent: IntentType) -> float:
        """计算从一个意图转移到另一个意图的概率"""
        if from_intent not in self.intent_transitions:
            return 0.0
        total_transitions = sum(self.intent_transitions[from_intent].values())
        if total_transitions == 0:
            return 0.0
        return self.intent_transitions[from_intent].get(to_intent, 0) / total_transitions

    @property
    def average_intent_complexity(self) -> float:
        """所有轮次的平均意图复杂度"""
        if not self.nodes:
            return 0.0
        return sum(node.metadata.get('complexity_score', 0.0) for node in self.nodes) / len(self.nodes)
