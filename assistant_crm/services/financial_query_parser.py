# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
from datetime import datetime, timedelta
from frappe.utils import getdate, get_first_day, get_last_day, add_months


class FinancialQueryParser:
	"""Intelligent parser for natural language financial and budget queries"""
	
	def __init__(self):
		self.user = frappe.session.user
		self.query_patterns = self._initialize_query_patterns()
	
	def _initialize_query_patterns(self):
		"""Initialize regex patterns for different types of financial queries"""
		return {
			"budget_inquiry": {
				"patterns": [
					r"(?:what|show|get|find).*budget.*(?:for|of|in)\s+([^?]+)",
					r"budget.*(?:status|balance|remaining|left).*(?:for|of|in)\s+([^?]+)",
					r"(?:how much|what's).*budget.*(?:remaining|left|available).*(?:for|in)\s+([^?]+)",
					r"budget.*utilization.*(?:for|of|in)\s+([^?]+)",
					r"(?:what|show).*budgets?.*(?:do we have|available|allocated)"
				],
				"intent": "budget_inquiry"
			},
			"spending_analysis": {
				"patterns": [
					r"(?:how much|what).*(?:spent|spending|expenses?).*(?:on|for|in)\s+([^?]+)",
					r"(?:show|get|find).*(?:expenses?|spending|expenditure).*(?:for|of|in)\s+([^?]+)",
					r"actual.*(?:spending|expenses?).*(?:vs|versus|compared to).*budget",
					r"variance.*analysis.*(?:for|of|in)\s+([^?]+)"
				],
				"intent": "spending_analysis"
			},
			"budget_comparison": {
				"patterns": [
					r"budget.*vs.*actual.*(?:for|of|in)\s+([^?]+)",
					r"compare.*budget.*(?:with|to).*actual.*(?:for|of|in)\s+([^?]+)",
					r"budget.*performance.*(?:for|of|in)\s+([^?]+)",
					r"(?:over|under).*budget.*(?:for|of|in)\s+([^?]+)"
				],
				"intent": "budget_comparison"
			},
			"cost_center_query": {
				"patterns": [
					r"(?:cost center|department).*budget.*([^?]+)",
					r"budget.*(?:for|of).*(?:cost center|department)\s+([^?]+)",
					r"([^?\s]+).*(?:cost center|department).*budget"
				],
				"intent": "cost_center_query"
			},
			"project_query": {
				"patterns": [
					r"project.*budget.*([^?]+)",
					r"budget.*(?:for|of).*project\s+([^?]+)",
					r"([^?\s]+).*project.*budget"
				],
				"intent": "project_query"
			},
			"time_based_query": {
				"patterns": [
					r"budget.*(?:for|in|during)\s+(q[1-4]|quarter\s+[1-4]|[0-9]{4}|this\s+year|last\s+year|current\s+year)",
					r"(?:monthly|quarterly|yearly|annual).*budget",
					r"budget.*(?:january|february|march|april|may|june|july|august|september|october|november|december)",
					r"budget.*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
				],
				"intent": "time_based_query"
			},
			"account_query": {
				"patterns": [
					r"account.*budget.*([^?]+)",
					r"budget.*(?:for|of).*account\s+([^?]+)",
					r"([^?\s]+).*account.*budget"
				],
				"intent": "account_query"
			}
		}
	
	def parse_financial_query(self, query):
		"""Parse natural language financial query and extract intent and entities"""
		try:
			query_lower = query.lower().strip()
			
			# Extract intent and entities
			intent_result = self._extract_intent(query_lower)
			entities = self._extract_entities(query_lower)
			time_context = self._extract_time_context(query_lower)
			
			# Build structured query
			structured_query = {
				"original_query": query,
				"intent": intent_result["intent"],
				"confidence": intent_result["confidence"],
				"entities": entities,
				"time_context": time_context,
				"filters": self._build_filters(entities, time_context),
				"query_type": self._determine_query_type(intent_result["intent"], entities)
			}
			
			return structured_query
			
		except Exception as e:
			frappe.log_error(f"Error parsing financial query: {str(e)}", "Financial Query Parser")
			return {
				"original_query": query,
				"intent": "general_help",
				"confidence": 0,
				"entities": {},
				"time_context": {},
				"filters": {},
				"query_type": "general"
			}
	
	def _extract_intent(self, query):
		"""Extract intent from query using pattern matching"""
		best_match = {"intent": "general_help", "confidence": 0}
		
		for category, config in self.query_patterns.items():
			for pattern in config["patterns"]:
				match = re.search(pattern, query, re.IGNORECASE)
				if match:
					confidence = len(match.group(0)) / len(query)  # Simple confidence based on match length
					if confidence > best_match["confidence"]:
						best_match = {
							"intent": config["intent"],
							"confidence": confidence,
							"matched_pattern": pattern,
							"matched_text": match.group(0)
						}
		
		return best_match
	
	def _extract_entities(self, query):
		"""Extract entities like cost centers, projects, accounts, amounts from query"""
		entities = {
			"cost_centers": [],
			"projects": [],
			"accounts": [],
			"amounts": [],
			"departments": [],
			"companies": []
		}
		
		try:
			# Extract cost centers
			cost_center_patterns = [
				r"cost center\s+([a-zA-Z0-9\s\-_]+?)(?:\s|$|[,.])",
				r"department\s+([a-zA-Z0-9\s\-_]+?)(?:\s|$|[,.])",
				r"(?:for|in|of)\s+([a-zA-Z0-9\s\-_]+?)\s+(?:cost center|department)"
			]
			
			for pattern in cost_center_patterns:
				matches = re.findall(pattern, query, re.IGNORECASE)
				entities["cost_centers"].extend([match.strip() for match in matches])
			
			# Extract projects
			project_patterns = [
				r"project\s+([a-zA-Z0-9\s\-_]+?)(?:\s|$|[,.])",
				r"(?:for|in|of)\s+([a-zA-Z0-9\s\-_]+?)\s+project"
			]
			
			for pattern in project_patterns:
				matches = re.findall(pattern, query, re.IGNORECASE)
				entities["projects"].extend([match.strip() for match in matches])
			
			# Extract amounts
			amount_patterns = [
				r"\$([0-9,]+(?:\.[0-9]{2})?)",
				r"([0-9,]+(?:\.[0-9]{2})?)\s*(?:dollars?|usd|inr|eur)",
				r"amount.*?([0-9,]+(?:\.[0-9]{2})?)"
			]
			
			for pattern in amount_patterns:
				matches = re.findall(pattern, query, re.IGNORECASE)
				entities["amounts"].extend([match.replace(",", "") for match in matches])
			
			# Extract account names (more complex pattern)
			account_patterns = [
				r"account\s+([a-zA-Z0-9\s\-_]+?)(?:\s|$|[,.])",
				r"(?:for|in|of)\s+([a-zA-Z0-9\s\-_]+?)\s+account"
			]
			
			for pattern in account_patterns:
				matches = re.findall(pattern, query, re.IGNORECASE)
				entities["accounts"].extend([match.strip() for match in matches])
			
			# Clean up entities (remove duplicates and empty strings)
			for key in entities:
				entities[key] = list(set([item for item in entities[key] if item.strip()]))
			
			return entities
			
		except Exception as e:
			frappe.log_error(f"Error extracting entities: {str(e)}", "Financial Query Parser")
			return entities
	
	def _extract_time_context(self, query):
		"""Extract time-related context from query"""
		time_context = {
			"fiscal_year": None,
			"quarter": None,
			"month": None,
			"date_range": None,
			"relative_time": None
		}
		
		try:
			# Extract fiscal year
			fy_patterns = [
				r"(?:fy|fiscal year)\s*([0-9]{4})",
				r"([0-9]{4})\s*(?:fy|fiscal year)",
				r"year\s+([0-9]{4})"
			]
			
			for pattern in fy_patterns:
				match = re.search(pattern, query, re.IGNORECASE)
				if match:
					time_context["fiscal_year"] = match.group(1)
					break
			
			# Extract quarter
			quarter_patterns = [
				r"q([1-4])",
				r"quarter\s+([1-4])",
				r"([1-4])(?:st|nd|rd|th)\s+quarter"
			]
			
			for pattern in quarter_patterns:
				match = re.search(pattern, query, re.IGNORECASE)
				if match:
					time_context["quarter"] = int(match.group(1))
					break
			
			# Extract month
			month_patterns = [
				r"(january|february|march|april|may|june|july|august|september|october|november|december)",
				r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
			]
			
			month_mapping = {
				"jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
				"apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6,
				"jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "september": 9,
				"oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
			}
			
			for pattern in month_patterns:
				match = re.search(pattern, query, re.IGNORECASE)
				if match:
					month_name = match.group(1).lower()
					time_context["month"] = month_mapping.get(month_name)
					break
			
			# Extract relative time
			relative_patterns = [
				r"(this\s+year|current\s+year|last\s+year|previous\s+year)",
				r"(this\s+month|current\s+month|last\s+month|previous\s+month)",
				r"(this\s+quarter|current\s+quarter|last\s+quarter|previous\s+quarter)"
			]
			
			for pattern in relative_patterns:
				match = re.search(pattern, query, re.IGNORECASE)
				if match:
					time_context["relative_time"] = match.group(1).lower()
					break
			
			return time_context
			
		except Exception as e:
			frappe.log_error(f"Error extracting time context: {str(e)}", "Financial Query Parser")
			return time_context
	
	def _build_filters(self, entities, time_context):
		"""Build database filters based on extracted entities and time context"""
		filters = {}
		
		try:
			# Add entity filters
			if entities.get("cost_centers"):
				filters["cost_center"] = entities["cost_centers"][0]  # Use first match
			
			if entities.get("projects"):
				filters["project"] = entities["projects"][0]
			
			if entities.get("accounts"):
				filters["account"] = entities["accounts"][0]
			
			# Add time filters
			if time_context.get("fiscal_year"):
				filters["fiscal_year"] = time_context["fiscal_year"]
			
			# Handle relative time
			if time_context.get("relative_time"):
				relative = time_context["relative_time"]
				current_date = getdate()
				
				if "this year" in relative or "current year" in relative:
					filters["fiscal_year"] = str(current_date.year)
				elif "last year" in relative or "previous year" in relative:
					filters["fiscal_year"] = str(current_date.year - 1)
				elif "this month" in relative or "current month" in relative:
					filters["month"] = current_date.month
					filters["year"] = current_date.year
				elif "last month" in relative or "previous month" in relative:
					last_month = add_months(current_date, -1)
					filters["month"] = last_month.month
					filters["year"] = last_month.year
			
			# Handle quarter
			if time_context.get("quarter"):
				quarter = time_context["quarter"]
				current_year = getdate().year
				year = int(time_context.get("fiscal_year", current_year))
				
				quarter_months = {
					1: [4, 5, 6],    # Q1: Apr-Jun
					2: [7, 8, 9],    # Q2: Jul-Sep
					3: [10, 11, 12], # Q3: Oct-Dec
					4: [1, 2, 3]     # Q4: Jan-Mar
				}
				
				if quarter in quarter_months:
					filters["quarter"] = quarter
					filters["quarter_months"] = quarter_months[quarter]
					filters["fiscal_year"] = str(year)
			
			return filters
			
		except Exception as e:
			frappe.log_error(f"Error building filters: {str(e)}", "Financial Query Parser")
			return {}
	
	def _determine_query_type(self, intent, entities):
		"""Determine the specific type of query for processing"""
		if intent == "budget_inquiry":
			if entities.get("cost_centers"):
				return "cost_center_budget"
			elif entities.get("projects"):
				return "project_budget"
			elif entities.get("accounts"):
				return "account_budget"
			else:
				return "general_budget"
		
		elif intent == "spending_analysis":
			return "spending_analysis"
		
		elif intent == "budget_comparison":
			return "budget_vs_actual"
		
		elif intent in ["cost_center_query", "project_query", "account_query"]:
			return intent
		
		elif intent == "time_based_query":
			return "time_based_budget"
		
		else:
			return "general_financial"
	
	def validate_entities(self, entities):
		"""Validate extracted entities against actual Frappe data"""
		try:
			validated_entities = {}
			
			# Validate cost centers
			if entities.get("cost_centers"):
				for cc in entities["cost_centers"]:
					if frappe.db.exists("Cost Center", cc):
						validated_entities["cost_center"] = cc
						break
					else:
						# Try fuzzy matching
						similar_cc = frappe.db.sql("""
							SELECT name FROM `tabCost Center` 
							WHERE cost_center_name LIKE %s OR name LIKE %s
							LIMIT 1
						""", (f"%{cc}%", f"%{cc}%"))
						if similar_cc:
							validated_entities["cost_center"] = similar_cc[0][0]
							break
			
			# Validate projects
			if entities.get("projects"):
				for proj in entities["projects"]:
					if frappe.db.exists("Project", proj):
						validated_entities["project"] = proj
						break
					else:
						# Try fuzzy matching
						similar_proj = frappe.db.sql("""
							SELECT name FROM `tabProject` 
							WHERE project_name LIKE %s OR name LIKE %s
							LIMIT 1
						""", (f"%{proj}%", f"%{proj}%"))
						if similar_proj:
							validated_entities["project"] = similar_proj[0][0]
							break
			
			# Validate accounts
			if entities.get("accounts"):
				for acc in entities["accounts"]:
					if frappe.db.exists("Account", acc):
						validated_entities["account"] = acc
						break
					else:
						# Try fuzzy matching
						similar_acc = frappe.db.sql("""
							SELECT name FROM `tabAccount` 
							WHERE account_name LIKE %s OR name LIKE %s
							LIMIT 1
						""", (f"%{acc}%", f"%{acc}%"))
						if similar_acc:
							validated_entities["account"] = similar_acc[0][0]
							break
			
			return validated_entities
			
		except Exception as e:
			frappe.log_error(f"Error validating entities: {str(e)}", "Financial Query Parser")
			return {}
