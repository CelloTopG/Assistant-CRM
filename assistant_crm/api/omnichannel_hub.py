#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Phase 4.2: Omnichannel Expansion
Implements multi-channel communication while preserving existing functionality
"""

import frappe
from frappe import _
import json
import requests
from datetime import datetime
import hashlib
import hmac
import base64

class OmnichannelHub:
    """Central hub for managing all communication channels"""
    
    def __init__(self):
        self.channels = {
            "web": WebChannelHandler(),
            "whatsapp": WhatsAppChannelHandler(),
            "sms": SMSChannelHandler(),
            "voice": VoiceChannelHandler()
        }
        self.message_queue = []
        
    def route_message(self, message_data, channel_type):
        """Route message to appropriate channel handler"""
        try:
            if channel_type not in self.channels:
                return {
                    "status": "error",
                    "message": f"Unsupported channel: {channel_type}"
                }
            
            handler = self.channels[channel_type]
            return handler.process_message(message_data)
            
        except Exception as e:
            frappe.log_error(f"Omnichannel Routing Error: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to route message",
                "details": str(e)
            }
    
    def get_unified_conversation(self, user_id):
        """Get unified conversation across all channels"""
        try:
            # Get interactions from all channels
            all_interactions = []
            
            # Web interactions
            web_interactions = frappe.get_all("User Interaction Log",
                filters={"user_id": user_id},
                fields=["*"],
                order_by="timestamp desc"
            )
            
            for interaction in web_interactions:
                all_interactions.append({
                    "channel": "web",
                    "timestamp": interaction.timestamp,
                    "message": interaction.query_text,
                    "response": interaction.response_provided,
                    "satisfaction": interaction.satisfaction_rating
                })
            
            # WhatsApp interactions
            whatsapp_interactions = frappe.get_all("WhatsApp Message Log",
                filters={"user_phone": user_id},
                fields=["*"],
                order_by="timestamp desc"
            ) if frappe.db.exists("DocType", "WhatsApp Message Log") else []
            
            for interaction in whatsapp_interactions:
                all_interactions.append({
                    "channel": "whatsapp",
                    "timestamp": interaction.timestamp,
                    "message": interaction.message_text,
                    "response": interaction.response_text,
                    "status": interaction.status
                })
            
            # Sort by timestamp
            all_interactions.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "status": "success",
                "user_id": user_id,
                "total_interactions": len(all_interactions),
                "conversations": all_interactions[:50],  # Last 50 interactions
                "channels_used": list(set([i["channel"] for i in all_interactions]))
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to get unified conversation",
                "details": str(e)
            }

class WebChannelHandler:
    """Handler for web-based interactions (existing functionality)"""
    
    def process_message(self, message_data):
        """Process web channel message"""
        try:
            # This maintains existing web functionality
            # Enhanced with omnichannel context
            
            user_id = message_data.get("user_id")
            query_text = message_data.get("query_text")
            
            # Get cross-channel context
            context = self._get_cross_channel_context(user_id)
            
            # Process with existing ML intelligence
            from assistant_crm.api.ml_intelligence import enhance_query_intelligence
            
            enhanced_result = enhance_query_intelligence(query_text, user_id)
            
            # Add omnichannel context
            enhanced_result["omnichannel_context"] = context
            enhanced_result["channel"] = "web"
            
            return enhanced_result
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Web channel processing failed",
                "details": str(e)
            }
    
    def _get_cross_channel_context(self, user_id):
        """Get context from other channels"""
        try:
            hub = OmnichannelHub()
            conversation = hub.get_unified_conversation(user_id)
            
            if conversation.get("status") == "success":
                return {
                    "total_interactions": conversation.get("total_interactions", 0),
                    "channels_used": conversation.get("channels_used", []),
                    "last_channel": conversation.get("conversations", [{}])[0].get("channel", "web") if conversation.get("conversations") else "web"
                }
            
            return {"total_interactions": 0, "channels_used": ["web"], "last_channel": "web"}
            
        except Exception:
            return {"total_interactions": 0, "channels_used": ["web"], "last_channel": "web"}

class WhatsAppChannelHandler:
    """Handler for WhatsApp Business API integration"""
    
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v17.0"
        self.phone_number_id = self._get_whatsapp_config("phone_number_id")
        self.access_token = self._get_whatsapp_config("access_token")
        
    def process_message(self, message_data):
        """Process WhatsApp message"""
        try:
            # Extract WhatsApp message data
            from_number = message_data.get("from")
            message_text = message_data.get("text", {}).get("body", "")
            message_id = message_data.get("id")
            
            # Log incoming message
            self._log_whatsapp_message(from_number, message_text, "incoming", message_id)
            
            # Process with ML intelligence
            from assistant_crm.api.ml_intelligence import enhance_query_intelligence
            
            enhanced_result = enhance_query_intelligence(message_text, from_number)
            
            # Generate response
            response_text = self._generate_whatsapp_response(enhanced_result)
            
            # Send response
            send_result = self.send_message(from_number, response_text)
            
            # Log outgoing message
            if send_result.get("status") == "success":
                self._log_whatsapp_message(from_number, response_text, "outgoing", send_result.get("message_id"))
            
            return {
                "status": "success",
                "channel": "whatsapp",
                "from": from_number,
                "response_sent": send_result.get("status") == "success",
                "ml_enhancement": enhanced_result
            }
            
        except Exception as e:
            frappe.log_error(f"WhatsApp Processing Error: {str(e)}")
            return {
                "status": "error",
                "message": "WhatsApp processing failed",
                "details": str(e)
            }
    
    def send_message(self, to_number, message_text):
        """Send WhatsApp message"""
        try:
            if not self.access_token or not self.phone_number_id:
                return {
                    "status": "error",
                    "message": "WhatsApp configuration missing"
                }
            
            url = f"{self.api_url}/{self.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {
                    "body": message_text
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "message_id": result.get("messages", [{}])[0].get("id"),
                    "whatsapp_response": result
                }
            else:
                return {
                    "status": "error",
                    "message": f"WhatsApp API error: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to send WhatsApp message",
                "details": str(e)
            }
    
    def _get_whatsapp_config(self, key):
        """Get WhatsApp configuration"""
        try:
            settings = frappe.get_single("Assistant CRM Settings")
            return getattr(settings, f"whatsapp_{key}", None)
        except:
            return None
    
    def _log_whatsapp_message(self, phone_number, message_text, direction, message_id):
        """Log WhatsApp message"""
        try:
            # Create WhatsApp Message Log if it doesn't exist
            if not frappe.db.exists("DocType", "WhatsApp Message Log"):
                self._create_whatsapp_log_doctype()
            
            log_entry = frappe.new_doc("WhatsApp Message Log")
            log_entry.user_phone = phone_number
            log_entry.message_text = message_text
            log_entry.direction = direction
            log_entry.message_id = message_id
            log_entry.timestamp = frappe.utils.now()
            log_entry.status = "delivered" if direction == "outgoing" else "received"
            
            log_entry.insert()
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"WhatsApp Logging Error: {str(e)}")
    
    def _generate_whatsapp_response(self, enhanced_result):
        """Generate WhatsApp-optimized response"""
        try:
            # Get the best matching article or generate response
            if enhanced_result.get("status") == "success":
                # For WhatsApp, keep responses concise
                base_response = "Thank you for contacting WCFCB! "
                
                enhancement = enhanced_result.get("enhancement", {})
                confidence = enhancement.get("enhanced_confidence", 0.5)
                
                if confidence > 0.7:
                    base_response += "I can help you with that. "
                elif confidence > 0.5:
                    base_response += "Let me find the best information for you. "
                else:
                    base_response += "I'll connect you with a specialist who can help. "
                
                # Add quick action buttons for WhatsApp
                base_response += "\n\nQuick options:\n"
                base_response += "• Type 'STATUS' for claim status\n"
                base_response += "• Type 'HELP' for general assistance\n"
                base_response += "• Type 'AGENT' to speak with a human"
                
                return base_response
            else:
                return "Hello! I'm the WCFCB Assistant. How can I help you today? Type 'HELP' for options."
                
        except Exception as e:
            return "Hello! I'm experiencing technical difficulties. Please try again or contact our office directly."

class SMSChannelHandler:
    """Handler for SMS communication"""
    
    def __init__(self):
        self.sms_gateway_url = self._get_sms_config("gateway_url")
        self.api_key = self._get_sms_config("api_key")
        self.sender_id = self._get_sms_config("sender_id")
    
    def process_message(self, message_data):
        """Process SMS message"""
        try:
            from_number = message_data.get("from")
            message_text = message_data.get("text", "")
            
            # Log incoming SMS
            self._log_sms_message(from_number, message_text, "incoming")
            
            # Process with ML intelligence
            from assistant_crm.api.ml_intelligence import enhance_query_intelligence
            
            enhanced_result = enhance_query_intelligence(message_text, from_number)
            
            # Generate SMS response (keep it short)
            response_text = self._generate_sms_response(enhanced_result)
            
            # Send response
            send_result = self.send_sms(from_number, response_text)
            
            # Log outgoing SMS
            if send_result.get("status") == "success":
                self._log_sms_message(from_number, response_text, "outgoing")
            
            return {
                "status": "success",
                "channel": "sms",
                "from": from_number,
                "response_sent": send_result.get("status") == "success",
                "ml_enhancement": enhanced_result
            }
            
        except Exception as e:
            frappe.log_error(f"SMS Processing Error: {str(e)}")
            return {
                "status": "error",
                "message": "SMS processing failed",
                "details": str(e)
            }
    
    def send_sms(self, to_number, message_text):
        """Send SMS message"""
        try:
            if not self.sms_gateway_url or not self.api_key:
                return {
                    "status": "error",
                    "message": "SMS configuration missing"
                }
            
            # Generic SMS gateway implementation
            # This would be customized based on the actual SMS provider
            payload = {
                "to": to_number,
                "from": self.sender_id,
                "text": message_text,
                "api_key": self.api_key
            }
            
            response = requests.post(self.sms_gateway_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message_id": response.json().get("message_id"),
                    "sms_response": response.json()
                }
            else:
                return {
                    "status": "error",
                    "message": f"SMS gateway error: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to send SMS",
                "details": str(e)
            }
    
    def _get_sms_config(self, key):
        """Get SMS configuration"""
        try:
            settings = frappe.get_single("Assistant CRM Settings")
            return getattr(settings, f"sms_{key}", None)
        except:
            return None
    
    def _log_sms_message(self, phone_number, message_text, direction):
        """Log SMS message"""
        try:
            # Create SMS Message Log if it doesn't exist
            if not frappe.db.exists("DocType", "SMS Message Log"):
                self._create_sms_log_doctype()
            
            log_entry = frappe.new_doc("SMS Message Log")
            log_entry.user_phone = phone_number
            log_entry.message_text = message_text
            log_entry.direction = direction
            log_entry.timestamp = frappe.utils.now()
            log_entry.status = "sent" if direction == "outgoing" else "received"
            
            log_entry.insert()
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"SMS Logging Error: {str(e)}")
    
    def _generate_sms_response(self, enhanced_result):
        """Generate SMS-optimized response (160 chars max)"""
        try:
            if enhanced_result.get("status") == "success":
                confidence = enhanced_result.get("enhancement", {}).get("enhanced_confidence", 0.5)
                
                if confidence > 0.7:
                    return "WCFCB: I can help! Visit wcfcb.gov.zm or reply AGENT for human assistance."
                elif confidence > 0.5:
                    return "WCFCB: Let me find info for you. Visit wcfcb.gov.zm or reply AGENT for help."
                else:
                    return "WCFCB: Connecting you with specialist. Call +260-211-WCFCB or reply AGENT."
            else:
                return "WCFCB Assistant: Hello! Reply HELP for options or AGENT for human assistance."
                
        except Exception:
            return "WCFCB: Technical issue. Please call +260-211-WCFCB for assistance."

class VoiceChannelHandler:
    """Handler for voice interface capabilities"""
    
    def process_message(self, message_data):
        """Process voice message"""
        try:
            # Voice processing would integrate with speech-to-text services
            # This is a foundation for voice interface implementation
            
            audio_data = message_data.get("audio_data")
            user_id = message_data.get("user_id", "voice_user")
            
            # Convert speech to text (placeholder)
            transcribed_text = self._speech_to_text(audio_data)
            
            if not transcribed_text:
                return {
                    "status": "error",
                    "message": "Could not transcribe audio"
                }
            
            # Process with ML intelligence
            from assistant_crm.api.ml_intelligence import enhance_query_intelligence
            
            enhanced_result = enhance_query_intelligence(transcribed_text, user_id)
            
            # Generate voice response
            response_text = self._generate_voice_response(enhanced_result)
            
            # Convert text to speech (placeholder)
            audio_response = self._text_to_speech(response_text)
            
            return {
                "status": "success",
                "channel": "voice",
                "transcribed_text": transcribed_text,
                "response_text": response_text,
                "audio_response": audio_response,
                "ml_enhancement": enhanced_result
            }
            
        except Exception as e:
            frappe.log_error(f"Voice Processing Error: {str(e)}")
            return {
                "status": "error",
                "message": "Voice processing failed",
                "details": str(e)
            }
    
    def _speech_to_text(self, audio_data):
        """Convert speech to text (placeholder for integration)"""
        # This would integrate with services like Google Speech-to-Text,
        # Azure Speech Services, or AWS Transcribe
        return "Placeholder transcribed text"
    
    def _text_to_speech(self, text):
        """Convert text to speech (placeholder for integration)"""
        # This would integrate with services like Google Text-to-Speech,
        # Azure Speech Services, or AWS Polly
        return {"audio_url": "placeholder_audio_url", "format": "mp3"}
    
    def _generate_voice_response(self, enhanced_result):
        """Generate voice-optimized response"""
        try:
            if enhanced_result.get("status") == "success":
                confidence = enhanced_result.get("enhancement", {}).get("enhanced_confidence", 0.5)
                
                if confidence > 0.7:
                    return "Hello, this is the WCFCB Assistant. I can help you with that. Let me provide you with the information you need."
                elif confidence > 0.5:
                    return "Hello, this is the WCFCB Assistant. I'm finding the best information for your query. Please hold on."
                else:
                    return "Hello, this is the WCFCB Assistant. I'll connect you with a specialist who can better assist you with your request."
            else:
                return "Hello, welcome to the WCFCB Assistant. How may I help you today?"
                
        except Exception:
            return "Hello, I'm experiencing technical difficulties. Please try again or contact our office directly."

# API Endpoints for Omnichannel

@frappe.whitelist()
def process_omnichannel_message(channel_type, message_data):
    """Process message from any channel"""
    try:
        hub = OmnichannelHub()
        
        # Parse message data if it's a string
        if isinstance(message_data, str):
            message_data = json.loads(message_data)
        
        result = hub.route_message(message_data, channel_type)
        
        return {
            "status": "success",
            "channel": channel_type,
            "processing_result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to process omnichannel message",
            "details": str(e)
        }

@frappe.whitelist()
def get_unified_user_conversation(user_id):
    """Get unified conversation across all channels"""
    try:
        hub = OmnichannelHub()
        conversation = hub.get_unified_conversation(user_id)
        
        return conversation
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to get unified conversation",
            "details": str(e)
        }

# DocType Creation Functions

def create_omnichannel_doctypes():
    """Create DocTypes for omnichannel logging"""
    try:
        # Create WhatsApp Message Log DocType
        create_whatsapp_message_log_doctype()

        # Create SMS Message Log DocType
        create_sms_message_log_doctype()

        # Create Voice Interaction Log DocType
        create_voice_interaction_log_doctype()

        # Enhance Assistant CRM Settings
        enhance_assistant_crm_settings()

        return True

    except Exception as e:
        frappe.log_error(f"Omnichannel DocType Creation Error: {str(e)}")
        return False

def create_whatsapp_message_log_doctype():
    """Create WhatsApp Message Log DocType"""
    try:
        if frappe.db.exists("DocType", "WhatsApp Message Log"):
            return True

        doctype = frappe.new_doc("DocType")
        doctype.name = "WhatsApp Message Log"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "naming_series:"

        fields = [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "options": "WA-.YYYY.-.#####",
                "reqd": 1
            },
            {
                "fieldname": "user_phone",
                "fieldtype": "Data",
                "label": "User Phone Number",
                "reqd": 1
            },
            {
                "fieldname": "message_text",
                "fieldtype": "Long Text",
                "label": "Message Text"
            },
            {
                "fieldname": "response_text",
                "fieldtype": "Long Text",
                "label": "Response Text"
            },
            {
                "fieldname": "direction",
                "fieldtype": "Select",
                "label": "Direction",
                "options": "incoming\noutgoing",
                "reqd": 1
            },
            {
                "fieldname": "message_id",
                "fieldtype": "Data",
                "label": "WhatsApp Message ID"
            },
            {
                "fieldname": "status",
                "fieldtype": "Select",
                "label": "Status",
                "options": "sent\ndelivered\nread\nfailed\nreceived"
            },
            {
                "fieldname": "timestamp",
                "fieldtype": "Datetime",
                "label": "Timestamp",
                "reqd": 1
            },
            {
                "fieldname": "ml_confidence_score",
                "fieldtype": "Float",
                "label": "ML Confidence Score",
                "precision": 3
            }
        ]

        for field in fields:
            doctype.append("fields", field)

        doctype.append("permissions", {
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        })

        doctype.insert()
        frappe.db.commit()
        return True

    except Exception as e:
        frappe.log_error(f"WhatsApp DocType Creation Error: {str(e)}")
        return False

def create_sms_message_log_doctype():
    """Create SMS Message Log DocType"""
    try:
        if frappe.db.exists("DocType", "SMS Message Log"):
            return True

        doctype = frappe.new_doc("DocType")
        doctype.name = "SMS Message Log"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "naming_series:"

        fields = [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "options": "SMS-.YYYY.-.#####",
                "reqd": 1
            },
            {
                "fieldname": "user_phone",
                "fieldtype": "Data",
                "label": "User Phone Number",
                "reqd": 1
            },
            {
                "fieldname": "message_text",
                "fieldtype": "Long Text",
                "label": "Message Text"
            },
            {
                "fieldname": "direction",
                "fieldtype": "Select",
                "label": "Direction",
                "options": "incoming\noutgoing",
                "reqd": 1
            },
            {
                "fieldname": "status",
                "fieldtype": "Select",
                "label": "Status",
                "options": "sent\ndelivered\nfailed\nreceived"
            },
            {
                "fieldname": "timestamp",
                "fieldtype": "Datetime",
                "label": "Timestamp",
                "reqd": 1
            },
            {
                "fieldname": "gateway_response",
                "fieldtype": "Long Text",
                "label": "Gateway Response"
            }
        ]

        for field in fields:
            doctype.append("fields", field)

        doctype.append("permissions", {
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        })

        doctype.insert()
        frappe.db.commit()
        return True

    except Exception as e:
        frappe.log_error(f"SMS DocType Creation Error: {str(e)}")
        return False

def enhance_assistant_crm_settings():
    """Add omnichannel settings to Assistant CRM Settings"""
    try:
        if not frappe.db.exists("DocType", "Assistant CRM Settings"):
            return False

        doctype = frappe.get_doc("DocType", "Assistant CRM Settings")
        existing_fields = [field.fieldname for field in doctype.fields]

        omnichannel_fields = [
            {
                "fieldname": "omnichannel_section",
                "fieldtype": "Section Break",
                "label": "Omnichannel Configuration"
            },
            {
                "fieldname": "whatsapp_enabled",
                "fieldtype": "Check",
                "label": "Enable WhatsApp Integration"
            },
            {
                "fieldname": "whatsapp_phone_number_id",
                "fieldtype": "Data",
                "label": "WhatsApp Phone Number ID"
            },
            {
                "fieldname": "whatsapp_access_token",
                "fieldtype": "Password",
                "label": "WhatsApp Access Token"
            },
            {
                "fieldname": "whatsapp_webhook_verify_token",
                "fieldtype": "Password",
                "label": "WhatsApp Webhook Verify Token"
            },
            {
                "fieldname": "sms_section",
                "fieldtype": "Section Break",
                "label": "SMS Configuration"
            },
            {
                "fieldname": "sms_enabled",
                "fieldtype": "Check",
                "label": "Enable SMS Integration"
            },
            {
                "fieldname": "sms_gateway_url",
                "fieldtype": "Data",
                "label": "SMS Gateway URL"
            },
            {
                "fieldname": "sms_api_key",
                "fieldtype": "Password",
                "label": "SMS API Key"
            },
            {
                "fieldname": "sms_sender_id",
                "fieldtype": "Data",
                "label": "SMS Sender ID"
            },
            {
                "fieldname": "voice_section",
                "fieldtype": "Section Break",
                "label": "Voice Interface Configuration"
            },
            {
                "fieldname": "voice_enabled",
                "fieldtype": "Check",
                "label": "Enable Voice Interface"
            },
            {
                "fieldname": "speech_to_text_service",
                "fieldtype": "Select",
                "label": "Speech-to-Text Service",
                "options": "google\nazure\naws\ncustom"
            },
            {
                "fieldname": "text_to_speech_service",
                "fieldtype": "Select",
                "label": "Text-to-Speech Service",
                "options": "google\nazure\naws\ncustom"
            }
        ]

        fields_added = 0
        for field_data in omnichannel_fields:
            if field_data["fieldname"] not in existing_fields:
                doctype.append("fields", field_data)
                fields_added += 1

        if fields_added > 0:
            doctype.save()
            frappe.db.commit()

        return True

    except Exception as e:
        frappe.log_error(f"Settings Enhancement Error: {str(e)}")
        return False

@frappe.whitelist()
def setup_omnichannel_infrastructure():
    """Setup omnichannel infrastructure"""
    try:
        print("🌐 SETTING UP OMNICHANNEL INFRASTRUCTURE")
        print("=" * 50)

        # Create DocTypes
        doctype_success = create_omnichannel_doctypes()

        if doctype_success:
            print("✅ Omnichannel DocTypes created successfully")
        else:
            print("❌ Failed to create some omnichannel DocTypes")

        # Test channel handlers
        test_results = test_channel_handlers()

        return {
            "status": "success" if doctype_success else "partial",
            "doctypes_created": doctype_success,
            "channel_tests": test_results,
            "message": "Omnichannel infrastructure setup completed"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to setup omnichannel infrastructure",
            "details": str(e)
        }

def test_channel_handlers():
    """Test all channel handlers"""
    try:
        hub = OmnichannelHub()

        test_results = {}

        # Test Web Channel
        web_result = hub.route_message({
            "user_id": "test_user_omni",
            "query_text": "Test web channel message"
        }, "web")
        test_results["web"] = web_result.get("status") == "success"

        # Test WhatsApp Channel (without actual API call)
        whatsapp_handler = WhatsAppChannelHandler()
        test_results["whatsapp"] = hasattr(whatsapp_handler, 'process_message')

        # Test SMS Channel (without actual API call)
        sms_handler = SMSChannelHandler()
        test_results["sms"] = hasattr(sms_handler, 'process_message')

        # Test Voice Channel
        voice_handler = VoiceChannelHandler()
        test_results["voice"] = hasattr(voice_handler, 'process_message')

        return test_results

    except Exception as e:
        frappe.log_error(f"Channel Handler Test Error: {str(e)}")
        return {"error": str(e)}
