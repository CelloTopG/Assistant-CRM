import frappe
from frappe import _
from datetime import datetime, timedelta
import json
import pytz
from typing import Dict, List, Any, Optional
from assistant_crm.services.auto_reminder_service import AutoReminderService


class IntelligentSchedulerService:
    """Advanced scheduling service for WCFCB reminder automation"""
    
    def __init__(self):
        self.timezone = pytz.timezone('Africa/Lusaka')
        self.auto_reminder = AutoReminderService()
        self.scheduling_rules = self.load_scheduling_rules()
    
    def load_scheduling_rules(self) -> Dict[str, Any]:
        """Load intelligent scheduling rules"""
        return {
            'business_hours': {
                'start': 8,  # 8 AM
                'end': 17,   # 5 PM
                'timezone': 'Africa/Lusaka'
            },
            'working_days': [1, 2, 3, 4, 5],  # Monday to Friday
            'holidays': self.get_zambian_holidays(),
            'optimal_send_times': {
                'payment_reminders': {
                    'morning': 9,    # 9 AM
                    'afternoon': 14  # 2 PM
                },
                'returns_reminders': {
                    'morning': 10,   # 10 AM
                    'afternoon': 15  # 3 PM
                },
                'urgent_reminders': {
                    'immediate': True,
                    'max_delay_hours': 2
                }
            },
            'frequency_limits': {
                'daily_max_per_employer': 3,
                'weekly_max_per_employer': 10,
                'monthly_max_per_employer': 30
            },
            'priority_scheduling': {
                'Urgent': {'delay_minutes': 0, 'retry_hours': [1, 4, 8]},
                'High': {'delay_minutes': 30, 'retry_hours': [2, 8, 24]},
                'Medium': {'delay_minutes': 60, 'retry_hours': [4, 24, 72]},
                'Low': {'delay_minutes': 120, 'retry_hours': [8, 48, 168]}
            }
        }
    
    def get_zambian_holidays(self) -> List[str]:
        """Get Zambian public holidays for current year"""
        current_year = datetime.now().year
        holidays = [
            f'{current_year}-01-01',  # New Year's Day
            f'{current_year}-03-08',  # International Women's Day
            f'{current_year}-03-12',  # Youth Day
            f'{current_year}-05-01',  # Labour Day
            f'{current_year}-05-25',  # Africa Day
            f'{current_year}-07-06',  # Heroes Day (first Monday in July)
            f'{current_year}-07-07',  # Unity Day (first Tuesday in July)
            f'{current_year}-08-07',  # Farmers' Day (first Monday in August)
            f'{current_year}-10-24',  # Independence Day
            f'{current_year}-12-25',  # Christmas Day
        ]
        return holidays
    
    def schedule_reminder_batch(self, reminder_type: str, priority: str = 'Medium') -> Dict[str, Any]:
        """Schedule a batch of reminders with intelligent timing"""
        try:
            if reminder_type == 'payment':
                reminders_data = self.auto_reminder.get_upcoming_payment_deadlines()
            elif reminder_type == 'returns':
                reminders_data = self.auto_reminder.get_upcoming_returns_deadlines()
            else:
                return {'success': False, 'error': 'Invalid reminder type'}
            
            scheduled_reminders = []
            total_processed = 0
            
            for reminder_data in reminders_data:
                try:
                    # Calculate optimal send time
                    optimal_time = self.calculate_optimal_send_time(
                        reminder_data, reminder_type, priority
                    )
                    
                    # Check frequency limits
                    if not self.check_frequency_limits(reminder_data.get('employer_number')):
                        continue
                    
                    # Schedule the reminder
                    schedule_result = self.schedule_single_reminder(
                        reminder_data, optimal_time, reminder_type
                    )
                    
                    if schedule_result.get('success'):
                        scheduled_reminders.append(schedule_result)
                    
                    total_processed += 1
                    
                except Exception as e:
                    frappe.log_error(f"Error scheduling reminder for {reminder_data.get('employer_number')}: {str(e)}")
            
            return {
                'success': True,
                'scheduled_count': len(scheduled_reminders),
                'total_processed': total_processed,
                'scheduled_reminders': scheduled_reminders
            }
            
        except Exception as e:
            frappe.log_error(f"Error in batch scheduling: {str(e)}", "Intelligent Scheduler")
            return {'success': False, 'error': str(e)}
    
    def calculate_optimal_send_time(self, reminder_data: Dict[str, Any], 
                                  reminder_type: str, priority: str) -> datetime:
        """Calculate optimal time to send reminder based on multiple factors"""
        try:
            now = datetime.now(self.timezone)
            
            # Get priority-based delay
            priority_rules = self.scheduling_rules['priority_scheduling'].get(priority, {})
            delay_minutes = priority_rules.get('delay_minutes', 60)
            
            # Calculate base send time
            base_time = now + timedelta(minutes=delay_minutes)
            
            # Adjust for business hours
            optimal_time = self.adjust_for_business_hours(base_time, reminder_type)
            
            # Adjust for working days
            optimal_time = self.adjust_for_working_days(optimal_time)
            
            # Adjust for holidays
            optimal_time = self.adjust_for_holidays(optimal_time)
            
            # Adjust for employer preferences
            optimal_time = self.adjust_for_employer_preferences(
                optimal_time, reminder_data.get('employer_number')
            )
            
            return optimal_time
            
        except Exception as e:
            frappe.log_error(f"Error calculating optimal send time: {str(e)}")
            return datetime.now(self.timezone) + timedelta(hours=1)
    
    def adjust_for_business_hours(self, send_time: datetime, reminder_type: str) -> datetime:
        """Adjust send time to fall within business hours"""
        try:
            business_hours = self.scheduling_rules['business_hours']
            optimal_times = self.scheduling_rules['optimal_send_times'].get(reminder_type, {})
            
            # If it's urgent, allow immediate sending during extended hours
            if reminder_type == 'urgent_reminders':
                if 7 <= send_time.hour <= 20:  # 7 AM to 8 PM
                    return send_time
            
            # Check if within business hours
            if business_hours['start'] <= send_time.hour < business_hours['end']:
                # Adjust to optimal time within business hours
                if 'morning' in optimal_times and send_time.hour < 12:
                    return send_time.replace(hour=optimal_times['morning'], minute=0, second=0)
                elif 'afternoon' in optimal_times and send_time.hour >= 12:
                    return send_time.replace(hour=optimal_times['afternoon'], minute=0, second=0)
                else:
                    return send_time
            
            # If outside business hours, schedule for next business day
            if send_time.hour < business_hours['start']:
                # Too early - schedule for start of business
                return send_time.replace(hour=business_hours['start'], minute=0, second=0)
            else:
                # Too late - schedule for next day
                next_day = send_time + timedelta(days=1)
                return next_day.replace(hour=business_hours['start'], minute=0, second=0)
                
        except Exception as e:
            frappe.log_error(f"Error adjusting for business hours: {str(e)}")
            return send_time
    
    def adjust_for_working_days(self, send_time: datetime) -> datetime:
        """Adjust send time to fall on working days"""
        try:
            working_days = self.scheduling_rules['working_days']
            
            # Check if it's a working day (Monday=1, Sunday=7)
            weekday = send_time.weekday() + 1
            
            if weekday in working_days:
                return send_time
            
            # Find next working day
            days_to_add = 0
            while True:
                days_to_add += 1
                next_day = send_time + timedelta(days=days_to_add)
                if (next_day.weekday() + 1) in working_days:
                    return next_day.replace(hour=self.scheduling_rules['business_hours']['start'], 
                                          minute=0, second=0)
                if days_to_add > 7:  # Safety check
                    break
            
            return send_time
            
        except Exception as e:
            frappe.log_error(f"Error adjusting for working days: {str(e)}")
            return send_time
    
    def adjust_for_holidays(self, send_time: datetime) -> datetime:
        """Adjust send time to avoid public holidays"""
        try:
            holidays = self.scheduling_rules['holidays']
            send_date_str = send_time.strftime('%Y-%m-%d')
            
            if send_date_str in holidays:
                # Find next non-holiday working day
                days_to_add = 1
                while days_to_add <= 7:
                    next_day = send_time + timedelta(days=days_to_add)
                    next_date_str = next_day.strftime('%Y-%m-%d')
                    weekday = next_day.weekday() + 1
                    
                    if (next_date_str not in holidays and 
                        weekday in self.scheduling_rules['working_days']):
                        return next_day.replace(hour=self.scheduling_rules['business_hours']['start'],
                                              minute=0, second=0)
                    days_to_add += 1
            
            return send_time
            
        except Exception as e:
            frappe.log_error(f"Error adjusting for holidays: {str(e)}")
            return send_time
    
    def adjust_for_employer_preferences(self, send_time: datetime, employer_number: str) -> datetime:
        """Adjust send time based on employer communication preferences"""
        try:
            # Get employer preferences from database
            preferences = frappe.db.sql("""
                SELECT preferred_time, preferred_days, timezone
                FROM `tabEmployer Communication Preferences`
                WHERE employer_number = %s AND is_active = 1
                LIMIT 1
            """, (employer_number,), as_dict=True)
            
            if preferences:
                pref = preferences[0]
                
                # Adjust for preferred time
                if pref.get('preferred_time'):
                    preferred_hour = int(pref['preferred_time'].split(':')[0])
                    if 8 <= preferred_hour <= 17:  # Within business hours
                        send_time = send_time.replace(hour=preferred_hour, minute=0, second=0)
                
                # Adjust for preferred days
                if pref.get('preferred_days'):
                    preferred_days = json.loads(pref['preferred_days'])
                    current_weekday = send_time.weekday() + 1
                    
                    if current_weekday not in preferred_days:
                        # Find next preferred day
                        for day_offset in range(1, 8):
                            next_day = send_time + timedelta(days=day_offset)
                            if (next_day.weekday() + 1) in preferred_days:
                                send_time = next_day
                                break
            
            return send_time
            
        except Exception as e:
            frappe.log_error(f"Error adjusting for employer preferences: {str(e)}")
            return send_time
    
    def check_frequency_limits(self, employer_number: str) -> bool:
        """Check if sending another reminder violates frequency limits"""
        try:
            limits = self.scheduling_rules['frequency_limits']
            today = datetime.now().date()
            
            # Check daily limit
            daily_count = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabReminder Activity Log`
                WHERE employer_number = %s AND DATE(reminder_date) = %s
            """, (employer_number, today), as_dict=True)
            
            if daily_count and daily_count[0]['count'] >= limits['daily_max_per_employer']:
                return False
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error checking frequency limits: {str(e)}")
            return True  # Allow sending if check fails
    
    def schedule_single_reminder(self, reminder_data: Dict[str, Any], 
                               send_time: datetime, reminder_type: str) -> Dict[str, Any]:
        """Schedule a single reminder for future sending"""
        try:
            # Create scheduled reminder entry
            scheduled_reminder = {
                'doctype': 'Scheduled Reminder',
                'employer_number': reminder_data.get('employer_number'),
                'reminder_type': reminder_type,
                'scheduled_time': send_time,
                'priority': reminder_data.get('priority', 'Medium'),
                'status': 'Scheduled',
                'reminder_data': json.dumps(reminder_data),
                'created_by': frappe.session.user
            }
            
            # Create document if doctype exists
            if frappe.db.exists('DocType', 'Scheduled Reminder'):
                doc = frappe.get_doc(scheduled_reminder)
                doc.insert()
                
                return {
                    'success': True,
                    'reminder_id': doc.name,
                    'scheduled_time': send_time.isoformat(),
                    'employer_number': reminder_data.get('employer_number')
                }
            else:
                # Log for manual processing
                frappe.log_error(f"Scheduled reminder: {json.dumps(scheduled_reminder)}", "Scheduled Reminders")
                return {
                    'success': True,
                    'scheduled_time': send_time.isoformat(),
                    'employer_number': reminder_data.get('employer_number'),
                    'note': 'Logged for manual processing'
                }
                
        except Exception as e:
            frappe.log_error(f"Error scheduling single reminder: {str(e)}")
            return {'success': False, 'error': str(e)}
