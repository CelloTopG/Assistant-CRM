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
		# Step 1: Force Survey Tokenization (CRITICAL)
		if not token:
			token = frappe.form_dict.get('token') or frappe.form_dict.get('t')
		token = (token or '').strip().strip('"').strip("'")
		
		if not token:
			return {'success': False, 'message': 'Missing access token'}

		# Validate Survey Access Token
		access_token = frappe.db.get_value('Survey Access Token', {'token': token}, ['name', 'is_locked', 'expires_on', 'survey_response'], as_dict=True)
		
		if not access_token:
			# Fallback to legacy response_token for existing links (temporary)
			row = frappe.db.get_value('Survey Response', {'response_token': token}, ['name', 'status'], as_dict=True)
			if not row:
				return {'success': False, 'message': 'Invalid or expired link'}
			response_name = row.name
		else:
			if access_token.is_locked:
				return {'success': False, 'message': 'This link has been locked due to suspicious activity.'}
			
			if access_token.expires_on and frappe.utils.get_datetime(access_token.expires_on) < frappe.utils.now_datetime():
				return {'success': False, 'message': 'This survey link has expired.'}
			
			response_name = access_token.survey_response

		response = frappe.get_doc('Survey Response', response_name)
		if response.status == 'Completed':
			return {'success': False, 'message': 'This survey has been completed. Thank you for your interest.', 'survey_closed': True}
		if response.status == 'Closed':
			return {'success': False, 'message': 'This survey has been closed and is no longer accepting responses.', 'survey_closed': True}
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
		# Step 1 & 5: Force Tokenization and Prevent Pre-Login Viewing
		if not token:
			token = frappe.form_dict.get('token') or frappe.form_dict.get('t')
		token = (token or '').strip().strip('"').strip("'")
		
		if not token:
			return {'success': False, 'message': 'Access denied: Valid token required.'}

		# Validate Survey Access Token
		access_token_data = frappe.db.get_value('Survey Access Token', {'token': token}, '*', as_dict=True)
		
		if not access_token_data:
			# Fallback to legacy response_token
			row = frappe.db.get_value('Survey Response', {'response_token': token}, ['name', 'campaign', 'status'], as_dict=True)
			if not row:
				return {'success': False, 'message': 'Invalid survey token.'}
			response_name = row.name
			campaign_name = row.campaign
			status = row.status
			watermark_id = "LEGACY"
			email = row.get('recipient_email')
		else:
			if access_token_data.is_locked:
				return {'success': False, 'message': 'Access revoked: Token locked.'}
			
			if access_token_data.expires_on and frappe.utils.get_datetime(access_token_data.expires_on) < frappe.utils.now_datetime():
				return {'success': False, 'message': 'Access expired: This link has timed out.'}
			
			if access_token_data.max_views > 0 and access_token_data.views_count >= access_token_data.max_views:
				return {'success': False, 'message': 'Access limit reached: This survey can no longer be viewed.'}

			response_name = access_token_data.survey_response
			campaign_name = access_token_data.survey
			status = frappe.db.get_value('Survey Response', response_name, 'status')
			watermark_id = access_token_data.watermark_id
			email = access_token_data.email
			
			# Step 1 & 7: Log Activity and Increment Views
			frappe.db.set_value('Survey Access Token', access_token_data.name, {
				'views_count': access_token_data.views_count + 1,
				'last_ip': frappe.local.request_ip,
				'user_agent': frappe.get_request_header('User-Agent'),
				'last_viewed_at': frappe.utils.now()
			}, update_modified=False)
			frappe.db.commit()

		if status == 'Completed':
			return {'success': False, 'message': 'This survey has been completed. Thank you!', 'survey_closed': True}
		if status == 'Closed':
			return {'success': False, 'message': 'This survey is no longer accepting responses.', 'survey_closed': True}
		
		camp = frappe.get_doc('Survey Campaign', campaign_name)
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
		# Step 2: Build Watermark Data
		watermark = {
			"email": email or "Confidential",
			"ip": frappe.local.request_ip,
			"timestamp": frappe.utils.now(),
			"token_id": watermark_id
		}

		return {'success': True, 'campaign_label': camp.campaign_name, 'questions': questions, 'watermark': watermark}
	except Exception as e:
		frappe.log_error(f"get_survey_form failed: {str(e)}")
		return {'success': False, 'message': 'Failed to load survey.'}
