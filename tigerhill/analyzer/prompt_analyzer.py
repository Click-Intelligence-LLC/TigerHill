"""
Prompt Structure Analyzer

Analyzes captured LLM interaction data to extract prompt components,
identify repeated content, and compute token statistics.
"""
import re
from typing import List, Dict, Optional, Any
from tigerhill.analyzer.models import (
    PromptStructure,
    PromptComponent,
    PromptComponentType,
    IntentType,
    IntentUnit,
    TurnIntentAnalysis
)


class IntentClassifier:
    """意图分类器 - 分析用户输入的意图类型"""
    
    def __init__(self):
        # 定义关键词模式来识别不同的意图类型
        self.intent_patterns = {
            IntentType.INFORMATION_SEEKING: [
                r'什么|怎么|如何|为什么|哪里|谁|何时',
                r'explain|describe|what|how|why|where|who|when',
                r'定义|含义|意思|解释|说明'
            ],
            IntentType.TASK_EXECUTION: [
                r'执行|运行|调用|创建|生成|计算|处理',
                r'execute|run|call|create|generate|calculate|process',
                r'请做|帮我|完成|实现'
            ],
            IntentType.CREATIVE_GENERATION: [
                r'写|创作|设计|想象|构思|故事|诗歌|代码',
                r'write|create|design|imagine|story|poem|code',
                r'创意|创新|新颖|独特'
            ],
            IntentType.ANALYSIS_REQUEST: [
                r'分析|比较|评估|检查|审查|总结',
                r'analyze|compare|evaluate|check|review|summarize',
                r'优缺点|好坏|对比|差异'
            ],
            IntentType.CLARIFICATION: [
                r'澄清|确认|明确|详细|具体',
                r'clarify|confirm|specify|detail|specific',
                r'你是说|你的意思是|换句话说'
            ],
            IntentType.FOLLOW_UP: [
                r'继续|接着|还有|另外|补充',
                r'continue|furthermore|additionally|moreover',
                r'然后呢|接下来|之后'
            ],
            IntentType.CONTEXT_SETTING: [
                r'假设|设定|背景|上下文|环境',
                r'assume|context|background|setting|environment',
                r'在这种情况下|给定'
            ],
            IntentType.REFINEMENT: [
                r'改进|优化|完善|调整|修改|修正',
                r'improve|optimize|refine|adjust|modify|correct',
                r'更好|更准确|更详细'
            ],
            IntentType.VALIDATION: [
                r'验证|检查|测试|确认|正确|错误',
                r'validate|check|test|verify|correct|error',
                r'对不对|是否正确|有问题吗'
            ],
            IntentType.EXPLORATION: [
                r'探索|研究|调查|发现|了解',
                r'explore|research|investigate|discover|learn',
                r'可能性|选择|方案'
            ]
        }
    
    def classify_intent(self, text: str, context: Optional[Dict[str, Any]] = None) -> tuple[IntentType, float]:
        """
        对文本进行意图分类，支持上下文依赖分析
        
        Args:
            text: 要分类的文本
            context: 可选的上下文信息，包含历史意图、会话状态等
            
        Returns:
            (意图类型, 置信度) 元组
        """
        if not text or not text.strip():
            return IntentType.INFORMATION_SEEKING, 0.0
        
        text_lower = text.lower().strip()
        intent_scores = {}
        
        # 为每种意图类型计算匹配分数
        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                score += len(matches) * self._get_pattern_weight(pattern, intent_type)
            intent_scores[intent_type] = score
        
        # 上下文增强分析
        context_bonus = self._apply_context_bonus(text_lower, context, intent_scores)
        for intent_type, bonus in context_bonus.items():
            intent_scores[intent_type] += bonus
        
        # 处理上下文依赖的特殊情况
        if self._has_context_dependency(text_lower):
            # 如果文本显示对之前内容的依赖，调整意图分类
            intent_scores = self._adjust_for_context_dependency(intent_scores, context)
        
        # 找到最高分的意图类型
        if not intent_scores or max(intent_scores.values()) == 0:
            # 如果没有明确的模式匹配，使用默认意图但提高置信度
            return IntentType.INFORMATION_SEEKING, 0.5
        
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        confidence = self._calculate_confidence(best_intent[1], intent_scores, context)
        
        return best_intent[0], confidence
    
    def _get_pattern_weight(self, pattern: str, intent_type: IntentType) -> float:
        """获取模式匹配的权重"""
        # 中文模式通常更具体，给予更高权重
        if any('\u4e00' <= char <= '\u9fff' for char in pattern):
            return 1.5
        return 1.0
    
    def _apply_context_bonus(self, text: str, context: Optional[Dict[str, Any]], intent_scores: Dict[IntentType, float]) -> Dict[IntentType, float]:
        """应用上下文增强的奖励分数"""
        bonuses = {intent_type: 0.0 for intent_type in IntentType}
        
        if not context:
            return bonuses
        
        # 历史意图连续性奖励
        previous_intents = context.get('previous_intents', [])
        if previous_intents:
            last_intent = previous_intents[-1]
            # 如果当前意图与上一个意图相似，给予奖励
            for intent_type in intent_scores:
                if intent_type == last_intent:
                    bonuses[intent_type] += 0.5
        
        # 会话阶段奖励
        turn_index = context.get('turn_index', 1)
        total_turns = context.get('total_turns', 1)
        
        if turn_index > 1:
            # 后续轮次更可能是澄清、细化或继续
            if self._is_follow_up_intent(text):
                bonuses[IntentType.CLARIFICATION] += 0.3
                bonuses[IntentType.FOLLOW_UP] += 0.3
                bonuses[IntentType.REFINEMENT] += 0.2
        
        # 任务执行链奖励
        if self._is_task_execution_chain(previous_intents):
            bonuses[IntentType.TASK_EXECUTION] += 0.4
            bonuses[IntentType.REFINEMENT] += 0.3
        
        return bonuses
    
    def _has_context_dependency(self, text: str) -> bool:
        """检测文本是否显示对之前内容的依赖"""
        dependency_patterns = [
            r'[这那]个', r'[它它们她他]', r'上述', r'之前', r'刚才', r'上[一]?轮',
            r'continue', r'follow.*up', r'as.*mentioned', r'as.*discussed',
            r'在此基础上', r'接着', r'然后', r'接下来'
        ]
        
        for pattern in dependency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _is_follow_up_intent(self, text: str) -> bool:
        """判断是否为跟进意图"""
        follow_up_patterns = [
            r'还[有要]', r'另外', r'补充', r'修正', r'改[进善]', r'优化',
            r'continue', r'further', r'additionally', r'moreover', r'also',
            r'但是', r'不过', r'然而', r'可是'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in follow_up_patterns)
    
    def _is_task_execution_chain(self, previous_intents: List[IntentType]) -> bool:
        """判断是否处于任务执行链中"""
        if len(previous_intents) < 2:
            return False
        
        # 检查最近几轮是否主要是任务执行相关
        recent_intents = previous_intents[-3:]  # 最近3轮
        task_related = [IntentType.TASK_EXECUTION, IntentType.REFINEMENT, IntentType.CREATIVE_GENERATION]
        
        task_count = sum(1 for intent in recent_intents if intent in task_related)
        return task_count >= len(recent_intents) * 0.6
    
    def _adjust_for_context_dependency(self, intent_scores: Dict[IntentType, float], context: Optional[Dict[str, Any]]) -> Dict[IntentType, float]:
        """根据上下文依赖调整意图分数"""
        adjusted_scores = intent_scores.copy()
        
        if not context:
            return adjusted_scores
        
        previous_intents = context.get('previous_intents', [])
        if not previous_intents:
            return adjusted_scores
        
        last_intent = previous_intents[-1]
        
        # 根据上一个意图调整当前意图的可能性
        intent_transitions = {
            IntentType.INFORMATION_SEEKING: [IntentType.TASK_EXECUTION, IntentType.ANALYSIS_REQUEST, IntentType.CLARIFICATION],
            IntentType.TASK_EXECUTION: [IntentType.REFINEMENT, IntentType.VALIDATION, IntentType.CLARIFICATION, IntentType.FOLLOW_UP],
            IntentType.CREATIVE_GENERATION: [IntentType.REFINEMENT, IntentType.FOLLOW_UP, IntentType.CLARIFICATION],
            IntentType.ANALYSIS_REQUEST: [IntentType.CLARIFICATION, IntentType.FOLLOW_UP, IntentType.REFINEMENT]
        }
        
        if last_intent in intent_transitions:
            likely_next = intent_transitions[last_intent]
            for intent_type in adjusted_scores:
                if intent_type in likely_next:
                    adjusted_scores[intent_type] *= 1.3  # 提升可能性
        
        return adjusted_scores
    
    def _calculate_confidence(self, best_score: float, all_scores: Dict[IntentType, float], context: Optional[Dict[str, Any]]) -> float:
        """计算置信度分数"""
        if best_score <= 0:
            return 0.3
        
        # 基础置信度
        base_confidence = min(0.9, 0.4 + best_score * 0.1)
        
        # 分数分布分析
        sorted_scores = sorted(all_scores.values(), reverse=True)
        if len(sorted_scores) >= 2:
            score_gap = sorted_scores[0] - sorted_scores[1]
            # 分数差距越大，置信度越高
            confidence_boost = min(0.2, score_gap * 0.05)
            base_confidence += confidence_boost
        
        # 上下文一致性奖励
        if context and context.get('previous_intents'):
            consistency_bonus = self._calculate_consistency_bonus(all_scores, context['previous_intents'])
            base_confidence += consistency_bonus
        
        return min(1.0, base_confidence)
    
    def _calculate_consistency_bonus(self, current_scores: Dict[IntentType, float], previous_intents: List[IntentType]) -> float:
        """计算上下文一致性奖励"""
        if not previous_intents:
            return 0.0
        
        # 检查当前最高分意图是否与历史意图一致
        best_current = max(current_scores.items(), key=lambda x: x[1])
        if best_current[0] in previous_intents[-2:]:  # 最近两轮
            return 0.1
        
        # 检查意图转换是否合理
        if len(previous_intents) >= 2:
            last_intent = previous_intents[-1]
            second_last = previous_intents[-2]
            
            # 常见的合理转换模式
            reasonable_transitions = [
                (IntentType.INFORMATION_SEEKING, IntentType.TASK_EXECUTION),
                (IntentType.TASK_EXECUTION, IntentType.REFINEMENT),
                (IntentType.CREATIVE_GENERATION, IntentType.REFINEMENT),
                (IntentType.ANALYSIS_REQUEST, IntentType.CLARIFICATION)
            ]
            
            if (second_last, best_current[0]) in reasonable_transitions:
                return 0.05
        
        return 0.0
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取 - 可以替换为更复杂的NLP方法
        words = re.findall(r'\b\w+\b', text.lower())
        # 过滤掉常见停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return keywords[:10]  # 返回前10个关键词


