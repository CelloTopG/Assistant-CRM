# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
import requests
import time
from frappe import _
from frappe.utils import now, get_datetime
from assistant_crm.services.wcfcb_ai_service import WCFCBAIService
from assistant_crm.services.sentiment_analysis_service import SentimentAnalysisService
from assistant_crm.services.language_detection_service import LanguageDetectionService
from assistant_crm.services.crm_integration_service import CRMIntegrationService
from assistant_crm.services.agent_skill_matching_service import AgentSkillMatchingService


class OmnichannelRouter:
	"""Core omnichannel message routing service for WCFCB CRM"""
	
	def __init__(self):
		# Initialize services lazily to avoid circular imports and initialization errors
		self.ai_service = None
		self.sentiment_service = None
		self.language_service = None
		self.crm_service = None
		self.agent_matching_service = None

	def _get_ai_service(self):
		"""Legacy AI service accessor (now disabled).

		Historically this initialised WCFCBAIService / Gemini for omnichannel
		AI responses. That path has been fully decommissioned in favour of the
		Unified Inbox  SimplifiedChat  EnhancedAIService (Antoine / OpenAI)
		stack. We keep this method only so older code paths that call it do not
		crash; it always returns ``None`` so no AI is executed here.
		"""
		return None

	def _get_sentiment_service(self):
		"""Lazy initialization of sentiment service"""
		if self.sentiment_service is None:
			try:
				self.sentiment_service = SentimentAnalysisService()
			except Exception as e:
				frappe.log_error(f"Failed to initialize sentiment service: {str(e)}", "Omnichannel Router")
				return None
		return self.sentiment_service

	def _get_language_service(self):
		"""Lazy initialization of language service"""
		if self.language_service is None:
			try:
				self.language_service = LanguageDetectionService()
			except Exception as e:
				frappe.log_error(f"Failed to initialize language service: {str(e)}", "Omnichannel Router")
				return None
		return self.language_service

	def _get_crm_service(self):
		"""Lazy initialization of CRM service"""
		if self.crm_service is None:
			try:
				self.crm_service = CRMIntegrationService()
			except Exception as e:
				frappe.log_error(f"Failed to initialize CRM service: {str(e)}", "Omnichannel Router")
				return None
		return self.crm_service

	def _get_agent_matching_service(self):
		"""Lazy initialization of agent matching service"""
		if self.agent_matching_service is None:
			try:
				self.agent_matching_service = AgentSkillMatchingService()
			except Exception as e:
				frappe.log_error(f"Failed to initialize agent matching service: {str(e)}", "Omnichannel Router")
				return None
		return self.agent_matching_service
	
	def route_message(self, channel_type, channel_id, message_content, sender_info=None, **kwargs):
		"""Route incoming message through the omnichannel system"""
		try:
			# Simplified approach - skip CRM integration for now to avoid errors
			customer_id = None

			# Use provided timestamp if available, otherwise use current time
			received_at = kwargs.get('received_at', now())

			# Create omnichannel message record with minimal required fields
			message_doc = frappe.get_doc({
				"doctype": "Omnichannel Message",
				"channel_type": channel_type,
				"channel_id": channel_id,
				"message_content": message_content,
				"direction": "Inbound",
				"customer_id": customer_id,
				"sender_info": json.dumps(sender_info) if sender_info else None,
				"received_at": received_at,
				"status": "Received"
			})
			message_doc.insert(ignore_permissions=True)
			frappe.db.commit()

			# Process the message
			return self.process_inbound_message(message_doc.name)

		except Exception as e:
			frappe.log_error(f"Error routing message: {str(e)}", "Omnichannel Router")
			# Return a more user-friendly error
			return {
				"success": False,
				"error": "Failed to process message",
				"response": "Sorry, I encountered an error processing your message. Please try again."
			}
	
	def process_inbound_message(self, message_id):
		"""Process an inbound message"""
		try:
			message_doc = frappe.get_doc("Omnichannel Message", message_id)
			message_doc.update_status("Processing")

			# Get channel configuration
			channel_config = self.get_channel_config(message_doc.channel_type)
			if not channel_config:
				return {"success": False, "error": "Channel not configured"}

			# Simplified language detection and sentiment analysis with fallbacks
			detected_language = "en"  # Default fallback
			sentiment_analysis = {"sentiment": "neutral", "compound_score": 0}  # Default fallback

			# Try to detect language
			language_service = self._get_language_service()
			if language_service:
				try:
					detected_language = language_service.detect_language(message_doc.message_content)
				except Exception as e:
					frappe.log_error(f"Language detection failed: {str(e)}", "Omnichannel Router")

			# Try sentiment analysis
			sentiment_service = self._get_sentiment_service()
			if sentiment_service:
				try:
					sentiment_analysis = sentiment_service.analyze_sentiment(message_doc.message_content)
				except Exception as e:
					frappe.log_error(f"Sentiment analysis failed: {str(e)}", "Omnichannel Router")
			
			# Update message metadata
			metadata = {
				"detected_language": detected_language,
				"sentiment_analysis": sentiment_analysis,
				"channel_config": channel_config.name
			}
			message_doc.metadata = json.dumps(metadata)
			message_doc.save(ignore_permissions=True)

			# Skip escalation check for now to avoid complexity

			# Generate AI response
			if channel_config.auto_response_enabled:
				# Legacy AI path retired: do not call WCFCBAIService / Gemini here.
				# All new AI responses are produced via Unified Inbox 
				# SimplifiedChat  EnhancedAIService (Antoine / OpenAI).
				return {
					"success": True,
					"response": None,
					"note": "Omnichannel auto-response AI disabled; message stored for agent handling.",
				}

			# If no auto-response or AI disabled, escalate to agent
			return self.escalate_to_agent(message_doc, "Auto-response not available or disabled")

		except Exception as e:
			frappe.log_error(f"Error processing message {message_id}: {str(e)}", "Omnichannel Router")
			return {"success": False, "error": str(e)}

	def generate_ai_response(self, message_doc, language="en"):
		"""Legacy AI generator (no longer used).

		Kept for backward compatibility only; callers should not rely on this
		for real AI behaviour. It simply returns the generic fallback response
		without calling any model.
		"""
		return self._get_fallback_response(message_doc.message_content, language)

	def _get_fallback_response(self, message, language="en"):
		"""Get fallback response when AI service fails"""
		if language == "bem":
			return "Twatotela ukutumina message yenu. Tuletontonkanya na mukwai wandi."
		elif language == "ny":
			return "Tikuyamika chifukwa cha uthenga wanu. Tikuyankhulana ndi wogwira ntchito wathu."
		elif language == "to":
			return "Tulumba kuti mwatutumidde message. Tukambana a mukwetu."
		else:
			return "Thank you for your message. We are connecting you with one of our representatives who will assist you shortly."
	
	def get_wcfcb_context(self, message_content, language="en"):
		"""Get WCFCB-specific context for AI response generation"""
		context = {
			"organization": {
				"name": "Workers' Compensation Fund Control Board (WCFCB)",
				"services": [
					"Business Registration",
					"Pension Services", 
					"Employer Registration",
					"Claims Processing",
					"Compliance Monitoring"
				],
				"languages": ["English", "Bemba", "Nyanja", "Tonga"],
				"business_hours": "08:00 - 17:00 (Monday to Friday)"
			},
			"common_queries": self.get_common_queries_by_language(language),
			"escalation_triggers": [
				"complaint", "urgent", "emergency", "legal", "dispute",
				"unsatisfied", "manager", "supervisor"
			]
		}
		
		# Detect query type
		query_type = self.detect_query_type(message_content)
		if query_type:
			context["query_type"] = query_type
			context["specific_guidance"] = self.get_query_specific_guidance(query_type, language)
		
		return context
	
	def get_common_queries_by_language(self, language="en"):
		"""Get common queries and responses by language"""
		queries = {
			"en": {
				"business_registration": "For business registration, you need to provide company details, directors information, and required documents.",
				"pension_services": "Our pension services include retirement planning, benefit calculations, and claim processing.",
				"employer_registration": "Employers must register with WCFCB for workers' compensation coverage.",
				"claims_processing": "Claims are processed within 30 days of receiving complete documentation."
			},
			"bem": {
				"business_registration": "Ukufuna ukusungula business, mufwaikwa ukupeela company details, directors information, na ma documents yafwaikwa.",
				"pension_services": "Ma pension services yetu yakatila retirement planning, benefit calculations, na claim processing.",
				"employer_registration": "Ma employers bafwaikwa ukusungulwa na WCFCB ukupata workers' compensation coverage.",
				"claims_processing": "Ma claims yaprocesswa mu masiku 30 ukufuma pakupokela ma documents yonse."
			}
		}
		return queries.get(language, queries["en"])
	
	def detect_query_type(self, message_content):
		"""Detect the type of query from message content"""
		message_lower = message_content.lower()
		
		query_keywords = {
			"business_registration": ["business", "register", "company", "incorporation", "startup"],
			"pension_services": ["pension", "retirement", "benefits", "payout", "contribution"],
			"employer_registration": ["employer", "workers compensation", "coverage", "premium"],
			"claims_processing": ["claim", "compensation", "injury", "accident", "medical"],
			"compliance": ["compliance", "audit", "inspection", "violation", "penalty"]
		}
		
		for query_type, keywords in query_keywords.items():
			if any(keyword in message_lower for keyword in keywords):
				return query_type
		
		return None
	
	def get_query_specific_guidance(self, query_type, language="en"):
		"""Get specific guidance for query types"""
		guidance = {
			"en": {
				"business_registration": "To register your business with WCFCB, please visit our office with: 1) Certificate of Incorporation, 2) Directors' details, 3) Business plan, 4) Registration fee.",
				"pension_services": "For pension inquiries, please provide your member number and we'll assist with benefit statements, contribution history, or retirement planning.",
				"employer_registration": "Employers must register within 30 days of starting operations. Required documents: Business license, employee list, and premium payment.",
				"claims_processing": "To file a claim, submit: 1) Incident report, 2) Medical certificates, 3) Witness statements, 4) Employment verification."
			}
		}
		
		return guidance.get(language, guidance["en"]).get(query_type, "")
	
	def should_escalate(self, message_doc, sentiment_analysis):
		"""Determine if message should be escalated to human agent"""
		# Check sentiment score
		compound_score = sentiment_analysis.get("compound_score", 0)
		if compound_score < -0.6:  # Very negative sentiment
			return True
		
		# Check for escalation keywords
		escalation_keywords = [
			"complaint", "urgent", "emergency", "legal", "dispute",
			"unsatisfied", "manager", "supervisor", "escalate"
		]
		
		message_lower = message_doc.message_content.lower()
		if any(keyword in message_lower for keyword in escalation_keywords):
			return True
		
		# Check message complexity (length, questions)
		if len(message_doc.message_content) > 500:
			return True
		
		question_count = message_doc.message_content.count('?')
		if question_count > 3:
			return True
		
		return False
	
	def escalate_to_agent(self, message_doc, reason):
			"""Escalate message to human agent using AgentDashboard capacity model"""
			try:
				from assistant_crm.doctype.agent_dashboard.agent_dashboard import AgentDashboard

				# Use AgentDashboard to select the best available agent for the
				# Omnichannel branch. This keeps load balanced and respects
				# max_concurrent_chats and working hours.
				available_agents = AgentDashboard.get_available_agents(
					channel_type=message_doc.channel_type,
					routing_branch="Omnichannel",
				)

				assigned_agent = None
				if available_agents:
					best_agent = available_agents[0]
					result = best_agent.assign_message(message_doc.name)

					if result.get("success"):
						assigned_agent = best_agent.agent_user
						# Reload message to ensure we have the latest state after
						# assignment and update escalation metadata.
						message_doc = frappe.get_doc("Omnichannel Message", message_doc.name)
						message_doc.escalation_reason = reason
						message_doc.update_status("Escalated")

						# Notify the assigned agent in real time
						self.notify_agent(assigned_agent, message_doc)
					else:
						frappe.log_error(
							result.get("error"),
							"Omnichannel Router - Assignment Error",
						)
				else:
					# No agents available: mark as escalated with reason but
					# without a specific agent assignment.
					message_doc.escalation_reason = f"{reason} (No agents available)"
					message_doc.update_status("Escalated")

				return {
					"success": True,
					"escalated": bool(assigned_agent),
					"agent": assigned_agent,
					"reason": reason if assigned_agent else "No agents available",
				}
				
			except Exception as e:
				frappe.log_error(f"Error escalating message: {str(e)}", "Omnichannel Router")
				return {"success": False, "error": str(e)}
	
	def find_available_agent(self, channel_type):
		"""Find available agent for the channel"""
		try:
			from assistant_crm.doctype.agent_dashboard.agent_dashboard import AgentDashboard

			# Use the enhanced agent assignment system
				available_agents = AgentDashboard.get_available_agents(
					channel_type=channel_type,
					routing_branch="Omnichannel",
				)

				if available_agents:
					return available_agents[0].agent_user

			return None

		except Exception as e:
			frappe.log_error(f"Error finding available agent: {str(e)}", "Omnichannel Router")
			return None
	
	def notify_agent(self, agent, message_doc):
		"""Notify agent about escalated message"""
		frappe.publish_realtime(
			"message_escalated",
			{
				"message_id": message_doc.name,
				"channel_type": message_doc.channel_type,
				"customer_id": message_doc.customer_id,
				"message_content": message_doc.message_content[:100] + "..." if len(message_doc.message_content) > 100 else message_doc.message_content,
				"priority": message_doc.priority
			},
			user=agent
		)
	
	def send_response(self, message_doc, response_content):
		"""Send response through the appropriate channel"""
		try:
			channel_config = self.get_channel_config(message_doc.channel_type)
			if not channel_config:
				return {"success": False, "error": "Channel not configured"}
			
			if message_doc.channel_type == "WhatsApp":
				return self.send_whatsapp_message(message_doc, response_content, channel_config)
			elif message_doc.channel_type == "Facebook":
				return self.send_facebook_message(message_doc, response_content, channel_config)
			elif message_doc.channel_type == "Instagram":
				return self.send_instagram_message(message_doc, response_content, channel_config)
			elif message_doc.channel_type == "Telegram":
				return self.send_telegram_message(message_doc, response_content, channel_config)
			elif message_doc.channel_type == "Website Chat":
				return self.send_website_chat_message(message_doc, response_content)
			else:
				return {"success": False, "error": "Channel not supported for outbound messages"}
				
		except Exception as e:
			frappe.log_error(f"Error sending response: {str(e)}", "Omnichannel Router")
			return {"success": False, "error": str(e)}
	
	def send_whatsapp_message(self, message_doc, response_content, channel_config):
		"""Send WhatsApp message with real-time status tracking"""
		try:
			headers = {
				"Authorization": f"Bearer {channel_config.get_password('api_key')}",
				"Content-Type": "application/json"
			}

			data = {
				"messaging_product": "whatsapp",
				"to": message_doc.channel_id,
				"text": {"body": response_content}
			}

			api_url = f"{channel_config.api_endpoint or 'https://graph.facebook.com/v18.0'}/{channel_config.phone_number}/messages"
			response = requests.post(api_url, json=data, headers=headers, timeout=30)
			response.raise_for_status()

			whatsapp_message_id = response.json().get("messages", [{}])[0].get("id")

			# Real-time status update
			frappe.publish_realtime(
				"message_status_update",
				{
					"message_id": message_doc.name,
					"whatsapp_message_id": whatsapp_message_id,
					"status": "sent",
					"channel_type": "WhatsApp",
					"timestamp": now()
				},
				room=f"conversation_{getattr(message_doc, 'conversation_id', message_doc.name)}"
			)

			# Update omnichannel dashboard
			frappe.publish_realtime(
				"omnichannel_message",
				{
					"channel_type": "WhatsApp",
					"channel_id": message_doc.channel_id,
					"direction": "outbound",
					"content": response_content,
					"status": "sent",
					"timestamp": now(),
					"agent_id": getattr(message_doc, 'agent_assigned', None)
				},
				room="omnichannel_dashboard"
			)

			return {
				"success": True,
				"message_id": whatsapp_message_id,
				"status": "sent",
				"realtime_updated": True
			}

		except Exception as e:
			# Real-time error notification
			frappe.publish_realtime(
				"message_status_update",
				{
					"message_id": message_doc.name,
					"status": "failed",
					"error": str(e),
					"channel_type": "WhatsApp",
					"timestamp": now()
				},
				room=f"conversation_{getattr(message_doc, 'conversation_id', message_doc.name)}"
			)
			return {"success": False, "error": str(e)}

	def send_facebook_message(self, message_doc, response_content, channel_config):
		"""Send Facebook message with proper API formatting and delivery tracking"""
		try:
			# Validate response content
			if not response_content or not response_content.strip():
				return {"success": False, "error": "Empty response content"}

			# Ensure response content is within Facebook's limits (2000 characters)
			if len(response_content) > 2000:
				response_content = response_content[:1997] + "..."
				frappe.log_error(f"Facebook message truncated for user {message_doc.channel_id}", "Facebook Message Truncation")

			# Facebook Graph API endpoint
			api_url = f"https://graph.facebook.com/v18.0/me/messages"

			# Prepare message data with proper Facebook formatting
			message_data = {
				"recipient": {"id": message_doc.channel_id},
				"message": {
					"text": response_content
				},
				"messaging_type": "RESPONSE"  # Indicates this is a response to user message
			}

			# Headers for Facebook API
			headers = {
				"Content-Type": "application/json",
				"Authorization": f"Bearer {channel_config.get_password('access_token')}"
			}

			# Send message to Facebook
			start_time = time.time()
			response = requests.post(
				api_url,
				json=message_data,
				headers=headers,
				timeout=30
			)
			end_time = time.time()

			response_time = (end_time - start_time) * 1000  # Convert to milliseconds

			# Check response status
			if response.status_code == 200:
				response_json = response.json()
				facebook_message_id = response_json.get("message_id")

				# Log successful delivery
				frappe.log_error(
					f"Facebook message delivered successfully. Message ID: {facebook_message_id}, Response time: {response_time:.2f}ms",
					"Facebook Message Delivery Success"
				)

				# Real-time status update for unified inbox
				frappe.publish_realtime(
					"facebook_message_delivered",
					{
						"message_id": message_doc.name,
						"facebook_message_id": facebook_message_id,
						"status": "delivered",
						"channel_type": "Facebook",
						"timestamp": now(),
						"response_time": response_time
					},
					room=f"conversation_{getattr(message_doc, 'conversation_id', message_doc.name)}"
				)

				# Update omnichannel dashboard
				frappe.publish_realtime(
					"omnichannel_message",
					{
						"channel_type": "Facebook",
						"channel_id": message_doc.channel_id,
						"direction": "outbound",
						"content": response_content,
						"status": "delivered",
						"timestamp": now(),
						"agent_id": "Anna",
						"response_time": response_time
					},
					room="omnichannel_dashboard"
				)

				return {
					"success": True,
					"message_id": facebook_message_id,
					"status": "delivered",
					"response_time": response_time,
					"platform": "Facebook"
				}

			else:
				# Handle Facebook API errors
				error_details = response.json() if response.content else {"error": "Unknown error"}
				error_message = error_details.get("error", {}).get("message", "Facebook API error")

				frappe.log_error(
					f"Facebook API error: {response.status_code} - {error_message}. Response: {response.text}",
					"Facebook Message Delivery Error"
				)

				return {
					"success": False,
					"error": f"Facebook API error: {error_message}",
					"status_code": response.status_code,
					"platform": "Facebook"
				}

		except requests.exceptions.Timeout:
			error_msg = "Facebook API request timed out"
			frappe.log_error(error_msg, "Facebook Message Timeout")
			return {"success": False, "error": error_msg, "platform": "Facebook"}

		except requests.exceptions.ConnectionError:
			error_msg = "Failed to connect to Facebook API"
			frappe.log_error(error_msg, "Facebook Connection Error")
			return {"success": False, "error": error_msg, "platform": "Facebook"}

		except Exception as e:
			error_msg = f"Unexpected error sending Facebook message: {str(e)}"
			frappe.log_error(error_msg, "Facebook Message Error")
			return {"success": False, "error": error_msg, "platform": "Facebook"}

	def send_instagram_message(self, message_doc, response_content, channel_config):
		"""Send Instagram message"""
		# Instagram uses Facebook Graph API
		return self.send_facebook_message(message_doc, response_content, channel_config)

	def send_telegram_message(self, message_doc, response_content, channel_config):
		"""Send Telegram message"""
		try:
			api_url = f"https://api.telegram.org/bot{channel_config.get_password('api_key')}/sendMessage"

			data = {
				"chat_id": message_doc.channel_id,
				"text": response_content,
				"parse_mode": "Markdown"
			}

			response = requests.post(api_url, json=data, timeout=30)
			response.raise_for_status()

			return {"success": True, "message_id": response.json().get("result", {}).get("message_id")}

		except Exception as e:
			return {"success": False, "error": str(e)}

	def send_website_chat_message(self, message_doc, response_content):
		"""Send website chat message via real-time with enhanced features"""
		try:
			# Enhanced real-time message with metadata
			message_data = {
				"message": response_content,
				"sender": "WCFCB Assistant",
				"timestamp": now(),
				"session_id": message_doc.channel_id,
				"message_id": message_doc.name,
				"conversation_id": getattr(message_doc, 'conversation_id', None),
				"agent_name": getattr(message_doc, 'agent_assigned', None),
				"message_type": "response",
				"metadata": {
					"response_time": getattr(message_doc, 'response_time', 0),
					"ai_generated": getattr(message_doc, 'processed_by_ai', False),
					"priority": getattr(message_doc, 'priority', 'medium')
				}
			}

			# Send to specific chat room
			frappe.publish_realtime(
				"chat_message",
				message_data,
				room=f"chat_{message_doc.channel_id}"
			)

			# Also send to omnichannel monitoring
			frappe.publish_realtime(
				"omnichannel_message",
				{
					"channel_type": "Website Chat",
					"channel_id": message_doc.channel_id,
					"direction": "outbound",
					"content": response_content,
					"timestamp": now(),
					"agent_id": getattr(message_doc, 'agent_assigned', None)
				},
				room="omnichannel_dashboard"
			)

			return {"success": True, "message_id": f"web_{now()}", "realtime_sent": True}

		except Exception as e:
			frappe.log_error(f"Error sending website chat message: {str(e)}", "Omnichannel Router")
			return {"success": False, "error": str(e)}

	def get_channel_config(self, channel_type):
		"""Get channel configuration"""
		configs = frappe.get_all(
			"Channel Configuration",
			filters={"channel_type": channel_type, "enabled": 1},
			limit=1
		)

		if configs:
			return frappe.get_doc("Channel Configuration", configs[0].name)
		return None


