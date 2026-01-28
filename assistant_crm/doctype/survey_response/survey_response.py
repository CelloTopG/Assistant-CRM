# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

class SurveyResponse(Document):
	def before_insert(self):
		"""Ensure a unique per-response token exists on creation"""
		try:
			if not getattr(self, 'response_token', None):
				self.response_token = frappe.generate_hash(24)
		except Exception:
			pass


	def validate(self):
		"""Validate survey response"""
		self.set_response_time()
		self.analyze_sentiment()

	def set_response_time(self):
		"""Auto-populate response_time when response is completed"""
		try:
			if self.status == 'Completed' and not self.response_time:
				self.response_time = frappe.utils.now()
		except Exception:
			pass

	def analyze_sentiment(self):
		"""Analyze sentiment of text responses (always auto-calculated)"""
		if self.answers:
			try:
				answers_data = json.loads(self.answers) if isinstance(self.answers, str) else self.answers
				text_responses = []

				for answer in answers_data:
					if answer.get('type') == 'text' and answer.get('value'):
						text_responses.append(answer['value'])

				if text_responses:
					self.sentiment_score = self.calculate_sentiment_score(' '.join(text_responses))
				else:
					self.sentiment_score = None
			except:
				self.sentiment_score = None

	def calculate_sentiment_score(self, text):
		"""Calculate sentiment score from text"""
		positive_keywords = [
			'excellent', 'great', 'good', 'satisfied', 'happy', 'pleased',
			'wonderful', 'amazing', 'fantastic', 'helpful', 'professional'
		]

		negative_keywords = [
			'bad', 'poor', 'terrible', 'awful', 'horrible', 'unsatisfied',
			'unhappy', 'disappointed', 'frustrated', 'angry', 'rude'
		]

		text_lower = text.lower()

		positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
		negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)

		if positive_count > negative_count:
			return min(1.0, positive_count * 0.3)
		elif negative_count > positive_count:
			return max(-1.0, negative_count * -0.3)
		else:
			return 0.0

	def on_update(self):
		"""Update campaign statistics when response is updated"""
		if self.status == 'Completed':
			self.update_campaign_statistics()

	def update_campaign_statistics(self):
		"""Update parent campaign statistics"""
		campaign = frappe.get_doc('Survey Campaign', self.campaign)

		# Count total responses
		total_responses = frappe.db.count('Survey Response', {
			'campaign': self.campaign,
			'status': 'Completed'
		})

		# Calculate response rate
		response_rate = 0
		if campaign.total_sent and campaign.total_sent > 0:
			response_rate = (total_responses / campaign.total_sent) * 100

		# Calculate average rating (if applicable)
		avg_rating = 0
		try:
			if self.answers:
				answers_data = json.loads(self.answers) if isinstance(self.answers, str) else self.answers
				ratings = []

				for answer in answers_data:
					if answer.get('type') == 'rating' and answer.get('value'):
						ratings.append(float(answer['value']))

				if ratings:
					# Get all ratings for this campaign
					all_responses = frappe.db.sql("""
						SELECT answers
						FROM `tabSurvey Response`
						WHERE campaign = %s AND status = 'Completed'
					""", (self.campaign,), as_dict=True)

					all_ratings = []
					for resp in all_responses:
						try:
							resp_data = json.loads(resp['answers']) if isinstance(resp['answers'], str) else resp['answers']
							for ans in resp_data:
								if ans.get('type') == 'rating' and ans.get('value'):
									all_ratings.append(float(ans['value']))
						except:
							continue

					if all_ratings:
						avg_rating = sum(all_ratings) / len(all_ratings)
		except:
			pass

		# Update campaign (avoid validation on submitted doc by using db_set)
		try:
			campaign.db_set('total_responses', total_responses, update_modified=False)
			campaign.db_set('response_rate', response_rate, update_modified=False)
			campaign.db_set('average_rating', avg_rating, update_modified=False)
		except Exception:
			# Log but do not block user submission
			try:
				frappe.log_error('Failed to update campaign analytics after response submit', 'Survey Campaign Stats')
			except Exception:
				pass

