"""
意图分析服务
基于规则和内容特征分析用户输入的意图类型、置信度和复杂度
"""
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

class IntentAnalyzer:
    """意图分析器"""
    
    def __init__(self):
        # 意图关键词映射
        self.intent_keywords = {
            'information_seeking': [
                '什么', '怎么', '如何', '为什么', '哪里', '谁', '何时', '哪个', '哪些',
                'what', 'how', 'why', 'where', 'who', 'when', 'which',
                '解释', '说明', '介绍', '描述', '定义', '区别', '比较', '特点',
                'explain', 'describe', 'define', 'difference', 'compare', 'feature'
            ],
            'task_completion': [
                '创建', '生成', '制作', '编写', '开发', '构建', '设计', '实现',
                'create', 'generate', 'make', 'write', 'develop', 'build', 'design', 'implement',
                '帮我', '请', '需要', '想要', '可以', '能够',
                'help', 'please', 'need', 'want', 'can', 'could'
            ],
            'creative_writing': [
                '写', '故事', '诗歌', '文章', '作文', '小说', '剧本', '歌词',
                'write', 'story', 'poem', 'article', 'essay', 'novel', 'script', 'lyrics',
                '创意', '想象', '构思', '灵感', '创作',
                'creative', 'imagination', 'idea', 'inspiration', 'creation'
            ],
            'analysis': [
                '分析', '评估', '检查', '审查', '诊断', '测试', '验证', '比较',
                'analyze', 'evaluate', 'check', 'review', 'diagnose', 'test', 'verify', 'compare',
                '错误', '问题', 'bug', '故障', '异常', '修复', '解决',
                'error', 'problem', 'bug', 'issue', 'exception', 'fix', 'resolve'
            ],
            'clarification': [
                '确认', '明确', '清楚', '理解', '明白', '详细', '具体', '举例',
                'confirm', 'clarify', 'clear', 'understand', 'detail', 'specific', 'example',
                '重新', '再次', '重复', '换个', '其他', '不同',
                'again', 'repeat', 'different', 'other', 'another'
            ]
        }
        
        # 复杂度评估模式
        self.complexity_patterns = {
            'high': [
                r'\b(and|且|和|与)\b.*\b(and|且|和|与)\b',  # 多个条件
                r'\b(or|或)\b.*\b(or|或)\b',  # 多个选择
                r'\b(if|如果|假如|假设)\b',  # 条件语句
                r'\b(while|当|同时)\b',  # 循环或并发
                r'\b(function|函数|方法|类|class)\b',  # 编程概念
                r'\d+.*\d+.*\d+',  # 多个数字
                r'[,.;]{2,}',  # 多个标点符号
            ],
            'medium': [
                r'\b(and|且|和|与)\b',  # 简单连接
                r'\b(or|或)\b',  # 简单选择
                r'\d+',  # 包含数字
                r'\b(not|不|非)\b',  # 否定
                r'[,.;]',  # 标点符号
            ]
        }
    
    def analyze_intent(self, content: str) -> Dict[str, Any]:
        """
        分析文本的意图
        
        Args:
            content: 要分析的文本内容
            
        Returns:
            意图分析结果，包含主要意图、置信度、复杂度等信息
        """
        if not content or not content.strip():
            return self._create_empty_analysis()
        
        # 文本预处理
        processed_content = self._preprocess_text(content)
        
        # 意图识别
        intent_scores = self._calculate_intent_scores(processed_content)
        primary_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[primary_intent]
        
        # 复杂度评估
        complexity_score = self._calculate_complexity(content)
        
        # 生成意图单元
        intent_units = self._generate_intent_units(content, intent_scores)
        
        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "complexity_score": complexity_score,
            "total_tokens": len(content.split()),
            "intent_diversity": self._calculate_diversity(intent_scores),
            "intent_units": intent_units
        }
    
    def analyze_intent_flow(self, conversation_flow: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析对话中的意图流转模式
        
        Args:
            conversation_flow: 对话流程列表
            
        Returns:
            意图流转分析结果
        """
        intent_sequence = []
        
        # 提取意图序列
        for turn in conversation_flow:
            if "intent_analysis" in turn and turn["intent_analysis"]:
                intent_sequence.append(turn["intent_analysis"]["primary_intent"])
        
        if not intent_sequence:
            return self._create_empty_flow_analysis()
        
        # 构建流转矩阵
        transition_matrix = self._build_transition_matrix(intent_sequence)
        
        # 识别流转模式
        transition_patterns = self._identify_transition_patterns(intent_sequence)
        
        # 计算意图分布
        intent_distribution = self._calculate_intent_distribution(intent_sequence)
        
        return {
            "transition_matrix": transition_matrix,
            "transition_patterns": transition_patterns,
            "intent_distribution": intent_distribution
        }
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 转换为小写
        text = text.lower().strip()
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _calculate_intent_scores(self, content: str) -> Dict[str, float]:
        """计算各种意图的得分"""
        scores = {}
        total_words = len(content.split())
        
        for intent_type, keywords in self.intent_keywords.items():
            score = 0.0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in content:
                    # 根据关键词长度和匹配次数计算权重
                    keyword_weight = len(keyword) / max(len(k) for k in keywords)
                    match_count = content.count(keyword.lower())
                    score += keyword_weight * match_count
                    matched_keywords.append(keyword)
            
            # 归一化得分
            if total_words > 0:
                score = min(score / total_words, 1.0)
            else:
                score = 0.0
                
            scores[intent_type] = score
        
        # 如果没有明显的意图关键词，使用默认意图
        if max(scores.values()) < 0.1:
            scores['information_seeking'] = 0.3  # 默认意图
        
        return scores
    
    def _calculate_complexity(self, content: str) -> float:
        """计算文本复杂度"""
        complexity_score = 0.0
        
        # 检查高复杂度模式
        for pattern in self.complexity_patterns.get('high', []):
            if re.search(pattern, content, re.IGNORECASE):
                complexity_score += 0.3
        
        # 检查中等复杂度模式
        for pattern in self.complexity_patterns.get('medium', []):
            if re.search(pattern, content, re.IGNORECASE):
                complexity_score += 0.1
        
        # 基于长度调整复杂度
        word_count = len(content.split())
        if word_count > 50:
            complexity_score += 0.2
        elif word_count > 20:
            complexity_score += 0.1
        
        # 基于句子数量调整复杂度
        sentence_count = len(re.split(r'[.!?]+', content))
        if sentence_count > 3:
            complexity_score += 0.1
        
        return min(complexity_score, 1.0)
    
    def _generate_intent_units(self, content: str, intent_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """生成意图单元"""
        intent_units = []
        words = content.split()
        total_words = len(words)
        
        # 为每个意图类型生成一个单元（如果得分大于0）
        for intent_type, score in intent_scores.items():
            if score > 0:
                unit_id = hashlib.md5(f"{intent_type}_{content[:20]}_{score}".encode()).hexdigest()[:8]
                
                intent_units.append({
                    "id": unit_id,
                    "intent_type": intent_type,
                    "confidence": score,
                    "complexity_score": self._calculate_complexity(content),
                    "tokens": total_words,
                    "start_pos": 0,
                    "end_pos": total_words,
                    "metadata": {
                        "matched_keywords": self._get_matched_keywords(content, intent_type),
                        "analysis_timestamp": datetime.now().isoformat()
                    }
                })
        
        return intent_units
    
    def _get_matched_keywords(self, content: str, intent_type: str) -> List[str]:
        """获取匹配的关键词"""
        matched_keywords = []
        content_lower = content.lower()
        
        if intent_type in self.intent_keywords:
            for keyword in self.intent_keywords[intent_type]:
                if keyword.lower() in content_lower:
                    matched_keywords.append(keyword)
        
        return matched_keywords
    
    def _calculate_diversity(self, intent_scores: Dict[str, float]) -> float:
        """计算意图多样性"""
        if not intent_scores:
            return 0.0
        
        # 计算香农多样性指数
        total_score = sum(intent_scores.values())
        if total_score == 0:
            return 0.0
        
        diversity = 0.0
        for score in intent_scores.values():
            if score > 0:
                proportion = score / total_score
                diversity -= proportion * (proportion ** 0.5)  # 简化的多样性计算
        
        return max(0.0, min(diversity, 1.0))
    
    def _build_transition_matrix(self, intent_sequence: List[str]) -> Dict[str, Dict[str, int]]:
        """构建意图流转矩阵"""
        matrix = {}
        
        # 初始化矩阵
        unique_intents = list(set(intent_sequence))
        for from_intent in unique_intents:
            matrix[from_intent] = {}
            for to_intent in unique_intents:
                matrix[from_intent][to_intent] = 0
        
        # 填充流转计数
        for i in range(len(intent_sequence) - 1):
            from_intent = intent_sequence[i]
            to_intent = intent_sequence[i + 1]
            matrix[from_intent][to_intent] += 1
        
        return matrix
    
    def _identify_transition_patterns(self, intent_sequence: List[str]) -> List[Dict[str, Any]]:
        """识别流转模式"""
        patterns = []
        
        # 统计两两流转
        transition_counts = {}
        for i in range(len(intent_sequence) - 1):
            transition = f"{intent_sequence[i]}->{intent_sequence[i + 1]}"
            transition_counts[transition] = transition_counts.get(transition, 0) + 1
        
        # 生成模式列表
        for transition, count in transition_counts.items():
            from_intent, to_intent = transition.split("->")
            
            patterns.append({
                "from_intent": from_intent,
                "to_intent": to_intent,
                "frequency": count,
                "confidence": min(count / len(intent_sequence), 1.0)
            })
        
        # 按频率排序
        patterns.sort(key=lambda x: x["frequency"], reverse=True)
        
        return patterns[:10]  # 只返回前10个模式
    
    def _calculate_intent_distribution(self, intent_sequence: List[str]) -> Dict[str, int]:
        """计算意图分布"""
        distribution = {}
        
        for intent in intent_sequence:
            distribution[intent] = distribution.get(intent, 0) + 1
        
        return distribution
    
    def _create_empty_analysis(self) -> Dict[str, Any]:
        """创建空的分析结果"""
        return {
            "primary_intent": "unknown",
            "confidence": 0.0,
            "complexity_score": 0.0,
            "total_tokens": 0,
            "intent_diversity": 0.0,
            "intent_units": []
        }
    
    def _create_empty_flow_analysis(self) -> Dict[str, Any]:
        """创建空的流转分析结果"""
        return {
            "transition_matrix": {},
            "transition_patterns": [],
            "intent_distribution": {}
        }