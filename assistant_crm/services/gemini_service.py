# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import os
import json
import requests
import time
# Temporarily commented out to fix import issues
# from assistant_crm.assistant_crm.services.cache_service import get_cache_service
# from assistant_crm.assistant_crm.services.error_handler import get_error_handler
# from assistant_crm.assistant_crm.services.monitoring_service import get_monitoring_service

# Simple replacements for the complex services
def get_cache_service():
    """Simple cache service replacement"""
    class SimpleCacheService:
        def get_cached_response(self, message, user_context):
            return None  # No caching for now
        def _update_cache_stats(self, stat):
            pass  # No stats for now
        def cache_response(self, message, user_context, response):
            pass  # No caching for now
    return SimpleCacheService()

def get_error_handler(service_name):
    """Simple error handler replacement with execute_with_retry method"""
    class SimpleErrorHandler:
        def __init__(self):
            self.max_retries = 3

        def execute_with_retry(self, func, *args, **kwargs):
            """Execute function with simple retry logic"""
            last_exception = None

            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < self.max_retries:
                        import time
                        time.sleep(1 * (attempt + 1))  # Simple backoff
                    continue

            # If all retries failed, raise the last exception
            raise last_exception

        def get_fallback_response(self, error):
            error_message = "I apologize, but I'm experiencing technical difficulties. Please try again later."

            # Check if it's an API key error
            error_str = str(error).lower()
            if "api key" in error_str and ("invalid" in error_str or "not valid" in error_str):
                error_message = "I apologize, but there's an issue with the API configuration. Please contact support or try again later."
            elif "quota" in error_str or "limit" in error_str:
                error_message = "I apologize, but the service is temporarily at capacity. Please try again in a few minutes."

            return {
                "response": error_message,
                "success": False,
                "error": str(error),
                "context_data": {
                    "error_type": "api_error",
                    "fallback_used": True
                }
            }
    return SimpleErrorHandler()

def get_monitoring_service():
    """Simple monitoring service replacement"""
    class SimpleMonitoringService:
        def record_api_call(self, service, method, duration, status, error=None):
            pass  # No monitoring for now
    return SimpleMonitoringService()


