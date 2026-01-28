import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from assistant_crm.services.predictive_analytics_service import PredictiveAnalyticsService


@frappe.whitelist(allow_guest=False)
def get_churn_predictions(customer_id=None, limit=50):
    """Get customer churn predictions"""
    try:
        analytics_service = PredictiveAnalyticsService()
        
        # Convert limit to integer
        limit = int(limit) if limit else 50
        
        result = analytics_service.predict_customer_churn(customer_id, limit)
        
        return {
            'success': result.get('success', False),
            'predictions': result.get('predictions', []),
            'summary': result.get('summary', {}),
            'total_analyzed': result.get('total_customers_analyzed', 0),
            'message': f"Analyzed {result.get('total_customers_analyzed', 0)} customers for churn risk"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in churn predictions API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'predictions': [],
            'message': 'Failed to generate churn predictions'
        }


@frappe.whitelist(allow_guest=False)
def get_volume_forecast(forecast_days=30):
    """Get conversation volume forecast"""
    try:
        analytics_service = PredictiveAnalyticsService()
        
        # Convert forecast_days to integer
        forecast_days = int(forecast_days) if forecast_days else 30
        
        result = analytics_service.forecast_conversation_volume(forecast_days)
        
        return {
            'success': result.get('success', False),
            'forecast': result.get('forecast', []),
            'capacity_recommendations': result.get('capacity_recommendations', {}),
            'forecast_period': forecast_days,
            'historical_data_points': result.get('historical_data_points', 0),
            'message': f"Generated {forecast_days}-day conversation volume forecast"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in volume forecast API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'forecast': [],
            'message': 'Failed to generate volume forecast'
        }


@frappe.whitelist(allow_guest=False)
def get_operational_insights(period_days=30):
    """Get comprehensive operational insights"""
    try:
        analytics_service = PredictiveAnalyticsService()
        
        # Convert period_days to integer
        period_days = int(period_days) if period_days else 30
        
        result = analytics_service.generate_operational_insights(period_days)
        
        return {
            'success': result.get('success', False),
            'insights': result,
            'analysis_period': period_days,
            'message': f"Generated operational insights for {period_days}-day period"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in operational insights API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'insights': {},
            'message': 'Failed to generate operational insights'
        }


@frappe.whitelist(allow_guest=False)
def get_analytics_dashboard_data(period='month'):
    """Get comprehensive analytics dashboard data"""
    try:
        # Determine period in days
        period_mapping = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365
        }
        period_days = period_mapping.get(period, 30)
        
        analytics_service = PredictiveAnalyticsService()
        
        # Get churn predictions (top 20 high-risk customers)
        churn_result = analytics_service.predict_customer_churn(limit=20)
        high_risk_customers = [
            p for p in churn_result.get('predictions', []) 
            if p['risk_level'] == 'High'
        ][:10]  # Top 10 high-risk
        
        # Get volume forecast (next 14 days)
        forecast_result = analytics_service.forecast_conversation_volume(14)
        
        # Get operational insights
        insights_result = analytics_service.generate_operational_insights(period_days)
        
        # Get key metrics summary
        key_metrics = get_key_metrics_summary(period_days)
        
        # Get trend analysis
        trend_analysis = get_trend_analysis(period_days)
        
        return {
            'success': True,
            'period': period,
            'period_days': period_days,
            'key_metrics': key_metrics,
            'churn_predictions': {
                'high_risk_customers': high_risk_customers,
                'summary': churn_result.get('summary', {})
            },
            'volume_forecast': {
                'forecast_data': forecast_result.get('forecast', [])[:7],  # Next 7 days
                'capacity_recommendations': forecast_result.get('capacity_recommendations', {})
            },
            'operational_insights': insights_result,
            'trend_analysis': trend_analysis,
            'dashboard_generated': frappe.utils.now()
        }
        
    except Exception as e:
        frappe.log_error(f"Error in analytics dashboard API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load analytics dashboard data'
        }


