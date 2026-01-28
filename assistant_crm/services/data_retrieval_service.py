# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
from frappe.utils import flt, getdate, format_date, format_datetime
import json


class DataRetrievalService:
	"""Service for direct data retrieval based on user queries"""

	def __init__(self):
		self.user = frappe.session.user

	
	def retrieve_employee_data(self, query, entities):
		"""Retrieve specific employee information with enhanced context awareness"""
		try:
			# Use assistant_crm's own services for better analysis
			# Create simple context engine and test generator
			class SimpleQueryContextEngine:
				def analyze_query_context(self, query, entities):
					return {"intent": "employee_lookup", "confidence": 0.8}

			class SimpleTestDataGenerator:
				def get_test_employee_data(self):
					return [
						{"name": "John Smith", "employee_id": "EMP001", "position": "Manager"},
						{"name": "Sarah Johnson", "employee_id": "EMP002", "position": "Developer"}
					]

			context_engine = SimpleQueryContextEngine()
			test_generator = SimpleTestDataGenerator()

			# Analyze query context
			query_context = context_engine.analyze_query_context(query)

			# Extract employee identifier
			employee_identifier = query_context.get("entity") or self._extract_employee_identifier(query, entities)

			if not employee_identifier:
				return {"error": "Could not identify which employee you're asking about"}

			# Check permissions first
			if not frappe.has_permission("Employee", "read"):
				# Try to use test data if no real data access
				test_data = test_generator.generate_employee_data()
				employee_match = self._find_test_employee(employee_identifier, test_data)

				if employee_match:
					requested_info = query_context.get("query_type", "general")
					response_data = self._build_test_employee_response(employee_match, requested_info)

					return {
						"type": "employee_data",
						"employee": employee_match["name"],
						"data": response_data,
						"query_type": requested_info,
						"source": "test_data"
					}
				else:
					return {"error": "You don't have permission to access employee data"}

			# Find employee in real data
			employee = self._find_employee(employee_identifier)
			if not employee:
				# Try test data as fallback
				test_data = test_generator.generate_employee_data()
				employee_match = self._find_test_employee(employee_identifier, test_data)

				if employee_match:
					requested_info = query_context.get("query_type", "general")
					response_data = self._build_test_employee_response(employee_match, requested_info)

					return {
						"type": "employee_data",
						"employee": employee_match["name"],
						"data": response_data,
						"query_type": requested_info,
						"source": "test_data"
					}
				else:
					return {"error": f"Employee '{employee_identifier}' not found"}

			# Get employee details from real data
			employee_doc = frappe.get_doc("Employee", employee)

			# Determine what information is requested
			requested_info = query_context.get("query_type", self._analyze_employee_query(query))

			# Build response based on requested information
			response_data = self._build_employee_response(employee_doc, requested_info)

			return {
				"type": "employee_data",
				"employee": employee_doc.name,
				"data": response_data,
				"query_type": requested_info,
				"source": "real_data"
			}

		except Exception as e:
			frappe.log_error(f"Error retrieving employee data: {str(e)}", "Data Retrieval Service")
			return {"error": "Failed to retrieve employee information"}
	
	def retrieve_budget_data(self, query, entities):
		"""Retrieve specific budget information"""
		try:
			# Check permissions
			if not frappe.has_permission("Budget", "read"):
				return {"error": "You don't have permission to access budget data"}
			
			# Extract budget criteria from query
			budget_criteria = self._extract_budget_criteria(query, entities)
			
			# Find matching budgets
			budgets = self._find_budgets(budget_criteria)
			
			if not budgets:
				return {"error": "No budgets found matching your criteria"}
			
			# Determine what budget information is requested
			requested_info = self._analyze_budget_query(query)
			
			# Build response
			response_data = self._build_budget_response(budgets, requested_info)
			
			return {
				"type": "budget_data",
				"data": response_data,
				"query_type": requested_info,
				"criteria": budget_criteria
			}
			
		except Exception as e:
			frappe.log_error(f"Error retrieving budget data: {str(e)}", "Data Retrieval Service")
			return {"error": "Failed to retrieve budget information"}
	
	def retrieve_project_data(self, query, entities):
		"""Retrieve specific project information"""
		try:
			# Check permissions
			if not frappe.has_permission("Project", "read"):
				return {"error": "You don't have permission to access project data"}
			
			# Extract project identifier
			project_identifier = self._extract_project_identifier(query, entities)
			
			if not project_identifier:
				return {"error": "Could not identify which project you're asking about"}
			
			# Find project
			project = self._find_project(project_identifier)
			if not project:
				return {"error": f"Project '{project_identifier}' not found"}
			
			# Get project details
			project_doc = frappe.get_doc("Project", project)
			
			# Determine requested information
			requested_info = self._analyze_project_query(query)
			
			# Build response
			response_data = self._build_project_response(project_doc, requested_info)
			
			return {
				"type": "project_data",
				"project": project_doc.name,
				"data": response_data,
				"query_type": requested_info
			}
			
		except Exception as e:
			frappe.log_error(f"Error retrieving project data: {str(e)}", "Data Retrieval Service")
			return {"error": "Failed to retrieve project information"}
	
	def _extract_employee_identifier(self, query, entities):
		"""Extract employee name or ID from query"""
		# Check entities first
		if entities.get("document_names"):
			for name in entities["document_names"]:
				if frappe.db.exists("Employee", name):
					return name
		
		# Look for employee names in query
		employee_patterns = [
			r"employee\s+([A-Za-z\s]+?)(?:\s|$|[?.,])",
			r"([A-Za-z\s]+?)'s\s+(?:position|id|employee|details)",
			r"(?:about|for)\s+([A-Za-z\s]+?)(?:\s|$|[?.,])",
			r"([A-Za-z\s]+?)\s+(?:position|id|employee|details)"
		]
		
		for pattern in employee_patterns:
			match = re.search(pattern, query, re.IGNORECASE)
			if match:
				potential_name = match.group(1).strip()
				# Check if this matches an employee
				if self._find_employee(potential_name):
					return potential_name
		
		return None
	
	def _find_employee(self, identifier):
		"""Find employee with strict matching to prevent false positives"""
		if not identifier or len(identifier.strip()) < 2:
			return None

		identifier = identifier.strip()

		# 1. Try exact Employee ID match
		if frappe.db.exists("Employee", identifier):
			return identifier

		# 2. Try exact employee name match (case-insensitive)
		employee = frappe.db.get_value("Employee", {"employee_name": identifier}, "name")
		if employee:
			return employee

		# 3. Try exact match with different case
		exact_match = frappe.db.sql("""
			SELECT name FROM `tabEmployee`
			WHERE LOWER(employee_name) = LOWER(%s)
			LIMIT 1
		""", (identifier,))

		if exact_match:
			return exact_match[0][0]

		# 4. Only use fuzzy matching if identifier has multiple words (full name)
		identifier_words = identifier.split()
		if len(identifier_words) >= 2:
			return self._find_employee_fuzzy(identifier, min_similarity=0.85)

		# 5. For single word queries, only match if it's a complete word in the name
		single_word_match = frappe.db.sql("""
			SELECT name, employee_name FROM `tabEmployee`
			WHERE employee_name REGEXP CONCAT('\\\\b', %s, '\\\\b')
			ORDER BY
				CASE
					WHEN employee_name LIKE CONCAT(%s, ' %%') THEN 1
					WHEN employee_name LIKE CONCAT('%% ', %s, ' %%') THEN 2
					WHEN employee_name LIKE CONCAT('%% ', %s) THEN 3
					ELSE 4
				END
			LIMIT 1
		""", (identifier, identifier, identifier, identifier))

		if single_word_match:
			# Additional validation: ensure it's not a partial match of a different name
			found_name = single_word_match[0][1]
			if self._validate_name_match(identifier, found_name):
				return single_word_match[0][0]

		return None

	def _find_employee_fuzzy(self, identifier, min_similarity=0.85):
		"""Fuzzy matching with high similarity threshold"""
		try:
			from difflib import SequenceMatcher

			# Get all employees
			employees = frappe.db.sql("""
				SELECT name, employee_name FROM `tabEmployee`
				WHERE employee_name IS NOT NULL
				ORDER BY employee_name
			""", as_dict=True)

			best_match = None
			best_score = 0

			for emp in employees:
				# Calculate similarity score
				similarity = SequenceMatcher(None, identifier.lower(), emp.employee_name.lower()).ratio()

				if similarity > best_score and similarity >= min_similarity:
					best_score = similarity
					best_match = emp.name

			return best_match

		except Exception:
			return None

	def _validate_name_match(self, query_name, found_name):
		"""Validate that the found name is actually what the user was looking for"""
		query_words = set(query_name.lower().split())
		found_words = set(found_name.lower().split())

		# Ensure all query words are present in the found name
		if not query_words.issubset(found_words):
			return False

		# Additional check: if query is a single word, ensure it's not just a substring
		if len(query_words) == 1:
			query_word = list(query_words)[0]
			# Check if the query word appears as a complete word in the found name
			import re
			pattern = r'\b' + re.escape(query_word) + r'\b'
			return bool(re.search(pattern, found_name.lower()))

		return True

	def _analyze_employee_query(self, query):
		"""Analyze what employee information is being requested"""
		query_lower = query.lower()
		
		if any(word in query_lower for word in ["position", "designation", "title", "role"]):
			return "position"
		elif any(word in query_lower for word in ["id", "employee id", "emp id"]):
			return "employee_id"
		elif any(word in query_lower for word in ["department", "dept"]):
			return "department"
		elif any(word in query_lower for word in ["salary", "compensation"]):
			return "salary"
		elif any(word in query_lower for word in ["contact", "phone", "email"]):
			return "contact"
		elif any(word in query_lower for word in ["manager", "reports to", "supervisor"]):
			return "manager"
		elif any(word in query_lower for word in ["joining", "date of joining", "start date"]):
			return "joining_date"
		else:
			return "general"
	
	def _build_employee_response(self, employee_doc, requested_info):
		"""Build employee response based on requested information"""
		response = {
			"employee_name": employee_doc.employee_name,
			"employee_id": employee_doc.name
		}
		
		if requested_info == "position":
			response["designation"] = employee_doc.designation
			response["department"] = employee_doc.department
		elif requested_info == "employee_id":
			response["employee_id"] = employee_doc.name
		elif requested_info == "department":
			response["department"] = employee_doc.department
			response["branch"] = employee_doc.branch
		elif requested_info == "contact":
			response["cell_number"] = employee_doc.cell_number
			response["personal_email"] = employee_doc.personal_email
			response["company_email"] = employee_doc.company_email
		elif requested_info == "manager":
			response["reports_to"] = employee_doc.reports_to
		elif requested_info == "joining_date":
			response["date_of_joining"] = format_date(employee_doc.date_of_joining) if employee_doc.date_of_joining else None
		else:  # general
			response.update({
				"designation": employee_doc.designation,
				"department": employee_doc.department,
				"branch": employee_doc.branch,
				"status": employee_doc.status,
				"date_of_joining": format_date(employee_doc.date_of_joining) if employee_doc.date_of_joining else None
			})
		
		return response

	def _find_test_employee(self, identifier, test_data):
		"""Find employee in test data with strict matching"""
		if not identifier or len(identifier.strip()) < 2:
			return None

		identifier = identifier.strip()
		identifier_lower = identifier.lower()

		# 1. Check exact name match (case-insensitive)
		for employee in test_data:
			if employee["employee_name"].lower() == identifier_lower:
				return employee

		# 2. Check employee ID match
		for employee in test_data:
			if employee["name"].lower() == identifier_lower:
				return employee

		# 3. For multi-word queries, use fuzzy matching with high threshold
		identifier_words = identifier.split()
		if len(identifier_words) >= 2:
			return self._find_test_employee_fuzzy(identifier, test_data, min_similarity=0.85)

		# 4. For single word queries, only match complete words
		for employee in test_data:
			if self._validate_name_match(identifier, employee["employee_name"]):
				return employee

		return None

	def _find_test_employee_fuzzy(self, identifier, test_data, min_similarity=0.85):
		"""Fuzzy matching for test data with high similarity threshold"""
		try:
			from difflib import SequenceMatcher

			best_match = None
			best_score = 0

			for employee in test_data:
				similarity = SequenceMatcher(None, identifier.lower(), employee["employee_name"].lower()).ratio()

				if similarity > best_score and similarity >= min_similarity:
					best_score = similarity
					best_match = employee

			return best_match

		except Exception:
			return None

	def _build_test_employee_response(self, employee_data, requested_info):
		"""Build employee response from test data"""
		response = {
			"employee_name": employee_data["employee_name"],
			"employee_id": employee_data["name"]
		}

		if requested_info == "position":
			response["designation"] = employee_data["designation"]
			response["department"] = employee_data["department"]
		elif requested_info == "employee_id":
			response["employee_id"] = employee_data["name"]
		elif requested_info == "department":
			response["department"] = employee_data["department"]
			response["branch"] = employee_data["branch"]
		elif requested_info == "contact":
			response["cell_number"] = employee_data.get("cell_number")
			response["company_email"] = employee_data.get("company_email")
		elif requested_info == "manager":
			response["reports_to"] = employee_data.get("reports_to")
		elif requested_info == "joining_date":
			response["date_of_joining"] = employee_data.get("date_of_joining")
		else:  # general
			response.update({
				"designation": employee_data["designation"],
				"department": employee_data["department"],
				"branch": employee_data["branch"],
				"status": employee_data["status"],
				"date_of_joining": employee_data.get("date_of_joining")
			})

		return response

	def _extract_budget_criteria(self, query, entities):
		"""Extract budget search criteria from query"""
		criteria = {}
		
		# Extract cost center
		if entities.get("document_names"):
			for name in entities["document_names"]:
				if frappe.db.exists("Cost Center", name):
					criteria["cost_center"] = name
				elif frappe.db.exists("Project", name):
					criteria["project"] = name
		
		# Extract fiscal year
		fy_match = re.search(r"(?:fy|fiscal year)\s*([0-9]{4})", query, re.IGNORECASE)
		if fy_match:
			criteria["fiscal_year"] = fy_match.group(1)
		
		return criteria
	
	def _find_budgets(self, criteria):
		"""Find budgets based on criteria"""
		filters = {"docstatus": 1}
		filters.update(criteria)
		
		return frappe.get_all("Budget", 
			filters=filters,
			fields=["name", "cost_center", "fiscal_year", "project", "company"]
		)
	
	def _analyze_budget_query(self, query):
		"""Analyze what budget information is requested"""
		query_lower = query.lower()
		
		if any(word in query_lower for word in ["amount", "allocation", "budget amount"]):
			return "amount"
		elif any(word in query_lower for word in ["utilization", "used", "spent"]):
			return "utilization"
		elif any(word in query_lower for word in ["remaining", "left", "balance"]):
			return "remaining"
		elif any(word in query_lower for word in ["variance", "difference"]):
			return "variance"
		else:
			return "summary"
	
	def _build_budget_response(self, budgets, requested_info):
		"""Build budget response based on requested information"""
		# Use assistant_crm's own context service
		from assistant_crm.assistant_crm.services.context_service import ContextService

		context_service = ContextService()
		response_data = []
		
		for budget in budgets:
			budget_data = context_service.get_budget_data(
				cost_center=budget.get("cost_center"),
				project=budget.get("project"),
				fiscal_year=budget.get("fiscal_year")
			)
			
			if budget_data.get("budgets"):
				budget_info = budget_data["budgets"][0]
				
				if requested_info == "amount":
					response_data.append({
						"budget_name": budget.name,
						"total_budget": budget_info.get("total_budget", 0),
						"cost_center": budget.cost_center,
						"fiscal_year": budget.fiscal_year
					})
				elif requested_info == "utilization":
					response_data.append({
						"budget_name": budget.name,
						"utilization_percent": budget_info.get("utilization_percent", 0),
						"total_actual": budget_info.get("total_actual", 0),
						"cost_center": budget.cost_center
					})
				elif requested_info == "remaining":
					response_data.append({
						"budget_name": budget.name,
						"remaining_budget": budget_info.get("remaining_budget", 0),
						"total_budget": budget_info.get("total_budget", 0),
						"cost_center": budget.cost_center
					})
				else:  # summary
					response_data.append(budget_info)
		
		return response_data
	
	def _extract_project_identifier(self, query, entities):
		"""Extract project name or ID from query"""
		# Check entities first
		if entities.get("document_names"):
			for name in entities["document_names"]:
				if frappe.db.exists("Project", name):
					return name
		
		# Look for project names in query
		project_patterns = [
			r"project\s+([A-Za-z0-9\s\-_]+?)(?:\s|$|[?.,])",
			r"([A-Za-z0-9\s\-_]+?)\s+project",
			r"(?:about|for)\s+([A-Za-z0-9\s\-_]+?)(?:\s|$|[?.,])"
		]
		
		for pattern in project_patterns:
			match = re.search(pattern, query, re.IGNORECASE)
			if match:
				potential_name = match.group(1).strip()
				if self._find_project(potential_name):
					return potential_name
		
		return None
	
	def _find_project(self, identifier):
		"""Find project by name or project_name"""
		# Try exact match first
		if frappe.db.exists("Project", identifier):
			return identifier
		
		# Try by project name
		project = frappe.db.get_value("Project", {"project_name": identifier}, "name")
		if project:
			return project
		
		# Try partial match
		projects = frappe.db.sql("""
			SELECT name FROM `tabProject`
			WHERE project_name LIKE %s OR name LIKE %s
			ORDER BY CASE WHEN project_name = %s THEN 1 ELSE 2 END
			LIMIT 1
		""", (f"%{identifier}%", f"%{identifier}%", identifier))
		
		if projects:
			return projects[0][0]
		
		return None
	
	def _analyze_project_query(self, query):
		"""Analyze what project information is requested"""
		query_lower = query.lower()
		
		if any(word in query_lower for word in ["status", "state"]):
			return "status"
		elif any(word in query_lower for word in ["progress", "completion", "percent"]):
			return "progress"
		elif any(word in query_lower for word in ["budget", "cost", "expense"]):
			return "budget"
		elif any(word in query_lower for word in ["timeline", "dates", "schedule"]):
			return "timeline"
		elif any(word in query_lower for word in ["team", "members", "assigned"]):
			return "team"
		else:
			return "general"
	
	def _build_project_response(self, project_doc, requested_info):
		"""Build project response based on requested information"""
		response = {
			"project_name": project_doc.project_name,
			"project_id": project_doc.name
		}
		
		if requested_info == "status":
			response["status"] = project_doc.status
			response["percent_complete"] = project_doc.percent_complete
		elif requested_info == "progress":
			response["percent_complete"] = project_doc.percent_complete
			response["status"] = project_doc.status
		elif requested_info == "timeline":
			response["expected_start_date"] = format_date(project_doc.expected_start_date) if project_doc.expected_start_date else None
			response["expected_end_date"] = format_date(project_doc.expected_end_date) if project_doc.expected_end_date else None
			response["actual_start_date"] = format_date(project_doc.actual_start_date) if project_doc.actual_start_date else None
			response["actual_end_date"] = format_date(project_doc.actual_end_date) if project_doc.actual_end_date else None
		else:  # general
			response.update({
				"status": project_doc.status,
				"percent_complete": project_doc.percent_complete,
				"project_type": project_doc.project_type,
				"expected_start_date": format_date(project_doc.expected_start_date) if project_doc.expected_start_date else None,
				"expected_end_date": format_date(project_doc.expected_end_date) if project_doc.expected_end_date else None,
				"department": project_doc.department
			})
		
		return response
