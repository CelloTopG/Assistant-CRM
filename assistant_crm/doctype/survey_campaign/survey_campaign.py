# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime

class SurveyCampaign(Document):
	def validate(self):
		"""Validate survey campaign data"""
		self.validate_dates()
		self.validate_questions()
		self.validate_distribution_channels()
	
	def validate_dates(self):
		"""Validate start and end dates"""
		if self.start_date and self.end_date:
			if frappe.utils.getdate(self.start_date) > frappe.utils.getdate(self.end_date):
				frappe.throw("Start date cannot be after end date")
	
	def validate_questions(self):
		"""Validate survey questions"""
		if not self.survey_questions:
			frappe.throw("At least one survey question is required")

		# Auto-normalize question order based on row position (idx)
		try:
			rows = sorted(list(self.survey_questions or []), key=lambda r: (getattr(r, 'idx', 0) or 0))
		except Exception:
			rows = list(self.survey_questions or [])
		seen = set()
		changed = False
		for i, q in enumerate(rows, start=1):
			if not getattr(q, 'order', None) or q.order in seen:
				q.order = i
				changed = True
			seen.add(q.order)
		# Final safety check (should not trigger after normalization)
		orders = [q.order for q in self.survey_questions if q.order]
		if len(orders) != len(set(orders)):
			frappe.throw("Question orders must be unique")
		if changed:
			try:
				frappe.msgprint("Question order auto-normalized to 1..N based on table order", indicator="blue", alert=True)
			except Exception:
				pass
	
	def validate_distribution_channels(self):
		"""Validate distribution channels"""
		if not self.distribution_channels:
			frappe.throw("At least one distribution channel is required")
		
		active_channels = [ch for ch in self.distribution_channels if ch.is_active]
		if not active_channels:
			frappe.throw("At least one distribution channel must be active")
	
	def on_submit(self):
		"""Actions when campaign is submitted"""
		# Do not mutate fields after submit to avoid 'Cannot Update After Submit'
		# Status is implicitly Active by virtue of submission; just distribute.
		self.distribute_survey()
	
	def distribute_survey(self):
		"""Distribute survey to target audience"""
		from assistant_crm.services.survey_service import SurveyService

		survey_service = SurveyService()
		result = survey_service.distribute_survey(self)

		if result.get('success'):
			targeted = result.get('targeted_count', result.get('recipient_count', 0))
			delivered = result.get('delivered_count', result.get('recipient_count', 0))
			stats = result.get('channel_stats', {}) or {}
			success_ch = [ch for ch, s in stats.items() if (s or {}).get('success', 0) > 0]
			failed_ch = []
			for ch, s in stats.items():
				if (s or {}).get('attempts', 0) > 0 and (s or {}).get('success', 0) == 0:
					reasons = (s or {}).get('reasons', {}) or {}
					top_reason = max(reasons, key=reasons.get) if reasons else 'failed'
					failed_ch.append(f"{ch} ({top_reason})")
			msg = (
				f"Targeted {targeted} user(s). Delivered: {delivered}. "
				f"Success: {', '.join(success_ch) if success_ch else 'None'}. "
				f"Failed: {', '.join(failed_ch) if failed_ch else 'None'}."
			)
			frappe.msgprint(msg)
		else:
			frappe.throw(f"Failed to distribute survey: {result.get('error', 'Unknown error')}")

@frappe.whitelist(allow_guest=False)
def get_target_audience_count(campaign_name):
	"""Get count of target audience for campaign"""
	try:
		if not frappe.db.exists('Survey Campaign', campaign_name):
			return {'count': 0, 'error': 'Campaign not found'}

		campaign = frappe.get_doc('Survey Campaign', campaign_name)

		from assistant_crm.services.survey_service import SurveyService
		survey_service = SurveyService()

		recipients = survey_service.get_survey_recipients(campaign)
		return {'count': len(recipients)}

	except Exception as e:
		frappe.log_error(f"Target audience count error: {str(e)}")
		return {'count': 0, 'error': str(e)}

@frappe.whitelist(allow_guest=False)
def preview_survey(campaign_name):
	"""Preview survey questions and format"""
	campaign = frappe.get_doc('Survey Campaign', campaign_name)
	
	# Sort questions by order
	questions = sorted(campaign.survey_questions, key=lambda x: x.order or 0)
	
	preview_data = {
		'campaign_name': campaign.campaign_name,
		'survey_type': campaign.survey_type,
		'questions': []
	}
	
	for q in questions:
		question_data = {
			'text': q.question_text,
			'type': q.question_type,
			'required': q.is_required,
			'order': q.order
		}
		
		if q.question_type == 'Multiple Choice' and q.options:
			question_data['options'] = q.options.split('\n')
		
		preview_data['questions'].append(question_data)
	
	return preview_data

