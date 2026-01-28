# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import json


class CampaignAnalytics(Document):
    """Campaign analytics for tracking bulk messaging performance"""
    
    def validate(self):
        """Validate campaign analytics"""
        self.calculate_rates()
        self.calculate_engagement_score()
    
    def calculate_rates(self):
        """Calculate delivery, read, and click rates"""
        if self.messages_sent and self.messages_sent > 0:
            self.delivery_rate = (self.messages_delivered / self.messages_sent) * 100
            
            if self.messages_delivered > 0:
                self.read_rate = (self.messages_read / self.messages_delivered) * 100
                self.click_rate = (self.messages_clicked / self.messages_delivered) * 100
    
    def calculate_engagement_score(self):
        """Calculate overall engagement score"""
        try:
            # Weighted engagement score
            delivery_weight = 0.3
            read_weight = 0.4
            click_weight = 0.2
            response_weight = 0.1
            
            delivery_score = (self.delivery_rate or 0) / 100
            read_score = (self.read_rate or 0) / 100
            click_score = (self.click_rate or 0) / 100
            
            # Response score based on positive vs negative responses
            response_score = 0
            if self.responses_received and self.responses_received > 0:
                positive_ratio = (self.positive_responses or 0) / self.responses_received
                response_score = positive_ratio
            
            self.engagement_score = (
                (delivery_score * delivery_weight) +
                (read_score * read_weight) +
                (click_score * click_weight) +
                (response_score * response_weight)
            ) * 100
            
        except Exception as e:
            frappe.log_error(f"Error calculating engagement score: {str(e)}", "Campaign Analytics")
            self.engagement_score = 0
    
    def generate_analytics_report(self):
        """Generate comprehensive analytics report"""
        try:
            report = {
                "campaign_overview": {
                    "campaign_name": frappe.db.get_value("Bulk Message Campaign", self.campaign, "campaign_name"),
                    "total_recipients": self.total_recipients,
                    "messages_sent": self.messages_sent,
                    "delivery_rate": self.delivery_rate,
                    "engagement_score": self.engagement_score
                },
                "performance_metrics": {
                    "delivery": {
                        "delivered": self.messages_delivered,
                        "failed": self.messages_failed,
                        "rate": self.delivery_rate
                    },
                    "engagement": {
                        "read": self.messages_read,
                        "clicked": self.messages_clicked,
                        "read_rate": self.read_rate,
                        "click_rate": self.click_rate
                    },
                    "responses": {
                        "total": self.responses_received,
                        "positive": self.positive_responses,
                        "negative": self.negative_responses,
                        "escalations": self.escalations_triggered
                    }
                },
                "channel_performance": [
                    {
                        "channel": metric.channel_type,
                        "sent": metric.messages_sent,
                        "delivered": metric.messages_delivered,
                        "delivery_rate": metric.delivery_rate,
                        "engagement_rate": metric.engagement_rate
                    }
                    for metric in self.channel_metrics
                ],
                "cost_analysis": {
                    "total_cost": self.total_cost,
                    "cost_per_message": self.cost_per_message,
                    "cost_per_engagement": self.cost_per_engagement,
                    "roi_estimate": self.roi_estimate
                },
                "recommendations": self.generate_recommendations()
            }
            
            return report
            
        except Exception as e:
            frappe.log_error(f"Error generating analytics report: {str(e)}", "Campaign Analytics")
            return {}
    
    def generate_recommendations(self):
        """Generate recommendations based on analytics"""
        recommendations = []
        
        try:
            # Delivery rate recommendations
            if self.delivery_rate < 90:
                recommendations.append({
                    "type": "delivery",
                    "priority": "high",
                    "message": "Delivery rate is below 90%. Consider reviewing contact data quality and channel configurations."
                })
            
            # Engagement recommendations
            if self.read_rate < 50:
                recommendations.append({
                    "type": "engagement",
                    "priority": "medium",
                    "message": "Read rate is below 50%. Consider improving subject lines and send timing."
                })
            
            if self.click_rate < 10:
                recommendations.append({
                    "type": "content",
                    "priority": "medium",
                    "message": "Click rate is below 10%. Consider improving call-to-action and content relevance."
                })
            
            # Channel performance recommendations
            best_channel = None
            best_rate = 0
            for metric in self.channel_metrics:
                if metric.delivery_rate > best_rate:
                    best_rate = metric.delivery_rate
                    best_channel = metric.channel_type
            
            if best_channel:
                recommendations.append({
                    "type": "channel",
                    "priority": "low",
                    "message": f"{best_channel} shows the best performance. Consider prioritizing this channel for future campaigns."
                })
            
            # Timing recommendations
            if self.peak_engagement_hour:
                recommendations.append({
                    "type": "timing",
                    "priority": "low",
                    "message": f"Peak engagement occurs at {self.peak_engagement_hour}. Consider scheduling future campaigns around this time."
                })
            
            return recommendations
            
        except Exception as e:
            frappe.log_error(f"Error generating recommendations: {str(e)}", "Campaign Analytics")
            return []


