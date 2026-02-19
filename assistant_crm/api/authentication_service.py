#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Authentication Service
Multi-factor authentication system for secure chatbot user verification
Maintains WorkCom's warm personality throughout authentication flows
"""

import frappe
import hashlib
import secrets
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class AuthenticationService:
    """
    Comprehensive authentication service for Assistant CRM users
    Supports multiple verification methods while preserving WorkCom's personality
    """
    
    def __init__(self):
        self.session_timeout = 30 * 60  # 30 minutes in seconds
        self.max_auth_attempts = 3
        self.otp_validity = 5 * 60  # 5 minutes for OTP
        
    def initiate_authentication(self, user_input: str, conversation_context: Dict) -> Dict:
        """
        Initiate authentication process based on user input
        Maintains WorkCom's warm, professional tone throughout
        """
        try:
            # Analyze user input for authentication triggers
            auth_triggers = self.detect_authentication_triggers(user_input)
            
            if not auth_triggers:
                return {
                    "requires_auth": False,
                    "response": self.generate_general_response(user_input),
                    "next_step": "continue_conversation"
                }
            
            # Determine authentication method needed
            auth_method = self.determine_auth_method(auth_triggers, conversation_context)
            
            # Generate WorkCom's warm authentication request
            auth_response = self.generate_auth_request(auth_method, conversation_context)
            
            return {
                "requires_auth": True,
                "auth_method": auth_method,
                "response": auth_response,
                "next_step": "collect_credentials",
                "session_id": self.create_temp_session(conversation_context)
            }
            
        except Exception as e:
            frappe.log_error(f"Authentication initiation error: {str(e)}")
            return {
                "requires_auth": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    def detect_authentication_triggers(self, user_input: str) -> List[str]:
        """
        Detect if user input requires authentication for data access
        """
        auth_keywords = {
            "claim_status": ["claim status", "my claim", "claim number", "claim progress"],
            "payment_info": ["payment", "compensation", "benefits", "when paid"],
            "personal_data": ["my information", "my profile", "my details", "update"],
            "medical_info": ["medical", "doctor", "treatment", "injury"],
            "employer_data": ["company", "employer", "workplace", "employees"]
        }
        
        user_input_lower = user_input.lower()
        triggers = []
        
        for category, keywords in auth_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                triggers.append(category)
        
        return triggers
    
    def determine_auth_method(self, triggers: List[str], context: Dict) -> str:
        """
        Determine appropriate authentication method based on data sensitivity
        """
        high_security_triggers = ["payment_info", "medical_info", "personal_data"]
        
        if any(trigger in high_security_triggers for trigger in triggers):
            return "enhanced_verification"
        else:
            return "basic_verification"
    
    def generate_auth_request(self, auth_method: str, context: Dict) -> str:
        """
        Generate WorkCom's warm, professional authentication request
        """
        if auth_method == "basic_verification":
            return """Hi there! I'd be happy to help you with your personal information. 😊

To make sure I'm providing your details to the right person, I'll need to verify your identity first. This keeps your information safe and secure.

