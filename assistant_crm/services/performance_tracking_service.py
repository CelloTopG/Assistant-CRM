import frappe
from frappe import _
from datetime import datetime, timedelta
import json

class PerformanceTrackingService:
    def __init__(self):
        self.sla_configs = self.load_sla_configurations()

    def load_sla_configurations(self):
        """Load SLA configurations"""
        return frappe.db.sql("""
            SELECT priority, channel, first_response_time, resolution_time, escalation_time
            FROM `tabSLA Configuration`
            WHERE is_active = 1
        """, as_dict=True)

    def calculate_agent_metrics(self, agent_id, date=None):
        """Calculate daily metrics for an agent"""
        if not date:
            date = frappe.utils.today()

        # Get conversations handled by agent on the date
        conversations = frappe.db.sql("""
            SELECT name, conversation_id, creation, status, priority,
                   assigned_agent, last_message_time
            FROM `tabOmnichannel Conversation`
            WHERE assigned_agent = %s
            AND DATE(creation) = %s
        """, (agent_id, date), as_dict=True)

        if not conversations:
            return None

        # Get messages for response time calculations
        conversation_ids = [conv['conversation_id'] for conv in conversations]
        messages = self.get_conversation_messages(conversation_ids)

        metrics = {
            'agent': agent_id,
            'metric_date': date,
            'conversations_handled': len(conversations),
            'average_response_time': self.calculate_average_response_time(conversations, messages),
            'average_resolution_time': self.calculate_average_resolution_time(conversations),
            'first_response_time': self.calculate_first_response_time(conversations, messages),
            'sla_compliance_rate': self.calculate_sla_compliance(conversations, messages),
            'escalations_received': self.count_escalations(conversations),
            'active_hours': self.calculate_active_hours(agent_id, date),
            'utilization_rate': self.calculate_utilization_rate(agent_id, date)
        }

        # Save or update metrics
        existing = frappe.db.get_value('Agent Performance Metric',
                                     {'agent': agent_id, 'metric_date': date}, 'name')

        if existing:
            frappe.db.set_value('Agent Performance Metric', existing, metrics)
        else:
            metric_doc = frappe.get_doc({
                'doctype': 'Agent Performance Metric',
                **metrics
            })
            metric_doc.insert()

        return metrics

    def get_conversation_messages(self, conversation_ids):
        """Get messages for conversations"""
        if not conversation_ids:
            return []
        
        placeholders = ', '.join(['%s'] * len(conversation_ids))
        return frappe.db.sql(f"""
            SELECT conversation_id, direction, timestamp, sender_type
            FROM `tabOmnichannel Message`
            WHERE conversation_id IN ({placeholders})
            ORDER BY timestamp ASC
        """, conversation_ids, as_dict=True)

    def calculate_average_response_time(self, conversations, messages):
        """Calculate average response time in minutes"""
        response_times = []
        
        # Group messages by conversation
        messages_by_conv = {}
        for msg in messages:
            if msg['conversation_id'] not in messages_by_conv:
                messages_by_conv[msg['conversation_id']] = []
            messages_by_conv[msg['conversation_id']].append(msg)

        for conv in conversations:
            conv_messages = messages_by_conv.get(conv['conversation_id'], [])
            if not conv_messages:
                continue
            
            # Find first customer message and first agent response
            first_customer_msg = None
            first_agent_response = None
            
            for msg in conv_messages:
                if msg['direction'] == 'Inbound' and not first_customer_msg:
                    first_customer_msg = msg
                elif (msg['direction'] == 'Outbound' and 
                      msg['sender_type'] == 'Agent' and 
                      first_customer_msg and 
                      not first_agent_response):
                    first_agent_response = msg
                    break
            
            if first_customer_msg and first_agent_response:
                response_time = (first_agent_response['timestamp'] - 
                               first_customer_msg['timestamp']).total_seconds() / 60
                response_times.append(response_time)

        return sum(response_times) / len(response_times) if response_times else 0

    def calculate_average_resolution_time(self, conversations):
        """Calculate average resolution time in hours"""
        resolution_times = []
        
        for conv in conversations:
            if conv['status'] in ['Resolved', 'Closed']:
                resolution_time = (conv['last_message_time'] - 
                                 conv['creation']).total_seconds() / 3600
                resolution_times.append(resolution_time)
        
        return sum(resolution_times) / len(resolution_times) if resolution_times else 0

    def calculate_first_response_time(self, conversations, messages):
        """Calculate average first response time in minutes"""
        # This is similar to average_response_time but focuses on first response only
        return self.calculate_average_response_time(conversations, messages)

    def calculate_sla_compliance(self, conversations, messages):
        """Calculate SLA compliance rate"""
        total_conversations = len(conversations)
        compliant_conversations = 0

        for conv in conversations:
            sla_config = self.get_sla_config(conv.get('priority'), 'All')  # Simplified
            if self.is_sla_compliant(conv, sla_config, messages):
                compliant_conversations += 1

        return (compliant_conversations / total_conversations * 100) if total_conversations > 0 else 0

    def get_sla_config(self, priority, channel):
        """Get SLA configuration for priority and channel"""
        for config in self.sla_configs:
            if (config['priority'] == priority or config['priority'] == 'All') and \
               (config['channel'] == channel or config['channel'] == 'All'):
                return config
        return None

    def is_sla_compliant(self, conversation, sla_config, messages):
        """Check if conversation meets SLA requirements"""
        if not sla_config:
            return True

        # Find first response time for this conversation
        conv_messages = [msg for msg in messages if msg['conversation_id'] == conversation['conversation_id']]
        
        first_customer_msg = None
        first_agent_response = None
        
        for msg in conv_messages:
            if msg['direction'] == 'Inbound' and not first_customer_msg:
                first_customer_msg = msg
            elif (msg['direction'] == 'Outbound' and 
                  msg['sender_type'] == 'Agent' and 
                  first_customer_msg and 
                  not first_agent_response):
                first_agent_response = msg
                break
        
        # Check first response time SLA
        if first_customer_msg and first_agent_response and sla_config.get('first_response_time'):
            response_time_minutes = (first_agent_response['timestamp'] - 
                                   first_customer_msg['timestamp']).total_seconds() / 60
            
            if response_time_minutes > sla_config['first_response_time']:
                return False

        return True


    def count_escalations(self, conversations):
        """Count escalations for conversations"""
        escalation_count = 0
        for conv in conversations:
            if conv.get('escalation_level', 0) > 0:
                escalation_count += 1
        return escalation_count

    def calculate_active_hours(self, agent_id, date):
        """Calculate active hours for agent on given date"""
        # This is a simplified calculation
        # In a real implementation, you might track login/logout times or message activity
        
        # Get message activity for the agent on the date
        messages = frappe.db.sql("""
            SELECT timestamp
            FROM `tabOmnichannel Message`
            WHERE sender_id = %s
            AND DATE(timestamp) = %s
            AND direction = 'Outbound'
            ORDER BY timestamp
        """, (agent_id, date), as_dict=True)
        
        if not messages:
            return 0
        
        # Calculate active hours based on message activity span
        first_activity = messages[0]['timestamp']
        last_activity = messages[-1]['timestamp']
        
        active_duration = (last_activity - first_activity).total_seconds() / 3600
        return min(active_duration, 8)  # Cap at 8 hours

    def calculate_utilization_rate(self, agent_id, date):
        """Calculate utilization rate for agent"""
        active_hours = self.calculate_active_hours(agent_id, date)
        standard_hours = 8  # Assuming 8-hour work day
        
        return min(100, (active_hours / standard_hours) * 100) if standard_hours > 0 else 0

    def generate_performance_report(self, agent_id=None, start_date=None, end_date=None):
        """Generate comprehensive performance report"""
        if not start_date:
            start_date = frappe.utils.add_days(frappe.utils.today(), -30)
        if not end_date:
            end_date = frappe.utils.today()

        conditions = ['metric_date BETWEEN %s AND %s']
        values = [start_date, end_date]

        if agent_id:
            conditions.append('agent = %s')
            values.append(agent_id)

        metrics = frappe.db.sql(f"""
            SELECT agent, AVG(conversations_handled) as avg_conversations,
                   AVG(average_response_time) as avg_response_time,
                   AVG(sla_compliance_rate) as avg_sla_compliance,
                   AVG(customer_satisfaction_score) as avg_csat,
                   SUM(conversations_handled) as total_conversations,
                   AVG(quality_score) as avg_quality_score
            FROM `tabAgent Performance Metric`
            WHERE {' AND '.join(conditions)}
            GROUP BY agent
            ORDER BY avg_csat DESC, avg_sla_compliance DESC
        """, values, as_dict=True)

        return metrics

    def get_sla_breach_alerts(self, agent_id=None):
        """Get SLA breach alerts"""
        conditions = ['status IN ("Open", "Assigned", "Pending")']
        values = []
        
        if agent_id:
            conditions.append('assigned_agent = %s')
            values.append(agent_id)
        
        conversations = frappe.db.sql(f"""
            SELECT conversation_id, priority, creation, assigned_agent,
                   TIMESTAMPDIFF(MINUTE, creation, NOW()) as minutes_elapsed
            FROM `tabOmnichannel Conversation`
            WHERE {' AND '.join(conditions)}
            ORDER BY creation ASC
        """, values, as_dict=True)
        
        breach_alerts = []
        
        for conv in conversations:
            sla_config = self.get_sla_config(conv['priority'], 'All')
            if sla_config and sla_config.get('first_response_time'):
                if conv['minutes_elapsed'] > sla_config['first_response_time']:
                    conv['breach_type'] = 'First Response'
                    conv['sla_threshold'] = sla_config['first_response_time']
                    breach_alerts.append(conv)
        
        return breach_alerts

@frappe.whitelist(allow_guest=False)
def calculate_daily_metrics(agent_id=None, date=None):
    """API endpoint to calculate daily metrics"""
    service = PerformanceTrackingService()
    
    if agent_id:
        return service.calculate_agent_metrics(agent_id, date)
    else:
        # Calculate for all agents
        agents = frappe.db.sql("""
            SELECT DISTINCT assigned_agent as agent
            FROM `tabOmnichannel Conversation`
            WHERE assigned_agent IS NOT NULL
            AND DATE(creation) = %s
        """, (date or frappe.utils.today(),), as_dict=True)
        
        results = []
        for agent in agents:
            metrics = service.calculate_agent_metrics(agent['agent'], date)
            if metrics:
                results.append(metrics)
        
        return results