@frappe.whitelist()
def generate_campaign_analytics(campaign_name):
    """Generate analytics for a specific campaign"""
    try:
        campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
        
        # Check if analytics already exist for today
        existing = frappe.db.get_value(
            "Campaign Analytics",
            {"campaign": campaign_name, "analytics_date": frappe.utils.today()},
            "name"
        )
        
        if existing:
            analytics = frappe.get_doc("Campaign Analytics", existing)
        else:
            # Create new analytics record
            analytics = frappe.get_doc({
                "doctype": "Campaign Analytics",
                "campaign": campaign_name,
                "analytics_date": frappe.utils.today()
            })
        
        # Update analytics data
        analytics.total_recipients = campaign.total_recipients or 0
        analytics.messages_sent = campaign.messages_sent or 0
        analytics.messages_delivered = campaign.messages_delivered or 0
        analytics.messages_failed = campaign.messages_failed or 0
        
        # Calculate additional metrics (this would integrate with actual messaging services)
        analytics.messages_read = calculate_read_messages(campaign_name)
        analytics.messages_clicked = calculate_clicked_messages(campaign_name)
        analytics.responses_received = calculate_responses(campaign_name)
        
        # Save analytics
        if existing:
            analytics.save()
        else:
            analytics.insert()
        
        return {
            "success": True,
            "analytics_id": analytics.name,
            "report": analytics.generate_analytics_report()
        }
        
    except Exception as e:
        frappe.log_error(f"Error generating campaign analytics: {str(e)}", "Campaign Analytics")
        return {
            "success": False,
            "error": str(e)
        }


def calculate_read_messages(campaign_name):
    """Calculate number of read messages (placeholder for integration)"""
    # This would integrate with actual messaging service APIs
    # For now, return estimated based on industry averages
    campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
    delivered = campaign.messages_delivered or 0
    return int(delivered * 0.6)  # Assume 60% read rate


def calculate_clicked_messages(campaign_name):
    """Calculate number of clicked messages (placeholder for integration)"""
    # This would integrate with actual messaging service APIs
    campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
    delivered = campaign.messages_delivered or 0
    return int(delivered * 0.15)  # Assume 15% click rate


def calculate_responses(campaign_name):
    """Calculate number of responses received (placeholder for integration)"""
    # This would integrate with chat history or response tracking
    return 0


@frappe.whitelist()
def get_campaign_performance_summary(date_range="30"):
    """Get campaign performance summary for specified date range"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=int(date_range))
        
        analytics = frappe.db.sql("""
            SELECT 
                AVG(delivery_rate) as avg_delivery_rate,
                AVG(read_rate) as avg_read_rate,
                AVG(click_rate) as avg_click_rate,
                AVG(engagement_score) as avg_engagement_score,
                SUM(total_recipients) as total_recipients,
                SUM(messages_sent) as total_sent,
                SUM(messages_delivered) as total_delivered,
                COUNT(*) as total_campaigns
            FROM `tabCampaign Analytics`
            WHERE analytics_date BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)
        
        if analytics:
            summary = analytics[0]
            summary['date_range'] = f"{start_date} to {end_date}"
            return {
                "success": True,
                "summary": summary
            }
        else:
            return {
                "success": True,
                "summary": {},
                "message": "No analytics data found for the specified date range"
            }
            
    except Exception as e:
        frappe.log_error(f"Error getting campaign performance summary: {str(e)}", "Campaign Analytics")
        return {
            "success": False,
            "error": str(e)
        }