# Utility functions for external API calls
@frappe.whitelist(allow_guest=True)
def process_inbound_message(message_id):
	"""API endpoint to process inbound message"""
	router = OmnichannelRouter()
	return router.process_inbound_message(message_id)


@frappe.whitelist()
def get_message_statistics():
	"""Get omnichannel message statistics"""
	try:
		stats = {
			"total_messages": frappe.db.count("Omnichannel Message"),
			"messages_today": frappe.db.count("Omnichannel Message", {
				"received_at": [">=", frappe.utils.today()]
			}),
			"pending_messages": frappe.db.count("Omnichannel Message", {
				"status": ["in", ["Received", "Processing"]]
			}),
			"escalated_messages": frappe.db.count("Omnichannel Message", {
				"escalated_to_agent": 1,
				"status": ["!=", "Closed"]
			}),
			"by_channel": frappe.db.sql("""
				SELECT channel_type, COUNT(*) as count
				FROM `tabOmnichannel Message`
				WHERE DATE(received_at) = CURDATE()
				GROUP BY channel_type
			""", as_dict=True),
			"response_times": frappe.db.sql("""
				SELECT AVG(response_time) as avg_response_time,
					   MIN(response_time) as min_response_time,
					   MAX(response_time) as max_response_time
				FROM `tabOmnichannel Message`
				WHERE response_time IS NOT NULL
				AND DATE(received_at) = CURDATE()
			""", as_dict=True)[0] if frappe.db.sql("""
				SELECT COUNT(*) as count
				FROM `tabOmnichannel Message`
				WHERE response_time IS NOT NULL
				AND DATE(received_at) = CURDATE()
			""", as_dict=True)[0].get("count", 0) > 0 else {}
		}

		return {"success": True, "data": stats}

	except Exception as e:
		frappe.log_error(f"Error getting message statistics: {str(e)}", "Omnichannel Router")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_agent_response(message_id, response, agent):
	"""Send agent response to customer"""
	try:
		message_doc = frappe.get_doc("Omnichannel Message", message_id)

		# Verify agent assignment
		if message_doc.agent_assigned != agent:
			return {"success": False, "error": "Message not assigned to this agent"}

		# Send response through appropriate channel
		router = OmnichannelRouter()
		send_result = router.send_response(message_doc, response)

		if send_result.get("success"):
			# Log agent response
			router.crm_service.log_interaction(
				message_doc.customer_id,
				message_doc,
				response
			)

			# Update message with agent response
			message_doc.ai_response = response
			message_doc.save()

			return {"success": True, "message": "Response sent successfully"}
		else:
			return send_result

	except Exception as e:
		frappe.log_error(f"Error sending agent response: {str(e)}", "Omnichannel Router")
		return {"success": False, "error": str(e)}

	def smart_route_conversation(self, conversation_id, message_content, customer_data=None):
		"""Smart route conversation using comprehensive AI analysis"""
		try:
			# Get comprehensive analysis
			sentiment_service = self._get_sentiment_service()
			if not sentiment_service:
				return self._fallback_routing(conversation_id)

			analysis = sentiment_service.get_comprehensive_analysis(message_content, customer_data)

			# Extract routing requirements
			routing_recommendation = analysis.get('routing_recommendation', {})
			required_skills = routing_recommendation.get('required_skills', [])
			avoid_skills = routing_recommendation.get('avoid_skills', [])
			priority_score = routing_recommendation.get('priority_score', 50)

			# Detect customer language
			language_service = self._get_language_service()
			customer_language = 'en'
			if language_service:
				lang_result = language_service.detect_language(message_content)
				customer_language = lang_result.get('language', 'en')

			# Find best agent
			agent_matching_service = self._get_agent_matching_service()
			if agent_matching_service:
				best_agent = agent_matching_service.find_best_agent(
					required_skills=required_skills,
					avoid_skills=avoid_skills,
					priority_score=priority_score,
					customer_language=customer_language
				)

				if best_agent:
					# Assign conversation to agent
					assignment_result = self._assign_conversation_to_agent(
						conversation_id, best_agent, analysis
					)

					if assignment_result.get('success'):
						# Log routing decision
						self._log_routing_decision(conversation_id, analysis, best_agent)

						return {
							'success': True,
							'routing_type': 'agent',
							'agent_id': best_agent['agent_id'],
							'agent_name': best_agent['agent_name'],
							'match_score': best_agent['match_score'],
							'estimated_response_time': best_agent['estimated_response_time'],
							'analysis': analysis,
							'message': f"Conversation routed to {best_agent['agent_name']}"
						}

			# If no agent available, check for escalation
			if routing_recommendation.get('escalation_needed'):
				escalation_result = self._escalate_conversation(conversation_id, analysis)
				if escalation_result.get('success'):
					return escalation_result

			# Fallback to AI handling
			return self._route_to_ai(conversation_id, analysis)

		except Exception as e:
			frappe.log_error(f"Error in smart routing: {str(e)}", "Omnichannel Router")
			return self._fallback_routing(conversation_id)

	def _assign_conversation_to_agent(self, conversation_id, agent_info, analysis):
		"""Assign conversation to specific agent"""
		try:
			# Update conversation assignment
			frappe.db.sql("""
				UPDATE `tabConversation`
				SET assigned_agent = %s,
					assignment_time = NOW(),
					status = 'Assigned',
					priority_score = %s,
					routing_analysis = %s
				WHERE name = %s
			""", (
				agent_info['agent_id'],
				analysis['routing_recommendation']['priority_score'],
				json.dumps(analysis),
				conversation_id
			))

			# Create assignment notification
			self._create_agent_notification(agent_info['agent_id'], conversation_id, analysis)

			frappe.db.commit()
			return {'success': True}

		except Exception as e:
			frappe.log_error(f"Error assigning conversation to agent: {str(e)}")
			return {'success': False, 'error': str(e)}

	def _escalate_conversation(self, conversation_id, analysis):
		"""Escalate conversation to supervisor or specialist"""
		try:
			# Find supervisor or specialist
			escalation_target = self._find_escalation_target(analysis)

			if escalation_target:
				# Update conversation for escalation
				frappe.db.sql("""
					UPDATE `tabConversation`
					SET status = 'Escalated',
						escalation_reason = %s,
						escalated_to = %s,
						escalation_time = NOW()
					WHERE name = %s
				""", (
					analysis['routing_recommendation'].get('escalation_reason', 'High priority'),
					escalation_target['agent_id'],
					conversation_id
				))

				# Create escalation notification
				self._create_escalation_notification(escalation_target['agent_id'], conversation_id, analysis)

				frappe.db.commit()

				return {
					'success': True,
					'routing_type': 'escalation',
					'escalated_to': escalation_target['agent_name'],
					'escalation_reason': analysis['routing_recommendation'].get('escalation_reason'),
					'message': f"Conversation escalated to {escalation_target['agent_name']}"
				}

			return {'success': False, 'error': 'No escalation target available'}

		except Exception as e:
			frappe.log_error(f"Error escalating conversation: {str(e)}")
			return {'success': False, 'error': str(e)}

	def _route_to_ai(self, conversation_id, analysis):
		"""Route conversation to AI handling"""
		try:
			# Update conversation for AI handling
			frappe.db.sql("""
				UPDATE `tabConversation`
				SET status = 'AI_Handling',
					ai_confidence = %s,
					routing_analysis = %s
				WHERE name = %s
			""", (
				analysis['sentiment']['confidence'],
				json.dumps(analysis),
				conversation_id
			))

			frappe.db.commit()

			return {
				'success': True,
				'routing_type': 'ai',
				'ai_confidence': analysis['sentiment']['confidence'],
				'message': 'Conversation routed to AI assistant'
			}

		except Exception as e:
			frappe.log_error(f"Error routing to AI: {str(e)}")
			return {'success': False, 'error': str(e)}


@frappe.whitelist()
def auto_assign_to_agent(message_id):
	"""Auto-assign message to available agent"""
	try:
		from assistant_crm.doctype.agent_dashboard.agent_dashboard import AgentDashboard
			# Use the Omnichannel routing branch so this pool stays separate
			# from Unified Inbox agents.
			return AgentDashboard.auto_assign_conversation(
				message_id,
				routing_branch="Omnichannel",
			)

	except Exception as e:
		frappe.log_error(f"Error in auto-assignment: {str(e)}", "Omnichannel Router")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def smart_route_conversation(conversation_id, message_content, customer_data=None):
	"""Smart route conversation using AI-powered analysis"""
	try:
		router = OmnichannelRouter()
		return router.smart_route_conversation(conversation_id, message_content, customer_data)
	except Exception as e:
		frappe.log_error(f"Error in smart routing: {str(e)}", "Omnichannel Router")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_routing_analytics(period='today'):
	"""Get routing analytics and performance metrics"""
	try:
		router = OmnichannelRouter()
		return router.get_routing_analytics(period)
	except Exception as e:
		frappe.log_error(f"Error getting routing analytics: {str(e)}", "Omnichannel Router")
		return {"success": False, "error": str(e)}
