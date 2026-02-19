import frappe
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import hmac
import base64


class AdvancedSocialMediaService:
    """
    Advanced Social Media Integration Service for WCFCB Assistant CRM
    Phase B: Telegram, LinkedIn, Twitter/X Integration
    Compliance Target: 98/100 score
    """
    
    def __init__(self):
        self.telegram_config = self.get_telegram_configuration()
        self.linkedin_config = self.get_linkedin_configuration()
        self.twitter_config = self.get_twitter_configuration()
        
    def get_telegram_configuration(self) -> Dict[str, Any]:
        """Get Telegram Bot API configuration"""
        try:
            settings = frappe.get_single("Advanced Social Media Settings")
            return {
                "bot_token": settings.get("telegram_bot_token"),
                "webhook_url": settings.get("telegram_webhook_url"),
                "api_url": f"https://api.telegram.org/bot{settings.get('telegram_bot_token', '')}",
                "enabled": settings.get("telegram_enabled", 0),
                "auto_response": settings.get("telegram_auto_response", 1),
                "business_hours_only": settings.get("telegram_business_hours_only", 1)
            }
        except Exception:
            return {
                "bot_token": "",
                "webhook_url": "",
                "api_url": "",
                "enabled": 0,
                "auto_response": 1,
                "business_hours_only": 1
            }
    
    def get_linkedin_configuration(self) -> Dict[str, Any]:
        """Get LinkedIn API configuration"""
        try:
            settings = frappe.get_single("Advanced Social Media Settings")
            return {
                "client_id": settings.get("linkedin_client_id"),
                "client_secret": settings.get("linkedin_client_secret"),
                "access_token": settings.get("linkedin_access_token"),
                "company_id": settings.get("linkedin_company_id"),
                "api_version": settings.get("linkedin_api_version", "v2"),
                "enabled": settings.get("linkedin_enabled", 0),
                "auto_response": settings.get("linkedin_auto_response", 1)
            }
        except Exception:
            return {
                "client_id": "",
                "client_secret": "",
                "access_token": "",
                "company_id": "",
                "api_version": "v2",
                "enabled": 0,
                "auto_response": 1
            }
    
    def get_twitter_configuration(self) -> Dict[str, Any]:
        """Get Twitter/X API configuration"""
        try:
            settings = frappe.get_single("Advanced Social Media Settings")
            return {
                "api_key": settings.get("twitter_api_key"),
                "api_secret": settings.get("twitter_api_secret"),
                "access_token": settings.get("twitter_access_token"),
                "access_token_secret": settings.get("twitter_access_token_secret"),
                "bearer_token": settings.get("twitter_bearer_token"),
                "api_version": settings.get("twitter_api_version", "2"),
                "enabled": settings.get("twitter_enabled", 0),
                "auto_response": settings.get("twitter_auto_response", 1)
            }
        except Exception:
            return {
                "api_key": "",
                "api_secret": "",
                "access_token": "",
                "access_token_secret": "",
                "bearer_token": "",
                "api_version": "2",
                "enabled": 0,
                "auto_response": 1
            }
    
    def handle_telegram_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Telegram webhook events"""
        try:
            if not self.telegram_config["enabled"]:
                return {"success": False, "error": "Telegram integration disabled"}
            
            # Extract message data
            message = data.get("message", {})
            if not message:
                return {"success": True, "message": "No message to process"}
            
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            username = message.get("from", {}).get("username", "")
            first_name = message.get("from", {}).get("first_name", "")
            last_name = message.get("from", {}).get("last_name", "")
            message_text = message.get("text", "")
            message_id = message.get("message_id")
            timestamp = message.get("date")
            
            # Create conversation record
            conversation_id = self.create_telegram_conversation(
                chat_id=chat_id,
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                message_text=message_text,
                message_id=message_id,
                timestamp=timestamp
            )
            
            # Route to appropriate agent
            routing_result = self.route_telegram_message(
                conversation_id=conversation_id,
                message_text=message_text,
                user_info={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name
                }
            )
            
            # Send auto-response if enabled and during business hours
            if (self.telegram_config["auto_response"] and 
                self.is_business_hours() if self.telegram_config["business_hours_only"] else True):
                self.send_telegram_auto_response(chat_id, message_text)
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "routing_result": routing_result,
                "platform": "telegram"
            }
            
        except Exception as e:
            frappe.log_error(title="Telegram Webhook Failed", message=f"Error handling Telegram webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_linkedin_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LinkedIn webhook events (messages, comments)"""
        try:
            if not self.linkedin_config["enabled"]:
                return {"success": False, "error": "LinkedIn integration disabled"}
            
            # Process LinkedIn webhook data
            # LinkedIn uses different webhook formats for different events
            event_type = data.get("eventType", "")
            
            if event_type == "MESSAGE_EVENT":
                return self.process_linkedin_message(data)
            elif event_type == "COMMENT_EVENT":
                return self.process_linkedin_comment(data)
            else:
                return {"success": True, "message": f"Unhandled event type: {event_type}"}
            
        except Exception as e:
            frappe.log_error(title="LinkedIn Webhook Failed", message=f"Error handling LinkedIn webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_twitter_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Twitter/X webhook events (mentions, DMs)"""
        try:
            if not self.twitter_config["enabled"]:
                return {"success": False, "error": "Twitter integration disabled"}
            
            # Process Twitter webhook data
            if "direct_message_events" in data:
                return self.process_twitter_dm(data["direct_message_events"])
            elif "tweet_create_events" in data:
                return self.process_twitter_mentions(data["tweet_create_events"])
            else:
                return {"success": True, "message": "No relevant events to process"}
            
        except Exception as e:
            frappe.log_error(title="Twitter Webhook Failed", message=f"Error handling Twitter webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_telegram_message(self, chat_id: str, message_text: str, conversation_id: str = None) -> Dict[str, Any]:
        """Send message via Telegram Bot API"""
        try:
            if not self.telegram_config["enabled"]:
                return {"success": False, "error": "Telegram integration disabled"}
            
            url = f"{self.telegram_config['api_url']}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("ok"):
                # Log outbound message
                if conversation_id:
                    self.log_outbound_message(
                        conversation_id=conversation_id,
                        message_text=message_text,
                        platform="telegram",
                        platform_message_id=str(result["result"]["message_id"])
                    )
                
                return {
                    "success": True,
                    "message_id": result["result"]["message_id"],
                    "chat_id": chat_id
                }
            else:
                return {
                    "success": False,
                    "error": result.get("description", "Unknown error")
                }
            
        except Exception as e:
            frappe.log_error(title="Telegram Send Failed", message=f"Error sending Telegram message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_linkedin_message(self, recipient_id: str, message_text: str, conversation_id: str = None) -> Dict[str, Any]:
        """Send message via LinkedIn Messaging API"""
        try:
            if not self.linkedin_config["enabled"]:
                return {"success": False, "error": "LinkedIn integration disabled"}
            
            url = f"https://api.linkedin.com/{self.linkedin_config['api_version']}/messaging/conversations"
            
            headers = {
                "Authorization": f"Bearer {self.linkedin_config['access_token']}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            payload = {
                "recipients": [recipient_id],
                "subject": "Message from WCFCB",
                "body": {
                    "text": message_text
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # Log outbound message
            if conversation_id:
                self.log_outbound_message(
                    conversation_id=conversation_id,
                    message_text=message_text,
                    platform="linkedin",
                    platform_message_id=result.get("id", "")
                )
            
            return {
                "success": True,
                "conversation_id": result.get("id"),
                "recipient_id": recipient_id
            }
            
        except Exception as e:
            frappe.log_error(title="LinkedIn Send Failed", message=f"Error sending LinkedIn message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_twitter_dm(self, recipient_id: str, message_text: str, conversation_id: str = None) -> Dict[str, Any]:
        """Send direct message via Twitter API"""
        try:
            if not self.twitter_config["enabled"]:
                return {"success": False, "error": "Twitter integration disabled"}
            
            url = "https://api.twitter.com/2/dm_conversations/with/{}/messages".format(recipient_id)
            
            headers = {
                "Authorization": f"Bearer {self.twitter_config['bearer_token']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": message_text,
                "media_id": None  # Can be extended for media support
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # Log outbound message
            if conversation_id:
                self.log_outbound_message(
                    conversation_id=conversation_id,
                    message_text=message_text,
                    platform="twitter",
                    platform_message_id=result.get("data", {}).get("dm_event_id", "")
                )
            
            return {
                "success": True,
                "dm_event_id": result.get("data", {}).get("dm_event_id"),
                "recipient_id": recipient_id
            }
            
        except Exception as e:
            frappe.log_error(title="Twitter DM Failed", message=f"Error sending Twitter DM: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_telegram_conversation(self, chat_id: str, user_id: str, username: str, 
                                   first_name: str, last_name: str, message_text: str,
                                   message_id: int, timestamp: int) -> str:
        """Create conversation record for Telegram message"""
        try:
            message_time = datetime.fromtimestamp(timestamp)
            full_name = f"{first_name} {last_name}".strip() or username or f"User {user_id}"
            
            conversation = frappe.get_doc({
                "doctype": "Omnichannel Conversation",
                "customer_name": full_name,
                "channel_type": "telegram",
                "conversation_status": "Open",
                "subject": f"Telegram message from {full_name}",
                "platform_user_id": str(user_id),
                "platform_message_id": str(message_id),
                "start_time": message_time,
                "last_message_time": message_time,
                "message_count": 1,
                "platform_data": json.dumps({
                    "chat_id": chat_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "platform": "telegram"
                })
            })
            conversation.insert()
            
            # Create initial message record
            self.create_message_record(
                conversation_id=conversation.name,
                sender_id=str(user_id),
                message_text=message_text,
                message_id=str(message_id),
                timestamp=message_time,
                platform="telegram"
            )
            
            frappe.db.commit()
            return conversation.name
            
        except Exception as e:
            frappe.log_error(title="Telegram Convo Failed", message=f"Error creating Telegram conversation: {str(e)}")
            return None

    def process_linkedin_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process LinkedIn message event"""
        try:
            message_data = data.get("data", {})
            sender_id = message_data.get("from", {}).get("id")
            message_text = message_data.get("body", {}).get("text", "")
            message_id = message_data.get("id")
            timestamp = message_data.get("createdAt", int(datetime.now().timestamp() * 1000))

            # Get sender information
            sender_info = self.get_linkedin_user_info(sender_id)

            # Create conversation
            conversation_id = self.create_linkedin_conversation(
                sender_id=sender_id,
                sender_info=sender_info,
                message_text=message_text,
                message_id=message_id,
                timestamp=timestamp
            )

            # Route message
            routing_result = self.route_linkedin_message(
                conversation_id=conversation_id,
                message_text=message_text,
                sender_info=sender_info
            )

            return {
                "success": True,
                "conversation_id": conversation_id,
                "routing_result": routing_result,
                "platform": "linkedin"
            }

        except Exception as e:
            frappe.log_error(title="LinkedIn Process Failed", message=f"Error processing LinkedIn message: {str(e)}")
            return {"success": False, "error": str(e)}

    def process_twitter_dm(self, dm_events: List[Dict]) -> Dict[str, Any]:
        """Process Twitter direct message events"""
        try:
            processed_messages = []

            for dm_event in dm_events:
                sender_id = dm_event.get("message_create", {}).get("sender_id")
                message_text = dm_event.get("message_create", {}).get("message_data", {}).get("text", "")
                message_id = dm_event.get("id")
                timestamp = int(dm_event.get("created_timestamp", "0"))

                # Get sender information
                sender_info = self.get_twitter_user_info(sender_id)

                # Create conversation
                conversation_id = self.create_twitter_conversation(
                    sender_id=sender_id,
                    sender_info=sender_info,
                    message_text=message_text,
                    message_id=message_id,
                    timestamp=timestamp
                )

                # Route message
                routing_result = self.route_twitter_message(
                    conversation_id=conversation_id,
                    message_text=message_text,
                    sender_info=sender_info
                )

                processed_messages.append({
                    "conversation_id": conversation_id,
                    "routing_result": routing_result
                })

            return {
                "success": True,
                "processed_messages": processed_messages,
                "count": len(processed_messages),
                "platform": "twitter"
            }

        except Exception as e:
            frappe.log_error(title="Twitter DM Process Failed", message=f"Error processing Twitter DMs: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_linkedin_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get LinkedIn user information"""
        try:
            url = f"https://api.linkedin.com/{self.linkedin_config['api_version']}/people/{user_id}"
            headers = {
                "Authorization": f"Bearer {self.linkedin_config['access_token']}"
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            user_data = response.json()
            return {
                "first_name": user_data.get("firstName", {}).get("localized", {}).get("en_US", ""),
                "last_name": user_data.get("lastName", {}).get("localized", {}).get("en_US", ""),
                "headline": user_data.get("headline", {}).get("localized", {}).get("en_US", ""),
                "profile_picture": user_data.get("profilePicture", {}).get("displayImage", ""),
                "full_name": f"{user_data.get('firstName', {}).get('localized', {}).get('en_US', '')} {user_data.get('lastName', {}).get('localized', {}).get('en_US', '')}".strip()
            }

        except Exception as e:
            frappe.log_error(title="LinkedIn User Info Failed", message=f"Error getting LinkedIn user info: {str(e)}")
            return {
                "first_name": "",
                "last_name": "",
                "headline": "",
                "profile_picture": "",
                "full_name": "Unknown LinkedIn User"
            }

    def get_twitter_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get Twitter user information"""
        try:
            url = f"https://api.twitter.com/2/users/{user_id}"
            headers = {
                "Authorization": f"Bearer {self.twitter_config['bearer_token']}"
            }
            params = {
                "user.fields": "name,username,profile_image_url,description"
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()
            user_data = result.get("data", {})

            return {
                "name": user_data.get("name", ""),
                "username": user_data.get("username", ""),
                "description": user_data.get("description", ""),
                "profile_image": user_data.get("profile_image_url", ""),
                "full_name": user_data.get("name", user_data.get("username", "Unknown Twitter User"))
            }

        except Exception as e:
            frappe.log_error(title="Twitter User Info Failed", message=f"Error getting Twitter user info: {str(e)}")
            return {
                "name": "",
                "username": "",
                "description": "",
                "profile_image": "",
                "full_name": "Unknown Twitter User"
            }

    def route_telegram_message(self, conversation_id: str, message_text: str, user_info: Dict) -> Dict[str, Any]:
        """Route Telegram message to appropriate agent"""
        try:
            from assistant_crm.services.omnichannel_router import OmnichannelRouter

            router = OmnichannelRouter()
            routing_result = router.smart_route_conversation(
                conversation_id=conversation_id,
                message_content=message_text,
                customer_data={
                    "name": f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip(),
                    "platform": "telegram"
                }
            )

            return routing_result

        except Exception as e:
            frappe.log_error(title="Telegram Routing Failed", message=f"Error routing Telegram message: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_telegram_auto_response(self, chat_id: str, message_text: str):
        """Send automatic response for Telegram"""
        try:
            # Generate appropriate auto-response based on message content
            from assistant_crm.services.wcfcb_ai_service import WCFCBAIService

            ai_service = WCFCBAIService()
            auto_response = ai_service.generate_auto_response(
                message_content=message_text,
                platform="telegram",
                response_type="acknowledgment"
            )

            if auto_response and auto_response.get("response"):
                self.send_telegram_message(chat_id, auto_response["response"])

        except Exception as e:
            frappe.log_error(title="Telegram Auto-Response Failed", message=f"Error sending Telegram auto-response: {str(e)}")

    def is_business_hours(self) -> bool:
        """Check if current time is within business hours using centralized utility."""
        try:
            from assistant_crm.business_utils import is_business_hours
            return is_business_hours()
        except Exception:
            return True  # Default to allowing responses

        except Exception:
            return True  # Default to allowing responses

    def create_message_record(self, conversation_id: str, sender_id: str, message_text: str,
                            message_id: str, timestamp: datetime, platform: str):
        """Create message record in database"""
        try:
            message = frappe.get_doc({
                "doctype": "Omnichannel Message",
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "message_content": message_text,
                "message_type": "text",
                "channel_type": platform,
                "platform_message_id": message_id,
                "timestamp": timestamp,
                "is_inbound": 1,
                "message_status": "received"
            })
            message.insert()

        except Exception as e:
            frappe.log_error(title="Record Creation Failed", message=f"Error creating message record: {str(e)}")

    def log_outbound_message(self, conversation_id: str, message_text: str, platform: str, platform_message_id: str = None):
        """Log outbound message to database"""
        try:
            message = frappe.get_doc({
                "doctype": "Omnichannel Message",
                "conversation_id": conversation_id,
                "sender_id": frappe.session.user,
                "message_content": message_text,
                "message_type": "text",
                "channel_type": platform,
                "platform_message_id": platform_message_id,
                "timestamp": datetime.now(),
                "is_inbound": 0,
                "message_status": "sent"
            })
            message.insert()

            # Update conversation last message time
            conversation = frappe.get_doc("Omnichannel Conversation", conversation_id)
            conversation.last_message_time = datetime.now()
            conversation.message_count = (conversation.message_count or 0) + 1
            conversation.save()

            frappe.db.commit()

        except Exception as e:
            frappe.log_error(title="Outbound Log Failed", message=f"Error logging outbound message: {str(e)}")
