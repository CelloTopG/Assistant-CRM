#!/usr/bin/env python3

import frappe
from frappe import _
import json
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def trigger_escalation(escalation_type, user_context=None, conversation_data=None, priority="normal"):
    """
    Main escalation trigger function
    Routes escalations based on type and context
    """
    try:
        # Parse context and conversation data
        context = json.loads(user_context) if user_context else {}
        conversation = json.loads(conversation_data) if conversation_data else {}
        
        # Determine escalation routing
        escalation_config = get_escalation_config(escalation_type, context, priority)
        
        # Create escalation record
        escalation_record = create_escalation_record(
            escalation_type, context, conversation, escalation_config
        )
        
        # Route to appropriate handler
        routing_result = route_escalation(escalation_record, escalation_config)
        
        # Log escalation for monitoring
        log_escalation_event(escalation_record, routing_result)
        
        return {
            'success': True,
            'escalation_id': escalation_record.name,
            'routing': routing_result,
            'estimated_response_time': escalation_config.get('response_time'),
            'contact_method': escalation_config.get('contact_method'),
            'message': 'Your request has been escalated to a human agent.'
        }
        
    except Exception as e:
        frappe.log_error(f"Escalation trigger error: {str(e)}", "Escalation Management")
        return {
            'success': False,
            'message': 'Unable to process escalation. Please contact support directly.',
            'fallback_contact': get_fallback_contact_info(),
            'error': str(e)
        }

def get_escalation_config(escalation_type, context, priority):
    """Get escalation configuration based on type and context"""
    
    # Base configuration
    config = {
        'response_time': '24 hours',
        'contact_method': 'email',
        'department': 'general_support',
        'priority_level': priority
    }
    
    user_role = context.get('role', 'General')
    
    # Configure based on escalation type
    if escalation_type == 'api_failure':
        config.update({
            'department': 'technical_support',
            'response_time': '2 hours' if priority == 'urgent' else '4 hours',
            'contact_method': 'phone',
            'specialist_required': True
        })
    
    elif escalation_type == 'payment_issue':
        config.update({
            'department': 'finance_support',
            'response_time': '4 hours' if user_role == 'Employer' else '24 hours',
            'contact_method': 'phone' if priority == 'urgent' else 'email',
            'requires_verification': True
        })
    
    elif escalation_type == 'claim_dispute':
        config.update({
            'department': 'claims_support',
            'response_time': '2 hours',
            'contact_method': 'phone',
            'specialist_required': True,
            'legal_review': True
        })
    
    elif escalation_type == 'complex_query':
        config.update({
            'department': 'specialist_support',
            'response_time': '1 hour' if priority == 'urgent' else '4 hours',
            'contact_method': 'phone',
            'context_preservation': True
        })
    
    elif escalation_type == 'user_request':
        config.update({
            'department': 'customer_service',
            'response_time': '30 minutes' if priority == 'urgent' else '2 hours',
            'contact_method': 'phone',
            'immediate_callback': priority == 'urgent'
        })
    
    elif escalation_type == 'system_error':
        config.update({
            'department': 'technical_support',
            'response_time': '1 hour',
            'contact_method': 'phone',
            'system_admin_alert': True
        })
    
    # Adjust based on user role
    if user_role == 'Employer':
        config['priority_boost'] = True
        if config['response_time'] == '24 hours':
            config['response_time'] = '4 hours'
    
    elif user_role == 'Beneficiary':
        if escalation_type in ['claim_dispute', 'payment_issue']:
            config['priority_boost'] = True
            config['response_time'] = '2 hours'
    
    return config

