# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, get_datetime, add_to_date
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
import random
import hashlib

# Set up logging
logger = logging.getLogger(__name__)

class ResponseOptimizationManager:
    """
    Enhanced response optimization manager for Phase 2 with verbosity control and clarity improvements.
    Manages response optimization, quality scoring, and A/B testing for the assistant_crm system.
    Provides continuous improvement mechanisms for response effectiveness.
    """

    def __init__(self):
        """Initialize response optimization manager."""
        self.quality_metrics = {}
        self.ab_test_variants = {}
        self.optimization_settings = self._load_optimization_settings()

        # Phase 2 enhancements - verbosity control
        self.verbosity_thresholds = {
            'concise': {'max_words': 50, 'max_sentences': 3},
            'moderate': {'max_words': 100, 'max_sentences': 5},
            'detailed': {'max_words': 200, 'max_sentences': 8},
            'comprehensive': {'max_words': 300, 'max_sentences': 12}
        }

        # Clarity improvement patterns
        self.clarity_patterns = {
            'remove_redundancy': [
                r'\b(basically|essentially|actually|literally)\b',
                r'\b(in order to|for the purpose of)\b',
                r'\b(due to the fact that|because of the fact that)\b'
            ],
            'simplify_language': [
                ('utilize', 'use'),
                ('facilitate', 'help'),
                ('demonstrate', 'show'),
                ('implement', 'do'),
                ('assistance', 'help')
            ],
            'improve_structure': {
                'use_bullet_points': True,
                'numbered_steps': True,
                'clear_sections': True
            }
        }
    
    def _load_optimization_settings(self) -> Dict:
        """Load optimization settings from configuration."""
        try:
            # Get optimization settings from database or use defaults
            settings = frappe.get_single("Assistant CRM Settings")
            return {
                "enable_ab_testing": getattr(settings, 'enable_ab_testing', True),
                "quality_threshold": getattr(settings, 'response_quality_threshold', 0.7),
                "ab_test_split_ratio": getattr(settings, 'ab_test_split_ratio', 0.5),
                "optimization_learning_rate": getattr(settings, 'optimization_learning_rate', 0.1),
                "min_samples_for_optimization": getattr(settings, 'min_samples_for_optimization', 50)
            }
        except Exception:
            # Return default settings if database access fails
            return {
                "enable_ab_testing": True,
                "quality_threshold": 0.7,
                "ab_test_split_ratio": 0.5,
                "optimization_learning_rate": 0.1,
                "min_samples_for_optimization": 50
            }
    
    def calculate_response_quality_score(self, response: str, user_message: str, 
                                       intent: str, confidence: float, 
                                       user_context: Dict = None) -> Dict:
        """
        Calculate comprehensive response quality score.
        
        Args:
            response (str): Generated response
            user_message (str): Original user message
            intent (str): Detected intent
            confidence (float): Intent confidence score
            user_context (Dict): User context information
            
        Returns:
            Dict: Quality score breakdown and overall score
        """
        try:
            quality_factors = {}
            
            # 1. Intent Alignment Score (25%)
            quality_factors['intent_alignment'] = self._calculate_intent_alignment_score(
                response, intent, confidence
            )
            
            # 2. Response Completeness Score (20%)
            quality_factors['completeness'] = self._calculate_completeness_score(
                response, user_message, intent
            )
            
            # 3. Clarity and Readability Score (20%)
            quality_factors['clarity'] = self._calculate_clarity_score(response)
            
            # 4. Empathy and Tone Score (15%)
            quality_factors['empathy'] = self._calculate_empathy_score(
                response, user_message, user_context
            )
            
            # 5. Actionability Score (10%)
            quality_factors['actionability'] = self._calculate_actionability_score(
                response, intent
            )
            
            # 6. Length Appropriateness Score (10%)
            quality_factors['length_appropriateness'] = self._calculate_length_score(
                response, intent, user_context
            )
            
            # Calculate weighted overall score
            weights = {
                'intent_alignment': 0.25,
                'completeness': 0.20,
                'clarity': 0.20,
                'empathy': 0.15,
                'actionability': 0.10,
                'length_appropriateness': 0.10
            }
            
            overall_score = sum(
                quality_factors[factor] * weights[factor] 
                for factor in quality_factors
            )
            
            return {
                'overall_score': round(overall_score, 3),
                'quality_factors': quality_factors,
                'weights': weights,
                'quality_grade': self._get_quality_grade(overall_score),
                'improvement_suggestions': self._generate_improvement_suggestions(quality_factors)
            }
            
        except Exception as e:
            logger.error(f"Error calculating response quality score: {str(e)}")
            return {
                'overall_score': 0.5,
                'quality_factors': {},
                'error': str(e)
            }
    
    def _calculate_intent_alignment_score(self, response: str, intent: str, confidence: float) -> float:
        """Calculate how well the response aligns with the detected intent."""
        # Base score from confidence
        base_score = confidence
        
        # Intent-specific keywords that should appear in responses
        intent_keywords = {
            'greeting': ['hello', 'hi', 'welcome', 'help'],
            'claim_submission': ['claim', 'submit', 'process', 'documentation'],
            'payment_status': ['payment', 'status', 'amount', 'schedule'],
            'document_request': ['document', 'form', 'download', 'upload'],
            'technical_help': ['help', 'support', 'assistance', 'guide'],
            'agent_request': ['agent', 'specialist', 'human', 'transfer']
        }
        
        keywords = intent_keywords.get(intent, [])
        if keywords:
            response_lower = response.lower()
            keyword_matches = sum(1 for keyword in keywords if keyword in response_lower)
            keyword_score = min(1.0, keyword_matches / len(keywords))
            
            # Combine confidence and keyword alignment
            return (base_score * 0.7) + (keyword_score * 0.3)
        
        return base_score
    
    def _calculate_completeness_score(self, response: str, user_message: str, intent: str) -> float:
        """Calculate response completeness based on intent requirements."""
        response_length = len(response)
        
        # Intent-specific completeness requirements
        completeness_requirements = {
            'greeting': {'min_length': 20, 'max_length': 150},
            'claim_submission': {'min_length': 100, 'max_length': 400},
            'payment_status': {'min_length': 80, 'max_length': 300},
            'document_request': {'min_length': 60, 'max_length': 250},
            'technical_help': {'min_length': 100, 'max_length': 500},
            'agent_request': {'min_length': 50, 'max_length': 200}
        }
        
        requirements = completeness_requirements.get(intent, {'min_length': 50, 'max_length': 300})
        
        if response_length < requirements['min_length']:
            return 0.3  # Too short
        elif response_length > requirements['max_length']:
            return 0.7  # Too long
        else:
            # Optimal length range
            return 1.0
    
    def _calculate_clarity_score(self, response: str) -> float:
        """Calculate response clarity and readability."""
        # Simple readability metrics
        sentences = response.split('.')
        words = response.split()
        
        if not sentences or not words:
            return 0.0
        
        # Average sentence length (optimal: 10-20 words)
        avg_sentence_length = len(words) / len(sentences)
        sentence_score = 1.0 if 10 <= avg_sentence_length <= 20 else 0.7
        
        # Check for clear structure (questions, bullet points, etc.)
        structure_indicators = ['?', '•', '1.', '2.', '3.', '\n-', '\n*']
        has_structure = any(indicator in response for indicator in structure_indicators)
        structure_score = 1.0 if has_structure else 0.8
        
        # Check for jargon or complex terms
        complex_terms = ['pursuant', 'heretofore', 'aforementioned', 'notwithstanding']
        has_jargon = any(term in response.lower() for term in complex_terms)
        jargon_score = 0.6 if has_jargon else 1.0
        
        return (sentence_score + structure_score + jargon_score) / 3
    
    def _calculate_empathy_score(self, response: str, user_message: str, user_context: Dict = None) -> float:
        """Calculate empathy and emotional appropriateness of response."""
        response_lower = response.lower()
        user_message_lower = user_message.lower()
        
        # Empathy indicators
        empathy_phrases = [
            'i understand', 'i know', 'i realize', 'i appreciate',
            'thank you for', 'i\'m sorry', 'i apologize',
            'let me help', 'i\'ll help', 'i\'m here to help'
        ]
        
        empathy_count = sum(1 for phrase in empathy_phrases if phrase in response_lower)
        empathy_score = min(1.0, empathy_count * 0.3)
        
        # Check for emotional context in user message
        emotional_indicators = [
            'frustrated', 'worried', 'concerned', 'urgent', 'help',
            'problem', 'issue', 'difficult', 'confused'
        ]
        
        user_emotional = any(indicator in user_message_lower for indicator in emotional_indicators)
        
        if user_emotional:
            # Response should be more empathetic for emotional messages
            return empathy_score * 1.2 if empathy_score > 0.5 else 0.4
        else:
            # Standard empathy level is fine
            return max(0.7, empathy_score)
    
    def _calculate_actionability_score(self, response: str, intent: str) -> float:
        """Calculate how actionable the response is."""
        response_lower = response.lower()
        
        # Action indicators
        action_phrases = [
            'you can', 'please', 'click', 'visit', 'download',
            'submit', 'contact', 'call', 'email', 'follow these steps',
            'here\'s how', 'to do this', 'next step'
        ]
        
        action_count = sum(1 for phrase in action_phrases if phrase in response_lower)
        
        # Intent-specific actionability requirements
        high_action_intents = ['claim_submission', 'document_request', 'technical_help']
        medium_action_intents = ['payment_status', 'agent_request']
        low_action_intents = ['greeting']
        
        if intent in high_action_intents:
            return min(1.0, action_count * 0.25)
        elif intent in medium_action_intents:
            return min(1.0, action_count * 0.4)
        else:
            return min(1.0, 0.7 + (action_count * 0.1))
    
    def _calculate_length_score(self, response: str, intent: str, user_context: Dict = None) -> float:
        """Calculate length appropriateness score."""
        response_length = len(response)
        
        # Get user role for length preferences
        user_role = user_context.get('user_role', 'unknown') if user_context else 'unknown'
        
        # Role-based length preferences
        role_preferences = {
            'employer': {'min': 80, 'optimal_min': 120, 'optimal_max': 300, 'max': 500},
            'beneficiary': {'min': 50, 'optimal_min': 80, 'optimal_max': 200, 'max': 350},
            'employee': {'min': 40, 'optimal_min': 70, 'optimal_max': 180, 'max': 300},
            'stakeholder': {'min': 100, 'optimal_min': 150, 'optimal_max': 400, 'max': 600}
        }
        
        prefs = role_preferences.get(user_role, role_preferences['beneficiary'])
        
        if response_length < prefs['min']:
            return 0.3  # Too short
        elif response_length > prefs['max']:
            return 0.4  # Too long
        elif prefs['optimal_min'] <= response_length <= prefs['optimal_max']:
            return 1.0  # Optimal length
        else:
            return 0.7  # Acceptable length
    
    def _get_quality_grade(self, score: float) -> str:
        """Convert quality score to letter grade."""
        if score >= 0.9:
            return 'A+'
        elif score >= 0.8:
            return 'A'
        elif score >= 0.7:
            return 'B'
        elif score >= 0.6:
            return 'C'
        elif score >= 0.5:
            return 'D'
        else:
            return 'F'
    
    def _generate_improvement_suggestions(self, quality_factors: Dict) -> List[str]:
        """Generate specific improvement suggestions based on quality factors."""
        suggestions = []
        
        for factor, score in quality_factors.items():
            if score < 0.6:
                if factor == 'intent_alignment':
                    suggestions.append("Improve intent alignment by including more relevant keywords")
                elif factor == 'completeness':
                    suggestions.append("Provide more comprehensive information or reduce verbosity")
                elif factor == 'clarity':
                    suggestions.append("Improve clarity with shorter sentences and better structure")
                elif factor == 'empathy':
                    suggestions.append("Add more empathetic language and acknowledgment")
                elif factor == 'actionability':
                    suggestions.append("Include more specific action items and next steps")
                elif factor == 'length_appropriateness':
                    suggestions.append("Adjust response length to be more appropriate for the context")
        
        return suggestions

    def setup_ab_test(self, test_name: str, variant_a: Dict, variant_b: Dict,
                     target_metric: str = "user_satisfaction") -> Dict:
        """
        Set up an A/B test for response optimization.

        Args:
            test_name (str): Name of the A/B test
            variant_a (Dict): Configuration for variant A
            variant_b (Dict): Configuration for variant B
            target_metric (str): Metric to optimize for

        Returns:
            Dict: A/B test configuration
        """
        try:
            test_config = {
                "test_name": test_name,
                "start_date": now(),
                "status": "active",
                "target_metric": target_metric,
                "split_ratio": self.optimization_settings["ab_test_split_ratio"],
                "variants": {
                    "A": {
                        "config": variant_a,
                        "traffic_percentage": 50,
                        "metrics": {
                            "impressions": 0,
                            "conversions": 0,
                            "quality_scores": [],
                            "user_satisfaction": []
                        }
                    },
                    "B": {
                        "config": variant_b,
                        "traffic_percentage": 50,
                        "metrics": {
                            "impressions": 0,
                            "conversions": 0,
                            "quality_scores": [],
                            "user_satisfaction": []
                        }
                    }
                }
            }

            # Store A/B test configuration
            self.ab_test_variants[test_name] = test_config

            # Save to database
            self._save_ab_test_config(test_config)

            return {
                "status": "success",
                "test_id": test_name,
                "message": "A/B test configured successfully"
            }

        except Exception as e:
            logger.error(f"Error setting up A/B test: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to setup A/B test",
                "details": str(e)
            }

    def get_ab_test_variant(self, test_name: str, user_id: str, session_id: str) -> str:
        """
        Get A/B test variant for a user session.

        Args:
            test_name (str): Name of the A/B test
            user_id (str): User identifier
            session_id (str): Session identifier

        Returns:
            str: Variant identifier ('A' or 'B')
        """
        try:
            if test_name not in self.ab_test_variants:
                return 'A'  # Default to variant A if test not found

            test_config = self.ab_test_variants[test_name]

            if test_config["status"] != "active":
                return 'A'  # Default to variant A if test not active

            # Use consistent hashing to assign users to variants
            hash_input = f"{test_name}_{user_id}_{session_id}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

            # Determine variant based on split ratio
            split_ratio = test_config["split_ratio"]
            if (hash_value % 100) < (split_ratio * 100):
                return 'A'
            else:
                return 'B'

        except Exception as e:
            logger.error(f"Error getting A/B test variant: {str(e)}")
            return 'A'  # Default to variant A on error

    def record_ab_test_interaction(self, test_name: str, variant: str,
                                  quality_score: float, user_satisfaction: float = None,
                                  conversion: bool = False) -> Dict:
        """
        Record an interaction for A/B test analysis.

        Args:
            test_name (str): Name of the A/B test
            variant (str): Variant identifier
            quality_score (float): Response quality score
            user_satisfaction (float): User satisfaction score
            conversion (bool): Whether the interaction was successful

        Returns:
            Dict: Recording result
        """
        try:
            if test_name not in self.ab_test_variants:
                return {"status": "error", "message": "A/B test not found"}

            test_config = self.ab_test_variants[test_name]
            variant_data = test_config["variants"][variant]

            # Update metrics
            variant_data["metrics"]["impressions"] += 1
            variant_data["metrics"]["quality_scores"].append(quality_score)

            if user_satisfaction is not None:
                variant_data["metrics"]["user_satisfaction"].append(user_satisfaction)

            if conversion:
                variant_data["metrics"]["conversions"] += 1

            # Save updated metrics
            self._save_ab_test_metrics(test_name, variant, variant_data["metrics"])

            return {
                "status": "success",
                "message": "A/B test interaction recorded"
            }

        except Exception as e:
            logger.error(f"Error recording A/B test interaction: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to record interaction",
                "details": str(e)
            }

    def analyze_ab_test_results(self, test_name: str) -> Dict:
        """
        Analyze A/B test results and determine statistical significance.

        Args:
            test_name (str): Name of the A/B test

        Returns:
            Dict: Analysis results
        """
        try:
            if test_name not in self.ab_test_variants:
                return {"status": "error", "message": "A/B test not found"}

            test_config = self.ab_test_variants[test_name]
            variant_a = test_config["variants"]["A"]["metrics"]
            variant_b = test_config["variants"]["B"]["metrics"]

            # Calculate performance metrics
            results = {
                "test_name": test_name,
                "status": test_config["status"],
                "target_metric": test_config["target_metric"],
                "analysis_date": now(),
                "variants": {
                    "A": self._calculate_variant_performance(variant_a),
                    "B": self._calculate_variant_performance(variant_b)
                }
            }

            # Determine winner
            results["winner"] = self._determine_ab_test_winner(results["variants"])

            # Statistical significance
            results["statistical_significance"] = self._calculate_statistical_significance(
                variant_a, variant_b
            )

            # Recommendations
            results["recommendations"] = self._generate_ab_test_recommendations(results)

            return results

        except Exception as e:
            logger.error(f"Error analyzing A/B test results: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to analyze A/B test",
                "details": str(e)
            }

    def _calculate_variant_performance(self, metrics: Dict) -> Dict:
        """Calculate performance metrics for a variant."""
        impressions = metrics["impressions"]
        conversions = metrics["conversions"]
        quality_scores = metrics["quality_scores"]
        satisfaction_scores = metrics["user_satisfaction"]

        return {
            "impressions": impressions,
            "conversions": conversions,
            "conversion_rate": (conversions / impressions) if impressions > 0 else 0,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            "avg_satisfaction": sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
            "sample_size": len(quality_scores)
        }

    def _determine_ab_test_winner(self, variants: Dict) -> Dict:
        """Determine the winning variant based on target metrics."""
        variant_a = variants["A"]
        variant_b = variants["B"]

        # Compare based on multiple metrics
        a_score = (
            variant_a["avg_quality_score"] * 0.4 +
            variant_a["avg_satisfaction"] * 0.4 +
            variant_a["conversion_rate"] * 0.2
        )

        b_score = (
            variant_b["avg_quality_score"] * 0.4 +
            variant_b["avg_satisfaction"] * 0.4 +
            variant_b["conversion_rate"] * 0.2
        )

        if abs(a_score - b_score) < 0.05:  # Too close to call
            return {
                "winner": "inconclusive",
                "confidence": "low",
                "score_difference": abs(a_score - b_score)
            }
        elif a_score > b_score:
            return {
                "winner": "A",
                "confidence": "high" if (a_score - b_score) > 0.1 else "medium",
                "score_difference": a_score - b_score
            }
        else:
            return {
                "winner": "B",
                "confidence": "high" if (b_score - a_score) > 0.1 else "medium",
                "score_difference": b_score - a_score
            }

    def _calculate_statistical_significance(self, variant_a: Dict, variant_b: Dict) -> Dict:
        """Calculate statistical significance of A/B test results."""
        # Simple statistical significance calculation
        # In production, would use proper statistical tests

        a_sample_size = len(variant_a.get("quality_scores", []))
        b_sample_size = len(variant_b.get("quality_scores", []))

        min_sample_size = self.optimization_settings["min_samples_for_optimization"]

        if a_sample_size < min_sample_size or b_sample_size < min_sample_size:
            return {
                "significant": False,
                "confidence_level": 0,
                "p_value": 1.0,
                "message": f"Insufficient sample size (need {min_sample_size} minimum)"
            }

        # Simplified significance calculation
        # In production, would use proper t-test or chi-square test
        total_samples = a_sample_size + b_sample_size
        confidence_level = min(95, (total_samples / min_sample_size) * 50)

        return {
            "significant": confidence_level >= 80,
            "confidence_level": confidence_level,
            "p_value": max(0.01, 1 - (confidence_level / 100)),
            "sample_sizes": {"A": a_sample_size, "B": b_sample_size}
        }

    def _generate_ab_test_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on A/B test results."""
        recommendations = []

        winner = results["winner"]
        significance = results["statistical_significance"]

        if not significance["significant"]:
            recommendations.append("Continue test - insufficient data for statistical significance")
            recommendations.append(f"Need at least {significance.get('message', 'more samples')}")

        elif winner["winner"] == "inconclusive":
            recommendations.append("Results are too close to determine a clear winner")
            recommendations.append("Consider testing more distinct variants")

        elif winner["confidence"] == "high":
            recommendations.append(f"Implement variant {winner['winner']} - high confidence winner")
            recommendations.append("Monitor performance after implementation")

        else:
            recommendations.append(f"Variant {winner['winner']} shows promise but continue testing")
            recommendations.append("Gather more data before making final decision")

        return recommendations

    def _save_ab_test_config(self, test_config: Dict):
        """Save A/B test configuration to database."""
        try:
            # Create or update A/B test record
            test_doc = frappe.new_doc("Response Optimization Test")
            test_doc.test_name = test_config["test_name"]
            test_doc.start_date = test_config["start_date"]
            test_doc.status = test_config["status"]
            test_doc.target_metric = test_config["target_metric"]
            test_doc.test_config = json.dumps(test_config)
            test_doc.insert()
            frappe.db.commit()

        except Exception as e:
            logger.error(f"Error saving A/B test config: {str(e)}")

    def _save_ab_test_metrics(self, test_name: str, variant: str, metrics: Dict):
        """Save A/B test metrics to database."""
        try:
            # Create metrics record
            metrics_doc = frappe.new_doc("Response Optimization Metric")
            metrics_doc.test_name = test_name
            metrics_doc.variant = variant
            metrics_doc.timestamp = now()
            metrics_doc.metrics_data = json.dumps(metrics)
            metrics_doc.insert()
            frappe.db.commit()

        except Exception as e:
            logger.error(f"Error saving A/B test metrics: {str(e)}")

    def optimize_response_templates(self, intent: str, user_role: str) -> Dict:
        """
        Optimize response templates based on historical performance data.

        Args:
            intent (str): Intent to optimize for
            user_role (str): User role to optimize for

        Returns:
            Dict: Optimization results and recommendations
        """
        try:
            # Get historical performance data
            performance_data = self._get_historical_performance(intent, user_role)

            if not performance_data:
                return {
                    "status": "insufficient_data",
                    "message": "Not enough historical data for optimization"
                }

            # Analyze patterns in high-performing responses
            optimization_insights = self._analyze_performance_patterns(performance_data)

            # Generate optimized template suggestions
            template_suggestions = self._generate_template_optimizations(
                intent, user_role, optimization_insights
            )

            return {
                "status": "success",
                "intent": intent,
                "user_role": user_role,
                "optimization_insights": optimization_insights,
                "template_suggestions": template_suggestions,
                "performance_data_size": len(performance_data)
            }

        except Exception as e:
            logger.error(f"Error optimizing response templates: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to optimize templates",
                "details": str(e)
            }

    def _get_historical_performance(self, intent: str, user_role: str) -> List[Dict]:
        """Get historical performance data for intent and user role."""
        try:
            # Get conversation turns with quality scores
            filters = {
                "intent": intent,
                "response_quality_score": [">", 0]
            }

            turns = frappe.get_all("Conversation Turn",
                filters=filters,
                fields=["*"],
                order_by="timestamp desc",
                limit=200
            )

            # Filter by user role if available
            filtered_turns = []
            for turn in turns:
                try:
                    context_data = json.loads(turn.context_data) if turn.context_data else {}
                    if context_data.get("user_role") == user_role:
                        filtered_turns.append(turn)
                except:
                    continue

            return filtered_turns

        except Exception as e:
            logger.error(f"Error getting historical performance: {str(e)}")
            return []

    def _analyze_performance_patterns(self, performance_data: List[Dict]) -> Dict:
        """Analyze patterns in high-performing responses."""
        if not performance_data:
            return {}

        # Sort by quality score
        sorted_data = sorted(performance_data, key=lambda x: x.response_quality_score or 0, reverse=True)

        # Analyze top 25% of responses
        top_quartile_size = max(1, len(sorted_data) // 4)
        top_responses = sorted_data[:top_quartile_size]

        patterns = {
            "avg_length": sum(len(r.bot_response) for r in top_responses) / len(top_responses),
            "common_phrases": self._extract_common_phrases(top_responses),
            "avg_quality_score": sum(r.response_quality_score for r in top_responses) / len(top_responses),
            "response_structures": self._analyze_response_structures(top_responses)
        }

        return patterns

    def _extract_common_phrases(self, responses: List[Dict]) -> List[str]:
        """Extract common phrases from high-performing responses."""
        # Simple phrase extraction (in production, would use NLP)
        phrase_counts = {}

        for response in responses:
            text = response.bot_response.lower()
            # Extract 2-3 word phrases
            words = text.split()
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

        # Return most common phrases
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        return [phrase for phrase, count in sorted_phrases[:10] if count > 1]

    def _analyze_response_structures(self, responses: List[Dict]) -> Dict:
        """Analyze structural patterns in responses."""
        structures = {
            "has_questions": 0,
            "has_bullet_points": 0,
            "has_numbered_lists": 0,
            "starts_with_greeting": 0,
            "ends_with_offer": 0
        }

        for response in responses:
            text = response.bot_response

            if "?" in text:
                structures["has_questions"] += 1
            if "•" in text or "\n-" in text:
                structures["has_bullet_points"] += 1
            if any(f"{i}." in text for i in range(1, 6)):
                structures["has_numbered_lists"] += 1
            if any(text.lower().startswith(greeting) for greeting in ["hello", "hi", "good"]):
                structures["starts_with_greeting"] += 1
            if any(text.lower().endswith(offer) for offer in ["help?", "assist?", "support?"]):
                structures["ends_with_offer"] += 1

        # Convert to percentages
        total = len(responses)
        return {k: (v / total) * 100 for k, v in structures.items()}

    def _generate_template_optimizations(self, intent: str, user_role: str, insights: Dict) -> List[str]:
        """Generate template optimization suggestions."""
        suggestions = []

        if insights.get("avg_length"):
            suggestions.append(f"Optimal response length: ~{int(insights['avg_length'])} characters")

        if insights.get("common_phrases"):
            suggestions.append(f"Include high-performing phrases: {', '.join(insights['common_phrases'][:3])}")

        structures = insights.get("response_structures", {})
        if structures.get("has_questions", 0) > 50:
            suggestions.append("Include clarifying questions to improve engagement")

        if structures.get("has_bullet_points", 0) > 40:
            suggestions.append("Use bullet points for better readability")

        if structures.get("starts_with_greeting", 0) > 60:
            suggestions.append("Start responses with appropriate greetings")

        return suggestions

    # Phase 2 Enhancement Methods
    def optimize_response_verbosity(self, response: str, target_level: str = 'moderate',
                                  user_context: Dict = None) -> Dict[str, Any]:
        """
        Optimize response to avoid verbosity while maintaining clarity

        Args:
            response: Original response text
            target_level: Target verbosity level (concise, moderate, detailed, comprehensive)
            user_context: User context for personalization

        Returns:
            Dict containing optimized response and analysis
        """
        try:
            # Analyze current response
            analysis = self._analyze_response_verbosity(response)

            # Determine optimal verbosity level based on context
            if user_context:
                target_level = self._determine_optimal_verbosity(user_context, analysis)

            # Apply verbosity optimization
            optimized_response = self._apply_verbosity_optimization(response, target_level, analysis)

            # Improve clarity
            clarity_improved = self._improve_response_clarity(optimized_response)

            # Final quality check
            quality_score = self._calculate_clarity_improvement_score(clarity_improved, response)

            return {
                'success': True,
                'original_response': response,
                'optimized_response': clarity_improved,
                'target_level': target_level,
                'verbosity_analysis': analysis,
                'quality_improvement': quality_score,
                'optimization_applied': True,
                'timestamp': now()
            }

        except Exception as e:
            frappe.log_error(f"Response verbosity optimization error: {str(e)}", "ResponseOptimizationManager")
            return {
                'success': False,
                'error': str(e),
                'original_response': response,
                'optimized_response': response,
                'optimization_applied': False
            }

    def _analyze_response_verbosity(self, response: str) -> Dict[str, Any]:
        """Analyze response verbosity metrics"""
        import re

        # Basic metrics
        word_count = len(response.split())
        sentence_count = len(re.split(r'[.!?]+', response.strip()))
        char_count = len(response)

        # Advanced metrics
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        complex_words = len([word for word in response.split() if len(word) > 7])
        redundant_phrases = sum(1 for pattern in self.clarity_patterns['remove_redundancy']
                               if re.search(pattern, response, re.IGNORECASE))

        # Determine current verbosity level
        current_level = 'comprehensive'
        for level, thresholds in self.verbosity_thresholds.items():
            if (word_count <= thresholds['max_words'] and
                sentence_count <= thresholds['max_sentences']):
                current_level = level
                break

        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'char_count': char_count,
            'avg_words_per_sentence': avg_words_per_sentence,
            'complex_words': complex_words,
            'redundant_phrases': redundant_phrases,
            'current_level': current_level,
            'readability_score': self._calculate_readability_score(response)
        }

    def _determine_optimal_verbosity(self, user_context: Dict, analysis: Dict) -> str:
        """Determine optimal verbosity level based on user context"""

        # Default to moderate
        optimal_level = 'moderate'

        # Adjust based on user persona
        persona = user_context.get('persona', 'general')
        if persona == 'beneficiary':
            optimal_level = 'concise'  # Beneficiaries prefer simple, direct answers
        elif persona == 'employer':
            optimal_level = 'detailed'  # Employers may need more comprehensive information
        elif persona == 'wcfcb_staff':
            optimal_level = 'comprehensive'  # Staff may need full details

        # Adjust based on urgency
        if user_context.get('urgency') == 'high':
            optimal_level = 'concise'

        # Adjust based on user engagement level
        engagement = user_context.get('engagement_level', 'medium')
        if engagement == 'low':
            optimal_level = 'concise'
        elif engagement == 'high':
            optimal_level = 'detailed'

        return optimal_level

    def _apply_verbosity_optimization(self, response: str, target_level: str, analysis: Dict) -> str:
        """Apply verbosity optimization to response"""
        import re

        target_thresholds = self.verbosity_thresholds[target_level]
        current_words = analysis['word_count']
        target_words = target_thresholds['max_words']

        # If already within target, return as is
        if current_words <= target_words:
            return response

        # Split into sentences
        sentences = re.split(r'[.!?]+', response.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        # Prioritize sentences by importance
        prioritized_sentences = self._prioritize_sentences(sentences)

        # Build optimized response within word limit
        optimized_sentences = []
        word_count = 0

        for sentence in prioritized_sentences:
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= target_words:
                optimized_sentences.append(sentence)
                word_count += sentence_words
            else:
                break

        # Ensure we have at least one sentence
        if not optimized_sentences and prioritized_sentences:
            # Take the first sentence and truncate if necessary
            first_sentence = prioritized_sentences[0]
            words = first_sentence.split()
            if len(words) > target_words:
                optimized_sentences = [' '.join(words[:target_words]) + '...']
            else:
                optimized_sentences = [first_sentence]

        return '. '.join(optimized_sentences) + '.'

    def _prioritize_sentences(self, sentences: List[str]) -> List[str]:
        """Prioritize sentences by importance for verbosity optimization"""

        # Importance indicators
        importance_keywords = [
            'important', 'key', 'main', 'primary', 'essential', 'critical',
            'first', 'step', 'process', 'required', 'must', 'need'
        ]

        question_indicators = ['?', 'how', 'what', 'when', 'where', 'why']
        action_indicators = ['please', 'click', 'visit', 'contact', 'submit', 'complete']

        scored_sentences = []

        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()

            # Score based on importance keywords
            score += sum(2 for keyword in importance_keywords if keyword in sentence_lower)

            # Score based on questions (usually important)
            score += sum(1 for indicator in question_indicators if indicator in sentence_lower)

            # Score based on action items
            score += sum(3 for indicator in action_indicators if indicator in sentence_lower)

            # Prefer shorter sentences for clarity
            word_count = len(sentence.split())
            if word_count <= 15:
                score += 1

            # Prefer sentences at the beginning (usually more important)
            position_bonus = max(0, 3 - sentences.index(sentence))
            score += position_bonus

            scored_sentences.append((sentence, score))

        # Sort by score (descending) and return sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [sentence for sentence, score in scored_sentences]

    def _improve_response_clarity(self, response: str) -> str:
        """Improve response clarity by removing redundancy and simplifying language"""
        import re

        improved_response = response

        # Remove redundant phrases
        for pattern in self.clarity_patterns['remove_redundancy']:
            improved_response = re.sub(pattern, '', improved_response, flags=re.IGNORECASE)

        # Simplify language
        for complex_word, simple_word in self.clarity_patterns['simplify_language']:
            improved_response = re.sub(r'\b' + complex_word + r'\b', simple_word,
                                     improved_response, flags=re.IGNORECASE)

        # Clean up extra spaces
        improved_response = re.sub(r'\s+', ' ', improved_response).strip()

        return improved_response

    def _calculate_readability_score(self, text: str) -> float:
        """Calculate a simple readability score"""
        import re

        # Simple readability based on sentence length and word complexity
        sentences = re.split(r'[.!?]+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        total_words = len(text.split())
        avg_sentence_length = total_words / len(sentences)

        # Count complex words (more than 6 characters)
        complex_words = len([word for word in text.split() if len(word) > 6])
        complex_word_ratio = complex_words / max(total_words, 1)

        # Simple readability score (higher is more readable)
        readability = max(0, 1.0 - (avg_sentence_length / 20) - complex_word_ratio)

        return min(readability, 1.0)

    def _calculate_clarity_improvement_score(self, optimized_response: str, original_response: str) -> Dict[str, float]:
        """Calculate clarity improvement score between original and optimized responses"""

        original_analysis = self._analyze_response_verbosity(original_response)
        optimized_analysis = self._analyze_response_verbosity(optimized_response)

        # Calculate improvements
        word_reduction = (original_analysis['word_count'] - optimized_analysis['word_count']) / max(original_analysis['word_count'], 1)
        readability_improvement = optimized_analysis['readability_score'] - original_analysis['readability_score']
        redundancy_reduction = (original_analysis['redundant_phrases'] - optimized_analysis['redundant_phrases']) / max(original_analysis['redundant_phrases'], 1)

        overall_improvement = (word_reduction + readability_improvement + redundancy_reduction) / 3

        return {
            'word_reduction': word_reduction,
            'readability_improvement': readability_improvement,
            'redundancy_reduction': redundancy_reduction,
            'overall_improvement': overall_improvement,
            'clarity_score': optimized_analysis['readability_score']
        }


# Utility functions for integration

def get_response_optimization_manager() -> ResponseOptimizationManager:
    """Get response optimization manager instance."""
    return ResponseOptimizationManager()


def calculate_response_quality(response: str, user_message: str, intent: str,
                             confidence: float, user_context: Dict = None) -> Dict:
    """
    Calculate response quality score.

    Args:
        response (str): Generated response
        user_message (str): Original user message
        intent (str): Detected intent
        confidence (float): Intent confidence
        user_context (Dict): User context

    Returns:
        Dict: Quality score and analysis
    """
    optimizer = get_response_optimization_manager()
    return optimizer.calculate_response_quality_score(
        response, user_message, intent, confidence, user_context
    )


def optimize_response_for_user(response: str, user_context: Dict,
                              quality_score: Dict = None) -> str:
    """
    Optimize response based on user context and quality analysis.

    Args:
        response (str): Original response
        user_context (Dict): User context information
        quality_score (Dict): Quality score analysis

    Returns:
        str: Optimized response
    """
    if not quality_score or quality_score.get("overall_score", 1.0) > 0.8:
        return response  # Response is already high quality

    # Apply optimizations based on quality factors
    optimized_response = response

    improvement_suggestions = quality_score.get("improvement_suggestions", [])

    for suggestion in improvement_suggestions:
        if "empathetic language" in suggestion.lower():
            if not any(phrase in optimized_response.lower() for phrase in ["i understand", "i know"]):
                optimized_response = "I understand your concern. " + optimized_response

        elif "action items" in suggestion.lower():
            if "?" not in optimized_response:
                optimized_response += " Is there anything specific I can help you with?"

        elif "clarity" in suggestion.lower():
            # Add structure if missing
            if len(optimized_response) > 200 and "\n" not in optimized_response:
                # Split into paragraphs for better readability
                sentences = optimized_response.split(". ")
                if len(sentences) > 2:
                    mid_point = len(sentences) // 2
                    optimized_response = ". ".join(sentences[:mid_point]) + ".\n\n" + ". ".join(sentences[mid_point:])

    return optimized_response


