import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from assistant_crm.services.omnichannel_router import OmnichannelRouter
from assistant_crm.services.agent_skill_matching_service import AgentSkillMatchingService
from assistant_crm.services.sentiment_analysis_service import SentimentAnalysisService


@frappe.whitelist(allow_guest=False)
def route_conversation_smart(conversation_id, message_content, customer_data=None):
    """Smart route conversation using AI-powered analysis"""
    try:
        # Parse customer data if it's a string
        if isinstance(customer_data, str):
            customer_data = json.loads(customer_data)
        
        router = OmnichannelRouter()
        result = router.smart_route_conversation(conversation_id, message_content, customer_data)
        
        return {
            'success': result.get('success', False),
            'routing_result': result,
            'message': result.get('message', 'Routing completed')
        }
        
    except Exception as e:
        frappe.log_error(f"Error in smart routing API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to route conversation'
        }


@frappe.whitelist(allow_guest=False)
def get_available_agents(required_skills=None, customer_language='en'):
    """Get list of available agents with skill matching"""
    try:
        # Parse required skills if it's a string
        if isinstance(required_skills, str):
            required_skills = json.loads(required_skills) if required_skills else []
        
        agent_matching = AgentSkillMatchingService()
        available_agents = agent_matching.get_available_agents()
        
        # Filter and score agents if skills are specified
        if required_skills:
            scored_agents = []
            for agent in available_agents:
                score = agent_matching.calculate_agent_score(
                    agent, required_skills, [], 50, customer_language
                )
                if score > 0:
                    agent['match_score'] = score
                    agent['match_details'] = agent_matching.get_match_details(agent, required_skills)
                    scored_agents.append(agent)
            
            # Sort by score
            scored_agents.sort(key=lambda x: x['match_score'], reverse=True)
            available_agents = scored_agents
        
        return {
            'success': True,
            'agents': available_agents,
            'total_available': len(available_agents),
            'filters_applied': {
                'required_skills': required_skills,
                'customer_language': customer_language
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting available agents: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'agents': []
        }


@frappe.whitelist(allow_guest=False)
def analyze_message_for_routing(message_content, customer_data=None):
    """Analyze message content for routing recommendations"""
    try:
        # Parse customer data if it's a string
        if isinstance(customer_data, str):
            customer_data = json.loads(customer_data) if customer_data else None
        
        sentiment_service = SentimentAnalysisService()
        analysis = sentiment_service.get_comprehensive_analysis(message_content, customer_data)
        
        return {
            'success': True,
            'analysis': analysis,
            'routing_recommendation': analysis.get('routing_recommendation', {}),
            'message': 'Message analysis completed'
        }
        
    except Exception as e:
        frappe.log_error(f"Error analyzing message for routing: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'analysis': {}
        }


@frappe.whitelist(allow_guest=False)
def get_routing_analytics(period='today', agent_id=None):
    """Get comprehensive routing analytics"""
    try:
        # Calculate date range
        if period == 'today':
            start_date = end_date = frappe.utils.today()
        elif period == 'week':
            start_date = frappe.utils.add_days(frappe.utils.today(), -7)
            end_date = frappe.utils.today()
        elif period == 'month':
            start_date = frappe.utils.add_days(frappe.utils.today(), -30)
            end_date = frappe.utils.today()
        else:
            start_date = end_date = frappe.utils.today()
        
        # Get routing statistics
        routing_stats = get_routing_statistics(start_date, end_date, agent_id)
        
        # Get agent performance
        agent_performance = get_agent_routing_performance(start_date, end_date, agent_id)
        
        # Get routing efficiency metrics
        efficiency_metrics = get_routing_efficiency_metrics(start_date, end_date)
        
        # Get real-time status
        realtime_status = get_realtime_routing_status()
        
        return {
            'success': True,
            'period': period,
            'date_range': {'start': start_date, 'end': end_date},
            'routing_statistics': routing_stats,
            'agent_performance': agent_performance,
            'efficiency_metrics': efficiency_metrics,
            'realtime_status': realtime_status
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting routing analytics: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load routing analytics'
        }


@frappe.whitelist(allow_guest=False)
def update_agent_availability(agent_id, availability_status, max_concurrent=None):
    """Update agent availability and capacity"""
    try:
        # Validate availability status
        valid_statuses = ['Available', 'Busy', 'Away', 'Offline']
        if availability_status not in valid_statuses:
            return {
                'success': False,
                'error': f'Invalid availability status. Must be one of: {valid_statuses}'
            }
        
        # Update agent profile
        update_data = {
            'availability_status': availability_status,
            'last_activity': frappe.utils.now()
        }
        
        if max_concurrent is not None:
            update_data['max_concurrent_conversations'] = max_concurrent
        
        # Check if agent profile exists
        if frappe.db.exists('Agent Profile', {'user': agent_id}):
            frappe.db.set_value('Agent Profile', {'user': agent_id}, update_data)
        else:
            # Create new agent profile
            agent_profile = frappe.get_doc({
                'doctype': 'Agent Profile',
                'user': agent_id,
                'skills': json.dumps(['standard']),
                'languages': json.dumps(['en']),
                'experience_level': 'Intermediate',
                'max_concurrent_conversations': max_concurrent or 5,
                'current_workload': 0,
                **update_data
            })
            agent_profile.insert()
        
        return {
            'success': True,
            'agent_id': agent_id,
            'availability_status': availability_status,
            'message': f'Agent availability updated to {availability_status}'
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating agent availability: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to update availability for agent {agent_id}'
        }


@frappe.whitelist(allow_guest=False)
def get_agent_workload_status(agent_id=None):
    """Get current workload status for agents"""
    try:
        if agent_id:
            # Get specific agent workload
            agent_data = frappe.db.sql("""
                SELECT user as agent_id, full_name, availability_status,
                       current_workload, max_concurrent_conversations,
                       last_activity
                FROM `tabAgent Profile` ap
                LEFT JOIN `tabUser` u ON ap.user = u.name
                WHERE ap.user = %s
            """, (agent_id,), as_dict=True)
        else:
            # Get all agents workload
            agent_data = frappe.db.sql("""
                SELECT user as agent_id, full_name, availability_status,
                       current_workload, max_concurrent_conversations,
                       last_activity
                FROM `tabAgent Profile` ap
                LEFT JOIN `tabUser` u ON ap.user = u.name
                WHERE u.enabled = 1
                ORDER BY current_workload ASC
            """, as_dict=True)
        
        # Calculate workload percentages and status
        for agent in agent_data:
            if agent['max_concurrent_conversations'] > 0:
                workload_percentage = (agent['current_workload'] / agent['max_concurrent_conversations']) * 100
                agent['workload_percentage'] = round(workload_percentage, 1)
                
                if workload_percentage >= 100:
                    agent['workload_status'] = 'At Capacity'
                elif workload_percentage >= 80:
                    agent['workload_status'] = 'High Load'
                elif workload_percentage >= 50:
                    agent['workload_status'] = 'Moderate Load'
                else:
                    agent['workload_status'] = 'Available'
            else:
                agent['workload_percentage'] = 0
                agent['workload_status'] = 'Available'
        
        return {
            'success': True,
            'agents': agent_data,
            'total_agents': len(agent_data),
            'timestamp': frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting agent workload status: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'agents': []
        }


@frappe.whitelist(allow_guest=False)
def configure_routing_rules(rules_data):
    """Configure smart routing rules and parameters"""
    try:
        # Parse rules data if it's a string
        if isinstance(rules_data, str):
            rules_data = json.loads(rules_data)
        
        # Validate rules data structure
        required_fields = ['skill_weights', 'priority_thresholds', 'escalation_rules']
        for field in required_fields:
            if field not in rules_data:
                return {
                    'success': False,
                    'error': f'Missing required field: {field}'
                }
        
        # Save routing configuration
        config_doc = frappe.get_doc({
            'doctype': 'Routing Configuration',
            'configuration_name': rules_data.get('name', 'Default Routing Rules'),
            'skill_weights': json.dumps(rules_data['skill_weights']),
            'priority_thresholds': json.dumps(rules_data['priority_thresholds']),
            'escalation_rules': json.dumps(rules_data['escalation_rules']),
            'is_active': rules_data.get('is_active', True),
            'created_by': frappe.session.user
        })
        
        # Check if configuration exists
        existing = frappe.db.exists('Routing Configuration', 
                                  {'configuration_name': config_doc.configuration_name})
        
        if existing:
            # Update existing configuration
            existing_doc = frappe.get_doc('Routing Configuration', existing)
            existing_doc.update(config_doc.as_dict())
            existing_doc.save()
            config_id = existing
        else:
            # Create new configuration
            config_doc.insert()
            config_id = config_doc.name
        
        return {
            'success': True,
            'configuration_id': config_id,
            'message': 'Routing rules configured successfully'
        }
        
    except Exception as e:
        frappe.log_error(f"Error configuring routing rules: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to configure routing rules'
        }


def get_routing_statistics(start_date, end_date, agent_id=None):
    """Get routing statistics for the specified period"""
    try:
        # Base query conditions
        conditions = "WHERE DATE(creation) BETWEEN %s AND %s"
        params = [start_date, end_date]
        
        if agent_id:
            conditions += " AND assigned_agent = %s"
            params.append(agent_id)
        
        # Total conversations routed
        total_routed = frappe.db.sql(f"""
            SELECT COUNT(*) as count
            FROM `tabConversation`
            {conditions}
        """, params, as_dict=True)
        
        # Routing by type
        routing_by_type = frappe.db.sql(f"""
            SELECT 
                CASE 
                    WHEN assigned_agent IS NOT NULL THEN 'Agent'
                    WHEN status = 'AI_Handling' THEN 'AI'
                    WHEN status = 'Escalated' THEN 'Escalated'
                    ELSE 'Unassigned'
                END as routing_type,
                COUNT(*) as count
            FROM `tabConversation`
            {conditions}
            GROUP BY routing_type
        """, params, as_dict=True)
        
        # Average routing time
        avg_routing_time = frappe.db.sql(f"""
            SELECT AVG(TIMESTAMPDIFF(SECOND, creation, assignment_time)) as avg_seconds
            FROM `tabConversation`
            {conditions} AND assignment_time IS NOT NULL
        """, params, as_dict=True)
        
        return {
            'total_routed': total_routed[0]['count'] if total_routed else 0,
            'routing_by_type': routing_by_type,
            'avg_routing_time_seconds': avg_routing_time[0]['avg_seconds'] if avg_routing_time and avg_routing_time[0]['avg_seconds'] else 0
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting routing statistics: {str(e)}")
        return {
            'total_routed': 0,
            'routing_by_type': [],
            'avg_routing_time_seconds': 0
        }


def get_agent_routing_performance(start_date, end_date, agent_id=None):
    """Get agent routing performance metrics"""
    try:
        # Base query conditions
        conditions = "WHERE DATE(c.creation) BETWEEN %s AND %s AND c.assigned_agent IS NOT NULL"
        params = [start_date, end_date]

        if agent_id:
            conditions += " AND c.assigned_agent = %s"
            params.append(agent_id)

        # Agent performance metrics
        agent_metrics = frappe.db.sql(f"""
            SELECT
                c.assigned_agent as agent_id,
                u.full_name as agent_name,
                COUNT(*) as conversations_handled,
                AVG(TIMESTAMPDIFF(SECOND, c.assignment_time, c.first_response_time)) as avg_response_time,
                AVG(c.priority_score) as avg_priority_score,
                SUM(CASE WHEN c.status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM `tabConversation` c
            LEFT JOIN `tabUser` u ON c.assigned_agent = u.name
            {conditions}
            GROUP BY c.assigned_agent, u.full_name
            ORDER BY conversations_handled DESC
        """, params, as_dict=True)

        # Calculate resolution rates
        for metric in agent_metrics:
            if metric['conversations_handled'] > 0:
                metric['resolution_rate'] = round(
                    (metric['resolved_count'] / metric['conversations_handled']) * 100, 2
                )
            else:
                metric['resolution_rate'] = 0

        return agent_metrics

    except Exception as e:
        frappe.log_error(f"Error getting agent routing performance: {str(e)}")
        return []


def get_routing_efficiency_metrics(start_date, end_date):
    """Get routing efficiency metrics"""
    try:
        # Skill match accuracy
        skill_match_accuracy = frappe.db.sql("""
            SELECT
                AVG(CASE WHEN routing_analysis IS NOT NULL THEN
                    JSON_EXTRACT(routing_analysis, '$.routing_recommendation.priority_score')
                    ELSE 50 END) as avg_match_score
            FROM `tabConversation`
            WHERE DATE(creation) BETWEEN %s AND %s
            AND routing_analysis IS NOT NULL
        """, (start_date, end_date), as_dict=True)

        # Escalation rate
        escalation_rate = frappe.db.sql("""
            SELECT
                COUNT(CASE WHEN status = 'Escalated' THEN 1 END) as escalated,
                COUNT(*) as total,
                (COUNT(CASE WHEN status = 'Escalated' THEN 1 END) / COUNT(*)) * 100 as escalation_rate
            FROM `tabConversation`
            WHERE DATE(creation) BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)

        # AI vs Human routing success
        routing_success = frappe.db.sql("""
            SELECT
                CASE
                    WHEN assigned_agent IS NOT NULL THEN 'Human'
                    WHEN status = 'AI_Handling' THEN 'AI'
                    ELSE 'Other'
                END as routing_type,
                AVG(CASE WHEN status = 'Resolved' THEN 100 ELSE 0 END) as success_rate
            FROM `tabConversation`
            WHERE DATE(creation) BETWEEN %s AND %s
            GROUP BY routing_type
        """, (start_date, end_date), as_dict=True)

        return {
            'avg_match_score': skill_match_accuracy[0]['avg_match_score'] if skill_match_accuracy else 50,
            'escalation_rate': escalation_rate[0]['escalation_rate'] if escalation_rate else 0,
            'routing_success_by_type': routing_success
        }

    except Exception as e:
        frappe.log_error(f"Error getting routing efficiency metrics: {str(e)}")
        return {
            'avg_match_score': 50,
            'escalation_rate': 0,
            'routing_success_by_type': []
        }


def get_realtime_routing_status():
    """Get real-time routing status"""
    try:
        # Current queue status
        queue_status = frappe.db.sql("""
            SELECT
                status,
                COUNT(*) as count
            FROM `tabConversation`
            WHERE DATE(creation) = CURDATE()
            AND status IN ('Open', 'Assigned', 'AI_Handling', 'Escalated')
            GROUP BY status
        """, as_dict=True)

        # Agent availability summary
        agent_availability = frappe.db.sql("""
            SELECT
                availability_status,
                COUNT(*) as count,
                SUM(current_workload) as total_workload,
                SUM(max_concurrent_conversations) as total_capacity
            FROM `tabAgent Profile` ap
            LEFT JOIN `tabUser` u ON ap.user = u.name
            WHERE u.enabled = 1
            GROUP BY availability_status
        """, as_dict=True)

        # Recent routing activity (last hour)
        recent_activity = frappe.db.sql("""
            SELECT
                COUNT(*) as conversations_routed,
                AVG(TIMESTAMPDIFF(SECOND, creation, assignment_time)) as avg_routing_time
            FROM `tabConversation`
            WHERE assignment_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """, as_dict=True)

        return {
            'queue_status': queue_status,
            'agent_availability': agent_availability,
            'recent_activity': recent_activity[0] if recent_activity else {
                'conversations_routed': 0,
                'avg_routing_time': 0
            },
            'timestamp': frappe.utils.now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting real-time routing status: {str(e)}")
        return {
            'queue_status': [],
            'agent_availability': [],
            'recent_activity': {'conversations_routed': 0, 'avg_routing_time': 0},
            'timestamp': frappe.utils.now()
        }
