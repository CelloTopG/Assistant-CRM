import frappe
from frappe.model.document import Document
from datetime import datetime


class CallLog(Document):
    """Call Log DocType for VoIP functionality"""
    
    def validate(self):
        """Validate call log data"""
        self.validate_phone_number()
        self.validate_duration()
        self.set_defaults()
    
    def validate_phone_number(self):
        """Validate customer phone number format"""
        if self.customer_phone:
            # Remove any non-digit characters except +
            phone = self.customer_phone.strip()
            if not phone.startswith('+'):
                if phone.startswith('260'):
                    phone = '+' + phone
                elif phone.startswith('0'):
                    phone = '+260' + phone[1:]
                else:
                    phone = '+260' + phone
            
            self.customer_phone = phone
    
    def validate_duration(self):
        """Validate and calculate call duration"""
        if self.connect_time and self.end_time:
            if self.end_time < self.connect_time:
                frappe.throw("End time cannot be before connect time")
            
            # Calculate duration in seconds
            duration = (self.end_time - self.connect_time).total_seconds()
            self.duration = int(duration)
    
    def set_defaults(self):
        """Set default values"""
        if not self.call_session_id:
            self.call_session_id = frappe.generate_hash()[:16]
        
        if not self.start_time:
            self.start_time = datetime.now()
    
    def on_update(self):
        """Handle call log updates"""
        self.update_conversation_if_exists()
        self.update_customer_interaction_history()
    
    def update_conversation_if_exists(self):
        """Update related conversation record"""
        try:
            if self.call_session_id:
                # Find related conversation
                conversations = frappe.db.sql("""
                    SELECT name FROM `tabOmnichannel Conversation`
                    WHERE call_session_id = %s
                """, (self.call_session_id,), as_dict=True)
                
                if conversations:
                    conversation = frappe.get_doc("Omnichannel Conversation", conversations[0].name)
                    conversation.call_duration = self.duration or 0
                    conversation.call_status = self.call_status
                    
                    if self.call_status == "ended":
                        conversation.conversation_status = "Closed"
                        conversation.end_time = self.end_time
                    
                    conversation.save()
                    
        except Exception as e:
            frappe.log_error(f"Error updating conversation from call log: {str(e)}")
    
    def update_customer_interaction_history(self):
        """Update customer interaction history"""
        try:
            if self.customer_id and self.call_status == "ended":
                # Create interaction history record
                interaction = frappe.get_doc({
                    "doctype": "Chat History",
                    "customer_id": self.customer_id,
                    "agent_id": self.agent_id,
                    "channel_type": "voice",
                    "interaction_type": "call",
                    "interaction_data": {
                        "call_session_id": self.call_session_id,
                        "call_direction": self.call_direction,
                        "duration": self.duration,
                        "call_status": self.call_status
                    },
                    "timestamp": self.start_time,
                    "message_content": f"Voice call - Duration: {self.duration}s, Direction: {self.call_direction}"
                })
                interaction.insert()
                
        except Exception as e:
            frappe.log_error(f"Error updating customer interaction history: {str(e)}")
    
    def get_call_summary(self):
        """Get formatted call summary"""
        summary = {
            "call_session_id": self.call_session_id,
            "customer_phone": self.customer_phone,
            "agent_id": self.agent_id,
            "call_direction": self.call_direction,
            "call_status": self.call_status,
            "start_time": self.start_time,
            "duration": self.duration or 0,
            "formatted_duration": self.get_formatted_duration()
        }
        
        if self.customer_id:
            try:
                customer = frappe.get_doc("Customer", self.customer_id)
                summary["customer_name"] = customer.customer_name
            except:
                pass
        
        return summary
    
    def get_formatted_duration(self):
        """Get human-readable duration format"""
        if not self.duration:
            return "0s"
        
        duration = int(self.duration)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