@frappe.whitelist(allow_guest=True)
def submit_survey_response(token=None, answers=None, response_id=None):
	"""Submit survey response from external form (guest). Requires valid token.
	- token: per-response secret (required)
	- answers: list/dict of answers
	"""
	try:
		# Be tolerant to client variations: accept token from query/form and trim quotes/spaces
		if not token:
			token = frappe.form_dict.get('token') or frappe.form_dict.get('t')
		token = (token or '').strip().strip('"').strip("'")
		if not token:
			return {'success': False, 'message': 'Missing token'}
		row = frappe.db.get_value('Survey Response', {'response_token': token}, ['name', 'status'], as_dict=True)
		if not row:
			try:
				frappe.log_error(f"submit_survey_response: token not found: {token}", "Survey Token Lookup")
			except Exception:
				pass
			return {'success': False, 'message': 'Invalid or expired link'}
		response = frappe.get_doc('Survey Response', row.name)
		if response.status == 'Completed':
			return {'success': False, 'message': 'Survey already completed'}
		# Update response
		response.answers = json.dumps(answers) if isinstance(answers, (list, dict)) else answers
		response.status = 'Completed'
		response.response_time = frappe.utils.now()
		response.save()

		# Trigger low-score/negative-sentiment follow-up via background job (respects permissions)
		try:
			answers_data = json.loads(answers) if isinstance(answers, (str, bytes)) else (answers or [])
			# Enqueue so creation runs under a system user context (no ignore_permissions)
			frappe.enqueue(
				"assistant_crm.services.survey_service.create_follow_up_from_response",
				queue="short",
				response_name=response.name,
				answers=answers_data,
				now=False
			)
		except Exception as e:
			frappe.log_error(f"Low-score follow-up creation enqueue failed: {str(e)}", "Survey Response")

		return {'success': True, 'message': 'Thank you for your response!'}
	except Exception as e:
		frappe.log_error(f"Failed to submit survey response: {str(e)}")
		return {'success': False, 'message': 'Failed to submit response. Please try again.'}

@frappe.whitelist(allow_guest=True)
def get_survey_form(token: str = None):
	"""Return survey metadata and questions for rendering a dynamic form (guest)."""
	try:
		# Accept token from 'token' or 't' and normalize
		if not token:
			token = frappe.form_dict.get('token') or frappe.form_dict.get('t')
		token = (token or '').strip().strip('"').strip("'")
		if not token:
			return {'success': False, 'message': 'Missing token'}
		row = frappe.db.get_value('Survey Response', {'response_token': token}, ['name', 'campaign', 'status'], as_dict=True)
		if not row:
			try:
				frappe.log_error(f"get_survey_form: token not found: {token}", "Survey Token Lookup")
			except Exception:
				pass
			return {'success': False, 'message': 'Invalid or expired link'}
		if row.status == 'Completed':
			return {'success': False, 'message': 'This survey is already completed'}
		camp = frappe.get_doc('Survey Campaign', row.campaign)
		# Gate access when campaign is not active or outside the date range
		now_dt = frappe.utils.now_datetime()
		try:
			# Consider document submitted (docstatus=1) OR status in accepted open states
			accepted_statuses = ('Active', 'Submitted', 'Launched')
			status_ok = (getattr(camp, 'docstatus', 0) == 1) or (((camp.status or '').strip()) in accepted_statuses)
		except Exception:
			status_ok = True
		try:
			start_ok = True
			end_ok = True
			if getattr(camp, 'start_date', None):
				start_ok = now_dt >= frappe.utils.get_datetime(camp.start_date)
			if getattr(camp, 'end_date', None):
				end_ok = now_dt <= frappe.utils.get_datetime(camp.end_date)
		except Exception:
			start_ok = True
			end_ok = True
		if not (status_ok and start_ok and end_ok):
			return {'success': False, 'message': 'This survey is closed.'}
		# Build question list
		qs = sorted(list(camp.survey_questions or []), key=lambda q: ((q.order or 0), getattr(q, 'idx', 0)))
		questions = []
		for idx, q in enumerate(qs, start=1):
			opts = []
			if (q.question_type or '') == 'Multiple Choice' and (q.options or '').strip():
				opts = [o.strip() for o in q.options.splitlines() if o.strip()]
			questions.append({
				'index': idx,
				'question_text': q.question_text,
				'question_type': q.question_type,
				'options': opts
			})
		return {'success': True, 'campaign_label': camp.campaign_name, 'questions': questions}
	except Exception as e:
		frappe.log_error(f"get_survey_form failed: {str(e)}")
		return {'success': False, 'message': 'Failed to load survey.'}
