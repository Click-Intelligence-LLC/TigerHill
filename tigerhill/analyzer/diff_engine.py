"""
Diff Engine

Computes differences between consecutive prompt structures,
enabling delta/incremental visualization.
"""

import difflib
from typing import List, Dict, Set, Tuple, Optional, Any
from tigerhill.analyzer.models import (
    PromptStructure,
    TurnDiff,
    DiffOperation,
    PromptComponent,
    PromptComponentType,
    IntentType
)


class DiffEngine:
    """计算两轮之间的差异"""

    def compute_diff(
        self,
        from_structure: PromptStructure,
        to_structure: PromptStructure
    ) -> TurnDiff:
        """
        计算两个 PromptStructure 之间的差异

        Args:
            from_structure: 源结构（较早的 turn）
            to_structure: 目标结构（较新的 turn）

        Returns:
            TurnDiff 对象
        """
        diff = TurnDiff(
            from_turn=from_structure.turn_index,
            to_turn=to_structure.turn_index
        )

        # 1. 找出新增的组件
        from_contents = {
            self._component_key(c): c
            for c in from_structure.components
        }

        for comp in to_structure.components:
            key = self._component_key(comp)
            if key not in from_contents:
                diff.added_components.append(comp)
                diff.added_tokens += comp.tokens

        # 2. 找出删除的组件
        to_contents = {
            self._component_key(c): c
            for c in to_structure.components
        }

        for comp in from_structure.components:
            key = self._component_key(comp)
            if key not in to_contents:
                diff.removed_components.append(comp)
                diff.removed_tokens += comp.tokens

        # 3. 找出修改的组件（同类型但内容不同）
        modified = self._find_modified_components(
            from_structure,
            to_structure
        )
        diff.modified_components.extend(modified)

        # 4. 计算意图差异
        diff.intent_diff = self._compute_intent_diff(
            from_structure.intent_analysis,
            to_structure.intent_analysis
        )

        diff.total_changes = (
            len(diff.added_components) +
            len(diff.removed_components) +
            len(diff.modified_components)
        )

        return diff
    
    def _analyze_intent_units_diff(
        self,
        from_units: List,
        to_units: List
    ) -> Dict[str, Any]:
        """
        分析IntentUnit列表之间的详细差异
        
        Args:
            from_units: 源IntentUnit列表
            to_units: 目标IntentUnit列表
            
        Returns:
            IntentUnit差异分析结果
        """
        from_dict = {unit.intent_type: unit for unit in from_units}
        to_dict = {unit.intent_type: unit for unit in to_units}
        
        added_intents = set(to_dict.keys()) - set(from_dict.keys())
        removed_intents = set(from_dict.keys()) - set(to_dict.keys())
        common_intents = set(from_dict.keys()) & set(to_dict.keys())
        
        result = {
            "total_added": len(added_intents),
            "total_removed": len(removed_intents),
            "total_modified": 0,
            "added_intents": list(added_intents),
            "removed_intents": list(removed_intents),
            "modified_intents": []
        }
        
        # 分析共同意图的变化
        for intent_type in common_intents:
            from_unit = from_dict[intent_type]
            to_unit = to_dict[intent_type]
            
            confidence_change = to_unit.confidence - from_unit.confidence
            tokens_change = to_unit.tokens - from_unit.tokens
            
            # 检查是否有显著变化（置信度变化超过阈值或关键词变化）
            has_significant_change = (
                abs(confidence_change) > 0.1 or  # 置信度变化超过10%
                tokens_change != 0 or
                set(to_unit.keywords) != set(from_unit.keywords)
            )
            
            if has_significant_change:
                result["total_modified"] += 1
                result["modified_intents"].append({
                    "intent_type": intent_type.value,
                    "confidence_change": confidence_change,
                    "tokens_change": tokens_change,
                    "keywords_added": list(set(to_unit.keywords) - set(from_unit.keywords)),
                    "keywords_removed": list(set(from_unit.keywords) - set(to_unit.keywords)),
                    "context_dependencies_change": {
                        "old": from_unit.context_dependencies,
                        "new": to_unit.context_dependencies
                    }
                })
        
        return result
    
    def _classify_intent_transition(
        self,
        from_intent,
        to_intent
    ) -> str:
        """
        分类意图转换类型
        
        Args:
            from_intent: 源意图类型
            to_intent: 目标意图类型
            
        Returns:
            转换类型描述
        """
        # 定义常见的意图转换模式
        transition_patterns = {
            # 从询问到操作
            ("INQUIRY", "OPERATION"): "inquiry_to_operation",
            ("INQUIRY", "CREATION"): "inquiry_to_creation",
            
            # 从操作到确认
            ("OPERATION", "CONFIRMATION"): "operation_to_confirmation",
            ("CREATION", "CONFIRMATION"): "creation_to_confirmation",
            
            # 从确认到完成
            ("CONFIRMATION", "COMPLETION"): "confirmation_to_completion",
            
            # 问题解决流程
            ("PROBLEM_REPORTING", "ANALYSIS"): "problem_to_analysis",
            ("ANALYSIS", "SOLUTION"): "analysis_to_solution",
            
            # 学习流程
            ("INQUIRY", "LEARNING"): "inquiry_to_learning",
            ("LEARNING", "APPLICATION"): "learning_to_application",
            
            # 创造性流程
            ("BRAINSTORMING", "CREATION"): "brainstorming_to_creation",
            ("CREATION", "REFINEMENT"): "creation_to_refinement",
            
            # 反向转换（可能需要关注）
            ("OPERATION", "INQUIRY"): "operation_to_inquiry",
            ("COMPLETION", "INQUIRY"): "completion_to_inquiry",
        }
        
        key = (from_intent.value, to_intent.value)
        return transition_patterns.get(key, "unknown_transition")
    
    def _analyze_intent_transition(
        self,
        from_intent,
        to_intent
    ) -> Dict[str, Any]:
        """
        分析意图转换的合理性和模式
        
        Args:
            from_intent: 源意图分析
            to_intent: 目标意图分析
            
        Returns:
            转换分析结果
        """
        transition_type = self._classify_intent_transition(
            from_intent.primary_intent, to_intent.primary_intent
        )
        
        # 分析转换的合理性
        is_natural = transition_type in [
            "inquiry_to_operation", "inquiry_to_creation",
            "operation_to_confirmation", "creation_to_confirmation",
            "confirmation_to_completion", "problem_to_analysis",
            "analysis_to_solution", "brainstorming_to_creation"
        ]
        
        # 分析转换的复杂度变化
        complexity_change = to_intent.complexity_score - from_intent.complexity_score
        
        # 分析置信度变化
        confidence_change = to_intent.intent_confidence - from_intent.intent_confidence
        
        # 检测可能的意图漂移
        intent_drift = self._detect_intent_drift(from_intent, to_intent)
        
        return {
            "transition_type": transition_type,
            "is_natural": is_natural,
            "complexity_change": complexity_change,
            "confidence_change": confidence_change,
            "intent_drift": intent_drift,
            "transition_score": self._calculate_transition_score(
                from_intent, to_intent, is_natural
            )
        }
    
    def _analyze_intent_evolution(
        self,
        from_intent,
        to_intent
    ) -> Dict[str, Any]:
        """
        分析同一意图类型的演化
        
        Args:
            from_intent: 源意图分析
            to_intent: 目标意图分析
            
        Returns:
            演化分析结果
        """
        return {
            "intent_type": from_intent.primary_intent.value,
            "confidence_evolution": {
                "old": from_intent.intent_confidence,
                "new": to_intent.intent_confidence,
                "change": to_intent.intent_confidence - from_intent.intent_confidence,
                "trend": "increasing" if to_intent.intent_confidence > from_intent.intent_confidence else "decreasing"
            },
            "complexity_evolution": {
                "old": from_intent.complexity_score,
                "new": to_intent.complexity_score,
                "change": to_intent.complexity_score - from_intent.complexity_score,
                "trend": "increasing" if to_intent.complexity_score > from_intent.complexity_score else "decreasing"
            },
            "intent_units_evolution": self._analyze_intent_units_evolution(
                from_intent.intent_units, to_intent.intent_units
            ),
            "context_evolution": {
                "references_added": len(set(to_intent.context_references) - set(from_intent.context_references)),
                "references_removed": len(set(from_intent.context_references) - set(to_intent.context_references)),
                "context_stability": len(set(from_intent.context_references) & set(to_intent.context_references)) / max(len(from_intent.context_references), 1)
            }
        }
    
    def _detect_intent_drift(
        self,
        from_intent,
        to_intent
    ) -> Dict[str, Any]:
        """
        检测意图漂移
        
        Args:
            from_intent: 源意图分析
            to_intent: 目标意图分析
            
        Returns:
            意图漂移分析结果
        """
        # 分析关键词的变化
        from_keywords = set()
        to_keywords = set()
        
        for unit in from_intent.intent_units:
            from_keywords.update(unit.keywords)
        
        for unit in to_intent.intent_units:
            to_keywords.update(unit.keywords)
        
        keyword_overlap = len(from_keywords & to_keywords) / max(len(from_keywords | to_keywords), 1)
        
        # 分析上下文依赖的变化
        context_overlap = len(set(from_intent.context_references) & set(to_intent.context_references)) / max(len(set(from_intent.context_references) | set(to_intent.context_references)), 1)
        
        # 判断是否发生显著漂移
        significant_drift = keyword_overlap < 0.3 or context_overlap < 0.5
        
        return {
            "has_drift": significant_drift,
            "keyword_overlap": keyword_overlap,
            "context_overlap": context_overlap,
            "drift_severity": "high" if keyword_overlap < 0.2 else "medium" if keyword_overlap < 0.4 else "low"
        }
    
    def _calculate_transition_score(
        self,
        from_intent,
        to_intent,
        is_natural: bool
    ) -> float:
        """
        计算意图转换的评分
        
        Args:
            from_intent: 源意图分析
            to_intent: 目标意图分析
            is_natural: 是否为自然转换
            
        Returns:
            转换评分 (0-1)
        """
        base_score = 0.7 if is_natural else 0.3
        
        # 置信度变化奖励
        confidence_change = to_intent.intent_confidence - from_intent.intent_confidence
        confidence_score = max(0, min(1, 0.5 + confidence_change * 2))
        
        # 复杂度稳定性奖励
        complexity_change = abs(to_intent.complexity_score - from_intent.complexity_score)
        complexity_score = max(0, 1 - complexity_change / 10)  # 假设复杂度最大差异为10
        
        # 综合评分
        final_score = (base_score * 0.5 + confidence_score * 0.3 + complexity_score * 0.2)
        
        return round(final_score, 3)
    
    def _analyze_intent_units_evolution(
        self,
        from_units: List,
        to_units: List
    ) -> Dict[str, Any]:
        """
        分析IntentUnit列表的演化
        
        Args:
            from_units: 源IntentUnit列表
            to_units: 目标IntentUnit列表
            
        Returns:
            演化分析结果
        """
        from_dict = {unit.intent_type: unit for unit in from_units}
        to_dict = {unit.intent_type: unit for unit in to_units}
        
        evolution_details = []
        
        # 分析共同意图类型的演化
        for intent_type in set(from_dict.keys()) & set(to_dict.keys()):
            from_unit = from_dict[intent_type]
            to_unit = to_dict[intent_type]
            
            evolution_details.append({
                "intent_type": intent_type.value,
                "confidence_change": to_unit.confidence - from_unit.confidence,
                "tokens_change": to_unit.tokens - from_unit.tokens,
                "keywords_evolution": {
                    "preserved": list(set(from_unit.keywords) & set(to_unit.keywords)),
                    "added": list(set(to_unit.keywords) - set(from_unit.keywords)),
                    "removed": list(set(from_unit.keywords) - set(to_unit.keywords))
                },
                "context_dependencies_change": {
                    "old": from_unit.context_dependencies,
                    "new": to_unit.context_dependencies
                }
            })
        
        return {
            "total_evolved": len(evolution_details),
            "evolution_details": evolution_details,
            "average_confidence_change": sum(e["confidence_change"] for e in evolution_details) / len(evolution_details) if evolution_details else 0,
            "average_tokens_change": sum(e["tokens_change"] for e in evolution_details) / len(evolution_details) if evolution_details else 0
        }

    def _component_key(self, comp: PromptComponent) -> Tuple[str, str]:
        """
        生成组件的唯一标识

        Uses (type, content) as key for exact matching.
        """
        return (comp.type.value if hasattr(comp.type, 'value') else comp.type, comp.content)

    def _compute_intent_diff(
        self,
        from_intent: Optional,
        to_intent: Optional
    ) -> Optional[Dict[str, Any]]:
        """
        计算两个轮次之间的意图差异，增强对IntentUnit的详细比较
        
        Args:
            from_intent: 源轮次的意图分析
            to_intent: 目标轮次的意图分析
            
        Returns:
            意图差异字典或 None
        """
        if not from_intent and not to_intent:
            return None
        
        if not from_intent and to_intent:
            return {
                "type": "intent_added",
                "new_intent": to_intent.primary_intent.value,
                "new_confidence": to_intent.intent_confidence,
                "new_complexity": to_intent.complexity_score,
                "new_intent_units": len(to_intent.intent_units),
                "intent_diversity": to_intent.intent_diversity,
                "intent_units_details": self._analyze_intent_units_diff([], to_intent.intent_units)
            }
        
        if from_intent and not to_intent:
            return {
                "type": "intent_removed",
                "old_intent": from_intent.primary_intent.value,
                "old_confidence": from_intent.intent_confidence,
                "old_complexity": from_intent.complexity_score,
                "old_intent_units": len(from_intent.intent_units),
                "intent_diversity": from_intent.intent_diversity,
                "intent_units_details": self._analyze_intent_units_diff(from_intent.intent_units, [])
            }
        
        # 两者都存在，计算详细变化
        diff = {
            "type": "intent_changed",
            "old_intent": from_intent.primary_intent.value,
            "new_intent": to_intent.primary_intent.value,
            "confidence_change": to_intent.intent_confidence - from_intent.intent_confidence,
            "complexity_change": to_intent.complexity_score - from_intent.complexity_score,
            "intent_units_changed": len(to_intent.intent_units) != len(from_intent.intent_units),
            "diversity_change": to_intent.intent_diversity - from_intent.intent_diversity,
            "total_tokens_change": to_intent.total_tokens - from_intent.total_tokens
        }
        
        # 检查意图类型是否改变
        if from_intent.primary_intent != to_intent.primary_intent:
            diff["intent_type_changed"] = True
            diff["intent_transition"] = {
                "from": from_intent.primary_intent.value,
                "to": to_intent.primary_intent.value,
                "transition_type": self._classify_intent_transition(
                    from_intent.primary_intent, 
                    to_intent.primary_intent
                )
            }
            # 分析转换的合理性
            diff["transition_analysis"] = self._analyze_intent_transition(
                from_intent, to_intent
            )
        else:
            diff["intent_type_changed"] = False
            # 同一意图类型的深度分析
            diff["intent_evolution"] = self._analyze_intent_evolution(
                from_intent, to_intent
            )
        
        # 详细的IntentUnit差异分析
        diff["intent_units_details"] = self._analyze_intent_units_diff(
            from_intent.intent_units, to_intent.intent_units
        )
        
        # 上下文引用变化分析
        diff["context_references_change"] = {
            "old_count": len(from_intent.context_references),
            "new_count": len(to_intent.context_references),
            "added_references": list(set(to_intent.context_references) - set(from_intent.context_references)),
            "removed_references": list(set(from_intent.context_references) - set(to_intent.context_references))
        }
        
        return diff

    def _extract_intent_changes(self, old_content: str, new_content: str) -> Optional[Dict[str, Any]]:
        """
        增强的意图变化检测，提供更详细的意图变化分析
        
        Args:
            old_content: 旧内容
            new_content: 新内容
            
        Returns:
            详细的意图变化信息或 None
        """
        if not old_content or not new_content:
            return None
        
        # 基础关键词分析
        old_keywords = set(old_content.lower().split())
        new_keywords = set(new_content.lower().split())
        
        added_keywords = new_keywords - old_keywords
        removed_keywords = old_keywords - new_keywords
        
        # 增强的意图指标检测
        intent_indicators = {
            "question_words": {
                "what", "how", "why", "when", "where", "who", "which", "whether",
                "什么", "怎么", "为什么", "何时", "哪里", "谁", "哪个", "是否"
            },
            "action_words": {
                "create", "generate", "make", "do", "build", "write", "produce", 
                "develop", "design", "implement", "写", "创建", "生成", "做", "构建",
                "开发", "设计", "实现"
            },
            "analysis_words": {
                "analyze", "compare", "evaluate", "examine", "study", "assess",
                "分析", "比较", "评估", "检查", "研究", "审查"
            },
            "problem_words": {
                "problem", "issue", "error", "bug", "trouble", "fail", "wrong",
                "问题", "错误", "故障", "麻烦", "失败"
            },
            "solution_words": {
                "solution", "fix", "solve", "resolve", "answer", "help",
                "解决方案", "修复", "解决", "答案", "帮助"
            },
            "learning_words": {
                "learn", "understand", "explain", "teach", "study", "knowledge",
                "学习", "理解", "解释", "教", "知识"
            },
            "confirmation_words": {
                "confirm", "check", "verify", "sure", "correct", "right",
                "确认", "检查", "验证", "正确"
            },
            "completion_words": {
                "done", "complete", "finish", "end", "ready", "finished",
                "完成", "结束", "准备好"
            },
            "refinement_words": {
                "improve", "better", "optimize", "refine", "enhance", "polish",
                "改进", "更好", "优化", "完善", "提升"
            }
        }
        
        changes = {}
        
        # 分析各类型意图指标的变化
        for indicator_type, words in intent_indicators.items():
            added_indicators = added_keywords & words
            removed_indicators = removed_keywords & words
            
            if added_indicators or removed_indicators:
                # 计算变化强度
                change_intensity = len(added_indicators) + len(removed_indicators)
                
                changes[indicator_type] = {
                    "added": list(added_indicators),
                    "removed": list(removed_indicators),
                    "added_count": len(added_indicators),
                    "removed_count": len(removed_indicators),
                    "change_intensity": change_intensity,
                    "change_significance": "high" if change_intensity >= 3 else "medium" if change_intensity >= 2 else "low"
                }
        
        # 高级意图变化分析
        if changes:
            # 检测主要的意图转换
            primary_changes = self._detect_primary_intent_changes(changes)
            changes["primary_changes"] = primary_changes
            
            # 分析意图变化的连贯性
            coherence_analysis = self._analyze_intent_coherence(changes)
            changes["coherence_analysis"] = coherence_analysis
            
            # 预测可能的意图转换
            predicted_transitions = self._predict_intent_transitions(changes)
            changes["predicted_transitions"] = predicted_transitions
            
            # 计算整体意图变化评分
            overall_score = self._calculate_intent_change_score(changes)
            changes["overall_change_score"] = overall_score
        
        # 语义变化分析（基于关键词的语义相似度）
        semantic_changes = self._analyze_semantic_changes(old_content, new_content)
        if semantic_changes:
            changes["semantic_changes"] = semantic_changes
        
        return changes if changes else None
    
    def _detect_primary_intent_changes(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测主要的意图变化
        """
        primary_changes = {}
        
        # 定义意图转换的权重
        transition_weights = {
            "question_words": 1.0,
            "action_words": 1.2,
            "analysis_words": 0.8,
            "problem_words": 1.5,
            "solution_words": 1.3,
            "learning_words": 0.9,
            "confirmation_words": 0.7,
            "completion_words": 1.1,
            "refinement_words": 0.8
        }
        
        # 找出最显著的变化
        max_change_intensity = 0
        primary_change_type = None
        
        for change_type, change_data in changes.items():
            if change_type in transition_weights and isinstance(change_data, dict):
                weighted_intensity = change_data.get("change_intensity", 0) * transition_weights[change_type]
                if weighted_intensity > max_change_intensity:
                    max_change_intensity = weighted_intensity
                    primary_change_type = change_type
        
        if primary_change_type:
            primary_changes["primary_change_type"] = primary_change_type
            primary_changes["change_intensity"] = max_change_intensity
            primary_changes["change_direction"] = self._determine_change_direction(changes[primary_change_type])
        
        return primary_changes
    
    def _determine_change_direction(self, change_data: Dict[str, Any]) -> str:
        """
        确定意图变化的方向
        """
        added_count = change_data.get("added_count", 0)
        removed_count = change_data.get("removed_count", 0)
        
        if added_count > removed_count:
            return "addition_focused"
        elif removed_count > added_count:
            return "removal_focused"
        else:
            return "balanced"
    
    def _analyze_intent_coherence(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析意图变化的连贯性
        """
        # 定义连贯的意图转换模式
        coherent_patterns = [
            ("problem_words", "solution_words"),
            ("question_words", "action_words"),
            ("learning_words", "action_words"),
            ("analysis_words", "action_words"),
            ("action_words", "confirmation_words"),
            ("confirmation_words", "completion_words")
        ]
        
        coherence_score = 0
        coherent_transitions = []
        
        for pattern in coherent_patterns:
            if pattern[0] in changes and pattern[1] in changes:
                coherence_score += 1
                coherent_transitions.append({
                    "from": pattern[0],
                    "to": pattern[1],
                    "coherence_type": "natural_flow"
                })
        
        return {
            "coherence_score": coherence_score,
            "coherent_transitions": coherent_transitions,
            "overall_coherence": "high" if coherence_score >= 2 else "medium" if coherence_score >= 1 else "low"
        }
    
    def _predict_intent_transitions(self, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        预测可能的意图转换
        """
        predictions = []
        
        # 基于当前变化的预测规则
        if "problem_words" in changes:
            predictions.append({
                "predicted_intent": "solution_words",
                "probability": 0.8,
                "reason": "Problem statements typically lead to solution seeking"
            })
        
        if "question_words" in changes and "action_words" not in changes:
            predictions.append({
                "predicted_intent": "action_words",
                "probability": 0.7,
                "reason": "Questions often precede actions"
            })
        
        if "action_words" in changes and "confirmation_words" not in changes:
            predictions.append({
                "predicted_intent": "confirmation_words",
                "probability": 0.6,
                "reason": "Actions often require confirmation"
            })
        
        if "analysis_words" in changes:
            predictions.append({
                "predicted_intent": "action_words",
                "probability": 0.5,
                "reason": "Analysis typically leads to action"
            })
        
        return predictions
    
    def _calculate_intent_change_score(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算整体意图变化评分
        """
        total_changes = 0
        total_intensity = 0
        
        for change_type, change_data in changes.items():
            if isinstance(change_data, dict) and "change_intensity" in change_data:
                total_changes += 1
                total_intensity += change_data["change_intensity"]
        
        average_intensity = total_intensity / total_changes if total_changes > 0 else 0
        
        # 计算变化严重程度
        if average_intensity >= 5:
            severity = "major"
            score = 0.8
        elif average_intensity >= 3:
            severity = "moderate"
            score = 0.5
        elif average_intensity >= 1:
            severity = "minor"
            score = 0.3
        else:
            severity = "minimal"
            score = 0.1
        
        return {
            "overall_score": score,
            "severity": severity,
            "average_intensity": average_intensity,
            "total_change_types": total_changes
        }
    
    def _analyze_semantic_changes(self, old_content: str, new_content: str) -> Optional[Dict[str, Any]]:
        """
        分析语义变化（简化版本，基于关键词相似度）
        """
        old_words = set(old_content.lower().split())
        new_words = set(new_content.lower().split())
        
        # 计算词汇重叠度
        overlap = len(old_words & new_words)
        total_unique = len(old_words | new_words)
        
        if total_unique == 0:
            return None
        
        similarity = overlap / total_unique
        
        # 如果相似度太低，说明语义变化较大
        if similarity < 0.5:
            return {
                "semantic_similarity": similarity,
                "change_significance": "high",
                "vocabulary_overlap": overlap,
                "total_vocabulary": total_unique
            }
        
        return None

    def compute_intent_flow(
        self,
        structures: List[PromptStructure]
    ) -> Dict[str, Any]:
        """
        增强的意图流转分析，提供详细的IntentType流转分析
        
        Args:
            structures: List of PromptStructure objects in order
            
        Returns:
            详细的意图流转分析结果
        """
        if not structures or len(structures) < 2:
            return {
                "transition_matrix": {},
                "transition_patterns": {},
                "flow_statistics": {},
                "intent_sequences": [],
                "flow_analysis": {}
            }
        
        # 基础转换矩阵
        transition_matrix = {}
        
        # 增强的流转模式分析
        transition_patterns = {}
        
        # 意图序列
        intent_sequences = []
        
        # 详细的流转分析
        detailed_transitions = []
        
        for i in range(len(structures) - 1):
            current_structure = structures[i]
            next_structure = structures[i + 1]
            
            current_intent = current_structure.intent_analysis
            next_intent = next_structure.intent_analysis
            
            if current_intent and next_intent:
                from_intent = current_intent.primary_intent
                to_intent = next_intent.primary_intent
                
                # 更新基础转换矩阵
                if from_intent not in transition_matrix:
                    transition_matrix[from_intent] = {}
                
                if to_intent not in transition_matrix[from_intent]:
                    transition_matrix[from_intent][to_intent] = 0
                
                transition_matrix[from_intent][to_intent] += 1
                
                # 构建意图序列
                intent_sequences.append({
                    "turn_index": i,
                    "from_intent": from_intent.value,
                    "to_intent": to_intent.value,
                    "confidence_change": next_intent.intent_confidence - current_intent.intent_confidence,
                    "complexity_change": next_intent.complexity_score - current_intent.complexity_score
                })
                
                # 详细的转换分析
                transition_detail = self._analyze_transition_detail(
                    current_intent, next_intent, i
                )
                detailed_transitions.append(transition_detail)
                
                # 分析转换模式
                transition_type = self._classify_intent_transition(from_intent, to_intent)
                if transition_type not in transition_patterns:
                    transition_patterns[transition_type] = {
                        "count": 0,
                        "average_confidence_change": 0,
                        "average_complexity_change": 0,
                        "transitions": []
                    }
                
                pattern = transition_patterns[transition_type]
                pattern["count"] += 1
                pattern["transitions"].append({
                    "turn_index": i,
                    "confidence_change": next_intent.intent_confidence - current_intent.intent_confidence,
                    "complexity_change": next_intent.complexity_score - current_intent.complexity_score
                })
        
        # 计算模式统计
        for pattern_type, pattern_data in transition_patterns.items():
            if pattern_data["transitions"]:
                conf_changes = [t["confidence_change"] for t in pattern_data["transitions"]]
                comp_changes = [t["complexity_change"] for t in pattern_data["transitions"]]
                
                pattern_data["average_confidence_change"] = sum(conf_changes) / len(conf_changes)
                pattern_data["average_complexity_change"] = sum(comp_changes) / len(comp_changes)
                pattern_data["confidence_variance"] = self._calculate_variance(conf_changes)
                pattern_data["complexity_variance"] = self._calculate_variance(comp_changes)
        
        # 生成流转统计
        flow_statistics = self._generate_flow_statistics(
            transition_matrix, transition_patterns, intent_sequences
        )
        
        # 高级流转分析
        flow_analysis = self._analyze_intent_flow_patterns(
            structures, transition_matrix, intent_sequences
        )
        
        return {
            "transition_matrix": transition_matrix,
            "transition_patterns": transition_patterns,
            "flow_statistics": flow_statistics,
            "intent_sequences": intent_sequences,
            "flow_analysis": flow_analysis,
            "detailed_transitions": detailed_transitions
        }
    
    def _analyze_transition_detail(
        self,
        from_intent,
        to_intent,
        turn_index: int
    ) -> Dict[str, Any]:
        """
        分析单个转换的详细信息
        """
        transition_type = self._classify_intent_transition(
            from_intent.primary_intent, to_intent.primary_intent
        )
        
        # 分析转换的合理性
        is_natural = transition_type in [
            "inquiry_to_operation", "inquiry_to_creation",
            "operation_to_confirmation", "creation_to_confirmation",
            "confirmation_to_completion", "problem_to_analysis",
            "analysis_to_solution", "brainstorming_to_creation"
        ]
        
        # 分析IntentUnit的变化
        intent_units_diff = self._analyze_intent_units_diff(
            from_intent.intent_units, to_intent.intent_units
        )
        
        # 检测意图漂移
        intent_drift = self._detect_intent_drift(from_intent, to_intent)
        
        return {
            "turn_index": turn_index,
            "from_intent": from_intent.primary_intent.value,
            "to_intent": to_intent.primary_intent.value,
            "transition_type": transition_type,
            "is_natural": is_natural,
            "confidence_change": to_intent.intent_confidence - from_intent.intent_confidence,
            "complexity_change": to_intent.complexity_score - from_intent.complexity_score,
            "intent_units_change": intent_units_diff,
            "intent_drift": intent_drift,
            "transition_score": self._calculate_transition_score(
                from_intent, to_intent, is_natural
            )
        }
    
    def _generate_flow_statistics(
        self,
        transition_matrix: Dict,
        transition_patterns: Dict[str, Any],
        intent_sequences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成流转统计信息
        """
        total_transitions = sum(
            sum(targets.values()) for targets in transition_matrix.values()
        )
        
        # 计算每种意图类型的出现频率
        intent_frequency = {}
        for sequence in intent_sequences:
            from_intent = sequence["from_intent"]
            to_intent = sequence["to_intent"]
            
            intent_frequency[from_intent] = intent_frequency.get(from_intent, 0) + 1
            intent_frequency[to_intent] = intent_frequency.get(to_intent, 0) + 1
        
        # 找出最常见的转换
        most_common_transitions = []
        for from_intent, targets in transition_matrix.items():
            for to_intent, count in targets.items():
                most_common_transitions.append({
                    "from": from_intent.value,
                    "to": to_intent.value,
                    "count": count,
                    "percentage": count / total_transitions * 100 if total_transitions > 0 else 0
                })
        
        most_common_transitions.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total_transitions": total_transitions,
            "unique_transitions": len(most_common_transitions),
            "intent_frequency": intent_frequency,
            "most_common_transitions": most_common_transitions[:5],  # 前5个最常见的转换
            "transition_diversity": len(transition_patterns),
            "pattern_distribution": {
                pattern: data["count"] for pattern, data in transition_patterns.items()
            }
        }
    
    def _analyze_intent_flow_patterns(
        self,
        structures: List[PromptStructure],
        transition_matrix: Dict,
        intent_sequences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析高级意图流转模式
        """
        # 分析流转的稳定性
        confidence_stability = self._analyze_confidence_stability(intent_sequences)
        
        # 分析复杂度趋势
        complexity_trend = self._analyze_complexity_trend(intent_sequences)
        
        # 检测循环模式
        cycle_patterns = self._detect_cycle_patterns(intent_sequences)
        
        # 分析会话收敛性
        convergence_analysis = self._analyze_convergence(structures, intent_sequences)
        
        return {
            "confidence_stability": confidence_stability,
            "complexity_trend": complexity_trend,
            "cycle_patterns": cycle_patterns,
            "convergence_analysis": convergence_analysis,
            "flow_quality_score": self._calculate_flow_quality_score(
                confidence_stability, complexity_trend, cycle_patterns
            )
        }
    
    def _analyze_confidence_stability(self, intent_sequences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析置信度稳定性
        """
        if not intent_sequences:
            return {"stability_score": 0, "trend": "stable", "variance": 0}
        
        confidence_changes = [seq["confidence_change"] for seq in intent_sequences]
        
        # 计算方差
        variance = self._calculate_variance(confidence_changes)
        
        # 计算趋势
        avg_change = sum(confidence_changes) / len(confidence_changes)
        
        if abs(avg_change) < 0.05:
            trend = "stable"
        elif avg_change > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # 稳定性评分（方差越小越稳定）
        stability_score = max(0, 1 - variance / 0.5)  # 假设最大方差为0.5
        
        return {
            "stability_score": round(stability_score, 3),
            "trend": trend,
            "average_change": avg_change,
            "variance": variance
        }
    
    def _analyze_complexity_trend(self, intent_sequences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析复杂度趋势
        """
        if not intent_sequences:
            return {"trend": "stable", "average_change": 0, "complexity_evolution": []}
        
        complexity_changes = [seq["complexity_change"] for seq in intent_sequences]
        avg_change = sum(complexity_changes) / len(complexity_changes)
        
        if abs(avg_change) < 0.5:
            trend = "stable"
        elif avg_change > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # 复杂度演化路径
        complexity_evolution = []
        current_complexity = 0
        for i, change in enumerate(complexity_changes):
            current_complexity += change
            complexity_evolution.append({
                "step": i,
                "complexity": current_complexity,
                "change": change
            })
        
        return {
            "trend": trend,
            "average_change": avg_change,
            "complexity_evolution": complexity_evolution
        }
    
    def _detect_cycle_patterns(self, intent_sequences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测循环模式
        """
        cycles = []
        
        # 简单的2步和3步循环检测
        for i in range(len(intent_sequences) - 1):
            current_transition = (intent_sequences[i]["from_intent"], intent_sequences[i]["to_intent"])
            
            # 检测2步循环 (A->B->A)
            if i < len(intent_sequences) - 1:
                next_transition = (intent_sequences[i + 1]["from_intent"], intent_sequences[i + 1]["to_intent"])
                if current_transition[1] == next_transition[0] and current_transition[0] == next_transition[1]:
                    cycles.append({
                        "type": "2_step_cycle",
                        "pattern": f"{current_transition[0]}->{current_transition[1]}->{current_transition[0]}",
                        "start_index": i,
                        "length": 2
                    })
        
        return cycles
    
    def _analyze_convergence(
        self,
        structures: List[PromptStructure],
        intent_sequences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析会话收敛性
        """
        if len(intent_sequences) < 3:
            return {"has_convergence": False, "convergence_point": None}
        
        # 检测意图是否趋向稳定
        recent_intents = [seq["to_intent"] for seq in intent_sequences[-3:]]
        
        # 如果最近3个轮次的意图相同，认为出现收敛
        if len(set(recent_intents)) == 1:
            return {
                "has_convergence": True,
                "convergence_intent": recent_intents[0],
                "convergence_point": len(intent_sequences) - 3,
                "stability_duration": 3
            }
        
        return {"has_convergence": False, "convergence_point": None}
    
    def _calculate_flow_quality_score(
        self,
        confidence_stability: Dict[str, Any],
        complexity_trend: Dict[str, Any],
        cycle_patterns: List[Dict[str, Any]]
    ) -> float:
        """
        计算流转质量评分
        """
        # 置信度稳定性权重
        confidence_score = confidence_stability.get("stability_score", 0)
        
        # 复杂度趋势权重（稳定或适度增加为好评分）
        complexity_score = 1.0 if complexity_trend["trend"] == "stable" else 0.7 if complexity_trend["trend"] == "increasing" else 0.4
        
        # 循环模式惩罚（循环通常不是好的流转模式）
        cycle_penalty = len(cycle_patterns) * 0.1
        
        # 综合评分
        quality_score = (confidence_score * 0.5 + complexity_score * 0.3 - cycle_penalty)
        
        return max(0, min(1, quality_score))
    
    def _calculate_variance(self, values: List[float]) -> float:
        """
        计算方差
        """
        if not values:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance
    
    def _detect_intent_context_shift(
        self,
        from_intent,
        to_intent
    ) -> Dict[str, Any]:
        """
        检测意图上下文转移
        """
        # 分析上下文依赖的变化
        from_context_deps = set(from_intent.context_references or [])
        to_context_deps = set(to_intent.context_references or [])
        
        added_contexts = to_context_deps - from_context_deps
        removed_contexts = from_context_deps - to_context_deps
        
        # 分析关键词的变化
        from_keywords = set()
        to_keywords = set()
        
        for unit in from_intent.intent_units:
            from_keywords.update(unit.keywords or [])
        
        for unit in to_intent.intent_units:
            to_keywords.update(unit.keywords or [])
        
        keyword_overlap = len(from_keywords & to_keywords) / max(1, len(from_keywords | to_keywords))
        
        # 检测主题漂移
        theme_shift_score = 1 - keyword_overlap
        
        return {
            "theme_shift_score": round(theme_shift_score, 3),
            "keyword_overlap": round(keyword_overlap, 3),
            "context_changes": {
                "added": list(added_contexts),
                "removed": list(removed_contexts),
                "preserved": list(from_context_deps & to_context_deps)
            },
            "has_significant_shift": theme_shift_score > 0.7
        }
    
    def _analyze_intent_coherence(
        self,
        intent_sequence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析意图序列的连贯性
        """
        if len(intent_sequence) < 2:
            return {"coherence_score": 1.0, "coherence_pattern": "single"}
        
        # 计算相邻意图之间的相似度
        coherence_scores = []
        coherence_patterns = []
        
        for i in range(len(intent_sequence) - 1):
            current = intent_sequence[i]
            next_intent = intent_sequence[i + 1]
            
            # 基于意图类型判断连贯性
            coherence_score = self._calculate_intent_similarity(current, next_intent)
            coherence_scores.append(coherence_score)
            
            # 识别连贯性模式
            pattern = self._identify_coherence_pattern(current, next_intent)
            coherence_patterns.append(pattern)
        
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 1.0
        
        # 统计模式分布
        pattern_counts = {}
        for pattern in coherence_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        return {
            "coherence_score": round(avg_coherence, 3),
            "coherence_pattern": max(pattern_counts, key=pattern_counts.get) if pattern_counts else "unknown",
            "pattern_distribution": pattern_counts,
            "coherence_trend": self._analyze_coherence_trend(coherence_scores)
        }
    
    def _calculate_intent_similarity(
        self,
        current_intent: Dict[str, Any],
        next_intent: Dict[str, Any]
    ) -> float:
        """
        计算两个意图之间的相似度
        """
        # 基于意图类型的相似度
        intent_similarity = 1.0 if current_intent["to_intent"] == next_intent["from_intent"] else 0.3
        
        # 基于复杂度变化的相似度（变化越小越相似）
        complexity_diff = abs(current_intent["complexity_change"] - next_intent.get("complexity_change", 0))
        complexity_similarity = max(0, 1 - complexity_diff / 5.0)
        
        # 基于置信度变化的相似度
        confidence_diff = abs(current_intent["confidence_change"] - next_intent.get("confidence_change", 0))
        confidence_similarity = max(0, 1 - confidence_diff / 0.5)
        
        # 综合相似度
        total_similarity = (
            intent_similarity * 0.5 +
            complexity_similarity * 0.3 +
            confidence_similarity * 0.2
        )
        
        return total_similarity
    
    def _identify_coherence_pattern(
        self,
        current_intent: Dict[str, Any],
        next_intent: Dict[str, Any]
    ) -> str:
        """
        识别连贯性模式
        """
        current_type = current_intent["to_intent"]
        next_type = next_intent["from_intent"]
        
        # 定义连贯性模式规则
        if current_type == next_type:
            return "continuation"
        elif current_type == "inquiry" and next_type == "operation":
            return "inquiry_to_action"
        elif current_type == "operation" and next_type == "confirmation":
            return "action_to_confirmation"
        elif current_type == "creation" and next_type == "refinement":
            return "creation_to_refinement"
        elif current_type == "problem" and next_type == "analysis":
            return "problem_to_analysis"
        elif current_type == "analysis" and next_type == "solution":
            return "analysis_to_solution"
        else:
            return "transition"
    
    def _analyze_coherence_trend(self, coherence_scores: List[float]) -> str:
        """
        分析连贯性趋势
        """
        if len(coherence_scores) < 2:
            return "stable"
        
        # 计算趋势
        first_half = coherence_scores[:len(coherence_scores)//2]
        second_half = coherence_scores[len(coherence_scores)//2:]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        
        if abs(second_avg - first_avg) < 0.1:
            return "stable"
        elif second_avg > first_avg:
            return "improving"
        else:
            return "declining"
    
    def _predict_next_intent(
        self,
        intent_history: List[Dict[str, Any]],
        transition_matrix: Dict
    ) -> Dict[str, Any]:
        """
        基于历史意图预测下一个意图
        """
        if not intent_history:
            return {"predicted_intent": "unknown", "confidence": 0.0}
        
        # 获取最近的意图
        current_intent = intent_history[-1]["to_intent"]
        
        # 从转换矩阵中获取可能的下一个意图
        if current_intent in transition_matrix:
            possible_transitions = transition_matrix[current_intent]
            
            # 选择最可能的转换
            best_transition = max(possible_transitions.items(), key=lambda x: x[1])
            
            # 计算置信度（基于历史频率）
            total_transitions = sum(possible_transitions.values())
            confidence = best_transition[1] / total_transitions if total_transitions > 0 else 0
            
            return {
                "predicted_intent": best_transition[0],
                "confidence": round(confidence, 3),
                "alternatives": [
                    {"intent": intent, "probability": count/total_transitions}
                    for intent, count in sorted(possible_transitions.items(), key=lambda x: x[1], reverse=True)[:3]
                ]
            }
        
        return {"predicted_intent": "unknown", "confidence": 0.0}
    
    def _analyze_intent_stability(
        self,
        intent_sequence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析意图稳定性
        """
        if not intent_sequence:
            return {"stability_score": 0, "volatility": 0, "dominant_intent": None}
        
        # 统计意图类型分布
        intent_counts = {}
        for seq in intent_sequence:
            intent = seq["to_intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # 计算稳定性评分（最频繁的意图占比）
        total_sequences = len(intent_sequence)
        max_count = max(intent_counts.values()) if intent_counts else 0
        stability_score = max_count / total_sequences if total_sequences > 0 else 0
        
        # 计算波动性（意图变化的频率）
        changes = 0
        for i in range(len(intent_sequence) - 1):
            if intent_sequence[i]["to_intent"] != intent_sequence[i + 1]["from_intent"]:
                changes += 1
        
        volatility = changes / (len(intent_sequence) - 1) if len(intent_sequence) > 1 else 0
        
        # 找出主导意图
        dominant_intent = max(intent_counts, key=intent_counts.get) if intent_counts else None
        
        return {
            "stability_score": round(stability_score, 3),
            "volatility": round(volatility, 3),
            "dominant_intent": dominant_intent,
            "intent_distribution": intent_counts,
            "stability_trend": self._analyze_stability_trend(intent_sequence)
        }
    
    def _analyze_stability_trend(self, intent_sequence: List[Dict[str, Any]]) -> str:
        """
        分析稳定性趋势
        """
        if len(intent_sequence) < 3:
            return "insufficient_data"
        
        # 将序列分成前后两半
        mid_point = len(intent_sequence) // 2
        first_half = intent_sequence[:mid_point]
        second_half = intent_sequence[mid_point:]
        
        # 计算前半部分的稳定性
        first_stability = self._calculate_sequence_stability(first_half)
        second_stability = self._calculate_sequence_stability(second_half)
        
        if abs(second_stability - first_stability) < 0.1:
            return "stable"
        elif second_stability > first_stability:
            return "stabilizing"
        else:
            return "destabilizing"
    
    def _calculate_sequence_stability(self, sequence: List[Dict[str, Any]]) -> float:
        """
        计算序列稳定性
        """
        if not sequence:
            return 0
        
        # 统计最频繁意图的出现次数
        intent_counts = {}
        for seq in sequence:
            intent = seq["to_intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        max_count = max(intent_counts.values()) if intent_counts else 0
        return max_count / len(sequence) if sequence else 0

    def analyze_intent_patterns(
        self,
        structures: List[PromptStructure]
    ) -> Dict[str, Any]:
        """
        分析意图模式
        
        Args:
            structures: List of PromptStructure objects
            
        Returns:
            意图模式分析结果
        """
        intent_counts = {}
        complexity_scores = []
        confidence_scores = []
        
        for structure in structures:
            if structure.intent_analysis:
                intent_type = structure.intent_analysis.primary_intent
                intent_counts[intent_type] = intent_counts.get(intent_type, 0) + 1
                complexity_scores.append(structure.intent_analysis.complexity_score)
                confidence_scores.append(structure.intent_analysis.intent_confidence)
        
        analysis = {
            "intent_distribution": intent_counts,
            "most_common_intent": max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else None,
            "intent_diversity": len(intent_counts) / len(IntentType) if IntentType else 0,
            "average_complexity": sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0,
            "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "total_intent_changes": len(structures) - 1  # 相邻轮次间的变化数
        }
        
        # 计算意图流转矩阵
        analysis["intent_transitions"] = self.compute_intent_flow(structures)
        
        return analysis

    def _find_modified_components(
        self,
        from_structure: PromptStructure,
        to_structure: PromptStructure
    ) -> List[Dict]:
        """
        找出修改的组件

        Strategy: For each component type, compare old vs new versions.
        If type exists in both but content differs, it's modified.
        """
        modified = []

        # Group components by type
        from_by_type = self._group_by_type(from_structure.components)
        to_by_type = self._group_by_type(to_structure.components)

        # Check each type
        for comp_type in PromptComponentType:
            from_comps = from_by_type.get(comp_type, [])
            to_comps = to_by_type.get(comp_type, [])

            # Special handling for different component types
            if comp_type == PromptComponentType.SYSTEM:
                # System prompt should be unique, compare directly
                if from_comps and to_comps:
                    from_comp = from_comps[0]
                    to_comp = to_comps[0]
                    if from_comp.content != to_comp.content:
                        changes = self._compute_text_diff(
                            from_comp.content,
                            to_comp.content
                        )
                        modified.append({
                            "old": from_comp,
                            "new": to_comp,
                            "changes": changes
                        })

            elif comp_type == PromptComponentType.TOOLS:
                # Tools definition, compare as string
                if from_comps and to_comps:
                    from_comp = from_comps[0]
                    to_comp = to_comps[0]
                    if from_comp.content != to_comp.content:
                        modified.append({
                            "old": from_comp,
                            "new": to_comp,
                            "changes": [{"type": "modified", "summary": "Tools definition changed"}]
                        })

            # For HISTORY and NEW_INPUT, they're typically new each turn
            # so we don't mark them as "modified"

        return modified

    def _group_by_type(
        self,
        components: List[PromptComponent]
    ) -> Dict[PromptComponentType, List[PromptComponent]]:
        """按类型分组组件"""
        groups = {}
        for comp in components:
            comp_type = comp.type
            if comp_type not in groups:
                groups[comp_type] = []
            groups[comp_type].append(comp)
        return groups

    def _compute_text_diff(
        self,
        old_text: str,
        new_text: str
    ) -> List[Dict]:
        """
        计算文本级别的差异

        Returns a list of changes with type (added/removed/modified).
        """
        differ = difflib.Differ()
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff = list(differ.compare(old_lines, new_lines))

        changes = []
        for line in diff:
            if line.startswith('+ '):
                changes.append({
                    "type": "added",
                    "content": line[2:].rstrip('\n')
                })
            elif line.startswith('- '):
                changes.append({
                    "type": "removed",
                    "content": line[2:].rstrip('\n')
                })
            elif line.startswith('? '):
                # Marker line, skip
                continue

        return changes

    def compute_all_diffs(
        self,
        structures: List[PromptStructure]
    ) -> List[TurnDiff]:
        """
        计算所有相邻 turns 之间的差异

        Args:
            structures: List of PromptStructure objects in order

        Returns:
            List of TurnDiff objects
        """
        diffs = []

        for i in range(1, len(structures)):
            prev = structures[i - 1]
            curr = structures[i]
            diff = self.compute_diff(prev, curr)
            diffs.append(diff)

        return diffs
