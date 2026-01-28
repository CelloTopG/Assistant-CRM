import frappe
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import hmac


class SocialMediaIntegrationService:
    """
    Social Media Integration Service for WCFCB Assistant CRM
    Handles Facebook Messenger, Instagram Direct Messages, and other social platforms
    """
    
    def __init__(self):
        self.facebook_config = self.get_facebook_configuration()
        self.instagram_config = self.get_instagram_configuration()
        self.webhook_verify_token = self.get_webhook_verify_token()
        
    def get_facebook_configuration(self) -> Dict[str, Any]:
        """Get Facebook API configuration"""
        try:
            settings = frappe.get_single("Social Media Settings")
            return {
                "app_id": settings.get("facebook_app_id"),
                "app_secret": settings.get("facebook_app_secret"),
                "page_access_token": settings.get("facebook_page_access_token"),
                "page_id": settings.get("facebook_page_id"),
                "api_version": settings.get("facebook_api_version", "v18.0"),
                "enabled": settings.get("facebook_enabled", 0)
            }
        except Exception:
            return {
                "app_id": "",
                "app_secret": "",
                "page_access_token": "",
                "page_id": "",
                "api_version": "v18.0",
                "enabled": 0
            }
    
    def get_instagram_configuration(self) -> Dict[str, Any]:
        """Get Instagram API configuration"""
        try:
            settings = frappe.get_single("Social Media Settings")
            return {
                "business_account_id": settings.get("instagram_business_account_id"),
                "access_token": settings.get("instagram_access_token"),
                "api_version": settings.get("instagram_api_version", "v18.0"),
                "enabled": settings.get("instagram_enabled", 0)
            }
        except Exception:
            return {
                "business_account_id": "",
                "access_token": "",
                "api_version": "v18.0",
                "enabled": 0
            }
    
    def get_webhook_verify_token(self) -> str:
        """Get webhook verification token"""
        try:
            settings = frappe.get_single("Social Media Settings")
            return settings.get("webhook_verify_token", "wcfcb_webhook_verify_token")
        except Exception:
            return "wcfcb_webhook_verify_token"
    
    def verify_webhook_signature(self, payload: str, signature: str, platform: str = "facebook") -> bool:
        """Verify webhook signature for security"""
        try:
            if platform == "facebook":
                app_secret = self.facebook_config["app_secret"]
            else:
                app_secret = self.instagram_config.get("app_secret", self.facebook_config["app_secret"])
            
            if not app_secret:
                return False
            
            # Calculate expected signature
            expected_signature = hmac.new(
                app_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
            
        except Exception as e:
            frappe.log_error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def send_facebook_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Send Facebook Messenger message"""
        try:
            if not self.facebook_config["enabled"]:
                return {"success": False, "error": "Facebook integration disabled"}

            if not self.facebook_config["page_access_token"]:
                return {"success": False, "error": "Facebook page access token not configured"}

            url = f"https://graph.facebook.com/{self.facebook_config['api_version']}/me/messages"
            headers = {
                "Authorization": f"Bearer {self.facebook_config['page_access_token']}",
                "Content-Type": "application/json"
            }

            data = {
                "recipient": {"id": recipient_id},
                "message": {"text": message}
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "recipient_id": recipient_id
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                }

        except Exception as e:
            frappe.log_error(f"Facebook send error: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_facebook_bulk_messages(self, recipients: List[Dict], message: str) -> Dict[str, Any]:
        """Send bulk Facebook Messenger messages"""
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "results": []
        }

        for recipient in recipients:
            facebook_id = recipient.get("facebook_id") or recipient.get("messenger_id")
            if not facebook_id:
                results["failed"] += 1
                results["results"].append({
                    "recipient": recipient.get("email_id", "Unknown"),
                    "success": False,
                    "error": "No Facebook ID"
                })
                continue

            result = self.send_facebook_message(facebook_id, message)

            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1

            results["results"].append({
                "recipient": recipient.get("email_id", facebook_id),
                "facebook_id": facebook_id,
                **result
            })

        return results

    def send_instagram_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """Send Instagram Direct Message"""
        try:
            if not self.instagram_config["enabled"]:
                return {"success": False, "error": "Instagram integration disabled"}

            if not self.instagram_config["access_token"]:
                return {"success": False, "error": "Instagram access token not configured"}

            url = f"https://graph.facebook.com/{self.instagram_config['api_version']}/{self.instagram_config['business_account_id']}/messages"
            headers = {
                "Authorization": f"Bearer {self.instagram_config['access_token']}",
                "Content-Type": "application/json"
            }

            data = {
                "recipient": {"id": recipient_id},
                "message": {"text": message}
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "recipient_id": recipient_id
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                }

        except Exception as e:
            frappe.log_error(f"Instagram send error: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_instagram_bulk_messages(self, recipients: List[Dict], message: str) -> Dict[str, Any]:
        """Send bulk Instagram Direct Messages"""
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "results": []
        }

        for recipient in recipients:
            instagram_id = recipient.get("instagram_id") or recipient.get("ig_id")
            if not instagram_id:
                results["failed"] += 1
                results["results"].append({
                    "recipient": recipient.get("email_id", "Unknown"),
                    "success": False,
                    "error": "No Instagram ID"
                })
                continue

            result = self.send_instagram_message(instagram_id, message)

            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1

            results["results"].append({
                "recipient": recipient.get("email_id", instagram_id),
                "instagram_id": instagram_id,
                **result
            })

        return results

    def handle_facebook_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Facebook Messenger webhook events"""
        try:
            if not self.facebook_config["enabled"]:
                return {"success": False, "error": "Facebook integration disabled"}

            processed_messages = []
            
            # Process each entry in the webhook data
            for entry in data.get("entry", []):
                page_id = entry.get("id")
                
                # Process messaging events
                for messaging_event in entry.get("messaging", []):
                    result = self.process_facebook_message(messaging_event, page_id)
                    if result:
                        processed_messages.append(result)
            
            return {
                "success": True,
                "processed_messages": processed_messages,
                "count": len(processed_messages)
            }
            
        except Exception as e:
            frappe.log_error(f"Error handling Facebook webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_facebook_message(self, messaging_event: Dict[str, Any], page_id: str) -> Optional[Dict[str, Any]]:
        """Process individual Facebook Messenger message"""
        try:
            sender_id = messaging_event.get("sender", {}).get("id")
            recipient_id = messaging_event.get("recipient", {}).get("id")
            timestamp = messaging_event.get("timestamp")
            
            # Skip if this is a message sent by the page (our responses)
            if sender_id == page_id:
                return None
            
            # Get message content
            message_data = messaging_event.get("message", {})
            message_text = message_data.get("text", "")
            message_id = message_data.get("mid")
            
            # Handle attachments
            attachments = message_data.get("attachments", [])
            attachment_info = self.process_facebook_attachments(attachments)
            
            # Get sender information
            sender_info = self.get_facebook_user_info(sender_id)
            
            # Create conversation record
            conversation_id = self.create_facebook_conversation(
                sender_id=sender_id,
                sender_info=sender_info,
                message_text=message_text,
                message_id=message_id,
                timestamp=timestamp,
                attachments=attachment_info
            )
            
            # Route to appropriate agent
            routing_result = self.route_facebook_message(
                conversation_id=conversation_id,
                message_text=message_text,
                sender_info=sender_info
            )
            
            return {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "message_text": message_text,
                "routing_result": routing_result,
                "platform": "facebook"
            }
            
        except Exception as e:
            frappe.log_error(f"Error processing Facebook message: {str(e)}")
            return None
    
    def handle_instagram_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Instagram Direct Messages webhook events"""
        try:
            if not self.instagram_config["enabled"]:
                return {"success": False, "error": "Instagram integration disabled"}
            
            processed_messages = []
            
            # Process each entry in the webhook data
            for entry in data.get("entry", []):
                # Process messaging events
                for messaging_event in entry.get("messaging", []):
                    result = self.process_instagram_message(messaging_event)
                    if result:
                        processed_messages.append(result)
            
            return {
                "success": True,
                "processed_messages": processed_messages,
                "count": len(processed_messages)
            }
            
        except Exception as e:
            frappe.log_error(f"Error handling Instagram webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_instagram_message(self, messaging_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual Instagram Direct Message"""
        try:
            sender_id = messaging_event.get("sender", {}).get("id")
            recipient_id = messaging_event.get("recipient", {}).get("id")
            timestamp = messaging_event.get("timestamp")
            
            # Get message content
            message_data = messaging_event.get("message", {})
            message_text = message_data.get("text", "")
            message_id = message_data.get("mid")
            
            # Handle attachments
            attachments = message_data.get("attachments", [])
            attachment_info = self.process_instagram_attachments(attachments)
            
            # Get sender information
            sender_info = self.get_instagram_user_info(sender_id)
            
            # Create conversation record
            conversation_id = self.create_instagram_conversation(
                sender_id=sender_id,
                sender_info=sender_info,
                message_text=message_text,
                message_id=message_id,
                timestamp=timestamp,
                attachments=attachment_info
            )
            
            # Route to appropriate agent
            routing_result = self.route_instagram_message(
                conversation_id=conversation_id,
                message_text=message_text,
                sender_info=sender_info
            )
            
            return {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "message_text": message_text,
                "routing_result": routing_result,
                "platform": "instagram"
            }
            
        except Exception as e:
            frappe.log_error(f"Error processing Instagram message: {str(e)}")
            return None
    
    def get_facebook_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get Facebook user information"""
        try:
            url = f"https://graph.facebook.com/v{self.facebook_config['api_version']}/{user_id}"
            params = {
                "fields": "first_name,last_name,profile_pic",
                "access_token": self.facebook_config["page_access_token"]
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            return {
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "profile_pic": user_data.get("profile_pic", ""),
                "full_name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting Facebook user info: {str(e)}")
            return {
                "first_name": "",
                "last_name": "",
                "profile_pic": "",
                "full_name": "Unknown User"
            }
    
    def get_instagram_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get Instagram user information"""
        try:
            url = f"https://graph.facebook.com/v{self.instagram_config['api_version']}/{user_id}"
            params = {
                "fields": "name,username,profile_picture_url",
                "access_token": self.instagram_config["access_token"]
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            user_data = response.json()
            return {
                "name": user_data.get("name", ""),
                "username": user_data.get("username", ""),
                "profile_picture": user_data.get("profile_picture_url", ""),
                "full_name": user_data.get("name", user_data.get("username", "Unknown User"))
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting Instagram user info: {str(e)}")
            return {
                "name": "",
                "username": "",
                "profile_picture": "",
                "full_name": "Unknown User"
            }
    
    def process_facebook_attachments(self, attachments: List[Dict]) -> List[Dict[str, Any]]:
        """Process Facebook message attachments"""
        processed_attachments = []
        
        for attachment in attachments:
            attachment_type = attachment.get("type")
            payload = attachment.get("payload", {})
            
            processed_attachment = {
                "type": attachment_type,
                "url": payload.get("url", ""),
                "title": payload.get("title", ""),
                "coordinates": payload.get("coordinates", {}),
                "sticker_id": payload.get("sticker_id")
            }
            
            processed_attachments.append(processed_attachment)
        
        return processed_attachments
    
    def process_instagram_attachments(self, attachments: List[Dict]) -> List[Dict[str, Any]]:
        """Process Instagram message attachments"""
        processed_attachments = []
        
        for attachment in attachments:
            attachment_type = attachment.get("type")
            payload = attachment.get("payload", {})
            
            processed_attachment = {
                "type": attachment_type,
                "url": payload.get("url", ""),
                "title": payload.get("title", "")
            }
            
            processed_attachments.append(processed_attachment)
        
        return processed_attachments

    def send_facebook_message(self, recipient_id: str, message_text: str, conversation_id: str = None) -> Dict[str, Any]:
        """Send message via Facebook Messenger"""
        try:
            if not self.facebook_config["enabled"]:
                return {"success": False, "error": "Facebook integration disabled"}

            url = f"https://graph.facebook.com/v{self.facebook_config['api_version']}/me/messages"

            payload = {
                "recipient": {"id": recipient_id},
                "message": {"text": message_text},
                "messaging_type": "RESPONSE"
            }

            headers = {"Content-Type": "application/json"}
            params = {"access_token": self.facebook_config["page_access_token"]}

            response = requests.post(url, json=payload, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()

            # Log outbound message
            if conversation_id:
                self.log_outbound_message(
                    conversation_id=conversation_id,
                    message_text=message_text,
                    platform="facebook",
                    platform_message_id=result.get("message_id")
                )

            return {
                "success": True,
                "message_id": result.get("message_id"),
                "recipient_id": recipient_id
            }

        except Exception as e:
            frappe.log_error(f"Error sending Facebook message: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_instagram_message(self, recipient_id: str, message_text: str, conversation_id: str = None) -> Dict[str, Any]:
        """Send message via Instagram Direct Messages"""
        try:
            if not self.instagram_config["enabled"]:
                return {"success": False, "error": "Instagram integration disabled"}

            url = f"https://graph.facebook.com/v{self.instagram_config['api_version']}/me/messages"

            payload = {
                "recipient": {"id": recipient_id},
                "message": {"text": message_text}
            }

            headers = {"Content-Type": "application/json"}
            params = {"access_token": self.instagram_config["access_token"]}

            response = requests.post(url, json=payload, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            result = response.json()

            # Log outbound message
            if conversation_id:
                self.log_outbound_message(
                    conversation_id=conversation_id,
                    message_text=message_text,
                    platform="instagram",
                    platform_message_id=result.get("message_id")
                )

            return {
                "success": True,
                "message_id": result.get("message_id"),
                "recipient_id": recipient_id
            }

        except Exception as e:
            frappe.log_error(f"Error sending Instagram message: {str(e)}")
            return {"success": False, "error": str(e)}

    def create_facebook_conversation(self, sender_id: str, sender_info: Dict, message_text: str,
                                   message_id: str, timestamp: int, attachments: List[Dict]) -> str:
        """Create conversation record for Facebook message"""
        try:
            message_time = datetime.fromtimestamp(timestamp / 1000)

            conversation = frappe.get_doc({
                "doctype": "Omnichannel Conversation",
                "customer_name": sender_info.get("full_name", "Unknown"),
                "channel_type": "facebook",
                "conversation_status": "Open",
                "subject": f"Facebook message from {sender_info.get('full_name', 'Unknown')}",
                "platform_user_id": sender_id,
                "platform_message_id": message_id,
                "start_time": message_time,
                "last_message_time": message_time,
                "message_count": 1,
                "platform_data": json.dumps({
                    "sender_info": sender_info,
                    "platform": "facebook",
                    "page_id": self.facebook_config["page_id"]
                })
            })
            conversation.insert()

            # Create initial message record
            self.create_message_record(
                conversation_id=conversation.name,
                sender_id=sender_id,
                message_text=message_text,
                message_id=message_id,
                timestamp=message_time,
                attachments=attachments,
                platform="facebook"
            )

            frappe.db.commit()
            return conversation.name

        except Exception as e:
            frappe.log_error(f"Error creating Facebook conversation: {str(e)}")
            return None

    def create_instagram_conversation(self, sender_id: str, sender_info: Dict, message_text: str,
                                    message_id: str, timestamp: int, attachments: List[Dict]) -> str:
        """Create conversation record for Instagram message"""
        try:
            message_time = datetime.fromtimestamp(timestamp / 1000)

            conversation = frappe.get_doc({
                "doctype": "Omnichannel Conversation",
                "customer_name": sender_info.get("full_name", "Unknown"),
                "channel_type": "instagram",
                "conversation_status": "Open",
                "subject": f"Instagram DM from {sender_info.get('full_name', 'Unknown')}",
                "platform_user_id": sender_id,
                "platform_message_id": message_id,
                "start_time": message_time,
                "last_message_time": message_time,
                "message_count": 1,
                "platform_data": json.dumps({
                    "sender_info": sender_info,
                    "platform": "instagram",
                    "business_account_id": self.instagram_config["business_account_id"]
                })
            })
            conversation.insert()

            # Create initial message record
            self.create_message_record(
                conversation_id=conversation.name,
                sender_id=sender_id,
                message_text=message_text,
                message_id=message_id,
                timestamp=message_time,
                attachments=attachments,
                platform="instagram"
            )

            frappe.db.commit()
            return conversation.name

        except Exception as e:
            frappe.log_error(f"Error creating Instagram conversation: {str(e)}")
            return None