class GeminiService:
	"""Service class for Google Gemini API integration with live data context"""

	def __init__(self):
		self.api_key = self._get_api_key()
		self.model = self._get_model()
		self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

		# Rate limiting properties
		self.last_request_time = 0
		self.min_request_interval = 1.0  # Minimum 1 second between requests
		self.max_retries = 3
		self.retry_delay = 2.0  # Initial retry delay in seconds

	def _get_api_key(self):
		"""Get Google Gemini API key from settings or fallback to .env.ai file"""
		import frappe
		try:
			# Try to get from Assistant CRM Settings first (avoid circular import)
			try:
				if frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"):
					settings = frappe.get_doc("Assistant CRM Settings", "Assistant CRM Settings")
					if settings.enabled and settings.api_key and settings.ai_provider == "Google Gemini":
						return settings.get_password("api_key") or settings.api_key
			except Exception:
				pass  # Continue to fallback methods

			# Try to get from site config
			api_key = frappe.conf.get("google_gemini_api_key")
			if api_key:
				return api_key

			# Fallback to .env.ai file
			env_file_path = os.path.join(frappe.get_site_path(), "..", "..", ".env.ai")
			if os.path.exists(env_file_path):
				with open(env_file_path, 'r') as f:
					for line in f:
						if line.startswith('google_gemini_api_key='):
							return line.split('=', 1)[1].strip()

			# Final fallback - hardcoded key for testing
			return "AIzaSyBySMvjiFkaHWopOkh6apOXT1WIvD26CMQ"

		except Exception as e:
			frappe.log_error(f"Error getting Gemini API key: {str(e)}", "Gemini Service")
			# Return hardcoded key as last resort
			return "AIzaSyBySMvjiFkaHWopOkh6apOXT1WIvD26CMQ"

	def _get_model(self):
		"""Get model name from configuration"""
		import frappe
		try:
			# Try to get from Assistant CRM Settings first
			from assistant_crm.services.settings_service import get_settings_service

			settings_service = get_settings_service()
			ai_config = settings_service.get_ai_config()

			if ai_config.get("model_name") and ai_config.get("provider") == "Google Gemini":
				return ai_config.get("model_name")

			# Try .env.ai file
			env_model = os.getenv("gemini_model")
			if env_model:
				return env_model

			# Try site config
			model = frappe.conf.get("gemini_model", "gemini-1.5-flash")
			return model

		except Exception:
			return "gemini-1.5-flash"  # Default model

	def _build_system_prompt(self, user_context=None):
		"""Build system prompt for WCFCB context with WorkCom's personality"""
		base_prompt = """I'm WorkCom, a team member at the Workers' Compensation Fund Control Board (WCFCB) of Zambia. I'm here to help you with:

1. **Claims Processing**: Workplace injury claims, medical claims, disability benefits
2. **Employer Registration**: Business registration, compliance requirements, premium payments
3. **Payment Services**: Benefit payments, pension distributions, claim settlements
4. **Reports & Analytics**: Financial reports, compliance reports, benefit statements
5. **Safety & Health**: Workplace safety guidelines, health programs, prevention measures
6. **General Support**: Account inquiries, document requests, process guidance

**My Approach:**
- I always acknowledge what you've shared with me first, using your name when I know it
- I understand that workplace injuries can be traumatic and that financial stress adds to your burden
- I ask clarifying questions to understand your specific situation before providing solutions
- I provide clear, step-by-step guidance tailored to your exact circumstances
- I match your communication style and emotional needs - if you're urgent, I respond quickly; if you're overwhelmed, I take extra time to explain
- I recognize when situations are complex and may require human expertise
- I offer relevant resources and support options specific to your situation
- I'm patient with repeated questions and never rush you through processes

**What I Can Help With:**
- Workplace injury and compensation claims
- Employer registration and compliance
- Benefit calculations and payment schedules
- Required documentation and forms
- Safety program implementation
- Appeals and dispute resolution

**Current User Context:**"""

		if user_context:
			base_prompt += f"\n- User: {user_context.get('user', 'Unknown')}"
			base_prompt += f"\n- Full Name: {user_context.get('full_name', 'Unknown')}"
			base_prompt += f"\n- Roles: {', '.join(user_context.get('roles', []))}"
			base_prompt += f"\n- Company: {user_context.get('company', 'Not specified')}"

		base_prompt += "\n\nPlease provide helpful and contextual responses based on this information."

		return base_prompt

	def _format_chat_history(self, chat_history):
		"""Format chat history for context"""
		if not chat_history:
			return ""

		formatted_history = "\n**Recent Conversation:**\n"
		for chat in chat_history[-5:]:  # Last 5 messages for context
			formatted_history += f"User: {chat.get('message', '')}\n"
			if chat.get('response'):
				formatted_history += f"Assistant: {chat.get('response', '')}\n"

		return formatted_history

	def _format_contextual_data(self, contextual_data, query_analysis):
		"""Format contextual data for inclusion in prompt"""
		if not contextual_data or "error" in contextual_data:
			return ""

		formatted_context = f"\n**Relevant Context for '{query_analysis['intent']}' query:**\n"

		# Format different types of contextual data
		if "leave_balance" in contextual_data:
			formatted_context += "**Leave Balance Information:**\n"
			for leave_type, balance in contextual_data["leave_balance"].items():
				formatted_context += f"- {leave_type}: {balance['balance']} days remaining (Allocated: {balance['allocated']}, Used: {balance['used']})\n"

		elif "material_requests" in contextual_data:
			formatted_context += f"**Recent Material Requests ({contextual_data['count']} found):**\n"
			for mr in contextual_data["material_requests"][:5]:  # Limit to 5 for context
				formatted_context += f"- {mr['name']}: {mr['status']} (Date: {mr['transaction_date']})\n"

		elif "purchase_orders" in contextual_data:
			formatted_context += f"**Recent Purchase Orders ({contextual_data['count']} found):**\n"
			for po in contextual_data["purchase_orders"][:5]:
				formatted_context += f"- {po['name']}: {po['status']} - {po['supplier']} (Amount: {po.get('grand_total', 'N/A')})\n"

		elif "purchase_receipts" in contextual_data:
			formatted_context += f"**Recent Purchase Receipts ({contextual_data['count']} found):**\n"
			for pr in contextual_data["purchase_receipts"][:5]:
				formatted_context += f"- {pr['name']}: {pr['status']} - {pr['supplier']} (Date: {pr['posting_date']})\n"

		elif "employees" in contextual_data:
			formatted_context += f"**Employee Information ({contextual_data['count']} found):**\n"
			for emp in contextual_data["employees"][:5]:
				formatted_context += f"- {emp.get('employee_name', emp.get('name'))}: {emp.get('designation', 'N/A')} in {emp.get('department', 'N/A')}\n"

		elif "pending_workflows" in contextual_data:
			formatted_context += f"**Pending Workflow Items ({contextual_data['count']} found):**\n"
			for item in contextual_data["pending_workflows"][:5]:
				formatted_context += f"- {item['doctype']} {item['name']}: {item['status']} (Owner: {item['owner']})\n"

		elif "budget_vs_actual" in contextual_data:
			budget_data = contextual_data["budget_vs_actual"]
			formatted_context += f"**Budget vs Actual Analysis:**\n"
			formatted_context += f"- Total Budget: {budget_data.get('total_budget', 0):,.2f}\n"
			formatted_context += f"- Total Actual: {budget_data.get('total_actual', 0):,.2f}\n"
			formatted_context += f"- Variance: {budget_data.get('variance', 0):,.2f}\n"
			formatted_context += f"- Utilization: {budget_data.get('utilization_percent', 0):.1f}%\n"

			if contextual_data.get("alerts"):
				formatted_context += f"**Budget Alerts ({len(contextual_data['alerts'])} found):**\n"
				for alert in contextual_data["alerts"][:3]:
					formatted_context += f"- {alert.get('type', 'Alert')}: {alert.get('message', 'No details')}\n"

		elif "financial_kpis" in contextual_data:
			kpis = contextual_data["financial_kpis"]
			formatted_context += f"**Financial KPIs:**\n"
			formatted_context += f"- Total Budget Amount: {kpis.get('total_budget_amount', 0):,.2f}\n"
			formatted_context += f"- Total Actual Spending: {kpis.get('total_actual_spending', 0):,.2f}\n"
			formatted_context += f"- Overall Utilization: {kpis.get('overall_utilization_percent', 0):.1f}%\n"
			formatted_context += f"- Budget Lines: {kpis.get('total_budget_lines', 0)}\n"

			if kpis.get("savings_achieved", 0) > 0:
				formatted_context += f"- Savings Achieved: {kpis.get('savings_achieved', 0):,.2f}\n"
			if kpis.get("overspend_amount", 0) > 0:
				formatted_context += f"- Overspend Amount: {kpis.get('overspend_amount', 0):,.2f}\n"

		elif "budgets" in contextual_data:
			formatted_context += f"**Budget Information ({contextual_data.get('summary', {}).get('total_budgets', 0)} budgets found):**\n"
			summary = contextual_data.get("summary", {})
			formatted_context += f"- Total Allocated: {summary.get('total_allocated', 0):,.2f}\n"
			formatted_context += f"- Total Actual: {summary.get('total_actual', 0):,.2f}\n"
			formatted_context += f"- Overall Utilization: {summary.get('overall_utilization', 0):.1f}%\n"
			formatted_context += f"- Total Remaining: {summary.get('total_remaining', 0):,.2f}\n"

		elif "accounts" in contextual_data:
			formatted_context += f"**Account-wise Spending ({contextual_data.get('total_accounts', 0)} accounts):**\n"
			summary = contextual_data.get("summary", {})
			formatted_context += f"- Total Budget: {summary.get('total_budget', 0):,.2f}\n"
			formatted_context += f"- Total Actual: {summary.get('total_actual', 0):,.2f}\n"
			formatted_context += f"- Total Variance: {summary.get('total_variance', 0):,.2f}\n"

			# Show top spending accounts
			accounts = contextual_data.get("accounts", [])[:3]
			if accounts:
				formatted_context += "**Top Spending Accounts:**\n"
				for acc in accounts:
					formatted_context += f"- {acc.get('account_name', 'Unknown')}: {acc.get('actual_spending', 0):,.2f}\n"

		elif "message" in contextual_data:
			formatted_context += f"**Note:** {contextual_data['message']}\n"

		return formatted_context

	def process_message(self, message, user_context=None, chat_history=None):
		"""
		Process user message with Gemini API

		Args:
			message (str): User's message
			user_context (dict): User context information
			chat_history (list): Previous chat messages

		Returns:
			dict: AI response and metadata
		"""
		import frappe
		try:
			# Check cache first
			cache_service = get_cache_service()
			cached_response = cache_service.get_cached_response(message, user_context)

			if cached_response:
				cache_service._update_cache_stats("cache_hits")
				return cached_response

			cache_service._update_cache_stats("cache_misses")
			# Import here to avoid circular imports - FIXED: Use own app's context service
			from assistant_crm.assistant_crm.services.context_service import ContextService

			# Analyze query intent and get contextual data
			context_service = ContextService()
			query_analysis = context_service.analyze_query_intent(message)
			contextual_data = context_service.get_contextual_data(
				query_analysis["intent"],
				query_analysis["entities"],
				user_context,
				message  # Pass the original query for enhanced processing
			)

			# Check if we have direct data response
			if contextual_data.get("direct_data") and contextual_data.get("formatted_response"):
				# Return the formatted response directly without AI processing
				direct_response = {
					"response": contextual_data["formatted_response"],
					"context_used": True,
					"response_mode": "direct_data",
					"raw_data": contextual_data.get("raw_data")
				}

				# Cache direct data response with longer TTL
				cache_service.cache_response(message, direct_response, user_context, ttl=7200)

				return direct_response

			# Build the prompt with contextual data
			system_prompt = self._build_system_prompt(user_context)
			history_context = self._format_chat_history(chat_history)
			context_info = self._format_contextual_data(contextual_data, query_analysis)

			# Prepare the request payload
			payload = {
				"contents": [
					{
						"parts": [
							{
								"text": f"{system_prompt}\n\n{history_context}\n\n{context_info}\n\nUser Question: {message}"
							}
						]
					}
				],
				"generationConfig": {
					"temperature": 0.7,
					"topK": 40,
					"topP": 0.95,
					"maxOutputTokens": 1024,
				},
				"safetySettings": [
					{
						"category": "HARM_CATEGORY_HARASSMENT",
						"threshold": "BLOCK_MEDIUM_AND_ABOVE"
					},
					{
						"category": "HARM_CATEGORY_HATE_SPEECH",
						"threshold": "BLOCK_MEDIUM_AND_ABOVE"
					},
					{
						"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
						"threshold": "BLOCK_MEDIUM_AND_ABOVE"
					},
					{
						"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
						"threshold": "BLOCK_MEDIUM_AND_ABOVE"
					}
				]
			}

			# Make API request with error handling and monitoring
			error_handler = get_error_handler("gemini_api")
			monitoring_service = get_monitoring_service()

			def make_api_request():
				# Implement rate limiting
				current_time = time.time()
				time_since_last_request = current_time - self.last_request_time

				if time_since_last_request < self.min_request_interval:
					sleep_time = self.min_request_interval - time_since_last_request
					time.sleep(sleep_time)

				self.last_request_time = time.time()
				start_time = time.time()
				url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
				headers = {
					"Content-Type": "application/json"
				}

				try:
					response = requests.post(url, headers=headers, json=payload, timeout=30)

					# Handle quota exceeded specifically
					if response.status_code == 429:
						raise requests.exceptions.HTTPError(f"429 Rate limit exceeded: {response.text}")

					response.raise_for_status()

					# Record successful API call
					response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
					monitoring_service.record_api_call("gemini_api", "generateContent", response_time, "success")

					return response
				except requests.exceptions.HTTPError as e:
					# Record failed API call
					response_time = (time.time() - start_time) * 1000
					status = "rate_limit" if "429" in str(e) else "error"
					monitoring_service.record_api_call("gemini_api", "generateContent", response_time, status, str(e))

					# Handle quota exceeded with specific error message
					if "429" in str(e):
						raise Exception("Google Gemini API quota exceeded. Please try again later or upgrade your API plan.")
					raise
				except Exception as e:
					# Record failed API call
					response_time = (time.time() - start_time) * 1000
					status = "rate_limit" if "429" in str(e) else "error"
					monitoring_service.record_api_call("gemini_api", "generateContent", response_time, status, str(e))
					raise

			response = error_handler.execute_with_retry(make_api_request)

			# Parse response
			response_data = response.json()

			if "candidates" in response_data and len(response_data["candidates"]) > 0:
				ai_response = response_data["candidates"][0]["content"]["parts"][0]["text"]

				response_dict = {
					"response": ai_response,
					"context_data": {
						"model": self.model,
						"user_context": user_context,
						"tokens_used": response_data.get("usageMetadata", {})
					}
				}

				# Cache successful response
				cache_service.cache_response(message, response_dict, user_context)

				return response_dict
			else:
				frappe.log_error(f"Unexpected Gemini response: {response_data}", "Gemini Service")
				return {
					"response": "I apologize, but I couldn't generate a proper response. Please try rephrasing your question.",
					"context_data": {"error": "No candidates in response"}
				}

		except requests.exceptions.RequestException as e:
			try:
				frappe.log_error(f"Gemini API error: {str(e)}", "Gemini")
			except:
				pass  # Skip logging if it fails
			error_handler = get_error_handler("gemini_api")
			return error_handler.get_fallback_response(e)

		except Exception as e:
			# Use shorter method name to avoid database column length issues
			try:
				frappe.log_error(f"Gemini error: {str(e)}", "Gemini")
			except:
				pass  # Skip logging if it fails
			error_handler = get_error_handler("gemini_api")
			return error_handler.get_fallback_response(e)

	def test_connection(self):
		"""Test Gemini API connection"""
		try:
			# Use a simple test message to minimize token usage
			test_response = self.process_message("Test")
			return {
				"success": True,
				"response": test_response.get("response", "Connection successful"),
				"model": self.model
			}
		except Exception as e:
			error_message = str(e)

			# Handle specific quota errors
			if "quota exceeded" in error_message.lower() or "429" in error_message:
				return {
					"success": False,
					"error": "API quota exceeded",
					"message": "You exceeded your current quota, please check your plan and billing details. Consider upgrading your Google Gemini API plan or try again later."
				}

			# Handle other API errors
			return {
				"success": False,
				"error": error_message,
				"message": f"Connection failed: {error_message}"
			}

	def process_wcfcb_message(self, message, system_prompt, language="en"):
		"""Process WCFCB-specific message with custom system prompt"""
		try:
			# Build the full prompt with WCFCB context
			full_prompt = f"{system_prompt}\n\nUser Message: {message}\n\nPlease respond in {self._get_language_name(language)} language."

			# Make API request
			headers = {
				"Content-Type": "application/json"
			}

			data = {
				"contents": [{
					"parts": [{
						"text": full_prompt
					}]
				}],
				"generationConfig": {
					"temperature": 0.7,
					"topK": 40,
					"topP": 0.95,
					"maxOutputTokens": 1024,
				},
				"safetySettings": [
					{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
					{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
					{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
					{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
				]
			}

			url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
			response = requests.post(url, json=data, headers=headers, timeout=30)

			if response.status_code != 200:
				import frappe
				frappe.log_error(f"Gemini API Error: {response.status_code} - {response.text}", "WCFCB Gemini Service")
				return self._get_wcfcb_fallback_response(language)

			response_data = response.json()

			if "candidates" in response_data and len(response_data["candidates"]) > 0:
				candidate = response_data["candidates"][0]
				if "content" in candidate and "parts" in candidate["content"]:
					response_text = candidate["content"]["parts"][0]["text"]
					return response_text.strip()

			return self._get_wcfcb_fallback_response(language)

		except Exception as e:
			import frappe
			frappe.log_error(f"WCFCB Gemini API Error: {str(e)}", "WCFCB Gemini Service")
			return self._get_wcfcb_fallback_response(language)

	def _get_language_name(self, language_code):
		"""Get full language name from code"""
		language_names = {"en": "English", "bem": "Bemba", "ny": "Nyanja", "to": "Tonga"}
		return language_names.get(language_code, "English")

	def generate_response_with_context(self, message: str, context: dict = None) -> str:
		"""
		Generate AI response with live data context (replaces response assembler)
		"""
		try:
			# Build enhanced prompt with live data context
			enhanced_prompt = self._build_enhanced_prompt_with_context(message, context or {})
			# Generate response using Gemini
			response = self.generate_response(enhanced_prompt)
			if response and isinstance(response, str) and response.strip():
				return response.strip()
			else:
				return self._get_fallback_response_for_intent((context or {}).get('intent', 'unknown'))
		except Exception as e:
			import frappe
			frappe.log_error(f"Gemini context response error: {str(e)}", "GeminiService Context")
			return self._get_fallback_response_for_intent((context or {}).get('intent', 'unknown'))

	def _build_enhanced_prompt_with_context(self, message: str, context: dict) -> str:
		"""Build enhanced prompt with live data context"""
		base_prompt = (
			"""You are WorkCom, a helpful and professional AI assistant for WCFCB (Workers' Compensation Fund Control Board) in Zambia.

You help with:
- Workers' compensation claims and status
- Payment information and schedules
- Pension inquiries and benefits
- Account information and updates
- Document status and requirements
- General WCFCB services and guidance

Always be warm, professional, and helpful. Keep responses concise but informative."""
		)
		# Add live data context if available
		if context.get('has_live_data') and context.get('live_data'):
			live_data = context['live_data']
			data_context = f"\n\nLIVE DATA AVAILABLE:\n{json.dumps(live_data, indent=2)}"
			base_prompt += data_context
			base_prompt += "\n\nUse this live data to provide specific, personalized information in your response."
			# Guidance for multiple-claim scenarios
			try:
				if (context.get('intent') == 'claim_status' and isinstance(live_data, dict)
					and live_data.get('type') == 'claim_data' and isinstance(live_data.get('claims'), list)
					and len(live_data.get('claims')) > 1):
					base_prompt += "\n\nWhen there are multiple claims: 1) State how many claims exist for this user; 2) List each claim briefly with claim_id, status, and current_stage; 3) Ask the user which claim they would like an update on."
			except Exception:
				pass
		# Add intent context
		if context.get('intent'):
			intent = context['intent'].replace('_', ' ')
			base_prompt += f"\n\nUser's intent: {intent}"
		# Add recent conversation history
		if context.get('conversation_history'):
			try:
				hist = context.get('conversation_history')[-6:]
				lines = []
				for h in hist:
					role = (h.get('role') or 'user').lower()
					text = h.get('text') or ''
					prefix = 'User' if role == 'user' else 'WorkCom'
					lines.append(f"{prefix}: {text}")
				if lines:
					base_prompt += "\n\nRecent conversation (most recent last):\n" + "\n".join(lines)
			except Exception:
				pass
		# Add auth context summary
		if context.get('auth_context'):
			try:
				ac = context['auth_context']
				creds = ac.get('collected_credentials') or {}
				if creds:
					base_prompt += "\n\nCollected credentials (context):"
					for k, v in creds.items():
						base_prompt += f"\n- {k}: {v}"
			except Exception:
				pass
		# Add the user's message
		base_prompt += f"\n\nUser's message: {message}"
		base_prompt += "\n\nProvide a helpful response as WorkCom from WCFCB:"
		return base_prompt

	def _get_fallback_response_for_intent(self, intent: str) -> str:
		"""Get fallback response based on intent"""
		fallback_responses = {
			'greeting': "Hi! I'm WorkCom from WCFCB. How can I help you today? 😊",
			'goodbye': "Thank you for contacting WCFCB. Have a great day!",
			'claim_status': "I can help you check your claim status. Please provide your claim number or NRC.",
			'payment_status': "I can help you check your payment information. Please provide your NRC or reference number.",
			'pension_inquiry': "I can help you with pension inquiries. Please provide your NRC for personalized information.",
			'account_info': "I can help you with your account information. Please provide your NRC.",
			'agent_request': "I'll connect you with one of our agents. Please hold on.",
			'technical_help': "I'm here to help with technical issues. What specific problem are you experiencing?",
			'unknown': "I'm WorkCom from WCFCB. I can help you with claims, payments, pensions, and more. What would you like to know?"
		}
		return fallback_responses.get(intent, fallback_responses['unknown'])

	def generate_response(self, prompt: str) -> str:
		"""Send a composed prompt to Gemini and return the model text"""
		payload = {
			"contents": [{"parts": [{"text": prompt}]}],
			"generationConfig": {"temperature": 0.7, "topK": 40, "topP": 0.95, "maxOutputTokens": 1024},
			"safetySettings": [
				{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
				{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
				{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
				{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
			]
		}
		url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
		headers = {"Content-Type": "application/json"}
		error_handler = get_error_handler("gemini_api")
		monitoring_service = get_monitoring_service()
		def make_api_request():
			current_time = time.time()
			time_since_last = current_time - self.last_request_time
			if time_since_last < self.min_request_interval:
				time.sleep(self.min_request_interval - time_since_last)
			self.last_request_time = time.time()
			start = time.time()
			resp = requests.post(url, headers=headers, json=payload, timeout=30)
			if resp.status_code == 429:
				raise requests.exceptions.HTTPError(f"429 Rate limit exceeded: {resp.text}")
			resp.raise_for_status()
			monitoring_service.record_api_call("gemini_api", "generateContent", (time.time()-start)*1000, "success")
			return resp
		try:
			response = error_handler.execute_with_retry(make_api_request)
			data = response.json()
			if "candidates" in data and data["candidates"]:
				return data["candidates"][0]["content"]["parts"][0]["text"].strip()
			return ""
		except Exception:
			return ""

	def _get_wcfcb_fallback_response(self, language="en"):
		"""Get WCFCB fallback response when AI fails"""
		fallback_responses = {
			"en": "I apologize for the technical difficulty. Please contact WCFCB directly at +260-211-123456 or email info@wcfcb.gov.zm for immediate assistance with your inquiry.",
			"bem": "Ndeelomba pantu kuli technical difficulty. Please contact WCFCB directly pa +260-211-123456 or email info@wcfcb.gov.zm ukupata immediate assistance na inquiry yenu.",
			"ny": "Pepani chifukwa cha technical difficulty. Chonde contact WCFCB directly pa +260-211-123456 or email info@wcfcb.gov.zm kuti mupeze immediate assistance ndi funso lanu.",
			"to": "Ke kopa tshwarelo ka lebaka la technical difficulty. Ka kopo contact WCFCB directly ho +260-211-123456 kapa email info@wcfcb.gov.zm ho fumana immediate assistance ka potso ya hao."
		}
		return fallback_responses.get(language, fallback_responses["en"])

def process_wcfcb_message(self, message, system_prompt, language="en"):
	"""Process WCFCB-specific message with custom system prompt"""
	try:
		# Build the full prompt with WCFCB context
		full_prompt = f"{system_prompt}\n\nUser Message: {message}\n\nPlease respond in {self._get_language_name(language)} language."

		# Make API request
		headers = {
			"Content-Type": "application/json"
		}

		data = {
			"contents": [{
				"parts": [{
					"text": full_prompt
				}]
			}],
			"generationConfig": {
				"temperature": 0.7,
				"topK": 40,
				"topP": 0.95,
				"maxOutputTokens": 1024,
			},
			"safetySettings": [
				{
					"category": "HARM_CATEGORY_HARASSMENT",
					"threshold": "BLOCK_MEDIUM_AND_ABOVE"
				},
				{
					"category": "HARM_CATEGORY_HATE_SPEECH",
					"threshold": "BLOCK_MEDIUM_AND_ABOVE"
				},
				{
					"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
					"threshold": "BLOCK_MEDIUM_AND_ABOVE"
				},
				{
					"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
					"threshold": "BLOCK_MEDIUM_AND_ABOVE"
				}
			]
		}

		url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
		response = requests.post(url, json=data, headers=headers, timeout=30)

		if response.status_code != 200:
			frappe.log_error(f"Gemini API Error: {response.status_code} - {response.text}", "WCFCB Gemini Service")
			return self._get_wcfcb_fallback_response(language)

		response_data = response.json()

		if "candidates" in response_data and len(response_data["candidates"]) > 0:
			candidate = response_data["candidates"][0]
			if "content" in candidate and "parts" in candidate["content"]:
				response_text = candidate["content"]["parts"][0]["text"]
				return response_text.strip()

		return self._get_wcfcb_fallback_response(language)

	except Exception as e:
		frappe.log_error(f"WCFCB Gemini API Error: {str(e)}", "WCFCB Gemini Service")
		return self._get_wcfcb_fallback_response(language)

def _get_language_name(self, language_code):
	"""Get full language name from code"""
	language_names = {
		"en": "English",
		"bem": "Bemba",
		"ny": "Nyanja",
		"to": "Tonga"
	}
	return language_names.get(language_code, "English")

def generate_response_with_context(self, message: str, context: dict = None) -> str:
	"""
	Generate AI response with live data context (replaces response assembler)

	Args:
		message (str): User's message
		context (dict): Context including live data, intent, etc.

	Returns:
		str: AI-generated response with live data integration
	"""
	try:
		# Build enhanced prompt with live data context
		enhanced_prompt = self._build_enhanced_prompt_with_context(message, context or {})

		# Generate response using Gemini
		response = self.generate_response(enhanced_prompt)

		if response and isinstance(response, str) and response.strip():
			return response.strip()
		else:
			return self._get_fallback_response_for_intent(context.get('intent', 'unknown'))

	except Exception as e:
		import frappe
		frappe.log_error(f"Gemini context response error: {str(e)}", "GeminiService Context")
		return self._get_fallback_response_for_intent(context.get('intent', 'unknown'))

def _build_enhanced_prompt_with_context(self, message: str, context: dict) -> str:
	"""Build enhanced prompt with live data context"""

	# Base WorkCom personality and WCFCB context
	base_prompt = """You are WorkCom, a helpful and professional AI assistant for WCFCB (Workers' Compensation Fund Control Board) in Zambia.

You help with:
- Workers' compensation claims and status
- Payment information and schedules
- Pension inquiries and benefits
- Account information and updates
- Document status and requirements
- General WCFCB services and guidance

Always be warm, professional, and helpful. Keep responses concise but informative."""

	# Add live data context if available
	if context.get('has_live_data') and context.get('live_data'):
		live_data = context['live_data']
		data_context = f"\n\nLIVE DATA AVAILABLE:\n{json.dumps(live_data, indent=2)}"
		base_prompt += data_context
		base_prompt += "\n\nUse this live data to provide specific, personalized information in your response."
		# Guidance for multiple-claim scenarios
		try:
			if (context.get('intent') == 'claim_status' and isinstance(live_data, dict)
				and live_data.get('type') == 'claim_data' and isinstance(live_data.get('claims'), list)
				and len(live_data.get('claims')) > 1):
				base_prompt += "\n\nWhen there are multiple claims: 1) State how many claims exist for this user; 2) List each claim briefly with claim_id, status, and current_stage; 3) Ask the user which claim they would like an update on."
		except Exception:
			pass

	# Add intent context
	if context.get('intent'):
		intent = context['intent'].replace('_', ' ')
		base_prompt += f"\n\nUser's intent: {intent}"

	# Add recent conversation history (helps with follow-ups)
	if context.get('conversation_history'):
		try:
			hist = context.get('conversation_history')[-6:]
			lines = []
			for h in hist:
				role = (h.get('role') or 'user').lower()
				text = h.get('text') or ''
				prefix = 'User' if role == 'user' else 'WorkCom'
				lines.append(f"{prefix}: {text}")
			if lines:
				base_prompt += "\n\nRecent conversation (most recent last):\n" + "\n".join(lines)
		except Exception:
			pass

	# Add auth context summary so the model doesn't re-ask for provided items
	if context.get('auth_context'):
		try:
			ac = context['auth_context']
			creds = ac.get('collected_credentials') or {}
			if creds:
				base_prompt += "\n\nCollected credentials (context):"
				for k, v in creds.items():
					base_prompt += f"\n- {k}: {v}"
		except Exception:
			pass

	# Add the user's message
	base_prompt += f"\n\nUser's message: {message}"
	base_prompt += "\n\nProvide a helpful response as WorkCom from WCFCB:"

	return base_prompt

def _get_fallback_response_for_intent(self, intent: str) -> str:
	"""Get fallback response based on intent"""
	fallback_responses = {
		'greeting': "Hi! I'm WorkCom from WCFCB. How can I help you today? 😊",
		'goodbye': "Thank you for contacting WCFCB. Have a great day!",
		'claim_status': "I can help you check your claim status. Please provide your claim number or NRC.",
		'payment_status': "I can help you check your payment information. Please provide your NRC or reference number.",
		'pension_inquiry': "I can help you with pension inquiries. Please provide your NRC for personalized information.",
		'account_info': "I can help you with your account information. Please provide your NRC.",
		'agent_request': "I'll connect you with one of our agents. Please hold on.",
		'technical_help': "I'm here to help with technical issues. What specific problem are you experiencing?",
		'unknown': "I'm WorkCom from WCFCB. I can help you with claims, payments, pensions, and more. What would you like to know?"
	}
	return fallback_responses.get(intent, fallback_responses['unknown'])


	def generate_response(self, prompt: str) -> str:
		"""
		Simple helper that sends a composed prompt to Gemini generateContent and
		returns the model text. Reuses request/parse logic from other methods.
		"""
		payload = {
			"contents": [{"parts": [{"text": prompt}]}],
			"generationConfig": {
				"temperature": 0.7,
				"topK": 40,
				"topP": 0.95,
				"maxOutputTokens": 1024,
			},
			"safetySettings": [
				{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
				{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
				{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
				{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			]
		}

		url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
		headers = {"Content-Type": "application/json"}

		error_handler = get_error_handler("gemini_api")
		monitoring_service = get_monitoring_service()

		def make_api_request():
			# Basic rate limiting like in process_message
			current_time = time.time()
			time_since_last = current_time - self.last_request_time
			if time_since_last < self.min_request_interval:
				time.sleep(self.min_request_interval - time_since_last)
			self.last_request_time = time.time()

			start = time.time()
			resp = requests.post(url, headers=headers, json=payload, timeout=30)
			if resp.status_code == 429:
				raise requests.exceptions.HTTPError(f"429 Rate limit exceeded: {resp.text}")
			resp.raise_for_status()
			monitoring_service.record_api_call("gemini_api", "generateContent", (time.time()-start)*1000, "success")
			return resp

		try:
			response = error_handler.execute_with_retry(make_api_request)
			data = response.json()
			if "candidates" in data and data["candidates"]:
				return data["candidates"][0]["content"]["parts"][0]["text"].strip()
			return ""
		except Exception:
			return ""

def _get_wcfcb_fallback_response(self, language="en"):
	"""Get WCFCB fallback response when AI fails"""
	fallback_responses = {
		"en": "I apologize for the technical difficulty. Please contact WCFCB directly at +260-211-123456 or email info@wcfcb.gov.zm for immediate assistance with your inquiry.",
		"bem": "Ndeelomba pantu kuli technical difficulty. Please contact WCFCB directly pa +260-211-123456 or email info@wcfcb.gov.zm ukupata immediate assistance na inquiry yenu.",
		"ny": "Pepani chifukwa cha technical difficulty. Chonde contact WCFCB directly pa +260-211-123456 or email info@wcfcb.gov.zm kuti mupeze immediate assistance ndi funso lanu.",
		"to": "Ke kopa tshwarelo ka lebaka la technical difficulty. Ka kopo contact WCFCB directly ho +260-211-123456 kapa email info@wcfcb.gov.zm ho fumana immediate assistance ka potso ya hao."
	}

	return fallback_responses.get(language, fallback_responses["en"])

