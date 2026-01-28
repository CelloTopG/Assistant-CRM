import frappe
from frappe import _
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional, Tuple
from assistant_crm.services.performance_tracking_service import PerformanceTrackingService


class AgentSkillMatchingService:
    """Advanced agent skill profiling and matching system for optimal conversation routing"""
    
    def __init__(self):
        self.performance_tracker = PerformanceTrackingService()
        self.skill_weights = self.load_skill_weights()
        self.availability_cache = {}
    
    def load_skill_weights(self) -> Dict[str, float]:
        """Load skill importance weights for different conversation types"""
        return {
            'payments': 1.0,
            'claims': 1.0,
            'registration': 0.8,
            'compliance': 0.9,
            'crisis_management': 1.2,
            'conflict_resolution': 1.1,
            'de_escalation': 1.2,
            'empathy': 0.9,
            'patience': 0.8,
            'explanation': 0.7,
            'multilingual': 0.9,
            'technical_support': 0.8,
            'senior_level': 1.1,
            'trainee': 0.5
        }
    
    def find_best_agent(self, required_skills: List[str], avoid_skills: List[str] = None,
                       priority_score: int = 50, customer_language: str = 'en') -> Optional[Dict[str, Any]]:
        """Find the best available agent based on skills, availability, and workload"""
        try:
            # Get all available agents
            available_agents = self.get_available_agents()
            
            if not available_agents:
                return None
            
            # Score each agent
            agent_scores = []
            for agent in available_agents:
                score = self.calculate_agent_score(
                    agent, required_skills, avoid_skills, priority_score, customer_language
                )
                if score > 0:  # Only consider agents with positive scores
                    agent_scores.append({
                        'agent': agent,
                        'score': score,
                        'match_details': self.get_match_details(agent, required_skills)
                    })
            
            # Sort by score (highest first)
            agent_scores.sort(key=lambda x: x['score'], reverse=True)
            
            if agent_scores:
                best_match = agent_scores[0]
                
                # Update agent workload
                self.update_agent_workload(best_match['agent']['user_id'])
                
                return {
                    'agent_id': best_match['agent']['user_id'],
                    'agent_name': best_match['agent']['full_name'],
                    'match_score': best_match['score'],
                    'match_details': best_match['match_details'],
                    'estimated_response_time': self.estimate_response_time(best_match['agent']),
                    'agent_skills': best_match['agent']['skills'],
                    'current_workload': best_match['agent']['current_workload']
                }
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Error finding best agent: {str(e)}", "Agent Skill Matching")
            return None
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of currently available agents with their skills and workload"""
        try:
            # Get agents who are online and available
            agents = frappe.db.sql("""
                SELECT u.name as user_id, u.full_name, u.email,
                       ap.skills, ap.languages, ap.experience_level,
                       ap.max_concurrent_conversations, ap.current_workload,
                       ap.availability_status, ap.last_activity
                FROM `tabUser` u
                LEFT JOIN `tabAgent Profile` ap ON u.name = ap.user
                WHERE u.enabled = 1 
                AND ap.availability_status = 'Available'
                AND ap.last_activity >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
                ORDER BY ap.current_workload ASC, ap.last_activity DESC
            """, as_dict=True)
            
            # Process and enhance agent data
            enhanced_agents = []
            for agent in agents:
                try:
                    # Parse skills JSON
                    agent['skills'] = json.loads(agent.get('skills', '[]')) if agent.get('skills') else []
                    agent['languages'] = json.loads(agent.get('languages', '["en"]')) if agent.get('languages') else ['en']
                    
                    # Get recent performance metrics
                    agent['performance_metrics'] = self.get_agent_performance_metrics(agent['user_id'])
                    
                    # Check if agent is truly available (not at max capacity)
                    if agent['current_workload'] < agent['max_concurrent_conversations']:
                        enhanced_agents.append(agent)
                        
                except Exception as e:
                    frappe.log_error(f"Error processing agent {agent.get('user_id')}: {str(e)}")
                    continue
            
            return enhanced_agents
            
        except Exception as e:
            frappe.log_error(f"Error getting available agents: {str(e)}")
            return []
    
    def calculate_agent_score(self, agent: Dict[str, Any], required_skills: List[str],
                            avoid_skills: List[str], priority_score: int, customer_language: str) -> float:
        """Calculate comprehensive agent matching score"""
        try:
            total_score = 0.0
            
            # 1. Skill matching score (40% weight)
            skill_score = self.calculate_skill_score(agent['skills'], required_skills, avoid_skills)
            total_score += skill_score * 0.4
            
            # 2. Language matching score (15% weight)
            language_score = self.calculate_language_score(agent['languages'], customer_language)
            total_score += language_score * 0.15
            
            # 3. Performance score (25% weight)
            performance_score = self.calculate_performance_score(agent['performance_metrics'])
            total_score += performance_score * 0.25
            
            # 4. Availability/workload score (15% weight)
            availability_score = self.calculate_availability_score(agent)
            total_score += availability_score * 0.15
            
            # 5. Experience level bonus (5% weight)
            experience_score = self.calculate_experience_score(agent['experience_level'])
            total_score += experience_score * 0.05
            
            # Apply priority adjustments
            if priority_score > 80:  # High priority conversations
                # Prefer senior agents for high priority
                if agent['experience_level'] in ['Senior', 'Expert']:
                    total_score *= 1.2
                # Penalize overloaded agents more heavily
                if agent['current_workload'] > agent['max_concurrent_conversations'] * 0.8:
                    total_score *= 0.7
            
            return round(total_score, 2)
            
        except Exception as e:
            frappe.log_error(f"Error calculating agent score: {str(e)}")
            return 0.0
    
    def calculate_skill_score(self, agent_skills: List[str], required_skills: List[str],
                            avoid_skills: List[str]) -> float:
        """Calculate skill matching score"""
        try:
            if not required_skills:
                return 80.0  # Default score if no specific skills required
            
            # Check for avoided skills
            if avoid_skills:
                for avoid_skill in avoid_skills:
                    if avoid_skill in agent_skills:
                        return 0.0  # Disqualify agent if they have avoided skills
            
            # Calculate skill match percentage
            matched_skills = 0
            weighted_score = 0.0
            
            for skill in required_skills:
                if skill in agent_skills:
                    matched_skills += 1
                    # Apply skill weight
                    weight = self.skill_weights.get(skill, 1.0)
                    weighted_score += weight
            
            if matched_skills == 0:
                return 20.0  # Low score if no skills match
            
            # Calculate percentage with weights
            max_possible_score = sum(self.skill_weights.get(skill, 1.0) for skill in required_skills)
            skill_percentage = (weighted_score / max_possible_score) * 100
            
            # Bonus for having all required skills
            if matched_skills == len(required_skills):
                skill_percentage *= 1.1
            
            return min(skill_percentage, 100.0)
            
        except Exception as e:
            frappe.log_error(f"Error calculating skill score: {str(e)}")
            return 50.0
    
    def calculate_language_score(self, agent_languages: List[str], customer_language: str) -> float:
        """Calculate language matching score"""
        try:
            if customer_language in agent_languages:
                return 100.0
            elif 'en' in agent_languages:  # English as fallback
                return 70.0
            else:
                return 30.0  # Can still handle with translation
                
        except Exception as e:
            frappe.log_error(f"Error calculating language score: {str(e)}")
            return 50.0
    
    def calculate_performance_score(self, performance_metrics: Dict[str, Any]) -> float:
        """Calculate performance-based score"""
        try:
            if not performance_metrics:
                return 70.0  # Default score for new agents
            
            # Weighted performance factors
            factors = {
                'customer_satisfaction_score': 0.3,
                'average_response_time_score': 0.25,
                'resolution_rate': 0.25,
                'sla_compliance_rate': 0.2
            }
            
            total_score = 0.0
            for factor, weight in factors.items():
                score = performance_metrics.get(factor, 70.0)
                total_score += score * weight
            
            return min(total_score, 100.0)
            
        except Exception as e:
            frappe.log_error(f"Error calculating performance score: {str(e)}")
            return 70.0
    
    def calculate_availability_score(self, agent: Dict[str, Any]) -> float:
        """Calculate availability/workload score"""
        try:
            max_conversations = agent['max_concurrent_conversations']
            current_workload = agent['current_workload']
            
            if current_workload >= max_conversations:
                return 0.0  # Agent at capacity
            
            # Calculate workload percentage
            workload_percentage = (current_workload / max_conversations) * 100
            
            # Invert the score (lower workload = higher score)
            availability_score = 100 - workload_percentage
            
            return availability_score
            
        except Exception as e:
            frappe.log_error(f"Error calculating availability score: {str(e)}")
            return 50.0
    
    def calculate_experience_score(self, experience_level: str) -> float:
        """Calculate experience level score"""
        experience_scores = {
            'Expert': 100.0,
            'Senior': 90.0,
            'Intermediate': 75.0,
            'Junior': 60.0,
            'Trainee': 40.0
        }
        return experience_scores.get(experience_level, 70.0)
    
    def get_agent_performance_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get recent performance metrics for an agent"""
        try:
            # Get last 30 days performance
            end_date = frappe.utils.today()
            start_date = frappe.utils.add_days(end_date, -30)
            
            metrics = self.performance_tracker.calculate_agent_metrics(agent_id, start_date)
            
            if metrics:
                # Convert to scores (0-100)
                return {
                    'customer_satisfaction_score': min(metrics.get('customer_satisfaction_score', 3.5) * 20, 100),
                    'average_response_time_score': self.convert_response_time_to_score(metrics.get('average_response_time', 300)),
                    'resolution_rate': metrics.get('resolution_rate', 80.0),
                    'sla_compliance_rate': metrics.get('sla_compliance_rate', 85.0)
                }
            else:
                return {}
                
        except Exception as e:
            frappe.log_error(f"Error getting agent performance metrics: {str(e)}")
            return {}
    
    def convert_response_time_to_score(self, response_time_seconds: float) -> float:
        """Convert response time to score (0-100)"""
        # Excellent: < 60 seconds = 100 points
        # Good: 60-300 seconds = 80-99 points
        # Average: 300-600 seconds = 60-79 points
        # Poor: > 600 seconds = 0-59 points
        
        if response_time_seconds <= 60:
            return 100.0
        elif response_time_seconds <= 300:
            return 80 + (240 - (response_time_seconds - 60)) / 240 * 19
        elif response_time_seconds <= 600:
            return 60 + (300 - (response_time_seconds - 300)) / 300 * 19
        else:
            return max(0, 60 - (response_time_seconds - 600) / 60)
    
    def get_match_details(self, agent: Dict[str, Any], required_skills: List[str]) -> Dict[str, Any]:
        """Get detailed matching information"""
        try:
            matched_skills = [skill for skill in required_skills if skill in agent['skills']]
            missing_skills = [skill for skill in required_skills if skill not in agent['skills']]
            
            return {
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'skill_match_percentage': (len(matched_skills) / len(required_skills) * 100) if required_skills else 100,
                'agent_experience': agent['experience_level'],
                'current_workload': f"{agent['current_workload']}/{agent['max_concurrent_conversations']}",
                'languages': agent['languages']
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting match details: {str(e)}")
            return {}
    
    def estimate_response_time(self, agent: Dict[str, Any]) -> str:
        """Estimate response time based on agent workload and performance"""
        try:
            base_time = 5  # Base 5 minutes
            
            # Adjust for workload
            workload_factor = agent['current_workload'] / agent['max_concurrent_conversations']
            workload_adjustment = workload_factor * 10  # Up to 10 minutes additional
            
            # Adjust for performance
            performance_metrics = agent.get('performance_metrics', {})
            avg_response_score = performance_metrics.get('average_response_time_score', 70)
            
            if avg_response_score > 90:
                performance_adjustment = -2  # Fast responder
            elif avg_response_score < 50:
                performance_adjustment = 5   # Slower responder
            else:
                performance_adjustment = 0
            
            total_minutes = base_time + workload_adjustment + performance_adjustment
            total_minutes = max(1, min(total_minutes, 30))  # Cap between 1-30 minutes
            
            return f"{int(total_minutes)} minutes"
            
        except Exception as e:
            frappe.log_error(f"Error estimating response time: {str(e)}")
            return "5 minutes"
    
    def update_agent_workload(self, agent_id: str) -> None:
        """Update agent's current workload"""
        try:
            frappe.db.sql("""
                UPDATE `tabAgent Profile`
                SET current_workload = current_workload + 1,
                    last_assignment = NOW()
                WHERE user = %s
            """, (agent_id,))
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error updating agent workload: {str(e)}")
    
    def release_agent_workload(self, agent_id: str) -> None:
        """Release one conversation from agent's workload"""
        try:
            frappe.db.sql("""
                UPDATE `tabAgent Profile`
                SET current_workload = GREATEST(current_workload - 1, 0)
                WHERE user = %s
            """, (agent_id,))
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error releasing agent workload: {str(e)}")