@frappe.whitelist(allow_guest=False)
def launch_campaign(campaign_name):
	"""Launch survey campaign and distribute immediately.
	- If DocType is submittable, submit() will trigger on_submit -> distribute_survey()
	- If submit fails (no workflow/submittable), mark Active and call distribute_survey() manually
	"""
	try:
		if not frappe.db.exists('Survey Campaign', campaign_name):
			return {'success': False, 'error': 'Campaign not found'}

		campaign = frappe.get_doc('Survey Campaign', campaign_name)

		if (campaign.status or 'Draft') != 'Draft':
			return {'success': False, 'error': 'Only draft campaigns can be launched'}

		# Ensure dates
		if not campaign.start_date:
			campaign.start_date = frappe.utils.now()
		if not campaign.end_date:
			campaign.end_date = frappe.utils.add_days(campaign.start_date, 30)

		campaign.save()

		# Preferred path: submit (triggers on_submit -> distribute)
		try:
			campaign.submit()
			return {'success': True, 'message': 'Campaign submitted and distribution started'}
		except Exception as submit_error:
			frappe.log_error(f"Campaign submit error: {str(submit_error)}")
			# Fallback: activate and distribute manually
			campaign.status = 'Active'
			campaign.save()
			try:
				# Call the same distribution used on submit
				campaign.distribute_survey()
				return {'success': True, 'message': 'Campaign activated and distribution started'}
			except Exception as dist_error:
				frappe.log_error(f"Campaign distribution error (manual): {str(dist_error)}")
				return {'success': False, 'error': f'Distribution failed: {dist_error}'}

	except Exception as e:
		frappe.log_error(f"Launch campaign error: {str(e)}")
		return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=False)
def preview_recipients_from_doc(doc: dict | str, limit: int = 20):
	"""Preview recipients for the current (possibly unsaved) Survey Campaign form.
	Returns: {count: int, recipients: [...], active_channels: [...], safe_max_target: int, warnings: [...]}
	Adds warnings for unrecognized Custom Field filter_field values.
	"""
	try:
		import json as _json
		if isinstance(doc, str):
			doc = _json.loads(doc)
		# Build a transient Document from client JSON
		campaign = frappe.get_doc(doc)
		from assistant_crm.services.survey_service import SurveyService
		svc = SurveyService()
		recipients = svc.get_survey_recipients(campaign) or []
		count = len(recipients)
		# Active channels
		active_channels = [ch.channel for ch in (campaign.distribution_channels or []) if getattr(ch, 'is_active', 0)]
		# Safety threshold
		try:
			conf = frappe.get_conf() if hasattr(frappe, 'get_conf') else {}
			safe_max = int((conf or {}).get('survey_safe_max_target', 100))
		except Exception:
			safe_max = 100
		# Build warnings for unrecognized fields
		warnings = []
		field_keys = {'name','full_name','first_name','last_name','email_id','mobile_no','telegram_chat_id','facebook_psid','instagram_user_id'}

		# Valid fields for Beneficiary filtering (maps to ERPNext Contact and Customer type Individual)
		beneficiary_fields = {
			# Contact fields
			'first_name', 'last_name', 'full_name', 'email', 'email_id', 'phone', 'mobile', 'mobile_no',
			# Customer (Individual) fields via Dynamic Link
			'beneficiary_number', 'customer_name', 'nrc_number', 'tax_id', 'territory', 'customer_group', 'gender'
		}

		# Valid fields for Employer filtering (maps to ERPNext Customer type Company)
		employer_fields = {
			'employer_name', 'employer_code', 'customer_name', 'name',
			'email', 'email_id', 'phone', 'mobile', 'mobile_no',
			'territory', 'customer_group', 'industry', 'tax_id'
		}

		for f in (campaign.target_audience or []):
			ftype = (getattr(f, 'filter_type', '') or '').strip()
			ffield = (getattr(f, 'filter_field', '') or '').strip()

			if ftype == 'Custom Field':
				fkey = ffield.lower().replace(' ', '_').replace('-', '_')
				if fkey in ('full name', 'fullname'):
					fkey = 'full_name'
				if fkey and fkey not in field_keys:
					warnings.append(f"Unrecognized Custom Field '{ffield}'. Filter will be ignored. Use one of: {', '.join(sorted(field_keys))}.")

			elif ftype == 'Beneficiary':
				# Normalize field name for validation
				fkey = ffield.lower().replace(' ', '_').replace('-', '_')
				# Check if it's a known alias or actual field
				known_aliases = {'customer_name', 'customer name', 'id', 'name', 'email_address', 'email address',
								'phone_number', 'phone number', 'nrc', 'national_id'}
				if fkey not in known_aliases and fkey not in beneficiary_fields:
					warnings.append(f"Beneficiary field '{ffield}' may not exist. Valid fields: first_name, last_name, full_name, email, mobile, beneficiary_number, territory, customer_group.")

			elif ftype == 'Employer':
				# Normalize field name for validation
				fkey = ffield.lower().replace(' ', '_').replace('-', '_')
				# Check if it's a known alias or actual field
				known_aliases = {'id', 'code', 'name', 'company_name', 'company name', 'email_address', 'email address',
								'phone_number', 'phone number'}
				if fkey not in known_aliases and fkey not in employer_fields:
					warnings.append(f"Employer field '{ffield}' may not exist. Valid fields: employer_name, employer_code, email, mobile, territory, customer_group, industry.")
		# Sample recipients
		lim = int(limit or 20)
		sample = []
		for r in recipients[:lim]:
			row = {
				'name': r.get('name'),
				'first_name': r.get('first_name'),
				'last_name': r.get('last_name'),
				'email_id': r.get('email_id'),
				'mobile_no': r.get('mobile_no'),
				'telegram_chat_id': r.get('telegram_chat_id'),
				'facebook_psid': r.get('facebook_psid'),
				'instagram_user_id': r.get('instagram_user_id'),
				'ready': {}
			}
			for ch in active_channels:
				if ch == 'Telegram':
					row['ready'][ch] = bool(r.get('telegram_chat_id'))
				elif ch == 'Facebook':
					row['ready'][ch] = bool(r.get('facebook_psid'))
				elif ch == 'Instagram':
					row['ready'][ch] = bool(r.get('instagram_user_id'))
				elif ch in ('WhatsApp','SMS'):
					row['ready'][ch] = bool(r.get('mobile_no'))
				elif ch == 'Email':
					row['ready'][ch] = bool(r.get('email_id'))
			sample.append(row)
		return {
			'count': count,
			'recipients': sample,
			'active_channels': active_channels,
			'safe_max_target': safe_max,
			'warnings': warnings
		}
	except Exception as e:
		frappe.log_error(f"Preview recipients error: {str(e)}")
		return {'count': 0, 'recipients': [], 'active_channels': [], 'error': str(e), 'warnings': [str(e)]}

