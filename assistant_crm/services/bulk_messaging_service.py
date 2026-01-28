# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
from datetime import datetime
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor


class BulkMessagingService:
    """Service for executing bulk messaging campaigns"""
    
    def __init__(self):
        self.batch_size = 100
        self.rate_limits = {
            'WhatsApp': 1000,  # messages per hour
            'SMS': 10000,      # messages per hour
            'Email': 5000,     # messages per hour
            'Facebook': 500,   # messages per hour
            'Instagram': 500,  # messages per hour
            'Telegram': 1000   # messages per hour
        }
        self.delay_between_batches = 2  # seconds
    
    def execute_campaign(self, campaign_name):
        """Execute bulk messaging campaign"""
        try:
            campaign = frappe.get_doc('Bulk Message Campaign', campaign_name)
            
            if campaign.status != 'Draft':
                return {
                    'success': False,
                    'error': 'Campaign must be in Draft status to execute'
                }
            
            # Update status
            campaign.status = 'Running'
            campaign.save()
            frappe.db.commit()
            
            # Get recipients
            recipients = campaign.get_target_recipients()
            if not recipients:
                campaign.status = 'Failed'
                campaign.save()
                return {
                    'success': False,
                    'error': 'No recipients found for this campaign'
                }
            
            # Get message content
            message_content = campaign.get_message_content()
            if not message_content:
                campaign.status = 'Failed'
                campaign.save()
                return {
                    'success': False,
                    'error': 'No message content found'
                }
            
            # Execute campaign
            result = self.send_bulk_messages(campaign, recipients, message_content)
            
            # Update final status
            if result['success']:
                campaign.status = 'Completed'
            else:
                campaign.status = 'Failed'
            
            campaign.save()
            frappe.db.commit()
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Campaign execution error: {str(e)}", "Bulk Messaging Service")
            
            # Update campaign status to failed
            try:
                campaign = frappe.get_doc('Bulk Message Campaign', campaign_name)
                campaign.status = 'Failed'
                campaign.save()
                frappe.db.commit()
            except:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_bulk_messages(self, campaign, recipients, message_content):
        """Send messages to all recipients"""
        total_sent = 0
        total_delivered = 0
        total_failed = 0
        
        try:
            # Get enabled channels
            enabled_channels = [ch.channel_type for ch in campaign.channels if ch.is_enabled]
            
            # Process in batches
            for i in range(0, len(recipients), self.batch_size):
                batch = recipients[i:i + self.batch_size]
                
                for recipient in batch:
                    try:
                        # Personalize message
                        personalized_message = campaign.personalize_message(message_content, recipient)
                        
                        # Send via each enabled channel
                        for channel in enabled_channels:
                            success = self.send_single_message(
                                recipient, personalized_message, channel, campaign
                            )
                            
                            if success:
                                total_delivered += 1
                            else:
                                total_failed += 1
                            
                            total_sent += 1
                            
                            # Small delay between messages to avoid overwhelming APIs
                            time.sleep(0.1)
                    
                    except Exception as e:
                        total_failed += len(enabled_channels)
                        frappe.log_error(f"Failed to send message to {recipient.get('email_id')}: {str(e)}", 
                                       "Bulk Messaging Service")
                
                # Update progress
                campaign.messages_sent = total_sent
                campaign.messages_delivered = total_delivered
                campaign.messages_failed = total_failed
                campaign.delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
                campaign.save()
                frappe.db.commit()
                
                # Delay between batches
                if i + self.batch_size < len(recipients):
                    time.sleep(self.delay_between_batches)
            
            return {
                'success': True,
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_failed': total_failed,
                'delivery_rate': (total_delivered / total_sent * 100) if total_sent > 0 else 0
            }
            
        except Exception as e:
            frappe.log_error(f"Bulk messaging error: {str(e)}", "Bulk Messaging Service")
            return {
                'success': False,
                'error': str(e),
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_failed': total_failed
            }
    
    def send_single_message(self, recipient, message, channel, campaign):
        """Send single message via specified channel"""
        try:
            if channel == 'WhatsApp':
                return self.send_whatsapp_message(recipient, message)
            elif channel == 'SMS':
                return self.send_sms_message(recipient, message)
            elif channel == 'Email':
                return self.send_email_message(recipient, message, campaign)
            elif channel == 'Facebook':
                return self.send_facebook_message(recipient, message)
            elif channel == 'Instagram':
                return self.send_instagram_message(recipient, message)
            elif channel == 'Telegram':
                return self.send_telegram_message(recipient, message)
            else:
                frappe.log_error(f"Unsupported channel: {channel}", "Bulk Messaging Service")
                return False
                
        except Exception as e:
            frappe.log_error(f"Failed to send {channel} message: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_whatsapp_message(self, recipient, message):
        """Send WhatsApp message"""
        try:
            if not recipient.get('mobile_no'):
                return False

            # Use real WhatsApp service
            from assistant_crm.assistant_crm.services.whatsapp_service import WhatsAppService
            whatsapp_service = WhatsAppService()
            result = whatsapp_service.send_message(recipient['mobile_no'], message)

            if result.get("success"):
                frappe.log_error(f"WhatsApp message sent successfully to {recipient['mobile_no']}: {result.get('message_id')}",
                               "Bulk Messaging Service")
                return True
            else:
                frappe.log_error(f"WhatsApp send failed to {recipient['mobile_no']}: {result.get('error')}",
                               "Bulk Messaging Service")
                return False

        except Exception as e:
            frappe.log_error(f"WhatsApp send error: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_sms_message(self, recipient, message):
        """Send SMS message"""
        try:
            if not recipient.get('mobile_no'):
                return False

            # Use real SMS service
            from assistant_crm.assistant_crm.services.sms_service import SMSService
            sms_service = SMSService()
            result = sms_service.send_message(recipient['mobile_no'], message)

            if result.get("success"):
                frappe.log_error(f"SMS sent successfully to {recipient['mobile_no']}: {result.get('message_sid')}",
                               "Bulk Messaging Service")
                return True
            else:
                frappe.log_error(f"SMS send failed to {recipient['mobile_no']}: {result.get('error')}",
                               "Bulk Messaging Service")
                return False

        except Exception as e:
            frappe.log_error(f"SMS send error: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_email_message(self, recipient, message, campaign):
        """Send email message"""
        try:
            if not recipient.get('email_id'):
                return False
            
            subject = f"Message from WCFCB"
            if campaign.message_template:
                template_doc = frappe.get_doc("Message Template", campaign.message_template)
                if template_doc.subject:
                    subject = template_doc.subject
            
            frappe.sendmail(
                recipients=[recipient['email_id']],
                subject=subject,
                message=message,
                delayed=False
            )
            return True
            
        except Exception as e:
            frappe.log_error(f"Email send error: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_facebook_message(self, recipient, message):
        """Send Facebook message"""
        try:
            facebook_id = recipient.get('facebook_id') or recipient.get('messenger_id')
            if not facebook_id:
                frappe.log_error(f"No Facebook ID for recipient: {recipient.get('email_id')}",
                               "Bulk Messaging Service")
                return False

            # Use real Facebook service
            from assistant_crm.assistant_crm.services.social_media_integration_service import SocialMediaIntegrationService
            facebook_service = SocialMediaIntegrationService()
            result = facebook_service.send_facebook_message(facebook_id, message)

            if result.get("success"):
                frappe.log_error(f"Facebook message sent successfully to {facebook_id}: {result.get('message_id')}",
                               "Bulk Messaging Service")
                return True
            else:
                frappe.log_error(f"Facebook send failed to {facebook_id}: {result.get('error')}",
                               "Bulk Messaging Service")
                return False

        except Exception as e:
            frappe.log_error(f"Facebook send error: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_instagram_message(self, recipient, message):
        """Send Instagram message"""
        try:
            instagram_id = recipient.get('instagram_id') or recipient.get('ig_id')
            if not instagram_id:
                frappe.log_error(f"No Instagram ID for recipient: {recipient.get('email_id')}",
                               "Bulk Messaging Service")
                return False

            # Use real Instagram service
            from assistant_crm.assistant_crm.services.social_media_integration_service import SocialMediaIntegrationService
            instagram_service = SocialMediaIntegrationService()
            result = instagram_service.send_instagram_message(instagram_id, message)

            if result.get("success"):
                frappe.log_error(f"Instagram message sent successfully to {instagram_id}: {result.get('message_id')}",
                               "Bulk Messaging Service")
                return True
            else:
                frappe.log_error(f"Instagram send failed to {instagram_id}: {result.get('error')}",
                               "Bulk Messaging Service")
                return False

        except Exception as e:
            frappe.log_error(f"Instagram send error: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_telegram_message(self, recipient, message):
        """Send Telegram message"""
        try:
            chat_id = recipient.get('telegram_chat_id') or recipient.get('chat_id')
            if not chat_id:
                frappe.log_error(f"No Telegram chat ID for recipient: {recipient.get('email_id')}",
                               "Bulk Messaging Service")
                return False

            # Use real Telegram service
            from assistant_crm.assistant_crm.services.telegram_service import TelegramService
            telegram_service = TelegramService()
            result = telegram_service.send_message(chat_id, message)

            if result.get("success"):
                frappe.log_error(f"Telegram message sent successfully to {chat_id}: {result.get('message_id')}",
                               "Bulk Messaging Service")
                return True
            else:
                frappe.log_error(f"Telegram send failed to {chat_id}: {result.get('error')}",
                               "Bulk Messaging Service")
                return False

        except Exception as e:
            frappe.log_error(f"Telegram send error: {str(e)}", "Bulk Messaging Service")
            return False
    
    def send_test_message(self, campaign_name, test_email):
        """Send test message to specified email"""
        try:
            campaign = frappe.get_doc('Bulk Message Campaign', campaign_name)
            message_content = campaign.get_message_content()
            
            # Create test recipient
            test_recipient = {
                'email_id': test_email,
                'first_name': 'Test',
                'last_name': 'User',
                'mobile_no': '',
                'company': 'Test Company'
            }
            
            # Personalize message
            personalized_message = campaign.personalize_message(message_content, test_recipient)
            
            # Send test email
            success = self.send_email_message(test_recipient, personalized_message, campaign)
            
            return {
                'success': success,
                'message': 'Test message sent successfully' if success else 'Failed to send test message'
            }
            
        except Exception as e:
            frappe.log_error(f"Test message error: {str(e)}", "Bulk Messaging Service")
            return {
                'success': False,
                'error': str(e)
            }
