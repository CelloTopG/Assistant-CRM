# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime
import json

class EscalationWorkflow(Document):
    """
    DocType for managing escalation workflows in the assistant_crm system.
    Tracks escalation requests, conversation context, and resolution progress.
    """
    
    def before_insert(self):
        """Set default values before inserting the document."""
        if not self.escalation_date:
            self.escalation_date = now()
        
        if not self.status:
            self.status = "pending"
        
        if not self.conversation_turns:
            self.conversation_turns = 0
        
        if not self.previous_escalation_attempts:
            self.previous_escalation_attempts = 0
    
    def before_save(self):
        """Validate and process data before saving."""
        # Calculate escalation priority score
        self.escalation_priority_score = self._calculate_escalation_priority_score()
        
        # Auto-assign agent based on department and priority
        if not self.assigned_agent and self.status == "pending":
            self.assigned_agent = self._auto_assign_agent()
    
    def _calculate_escalation_priority_score(self):
        """Calculate escalation priority score based on various factors."""
        score = 0
        
        # Priority level weight (40%)
        priority_weights = {"low": 1, "medium": 2, "high": 3, "urgent": 4}
        score += priority_weights.get(self.priority_level, 2) * 0.4
        
        # Frustration level weight (25%)
        frustration_weights = {"low": 1, "medium": 2, "high": 3}
        score += frustration_weights.get(self.frustration_level, 1) * 0.25
        
        # Conversation duration weight (15%)
        if self.conversation_duration:
            duration_score = min(3, self.conversation_duration / 10)  # Max 3 points for 30+ minutes
            score += duration_score * 0.15
        
        # Previous escalation attempts weight (10%)
        attempt_score = min(3, self.previous_escalation_attempts)
        score += attempt_score * 0.10
        
        # ML recommendation weight (10%)
        if self.ml_escalation_probability:
            score += self.ml_escalation_probability * 0.10
        
        return round(score, 2)
    
    def _auto_assign_agent(self):
        """Auto-assign agent based on department and availability."""
        try:
            # Get available agents for the department
            agents = frappe.get_all("User",
                filters={
                    "enabled": 1,
                    "user_type": "System User"
                },
                fields=["name", "full_name"]
            )
            
            if agents:
                # Simple round-robin assignment (can be enhanced with workload balancing)
                return agents[0].name
            
        except Exception as e:
            frappe.log_error(f"Error auto-assigning agent: {str(e)}")
        
        return None
    
    def assign_to_agent(self, agent_id, notes=None):
        """Assign escalation to a specific agent."""
        self.assigned_agent = agent_id
        self.status = "assigned"
        if notes:
            self.escalation_notes = (self.escalation_notes or "") + f"\n\nAssigned to {agent_id}: {notes}"
        self.save()
        frappe.db.commit()
    
    def update_status(self, new_status, notes=None):
        """Update escalation status with optional notes."""
        old_status = self.status
        self.status = new_status
        
        if new_status == "resolved":
            self.resolution_date = now()
        
        if notes:
            self.escalation_notes = (self.escalation_notes or "") + f"\n\nStatus changed from {old_status} to {new_status}: {notes}"
        
        self.save()
        frappe.db.commit()
    
    def add_resolution_notes(self, notes, satisfaction_level=None):
        """Add resolution notes and customer satisfaction."""
        self.resolution_notes = notes
        if satisfaction_level:
            self.customer_satisfaction = satisfaction_level
        
        if self.status != "resolved":
            self.status = "resolved"
            self.resolution_date = now()
        
        self.save()
        frappe.db.commit()
    
    def get_escalation_analytics(self):
        """Get analytics for this escalation."""
        try:
            analytics = {
                "escalation_id": self.name,
                "query_id": self.query_id,
                "user_id": self.user_id,
                "session_id": self.session_id,
                "escalation_date": self.escalation_date,
                "resolution_date": self.resolution_date,
                "priority_level": self.priority_level,
                "escalation_type": self.escalation_type,
                "department": self.department,
                "status": self.status,
                "escalation_priority_score": getattr(self, 'escalation_priority_score', 0),
                "conversation_context": {
                    "turns": self.conversation_turns,
                    "duration": self.conversation_duration,
                    "frustration_level": self.frustration_level,
                    "previous_attempts": self.previous_escalation_attempts
                },
                "ml_insights": {
                    "escalation_probability": self.ml_escalation_probability,
                    "recommendation": self.ml_recommendation
                },
                "resolution_info": {
                    "assigned_agent": self.assigned_agent,
                    "customer_satisfaction": self.customer_satisfaction,
                    "resolution_time": self._calculate_resolution_time()
                }
            }
            
            return analytics
            
        except Exception as e:
            frappe.log_error(f"Error getting escalation analytics: {str(e)}")
            return {}
    
    def _calculate_resolution_time(self):
        """Calculate resolution time in hours."""
        if self.resolution_date and self.escalation_date:
            start = get_datetime(self.escalation_date)
            end = get_datetime(self.resolution_date)
            return round((end - start).total_seconds() / 3600, 2)
        return None
    
    @frappe.whitelist()
    def get_escalation_details(self):
        """Get detailed information about this escalation."""
        return {
            "escalation_info": {
                "escalation_id": self.name,
                "query_id": self.query_id,
                "escalation_date": self.escalation_date,
                "escalation_reason": self.escalation_reason,
                "escalation_type": self.escalation_type,
                "priority_level": self.priority_level,
                "department": self.department,
                "status": self.status
            },
            "query_details": {
                "query_text": self.query_text,
                "confidence_score": self.confidence_score,
                "user_id": self.user_id,
                "session_id": self.session_id
            },
            "conversation_context": {
                "conversation_turns": self.conversation_turns,
                "frustration_level": self.frustration_level,
                "conversation_duration": self.conversation_duration,
                "previous_escalation_attempts": self.previous_escalation_attempts
            },
            "ml_analysis": {
                "ml_escalation_probability": self.ml_escalation_probability,
                "ml_recommendation": self.ml_recommendation,
                "escalation_priority_score": getattr(self, 'escalation_priority_score', 0)
            },
            "resolution": {
                "assigned_agent": self.assigned_agent,
                "resolution_date": self.resolution_date,
                "resolution_notes": self.resolution_notes,
                "customer_satisfaction": self.customer_satisfaction,
                "resolution_time_hours": self._calculate_resolution_time()
            },
            "notes": self.escalation_notes
        }


