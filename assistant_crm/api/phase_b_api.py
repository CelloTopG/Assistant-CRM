import frappe
from frappe import _
import json
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def telegram_webhook():
    """
    Telegram Bot webhook endpoint
    Handles incoming messages from Telegram
    """
    try:
        if frappe.request.method == "POST":
            from assistant_crm.services.advanced_social_media_service import AdvancedSocialMediaService
            
            # Get request data
            data = json.loads(frappe.request.data)
            
            # Process webhook
            social_service = AdvancedSocialMediaService()
            result = social_service.handle_telegram_webhook(data)
            
            return {
                "success": result.get("success", False),
                "conversation_id": result.get("conversation_id"),
                "platform": "telegram"
            }
        else:
            frappe.throw(_("Method not allowed"), frappe.MethodNotAllowedError)
            
    except Exception as e:
        frappe.log_error(f"Error in Telegram webhook: {str(e)}")
        return {"error": str(e)}, 500


@frappe.whitelist(allow_guest=True)
def linkedin_webhook():
    """
    LinkedIn webhook endpoint
    Handles incoming messages and events from LinkedIn
    """
    try:
        if frappe.request.method == "POST":
            from assistant_crm.services.advanced_social_media_service import AdvancedSocialMediaService
            
            # Get request data
            data = json.loads(frappe.request.data)
            
            # Process webhook
            social_service = AdvancedSocialMediaService()
            result = social_service.handle_linkedin_webhook(data)
            
            return {
                "success": result.get("success", False),
                "processed_messages": result.get("processed_messages", []),
                "platform": "linkedin"
            }
        else:
            frappe.throw(_("Method not allowed"), frappe.MethodNotAllowedError)
            
    except Exception as e:
        frappe.log_error(f"Error in LinkedIn webhook: {str(e)}")
        return {"error": str(e)}, 500


@frappe.whitelist(allow_guest=True)
def twitter_webhook():
    """
    Twitter/X webhook endpoint
    Handles incoming DMs and mentions from Twitter
    """
    try:
        if frappe.request.method == "POST":
            from assistant_crm.services.advanced_social_media_service import AdvancedSocialMediaService
            
            # Get request data
            data = json.loads(frappe.request.data)
            
            # Process webhook
            social_service = AdvancedSocialMediaService()
            result = social_service.handle_twitter_webhook(data)
            
            return {
                "success": result.get("success", False),
                "processed_messages": result.get("processed_messages", []),
                "platform": "twitter"
            }
        else:
            frappe.throw(_("Method not allowed"), frappe.MethodNotAllowedError)
            
    except Exception as e:
        frappe.log_error(f"Error in Twitter webhook: {str(e)}")
        return {"error": str(e)}, 500


@frappe.whitelist(allow_guest=False)
def enhance_message_quality(message_text, target_tone="professional", platform="general", customer_context=None):
    """
    Enhance message quality with AI-powered tone adjustment and optimization
    
    Args:
        message_text: Original message text
        target_tone: Desired tone (professional, friendly, urgent, empathetic, informative)
        platform: Target platform for optimization
        customer_context: Optional customer context for personalization
        
    Returns:
        Dict containing enhanced message and analysis
    """
    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        
        ai_service = EnhancedAIService()
        
        # Parse customer context if provided as string
        if isinstance(customer_context, str):
            try:
                customer_context = json.loads(customer_context)
            except:
                customer_context = None
        
        result = ai_service.enhance_message_quality(
            message_text=message_text,
            target_tone=target_tone,
            platform=platform,
            customer_context=customer_context
        )
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in enhance_message_quality API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "original_message": message_text,
            "enhanced_message": message_text
        }