@frappe.whitelist(allow_guest=False)
def get_campaign_analytics(campaign_name):
	"""Get analytics for survey campaign"""
	campaign = frappe.get_doc('Survey Campaign', campaign_name)
	
	# Get response statistics
	responses = frappe.db.sql("""
		SELECT status, COUNT(*) as count,
			   AVG(sentiment_score) as avg_sentiment
		FROM `tabSurvey Response`
		WHERE campaign = %s
		GROUP BY status
	""", (campaign_name,), as_dict=True)
	
	# Get detailed response data
	completed_responses = frappe.db.sql("""
		SELECT answers, sentiment_score, response_time
		FROM `tabSurvey Response`
		WHERE campaign = %s AND status = 'Completed'
	""", (campaign_name,), as_dict=True)
	
	analytics = {
		'campaign_info': {
			'name': campaign.campaign_name,
			'type': campaign.survey_type,
			'total_sent': campaign.total_sent or 0,
			'total_responses': campaign.total_responses or 0,
			'response_rate': campaign.response_rate or 0
		},
		'response_breakdown': responses,
		'sentiment_analysis': calculate_sentiment_distribution(completed_responses),
		'response_trends': calculate_response_trends(completed_responses)
	}
	
	return analytics

def calculate_sentiment_distribution(responses):
	"""Calculate sentiment distribution from responses"""
	if not responses:
		return {'positive': 0, 'neutral': 0, 'negative': 0}
	
	positive = sum(1 for r in responses if r.get('sentiment_score', 0) > 0.3)
	negative = sum(1 for r in responses if r.get('sentiment_score', 0) < -0.3)
	neutral = len(responses) - positive - negative
	
	return {
		'positive': positive,
		'neutral': neutral,
		'negative': negative,
		'total': len(responses)
	}

def calculate_response_trends(responses):
	"""Calculate response trends over time"""
	if not responses:
		return []
	
	# Group responses by date
	from collections import defaultdict
	daily_responses = defaultdict(int)
	
	for response in responses:
		if response.get('response_time'):
			date = frappe.utils.getdate(response['response_time'])
			daily_responses[str(date)] += 1
	
	# Convert to list format
	trends = []
	for date, count in sorted(daily_responses.items()):
		trends.append({
			'date': date,
			'responses': count
		})
	
	return trends