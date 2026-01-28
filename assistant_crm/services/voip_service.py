import frappe
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid


class VoIPService:
    """
    VoIP/Softphone Service for WCFCB Assistant CRM
    Provides embedded call widget functionality with SIP-based softphone capabilities
    """
    
    def __init__(self):
        self.sip_config = self.get_sip_configuration()
        self.call_sessions = {}
        
    def get_sip_configuration(self) -> Dict[str, Any]:
        """Get SIP configuration from system settings"""
        try:
            settings = frappe.get_single("VoIP Settings")
            return {
                "sip_server": settings.get("sip_server", "sip.wcfcb.gov.zm"),
                "sip_port": settings.get("sip_port", 5060),
                "sip_domain": settings.get("sip_domain", "wcfcb.gov.zm"),
                "stun_server": settings.get("stun_server", "stun:stun.l.google.com:19302"),
                "turn_server": settings.get("turn_server", ""),
                "websocket_url": settings.get("websocket_url", "wss://sip.wcfcb.gov.zm:8089/ws"),
                "enabled": settings.get("enabled", 0)
            }
        except Exception:
            # Default configuration
            return {
                "sip_server": "sip.wcfcb.gov.zm",
                "sip_port": 5060,
                "sip_domain": "wcfcb.gov.zm",
                "stun_server": "stun:stun.l.google.com:19302",
                "turn_server": "",
                "websocket_url": "wss://sip.wcfcb.gov.zm:8089/ws",
                "enabled": 1
            }
    
    def initiate_call(self, agent_id: str, customer_phone: str, customer_id: str = None) -> Dict[str, Any]:
        """
        Initiate an outbound call from agent to customer
        
        Args:
            agent_id: ID of the agent making the call
            customer_phone: Customer's phone number
            customer_id: Optional customer ID for linking
            
        Returns:
            Dict containing call session information
        """
        try:
            # Generate unique call session ID
            call_session_id = str(uuid.uuid4())
            
            # Get agent SIP credentials
            agent_sip = self.get_agent_sip_credentials(agent_id)
            if not agent_sip:
                return {
                    "success": False,
                    "error": "Agent SIP credentials not found",
                    "call_session_id": None
                }
            
            # Create call session record
            call_session = {
                "call_session_id": call_session_id,
                "agent_id": agent_id,
                "customer_phone": customer_phone,
                "customer_id": customer_id,
                "call_direction": "outbound",
                "call_status": "initiating",
                "start_time": datetime.now(),
                "agent_sip_uri": f"sip:{agent_sip['username']}@{self.sip_config['sip_domain']}",
                "customer_sip_uri": f"sip:{customer_phone}@{self.sip_config['sip_domain']}",
                "sip_config": self.sip_config
            }
            
            # Store session in memory and database
            self.call_sessions[call_session_id] = call_session
            self.create_call_log(call_session)
            
            return {
                "success": True,
                "call_session_id": call_session_id,
                "sip_config": self.sip_config,
                "agent_credentials": agent_sip,
                "customer_uri": call_session["customer_sip_uri"],
                "websocket_url": self.sip_config["websocket_url"]
            }
            
        except Exception as e:
            frappe.log_error(f"Error initiating call: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "call_session_id": None
            }
    
    def handle_incoming_call(self, caller_phone: str, agent_id: str = None) -> Dict[str, Any]:
        """
        Handle incoming call and route to available agent
        
        Args:
            caller_phone: Phone number of the caller
            agent_id: Optional specific agent to route to
            
        Returns:
            Dict containing call routing information
        """
        try:
            # Generate call session ID
            call_session_id = str(uuid.uuid4())
            
            # Find customer by phone number
            customer = self.find_customer_by_phone(caller_phone)
            
            # Route to appropriate agent
            if not agent_id:
                agent_id = self.route_call_to_agent(caller_phone, customer)
            
            if not agent_id:
                return {
                    "success": False,
                    "error": "No available agents",
                    "call_session_id": call_session_id,
                    "action": "send_to_voicemail"
                }
            
            # Get agent SIP credentials
            agent_sip = self.get_agent_sip_credentials(agent_id)
            
            # Create call session
            call_session = {
                "call_session_id": call_session_id,
                "agent_id": agent_id,
                "customer_phone": caller_phone,
                "customer_id": customer.get("name") if customer else None,
                "call_direction": "inbound",
                "call_status": "ringing",
                "start_time": datetime.now(),
                "agent_sip_uri": f"sip:{agent_sip['username']}@{self.sip_config['sip_domain']}",
                "customer_sip_uri": f"sip:{caller_phone}@{self.sip_config['sip_domain']}",
                "customer_context": customer
            }
            
            # Store session
            self.call_sessions[call_session_id] = call_session
            self.create_call_log(call_session)
            
            # Notify agent of incoming call
            self.notify_agent_incoming_call(agent_id, call_session)
            
            return {
                "success": True,
                "call_session_id": call_session_id,
                "agent_id": agent_id,
                "customer_context": customer,
                "routing_reason": "Available agent found"
            }
            
        except Exception as e:
            frappe.log_error(f"Error handling incoming call: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "call_session_id": None
            }
    
    def update_call_status(self, call_session_id: str, status: str, metadata: Dict = None) -> Dict[str, Any]:
        """
        Update call session status
        
        Args:
            call_session_id: Unique call session identifier
            status: New call status (ringing, connected, on_hold, ended, failed)
            metadata: Additional call metadata
            
        Returns:
            Dict containing update result
        """
        try:
            if call_session_id not in self.call_sessions:
                return {
                    "success": False,
                    "error": "Call session not found"
                }
            
            session = self.call_sessions[call_session_id]
            old_status = session["call_status"]
            session["call_status"] = status
            session["last_updated"] = datetime.now()
            
            if metadata:
                session.update(metadata)
            
            # Handle status-specific logic
            if status == "connected" and old_status != "connected":
                session["connect_time"] = datetime.now()
                self.on_call_connected(session)
                
            elif status == "ended":
                session["end_time"] = datetime.now()
                session["duration"] = self.calculate_call_duration(session)
                self.on_call_ended(session)
                
            elif status == "failed":
                session["end_time"] = datetime.now()
                session["failure_reason"] = metadata.get("reason", "Unknown")
                self.on_call_failed(session)
            
            # Update call log in database
            self.update_call_log(session)
            
            return {
                "success": True,
                "call_session_id": call_session_id,
                "status": status,
                "session": session
            }
            
        except Exception as e:
            frappe.log_error(f"Error updating call status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_agent_sip_credentials(self, agent_id: str) -> Optional[Dict[str, str]]:
        """Get SIP credentials for an agent"""
        try:
            agent_profile = frappe.get_doc("Agent Profile", {"user": agent_id})
            if agent_profile and agent_profile.sip_username:
                return {
                    "username": agent_profile.sip_username,
                    "password": agent_profile.get_password("sip_password"),
                    "display_name": agent_profile.full_name
                }
            else:
                # Generate default SIP credentials
                return {
                    "username": f"agent_{agent_id.replace('@', '_').replace('.', '_')}",
                    "password": frappe.generate_hash(agent_id)[:12],
                    "display_name": agent_id
                }
        except Exception as e:
            frappe.log_error(f"Error getting agent SIP credentials: {str(e)}")
            return None
    
    def find_customer_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find customer record by phone number"""
        try:
            # Search in Customer doctype
            customers = frappe.db.sql("""
                SELECT name, customer_name, mobile_no, phone, email_id
                FROM `tabCustomer`
                WHERE mobile_no = %s OR phone = %s
                LIMIT 1
            """, (phone_number, phone_number), as_dict=True)
            
            if customers:
                customer = customers[0]
                
                # Get recent interaction history
                recent_interactions = frappe.db.sql("""
                    SELECT creation, subject, status
                    FROM `tabOmnichannel Conversation`
                    WHERE customer_phone = %s
                    ORDER BY creation DESC
                    LIMIT 5
                """, (phone_number,), as_dict=True)
                
                customer["recent_interactions"] = recent_interactions
                return customer
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Error finding customer by phone: {str(e)}")
            return None
    
    def route_call_to_agent(self, caller_phone: str, customer: Dict = None) -> Optional[str]:
        """Route incoming call to most appropriate available agent"""
        try:
            # Use existing smart routing service
            from assistant_crm.services.agent_skill_matching_service import AgentSkillMatchingService
            
            agent_matcher = AgentSkillMatchingService()
            
            # Determine required skills based on customer context
            required_skills = ["voice_support", "general_support"]
            if customer:
                # Add specific skills based on customer history
                recent_topics = [i.get("subject", "") for i in customer.get("recent_interactions", [])]
                if any("payment" in topic.lower() for topic in recent_topics):
                    required_skills.append("payments")
                if any("claim" in topic.lower() for topic in recent_topics):
                    required_skills.append("claims")
            
            # Find best available agent
            best_agent = agent_matcher.find_best_agent(
                required_skills=required_skills,
                required_languages=["en"],
                priority_score=75,
                preferred_language="en"
            )
            
            if best_agent and best_agent.get("success"):
                return best_agent["agent"]["user"]
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Error routing call to agent: {str(e)}")
            return None
    
    def create_call_log(self, call_session: Dict[str, Any]) -> str:
        """Create call log record in database"""
        try:
            call_log = frappe.get_doc({
                "doctype": "Call Log",
                "call_session_id": call_session["call_session_id"],
                "agent_id": call_session["agent_id"],
                "customer_phone": call_session["customer_phone"],
                "customer_id": call_session.get("customer_id"),
                "call_direction": call_session["call_direction"],
                "call_status": call_session["call_status"],
                "start_time": call_session["start_time"],
                "agent_sip_uri": call_session["agent_sip_uri"],
                "customer_sip_uri": call_session["customer_sip_uri"]
            })
            call_log.insert()
            frappe.db.commit()
            
            return call_log.name
            
        except Exception as e:
            frappe.log_error(f"Error creating call log: {str(e)}")
            return None

    def update_call_log(self, call_session: Dict[str, Any]) -> bool:
        """Update existing call log record"""
        try:
            call_log = frappe.get_doc("Call Log", {"call_session_id": call_session["call_session_id"]})
            if call_log:
                call_log.call_status = call_session["call_status"]
                call_log.last_updated = call_session.get("last_updated", datetime.now())

                if "connect_time" in call_session:
                    call_log.connect_time = call_session["connect_time"]
                if "end_time" in call_session:
                    call_log.end_time = call_session["end_time"]
                if "duration" in call_session:
                    call_log.duration = call_session["duration"]
                if "failure_reason" in call_session:
                    call_log.failure_reason = call_session["failure_reason"]

                call_log.save()
                frappe.db.commit()
                return True

            return False

        except Exception as e:
            frappe.log_error(f"Error updating call log: {str(e)}")
            return False

    def calculate_call_duration(self, call_session: Dict[str, Any]) -> int:
        """Calculate call duration in seconds"""
        try:
            if "connect_time" in call_session and "end_time" in call_session:
                duration = call_session["end_time"] - call_session["connect_time"]
                return int(duration.total_seconds())
            return 0
        except Exception:
            return 0

    def on_call_connected(self, call_session: Dict[str, Any]):
        """Handle call connected event"""
        try:
            # Create conversation record if customer exists
            if call_session.get("customer_id"):
                self.create_conversation_from_call(call_session)

            # Notify agent of successful connection
            self.notify_agent_call_connected(call_session)

        except Exception as e:
            frappe.log_error(f"Error handling call connected: {str(e)}")

    def on_call_ended(self, call_session: Dict[str, Any]):
        """Handle call ended event"""
        try:
            # Update conversation with call summary
            if call_session.get("conversation_id"):
                self.update_conversation_call_summary(call_session)

            # Clean up session from memory
            if call_session["call_session_id"] in self.call_sessions:
                del self.call_sessions[call_session["call_session_id"]]

            # Update agent availability
            self.update_agent_availability(call_session["agent_id"], "Available")

        except Exception as e:
            frappe.log_error(f"Error handling call ended: {str(e)}")

    def on_call_failed(self, call_session: Dict[str, Any]):
        """Handle call failed event"""
        try:
            # Log failure reason
            frappe.log_error(f"Call failed: {call_session.get('failure_reason', 'Unknown')}")

            # Clean up session
            if call_session["call_session_id"] in self.call_sessions:
                del self.call_sessions[call_session["call_session_id"]]

            # Update agent availability
            self.update_agent_availability(call_session["agent_id"], "Available")

        except Exception as e:
            frappe.log_error(f"Error handling call failed: {str(e)}")

    def create_conversation_from_call(self, call_session: Dict[str, Any]) -> str:
        """Create conversation record from call session"""
        try:
            conversation = frappe.get_doc({
                "doctype": "Omnichannel Conversation",
                "customer_id": call_session.get("customer_id"),
                "customer_phone": call_session["customer_phone"],
                "agent_id": call_session["agent_id"],
                "channel_type": "voice",
                "conversation_status": "Active",
                "subject": f"Voice call from {call_session['customer_phone']}",
                "call_session_id": call_session["call_session_id"],
                "start_time": call_session["start_time"]
            })
            conversation.insert()
            frappe.db.commit()

            # Update call session with conversation ID
            call_session["conversation_id"] = conversation.name

            return conversation.name

        except Exception as e:
            frappe.log_error(f"Error creating conversation from call: {str(e)}")
            return None

    def update_conversation_call_summary(self, call_session: Dict[str, Any]):
        """Update conversation with call summary"""
        try:
            if call_session.get("conversation_id"):
                conversation = frappe.get_doc("Omnichannel Conversation", call_session["conversation_id"])
                conversation.conversation_status = "Closed"
                conversation.end_time = call_session.get("end_time")
                conversation.call_duration = call_session.get("duration", 0)
                conversation.resolution_summary = f"Voice call completed. Duration: {call_session.get('duration', 0)} seconds"
                conversation.save()
                frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error updating conversation call summary: {str(e)}")

    def notify_agent_incoming_call(self, agent_id: str, call_session: Dict[str, Any]):
        """Notify agent of incoming call"""
        try:
            # Create real-time notification
            notification = {
                "type": "incoming_call",
                "call_session_id": call_session["call_session_id"],
                "customer_phone": call_session["customer_phone"],
                "customer_context": call_session.get("customer_context"),
                "timestamp": datetime.now().isoformat()
            }

            # Send via websocket or real-time notification system
            frappe.publish_realtime(
                event="incoming_call",
                message=notification,
                user=agent_id
            )

        except Exception as e:
            frappe.log_error(f"Error notifying agent of incoming call: {str(e)}")

    def notify_agent_call_connected(self, call_session: Dict[str, Any]):
        """Notify agent that call is connected"""
        try:
            notification = {
                "type": "call_connected",
                "call_session_id": call_session["call_session_id"],
                "customer_phone": call_session["customer_phone"],
                "connect_time": call_session.get("connect_time", datetime.now()).isoformat()
            }

            frappe.publish_realtime(
                event="call_connected",
                message=notification,
                user=call_session["agent_id"]
            )

        except Exception as e:
            frappe.log_error(f"Error notifying agent of call connection: {str(e)}")

    def update_agent_availability(self, agent_id: str, status: str):
        """Update agent availability status"""
        try:
            agent_profile = frappe.get_doc("Agent Profile", {"user": agent_id})
            if agent_profile:
                agent_profile.availability_status = status
                agent_profile.save()
                frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error updating agent availability: {str(e)}")

    def get_call_session(self, call_session_id: str) -> Optional[Dict[str, Any]]:
        """Get call session by ID"""
        return self.call_sessions.get(call_session_id)

    def get_active_calls_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all active calls for an agent"""
        active_calls = []
        for session in self.call_sessions.values():
            if (session["agent_id"] == agent_id and
                session["call_status"] in ["ringing", "connected", "on_hold"]):
                active_calls.append(session)
        return active_calls

    def get_call_statistics(self, agent_id: str = None, date_range: Dict = None) -> Dict[str, Any]:
        """Get call statistics for reporting"""
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

            stats = frappe.db.sql(f"""
                SELECT
                    COUNT(*) as total_calls,
                    COUNT(CASE WHEN call_status = 'ended' THEN 1 END) as completed_calls,
                    COUNT(CASE WHEN call_status = 'failed' THEN 1 END) as failed_calls,
                    COUNT(CASE WHEN call_direction = 'inbound' THEN 1 END) as inbound_calls,
                    COUNT(CASE WHEN call_direction = 'outbound' THEN 1 END) as outbound_calls,
                    AVG(CASE WHEN duration > 0 THEN duration END) as avg_duration,
                    SUM(CASE WHEN duration > 0 THEN duration END) as total_duration
                FROM `tabCall Log`
                WHERE {where_clause}
            """, values, as_dict=True)

            return stats[0] if stats else {}

        except Exception as e:
            frappe.log_error(f"Error getting call statistics: {str(e)}")
            return {}