@frappe.whitelist(allow_guest=False)
def get_advanced_analytics_dashboard(date_range=None, agent_filter=None):
    """
    Get comprehensive analytics dashboard with predictive insights
    
    Args:
        date_range: Optional date range filter (JSON string)
        agent_filter: Optional agent filter
        
    Returns:
        Dict containing comprehensive dashboard data
    """
    try:
        from assistant_crm.services.advanced_analytics_service import AdvancedAnalyticsService
        
        # Parse date range if provided
        if isinstance(date_range, str):
            try:
                date_range = json.loads(date_range)
            except:
                date_range = None
        
        analytics_service = AdvancedAnalyticsService()
        result = analytics_service.generate_comprehensive_dashboard(
            date_range=date_range,
            agent_filter=agent_filter
        )
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in get_advanced_analytics_dashboard API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def send_advanced_social_message(platform, recipient_id, message_text, conversation_id=None):
    """
    Send message via advanced social media platforms (Telegram, LinkedIn, Twitter)
    
    Args:
        platform: Platform name (telegram, linkedin, twitter)
        recipient_id: Recipient identifier on the platform
        message_text: Message content
        conversation_id: Optional conversation ID for logging
        
    Returns:
        Dict containing send result
    """
    try:
        from assistant_crm.services.advanced_social_media_service import AdvancedSocialMediaService
        
        social_service = AdvancedSocialMediaService()
        
        if platform == "telegram":
            result = social_service.send_telegram_message(recipient_id, message_text, conversation_id)
        elif platform == "linkedin":
            result = social_service.send_linkedin_message(recipient_id, message_text, conversation_id)
        elif platform == "twitter":
            result = social_service.send_twitter_dm(recipient_id, message_text, conversation_id)
        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}"
            }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in send_advanced_social_message API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_platform_analytics(platform=None, date_range=None):
    """
    Get analytics for specific social media platforms
    
    Args:
        platform: Optional platform filter
        date_range: Optional date range filter
        
    Returns:
        Dict containing platform analytics
    """
    try:
        # Parse date range if provided
        if isinstance(date_range, str):
            try:
                date_range = json.loads(date_range)
            except:
                date_range = None
        
        # Build query conditions
        conditions = []
        values = []
        
        if platform:
            conditions.append("channel_type = %s")
            values.append(platform)
        else:
            # Include all Phase B platforms
            conditions.append("channel_type IN ('telegram', 'linkedin', 'twitter', 'facebook', 'instagram', 'whatsapp', 'email', 'sms')")
        
        if date_range:
            if date_range.get("start_date"):
                conditions.append("DATE(start_time) >= %s")
                values.append(date_range["start_date"])
            if date_range.get("end_date"):
                conditions.append("DATE(start_time) <= %s")
                values.append(date_range["end_date"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get platform statistics
        platform_stats = frappe.db.sql(f"""
            SELECT 
                channel_type as platform,
                COUNT(*) as total_conversations,
                COUNT(CASE WHEN conversation_status = 'Closed' THEN 1 END) as resolved_conversations,
                AVG(message_count) as avg_messages_per_conversation,
                AVG(CASE WHEN end_time IS NOT NULL THEN 
                    TIMESTAMPDIFF(MINUTE, start_time, end_time) END) as avg_resolution_time_minutes,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM `tabOmnichannel Conversation`
            WHERE {where_clause}
            GROUP BY channel_type
            ORDER BY total_conversations DESC
        """, values, as_dict=True)
        
        # Get message volume trends
        message_trends = frappe.db.sql(f"""
            SELECT 
                DATE(oc.start_time) as date,
                oc.channel_type as platform,
                COUNT(om.name) as message_count,
                COUNT(CASE WHEN om.is_inbound = 1 THEN 1 END) as inbound_messages,
                COUNT(CASE WHEN om.is_inbound = 0 THEN 1 END) as outbound_messages
            FROM `tabOmnichannel Conversation` oc
            LEFT JOIN `tabOmnichannel Message` om ON oc.name = om.conversation_id
            WHERE {where_clause}
            GROUP BY DATE(oc.start_time), oc.channel_type
            ORDER BY date DESC, platform
        """, values, as_dict=True)
        
        return {
            "success": True,
            "platform_stats": platform_stats,
            "message_trends": message_trends,
            "platform": platform,
            "date_range": date_range,
            "total_platforms": len(platform_stats)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_platform_analytics API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "platform_stats": [],
            "message_trends": []
        }


@frappe.whitelist(allow_guest=False)
def get_ai_enhancement_analytics(date_range=None):
    """
    Get analytics for AI message enhancement usage
    
    Args:
        date_range: Optional date range filter
        
    Returns:
        Dict containing AI enhancement analytics
    """
    try:
        # This would track AI enhancement usage if we had a logging system
        # For now, return mock data structure
        
        analytics = {
            "total_enhancements": 0,
            "average_improvement_score": 0.0,
            "most_used_tones": [],
            "platform_optimization_stats": {},
            "success_rate": 0.0,
            "time_saved_minutes": 0
        }
        
        # In a real implementation, this would query enhancement logs
        # For Phase B demo, we'll return the structure
        
        return {
            "success": True,
            "analytics": analytics,
            "date_range": date_range,
            "message": "AI enhancement analytics (demo structure)"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_ai_enhancement_analytics API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