@frappe.whitelist(allow_guest=False)
def get_customer_risk_analysis(customer_id):
    """Get detailed risk analysis for specific customer"""
    try:
        analytics_service = PredictiveAnalyticsService()
        
        # Get churn prediction for specific customer
        result = analytics_service.predict_customer_churn(customer_id)
        
        if result.get('success') and result.get('predictions'):
            customer_prediction = result['predictions'][0]
            
            # Get additional customer insights
            customer_insights = get_customer_detailed_insights(customer_id)
            
            return {
                'success': True,
                'customer_id': customer_id,
                'churn_analysis': customer_prediction,
                'detailed_insights': customer_insights,
                'message': f"Risk analysis completed for customer {customer_id}"
            }
        else:
            return {
                'success': False,
                'error': 'Customer not found or insufficient data',
                'message': f"Unable to analyze customer {customer_id}"
            }
        
    except Exception as e:
        frappe.log_error(f"Error in customer risk analysis API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to analyze customer {customer_id}'
        }


@frappe.whitelist(allow_guest=False)
def get_capacity_planning_data(forecast_days=30):
    """Get capacity planning recommendations"""
    try:
        analytics_service = PredictiveAnalyticsService()
        
        # Get volume forecast
        forecast_result = analytics_service.forecast_conversation_volume(int(forecast_days))
        
        if not forecast_result.get('success'):
            return {
                'success': False,
                'error': 'Failed to generate forecast',
                'message': 'Unable to generate capacity planning data'
            }
        
        forecast_data = forecast_result.get('forecast', [])
        
        # Calculate capacity metrics
        capacity_metrics = calculate_capacity_metrics(forecast_data)
        
        # Generate staffing recommendations
        staffing_recommendations = generate_staffing_recommendations(forecast_data)
        
        # Get current capacity status
        current_capacity = get_current_capacity_status()
        
        return {
            'success': True,
            'forecast_period': forecast_days,
            'forecast_data': forecast_data,
            'capacity_metrics': capacity_metrics,
            'staffing_recommendations': staffing_recommendations,
            'current_capacity': current_capacity,
            'message': f"Capacity planning data generated for {forecast_days} days"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in capacity planning API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to generate capacity planning data'
        }


