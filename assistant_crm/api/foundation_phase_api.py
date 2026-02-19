#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Foundation Phase API
Main integration layer for authentication, session management, and data access
Provides unified interface for WorkCom's live data capabilities while preserving existing functionality
"""

import frappe
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from .authentication_service import AuthenticationService
from .session_manager import SessionManager
from .data_connection_manager import DataConnectionManager

class FoundationPhaseAPI:
    """
    Foundation Phase API that coordinates authentication, sessions, and data access
    Provides unified interface for WorkCom's live data capabilities
    """
    
    def __init__(self):
        self.auth_service = AuthenticationService()
        self.session_manager = SessionManager()
        self.data_manager = DataConnectionManager()
        
    def process_chat_message(self, message: str, session_id: str = None, 
                           conversation_context: Dict = None) -> Dict:
        """
        Main entry point for processing chat messages with live data integration
        """
        try:
            conversation_context = conversation_context or {}
            
            # Check if session exists and is valid
            session_data = None
            if session_id:
                session_data = self.session_manager.get_session(session_id)
            
            # Determine if message requires authentication
            auth_result = self.auth_service.initiate_authentication(message, conversation_context)
            
            if auth_result["requires_auth"] and not session_data:
                # Start authentication process
                return {
                    "success": True,
                    "response": auth_result["response"],
                    "requires_auth": True,
                    "auth_method": auth_result.get("auth_method"),
                    "session_id": auth_result.get("session_id"),
                    "next_step": auth_result.get("next_step")
                }
            
            elif session_data and session_data.get("identity_verified"):
                # User is authenticated, process live data request
                return self.process_authenticated_message(message, session_data)
            
            else:
                # General conversation without authentication
                return self.process_general_message(message, conversation_context)
                
        except Exception as e:
            frappe.log_error(f"Foundation Phase chat processing error: {str(e)}")
            return {
                "success": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    def process_authenticated_message(self, message: str, session_data: Dict) -> Dict:
        """
        Process message from authenticated user with live data access
        """
        try:
            user_permissions = session_data.get("permissions", [])
            user_id = session_data.get("user_id")
            user_type = session_data.get("user_type")
            
            # Analyze message for data requests
            data_request = self.analyze_data_request(message, user_type)
            
            if data_request["is_data_request"]:
                # Fetch live data
                live_data_result = self.fetch_live_data(data_request, user_permissions, user_id)
                
                if live_data_result["success"]:
                    # Generate personalized response with live data
                    response = self.generate_data_response(
                        live_data_result["data"], 
                        data_request["request_type"],
                        user_type,
                        session_data
                    )
                    
                    # Update conversation history
                    self.session_manager.add_conversation_turn(
                        session_data["session_id"], message, response, data_request
                    )
                    
                    return {
                        "success": True,
                        "response": response,
                        "data_provided": True,
                        "data_type": data_request["request_type"],
                        "session_id": session_data["session_id"]
                    }
                else:
                    # Data fetch failed, provide fallback response
                    fallback_response = self.generate_fallback_response(
                        data_request["request_type"], live_data_result.get("error")
                    )
                    
                    return {
                        "success": True,
                        "response": fallback_response,
                        "data_provided": False,
                        "fallback_used": True,
                        "session_id": session_data["session_id"]
                    }
            else:
                # General conversation with authenticated context
                response = self.generate_contextual_response(message, session_data)
                
                self.session_manager.add_conversation_turn(
                    session_data["session_id"], message, response
                )
                
                return {
                    "success": True,
                    "response": response,
                    "data_provided": False,
                    "session_id": session_data["session_id"]
                }
                
        except Exception as e:
            frappe.log_error(f"Authenticated message processing error: {str(e)}")
            return {
                "success": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    def analyze_data_request(self, message: str, user_type: str) -> Dict:
        """
        Analyze message to determine if it's a data request and what type
        """
        message_lower = message.lower()
        
        # Define data request patterns by user type
        data_patterns = {
            "beneficiary": {
                "claim_status": ["claim status", "my claim", "claim progress", "case status"],
                "payment_info": ["payment", "compensation", "benefits", "money", "paid"],
                "medical_info": ["doctor", "medical", "treatment", "appointment"],
                "profile_info": ["my information", "my details", "contact", "address"]
            },
            "employer": {
                "employee_claims": ["employee claims", "worker claims", "staff claims"],
                "compliance_status": ["compliance", "premium", "safety", "training"],
                "company_info": ["company", "business", "employer"],
                "reports": ["report", "analytics", "statistics", "summary"]
            },
            "staff": {
                "case_management": ["case", "claim", "file", "review"],
                "user_lookup": ["user", "claimant", "employee", "lookup"],
                "system_status": ["system", "performance", "status", "health"],
                "analytics": ["analytics", "reports", "trends", "statistics"]
            }
        }
        
        user_patterns = data_patterns.get(user_type, data_patterns["beneficiary"])
        
        for request_type, keywords in user_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return {
                    "is_data_request": True,
                    "request_type": request_type,
                    "confidence": 0.8,
                    "extracted_params": self.extract_request_parameters(message, request_type)
                }
        
        return {
            "is_data_request": False,
            "request_type": None,
            "confidence": 0.0
        }
    
    def extract_request_parameters(self, message: str, request_type: str) -> Dict:
        """
        Extract parameters from message based on request type
        """
        import re
        
        params = {}
        
        if request_type in ["claim_status", "case_management"]:
            # Look for claim numbers
            claim_pattern = r'WC-\d{4}-\d{6}'
            claim_match = re.search(claim_pattern, message.upper())
            if claim_match:
                params["claim_number"] = claim_match.group()
        
        elif request_type == "payment_info":
            # Look for date ranges or specific payment types
            if "last" in message.lower():
                params["include_recent"] = True
            if "history" in message.lower():
                params["include_history"] = True
        
        return params
    
    def fetch_live_data(self, data_request: Dict, user_permissions: List[str], 
                       user_id: str) -> Dict:
        """
        Fetch live data based on request type and user permissions
        """
        try:
            request_type = data_request["request_type"]
            params = data_request.get("extracted_params", {})
            
            if request_type == "claim_status":
                claim_number = params.get("claim_number")
                if claim_number:
                    return self.data_manager.retrieve_claim_data(claim_number, user_permissions)
                else:
                    # Look up user's claims
                    return self.data_manager.get_live_data("user_claims", {"user_id": user_id}, user_permissions)
            
            elif request_type == "payment_info":
                return self.data_manager.retrieve_payment_information(user_id, user_permissions)
            
            elif request_type == "profile_info":
                return self.data_manager.retrieve_user_profile(user_id, user_permissions)
            
            elif request_type == "compliance_status":
                return self.data_manager.retrieve_employer_data(user_id, user_permissions)
            
            elif request_type == "medical_info":
                return self.data_manager.retrieve_medical_providers()
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported request type: {request_type}"
                }
                
        except Exception as e:
            frappe.log_error(f"Live data fetch error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_data_response(self, data: Dict, request_type: str, user_type: str, 
                             session_data: Dict) -> str:
        """
        Generate WorkCom's response with live data, maintaining her personality
        """
        user_name = session_data.get("verification_data", {}).get("claimant_name", "")
        first_name = user_name.split()[0] if user_name else ""
        
        if request_type == "claim_status":
            claim_data = data.get("data", {})
            if claim_data:
                return f"""Great news{f', {first_name}' if first_name else ''}! I have your current claim information. 😊

