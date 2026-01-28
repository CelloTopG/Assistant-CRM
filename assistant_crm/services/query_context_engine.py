# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
import json
from datetime import datetime, timedelta


class QueryContextEngine:
	"""Advanced query context engine for intent-based data retrieval"""
	
	def __init__(self):
		self.user = frappe.session.user
		self.query_patterns = self._initialize_query_patterns()
		self.response_templates = self._initialize_response_templates()
	
	def _initialize_query_patterns(self):
		"""Initialize comprehensive query patterns for different intents"""
		return {
			"employee_identification": {
				"patterns": [
					r"(?:what\s+is|show\s+me|get\s+me|find)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:'s)?\s+(?:employee\s+)?(?:id|emp\s+id|employee\s+number)",
					r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:'s)?\s+(?:employee\s+)?(?:id|emp\s+id|employee\s+number)",
					r"(?:employee\s+)?(?:id|emp\s+id)\s+(?:of|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
					r"(?:find|get|show)\s+(?:employee\s+)?(?:id|emp\s+id)\s+(?:for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
				],
				"confidence_boost": 2.5,
				"data_type": "employee",
				"query_type": "employee_id",
				"expected_response": "direct_data"
			},

			"employee_position": {
				"patterns": [
					r"(?:what\s+is|show\s+me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:'s)?\s+(?:position|role|job|title|designation)",
					r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:'s)?\s+(?:position|role|job|title|designation)",
					r"(?:position|role|job|title|designation)\s+(?:of|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
					r"(?:what\s+)?(?:position|role|job|title)\s+(?:does|is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
				],
				"confidence_boost": 2.5,
				"data_type": "employee",
				"query_type": "position",
				"expected_response": "direct_data"
			},

			"employee_department": {
				"patterns": [
					r"(?:what\s+)?(?:department|dept)\s+(?:does|is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
					r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:'s)?\s+(?:department|dept)",
					r"(?:which|what)\s+(?:department|dept)\s+(?:is|does)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
					r"(?:department|dept)\s+(?:of|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
				],
				"confidence_boost": 2.3,
				"data_type": "employee",
				"query_type": "department",
				"expected_response": "direct_data"
			},
			
			"budget_amount": {
				"patterns": [
					r"(?:what\s+is|show\s+me|how\s+much)\s+(?:the\s+)?(?:budget|allocation)\s+(?:for|of)\s+([A-Za-z\s]+)",
					r"(?:budget|allocation)\s+(?:amount|total)\s+(?:for|of)\s+([A-Za-z\s]+)",
					r"([A-Za-z\s]+)\s+(?:budget|allocation)\s+(?:amount|total)",
					r"(?:how\s+much\s+)?(?:budget|money|funds?)\s+(?:do\s+we\s+have|is\s+allocated)\s+(?:for|in)\s+([A-Za-z\s]+)"
				],
				"confidence_boost": 2.2,
				"data_type": "budget",
				"query_type": "amount",
				"expected_response": "direct_data"
			},
			
			"budget_remaining": {
				"patterns": [
					r"(?:how\s+much|what\s+is)\s+(?:budget\s+)?(?:remaining|left|balance)\s+(?:for|in)\s+([A-Za-z\s]+)",
					r"(?:remaining|left|balance)\s+(?:budget|funds?|money)\s+(?:for|in)\s+([A-Za-z\s]+)",
					r"([A-Za-z\s]+)\s+(?:remaining|left)\s+(?:budget|funds?)",
					r"(?:budget\s+)?(?:balance|remaining)\s+(?:for|of)\s+([A-Za-z\s]+)"
				],
				"confidence_boost": 2.0,
				"data_type": "budget",
				"query_type": "remaining",
				"expected_response": "direct_data"
			},
			
			"budget_utilization": {
				"patterns": [
					r"(?:budget\s+)?(?:utilization|usage|spent)\s+(?:for|of|in)\s+([A-Za-z\s]+)",
					r"(?:how\s+much\s+)?(?:spent|used)\s+(?:from|of)\s+([A-Za-z\s]+)\s+(?:budget|allocation)",
					r"([A-Za-z\s]+)\s+(?:budget\s+)?(?:utilization|usage|spending)",
					r"(?:percentage|percent)\s+(?:used|spent|utilized)\s+(?:for|of)\s+([A-Za-z\s]+)"
				],
				"confidence_boost": 1.8,
				"data_type": "budget",
				"query_type": "utilization",
				"expected_response": "direct_data"
			},
			
			"project_status": {
				"patterns": [
					r"(?:what\s+is|show\s+me)\s+(?:the\s+)?(?:status|progress)\s+(?:of|for)\s+(?:project\s+)?([A-Za-z0-9\s\-_]+)",
					r"(?:project\s+)?([A-Za-z0-9\s\-_]+)\s+(?:status|progress)",
					r"(?:status|progress)\s+(?:of|for)\s+(?:project\s+)?([A-Za-z0-9\s\-_]+)",
					r"(?:how\s+is)\s+(?:project\s+)?([A-Za-z0-9\s\-_]+)\s+(?:going|progressing)"
				],
				"confidence_boost": 1.9,
				"data_type": "project",
				"query_type": "status",
				"expected_response": "direct_data"
			},
			
			"general_help": {
				"patterns": [
					r"(?:how\s+do\s+i|how\s+can\s+i|where\s+do\s+i)\s+(?:find|get|access|see)",
					r"(?:show\s+me\s+how|teach\s+me|guide\s+me)\s+(?:to|how\s+to)",
					r"(?:steps|instructions|tutorial)\s+(?:to|for|on)",
					r"(?:where\s+is|where\s+can\s+i\s+find)\s+(?:the\s+)?"
				],
				"confidence_boost": 1.0,
				"data_type": "general",
				"query_type": "instructions",
				"expected_response": "instructions"
			}
		}
	
	def _initialize_response_templates(self):
		"""Initialize response templates for different query types"""
		return {
			"employee_id": {
				"direct_data": "**{employee_name}**'s Employee ID is: **{employee_id}**",
				"not_found": "I couldn't find an employee named '{query_entity}'. Please check the spelling or try a different name.",
				"no_permission": "I don't have permission to access employee ID information."
			},
			
			"position": {
				"direct_data": "**{employee_name}** holds the position of **{designation}** in the **{department}** department.",
				"not_found": "I couldn't find position information for '{query_entity}'.",
				"no_permission": "I don't have permission to access employee position information."
			},
			
			"department": {
				"direct_data": "**{employee_name}** works in the **{department}** department{branch_info}.",
				"not_found": "I couldn't find department information for '{query_entity}'.",
				"no_permission": "I don't have permission to access employee department information."
			},
			
			"budget_amount": {
				"direct_data": "**{entity_name}** has a total budget allocation of **${budget_amount:,.2f}** for {fiscal_year}.",
				"not_found": "I couldn't find budget information for '{query_entity}'.",
				"no_permission": "I don't have permission to access budget information."
			},
			
			"budget_remaining": {
				"direct_data": "**{entity_name}** has **${remaining_amount:,.2f}** remaining from a total budget of **${total_budget:,.2f}** ({remaining_percentage:.1f}% remaining).",
				"not_found": "I couldn't find remaining budget information for '{query_entity}'.",
				"no_permission": "I don't have permission to access budget information."
			},
			
			"budget_utilization": {
				"direct_data": "**{entity_name}** has utilized **{utilization_percentage:.1f}%** of its budget (**${spent_amount:,.2f}** out of **${total_budget:,.2f}**).",
				"not_found": "I couldn't find budget utilization information for '{query_entity}'.",
				"no_permission": "I don't have permission to access budget information."
			},
			
			"project_status": {
				"direct_data": "**{project_name}** is currently **{status}** with **{progress}%** completion.",
				"not_found": "I couldn't find status information for project '{query_entity}'.",
				"no_permission": "I don't have permission to access project information."
			}
		}
	
	def analyze_query_context(self, query):
		"""Analyze query and provide comprehensive context for data retrieval"""
		try:
			query_lower = query.lower().strip()
			
			# Find matching patterns
			matches = []
			for intent, config in self.query_patterns.items():
				for pattern in config["patterns"]:
					match = re.search(pattern, query_lower, re.IGNORECASE)
					if match:
						entity = match.group(1).strip() if match.groups() else None
						confidence = len(match.group(0)) / len(query) * config["confidence_boost"]
						
						matches.append({
							"intent": intent,
							"pattern": pattern,
							"entity": entity,
							"confidence": confidence,
							"data_type": config["data_type"],
							"query_type": config["query_type"],
							"expected_response": config["expected_response"],
							"matched_text": match.group(0)
						})
			
			# Sort by confidence and return best match
			if matches:
				best_match = max(matches, key=lambda x: x["confidence"])

				# Clean and validate the extracted entity
				cleaned_entity = self._clean_and_validate_entity(best_match["entity"], best_match["data_type"])

				return {
					"intent": best_match["intent"],
					"entity": cleaned_entity,
					"confidence": best_match["confidence"],
					"data_type": best_match["data_type"],
					"query_type": best_match["query_type"],
					"expected_response": best_match["expected_response"],
					"context": self._build_query_context(best_match, query),
					"all_matches": matches
				}
			
			# Default fallback
			return {
				"intent": "general_help",
				"entity": None,
				"confidence": 0.3,
				"data_type": "general",
				"query_type": "instructions",
				"expected_response": "instructions",
				"context": {"message": "I can help you find information. What specific data are you looking for?"}
			}
			
		except Exception as e:
			frappe.log_error(f"Error analyzing query context: {str(e)}", "Query Context Engine")
			return self._get_error_context()

	def _clean_and_validate_entity(self, entity, data_type):
		"""Clean and validate extracted entity names"""
		if not entity:
			return None

		# Remove common stop words and clean the entity
		stop_words = ["work", "in", "does", "is", "the", "a", "an", "and", "or", "but", "for", "of", "at", "by"]

		# Split entity into words and filter
		words = entity.strip().split()
		cleaned_words = []

		for word in words:
			word_clean = word.strip(".,!?;:")
			if word_clean.lower() not in stop_words and len(word_clean) > 1:
				# Capitalize first letter of each word for names
				if data_type == "employee":
					cleaned_words.append(word_clean.capitalize())
				else:
					cleaned_words.append(word_clean)

		if not cleaned_words:
			return None

		cleaned_entity = " ".join(cleaned_words)

		# Additional validation for employee names
		if data_type == "employee":
			# Ensure we have at least first and last name for employees
			if len(cleaned_words) < 2:
				return None

			# Validate name pattern (letters and spaces only)
			import re
			if not re.match(r'^[A-Za-z\s]+$', cleaned_entity):
				return None

		return cleaned_entity

	def _build_query_context(self, match, original_query):
		"""Build comprehensive context for the matched query"""
		context = {
			"original_query": original_query,
			"matched_intent": match["intent"],
			"extracted_entity": match["entity"],
			"confidence_score": match["confidence"],
			"data_retrieval_strategy": self._get_retrieval_strategy(match),
			"response_template": self.response_templates.get(match["query_type"], {}),
			"fallback_instructions": self._get_fallback_instructions(match["data_type"])
		}
		
		# Add specific context based on data type
		if match["data_type"] == "employee":
			context.update(self._get_employee_context(match["entity"]))
		elif match["data_type"] == "budget":
			context.update(self._get_budget_context(match["entity"]))
		elif match["data_type"] == "project":
			context.update(self._get_project_context(match["entity"]))
		
		return context
	
	def _get_retrieval_strategy(self, match):
		"""Get data retrieval strategy based on match"""
		strategies = {
			"employee": {
				"primary_doctype": "Employee",
				"search_fields": ["employee_name", "name"],
				"return_fields": ["name", "employee_name", "designation", "department", "branch", "status"],
				"permission_required": "Employee:read"
			},
			"budget": {
				"primary_doctype": "Budget",
				"search_fields": ["cost_center", "project"],
				"return_fields": ["name", "cost_center", "fiscal_year", "project"],
				"permission_required": "Budget:read"
			},
			"project": {
				"primary_doctype": "Project",
				"search_fields": ["project_name", "name"],
				"return_fields": ["name", "project_name", "status", "percent_complete"],
				"permission_required": "Project:read"
			}
		}
		
		return strategies.get(match["data_type"], {})
	
	def _get_employee_context(self, entity):
		"""Get employee-specific context"""
		return {
			"search_entity": entity,
			"entity_type": "employee",
			"common_variations": self._get_name_variations(entity) if entity else [],
			"search_tips": [
				"Try using the full name",
				"Check for common nicknames",
				"Verify spelling"
			]
		}
	
	def _get_budget_context(self, entity):
		"""Get budget-specific context"""
		return {
			"search_entity": entity,
			"entity_type": "budget",
			"possible_matches": [
				f"{entity} Department" if entity else "",
				f"{entity} Cost Center" if entity else "",
				f"Project {entity}" if entity else ""
			],
			"search_tips": [
				"Try using the full department name",
				"Check cost center names",
				"Look for project names"
			]
		}
	
	def _get_project_context(self, entity):
		"""Get project-specific context"""
		return {
			"search_entity": entity,
			"entity_type": "project",
			"search_tips": [
				"Try using the full project name",
				"Check project codes",
				"Look for similar project names"
			]
		}
	
	def _get_name_variations(self, name):
		"""Generate common name variations"""
		if not name:
			return []
		
		variations = [name]
		
		# Add variations with different cases
		variations.extend([
			name.title(),
			name.upper(),
			name.lower()
		])
		
		# Add variations with common name patterns
		name_parts = name.split()
		if len(name_parts) > 1:
			# First name only
			variations.append(name_parts[0])
			# Last name only
			variations.append(name_parts[-1])
			# First + Last (skip middle names)
			if len(name_parts) > 2:
				variations.append(f"{name_parts[0]} {name_parts[-1]}")
		
		return list(set(variations))
	
	def _get_fallback_instructions(self, data_type):
		"""Get fallback instructions for different data types"""
		instructions = {
			"employee": [
				"Go to the HR module",
				"Click on Employee List",
				"Use the search function to find the employee",
				"Click on the employee name to view details"
			],
			"budget": [
				"Go to the Accounting module",
				"Click on Budget under Budget and Cost Center",
				"Use filters to find the specific budget",
				"Click on the budget to view details"
			],
			"project": [
				"Go to the Projects module",
				"Click on Project List",
				"Search for the project name",
				"Click on the project to view status"
			],
			"general": [
				"Use the global search bar at the top",
				"Navigate to the relevant module",
				"Check your permissions with the system administrator"
			]
		}
		
		return instructions.get(data_type, instructions["general"])
	
	def _get_error_context(self):
		"""Get error context when analysis fails"""
		return {
			"intent": "error",
			"entity": None,
			"confidence": 0.0,
			"data_type": "general",
			"query_type": "error",
			"expected_response": "error",
			"context": {
				"message": "I had trouble understanding your query. Could you please rephrase it?",
				"suggestions": [
					"Be more specific about what information you need",
					"Include the full name or identifier",
					"Try using different keywords"
				]
			}
		}
	
	def get_suggested_queries(self, data_type=None):
		"""Get suggested queries for testing"""
		suggestions = {
			"employee": [
				"What is John Smith's employee ID?",
				"Show me Sarah Johnson's position",
				"What department does Mike Davis work in?",
				"Find employee ID for Lisa Wilson"
			],
			"budget": [
				"What is the budget amount for IT department?",
				"How much budget is remaining for Marketing?",
				"Show me HR budget utilization",
				"Budget allocation for Operations department"
			],
			"project": [
				"What is the status of Project Alpha?",
				"Show me progress of Website Redesign project",
				"Project Beta completion percentage",
				"How is the Mobile App project going?"
			],
			"general": [
				"How do I find employee information?",
				"Where can I check budget data?",
				"Show me how to access project status",
				"Guide me to the HR module"
			]
		}
		
		if data_type:
			return suggestions.get(data_type, [])
		
		# Return all suggestions
		all_suggestions = []
		for category, queries in suggestions.items():
			all_suggestions.extend(queries)
		
		return all_suggestions
