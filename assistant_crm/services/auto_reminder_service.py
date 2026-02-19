import frappe
from frappe import _
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional
from assistant_crm.services.bulk_messaging_service import BulkMessagingService
from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService


class AutoReminderService:
    """Advanced AI-powered reminder system for WCFCB processes"""
    
    def __init__(self):
        self.bulk_messaging = BulkMessagingService()
        self.corebusiness = CoreBusinessIntegrationService()
        self.reminder_templates = self.load_reminder_templates()
        self.business_rules = self.load_business_rules()
    
    def load_reminder_templates(self) -> Dict[str, Any]:
        """Load reminder templates from database"""
        try:
            templates = frappe.db.sql("""
                SELECT name, template_type, content, channels, 
                       advance_days, language, is_active
                FROM `tabMessage Template`
                WHERE template_type LIKE '%reminder%' AND is_active = 1
            """, as_dict=True)
            
            template_dict = {}
            for template in templates:
                template_dict[template.template_type] = template
            
            return template_dict
        except Exception as e:
            frappe.log_error(f"Error loading reminder templates: {str(e)}", "Auto Reminder Service")
            return {}
    
    def load_business_rules(self) -> Dict[str, Any]:
        """Load business rules for reminder scheduling"""
        return {
            'payment_reminders': {
                'advance_days': [30, 14, 7, 3, 1],  # Days before due date
                'escalation_days': [1, 3, 7],       # Days after due date
                'business_hours': {'start': 8, 'end': 17},
                'working_days': [1, 2, 3, 4, 5],    # Monday to Friday
                'priority_mapping': {
                    'high_value': 'High',
                    'regular': 'Medium',
                    'small_employer': 'Low'
                }
            },
            'returns_reminders': {
                'advance_days': [21, 14, 7, 3, 1],
                'escalation_days': [1, 5, 10],
                'business_hours': {'start': 8, 'end': 17},
                'working_days': [1, 2, 3, 4, 5],
                'priority_mapping': {
                    'large_employer': 'High',
                    'medium_employer': 'Medium',
                    'small_employer': 'Low'
                }
            },
            'compliance_reminders': {
                'advance_days': [14, 7, 3, 1],
                'escalation_days': [1, 3, 5],
                'business_hours': {'start': 8, 'end': 17},
                'working_days': [1, 2, 3, 4, 5],
                'priority_mapping': {
                    'critical': 'Urgent',
                    'important': 'High',
                    'standard': 'Medium'
                }
            }
        }
    
    def create_payment_reminders(self) -> Dict[str, Any]:
        """Create automatic payment reminders for upcoming deadlines"""
        try:
            # Get employers with upcoming payment deadlines
            upcoming_deadlines = self.get_upcoming_payment_deadlines()
            
            reminders_created = 0
            errors = []
            
            for deadline in upcoming_deadlines:
                try:
                    reminder_result = self.send_payment_reminder(deadline)
                    if reminder_result.get('success'):
                        reminders_created += 1
                    else:
                        errors.append(f"Failed for {deadline.get('employer_number')}: {reminder_result.get('error')}")
                except Exception as e:
                    errors.append(f"Error processing {deadline.get('employer_number')}: {str(e)}")
            
            return {
                'success': True,
                'reminders_created': reminders_created,
                'total_processed': len(upcoming_deadlines),
                'errors': errors
            }
            
        except Exception as e:
            frappe.log_error(f"Error creating payment reminders: {str(e)}", "Auto Reminder Service")
            return {
                'success': False,
                'error': str(e),
                'reminders_created': 0
            }
    
    def create_returns_reminders(self) -> Dict[str, Any]:
        """Create automatic returns submission reminders"""
        try:
            # Get employers with upcoming returns deadlines
            upcoming_returns = self.get_upcoming_returns_deadlines()
            
            reminders_created = 0
            errors = []
            
            for return_deadline in upcoming_returns:
                try:
                    reminder_result = self.send_returns_reminder(return_deadline)
                    if reminder_result.get('success'):
                        reminders_created += 1
                    else:
                        errors.append(f"Failed for {return_deadline.get('employer_number')}: {reminder_result.get('error')}")
                except Exception as e:
                    errors.append(f"Error processing {return_deadline.get('employer_number')}: {str(e)}")
            
            return {
                'success': True,
                'reminders_created': reminders_created,
                'total_processed': len(upcoming_returns),
                'errors': errors
            }
            
        except Exception as e:
            frappe.log_error(f"Error creating returns reminders: {str(e)}", "Auto Reminder Service")
            return {
                'success': False,
                'error': str(e),
                'reminders_created': 0
            }
    
    def get_upcoming_payment_deadlines(self) -> List[Dict[str, Any]]:
        """Get employers with upcoming payment deadlines from CoreBusiness"""
        try:
            # Get advance notification days
            advance_days = self.business_rules['payment_reminders']['advance_days']
            
            # Calculate date range for upcoming deadlines
            today = datetime.now().date()
            max_advance = max(advance_days)
            end_date = today + timedelta(days=max_advance)
            
            # Query CoreBusiness for upcoming payment deadlines
            deadlines = self.corebusiness.get_payment_deadlines(
                start_date=today,
                end_date=end_date
            )
            
            # Filter and enhance deadline data
            upcoming_deadlines = []
            for deadline in deadlines:
                due_date = datetime.strptime(deadline.get('due_date'), '%Y-%m-%d').date()
                days_until_due = (due_date - today).days
                
                # Check if reminder should be sent today
                if days_until_due in advance_days:
                    enhanced_deadline = self.enhance_deadline_data(deadline, 'payment')
                    enhanced_deadline['days_until_due'] = days_until_due
                    enhanced_deadline['reminder_type'] = 'advance'
                    upcoming_deadlines.append(enhanced_deadline)
                
                # Check for overdue reminders
                elif days_until_due < 0:
                    days_overdue = abs(days_until_due)
                    escalation_days = self.business_rules['payment_reminders']['escalation_days']
                    if days_overdue in escalation_days:
                        enhanced_deadline = self.enhance_deadline_data(deadline, 'payment')
                        enhanced_deadline['days_overdue'] = days_overdue
                        enhanced_deadline['reminder_type'] = 'overdue'
                        upcoming_deadlines.append(enhanced_deadline)
            
            return upcoming_deadlines
            
        except Exception as e:
            frappe.log_error(f"Error getting payment deadlines: {str(e)}", "Auto Reminder Service")
            return []
    
    def get_upcoming_returns_deadlines(self) -> List[Dict[str, Any]]:
        """Get employers with upcoming returns submission deadlines"""
        try:
            # Get advance notification days
            advance_days = self.business_rules['returns_reminders']['advance_days']
            
            # Calculate date range for upcoming deadlines
            today = datetime.now().date()
            max_advance = max(advance_days)
            end_date = today + timedelta(days=max_advance)
            
            # Query CoreBusiness for upcoming returns deadlines
            deadlines = self.corebusiness.get_returns_deadlines(
                start_date=today,
                end_date=end_date
            )
            
            # Filter and enhance deadline data
            upcoming_deadlines = []
            for deadline in deadlines:
                due_date = datetime.strptime(deadline.get('due_date'), '%Y-%m-%d').date()
                days_until_due = (due_date - today).days
                
                # Check if reminder should be sent today
                if days_until_due in advance_days:
                    enhanced_deadline = self.enhance_deadline_data(deadline, 'returns')
                    enhanced_deadline['days_until_due'] = days_until_due
                    enhanced_deadline['reminder_type'] = 'advance'
                    upcoming_deadlines.append(enhanced_deadline)
                
                # Check for overdue reminders
                elif days_until_due < 0:
                    days_overdue = abs(days_until_due)
                    escalation_days = self.business_rules['returns_reminders']['escalation_days']
                    if days_overdue in escalation_days:
                        enhanced_deadline = self.enhance_deadline_data(deadline, 'returns')
                        enhanced_deadline['days_overdue'] = days_overdue
                        enhanced_deadline['reminder_type'] = 'overdue'
                        upcoming_deadlines.append(enhanced_deadline)
            
            return upcoming_deadlines
            
        except Exception as e:
            frappe.log_error(f"Error getting returns deadlines: {str(e)}", "Auto Reminder Service")
            return []
    
    def enhance_deadline_data(self, deadline: Dict[str, Any], reminder_type: str) -> Dict[str, Any]:
        """Enhance deadline data with additional context and priority"""
        try:
            enhanced = deadline.copy()

            # Get employer details from CoreBusiness
            employer_details = self.corebusiness.get_employer_details(deadline.get('employer_number'))
            if employer_details:
                enhanced.update(employer_details)

            # Determine priority based on business rules
            priority_mapping = self.business_rules[f'{reminder_type}_reminders']['priority_mapping']
            employer_category = enhanced.get('employer_category', 'regular')
            enhanced['priority'] = priority_mapping.get(employer_category, 'Medium')

            # Add contact information
            enhanced['contact_info'] = self.get_employer_contact_info(deadline.get('employer_number'))

            # Add preferred communication channels
            enhanced['preferred_channels'] = self.get_preferred_channels(deadline.get('employer_number'))

            return enhanced

        except Exception as e:
            frappe.log_error(f"Error enhancing deadline data: {str(e)}", "Auto Reminder Service")
            return deadline

    def send_payment_reminder(self, deadline_info: Dict[str, Any]) -> Dict[str, Any]:
        """Send payment reminder to employer"""
        try:
            # Get appropriate template
            template_key = f"payment_reminder_{deadline_info.get('reminder_type', 'advance')}"
            template = self.get_reminder_template(template_key, deadline_info.get('priority', 'Medium'))

            if not template:
                return {'success': False, 'error': 'No suitable template found'}

            # Personalize message
            message = self.personalize_reminder_message(template, deadline_info)

            # Determine optimal send time
            send_time = self.calculate_optimal_send_time(deadline_info)

            # Send via preferred channels
            channels = deadline_info.get('preferred_channels', ['Email'])
            contact_info = deadline_info.get('contact_info', {})

            results = []
            for channel in channels:
                try:
                    result = self.send_reminder_message(
                        contact_info, message, channel, send_time, 'Payment Reminder'
                    )
                    results.append(result)
                except Exception as e:
                    results.append({'success': False, 'channel': channel, 'error': str(e)})

            # Log reminder activity
            self.log_reminder_activity(deadline_info, template_key, results)

            return {
                'success': any(r.get('success') for r in results),
                'results': results,
                'message_sent': message[:100] + '...' if len(message) > 100 else message
            }

        except Exception as e:
            frappe.log_error(f"Error sending payment reminder: {str(e)}", "Auto Reminder Service")
            return {'success': False, 'error': str(e)}

    def send_returns_reminder(self, deadline_info: Dict[str, Any]) -> Dict[str, Any]:
        """Send returns submission reminder to employer"""
        try:
            # Get appropriate template
            template_key = f"returns_reminder_{deadline_info.get('reminder_type', 'advance')}"
            template = self.get_reminder_template(template_key, deadline_info.get('priority', 'Medium'))

            if not template:
                return {'success': False, 'error': 'No suitable template found'}

            # Personalize message
            message = self.personalize_reminder_message(template, deadline_info)

            # Determine optimal send time
            send_time = self.calculate_optimal_send_time(deadline_info)

            # Send via preferred channels
            channels = deadline_info.get('preferred_channels', ['Email'])
            contact_info = deadline_info.get('contact_info', {})

            results = []
            for channel in channels:
                try:
                    result = self.send_reminder_message(
                        contact_info, message, channel, send_time, 'Returns Reminder'
                    )
                    results.append(result)
                except Exception as e:
                    results.append({'success': False, 'channel': channel, 'error': str(e)})

            # Log reminder activity
            self.log_reminder_activity(deadline_info, template_key, results)

            return {
                'success': any(r.get('success') for r in results),
                'results': results,
                'message_sent': message[:100] + '...' if len(message) > 100 else message
            }

        except Exception as e:
            frappe.log_error(f"Error sending returns reminder: {str(e)}", "Auto Reminder Service")
            return {'success': False, 'error': str(e)}

    def get_reminder_template(self, template_key: str, priority: str) -> Optional[Dict[str, Any]]:
        """Get appropriate reminder template based on type and priority"""
        try:
            # First try to get specific template
            template = self.reminder_templates.get(template_key)

            # If not found, try generic template
            if not template:
                generic_key = template_key.split('_')[0] + '_reminder'
                template = self.reminder_templates.get(generic_key)

            # If still not found, get default template
            if not template:
                template = self.reminder_templates.get('default_reminder')

            return template

        except Exception as e:
            frappe.log_error(f"Error getting reminder template: {str(e)}", "Auto Reminder Service")
            return None

    def personalize_reminder_message(self, template: Dict[str, Any], deadline_info: Dict[str, Any]) -> str:
        """Personalize reminder message with deadline-specific information"""
        try:
            message = template.get('content', '')

            # Define replacement variables
            variables = {
                'employer_name': deadline_info.get('company_name', 'Valued Employer'),
                'employer_number': deadline_info.get('employer_number', ''),
                'amount_due': deadline_info.get('amount_due', ''),
                'due_date': deadline_info.get('due_date', ''),
                'days_until_due': deadline_info.get('days_until_due', ''),
                'days_overdue': deadline_info.get('days_overdue', ''),
                'contact_person': deadline_info.get('contact_person', ''),
                'reminder_type': deadline_info.get('reminder_type', ''),
                'priority': deadline_info.get('priority', 'Medium')
            }

            # Replace variables in message
            for key, value in variables.items():
                placeholder = f'{{{key}}}'
                if placeholder in message:
                    message = message.replace(placeholder, str(value))

            # Add WCFCB signature and branding
            message = self.add_wcfcb_branding(message, deadline_info.get('reminder_type'))

            return message

        except Exception as e:
            frappe.log_error(f"Error personalizing reminder message: {str(e)}", "Auto Reminder Service")
            return template.get('content', 'Reminder from WCFCB')

    def add_wcfcb_branding(self, message: str, reminder_type: str) -> str:
        """Add WCFCB branding and signature to reminder message"""
        try:
            # Add professional closing
            if not message.endswith('\n'):
                message += '\n'

            message += '\n'
            message += 'Best regards,\n'
            message += 'WorkCom - WCFCB Virtual Assistant\n'
            message += 'Workers\' Compensation Fund Control Board\n'
            message += '\n'
            message += 'For assistance, contact us:\n'
            message += '📞 Phone: +260-XXX-XXXX\n'
            message += '📧 Email: info@wcfcb.gov.zm\n'
            message += '🌐 Website: www.wcfcb.gov.zm\n'
            message += '\n'
            message += 'This is an automated reminder. Please do not reply to this message.'

            return message

        except Exception as e:
            frappe.log_error(f"Error adding WCFCB branding: {str(e)}", "Auto Reminder Service")
            return message

    def calculate_optimal_send_time(self, deadline_info: Dict[str, Any]) -> datetime:
        """Calculate optimal time to send reminder based on business rules"""
        try:
            now = datetime.now()
            reminder_type = deadline_info.get('reminder_type', 'advance')

            # Get business rules for the reminder type
            if 'payment' in str(deadline_info.get('type', '')):
                rules = self.business_rules['payment_reminders']
            elif 'returns' in str(deadline_info.get('type', '')):
                rules = self.business_rules['returns_reminders']
            else:
                rules = self.business_rules['compliance_reminders']

            business_hours = rules['business_hours']
            working_days = rules['working_days']

            # If current time is within business hours and working day, send now
            if (now.weekday() + 1 in working_days and
                business_hours['start'] <= now.hour < business_hours['end']):
                return now

            # Otherwise, schedule for next business day at start of business hours
            next_send_time = now.replace(hour=business_hours['start'], minute=0, second=0, microsecond=0)

            # If it's after business hours today, schedule for tomorrow
            if now.hour >= business_hours['end']:
                next_send_time += timedelta(days=1)

            # Ensure it's a working day
            while (next_send_time.weekday() + 1) not in working_days:
                next_send_time += timedelta(days=1)

            return next_send_time

        except Exception as e:
            frappe.log_error(f"Error calculating optimal send time: {str(e)}", "Auto Reminder Service")
            return datetime.now()

    def send_reminder_message(self, contact_info: Dict[str, Any], message: str,
                            channel: str, send_time: datetime, reminder_type: str) -> Dict[str, Any]:
        """Send reminder message via specified channel"""
        try:
            # Prepare recipient information
            recipient_data = {
                'employer_number': contact_info.get('employer_number'),
                'company_name': contact_info.get('company_name'),
                'email_id': contact_info.get('email'),
                'mobile_no': contact_info.get('phone'),
                'contact_person': contact_info.get('contact_person')
            }

            # Create campaign for the reminder
            campaign_data = {
                'campaign_name': f"{reminder_type} - {contact_info.get('employer_number')} - {send_time.strftime('%Y-%m-%d')}",
                'campaign_type': 'Triggered',
                'status': 'Draft',
                'channels': [{'channel_type': channel}],
                'custom_message': message,
                'send_immediately': send_time <= datetime.now(),
                'scheduled_time': send_time if send_time > datetime.now() else None,
                'timezone': 'Africa/Lusaka'
            }

            # Use bulk messaging service to send
            campaign_id = self.bulk_messaging.create_campaign(campaign_data)

            if campaign_id:
                # Execute campaign
                execution_result = self.bulk_messaging.execute_campaign(campaign_id)
                return {
                    'success': execution_result.get('success', False),
                    'campaign_id': campaign_id,
                    'channel': channel,
                    'send_time': send_time.isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create campaign',
                    'channel': channel
                }

        except Exception as e:
            frappe.log_error(f"Error sending reminder message: {str(e)}", "Auto Reminder Service")
            return {
                'success': False,
                'error': str(e),
                'channel': channel
            }

    def get_employer_contact_info(self, employer_number: str) -> Dict[str, Any]:
        """Get employer contact information"""
        try:
            # Query contact information from database
            contact_info = frappe.db.sql("""
                SELECT email_id as email, mobile_no as phone,
                       first_name, last_name, company_name
                FROM `tabContact`
                WHERE employer_number = %s AND is_primary_contact = 1
                LIMIT 1
            """, (employer_number,), as_dict=True)

            if contact_info:
                contact = contact_info[0]
                contact['contact_person'] = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                contact['employer_number'] = employer_number
                return contact
            else:
                # Return default contact info
                return {
                    'employer_number': employer_number,
                    'email': f'info@employer{employer_number}.com',
                    'phone': '',
                    'contact_person': 'Contact Person',
                    'company_name': f'Employer {employer_number}'
                }

        except Exception as e:
            frappe.log_error(f"Error getting employer contact info: {str(e)}", "Auto Reminder Service")
            return {
                'employer_number': employer_number,
                'email': '',
                'phone': '',
                'contact_person': 'Contact Person',
                'company_name': f'Employer {employer_number}'
            }

    def get_preferred_channels(self, employer_number: str) -> List[str]:
        """Get preferred communication channels for employer"""
        try:
            # Query channel preferences
            preferences = frappe.db.sql("""
                SELECT preferred_channels
                FROM `tabChannel Configuration`
                WHERE employer_number = %s AND is_active = 1
                LIMIT 1
            """, (employer_number,), as_dict=True)

            if preferences and preferences[0].get('preferred_channels'):
                return json.loads(preferences[0]['preferred_channels'])
            else:
                # Default channels
                return ['Email', 'SMS']

        except Exception as e:
            frappe.log_error(f"Error getting preferred channels: {str(e)}", "Auto Reminder Service")
            return ['Email']

    def log_reminder_activity(self, deadline_info: Dict[str, Any], template_key: str,
                            results: List[Dict[str, Any]]) -> None:
        """Log reminder activity for tracking and analytics"""
        try:
            activity_log = {
                'doctype': 'Reminder Activity Log',
                'employer_number': deadline_info.get('employer_number'),
                'reminder_type': template_key,
                'due_date': deadline_info.get('due_date'),
                'reminder_date': datetime.now().date(),
                'priority': deadline_info.get('priority'),
                'channels_used': [r.get('channel') for r in results],
                'success_count': sum(1 for r in results if r.get('success')),
                'total_attempts': len(results),
                'results': json.dumps(results)
            }

            # Create log entry (if doctype exists)
            if frappe.db.exists('DocType', 'Reminder Activity Log'):
                log_doc = frappe.get_doc(activity_log)
                log_doc.insert()

        except Exception as e:
            frappe.log_error(f"Error logging reminder activity: {str(e)}", "Auto Reminder Service")