**Claim {claim_data.get('claim_number')}** - {claim_data.get('injury_type', 'Workplace Injury')}

📋 **Current Status**: {claim_data.get('status', 'In Progress')}
📅 **Current Stage**: {claim_data.get('current_stage', 'Under Review')}
⏭️ **Next Action**: {claim_data.get('next_action', 'Pending Review')}
🎯 **Expected Completion**: {claim_data.get('estimated_completion', 'TBD')}

{f"👩‍💼 **Your Case Manager**: {claim_data.get('case_manager')}" if claim_data.get('case_manager') else ""}

Your case is progressing well! Is there anything specific about your claim you'd like to know more about?"""
            
        elif request_type == "payment_info":
            payment_data = data.get("data", {})
            current_benefits = payment_data.get("current_benefits", {})
            
            if current_benefits:
                temp_disability = current_benefits.get("temporary_disability", {})
                return f"""Here's your current payment information{f', {first_name}' if first_name else ''}! 😊

💰 **Current Weekly Benefits**: ${temp_disability.get('weekly_amount', 0)}
📅 **Last Payment**: {temp_disability.get('last_payment', 'N/A')}
📅 **Next Payment**: {temp_disability.get('next_payment', 'TBD')}

Your payments are on schedule! They'll continue until your case reaches final resolution.

Would you like me to explain how your benefit amount was calculated, or do you have questions about upcoming payments?"""
        
        else:
            return f"""I have the information you requested{f', {first_name}' if first_name else ''}! 😊

{json.dumps(data, indent=2)}

Is there anything specific about this information you'd like me to explain further?"""
    
    def generate_fallback_response(self, request_type: str, error: str = None) -> str:
        """
        Generate fallback response when live data is unavailable
        """
        return f"""I'm sorry, but I'm having trouble accessing your live information right now. 😔

This might be due to:
• Temporary system maintenance
• Network connectivity issues
• High system load

In the meantime, I can still help you with:
• General information about WCFCB services
• Contact information for direct assistance
• Guidance on processes and procedures

Would you like me to help you with any of these, or would you prefer to try again in a few minutes?

For immediate assistance, you can also contact our support team:
📞 Phone: +260-XXX-XXXX
📧 Email: support@wcfcb.gov.zm"""
    
    def generate_contextual_response(self, message: str, session_data: Dict) -> str:
        """
        Generate contextual response for authenticated users
        """
        user_name = session_data.get("verification_data", {}).get("claimant_name", "")
        first_name = user_name.split()[0] if user_name else ""
        user_type = session_data.get("user_type", "beneficiary")
        
        # Personalized greeting based on user type
        if user_type == "beneficiary":
            return f"""I'm here to help you{f', {first_name}' if first_name else ''}! 😊

Since you're verified, I can provide you with personalized information about:
• Your claim status and progress
• Payment schedules and benefit information
• Medical provider details
• Contact information updates

What would you like to know about today?"""
        
        elif user_type == "employer":
            return f"""Hello{f', {first_name}' if first_name else ''}! I'm ready to assist with your business needs. 😊

I can help you with:
• Employee claim status and management
• Compliance requirements and status
• Premium information and payments
• Safety training and reporting
• Bulk operations and reporting

How can I help optimize your workers' compensation management today?"""
        
        else:
            return f"""Hello{f', {first_name}' if first_name else ''}! I'm here to help with your WCFCB needs. 😊

How can I assist you today?"""
    
    def process_general_message(self, message: str, context: Dict) -> Dict:
        """
        Process general message without authentication - preserves existing functionality
        """
        # Use existing static response system for general queries
        general_response = """Hi there! I'm WorkCom, your WCFCB assistant. 😊

I'm here to help you with information about workers' compensation, claims processes, and general WCFCB services.

For personal information about your specific claim or account, I'll need to verify your identity first to keep your details secure.

How can I help you today?"""
        
        return {
            "success": True,
            "response": general_response,
            "requires_auth": False,
            "data_provided": False
        }
    
    def generate_error_response(self) -> str:
        """Generate friendly error response maintaining WorkCom's personality"""
        return """I'm sorry, but I'm having a small technical difficulty right now. 😔

Please try again in a moment, or if you need immediate assistance, you can contact our support team:

📞 Phone: +260-XXX-XXXX
📧 Email: support@wcfcb.gov.zm

I'm here to help as soon as this is resolved!"""