Could you please provide your claim number? If you don't have it handy, I can help you find it with some basic details."""
        
        elif auth_method == "enhanced_verification":
            return """I'd love to help you access your personal information! 😊

Since this involves sensitive details, I need to verify your identity with a couple of steps to keep your information secure. Don't worry - it's quick and easy!

Let's start with your claim number. If you don't have it available, I can look it up using your name and date of birth."""
        
        else:
            return """Hello! I'm here to help you access your information securely. 😊

To get started, I'll need to verify who you are. This is just to make sure your personal details stay private and secure.

What information would you like to access today?"""
    
    def verify_claim_number(self, claim_number: str, session_context: Dict) -> Dict:
        """
        Verify claim number and retrieve basic claim information
        """
        try:
            # Sanitize claim number input
            clean_claim_number = self.sanitize_claim_number(claim_number)
            
            if not self.validate_claim_format(clean_claim_number):
                return {
                    "verified": False,
                    "response": """I'm having trouble with that claim number format. 😊

WCFCB claim numbers usually look like 'WC-2024-001234' or similar. Could you please double-check and try again?

If you're not sure about your claim number, I can help you find it using your name and date of birth instead.""",
                    "next_step": "retry_claim_number"
                }
            
            # Check if claim exists (simulated for now)
            claim_data = self.lookup_claim(clean_claim_number)
            
            if not claim_data:
                return {
                    "verified": False,
                    "response": """I couldn't find a claim with that number in our system. 😊

This might be because:
• The claim number was entered incorrectly
• The claim is very new and still being processed
• You might be thinking of a different reference number

Would you like to try again, or shall I help you find your claim using your personal details instead?""",
                    "next_step": "alternative_verification"
                }
            
            # Store claim context for session
            session_context["verified_claim"] = clean_claim_number
            session_context["claim_data"] = claim_data
            
            return {
                "verified": True,
                "response": f"""Perfect! I found your claim {clean_claim_number}. 😊

For additional security, could you please confirm your full name as it appears on the claim?""",
                "next_step": "verify_personal_details",
                "claim_data": claim_data
            }
            
        except Exception as e:
            frappe.log_error(f"Claim verification error: {str(e)}")
            return {
                "verified": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    def verify_personal_details(self, name: str, dob: str, session_context: Dict) -> Dict:
        """
        Verify personal details against claim information
        """
        try:
            claim_data = session_context.get("claim_data", {})
            
            # Normalize inputs for comparison
            provided_name = self.normalize_name(name)
            provided_dob = self.normalize_date(dob)
            
            # Compare with claim data (simulated verification)
            stored_name = self.normalize_name(claim_data.get("claimant_name", ""))
            stored_dob = self.normalize_date(claim_data.get("date_of_birth", ""))
            
            if provided_name == stored_name and provided_dob == stored_dob:
                # Successful verification
                session_context["identity_verified"] = True
                session_context["verification_time"] = datetime.now().isoformat()
                
                return {
                    "verified": True,
                    "response": """Excellent! I've verified your identity successfully. 😊

You now have secure access to your personal information. How can I help you today?

I can provide information about:
• Your claim status and progress
• Payment details and schedules  
• Medical provider information
• Contact details and updates

What would you like to know?""",
                    "next_step": "authenticated_conversation",
                    "session_context": session_context
                }
            else:
                # Failed verification
                attempts = session_context.get("auth_attempts", 0) + 1
                session_context["auth_attempts"] = attempts
                
                if attempts >= self.max_auth_attempts:
                    return {
                        "verified": False,
                        "response": """I'm sorry, but I wasn't able to verify your identity after several attempts. 😔

For your security, I need to end this verification process. Please contact our support team directly at:

📞 Phone: +260-XXX-XXXX
📧 Email: support@wcfcb.gov.zm

They'll be able to help you access your information safely. Is there anything else I can help you with that doesn't require personal verification?""",
                        "next_step": "end_auth_session"
                    }
                else:
                    return {
                        "verified": False,
                        "response": f"""The details don't quite match what I have on file. 😊

Please double-check and try again. Make sure to use:
• Your full name exactly as it appears on official documents
• Your date of birth in DD/MM/YYYY format

You have {self.max_auth_attempts - attempts} more attempt(s). Would you like to try again?""",
                        "next_step": "retry_personal_details"
                    }
                    
        except Exception as e:
            frappe.log_error(f"Personal details verification error: {str(e)}")
            return {
                "verified": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    def initiate_sms_verification(self, phone_number: str, session_context: Dict) -> Dict:
        """
        Initiate SMS OTP verification for enhanced security
        """
        try:
            # Validate phone number format
            clean_phone = self.sanitize_phone_number(phone_number)
            
            if not self.validate_phone_format(clean_phone):
                return {
                    "success": False,
                    "response": """I need a valid phone number to send you a verification code. 😊

Please provide your phone number in one of these formats:
• +260-XXX-XXXXXX
• 0XXX-XXXXXX
• XXXXXXXXXX

This should be the number we have on file for your account."""
                }
            
            # Generate OTP
            otp_code = self.generate_otp()
            
            # Store OTP in session (encrypted)
            session_context["otp_code"] = self.encrypt_otp(otp_code)
            session_context["otp_phone"] = clean_phone
            session_context["otp_generated"] = datetime.now().isoformat()
            
            # Simulate SMS sending (in production, integrate with SMS service)
            sms_sent = self.send_sms_otp(clean_phone, otp_code)
            
            if sms_sent:
                return {
                    "success": True,
                    "response": f"""Perfect! I've sent a 6-digit verification code to {self.mask_phone_number(clean_phone)}. 😊

The code will arrive within a few moments and is valid for 5 minutes.

Please enter the code when you receive it, and I'll complete your verification!""",
                    "next_step": "verify_otp"
                }
            else:
                return {
                    "success": False,
                    "response": """I'm having trouble sending the verification code right now. 😔

Let's try a different verification method. I can verify your identity using your claim number and personal details instead.

Would you like to proceed with that option?"""
                }
                
        except Exception as e:
            frappe.log_error(f"SMS verification error: {str(e)}")
            return {
                "success": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    def verify_otp(self, provided_otp: str, session_context: Dict) -> Dict:
        """
        Verify SMS OTP code
        """
        try:
            stored_otp = session_context.get("otp_code")
            otp_generated_time = session_context.get("otp_generated")
            
            if not stored_otp or not otp_generated_time:
                return {
                    "verified": False,
                    "response": """I don't have an active verification code for you. 😊

Let's start the verification process again. Would you like me to send a new code?"""
                }
            
            # Check OTP expiry
            generated_time = datetime.fromisoformat(otp_generated_time)
            if datetime.now() - generated_time > timedelta(seconds=self.otp_validity):
                return {
                    "verified": False,
                    "response": """The verification code has expired. 😊

For security, codes are only valid for 5 minutes. Would you like me to send you a new one?""",
                    "next_step": "resend_otp"
                }
            
            # Verify OTP
            if self.decrypt_and_verify_otp(provided_otp, stored_otp):
                session_context["sms_verified"] = True
                session_context["verification_complete"] = True
                
                return {
                    "verified": True,
                    "response": """Excellent! Your identity has been fully verified. 😊

You now have secure access to all your personal information. I'm ready to help you with:

• Detailed claim status and history
• Payment information and schedules
• Medical provider details
• Document uploads and updates
• Contact information changes

What would you like to know about today?""",
                    "next_step": "full_access_conversation"
                }
            else:
                attempts = session_context.get("otp_attempts", 0) + 1
                session_context["otp_attempts"] = attempts
                
                if attempts >= self.max_auth_attempts:
                    return {
                        "verified": False,
                        "response": """I'm sorry, but the verification code doesn't match after several attempts. 😔

For your security, I need to end this verification session. You can:

• Try the verification process again from the beginning
• Contact our support team for assistance: +260-XXX-XXXX

Is there anything else I can help you with that doesn't require verification?""",
                        "next_step": "end_verification"
                    }
                else:
                    return {
                        "verified": False,
                        "response": f"""That code doesn't match what I sent. 😊

Please check the code and try again. Make sure to enter all 6 digits exactly as received.

You have {self.max_auth_attempts - attempts} more attempt(s).""",
                        "next_step": "retry_otp"
                    }
                    
        except Exception as e:
            frappe.log_error(f"OTP verification error: {str(e)}")
            return {
                "verified": False,
                "response": self.generate_error_response(),
                "error": str(e)
            }
    
    # Utility Methods
    
    def sanitize_claim_number(self, claim_number: str) -> str:
        """Sanitize and format claim number"""
        return claim_number.strip().upper().replace(" ", "")
    
    def validate_claim_format(self, claim_number: str) -> bool:
        """Validate claim number format"""
        import re
        pattern = r'^WC-\d{4}-\d{6}$'
        return bool(re.match(pattern, claim_number))
    
    def lookup_claim(self, claim_number: str) -> Optional[Dict]:
        """
        Lookup claim in database (simulated for now)
        In production, this would query the actual WCFCB database
        """
        # Simulated claim data
        mock_claims = {
            "WC-2024-001234": {
                "claimant_name": "John Doe",
                "date_of_birth": "15/01/1985",
                "claim_status": "Medical Review",
                "injury_date": "20/02/2024",
                "employer": "TechCorp Industries"
            },
            "WC-2024-005678": {
                "claimant_name": "Sarah Johnson", 
                "date_of_birth": "15/03/1990",
                "claim_status": "Awaiting Rating",
                "injury_date": "20/02/2024",
                "employer": "Manufacturing Ltd"
            }
        }
        
        return mock_claims.get(claim_number)
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        return name.strip().lower().replace("  ", " ")
    
    def normalize_date(self, date_str: str) -> str:
        """Normalize date format for comparison"""
        # Handle various date formats
        import re
        date_str = re.sub(r'[^\d/]', '', date_str)
        return date_str.strip()
    
    def sanitize_phone_number(self, phone: str) -> str:
        """Sanitize phone number"""
        import re
        return re.sub(r'[^\d+]', '', phone)
    
    def validate_phone_format(self, phone: str) -> bool:
        """Validate phone number format"""
        import re
        patterns = [
            r'^\+260\d{9}$',  # +260XXXXXXXXX
            r'^0\d{9}$',      # 0XXXXXXXXX
            r'^\d{9}$'        # XXXXXXXXX
        ]
        return any(re.match(pattern, phone) for pattern in patterns)
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return f"{secrets.randbelow(1000000):06d}"
    
    def encrypt_otp(self, otp: str) -> str:
        """Encrypt OTP for storage"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    def decrypt_and_verify_otp(self, provided_otp: str, stored_hash: str) -> bool:
        """Verify OTP against stored hash"""
        provided_hash = hashlib.sha256(provided_otp.encode()).hexdigest()
        return provided_hash == stored_hash
    
    def mask_phone_number(self, phone: str) -> str:
        """Mask phone number for display"""
        if len(phone) >= 4:
            return f"***-{phone[-4:]}"
        return "***-****"
    
    def send_sms_otp(self, phone: str, otp: str) -> bool:
        """
        Send SMS OTP (simulated for now)
        In production, integrate with SMS service provider
        """
        # Simulate SMS sending
        frappe.log_error(f"SMS OTP sent to {phone}: {otp} (SIMULATION)")
        return True
    
    def create_temp_session(self, context: Dict) -> str:
        """Create temporary session for authentication process"""
        session_id = secrets.token_urlsafe(32)
        # In production, store in Redis or database
        return session_id
    
    def generate_general_response(self, user_input: str) -> str:
        """Generate general response for non-authenticated queries"""
        return """Hi there! I'm WorkCom, your WCFCB assistant. 😊

I'm here to help you with information about workers' compensation, claims processes, and general WCFCB services.

For personal information about your specific claim or account, I'll need to verify your identity first to keep your details secure.

How can I help you today?"""
    
    def generate_error_response(self) -> str:
        """Generate friendly error response maintaining WorkCom's personality"""
        return """I'm sorry, but I'm having a small technical difficulty right now. 😔

Please try again in a moment, or if you need immediate assistance, you can contact our support team:

📞 Phone: +260-XXX-XXXX
📧 Email: support@wcfcb.gov.zm

I'm here to help as soon as this is resolved!"""

# API Endpoints for Authentication Service

@frappe.whitelist()
def initiate_chat_authentication():
    """
    API endpoint to initiate authentication for chatbot users
    """
    try:
        data = frappe.local.form_dict
        user_input = data.get("message", "")
        conversation_context = data.get("context", {})
        
        auth_service = AuthenticationService()
        result = auth_service.initiate_authentication(user_input, conversation_context)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        frappe.log_error(f"Chat authentication API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def verify_user_credentials():
    """
    API endpoint to verify user credentials
    """
    try:
        data = frappe.local.form_dict
        verification_type = data.get("type", "")
        credentials = data.get("credentials", {})
        session_context = data.get("session_context", {})
        
        auth_service = AuthenticationService()
        
        if verification_type == "claim_number":
            result = auth_service.verify_claim_number(
                credentials.get("claim_number", ""),
                session_context
            )
        elif verification_type == "personal_details":
            result = auth_service.verify_personal_details(
                credentials.get("name", ""),
                credentials.get("dob", ""),
                session_context
            )
        elif verification_type == "sms_otp":
            result = auth_service.verify_otp(
                credentials.get("otp", ""),
                session_context
            )
        else:
            result = {
                "verified": False,
                "response": "Invalid verification type specified."
            }
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        frappe.log_error(f"Credential verification API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