def create_escalation_record(escalation_type, context, conversation, config):
    """Create escalation record in database"""
    
    try:
        escalation = frappe.new_doc("Escalation Record")
        escalation.escalation_type = escalation_type
        escalation.user_id = context.get('user_id')
        escalation.user_role = context.get('role', 'General')
        escalation.priority = config.get('priority_level', 'normal')
        escalation.department = config.get('department')
        escalation.status = 'Open'
        escalation.created_at = frappe.utils.now()
        
        # Store context and conversation data
        escalation.user_context = json.dumps(context)
        escalation.conversation_history = json.dumps(conversation)
        
        # Set routing information
        escalation.assigned_department = config.get('department')
        escalation.estimated_response_time = config.get('response_time')
        escalation.contact_method = config.get('contact_method')
        
        # Add special flags
        if config.get('specialist_required'):
            escalation.specialist_required = 1
        if config.get('requires_verification'):
            escalation.requires_verification = 1
        if config.get('legal_review'):
            escalation.legal_review_required = 1
        
        escalation.insert()
        frappe.db.commit()
        
        return escalation
        
    except Exception as e:
        frappe.log_error(f"Escalation record creation error: {str(e)}", "Escalation Management")
        raise

def route_escalation(escalation_record, config):
    """Route escalation to appropriate department/agent"""
    
    try:
        department = config.get('department')
        routing_result = {}
        
        # Get available agents for department
        available_agents = get_available_agents(department, config)
        
        if available_agents:
            # Assign to best available agent
            assigned_agent = select_best_agent(available_agents, escalation_record, config)
            
            # Update escalation record
            escalation_record.assigned_agent = assigned_agent['user_id']
            escalation_record.assigned_at = frappe.utils.now()
            escalation_record.save()
            
            # Notify agent
            notify_agent(assigned_agent, escalation_record, config)
            
            routing_result = {
                'status': 'assigned',
                'agent_id': assigned_agent['user_id'],
                'agent_name': assigned_agent['full_name'],
                'department': department,
                'contact_method': config.get('contact_method')
            }
            
        else:
            # No agents available - queue for next available
            escalation_record.status = 'Queued'
            escalation_record.save()
            
            # Send to department queue
            queue_escalation(escalation_record, config)
            
            routing_result = {
                'status': 'queued',
                'department': department,
                'queue_position': get_queue_position(escalation_record),
                'estimated_wait': calculate_estimated_wait(department)
            }
        
        return routing_result
        
    except Exception as e:
        frappe.log_error(f"Escalation routing error: {str(e)}", "Escalation Management")
        return {
            'status': 'error',
            'message': 'Routing failed, escalation logged for manual processing'
        }

def get_available_agents(department, config):
    """Get list of available agents for department"""
    
    try:
        # Query agent availability
        agents = frappe.db.sql("""
            SELECT 
                user_id, full_name, department, specialization,
                current_workload, max_concurrent_cases, status
            FROM `tabAgent Dashboard`
            WHERE department = %s 
            AND status = 'Available'
            AND current_workload < max_concurrent_cases
            ORDER BY current_workload ASC, last_assignment ASC
        """, (department,), as_dict=True)
        
        # Filter by specialization if required
        if config.get('specialist_required'):
            specialization = get_required_specialization(config)
            agents = [a for a in agents if specialization in (a.specialization or '')]
        
        return agents
        
    except Exception as e:
        frappe.log_error(f"Agent availability query error: {str(e)}", "Escalation Management")
        return []

def select_best_agent(available_agents, escalation_record, config):
    """Select the best available agent for the escalation"""
    
    # Scoring criteria
    for agent in available_agents:
        score = 0
        
        # Lower workload = higher score
        score += (10 - agent.current_workload) * 2
        
        # Specialization match
        if config.get('specialist_required'):
            required_spec = get_required_specialization(config)
            if required_spec in (agent.specialization or ''):
                score += 20
        
        # Department experience (could be tracked separately)
        score += 5  # Base department score
        
        # Priority handling capability
        if config.get('priority_level') == 'urgent':
            score += 10
        
        agent['selection_score'] = score
    
    # Return highest scoring agent
    return max(available_agents, key=lambda x: x['selection_score'])

