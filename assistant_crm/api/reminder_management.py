import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from assistant_crm.services.auto_reminder_service import AutoReminderService
from assistant_crm.services.intelligent_scheduler_service import IntelligentSchedulerService


@frappe.whitelist(allow_guest=False)
def create_payment_reminders():
    """Create automatic payment reminders for all upcoming deadlines"""
    try:
        auto_reminder = AutoReminderService()
        result = auto_reminder.create_payment_reminders()
        
        return {
            'success': result.get('success', False),
            'message': f"Created {result.get('reminders_created', 0)} payment reminders",
            'details': result
        }
        
    except Exception as e:
        frappe.log_error(f"Error in create_payment_reminders API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create payment reminders'
        }


@frappe.whitelist(allow_guest=False)
def create_returns_reminders():
    """Create automatic returns submission reminders for all upcoming deadlines"""
    try:
        auto_reminder = AutoReminderService()
        result = auto_reminder.create_returns_reminders()
        
        return {
            'success': result.get('success', False),
            'message': f"Created {result.get('reminders_created', 0)} returns reminders",
            'details': result
        }
        
    except Exception as e:
        frappe.log_error(f"Error in create_returns_reminders API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create returns reminders'
        }


@frappe.whitelist(allow_guest=False)
def schedule_reminder_batch(reminder_type, priority='Medium'):
    """Schedule a batch of reminders with intelligent timing"""
    try:
        scheduler = IntelligentSchedulerService()
        result = scheduler.schedule_reminder_batch(reminder_type, priority)
        
        return {
            'success': result.get('success', False),
            'message': f"Scheduled {result.get('scheduled_count', 0)} {reminder_type} reminders",
            'details': result
        }
        
    except Exception as e:
        frappe.log_error(f"Error in schedule_reminder_batch API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to schedule {reminder_type} reminders'
        }


@frappe.whitelist(allow_guest=False)
def get_reminder_dashboard_data(period='today'):
    """Get comprehensive reminder dashboard data"""
    try:
        # Calculate date range
        if period == 'today':
            start_date = end_date = frappe.utils.today()
        elif period == 'week':
            start_date = frappe.utils.add_days(frappe.utils.today(), -7)
            end_date = frappe.utils.today()
        elif period == 'month':
            start_date = frappe.utils.add_days(frappe.utils.today(), -30)
            end_date = frappe.utils.today()
        else:
            start_date = end_date = frappe.utils.today()
        
        # Get reminder statistics
        reminder_stats = get_reminder_statistics(start_date, end_date)
        
        # Get upcoming deadlines
        upcoming_deadlines = get_upcoming_deadlines()
        
        # Get recent reminder activity
        recent_activity = get_recent_reminder_activity(start_date, end_date)
        
        # Get performance metrics
        performance_metrics = get_reminder_performance_metrics(start_date, end_date)
        
        return {
            'success': True,
            'period': period,
            'date_range': {'start': start_date, 'end': end_date},
            'statistics': reminder_stats,
            'upcoming_deadlines': upcoming_deadlines,
            'recent_activity': recent_activity,
            'performance_metrics': performance_metrics
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_reminder_dashboard_data API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to load reminder dashboard data'
        }


@frappe.whitelist(allow_guest=False)
def get_employer_reminder_history(employer_number, limit=50):
    """Get reminder history for specific employer"""
    try:
        # Get reminder activity logs
        activity_logs = frappe.db.sql("""
            SELECT reminder_type, reminder_date, priority, channels_used,
                   success_count, total_attempts, results
            FROM `tabReminder Activity Log`
            WHERE employer_number = %s
            ORDER BY reminder_date DESC
            LIMIT %s
        """, (employer_number, limit), as_dict=True)
        
        # Get scheduled reminders
        scheduled_reminders = frappe.db.sql("""
            SELECT reminder_type, scheduled_time, priority, status
            FROM `tabScheduled Reminder`
            WHERE employer_number = %s AND status IN ('Scheduled', 'Processing')
            ORDER BY scheduled_time ASC
        """, (employer_number,), as_dict=True)
        
        return {
            'success': True,
            'employer_number': employer_number,
            'activity_logs': activity_logs,
            'scheduled_reminders': scheduled_reminders,
            'total_logs': len(activity_logs)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_employer_reminder_history API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to load reminder history for employer {employer_number}'
        }


@frappe.whitelist(allow_guest=False)
def update_reminder_preferences(employer_number, preferences):
    """Update reminder preferences for an employer"""
    try:
        # Parse preferences if it's a string
        if isinstance(preferences, str):
            preferences = json.loads(preferences)
        
        # Check if preferences record exists
        existing = frappe.db.exists('Employer Communication Preferences', 
                                  {'employer_number': employer_number})
        
        if existing:
            # Update existing preferences
            doc = frappe.get_doc('Employer Communication Preferences', existing)
            doc.update(preferences)
            doc.save()
        else:
            # Create new preferences record
            doc = frappe.get_doc({
                'doctype': 'Employer Communication Preferences',
                'employer_number': employer_number,
                **preferences
            })
            doc.insert()
        
        return {
            'success': True,
            'message': f'Updated reminder preferences for employer {employer_number}',
            'preferences': preferences
        }
        
    except Exception as e:
        frappe.log_error(f"Error in update_reminder_preferences API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to update preferences for employer {employer_number}'
        }


