# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime, time_diff_in_seconds
import json
from typing import Dict, Any, Optional


class UnifiedInboxConversation(Document):
    """
    Unified Inbox Conversation DocType for managing multi-platform conversations
    with AI-first response system and intelligent escalation to human agents.
    """
    
    def before_insert(self):
        """Set default values before inserting the document."""
        if not self.conversation_id:
            self.conversation_id = self.generate_conversation_id()
        
        if not self.creation_time:
            self.creation_time = now()
        
        if not self.status:
            self.status = "New"
        
        if not self.priority:
            self.priority = "Medium"
    
    def after_insert(self):
        """Actions to perform after inserting the document."""
        # Log conversation creation
        frappe.log_error(
            f"New unified inbox conversation created: {self.conversation_id} on {self.platform}",
            "Unified Inbox - Conversation Created"
        )

        # Auto-assign agent from Customer Service roles
        self.auto_assign_customer_service_agent()

        # Trigger AI processing if enabled
        if self.should_process_with_ai_supervising():
            self.trigger_ai_processing()
    
    def before_save(self):
        """Actions to perform before saving the document."""
        # Update last message time if status changed
        if self.has_value_changed("status"):
            self.last_message_time = now()
        
        # Calculate response time SLA
        if self.first_response_time and self.creation_time:
            response_time_seconds = time_diff_in_seconds(self.first_response_time, self.creation_time)
            self.response_time_sla = response_time_seconds / 60  # Convert to minutes
        
        # Auto-escalate if needed
        if self.should_auto_escalate():
            self.escalate_to_human_agent()
        
        # Calculate/Update SLA Expiry
        self.calculate_resolution_sla()
        self.update_sla_status()

    def calculate_resolution_sla(self):
        """Calculate the resolution SLA expiry based on the platform.
        Meta platforms (WhatsApp, Facebook, Instagram): 24 hours
        All other platforms: 48 hours
        """
        if self.resolution_sla_expiry:
            return

        from frappe.utils import add_hours
        
        meta_platforms = ["WhatsApp", "Facebook", "Instagram"]
        hours = 24 if self.platform in meta_platforms else 48
        
        start_time = self.creation_time or now()
        self.resolution_sla_expiry = add_hours(start_time, hours)

    def update_sla_status(self):
        """Update the SLA status based on current time and document status."""
        if self.status in ["Resolved", "Closed"]:
            if self.resolution_sla_expiry and get_datetime(self.last_message_time or now()) <= get_datetime(self.resolution_sla_expiry):
                self.sla_status = "Fulfilled"
            else:
                self.sla_status = "Exceeded"
        else:
            if self.resolution_sla_expiry and get_datetime(now()) > get_datetime(self.resolution_sla_expiry):
                self.sla_status = "Exceeded"
            else:
                self.sla_status = "In Progress"
    
    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        import hashlib
        import time
        
        # Create unique ID based on platform, timestamp, and random component
        unique_string = f"{self.platform}_{now()}_{frappe.generate_hash(length=8)}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16].upper()
    
    def should_process_with_ai(self) -> bool:
        """Determine if conversation should be processed with AI.

        Agent control via conversation-level mode:
        - ai_mode = "On": force AI on
        - ai_mode = "Off": force AI off
        - ai_mode = "Auto" or empty: defaults apply (UnassignedÔåÆAI on, AssignedÔåÆAI off)
        Additionally:
        - Tawk.to always bypasses AI
        - Global AI settings can disable AI entirely
        """
        # Tawk.to conversations bypass AI and go directly to human agents
        if getattr(self, "platform", None) == "Tawk.to":
            return False

        # Check global AI settings first (can disable AI entirely)
        global_ai_enabled = True
        try:
            ai_settings = frappe.get_single("Enhanced AI Settings")
            if ai_settings is not None:
                flag = ai_settings.get("enable_ai_responses")
                if flag in (0, "0", False):
                    global_ai_enabled = False
        except Exception:
            pass

        if not global_ai_enabled:
            try:
                crm_settings = frappe.get_single("Assistant CRM Settings")
                if not (crm_settings and crm_settings.get("enabled")):
                    return False
            except Exception:
                return False

        # Conversation-level AI mode
        mode = (getattr(self, "ai_mode", None) or "").strip() or "Auto"
        if mode == "On":
            return True
        if mode == "Off":
            return False

        # Auto mode defaults based on assignment status
        if self.assigned_agent:
            return False  # Default: AI off when assigned to human agent
        else:
            return True   # Default: AI on when unassigned

    def should_process_with_ai_supervising(self) -> bool:
        """AI gating used for Unified Inbox with supervising agents.

        Behaviour:
        - Tawk.to: always human-only (no AI).
        - Global AI settings can disable AI entirely.
        - ai_mode = "On": force AI on.
        - ai_mode = "Off": force AI off.
        - ai_mode = "Auto" or empty: AI is allowed by default and is only
          disabled when the conversation is explicitly marked as
          requiring human intervention (``requires_human_intervention``).

        Having an assigned agent no longer disables AI by itself; agents
        can supervise AI conversations and step in when needed.
        """
        # Tawk.to conversations bypass AI and go directly to human agents
        if getattr(self, "platform", None) == "Tawk.to":
            return False

        # Check global AI settings first (can disable AI entirely)
        global_ai_enabled = True
        try:
            ai_settings = frappe.get_single("Enhanced AI Settings")
            if ai_settings is not None:
                flag = ai_settings.get("enable_ai_responses")
                if flag in (0, "0", False):
                    global_ai_enabled = False
        except Exception:
            pass

        if not global_ai_enabled:
            try:
                crm_settings = frappe.get_single("Assistant CRM Settings")
                if not (crm_settings and crm_settings.get("enabled")):
                    return False
            except Exception:
                return False

        # Conversation-level AI mode
        mode = (getattr(self, "ai_mode", None) or "").strip() or "Auto"
        if mode == "On":
            return True
        if mode == "Off":
            return False

        # Auto mode: let AI handle the conversation by default unless the
        # conversation has been explicitly marked as requiring human
        # intervention (e.g. after an escalation event).
        if getattr(self, "requires_human_intervention", None):
            return False
        return True

    def trigger_ai_processing(self):
        """Trigger AI processing for the conversation."""
        try:
            # Update status to AI Processing
            self.db_set("status", "AI Processing")
            self.db_set("ai_handled", 1)
            
            # Enqueue AI processing job
            frappe.enqueue(
                "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                conversation_id=self.name,
                queue="default",
                timeout=300
            )
            
        except Exception as e:
            frappe.log_error(f"Failed to trigger AI processing: {str(e)}", "Unified Inbox - AI Processing Error")
    
    def should_auto_escalate(self) -> bool:
        """Determine if conversation should be auto-escalated to human agent."""
        # Already escalated
        if self.assigned_agent:
            return False
        
        # Tawk.to conversations are automatically assigned to agents
        if self.platform == "Tawk.to" and not self.assigned_agent:
            return True
        
        # Check AI confidence score
        if self.ai_confidence_score and self.ai_confidence_score < 0.7:
            return True
        
        # Check if requires human intervention flag is set
        if self.requires_human_intervention:
            return True
        
        # Check escalation triggers
        if self.escalation_triggers:
            triggers = json.loads(self.escalation_triggers) if isinstance(self.escalation_triggers, str) else self.escalation_triggers
            if triggers and len(triggers) > 0:
                return True
        
        return False
    
    def escalate_to_human_agent(self, reason: str = None):
        """Escalate conversation to human agent."""
        try:
            # Prefer the already-assigned supervising agent (if any);
            # otherwise fall back to the routing logic to find an
            # available agent.
            target_agent = self.assigned_agent or self.find_available_agent()

            if target_agent:
                self.db_set("assigned_agent", target_agent)
                self.db_set("agent_assigned_at", now())
                self.db_set("status", "Agent Assigned")
                self.db_set("escalated_at", now())
                # Once escalated, we explicitly require human intervention
                # so that further messages bypass AI.
                self.db_set("requires_human_intervention", 1)

                if reason:
                    self.db_set("escalation_reason", reason)

                # Create escalation workflow record
                self.create_escalation_record(target_agent, reason)

                # Notify agent
                self.notify_agent_assignment(target_agent)

            else:
                # No agents available, mark as new for manual assignment
                self.db_set("status", "New")
                self.db_set("escalation_reason", "No agents available")

        except Exception as e:
            try:
                frappe.log_error(
                    f"Failed to escalate conversation: {str(e)}"[:2000],
                    "Escalation Error"[:140],
                )
            except Exception:
                pass

    def find_available_agent(self) -> Optional[str]:
        """Find an available agent for assignment.

        This delegates to the Agent Dashboard capacity model so that
        Unified Inbox conversations share the same load-balancing and
        concurrency limits as Omnichannel, but through a separate
        routing branch/pool.
        """
        try:
            from assistant_crm.assistant_crm.assistant_crm_module.doctype.agent_dashboard.agent_dashboard import (  # type: ignore
                AgentDashboard,
            )

            # For Unified Inbox we typically care about the originating
            # platform (WhatsApp, Facebook, etc.), but the key is that we
            # only draw from the "Unified Inbox" routing branch so the
            # two webhook branches have distinct agent pools.
            available_agents = AgentDashboard.get_available_agents(
                channel_type=self.platform,
                routing_branch="Unified Inbox",
            )

            if not available_agents:
                return None

            # AgentDashboard.get_available_agents already orders by
            # current_active_chats asc, so the first one is the least
            # busy agent in this branch.
            return available_agents[0].agent_user

        except Exception as e:
            frappe.log_error(
                f"Failed to find available agent for Unified Inbox: {str(e)}",
                "Unified Inbox - Agent Selection Error",
            )
            return None

    def auto_assign_customer_service_agent(self) -> None:
        """Auto-assign conversation to users with Customer Service roles.

        This queries users with roles "WCF Customer Service Officer" or
        "WCF Customer Service Assistant" and assigns the conversation to
        the least busy agent (one with fewest active conversations).
        """
        try:
            # Skip if already assigned
            if self.assigned_agent:
                return

            # Get users with Customer Service roles
            customer_service_roles = [
                "WCF Customer Service Officer",
                "WCF Customer Service Assistant"
            ]

            # Query users with these roles who are enabled
            agents = frappe.db.sql("""
                SELECT DISTINCT u.name as user_id, u.full_name
                FROM `tabUser` u
                INNER JOIN `tabHas Role` hr ON hr.parent = u.name
                WHERE hr.role IN %(roles)s
                AND u.enabled = 1
                AND u.name NOT IN ('Administrator', 'Guest')
                ORDER BY u.full_name
            """, {"roles": customer_service_roles}, as_dict=True)

            if not agents:
                frappe.log_error(
                    "No agents with Customer Service roles found for auto-assignment",
                    "Unified Inbox - Auto Assignment"
                )
                return

            # Count active conversations per agent (least busy assignment)
            agent_workloads = []
            for agent in agents:
                active_count = frappe.db.count(
                    "Unified Inbox Conversation",
                    {
                        "assigned_agent": agent.user_id,
                        "status": ["not in", ["Resolved", "Closed"]],
                    },
                )
                agent_workloads.append({
                    "user_id": agent.user_id,
                    "full_name": agent.full_name,
                    "active_conversations": active_count
                })

            # Sort by active conversations (least busy first)
            agent_workloads.sort(key=lambda x: x["active_conversations"])

            # Assign to the least busy agent
            selected_agent = agent_workloads[0]["user_id"]

            # Update conversation with assignment
            self.db_set("assigned_agent", selected_agent)
            self.db_set("agent_assigned_at", now())
            self.db_set("status", "Agent Assigned")

            # Notify the assigned agent
            self.notify_agent_assignment(selected_agent)

            frappe.log_error(
                f"Auto-assigned conversation {self.conversation_id} to {selected_agent} "
                f"(workload: {agent_workloads[0]['active_conversations']} active conversations)",
                "Unified Inbox - Auto Assignment Success"
            )

        except Exception as e:
            frappe.log_error(
                f"Failed to auto-assign customer service agent: {str(e)}",
                "Unified Inbox - Auto Assignment Error"
            )

    def auto_assign_supervising_agent_if_needed(self) -> None:
        """Ensure every conversation has a supervising agent for oversight.

        This does **not** disable AI. In "Auto" mode the AI will continue
        to respond while the assigned agent can monitor the conversation
        and intervene when necessary. Tawk.to is excluded here and
        continues to use its existing direct-to-agent flow.
        """
        try:
            # Do not interfere with Tawk.to's explicit human-only flow.
            if getattr(self, "platform", None) == "Tawk.to":
                return
            # Already has a supervising agent
            if self.assigned_agent:
                return
            agent = self.find_available_agent()
            if not agent:
                return
            self.db_set("assigned_agent", agent)
            self.db_set("agent_assigned_at", now())
            # Mark as agent assigned if still in a new/empty state; do not
            # override more specific statuses (e.g. Escalated).
            if not self.status or self.status == "New":
                self.db_set("status", "Agent Assigned")
            self.notify_agent_assignment(agent)
            # Refresh Agent Dashboard workload snapshot so future routing
            # decisions see this conversation as active for the agent.
            try:
                from assistant_crm.assistant_crm.assistant_crm_module.doctype.agent_dashboard.agent_dashboard import (  # type: ignore
                    AgentDashboard,
                )
                AgentDashboard.sync_unified_inbox_load_for_agent(agent)
            except Exception as sync_err:
                frappe.log_error(
                    f"Failed to sync agent load after auto-assignment: {sync_err}",
                    "Unified Inbox - Auto Assignment Load Sync",
                )
        except Exception as e:
            frappe.log_error(
                f"Failed to auto-assign supervising agent: {str(e)}",
                "Unified Inbox - Auto Assignment Error",
            )
    
    def create_escalation_record(self, agent: str, reason: str = None):
        """Create escalation workflow record."""
        try:
            escalation_doc = frappe.get_doc({
                "doctype": "Escalation Workflow",
                "query_id": self.conversation_id,
                "user_id": self.customer_id or "Guest",
                "escalation_date": now(),
                "escalation_reason": reason or "auto_escalation",
                "escalation_type": "automatic",
                "priority_level": self.priority.lower() if self.priority else "medium",
                "department": "customer_service",
                "status": "assigned",
                "query_text": self.last_message_preview or "Conversation escalated from unified inbox",
                "assigned_agent": agent,
                "confidence_score": self.ai_confidence_score or 0.0
            })
            escalation_doc.insert(ignore_permissions=True)
            
        except Exception as e:
            try:
                frappe.log_error(
                    f"Failed to create escalation record: {str(e)}"[:2000],
                    "Escalation Record Error"[:140],
                )
            except Exception:
                pass
    
    def notify_agent_assignment(self, agent: str):
        """Notify agent of new conversation assignment."""
        try:
            # Create notification
            notification = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"New conversation assigned: {self.customer_name or 'Unknown Customer'}",
                "email_content": f"""
                <p>You have been assigned a new conversation:</p>
                <ul>
                    <li><strong>Platform:</strong> {self.platform}</li>
                    <li><strong>Customer:</strong> {self.customer_name or 'Unknown'}</li>
                    <li><strong>Priority:</strong> {self.priority}</li>
                    <li><strong>Last Message:</strong> {self.last_message_preview or 'No preview available'}</li>
                </ul>
                <p>Please respond as soon as possible.</p>
                """,
                "for_user": agent,
                "type": "Assignment"
            })
            notification.insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Failed to notify agent: {str(e)}", "Unified Inbox - Agent Notification Error")
    
    def update_conversation_context(self, context_data: Dict[str, Any]):
        """Update conversation context with new data."""
        current_context = {}
        if self.conversation_context:
            current_context = json.loads(self.conversation_context) if isinstance(self.conversation_context, str) else self.conversation_context
        
        current_context.update(context_data)
        self.db_set("conversation_context", json.dumps(current_context))
    
    def add_platform_metadata(self, metadata: Dict[str, Any]):
        """Add platform-specific metadata."""
        current_metadata = {}
        if self.platform_metadata:
            current_metadata = json.loads(self.platform_metadata) if isinstance(self.platform_metadata, str) else self.platform_metadata
        
        current_metadata.update(metadata)
        self.db_set("platform_metadata", json.dumps(current_metadata))
    
    def mark_resolved(self, resolution_notes: str = None):
        """Mark conversation as resolved."""
        self.db_set("status", "Resolved")
        if resolution_notes:
            self.db_set("agent_notes", resolution_notes)
        
        # Update related escalation workflow if exists
        escalation = frappe.get_all(
            "Escalation Workflow",
            filters={"query_id": self.conversation_id},
            limit=1
        )
        
        if escalation:
            frappe.db.set_value("Escalation Workflow", escalation[0].name, "status", "resolved")
            if resolution_notes:
                frappe.db.set_value("Escalation Workflow", escalation[0].name, "resolution_notes", resolution_notes)