def notify_agent(agent, escalation_record, config):
    """Notify assigned agent about new escalation"""
    
    try:
        # Create notification record
        notification = frappe.new_doc("Agent Notification")
        notification.agent_id = agent['user_id']
        notification.escalation_id = escalation_record.name
        notification.notification_type = 'New Escalation'
        notification.priority = config.get('priority_level', 'normal')
        notification.message = f"New {escalation_record.escalation_type} escalation assigned"
        notification.created_at = frappe.utils.now()
        notification.insert()
        
        # Send immediate notification based on contact method
        contact_method = config.get('contact_method', 'email')
        
        if contact_method == 'phone' or config.get('immediate_callback'):
            # Trigger phone notification
            send_phone_notification(agent, escalation_record)
        
        if contact_method in ['email', 'both']:
            # Send email notification
            send_email_notification(agent, escalation_record)
        
        # Update agent workload
        update_agent_workload(agent['user_id'], increment=1)
        
    except Exception as e:
        frappe.log_error(f"Agent notification error: {str(e)}", "Escalation Management")

def queue_escalation(escalation_record, config):
    """Add escalation to department queue"""
    
    try:
        queue_entry = frappe.new_doc("Escalation Queue")
        queue_entry.escalation_id = escalation_record.name
        queue_entry.department = config.get('department')
        queue_entry.priority = config.get('priority_level', 'normal')
        queue_entry.queued_at = frappe.utils.now()
        queue_entry.estimated_wait = calculate_estimated_wait(config.get('department'))
        queue_entry.insert()
        
        # Send queue notification to department
        send_department_notification(config.get('department'), escalation_record)
        
    except Exception as e:
        frappe.log_error(f"Queue escalation error: {str(e)}", "Escalation Management")

def log_escalation_event(escalation_record, routing_result):
    """Log escalation event for monitoring and analytics"""
    
    try:
        log_entry = frappe.new_doc("Escalation Log")
        log_entry.escalation_id = escalation_record.name
        log_entry.event_type = 'Escalation Created'
        log_entry.event_data = json.dumps(routing_result)
        log_entry.timestamp = frappe.utils.now()
        log_entry.user_role = escalation_record.user_role
        log_entry.department = escalation_record.department
        log_entry.insert()
        
    except Exception as e:
        frappe.log_error(f"Escalation logging error: {str(e)}", "Escalation Management")

def get_fallback_contact_info():
    """Get fallback contact information when escalation fails"""
    
    return {
        'phone': '+260-211-123456',
        'email': 'support@wcfcb.gov.zm',
        'whatsapp': '+260-977-123456',
        'emergency_hotline': '933'
    }

def get_required_specialization(config):
    """Get required agent specialization based on escalation config"""
    
    specialization_map = {
        'technical_support': 'Technical Systems',
        'finance_support': 'Financial Services',
        'claims_support': 'Claims Processing',
        'specialist_support': 'Complex Cases',
        'customer_service': 'Customer Relations'
    }
    
    return specialization_map.get(config.get('department'), 'General')

def get_queue_position(escalation_record):
    """Get position in department queue"""
    
    try:
        position = frappe.db.count("Escalation Queue", {
            'department': escalation_record.department,
            'queued_at': ['<', escalation_record.created_at]
        })
        return position + 1
        
    except:
        return 1

def calculate_estimated_wait(department):
    """Calculate estimated wait time for department"""
    
    # Base wait times by department (in minutes)
    base_wait_times = {
        'technical_support': 30,
        'finance_support': 45,
        'claims_support': 20,
        'specialist_support': 60,
        'customer_service': 15,
        'general_support': 30
    }
    
    base_wait = base_wait_times.get(department, 30)
    
    # Adjust based on current queue length
    queue_length = frappe.db.count("Escalation Queue", {'department': department})
    adjusted_wait = base_wait + (queue_length * 10)
    
    return f"{adjusted_wait} minutes"

def send_phone_notification(agent, escalation_record):
    """Send phone notification to agent"""
    # Implementation would integrate with phone system
    pass

def send_email_notification(agent, escalation_record):
    """Send email notification to agent"""
    # Implementation would use Frappe's email system
    pass

def send_department_notification(department, escalation_record):
    """Send notification to department"""
    # Implementation would notify department supervisors
    pass

def update_agent_workload(agent_id, increment=1):
    """Update agent's current workload"""
    try:
        frappe.db.sql("""
            UPDATE `tabAgent Dashboard` 
            SET current_workload = current_workload + %s,
                last_assignment = %s
            WHERE user_id = %s
        """, (increment, frappe.utils.now(), agent_id))
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Agent workload update error: {str(e)}", "Escalation Management")