def get_key_metrics_summary(period_days):
    """Get key metrics summary for dashboard"""
    try:
        end_date = frappe.utils.today()
        start_date = frappe.utils.add_days(end_date, -period_days)
        
        # Total conversations
        total_conversations = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabMessage`
            WHERE DATE(creation) BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)
        
        # Average response time
        avg_response_time = frappe.db.sql("""
            SELECT AVG(TIMESTAMPDIFF(MINUTE, creation, modified)) as avg_minutes
            FROM `tabMessage`
            WHERE DATE(creation) BETWEEN %s AND %s
            AND ai_response IS NOT NULL
        """, (start_date, end_date), as_dict=True)
        
        # Customer satisfaction (simulated)
        satisfaction_score = frappe.db.sql("""
            SELECT AVG(CASE 
                WHEN sentiment = 'positive' THEN 5
                WHEN sentiment = 'neutral' THEN 3
                WHEN sentiment = 'negative' THEN 1
                ELSE 3
            END) as avg_score
            FROM `tabMessage`
            WHERE DATE(creation) BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)
        
        # Resolution rate
        resolution_rate = frappe.db.sql("""
            SELECT 
                COUNT(CASE WHEN status = 'Resolved' THEN 1 END) as resolved,
                COUNT(*) as total
            FROM `tabConversation`
            WHERE DATE(creation) BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)
        
        # Calculate percentages and format
        total_count = total_conversations[0]['count'] if total_conversations else 0
        avg_response = avg_response_time[0]['avg_minutes'] if avg_response_time and avg_response_time[0]['avg_minutes'] else 0
        satisfaction = satisfaction_score[0]['avg_score'] if satisfaction_score and satisfaction_score[0]['avg_score'] else 3
        
        resolution_data = resolution_rate[0] if resolution_rate else {'resolved': 0, 'total': 1}
        resolution_percentage = (resolution_data['resolved'] / resolution_data['total'] * 100) if resolution_data['total'] > 0 else 0
        
        return {
            'total_conversations': total_count,
            'avg_response_time_minutes': round(avg_response, 1),
            'customer_satisfaction_score': round(satisfaction, 2),
            'resolution_rate_percentage': round(resolution_percentage, 1),
            'period_start': start_date,
            'period_end': end_date
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting key metrics summary: {str(e)}")
        return {
            'total_conversations': 0,
            'avg_response_time_minutes': 0,
            'customer_satisfaction_score': 3.0,
            'resolution_rate_percentage': 0
        }


def get_trend_analysis(period_days):
    """Get trend analysis for dashboard"""
    try:
        end_date = frappe.utils.today()
        start_date = frappe.utils.add_days(end_date, -period_days)
        
        # Daily conversation trends
        daily_trends = frappe.db.sql("""
            SELECT 
                DATE(creation) as date,
                COUNT(*) as conversation_count,
                AVG(CASE 
                    WHEN sentiment = 'positive' THEN 1
                    WHEN sentiment = 'negative' THEN -1
                    ELSE 0
                END) as sentiment_score
            FROM `tabMessage`
            WHERE DATE(creation) BETWEEN %s AND %s
            GROUP BY DATE(creation)
            ORDER BY date
        """, (start_date, end_date), as_dict=True)
        
        # Calculate growth rates
        if len(daily_trends) >= 2:
            recent_avg = sum(d['conversation_count'] for d in daily_trends[-7:]) / min(7, len(daily_trends))
            previous_avg = sum(d['conversation_count'] for d in daily_trends[:-7]) / max(1, len(daily_trends) - 7)
            growth_rate = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
        else:
            growth_rate = 0
        
        return {
            'daily_trends': daily_trends,
            'conversation_growth_rate': round(growth_rate, 1),
            'trend_period_days': period_days
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting trend analysis: {str(e)}")
        return {
            'daily_trends': [],
            'conversation_growth_rate': 0,
            'trend_period_days': period_days
        }


def get_customer_detailed_insights(customer_id):
    """Get detailed insights for specific customer"""
    try:
        # Get customer interaction history
        interaction_history = frappe.db.sql("""
            SELECT
                DATE(creation) as date,
                COUNT(*) as message_count,
                AVG(CASE
                    WHEN sentiment = 'positive' THEN 1
                    WHEN sentiment = 'negative' THEN -1
                    ELSE 0
                END) as avg_sentiment,
                GROUP_CONCAT(DISTINCT channel_type) as channels_used
            FROM `tabMessage`
            WHERE sender_id = %s
            AND creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            GROUP BY DATE(creation)
            ORDER BY date DESC
            LIMIT 30
        """, (customer_id,), as_dict=True)

        # Get customer topics/categories
        topics = frappe.db.sql("""
            SELECT
                CASE
                    WHEN message_content LIKE '%payment%' THEN 'Payment'
                    WHEN message_content LIKE '%claim%' THEN 'Claims'
                    WHEN message_content LIKE '%registration%' THEN 'Registration'
                    WHEN message_content LIKE '%compliance%' THEN 'Compliance'
                    ELSE 'General'
                END as topic,
                COUNT(*) as count
            FROM `tabMessage`
            WHERE sender_id = %s
            AND creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            GROUP BY topic
            ORDER BY count DESC
        """, (customer_id,), as_dict=True)

        # Calculate engagement metrics
        total_messages = sum(h['message_count'] for h in interaction_history)
        avg_sentiment = sum(h['avg_sentiment'] for h in interaction_history) / len(interaction_history) if interaction_history else 0

        return {
            'interaction_history': interaction_history,
            'topic_distribution': topics,
            'engagement_metrics': {
                'total_messages_90_days': total_messages,
                'avg_sentiment_score': round(avg_sentiment, 2),
                'interaction_frequency': round(total_messages / 90, 2) if total_messages > 0 else 0
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting customer detailed insights: {str(e)}")
        return {
            'interaction_history': [],
            'topic_distribution': [],
            'engagement_metrics': {}
        }


def calculate_capacity_metrics(forecast_data):
    """Calculate capacity metrics from forecast data"""
    try:
        if not forecast_data:
            return {}

        # Calculate peak and average volumes
        volumes = [f['predicted_volume'] for f in forecast_data]
        peak_volume = max(volumes)
        avg_volume = sum(volumes) / len(volumes)
        min_volume = min(volumes)

        # Calculate capacity utilization (assuming current capacity)
        current_capacity = get_current_agent_capacity()
        peak_utilization = (peak_volume / current_capacity * 100) if current_capacity > 0 else 0
        avg_utilization = (avg_volume / current_capacity * 100) if current_capacity > 0 else 0

        return {
            'peak_volume': peak_volume,
            'avg_volume': round(avg_volume, 1),
            'min_volume': min_volume,
            'volume_variance': round(peak_volume - min_volume, 1),
            'peak_utilization_percentage': round(peak_utilization, 1),
            'avg_utilization_percentage': round(avg_utilization, 1),
            'current_capacity': current_capacity
        }

    except Exception as e:
        frappe.log_error(f"Error calculating capacity metrics: {str(e)}")
        return {}


def generate_staffing_recommendations(forecast_data):
    """Generate staffing recommendations based on forecast"""
    try:
        if not forecast_data:
            return {}

        # Calculate required agents (assuming 1 agent handles 10 conversations per day)
        conversations_per_agent_per_day = 10

        recommendations = []
        for forecast in forecast_data:
            required_agents = math.ceil(forecast['predicted_volume'] / conversations_per_agent_per_day)

            recommendations.append({
                'date': forecast['date'],
                'predicted_volume': forecast['predicted_volume'],
                'recommended_agents': required_agents,
                'confidence_range': {
                    'min_agents': math.ceil(forecast['confidence_low'] / conversations_per_agent_per_day),
                    'max_agents': math.ceil(forecast['confidence_high'] / conversations_per_agent_per_day)
                }
            })

        # Calculate overall recommendations
        avg_required = sum(r['recommended_agents'] for r in recommendations) / len(recommendations)
        peak_required = max(r['recommended_agents'] for r in recommendations)

        return {
            'daily_recommendations': recommendations,
            'summary': {
                'avg_agents_required': round(avg_required, 1),
                'peak_agents_required': peak_required,
                'current_agents': get_current_agent_count(),
                'additional_agents_needed': max(0, peak_required - get_current_agent_count())
            }
        }

    except Exception as e:
        frappe.log_error(f"Error generating staffing recommendations: {str(e)}")
        return {}


def get_current_capacity_status():
    """Get current system capacity status"""
    try:
        # Get current agent availability
        agent_status = frappe.db.sql("""
            SELECT
                availability_status,
                COUNT(*) as count,
                SUM(current_workload) as total_workload,
                SUM(max_concurrent_conversations) as total_capacity
            FROM `tabAgent Profile` ap
            LEFT JOIN `tabUser` u ON ap.user = u.name
            WHERE u.enabled = 1
            GROUP BY availability_status
        """, as_dict=True)

        # Calculate totals
        total_agents = sum(a['count'] for a in agent_status)
        total_capacity = sum(a['total_capacity'] for a in agent_status)
        total_workload = sum(a['total_workload'] for a in agent_status)

        utilization = (total_workload / total_capacity * 100) if total_capacity > 0 else 0

        return {
            'agent_status_breakdown': agent_status,
            'total_agents': total_agents,
            'total_capacity': total_capacity,
            'current_workload': total_workload,
            'utilization_percentage': round(utilization, 1),
            'available_capacity': max(0, total_capacity - total_workload)
        }

    except Exception as e:
        frappe.log_error(f"Error getting current capacity status: {str(e)}")
        return {
            'total_agents': 0,
            'total_capacity': 0,
            'current_workload': 0,
            'utilization_percentage': 0
        }


def get_current_agent_capacity():
    """Get current total agent capacity"""
    try:
        capacity = frappe.db.sql("""
            SELECT SUM(max_concurrent_conversations) as total_capacity
            FROM `tabAgent Profile` ap
            LEFT JOIN `tabUser` u ON ap.user = u.name
            WHERE u.enabled = 1 AND ap.availability_status = 'Available'
        """, as_dict=True)

        return capacity[0]['total_capacity'] if capacity and capacity[0]['total_capacity'] else 0

    except Exception as e:
        frappe.log_error(f"Error getting current agent capacity: {str(e)}")
        return 0


def get_current_agent_count():
    """Get current number of active agents"""
    try:
        count = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabAgent Profile` ap
            LEFT JOIN `tabUser` u ON ap.user = u.name
            WHERE u.enabled = 1 AND ap.availability_status = 'Available'
        """, as_dict=True)

        return count[0]['count'] if count else 0

    except Exception as e:
        frappe.log_error(f"Error getting current agent count: {str(e)}")
        return 0