def get_call_analytics(agent_id=None, date_range=None):
    """Get call analytics for dashboard"""
    try:
        conditions = []
        values = []
        
        if agent_id:
            conditions.append("agent_id = %s")
            values.append(agent_id)
        
        if date_range:
            if date_range.get("start_date"):
                conditions.append("DATE(start_time) >= %s")
                values.append(date_range["start_date"])
            if date_range.get("end_date"):
                conditions.append("DATE(start_time) <= %s")
                values.append(date_range["end_date"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get basic statistics
        stats = frappe.db.sql(f"""
            SELECT 
                COUNT(*) as total_calls,
                COUNT(CASE WHEN call_status = 'ended' THEN 1 END) as completed_calls,
                COUNT(CASE WHEN call_status = 'failed' THEN 1 END) as failed_calls,
                COUNT(CASE WHEN call_direction = 'inbound' THEN 1 END) as inbound_calls,
                COUNT(CASE WHEN call_direction = 'outbound' THEN 1 END) as outbound_calls,
                AVG(CASE WHEN duration > 0 THEN duration END) as avg_duration,
                SUM(CASE WHEN duration > 0 THEN duration END) as total_duration,
                MAX(duration) as max_duration,
                MIN(CASE WHEN duration > 0 THEN duration END) as min_duration
            FROM `tabCall Log`
            WHERE {where_clause}
        """, values, as_dict=True)
        
        # Get hourly distribution
        hourly_stats = frappe.db.sql(f"""
            SELECT 
                HOUR(start_time) as hour,
                COUNT(*) as call_count,
                AVG(CASE WHEN duration > 0 THEN duration END) as avg_duration
            FROM `tabCall Log`
            WHERE {where_clause}
            GROUP BY HOUR(start_time)
            ORDER BY hour
        """, values, as_dict=True)
        
        # Get daily trends (last 30 days)
        daily_trends = frappe.db.sql(f"""
            SELECT 
                DATE(start_time) as date,
                COUNT(*) as call_count,
                COUNT(CASE WHEN call_status = 'ended' THEN 1 END) as completed_calls,
                AVG(CASE WHEN duration > 0 THEN duration END) as avg_duration
            FROM `tabCall Log`
            WHERE {where_clause} AND start_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(start_time)
            ORDER BY date DESC
        """, values, as_dict=True)
        
        return {
            "summary": stats[0] if stats else {},
            "hourly_distribution": hourly_stats,
            "daily_trends": daily_trends,
            "success_rate": (stats[0]["completed_calls"] / stats[0]["total_calls"] * 100) if stats and stats[0]["total_calls"] > 0 else 0
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting call analytics: {str(e)}")
        return {
            "summary": {},
            "hourly_distribution": [],
            "daily_trends": [],
            "success_rate": 0
        }


def get_agent_call_performance(agent_id, date_range=None):
    """Get specific agent call performance metrics"""
    try:
        conditions = ["agent_id = %s"]
        values = [agent_id]
        
        if date_range:
            if date_range.get("start_date"):
                conditions.append("DATE(start_time) >= %s")
                values.append(date_range["start_date"])
            if date_range.get("end_date"):
                conditions.append("DATE(start_time) <= %s")
                values.append(date_range["end_date"])
        
        where_clause = " AND ".join(conditions)
        
        performance = frappe.db.sql(f"""
            SELECT 
                COUNT(*) as total_calls,
                COUNT(CASE WHEN call_status = 'ended' THEN 1 END) as completed_calls,
                COUNT(CASE WHEN call_status = 'failed' THEN 1 END) as failed_calls,
                AVG(CASE WHEN duration > 0 THEN duration END) as avg_call_duration,
                SUM(CASE WHEN duration > 0 THEN duration END) as total_talk_time,
                COUNT(CASE WHEN call_direction = 'inbound' THEN 1 END) as inbound_calls,
                COUNT(CASE WHEN call_direction = 'outbound' THEN 1 END) as outbound_calls
            FROM `tabCall Log`
            WHERE {where_clause}
        """, values, as_dict=True)
        
        if performance:
            perf = performance[0]
            perf["success_rate"] = (perf["completed_calls"] / perf["total_calls"] * 100) if perf["total_calls"] > 0 else 0
            perf["avg_call_duration_formatted"] = format_duration(perf["avg_call_duration"] or 0)
            perf["total_talk_time_formatted"] = format_duration(perf["total_talk_time"] or 0)
            
            return perf
        
        return {}
        
    except Exception as e:
        frappe.log_error(f"Error getting agent call performance: {str(e)}")
        return {}


def format_duration(seconds):
    """Format duration in seconds to human readable format"""
    if not seconds:
        return "0s"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