@frappe.whitelist()
def get_pending_escalations(department=None, priority=None, limit=50):
    """Get pending escalations with optional filters."""
    filters = {"status": ["in", ["pending", "assigned", "in_progress"]]}
    
    if department:
        filters["department"] = department
    if priority:
        filters["priority_level"] = priority
    
    escalations = frappe.get_all("Escalation Workflow",
        filters=filters,
        fields=["*"],
        order_by="escalation_date desc",
        limit=limit
    )
    
    return escalations


@frappe.whitelist()
def get_escalation_analytics_summary(date_range=None, department=None):
    """Get escalation analytics summary."""
    try:
        filters = {}
        if date_range:
            filters["escalation_date"] = [">=", date_range]
        if department:
            filters["department"] = department
        
        escalations = frappe.get_all("Escalation Workflow",
            filters=filters,
            fields=["*"],
            order_by="escalation_date desc"
        )
        
        if not escalations:
            return {"error": "No escalations found"}
        
        # Calculate summary analytics
        total_escalations = len(escalations)
        resolved_escalations = len([e for e in escalations if e.status == "resolved"])
        resolution_rate = (resolved_escalations / total_escalations) * 100 if total_escalations > 0 else 0
        
        # Priority distribution
        priority_counts = {}
        for escalation in escalations:
            priority = escalation.priority_level or "unknown"
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Department distribution
        department_counts = {}
        for escalation in escalations:
            dept = escalation.department or "unknown"
            department_counts[dept] = department_counts.get(dept, 0) + 1
        
        # Average resolution time
        resolved_with_time = [e for e in escalations if e.resolution_date and e.escalation_date]
        avg_resolution_time = 0
        if resolved_with_time:
            total_time = sum(
                (get_datetime(e.resolution_date) - get_datetime(e.escalation_date)).total_seconds() / 3600
                for e in resolved_with_time
            )
            avg_resolution_time = round(total_time / len(resolved_with_time), 2)
        
        return {
            "summary": {
                "total_escalations": total_escalations,
                "resolved_escalations": resolved_escalations,
                "resolution_rate": round(resolution_rate, 2),
                "average_resolution_time_hours": avg_resolution_time
            },
            "distributions": {
                "priority": priority_counts,
                "department": department_counts
            },
            "trends": {
                "escalation_reasons": _get_escalation_reason_trends(escalations),
                "frustration_levels": _get_frustration_level_trends(escalations)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting escalation analytics summary: {str(e)}")
        return {
            "error": "Failed to generate analytics summary",
            "details": str(e)
        }


def _get_escalation_reason_trends(escalations):
    """Get escalation reason trends."""
    reason_counts = {}
    for escalation in escalations:
        reason = escalation.escalation_reason or "unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return reason_counts


def _get_frustration_level_trends(escalations):
    """Get frustration level trends."""
    frustration_counts = {}
    for escalation in escalations:
        level = escalation.frustration_level or "unknown"
        frustration_counts[level] = frustration_counts.get(level, 0) + 1
    return frustration_counts


@frappe.whitelist()
def update_escalation_status(escalation_id, new_status, notes=None):
    """Update escalation status."""
    try:
        escalation = frappe.get_doc("Escalation Workflow", escalation_id)
        escalation.update_status(new_status, notes)
        return {
            "status": "success",
            "message": "Escalation status updated successfully"
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "Escalation not found"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to update escalation status",
            "details": str(e)
        }
