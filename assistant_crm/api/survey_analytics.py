import frappe
from frappe import _
from assistant_crm.services.survey_service import SurveyService
import json
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=False)
def get_campaign_analytics(campaign_name):
    """Get comprehensive analytics for a survey campaign"""
    try:
        survey_service = SurveyService()
        
        # Get campaign details
        campaign = frappe.get_doc('Survey Campaign', campaign_name)
        
        # Get basic analytics from service
        analytics = survey_service.generate_survey_analytics(campaign_name)
        
        # Get detailed response breakdown
        response_breakdown = get_response_breakdown(campaign_name)
        
        # Get question-wise analytics
        question_analytics = get_question_analytics(campaign_name)
        
        # Get demographic breakdown
        demographic_breakdown = get_demographic_breakdown(campaign_name)
        
        return {
            'success': True,
            'campaign_info': {
                'name': campaign.campaign_name,
                'type': campaign.survey_type,
                'status': campaign.status,
                'total_sent': campaign.total_sent or 0,
                'total_responses': campaign.total_responses or 0,
                'response_rate': campaign.response_rate or 0,
                'average_rating': campaign.average_rating or 0
            },
            'analytics': analytics,
            'response_breakdown': response_breakdown,
            'question_analytics': question_analytics,
            'demographic_breakdown': demographic_breakdown
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get campaign analytics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_response_breakdown(campaign_name):
    """Get detailed response status breakdown"""
    breakdown = frappe.db.sql("""
        SELECT status, COUNT(*) as count,
               AVG(sentiment_score) as avg_sentiment
        FROM `tabSurvey Response`
        WHERE campaign = %s
        GROUP BY status
    """, (campaign_name,), as_dict=True)
    
    # Calculate percentages
    total_responses = sum(item['count'] for item in breakdown)
    for item in breakdown:
        item['percentage'] = (item['count'] / total_responses * 100) if total_responses > 0 else 0
    
    return breakdown

def get_question_analytics(campaign_name):
    """Get analytics for each question in the survey"""
    # Get all completed responses
    responses = frappe.db.sql("""
        SELECT answers
        FROM `tabSurvey Response`
        WHERE campaign = %s AND status = 'Completed'
    """, (campaign_name,), as_dict=True)
    
    if not responses:
        return []
    
    # Get campaign questions
    campaign = frappe.get_doc('Survey Campaign', campaign_name)
    questions = sorted(campaign.survey_questions, key=lambda x: x.order or 0)
    
    question_analytics = []
    
    for i, question in enumerate(questions):
        analytics = {
            'question_text': question.question_text,
            'question_type': question.question_type,
            'order': question.order,
            'responses': []
        }
        
        # Collect responses for this question
        question_responses = []
        for response in responses:
            try:
                answers_data = json.loads(response['answers']) if isinstance(response['answers'], str) else response['answers']
                if i < len(answers_data) and answers_data[i].get('value'):
                    question_responses.append(answers_data[i]['value'])
            except:
                continue
        
        # Analyze based on question type
        if question.question_type == 'Rating':
            analytics.update(analyze_rating_responses(question_responses))
        elif question.question_type == 'Multiple Choice':
            analytics.update(analyze_multiple_choice_responses(question_responses))
        elif question.question_type == 'Text':
            analytics.update(analyze_text_responses(question_responses))
        elif question.question_type == 'Yes/No':
            analytics.update(analyze_yes_no_responses(question_responses))
        
        question_analytics.append(analytics)
    
    return question_analytics

def analyze_rating_responses(responses):
    """Analyze rating question responses"""
    if not responses:
        return {'total_responses': 0}
    
    ratings = [float(r) for r in responses if r]
    
    # Calculate distribution
    distribution = {}
    for rating in [1, 2, 3, 4, 5]:
        distribution[str(rating)] = ratings.count(rating)
    
    return {
        'total_responses': len(ratings),
        'average_rating': sum(ratings) / len(ratings) if ratings else 0,
        'distribution': distribution,
        'satisfaction_rate': (sum(1 for r in ratings if r >= 4) / len(ratings) * 100) if ratings else 0
    }

def analyze_multiple_choice_responses(responses):
    """Analyze multiple choice question responses"""
    if not responses:
        return {'total_responses': 0}
    
    # Count each option
    option_counts = {}
    for response in responses:
        option_counts[response] = option_counts.get(response, 0) + 1
    
    # Calculate percentages
    total = len(responses)
    option_percentages = {option: (count / total * 100) for option, count in option_counts.items()}
    
    return {
        'total_responses': total,
        'option_counts': option_counts,
        'option_percentages': option_percentages,
        'most_popular': max(option_counts.items(), key=lambda x: x[1])[0] if option_counts else None
    }

def analyze_text_responses(responses):
    """Analyze text question responses"""
    if not responses:
        return {'total_responses': 0}
    
    # Basic text analysis
    total_responses = len(responses)
    avg_length = sum(len(r) for r in responses) / total_responses if responses else 0
    
    # Simple keyword analysis
    all_text = ' '.join(responses).lower()
    common_words = get_common_words(all_text)
    
    return {
        'total_responses': total_responses,
        'average_length': avg_length,
        'common_words': common_words,
        'sample_responses': responses[:5]  # First 5 responses as samples
    }

def analyze_yes_no_responses(responses):
    """Analyze Yes/No question responses"""
    if not responses:
        return {'total_responses': 0}
    
    yes_count = sum(1 for r in responses if r.lower() in ['yes', 'y', '1', 'true'])
    no_count = len(responses) - yes_count
    
    return {
        'total_responses': len(responses),
        'yes_count': yes_count,
        'no_count': no_count,
        'yes_percentage': (yes_count / len(responses) * 100) if responses else 0,
        'no_percentage': (no_count / len(responses) * 100) if responses else 0
    }

def get_common_words(text, limit=10):
    """Get most common words from text"""
    import re
    from collections import Counter
    
    # Simple word extraction (excluding common stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
    
    words = re.findall(r'\b\w+\b', text.lower())
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    return dict(Counter(filtered_words).most_common(limit))

def get_demographic_breakdown(campaign_name):
    """Get demographic breakdown of survey responses"""
    demographic_data = frappe.db.sql("""
        SELECT c.stakeholder_type, COUNT(sr.name) as response_count,
               AVG(sr.sentiment_score) as avg_sentiment
        FROM `tabSurvey Response` sr
        LEFT JOIN `tabContact` c ON sr.recipient_id = c.name
        WHERE sr.campaign = %s AND sr.status = 'Completed'
        GROUP BY c.stakeholder_type
    """, (campaign_name,), as_dict=True)
    
    return demographic_data

@frappe.whitelist(allow_guest=False)
def get_survey_dashboard_data(period='month'):
    """Get dashboard data for all surveys"""
    # Calculate date range
    if period == 'week':
        start_date = frappe.utils.add_days(frappe.utils.today(), -7)
    elif period == 'month':
        start_date = frappe.utils.add_days(frappe.utils.today(), -30)
    elif period == 'quarter':
        start_date = frappe.utils.add_days(frappe.utils.today(), -90)
    else:
        start_date = frappe.utils.add_days(frappe.utils.today(), -30)
    
    end_date = frappe.utils.today()
    
    # Get campaign summary
    campaigns = frappe.db.sql("""
        SELECT name, campaign_name, survey_type, status,
               total_sent, total_responses, response_rate, average_rating
        FROM `tabSurvey Campaign`
        WHERE creation BETWEEN %s AND %s
        ORDER BY creation DESC
    """, (start_date, end_date), as_dict=True)
    
    # Calculate overall statistics
    total_campaigns = len(campaigns)
    total_sent = sum(c.get('total_sent', 0) for c in campaigns)
    total_responses = sum(c.get('total_responses', 0) for c in campaigns)
    overall_response_rate = (total_responses / total_sent * 100) if total_sent > 0 else 0
    
    # Get sentiment trends
    sentiment_trends = frappe.db.sql("""
        SELECT DATE(response_time) as date,
               AVG(sentiment_score) as avg_sentiment,
               COUNT(*) as response_count
        FROM `tabSurvey Response`
        WHERE response_time BETWEEN %s AND %s
        AND status = 'Completed'
        GROUP BY DATE(response_time)
        ORDER BY date
    """, (start_date, end_date), as_dict=True)
    
    # Get top performing campaigns
    top_campaigns = sorted(campaigns, key=lambda x: x.get('response_rate', 0), reverse=True)[:5]
    
    return {
        'success': True,
        'period': period,
        'summary': {
            'total_campaigns': total_campaigns,
            'total_sent': total_sent,
            'total_responses': total_responses,
            'overall_response_rate': overall_response_rate
        },
        'campaigns': campaigns,
        'sentiment_trends': sentiment_trends,
        'top_campaigns': top_campaigns
    }

@frappe.whitelist(allow_guest=False)
def export_survey_data(campaign_name, format='json'):
    """Export survey data in various formats"""
    try:
        # Get campaign data
        campaign = frappe.get_doc('Survey Campaign', campaign_name)
        
        # Get all responses
        responses = frappe.db.sql("""
            SELECT sr.*, c.first_name, c.last_name, c.stakeholder_type
            FROM `tabSurvey Response` sr
            LEFT JOIN `tabContact` c ON sr.recipient_id = c.name
            WHERE sr.campaign = %s
            ORDER BY sr.response_time DESC
        """, (campaign_name,), as_dict=True)
        
        # Get analytics
        analytics = get_campaign_analytics(campaign_name)
        
        export_data = {
            'campaign_info': {
                'name': campaign.campaign_name,
                'type': campaign.survey_type,
                'status': campaign.status,
                'start_date': str(campaign.start_date) if campaign.start_date else None,
                'end_date': str(campaign.end_date) if campaign.end_date else None
            },
            'responses': responses,
            'analytics': analytics.get('analytics', {}),
            'exported_at': frappe.utils.now(),
            'exported_by': frappe.session.user
        }
        
        if format == 'csv':
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            
            # Flatten response data for CSV
            csv_data = []
            for response in responses:
                row = {
                    'response_id': response['name'],
                    'recipient_name': f"{response.get('first_name', '')} {response.get('last_name', '')}".strip(),
                    'stakeholder_type': response.get('stakeholder_type', ''),
                    'status': response['status'],
                    'sent_time': response.get('sent_time', ''),
                    'response_time': response.get('response_time', ''),
                    'sentiment_score': response.get('sentiment_score', '')
                }
                
                # Add answer data
                if response.get('answers'):
                    try:
                        answers = json.loads(response['answers']) if isinstance(response['answers'], str) else response['answers']
                        for i, answer in enumerate(answers):
                            row[f'question_{i+1}_answer'] = answer.get('value', '')
                    except:
                        pass
                
                csv_data.append(row)
            
            if csv_data:
                writer = csv.DictWriter(output, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
            
            return {
                'success': True,
                'format': 'csv',
                'data': output.getvalue()
            }
        
        return {
            'success': True,
            'format': 'json',
            'data': export_data
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to export survey data: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@frappe.whitelist(allow_guest=False)
def get_real_time_survey_alerts():
    """Get real-time alerts for survey campaigns"""
    alerts = []
    
    # Low response rate alerts
    low_response_campaigns = frappe.db.sql("""
        SELECT name, campaign_name, response_rate, total_sent
        FROM `tabSurvey Campaign`
        WHERE status = 'Active'
        AND total_sent > 10
        AND response_rate < 20
    """, as_dict=True)
    
    for campaign in low_response_campaigns:
        alerts.append({
            'type': 'low_response_rate',
            'priority': 'medium',
            'message': f"Low response rate ({campaign['response_rate']:.1f}%) for campaign '{campaign['campaign_name']}'",
            'campaign': campaign['name']
        })
    
    # Negative sentiment alerts
    negative_sentiment = frappe.db.sql("""
        SELECT sr.campaign, sc.campaign_name, COUNT(*) as negative_count
        FROM `tabSurvey Response` sr
        JOIN `tabSurvey Campaign` sc ON sr.campaign = sc.name
        WHERE sr.sentiment_score < -0.5
        AND sr.response_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY sr.campaign
        HAVING negative_count >= 3
    """, as_dict=True)
    
    for sentiment in negative_sentiment:
        alerts.append({
            'type': 'negative_sentiment',
            'priority': 'high',
            'message': f"Multiple negative responses ({sentiment['negative_count']}) for campaign '{sentiment['campaign_name']}'",
            'campaign': sentiment['campaign']
        })
    
    return {
        'success': True,
        'alerts': alerts,
        'alert_count': len(alerts)
    }
