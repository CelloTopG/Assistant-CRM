"""
Knowledge Base Gap Analysis Service for WCFCB Assistant CRM Phase 2
Identifies knowledge gaps and provides recommendations for knowledge base improvements
"""

import frappe
from frappe.utils import now, get_datetime
from typing import Dict, List, Any, Optional, Tuple
import json
import re
from collections import defaultdict, Counter


class KnowledgeGapAnalysisService:
    """
    Service to analyze knowledge base gaps and provide recommendations
    for improving WorkCom's response capabilities
    """
    
    def __init__(self):
        # Common question patterns that indicate knowledge gaps
        self.gap_indicators = {
            'unanswered_questions': [
                r'\bwhat\s+is\b', r'\bhow\s+do\s+i\b', r'\bwhere\s+can\s+i\b',
                r'\bwhen\s+will\b', r'\bwhy\s+does\b', r'\bwho\s+should\b'
            ],
            'confusion_patterns': [
                r'\bi\s+don\'t\s+understand\b', r'\bconfused\s+about\b',
                r'\bnot\s+clear\b', r'\bcan\s+you\s+explain\b'
            ],
            'escalation_triggers': [
                r'\bspeak\s+to\s+someone\b', r'\bhuman\s+agent\b',
                r'\bnot\s+helpful\b', r'\bstill\s+need\s+help\b'
            ],
            'process_gaps': [
                r'\bstep\s+by\s+step\b', r'\bprocess\s+for\b',
                r'\bhow\s+to\s+complete\b', r'\bwhat\s+documents\b'
            ]
        }
        
        # Knowledge areas for WCFCB
        self.knowledge_areas = {
            'business_registration': {
                'keywords': ['business', 'company', 'registration', 'license'],
                'priority': 'high',
                'persona': 'employer'
            },
            'employee_contributions': {
                'keywords': ['contribution', 'payroll', 'employee', 'monthly'],
                'priority': 'high',
                'persona': 'employer'
            },
            'pension_payments': {
                'keywords': ['pension', 'payment', 'benefit', 'retirement'],
                'priority': 'high',
                'persona': 'beneficiary'
            },
            'medical_claims': {
                'keywords': ['medical', 'claim', 'healthcare', 'treatment'],
                'priority': 'high',
                'persona': 'beneficiary'
            },
            'supplier_payments': {
                'keywords': ['invoice', 'payment', 'vendor', 'supplier'],
                'priority': 'medium',
                'persona': 'supplier'
            },
            'system_administration': {
                'keywords': ['system', 'admin', 'user', 'access'],
                'priority': 'medium',
                'persona': 'wcfcb_staff'
            }
        }
        
        # Gap severity levels
        self.severity_levels = {
            'critical': {'score_threshold': 0.8, 'action': 'immediate'},
            'high': {'score_threshold': 0.6, 'action': 'urgent'},
            'medium': {'score_threshold': 0.4, 'action': 'planned'},
            'low': {'score_threshold': 0.2, 'action': 'monitor'}
        }
    
    def analyze_knowledge_gaps(self, conversation_data: List[Dict], 
                             knowledge_base_articles: List[Dict] = None,
                             time_period: str = '30_days') -> Dict[str, Any]:
        """
        Analyze knowledge gaps based on conversation data and knowledge base
        
        Args:
            conversation_data: List of conversation records
            knowledge_base_articles: Current knowledge base articles
            time_period: Analysis time period
            
        Returns:
            Dict containing gap analysis and recommendations
        """
        try:
            # Analyze conversation patterns
            conversation_analysis = self._analyze_conversation_patterns(conversation_data)
            
            # Identify unanswered questions
            unanswered_questions = self._identify_unanswered_questions(conversation_data)
            
            # Analyze escalation patterns
            escalation_analysis = self._analyze_escalation_patterns(conversation_data)
            
            # Check knowledge base coverage
            coverage_analysis = self._analyze_knowledge_coverage(
                conversation_data, knowledge_base_articles
            )
            
            # Identify priority gaps
            priority_gaps = self._identify_priority_gaps(
                conversation_analysis, unanswered_questions, escalation_analysis
            )
            
            # Generate recommendations
            recommendations = self._generate_gap_recommendations(priority_gaps, coverage_analysis)
            
            # Calculate overall knowledge health score
            health_score = self._calculate_knowledge_health_score(
                conversation_analysis, coverage_analysis, escalation_analysis
            )
            
            return {
                'success': True,
                'analysis_period': time_period,
                'conversation_analysis': conversation_analysis,
                'unanswered_questions': unanswered_questions,
                'escalation_analysis': escalation_analysis,
                'coverage_analysis': coverage_analysis,
                'priority_gaps': priority_gaps,
                'recommendations': recommendations,
                'knowledge_health_score': health_score,
                'timestamp': now()
            }
            
        except Exception as e:
            frappe.log_error(f"Knowledge gap analysis error: {str(e)}", "KnowledgeGapAnalysisService")
            return {
                'success': False,
                'error': str(e),
                'recommendations': [],
                'knowledge_health_score': 0.5
            }
    
    def _analyze_conversation_patterns(self, conversation_data: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in conversation data"""
        
        patterns = {
            'total_conversations': len(conversation_data),
            'question_patterns': defaultdict(int),
            'topic_distribution': defaultdict(int),
            'resolution_rates': {},
            'common_issues': []
        }
        
        for conversation in conversation_data:
            messages = conversation.get('messages', [])
            
            for message in messages:
                content = message.get('content', '').lower()
                
                # Analyze question patterns
                for pattern_type, pattern_list in self.gap_indicators.items():
                    for pattern in pattern_list:
                        if re.search(pattern, content):
                            patterns['question_patterns'][pattern_type] += 1
                
                # Analyze topic distribution
                for topic, topic_data in self.knowledge_areas.items():
                    if any(keyword in content for keyword in topic_data['keywords']):
                        patterns['topic_distribution'][topic] += 1
        
        # Calculate resolution rates
        resolved_conversations = sum(1 for conv in conversation_data 
                                   if conv.get('status') == 'resolved')
        patterns['resolution_rates']['overall'] = (
            resolved_conversations / max(len(conversation_data), 1)
        )
        
        return patterns
    
    def _identify_unanswered_questions(self, conversation_data: List[Dict]) -> List[Dict[str, Any]]:
        """Identify questions that weren't adequately answered"""
        
        unanswered = []
        
        for conversation in conversation_data:
            messages = conversation.get('messages', [])
            
            # Look for question-answer patterns
            for i, message in enumerate(messages):
                if message.get('sender') == 'user':
                    content = message.get('content', '')
                    
                    # Check if this looks like a question
                    if self._is_question(content):
                        # Check if there's an adequate response
                        response_quality = self._evaluate_response_quality(
                            messages, i, content
                        )
                        
                        if response_quality['score'] < 0.6:  # Threshold for adequate response
                            unanswered.append({
                                'question': content,
                                'conversation_id': conversation.get('id'),
                                'response_quality': response_quality,
                                'topic_area': self._classify_question_topic(content),
                                'urgency': self._assess_question_urgency(content)
                            })
        
        return unanswered
    
    def _analyze_escalation_patterns(self, conversation_data: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in conversation escalations"""
        
        escalation_analysis = {
            'total_escalations': 0,
            'escalation_rate': 0.0,
            'escalation_triggers': defaultdict(int),
            'escalation_topics': defaultdict(int),
            'time_to_escalation': []
        }
        
        for conversation in conversation_data:
            if conversation.get('escalated', False):
                escalation_analysis['total_escalations'] += 1
                
                # Analyze escalation triggers
                messages = conversation.get('messages', [])
                for message in messages:
                    content = message.get('content', '').lower()
                    
                    for trigger_pattern in self.gap_indicators['escalation_triggers']:
                        if re.search(trigger_pattern, content):
                            escalation_analysis['escalation_triggers'][trigger_pattern] += 1
                
                # Analyze escalation topics
                topic = self._classify_conversation_topic(conversation)
                if topic:
                    escalation_analysis['escalation_topics'][topic] += 1
        
        # Calculate escalation rate
        escalation_analysis['escalation_rate'] = (
            escalation_analysis['total_escalations'] / max(len(conversation_data), 1)
        )
        
        return escalation_analysis
    
    def _analyze_knowledge_coverage(self, conversation_data: List[Dict], 
                                  knowledge_base_articles: List[Dict] = None) -> Dict[str, Any]:
        """Analyze knowledge base coverage for common topics"""
        
        coverage = {
            'total_articles': len(knowledge_base_articles) if knowledge_base_articles else 0,
            'topic_coverage': {},
            'coverage_gaps': [],
            'article_effectiveness': {}
        }
        
        # Analyze topic coverage
        for topic, topic_data in self.knowledge_areas.items():
            # Count conversations about this topic
            topic_conversations = sum(
                1 for conv in conversation_data
                if self._conversation_matches_topic(conv, topic_data['keywords'])
            )
            
            # Count relevant articles
            topic_articles = 0
            if knowledge_base_articles:
                topic_articles = sum(
                    1 for article in knowledge_base_articles
                    if self._article_matches_topic(article, topic_data['keywords'])
                )
            
            coverage['topic_coverage'][topic] = {
                'conversations': topic_conversations,
                'articles': topic_articles,
                'coverage_ratio': topic_articles / max(topic_conversations, 1),
                'priority': topic_data['priority']
            }
            
            # Identify gaps
            if topic_conversations > 0 and topic_articles == 0:
                coverage['coverage_gaps'].append({
                    'topic': topic,
                    'conversations': topic_conversations,
                    'priority': topic_data['priority']
                })
        
        return coverage
    
    def _identify_priority_gaps(self, conversation_analysis: Dict, 
                              unanswered_questions: List[Dict],
                              escalation_analysis: Dict) -> List[Dict[str, Any]]:
        """Identify priority knowledge gaps"""
        
        gaps = []
        
        # High-frequency unanswered questions
        question_topics = defaultdict(list)
        for question in unanswered_questions:
            topic = question['topic_area']
            question_topics[topic].append(question)
        
        for topic, questions in question_topics.items():
            if len(questions) >= 3:  # Threshold for priority gap
                gaps.append({
                    'type': 'unanswered_questions',
                    'topic': topic,
                    'frequency': len(questions),
                    'severity': self._calculate_gap_severity(len(questions), 'frequency'),
                    'sample_questions': questions[:3],
                    'recommended_action': 'create_knowledge_article'
                })
        
        # High-escalation topics
        for topic, escalation_count in escalation_analysis['escalation_topics'].items():
            if escalation_count >= 2:  # Threshold for escalation concern
                gaps.append({
                    'type': 'escalation_trigger',
                    'topic': topic,
                    'escalation_count': escalation_count,
                    'severity': self._calculate_gap_severity(escalation_count, 'escalation'),
                    'recommended_action': 'improve_response_quality'
                })
        
        # Sort by severity
        gaps.sort(key=lambda x: x['severity'], reverse=True)
        
        return gaps
    
    def _generate_gap_recommendations(self, priority_gaps: List[Dict], 
                                    coverage_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate specific recommendations for addressing knowledge gaps"""
        
        recommendations = []
        
        for gap in priority_gaps:
            if gap['type'] == 'unanswered_questions':
                recommendations.append({
                    'priority': 'high' if gap['severity'] > 0.7 else 'medium',
                    'action': 'Create Knowledge Article',
                    'topic': gap['topic'],
                    'description': f"Create comprehensive article for {gap['topic']} based on {gap['frequency']} unanswered questions",
                    'estimated_effort': 'medium',
                    'expected_impact': 'high',
                    'sample_content': self._generate_article_outline(gap['sample_questions'])
                })
            
            elif gap['type'] == 'escalation_trigger':
                recommendations.append({
                    'priority': 'high',
                    'action': 'Improve Response Templates',
                    'topic': gap['topic'],
                    'description': f"Enhance response quality for {gap['topic']} to reduce {gap['escalation_count']} escalations",
                    'estimated_effort': 'low',
                    'expected_impact': 'medium',
                    'specific_improvements': ['add_examples', 'simplify_language', 'provide_alternatives']
                })
        
        # Add coverage gap recommendations
        for gap in coverage_analysis['coverage_gaps']:
            if gap['priority'] == 'high':
                recommendations.append({
                    'priority': 'high',
                    'action': 'Create Missing Content',
                    'topic': gap['topic'],
                    'description': f"Create content for {gap['topic']} - {gap['conversations']} conversations with no articles",
                    'estimated_effort': 'high',
                    'expected_impact': 'high'
                })
        
        return recommendations
    
    def _calculate_knowledge_health_score(self, conversation_analysis: Dict,
                                        coverage_analysis: Dict,
                                        escalation_analysis: Dict) -> Dict[str, float]:
        """Calculate overall knowledge base health score"""
        
        # Resolution rate score (0-1)
        resolution_score = conversation_analysis['resolution_rates'].get('overall', 0.5)
        
        # Coverage score (0-1)
        coverage_scores = [
            data['coverage_ratio'] for data in coverage_analysis['topic_coverage'].values()
        ]
        coverage_score = sum(coverage_scores) / max(len(coverage_scores), 1)
        
        # Escalation score (inverse - lower escalation is better)
        escalation_score = max(0, 1 - escalation_analysis['escalation_rate'])
        
        # Overall health score
        overall_score = (resolution_score * 0.4 + coverage_score * 0.4 + escalation_score * 0.2)
        
        return {
            'overall': overall_score,
            'resolution_rate': resolution_score,
            'coverage_score': coverage_score,
            'escalation_score': escalation_score,
            'health_level': self._get_health_level(overall_score)
        }
    
    def _is_question(self, text: str) -> bool:
        """Check if text contains a question"""
        question_indicators = ['?', 'what', 'how', 'when', 'where', 'why', 'who', 'which']
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in question_indicators)
    
    def _evaluate_response_quality(self, messages: List[Dict], question_index: int, question: str) -> Dict[str, Any]:
        """Evaluate the quality of response to a question"""
        
        # Look for assistant response after the question
        response_quality = {'score': 0.0, 'factors': []}
        
        if question_index + 1 < len(messages):
            response = messages[question_index + 1]
            if response.get('sender') == 'assistant':
                response_content = response.get('content', '')
                
                # Basic quality indicators
                if len(response_content) > 20:
                    response_quality['score'] += 0.3
                    response_quality['factors'].append('adequate_length')
                
                if any(word in response_content.lower() for word in ['here', 'help', 'can', 'will']):
                    response_quality['score'] += 0.2
                    response_quality['factors'].append('helpful_language')
                
                if 'http' in response_content or 'contact' in response_content.lower():
                    response_quality['score'] += 0.3
                    response_quality['factors'].append('actionable_information')
                
                # Check for follow-up questions indicating confusion
                if question_index + 2 < len(messages):
                    follow_up = messages[question_index + 2]
                    if follow_up.get('sender') == 'user' and self._is_question(follow_up.get('content', '')):
                        response_quality['score'] -= 0.2
                        response_quality['factors'].append('confusion_follow_up')
        
        return response_quality
    
    def _classify_question_topic(self, question: str) -> str:
        """Classify question into knowledge area topic"""
        question_lower = question.lower()
        
        for topic, topic_data in self.knowledge_areas.items():
            if any(keyword in question_lower for keyword in topic_data['keywords']):
                return topic
        
        return 'general'
    
    def _assess_question_urgency(self, question: str) -> str:
        """Assess urgency level of a question"""
        urgent_indicators = ['urgent', 'asap', 'immediately', 'emergency', 'help']
        question_lower = question.lower()
        
        if any(indicator in question_lower for indicator in urgent_indicators):
            return 'high'
        
        return 'normal'
    
    def _classify_conversation_topic(self, conversation: Dict) -> str:
        """Classify conversation topic based on content"""
        all_content = ' '.join([
            msg.get('content', '') for msg in conversation.get('messages', [])
        ]).lower()
        
        for topic, topic_data in self.knowledge_areas.items():
            if any(keyword in all_content for keyword in topic_data['keywords']):
                return topic
        
        return 'general'
    
    def _conversation_matches_topic(self, conversation: Dict, keywords: List[str]) -> bool:
        """Check if conversation matches topic keywords"""
        all_content = ' '.join([
            msg.get('content', '') for msg in conversation.get('messages', [])
        ]).lower()
        
        return any(keyword in all_content for keyword in keywords)
    
    def _article_matches_topic(self, article: Dict, keywords: List[str]) -> bool:
        """Check if article matches topic keywords"""
        article_content = (
            article.get('title', '') + ' ' + 
            article.get('content', '') + ' ' + 
            ' '.join(article.get('keywords', []))
        ).lower()
        
        return any(keyword in article_content for keyword in keywords)
    
    def _calculate_gap_severity(self, count: int, gap_type: str) -> float:
        """Calculate severity score for a gap"""
        if gap_type == 'frequency':
            # More frequent = higher severity
            return min(count / 10.0, 1.0)
        elif gap_type == 'escalation':
            # More escalations = higher severity
            return min(count / 5.0, 1.0)
        
        return 0.5
    
    def _generate_article_outline(self, sample_questions: List[Dict]) -> List[str]:
        """Generate article outline based on sample questions"""
        outline = [
            "Overview and Introduction",
            "Step-by-step Process",
            "Required Documents",
            "Common Issues and Solutions",
            "Contact Information"
        ]
        
        # Add specific sections based on questions
        question_texts = [q['question'] for q in sample_questions]
        all_questions = ' '.join(question_texts).lower()
        
        if 'document' in all_questions:
            outline.insert(2, "Document Requirements")
        
        if 'time' in all_questions or 'when' in all_questions:
            outline.insert(-1, "Timeline and Deadlines")
        
        return outline
    
    def _get_health_level(self, score: float) -> str:
        """Get health level description from score"""
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'fair'
        else:
            return 'needs_improvement'