# Foundation Phase API Endpoints

@frappe.whitelist()
def process_foundation_chat():
    """
    Foundation Phase API endpoint for processing chat messages with live data integration
    """
    try:
        data = frappe.local.form_dict
        message = data.get("message", "")
        session_id = data.get("session_id")
        conversation_context = data.get("conversation_context", {})
        
        api = FoundationPhaseAPI()
        result = api.process_chat_message(message, session_id, conversation_context)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        frappe.log_error(f"Foundation Phase chat API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def test_foundation_components():
    """
    Test endpoint to verify Foundation Phase components are working
    """
    try:
        results = {}
        
        # Test Authentication Service
        try:
            auth_service = AuthenticationService()
            auth_test = auth_service.initiate_authentication("I need my claim status", {})
            results["authentication_service"] = {
                "status": "working",
                "test_result": auth_test.get("requires_auth", False)
            }
        except Exception as e:
            results["authentication_service"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Test Session Manager
        try:
            session_manager = SessionManager()
            session_test = session_manager.create_session("test_user", "beneficiary", ["read_own_claims"])
            results["session_manager"] = {
                "status": "working",
                "test_result": session_test.get("success", False)
            }
        except Exception as e:
            results["session_manager"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Test Data Connection Manager
        try:
            data_manager = DataConnectionManager()
            data_test = data_manager.get_live_data("claim_details", {"claim_number": "WC-2024-001234"}, ["read_own_claims"])
            results["data_connection_manager"] = {
                "status": "working",
                "test_result": data_test.get("success", False)
            }
        except Exception as e:
            results["data_connection_manager"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall status
        working_components = len([r for r in results.values() if r.get("status") == "working"])
        total_components = len(results)
        
        return {
            "success": True,
            "foundation_phase_status": "operational" if working_components == total_components else "partial",
            "components_working": f"{working_components}/{total_components}",
            "component_details": results,
            "message": "Foundation Phase components tested successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Foundation Phase test error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