@frappe.whitelist(allow_guest=False)
def test_reminder_template(template_name, sample_data):
    """Test a reminder template with sample data"""
    try:
        # Parse sample data if it's a string
        if isinstance(sample_data, str):
            sample_data = json.loads(sample_data)
        
        # Get template
        template = frappe.get_doc('Message Template', template_name)
        
        # Create auto reminder service instance
        auto_reminder = AutoReminderService()
        
        # Personalize message with sample data
        personalized_message = auto_reminder.personalize_reminder_message(
            template.as_dict(), sample_data
        )
        
        return {
            'success': True,
            'template_name': template_name,
            'original_content': template.content,
            'personalized_content': personalized_message,
            'sample_data': sample_data
        }
        
    except Exception as e:
        frappe.log_error(f"Error in test_reminder_template API: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to test template {template_name}'
        }


def get_reminder_statistics(start_date, end_date):
    """Get reminder statistics for the specified period"""
    try:
        # Total reminders sent
        total_sent = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s
        """, (start_date, end_date), as_dict=True)
        
        # Success rate
        successful_reminders = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s AND success_count > 0
        """, (start_date, end_date), as_dict=True)
        
        # Reminders by type
        by_type = frappe.db.sql("""
            SELECT reminder_type, COUNT(*) as count
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s
            GROUP BY reminder_type
        """, (start_date, end_date), as_dict=True)
        
        # Reminders by priority
        by_priority = frappe.db.sql("""
            SELECT priority, COUNT(*) as count
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s
            GROUP BY priority
        """, (start_date, end_date), as_dict=True)
        
        total_count = total_sent[0]['count'] if total_sent else 0
        success_count = successful_reminders[0]['count'] if successful_reminders else 0
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'total_sent': total_count,
            'successful': success_count,
            'success_rate': round(success_rate, 2),
            'by_type': by_type,
            'by_priority': by_priority
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting reminder statistics: {str(e)}")
        return {
            'total_sent': 0,
            'successful': 0,
            'success_rate': 0,
            'by_type': [],
            'by_priority': []
        }


def get_upcoming_deadlines():
    """Get upcoming payment and returns deadlines"""
    try:
        auto_reminder = AutoReminderService()
        
        # Get upcoming payment deadlines
        payment_deadlines = auto_reminder.get_upcoming_payment_deadlines()
        
        # Get upcoming returns deadlines
        returns_deadlines = auto_reminder.get_upcoming_returns_deadlines()
        
        return {
            'payment_deadlines': payment_deadlines[:10],  # Limit to 10
            'returns_deadlines': returns_deadlines[:10],   # Limit to 10
            'total_payment': len(payment_deadlines),
            'total_returns': len(returns_deadlines)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting upcoming deadlines: {str(e)}")
        return {
            'payment_deadlines': [],
            'returns_deadlines': [],
            'total_payment': 0,
            'total_returns': 0
        }


def get_recent_reminder_activity(start_date, end_date):
    """Get recent reminder activity"""
    try:
        activity = frappe.db.sql("""
            SELECT employer_number, reminder_type, reminder_date, priority,
                   success_count, total_attempts
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s
            ORDER BY reminder_date DESC
            LIMIT 20
        """, (start_date, end_date), as_dict=True)
        
        return activity
        
    except Exception as e:
        frappe.log_error(f"Error getting recent reminder activity: {str(e)}")
        return []


def get_reminder_performance_metrics(start_date, end_date):
    """Get reminder performance metrics"""
    try:
        # Average response time (if tracked)
        avg_response_time = frappe.db.sql("""
            SELECT AVG(TIMESTAMPDIFF(HOUR, reminder_date, response_time)) as avg_hours
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s AND response_time IS NOT NULL
        """, (start_date, end_date), as_dict=True)
        
        # Channel effectiveness
        channel_effectiveness = frappe.db.sql("""
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(channels_used, '$[0]')) as channel,
                COUNT(*) as total,
                SUM(success_count) as successful
            FROM `tabReminder Activity Log`
            WHERE reminder_date BETWEEN %s AND %s
            GROUP BY JSON_UNQUOTE(JSON_EXTRACT(channels_used, '$[0]'))
        """, (start_date, end_date), as_dict=True)
        
        return {
            'avg_response_time_hours': avg_response_time[0]['avg_hours'] if avg_response_time and avg_response_time[0]['avg_hours'] else 0,
            'channel_effectiveness': channel_effectiveness
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting reminder performance metrics: {str(e)}")
        return {
            'avg_response_time_hours': 0,
            'channel_effectiveness': []
        }