class PromptAnalyzer:
    """Prompt 结构分析器"""

    def __init__(self, model_name: str = "gemini-pro"):
        """
        Initialize the analyzer.

        Args:
            model_name: Model name for token counting (e.g., "gemini-pro", "gpt-4")
        """
        self.model_name = model_name
        self.encoder = None
        self.intent_classifier = IntentClassifier()

        # Try to import tiktoken for accurate token counting
        try:
            import tiktoken
            # Map model names to tiktoken encodings
            if "gpt" in model_name.lower():
                self.encoder = tiktoken.encoding_for_model(model_name)
            elif "gemini" in model_name.lower():
                # Gemini uses similar tokenization to GPT-3.5
                self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except ImportError:
            # Fall back to simple estimation
            pass

    def analyze_turn(
        self,
        turn_data: Dict[str, Any],
        turn_index: int,
        previous_structure: Optional[PromptStructure] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PromptStructure:
        """
        分析单个 turn 的 prompt 结构

        Args:
            turn_data: 原始 turn 数据（从 capture JSON）
            turn_index: 轮次索引（从 1 开始）
            previous_structure: 上一轮的结构（用于 diff）

        Returns:
            PromptStructure 对象
        """
        components = []

        # 1. 提取请求数据
        requests = turn_data.get("requests", [])
        if not requests:
            # Empty turn, return empty structure
            return PromptStructure(
                turn_index=turn_index,
                total_tokens=0,
                components=[],
                stats={}
            )

        # Gemini CLI may have multiple requests per turn
        # Find the actual generateContent request (not metadata requests)
        main_request = None
        for req in requests:
            url = req.get("url", "")
            # Look for generateContent or streamGenerateContent requests
            if "generateContent" in url:
                # Prefer requests with contents field
                if "contents" in req:
                    main_request = req
                    break

        # Fallback to first request with contents
        if not main_request:
            for req in requests:
                if "contents" in req:
                    main_request = req
                    break

        # If still no request found, use first request
        if not main_request:
            main_request = requests[0]

        contents = main_request.get("contents", [])

        # 2. 分析 system prompt
        system_parts = self._extract_system_prompt(contents, turn_data)
        if system_parts:
            comp = PromptComponent(
                type=PromptComponentType.SYSTEM,
                content=system_parts,
                tokens=self._count_tokens(system_parts),
                role="system"
            )

            # 检查是否重复
            if previous_structure:
                comp.is_repeated = self._is_component_repeated(
                    comp, previous_structure, PromptComponentType.SYSTEM
                )
                if comp.is_repeated:
                    # Find first occurrence
                    comp.first_seen_turn = 1
                else:
                    comp.first_seen_turn = turn_index

            components.append(comp)

        # 3. 分析历史对话
        history_components = self._extract_history(contents, turn_index, turn_data)
        components.extend(history_components)

        # 4. 分析新用户输入
        new_input = self._extract_new_input(contents, turn_data)
        if new_input:
            components.append(PromptComponent(
                type=PromptComponentType.NEW_USER_INPUT,
                content=new_input,
                tokens=self._count_tokens(new_input),
                role="user",
                is_repeated=False,
                first_seen_turn=turn_index
            ))

        # 5. 分析工具定义（如果有）
        tools = self._extract_tools(main_request)
        if tools:
            tools_str = str(tools)
            comp = PromptComponent(
                type=PromptComponentType.TOOLS,
                content=tools_str,
                tokens=self._count_tokens(tools_str)
            )

            # Check if tools are repeated
            if previous_structure:
                comp.is_repeated = self._is_component_repeated(
                    comp, previous_structure, PromptComponentType.TOOLS
                )

            components.append(comp)

        # 6. 进行意图分析（传入上下文）
        intent_analysis = self._analyze_intents(new_input, turn_index, turn_data, context)

        # 7. 计算统计信息
        total_tokens = sum(c.tokens for c in components)
        repeated_tokens = sum(c.tokens for c in components if c.is_repeated)

        stats = {
            "system_tokens": sum(
                c.tokens for c in components
                if c.type == PromptComponentType.SYSTEM
            ),
            "history_tokens": sum(
                c.tokens for c in components
                if c.type == PromptComponentType.HISTORY
            ),
            "new_tokens": sum(
                c.tokens for c in components
                if c.type == PromptComponentType.NEW_USER_INPUT
            ),
            "tools_tokens": sum(
                c.tokens for c in components
                if c.type == PromptComponentType.TOOLS
            ),
            "repeated_ratio": repeated_tokens / total_tokens if total_tokens > 0 else 0,
            "unique_tokens": total_tokens - repeated_tokens
        }

        return PromptStructure(
            turn_index=turn_index,
            total_tokens=total_tokens,
            components=components,
            stats=stats,
            intent_analysis=intent_analysis
        )
    
    def _build_intent_context(self, turn_data: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建意图分析的上下文信息"""
        context = {
            'turn_index': turn_data.get('turn_index', 1),
            'total_turns': turn_data.get('total_turns', 1),
            'session_id': turn_data.get('session_id', 'unknown')
        }
        
        # 从历史中提取之前的意图信息
        previous_intents = []
        for item in history:
            if item.get('role') == 'user' and 'intent_analysis' in item:
                # 如果历史项中包含意图分析，提取意图类型
                intent_data = item['intent_analysis']
                if isinstance(intent_data, dict) and 'primary_intent' in intent_data:
                    try:
                        intent_type = IntentType(intent_data['primary_intent']['intent_type'])
                        previous_intents.append(intent_type)
                    except (ValueError, KeyError):
                        continue
        
        context['previous_intents'] = previous_intents
        
        # 添加会话状态信息
        context['has_tools'] = bool(self._extract_tools(turn_data))
        context['is_multilingual'] = self._detect_multilingual_context(history)
        
        return context
    
    def _detect_multilingual_context(self, history: List[Dict[str, Any]]) -> bool:
        """检测是否为多语言上下文"""
        if not history:
            return False
        
        # 简单的多语言检测：检查是否有中英文混合
        has_chinese = any(re.search(r'[\u4e00-\u9fff]', item.get('content', '')) for item in history[-3:])
        has_english = any(re.search(r'[a-zA-Z]{3,}', item.get('content', '')) for item in history[-3:])
        
        return has_chinese and has_english

    def _analyze_intents(
        self, 
        user_input: Optional[str], 
        turn_index: int, 
        turn_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[TurnIntentAnalysis]:
        """
        分析用户输入的意图
        
        Args:
            user_input: 用户输入文本
            turn_index: 轮次索引
            turn_data: 完整的轮次数据
            
        Returns:
            TurnIntentAnalysis 对象或 None
        """
        if not user_input or not user_input.strip():
            return None
        
        # 提取上下文引用
        context_references = self._extract_context_references(user_input, turn_index)
        
        # 进行意图分类
        primary_intent, confidence = self.intent_classifier.classify_intent(user_input)
        
        # 提取关键词
        keywords = self.intent_classifier.extract_keywords(user_input)
        
        # 创建意图单元
        intent_unit = IntentUnit(
            intent_type=primary_intent,
            content=user_input,
            confidence=confidence,
            tokens=self._count_tokens(user_input),
            keywords=keywords,
            context_dependencies=context_references,
            metadata={
                "turn_index": turn_index,
                "classification_method": "rule_based",
                "input_length": len(user_input)
            }
        )
        
        # 计算复杂度分数
        complexity_score = self._calculate_complexity_score(user_input, keywords, context_references)
        
        return TurnIntentAnalysis(
            turn_index=turn_index,
            intent_units=[intent_unit],
            primary_intent=primary_intent,
            intent_confidence=confidence,
            context_references=[ref for ref in context_references if ref.isdigit()],
            complexity_score=complexity_score
        )

    def _extract_context_references(self, text: str, current_turn: int) -> List[str]:
        """
        提取文本中对之前轮次的引用
        
        Args:
            text: 用户输入文本
            current_turn: 当前轮次索引
            
        Returns:
            上下文引用列表
        """
        references = []
        
        # 匹配对之前轮次的引用（如"上一轮"、"刚才"、"之前说"等）
        context_patterns = [
            r'上[一]?轮[次]?',
            r'刚才',
            r'之前[说讲]的?',
            r'上[一]?次',
            r'前面',
            r'之前'
        ]
        
        for pattern in context_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 如果有对上下文的引用，假设引用的是上一轮
                if current_turn > 1:
                    references.append(str(current_turn - 1))
                break
        
        # 匹配具体的轮次引用（如"第3轮"、"turn 5"等）
        turn_patterns = [
            r'第(\d+)[轮次个]?',
            r'turn\s+(\d+)',
            r'round\s+(\d+)'
        ]
        
        for pattern in turn_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                try:
                    turn_num = int(match)
                    if 1 <= turn_num < current_turn:
                        references.append(str(turn_num))
                except ValueError:
                    continue
        
        return list(set(references))  # 去重

    def _calculate_complexity_score(self, text: str, keywords: List[str], context_references: List[str]) -> float:
        """
        计算输入文本的复杂度分数
        
        Args:
            text: 输入文本
            keywords: 提取的关键词
            context_references: 上下文引用
            
        Returns:
            0-1 范围的复杂度分数
        """
        if not text:
            return 0.0
        
        # 基础复杂度指标
        text_length = len(text)
        word_count = len(text.split())
        
        # 关键词密度
        keyword_density = len(keywords) / word_count if word_count > 0 else 0
        
        # 上下文依赖复杂度
        context_complexity = len(context_references) * 0.1
        
        # 特殊字符和标点复杂度
        punctuation_count = len(re.findall(r'[，。！？；：""''（）【】《》]', text))
        punctuation_complexity = punctuation_count / text_length if text_length > 0 else 0
        
        # 综合计算复杂度分数
        complexity = min(1.0, (
            keyword_density * 0.3 +
            context_complexity * 0.3 +
            punctuation_complexity * 0.2 +
            min(0.3, word_count / 100) * 0.2
        ))
        
        return complexity

    def _extract_system_prompt(
        self,
        contents: List[Dict],
        turn_data: Dict
    ) -> Optional[str]:
        """
        提取 system prompt

        Gemini CLI 的 system prompt 可能在：
        1. turn_data.system_prompt 字段
        2. contents 的第一个 user message（包含系统指令）
        """
        # Check for explicit system_prompt field at turn level
        if "system_prompt" in turn_data:
            return str(turn_data["system_prompt"])

        # Check for system_instruction field
        if "system_instruction" in turn_data:
            return str(turn_data["system_instruction"])

        # Heuristic: Look for system-like content in first user message
        if contents and len(contents) > 0:
            first_content = contents[0]
            if first_content.get("role") == "user":
                parts = first_content.get("parts", [])
                for part in parts:
                    text = part.get("text", "")
                    # Check if it looks like a system prompt
                    # Common patterns: very long instruction, starts with "You are", etc.
                    system_indicators = [
                        "You are a specialized",
                        "You are a helpful",
                        "Your sole function is",
                        "你是一个",
                        "你的功能是",
                        "System:",
                        "Instructions:",
                    ]

                    # If it contains system indicators OR is very long (>500 chars), treat as system
                    if any(indicator in text for indicator in system_indicators):
                        return text

                    # Very long first message is likely system prompt
                    if len(text) > 500 and first_content == contents[0]:
                        return text

        return None

    def _extract_history(
        self,
        contents: List[Dict],
        current_turn: int,
        turn_data: Dict
    ) -> List[PromptComponent]:
        """
        提取历史对话

        历史对话是除了 system prompt 和最后一条用户消息之外的所有消息
        """
        history = []

        # Strategy 1: Use conversation_history if available
        conv_history = turn_data.get("conversation_history", [])
        if conv_history and isinstance(conv_history, list):
            # Check if it's a valid conversation history (list of dicts with role/content)
            if conv_history and isinstance(conv_history[0], dict):
                for i, msg in enumerate(conv_history):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")

                    if content and isinstance(content, str):
                        comp = PromptComponent(
                            type=PromptComponentType.HISTORY,
                            content=content,
                            tokens=self._count_tokens(content),
                            role=role,
                            is_repeated=current_turn > 1,
                            first_seen_turn=max(1, current_turn - len(conv_history) + i)
                        )
                        history.append(comp)
                return history

        # Strategy 2: Parse from contents
        # Skip system prompt (first message if it's a system prompt)
        # Skip last user message (new input)
        start_idx = 0

        # Check if first message is system prompt
        if contents and len(contents) > 0:
            first_content = contents[0]
            if first_content.get("role") == "user":
                parts = first_content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    # If very long or contains system indicators, skip it
                    if len(text) > 500 or "You are a specialized" in text or "Your sole function is" in text:
                        start_idx = 1

        # Extract history from remaining messages (except last user message)
        for i in range(start_idx, len(contents)):
            content_item = contents[i]
            role = content_item.get("role")
            parts = content_item.get("parts", [])

            # Determine if this is the last user message (new input)
            is_last_user = False
            if role == "user" and i == len(contents) - 1:
                is_last_user = True

            # Skip the last user message (it's new input, not history)
            if is_last_user:
                continue

            for part in parts:
                text = part.get("text", "")
                if not text:
                    continue

                comp = PromptComponent(
                    type=PromptComponentType.HISTORY,
                    content=text,
                    tokens=self._count_tokens(text),
                    role=role,
                    is_repeated=current_turn > 1,
                    first_seen_turn=1 if current_turn > 1 else current_turn
                )
                history.append(comp)

        return history

    def _extract_new_input(
        self,
        contents: List[Dict],
        turn_data: Dict
    ) -> Optional[str]:
        """
        提取新用户输入（最后一条用户消息）

        但要注意：如果最后一条用户消息是 system prompt（很长），则不算作新输入
        """
        if not contents:
            return None

        # The last user message is typically the new input
        for content in reversed(contents):
            if content.get("role") == "user":
                parts = content.get("parts", [])
                for part in parts:
                    text = part.get("text", "")
                    if text:
                        # If this is a very long message AND it's the first content item,
                        # it might be a system prompt, not new input
                        if len(text) > 500 and content == contents[0]:
                            # This is likely system prompt, keep looking
                            continue
                        return text
        return None

    def _extract_tools(self, request: Dict) -> Optional[List]:
        """提取工具定义"""
        return request.get("tools")

    def _count_tokens(self, text: str) -> int:
        """
        计算 token 数量

        Uses tiktoken if available, otherwise falls back to estimation.
        """
        if not text:
            return 0

        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass

        # Fallback: Rough estimation (1 token ≈ 4 characters for English)
        # For Chinese/Japanese, use ~1.5 characters per token
        # Simple heuristic: average of both
        return max(1, int(len(text) / 3))

    def _is_component_repeated(
        self,
        current: PromptComponent,
        previous_structure: PromptStructure,
        component_type: PromptComponentType
    ) -> bool:
        """
        检查组件是否在上一轮出现过

        Uses exact content matching.
        """
        for prev_comp in previous_structure.components:
            if prev_comp.type == component_type:
                # Exact match on content
                if prev_comp.content == current.content:
                    return True
        return False

    def analyze_session(
        self,
        session_data: Dict[str, Any]
    ) -> List[PromptStructure]:
        """
        分析整个会话的所有 turns

        Gemini CLI 特殊处理：
        - 所有交互可能在 1 个 turn 中
        - 每个 generateContent request 代表一次实际交互
        - 我们把每个 request 当作一个"虚拟 turn"

        Args:
            session_data: 完整的 session capture data

        Returns:
            List of PromptStructure for each interaction
        """
        turns = session_data.get("turns", [])
        structures = []

        # 如果只有 1 个 turn，但有多个 requests，按 request 分析
        if len(turns) == 1 and len(turns[0].get("requests", [])) > 1:
            # Gemini CLI 格式：所有交互在 1 个 turn 的多个 requests 中
            turn = turns[0]
            requests = turn.get("requests", [])

            # 找出所有有 contents 的 requests（真实的 LLM 交互）
            # 注意：Gemini CLI 可能对同一次交互发送多个请求（regular + stream）
            # 我们根据 contents 长度去重，只保留独特的交互
            all_requests = []
            for req in requests:
                url = req.get("url", "")
                # Match both generateContent and streamGenerateContent
                is_generate_request = ("GenerateContent" in url or "generateContent" in url)
                if is_generate_request and "contents" in req:
                    contents_len = len(req.get("contents", []))
                    all_requests.append({
                        'request': req,
                        'contents_len': contents_len
                    })

            # 去重：根据 contents 长度，保留每个长度的第一个请求
            seen_lens = set()
            llm_requests = []
            for item in all_requests:
                if item['contents_len'] not in seen_lens:
                    llm_requests.append(item['request'])
                    seen_lens.add(item['contents_len'])

            # 分析每个 request
            for i, req in enumerate(llm_requests):
                # 创建临时 turn_data
                temp_turn_data = {
                    "turn_number": i + 1,
                    "requests": [req],
                    "system_prompt": turn.get("system_prompt")
                }

                prev_structure = structures[-1] if structures else None
                structure = self.analyze_turn(temp_turn_data, i + 1, prev_structure)
                structures.append(structure)

        else:
            # 标准格式：每个 turn 一个交互
            for i, turn_data in enumerate(turns):
                prev_structure = structures[-1] if structures else None
                structure = self.analyze_turn(turn_data, i + 1, prev_structure)
                structures.append(structure)

        return structures
    
    def analyze_intent_flow(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析会话级别的意图流
        
        Args:
            session_data: 会话数据，包含多个对话轮次
            
        Returns:
            意图流分析结果，包含转换矩阵、模式识别等
        """
        turns = session_data.get('turns', [])
        if not turns:
            return {
                'intent_transitions': [],
                'intent_distribution': {},
                'flow_patterns': [],
                'complexity_trend': [],
                'session_summary': {}
            }
        
        # 提取每轮的意图信息
        intent_sequence = []
        complexity_scores = []
        
        for turn in turns:
            # 获取或分析意图
            if 'intent_analysis' in turn and turn['intent_analysis']:
                intent_analysis = turn['intent_analysis']
                if isinstance(intent_analysis, TurnIntentAnalysis):
                    intent_sequence.append(intent_analysis.primary_intent.intent_type)
                    complexity_scores.append(intent_analysis.complexity_score)
                elif isinstance(intent_analysis, dict):
                    # 处理字典格式的意图分析
                    primary_intent_data = intent_analysis.get('primary_intent', {})
                    if primary_intent_data:
                        try:
                            intent_type = IntentType(primary_intent_data.get('intent_type', 'INFORMATION_SEEKING'))
                            intent_sequence.append(intent_type)
                            complexity_scores.append(intent_analysis.get('complexity_score', 0.0))
                        except ValueError:
                            intent_sequence.append(IntentType.INFORMATION_SEEKING)
                            complexity_scores.append(0.0)
            else:
                # 如果没有意图分析，进行快速分析
                user_input = turn.get('user_input', '')
                if user_input:
                    intent_type, _ = self.intent_classifier.classify_intent(user_input)
                    intent_sequence.append(intent_type)
                    complexity_scores.append(0.5)  # 默认复杂度
                else:
                    intent_sequence.append(IntentType.INFORMATION_SEEKING)
                    complexity_scores.append(0.0)
        
        # 分析意图转换
        transitions = self._analyze_intent_transitions(intent_sequence)
        
        # 计算意图分布
        distribution = self._calculate_intent_distribution(intent_sequence)
        
        # 识别流模式
        patterns = self._identify_flow_patterns(intent_sequence)
        
        # 分析复杂度趋势
        complexity_trend = self._analyze_complexity_trend(complexity_scores)
        
        # 生成会话摘要
        session_summary = self._generate_session_summary(intent_sequence, distribution, patterns)
        
        return {
            'intent_transitions': transitions,
            'intent_distribution': distribution,
            'flow_patterns': patterns,
            'complexity_trend': complexity_trend,
            'session_summary': session_summary,
            'total_turns': len(turns),
            'intent_sequence': [intent.value for intent in intent_sequence]
        }
    
    def _analyze_intent_transitions(self, intent_sequence: List[IntentType]) -> List[Dict[str, Any]]:
        """分析意图转换模式"""
        transitions = []
        transition_counts = {}
        
        for i in range(len(intent_sequence) - 1):
            from_intent = intent_sequence[i]
            to_intent = intent_sequence[i + 1]
            
            transition_key = f"{from_intent.value}->{to_intent.value}"
            transition_counts[transition_key] = transition_counts.get(transition_key, 0) + 1
            
            transitions.append({
                'from': from_intent.value,
                'to': to_intent.value,
                'position': i + 1,
                'type': self._classify_transition_type(from_intent, to_intent)
            })
        
        # 添加转换频率信息
        for transition in transitions:
            transition_key = f"{transition['from']}->{transition['to']}"
            transition['frequency'] = transition_counts[transition_key]
        
        return transitions
    
    def _classify_transition_type(self, from_intent: IntentType, to_intent: IntentType) -> str:
        """分类转换类型"""
        # 定义常见的转换模式
        task_progression = {
            IntentType.INFORMATION_SEEKING: [IntentType.TASK_EXECUTION, IntentType.ANALYSIS_REQUEST],
            IntentType.TASK_EXECUTION: [IntentType.REFINEMENT, IntentType.VALIDATION],
            IntentType.CREATIVE_GENERATION: [IntentType.REFINEMENT, IntentType.FOLLOW_UP]
        }
        
        clarification_flow = {
            IntentType.INFORMATION_SEEKING: [IntentType.CLARIFICATION],
            IntentType.TASK_EXECUTION: [IntentType.CLARIFICATION],
            IntentType.ANALYSIS_REQUEST: [IntentType.CLARIFICATION]
        }
        
        # 检查是否为任务进展
        if from_intent in task_progression and to_intent in task_progression[from_intent]:
            return 'task_progression'
        
        # 检查是否为澄清流程
        if from_intent in clarification_flow and to_intent in clarification_flow[from_intent]:
            return 'clarification_flow'
        
        # 检查是否为循环
        if from_intent == to_intent:
            return 'repetition'
        
        # 检查是否为返回
        if from_intent in [IntentType.CLARIFICATION, IntentType.VALIDATION] and to_intent in [IntentType.TASK_EXECUTION, IntentType.INFORMATION_SEEKING]:
            return 'return_to_main'
        
        return 'other'
    
    def _calculate_intent_distribution(self, intent_sequence: List[IntentType]) -> Dict[str, Any]:
        """计算意图分布"""
        distribution = {}
        for intent in intent_sequence:
            intent_name = intent.value
            distribution[intent_name] = distribution.get(intent_name, 0) + 1
        
        # 转换为百分比
        total = len(intent_sequence)
        for intent_name in distribution:
            distribution[intent_name] = {
                'count': distribution[intent_name],
                'percentage': round(distribution[intent_name] / total * 100, 1)
            }
        
        return distribution
    
    def _identify_flow_patterns(self, intent_sequence: List[IntentType]) -> List[Dict[str, Any]]:
        """识别流模式"""
        patterns = []
        
        # 模式1: 任务导向序列
        task_patterns = [
            [IntentType.INFORMATION_SEEKING, IntentType.TASK_EXECUTION, IntentType.REFINEMENT],
            [IntentType.TASK_EXECUTION, IntentType.REFINEMENT, IntentType.VALIDATION],
            [IntentType.INFORMATION_SEEKING, IntentType.ANALYSIS_REQUEST, IntentType.CLARIFICATION]
        ]
        
        for pattern in task_patterns:
            positions = self._find_pattern_positions(intent_sequence, pattern)
            if positions:
                patterns.append({
                    'type': 'task_oriented',
                    'pattern': [intent.value for intent in pattern],
                    'positions': positions,
                    'description': '任务导向的对话序列'
                })
        
        # 模式2: 探索性序列
        exploration_patterns = [
            [IntentType.INFORMATION_SEEKING, IntentType.INFORMATION_SEEKING, IntentType.ANALYSIS_REQUEST],
            [IntentType.CREATIVE_GENERATION, IntentType.CREATIVE_GENERATION, IntentType.REFINEMENT]
        ]
        
        for pattern in exploration_patterns:
            positions = self._find_pattern_positions(intent_sequence, pattern)
            if positions:
                patterns.append({
                    'type': 'exploration',
                    'pattern': [intent.value for intent in pattern],
                    'positions': positions,
                    'description': '探索性的对话序列'
                })
        
        # 模式3: 问题解决序列
        problem_solving_patterns = [
            [IntentType.TASK_EXECUTION, IntentType.CLARIFICATION, IntentType.TASK_EXECUTION],
            [IntentType.ANALYSIS_REQUEST, IntentType.CLARIFICATION, IntentType.ANALYSIS_REQUEST]
        ]
        
        for pattern in problem_solving_patterns:
            positions = self._find_pattern_positions(intent_sequence, pattern)
            if positions:
                patterns.append({
                    'type': 'problem_solving',
                    'pattern': [intent.value for intent in pattern],
                    'positions': positions,
                    'description': '问题解决的对话序列'
                })
        
        return patterns
    
    def _find_pattern_positions(self, sequence: List[IntentType], pattern: List[IntentType]) -> List[int]:
        """在序列中查找模式的位置"""
        positions = []
        pattern_length = len(pattern)
        
        for i in range(len(sequence) - pattern_length + 1):
            if sequence[i:i + pattern_length] == pattern:
                positions.append(i)
        
        return positions
    
    def _analyze_complexity_trend(self, complexity_scores: List[float]) -> Dict[str, Any]:
        """分析复杂度趋势"""
        if len(complexity_scores) < 2:
            return {'trend': 'stable', 'change': 0.0}
        
        # 计算趋势
        first_half = complexity_scores[:len(complexity_scores) // 2]
        second_half = complexity_scores[len(complexity_scores) // 2:]
        
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0
        
        change = avg_second - avg_first
        
        if abs(change) < 0.1:
            trend = 'stable'
        elif change > 0.3:
            trend = 'increasing'
        elif change < -0.3:
            trend = 'decreasing'
        else:
            trend = 'slight_' + ('increase' if change > 0 else 'decrease')
        
        return {
            'trend': trend,
            'change': round(change, 3),
            'avg_first_half': round(avg_first, 3),
            'avg_second_half': round(avg_second, 3)
        }
    
    def _generate_session_summary(self, intent_sequence: List[IntentType], distribution: Dict[str, Any], patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成会话摘要"""
        if not intent_sequence:
            return {'type': 'empty', 'description': '空会话'}
        
        # 确定主导意图
        dominant_intent = max(distribution.items(), key=lambda x: x[1]['count'])[0]
        
        # 分析会话类型
        if len(patterns) > 0:
            pattern_types = [p['type'] for p in patterns]
            if 'task_oriented' in pattern_types:
                session_type = 'task_oriented'
                description = '任务导向的对话，有明确的目标和步骤'
            elif 'exploration' in pattern_types:
                session_type = 'exploratory'
                description = '探索性对话，用户在学习或发现信息'
            elif 'problem_solving' in pattern_types:
                session_type = 'problem_solving'
                description = '问题解决对话，包含澄清和迭代'
            else:
                session_type = 'mixed'
                description = '混合类型的对话'
        else:
            # 基于意图分布判断
            if distribution.get('TASK_EXECUTION', {}).get('percentage', 0) > 40:
                session_type = 'task_oriented'
                description = '以任务执行为主的对话'
            elif distribution.get('INFORMATION_SEEKING', {}).get('percentage', 0) > 50:
                session_type = 'information_seeking'
                description = '以信息寻求为主的对话'
            elif distribution.get('CREATIVE_GENERATION', {}).get('percentage', 0) > 30:
                session_type = 'creative'
                description = '以创意生成为主的对话'
            else:
                session_type = 'mixed'
                description = '混合意图的对话'
        
        return {
            'type': session_type,
            'description': description,
            'dominant_intent': dominant_intent,
            'total_intents': len(intent_sequence),
            'intent_diversity': len(distribution)
        }
