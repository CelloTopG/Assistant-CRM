# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, get_datetime


class ContextService:
	"""Service class for gathering user and system context with persona-specific enhancements"""

	def __init__(self):
		self.user = frappe.session.user
		self.persona_cache = {}
		self.preference_cache = {}
	
	def get_user_context(self):
		"""Get comprehensive user context for AI responses"""
		try:
			user_doc = frappe.get_doc("User", self.user)
			
			# Get user roles
			roles = frappe.get_roles(self.user)
			
			# Get user's default company
			default_company = frappe.defaults.get_user_default("Company")
			
			# Get user's employee record if exists
			employee_info = self._get_employee_info()
			
			# Get user's recent activity context
			recent_activity = self._get_recent_activity()
			
			# Enhanced context for live data integration
			context = {
				"user": self.user,
				"user_id": self.user,  # Required for live data integration
				"full_name": user_doc.full_name or user_doc.first_name,
				"email": user_doc.email,
				"roles": roles,
				"company": default_company,
				"employee_info": employee_info,
				"recent_activity": recent_activity,
				"system_info": self._get_system_info(),
				# Live data integration fields for testing
				"employer_code": "EMP-2024-001",  # Default test employer
				"beneficiary_id": "BEN-2024-0001",  # Default test beneficiary
				"user_role": self._determine_user_role(roles),
				"user_type": self._determine_user_type(roles)
			}
			
			return context
			
		except Exception as e:
			frappe.log_error(f"Error getting user context: {str(e)}", "Context Service")
			return {
				"user": self.user,
				"user_id": self.user,
				"full_name": "Unknown",
				"roles": [],
				"company": None,
				"employer_code": "EMP-2024-001",
				"beneficiary_id": "BEN-2024-0001",
				"user_role": "beneficiary",
				"user_type": "beneficiary",
				"error": "Failed to load user context"
			}

	def _determine_user_role(self, roles):
		"""Determine user role for live data integration"""
		if "Employer" in roles or "HR Manager" in roles:
			return "employer"
		elif "Beneficiary" in roles or "Employee" in roles:
			return "beneficiary"
		elif "Supplier" in roles or "Vendor" in roles:
			return "supplier"
		elif "WCFCB Staff" in roles or "System Manager" in roles:
			return "wcfcb_staff"
		else:
			return "beneficiary"  # Default to beneficiary for testing

	def _determine_user_type(self, roles):
		"""Determine user type for live data integration"""
		return self._determine_user_role(roles)  # Same logic for now
	
	def _get_employee_info(self):
		"""Get employee information if user is linked to an employee"""
		try:
			employee = frappe.db.get_value("Employee", {"user_id": self.user}, 
				["name", "employee_name", "department", "designation", "company"], as_dict=True)
			
			if employee:
				return {
					"employee_id": employee.name,
					"employee_name": employee.employee_name,
					"department": employee.department,
					"designation": employee.designation,
					"company": employee.company
				}
			
			return None
			
		except Exception:
			return None
	
	def _get_recent_activity(self):
		"""Get user's recent activity for context"""
		try:
			# Get recent documents created/modified by user
			recent_docs = frappe.db.sql("""
				SELECT doctype, name, modified
				FROM (
					SELECT 'Material Request' as doctype, name, modified
					FROM `tabMaterial Request`
					WHERE owner = %s
					UNION ALL
					SELECT 'Purchase Order' as doctype, name, modified
					FROM `tabPurchase Order`
					WHERE owner = %s
					UNION ALL
					SELECT 'Leave Application' as doctype, name, modified
					FROM `tabLeave Application`
					WHERE owner = %s
				) as combined
				ORDER BY modified DESC
				LIMIT 5
			""", (self.user, self.user, self.user), as_dict=True)
			
			return recent_docs
			
		except Exception:
			return []
	
	def _get_system_info(self):
		"""Get relevant system information"""
		try:
			return {
				"site": frappe.local.site,
				"installed_apps": frappe.get_installed_apps(),
				"system_settings": {
					"country": frappe.db.get_single_value("System Settings", "country"),
					"time_zone": frappe.db.get_single_value("System Settings", "time_zone")
				}
			}
		except Exception:
			return {}
	
	def get_doctype_context(self, doctype, name=None):
		"""Get context about a specific doctype or document"""
		try:
			if not frappe.has_permission(doctype, "read"):
				return {"error": "No permission to access this document type"}
			
			context = {
				"doctype": doctype,
				"permissions": {
					"read": frappe.has_permission(doctype, "read"),
					"write": frappe.has_permission(doctype, "write"),
					"create": frappe.has_permission(doctype, "create"),
					"delete": frappe.has_permission(doctype, "delete")
				}
			}
			
			# Get doctype meta information
			meta = frappe.get_meta(doctype)
			context["doctype_info"] = {
				"module": meta.module,
				"is_submittable": meta.is_submittable,
				"has_workflow": bool(frappe.get_all("Workflow", {"document_type": doctype}))
			}
			
			# If specific document requested
			if name:
				if frappe.has_permission(doctype, "read", name):
					doc = frappe.get_doc(doctype, name)
					context["document"] = {
						"name": doc.name,
						"status": getattr(doc, "status", None),
						"docstatus": doc.docstatus,
						"owner": doc.owner,
						"modified": doc.modified
					}
				else:
					context["document"] = {"error": "No permission to access this document"}
			
			return context
			
		except Exception as e:
			frappe.log_error(f"Error getting doctype context: {str(e)}", "Context Service")
			return {"error": "Failed to get document context"}
	
	def search_documents(self, query, doctypes=None, limit=10):
		"""Search for documents based on query"""
		try:
			if not doctypes:
				doctypes = ["Material Request", "Purchase Order", "Purchase Receipt", 
						   "Leave Application", "Employee", "Item"]
			
			results = []
			
			for doctype in doctypes:
				if not frappe.has_permission(doctype, "read"):
					continue
				
				try:
					# Simple search in name and title fields
					docs = frappe.get_all(
						doctype,
						filters=[
							["name", "like", f"%{query}%"]
						],
						fields=["name", "modified", "owner"],
						limit=limit//len(doctypes) + 1
					)
					
					for doc in docs:
						results.append({
							"doctype": doctype,
							"name": doc.name,
							"modified": doc.modified,
							"owner": doc.owner
						})
						
				except Exception:
					continue
			
			return results[:limit]
			
		except Exception as e:
			frappe.log_error(f"Error searching documents: {str(e)}", "Context Service")
			return []
	
	def get_workflow_info(self, doctype, name=None):
		"""Get workflow information for a doctype or document"""
		try:
			workflows = frappe.get_all("Workflow",
				{"document_type": doctype},
				["name", "workflow_name", "workflow_state_field"]
			)

			if not workflows:
				return {"has_workflow": False}

			workflow = workflows[0]
			workflow_info = {
				"has_workflow": True,
				"workflow_name": workflow.workflow_name,
				"state_field": workflow.workflow_state_field
			}

			# Get workflow states
			states = frappe.get_all("Workflow State",
				{"parent": workflow.name},
				["state", "allow_edit", "is_optional_state"]
			)
			workflow_info["states"] = states

			# If specific document, get current state
			if name and frappe.has_permission(doctype, "read", name):
				doc = frappe.get_doc(doctype, name)
				current_state = getattr(doc, workflow.workflow_state_field, None)
				workflow_info["current_state"] = current_state

			return workflow_info

		except Exception as e:
			frappe.log_error(f"Error getting workflow info: {str(e)}", "Context Service")
			return {"error": "Failed to get workflow information"}

	def analyze_query_intent(self, query):
		"""Analyze user query to determine intent and extract relevant information"""
		query_lower = query.lower()

		# Define intent patterns
		intents = {
			"leave_balance": ["leave balance", "remaining leaves", "leave left", "vacation days"],
			"material_request": ["material request", "purchase request", "item request", "requisition"],
			"purchase_order": ["purchase order", "po", "buying", "procurement"],
			"purchase_receipt": ["purchase receipt", "goods receipt", "delivery", "received items"],
			"employee_info": ["employee", "staff", "colleague", "team member"],
			"workflow_status": ["status", "approval", "workflow", "pending", "approved", "rejected"],
			"budget_inquiry": ["budget", "budget balance", "budget remaining", "budget left", "budget available", "budget allocation", "budget status"],
			"spending_analysis": ["spending", "expenses", "expenditure", "actual spending", "money spent", "costs"],
			"budget_comparison": ["budget vs actual", "budget variance", "budget performance", "over budget", "under budget"],
			"financial_kpis": ["financial kpis", "budget kpis", "financial metrics", "budget metrics", "financial performance"],
			"reports": ["report", "analytics", "dashboard", "summary"],
			"navigation": ["how to", "where is", "find", "navigate", "access"],
			"general_help": ["help", "assist", "support", "guide"]
		}

		detected_intent = "general_help"  # default
		confidence = 0

		for intent, keywords in intents.items():
			matches = sum(1 for keyword in keywords if keyword in query_lower)
			if matches > confidence:
				confidence = matches
				detected_intent = intent

		# Extract entities (document names, numbers, etc.)
		entities = self._extract_entities(query)

		return {
			"intent": detected_intent,
			"confidence": confidence,
			"entities": entities,
			"original_query": query
		}

	def _extract_entities(self, query):
		"""Extract entities like document names, numbers from query"""
		import re

		entities = {
			"document_names": [],
			"numbers": [],
			"dates": [],
			"users": []
		}

		# Extract document-like patterns (e.g., MR-2024-00001)
		doc_pattern = r'\b[A-Z]{2,4}-\d{4}-\d{5}\b'
		entities["document_names"] = re.findall(doc_pattern, query)

		# Extract numbers
		number_pattern = r'\b\d+\b'
		entities["numbers"] = re.findall(number_pattern, query)

		# Extract potential user mentions (@username or "user name")
		user_pattern = r'@(\w+)|"([^"]+)"'
		user_matches = re.findall(user_pattern, query)
		entities["users"] = [match[0] or match[1] for match in user_matches]

		return entities

	def get_contextual_data(self, intent, entities, user_context, query=""):
		"""Get relevant data based on query intent and entities with enhanced direct data retrieval"""
		try:
			# Check if user wants direct data instead of instructions
			# Use assistant_crm's own services instead of exn_assistant
			from assistant_crm.assistant_crm.services.data_retrieval_service import DataRetrievalService

			# Create simple mode detector and formatter classes
			class SimpleResponseModeDetector:
				def should_provide_direct_data(self, query, intent):
					return intent in ["employee_lookup", "financial_data", "budget_info"]

			class SimpleMarkdownFormatter:
				def format_data_response(self, data, query_type):
					return {"formatted_data": data, "type": query_type}

			mode_detector = SimpleResponseModeDetector()
			data_retrieval = DataRetrievalService()
			formatter = SimpleMarkdownFormatter()

			# Detect response mode and check for user overrides
			mode_result = mode_detector.detect_response_mode(query) if query else {"mode": "instructions"}
			should_provide_direct_data = mode_detector.should_provide_direct_data(query) if query else False

			# Check for explicit user preference override
			user_override = mode_result.get("override_detected", False)
			if user_override == "force_data":
				should_provide_direct_data = True
			elif user_override == "force_instructions":
				should_provide_direct_data = False

			# Handle direct data requests
			if should_provide_direct_data:
				if intent == "employee_info":
					employee_data = data_retrieval.retrieve_employee_data(query, entities)
					if "error" not in employee_data:
						mode_result = mode_detector.detect_response_mode(query)
						query_type = employee_data.get("query_type", mode_result.get("data_type", "general"))
						formatted_response = formatter.format_employee_data(employee_data, query_type)

						# Add source information if using test data
						if employee_data.get("source") == "test_data":
							formatted_response += "\n\n*Note: This is sample data for demonstration purposes.*"

						return {
							"direct_data": True,
							"formatted_response": formatted_response,
							"raw_data": employee_data,
							"response_mode": "direct_data",
							"data_source": employee_data.get("source", "real_data")
						}

				elif intent in ["budget_inquiry", "spending_analysis", "budget_comparison"]:
					budget_data = data_retrieval.retrieve_budget_data(query, entities)
					if "error" not in budget_data:
						mode_result = mode_detector.detect_response_mode(query)
						query_type = budget_data.get("query_type", "summary")
						formatted_response = formatter.format_budget_data(budget_data, query_type)
						return {
							"direct_data": True,
							"formatted_response": formatted_response,
							"raw_data": budget_data,
							"response_mode": "direct_data"
						}

			# Fall back to traditional contextual data retrieval
			if intent == "leave_balance":
				return self._get_leave_balance_data(user_context)
			elif intent == "material_request":
				return self._get_material_request_data(entities, user_context)
			elif intent == "purchase_order":
				return self._get_purchase_order_data(entities, user_context)
			elif intent == "purchase_receipt":
				return self._get_purchase_receipt_data(entities, user_context)
			elif intent == "employee_info":
				return self._get_employee_data(entities, user_context)
			elif intent == "workflow_status":
				return self._get_workflow_status_data(entities, user_context)
			elif intent == "budget_inquiry":
				return self._get_budget_inquiry_data(entities, user_context)
			elif intent == "spending_analysis":
				return self._get_spending_analysis_data(entities, user_context)
			elif intent == "budget_comparison":
				return self._get_budget_comparison_data(entities, user_context)
			elif intent == "financial_kpis":
				return self._get_financial_kpis_data(entities, user_context)
			else:
				return {"message": "I can help you with various Frappe/ERPNext tasks including budget analysis, financial data, and business processes. What would you like to know?"}

		except Exception as e:
			frappe.log_error(f"Error getting contextual data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve relevant data"}

	def _get_leave_balance_data(self, user_context):
		"""Get leave balance information for the user"""
		try:
			if not user_context.get("employee_info"):
				return {"message": "You don't appear to be linked to an employee record. Please contact HR to set up your employee profile."}

			employee = user_context["employee_info"]["employee_id"]

			# Get leave allocations
			leave_allocations = frappe.get_all("Leave Allocation",
				filters={"employee": employee, "docstatus": 1},
				fields=["leave_type", "total_leaves_allocated", "new_leaves_allocated", "from_date", "to_date"],
				order_by="from_date desc"
			)

			# Get leave applications
			leave_applications = frappe.get_all("Leave Application",
				filters={"employee": employee, "docstatus": 1},
				fields=["leave_type", "total_leave_days", "from_date", "to_date"],
				order_by="from_date desc"
			)

			# Calculate balances
			leave_balance = {}
			for allocation in leave_allocations:
				leave_type = allocation.leave_type
				if leave_type not in leave_balance:
					leave_balance[leave_type] = {
						"allocated": 0,
						"used": 0,
						"balance": 0
					}
				leave_balance[leave_type]["allocated"] += allocation.total_leaves_allocated or 0

			for application in leave_applications:
				leave_type = application.leave_type
				if leave_type in leave_balance:
					leave_balance[leave_type]["used"] += application.total_leave_days or 0

			# Calculate final balances
			for leave_type in leave_balance:
				leave_balance[leave_type]["balance"] = (
					leave_balance[leave_type]["allocated"] - leave_balance[leave_type]["used"]
				)

			return {
				"leave_balance": leave_balance,
				"employee_name": user_context["employee_info"]["employee_name"]
			}

		except Exception as e:
			frappe.log_error(f"Error getting leave balance: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve leave balance information"}

	def _get_material_request_data(self, entities, user_context):
		"""Get material request data"""
		try:
			filters = {"docstatus": ["!=", 2]}  # Not cancelled

			# If specific document names mentioned
			if entities.get("document_names"):
				filters["name"] = ["in", entities["document_names"]]
			else:
				# Get recent material requests for user
				filters["owner"] = self.user

			material_requests = frappe.get_all("Material Request",
				filters=filters,
				fields=["name", "transaction_date", "status", "material_request_type", "total_qty"],
				order_by="creation desc",
				limit=10
			)

			return {
				"material_requests": material_requests,
				"count": len(material_requests)
			}

		except Exception as e:
			frappe.log_error(f"Error getting material request data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve material request information"}

	def _get_purchase_order_data(self, entities, user_context):
		"""Get purchase order data"""
		try:
			filters = {"docstatus": ["!=", 2]}

			if entities.get("document_names"):
				filters["name"] = ["in", entities["document_names"]]
			else:
				filters["owner"] = self.user

			purchase_orders = frappe.get_all("Purchase Order",
				filters=filters,
				fields=["name", "transaction_date", "status", "supplier", "grand_total"],
				order_by="creation desc",
				limit=10
			)

			return {
				"purchase_orders": purchase_orders,
				"count": len(purchase_orders)
			}

		except Exception as e:
			frappe.log_error(f"Error getting purchase order data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve purchase order information"}

	def _get_purchase_receipt_data(self, entities, user_context):
		"""Get purchase receipt data"""
		try:
			filters = {"docstatus": ["!=", 2]}

			if entities.get("document_names"):
				filters["name"] = ["in", entities["document_names"]]
			else:
				filters["owner"] = self.user

			purchase_receipts = frappe.get_all("Purchase Receipt",
				filters=filters,
				fields=["name", "posting_date", "status", "supplier", "grand_total"],
				order_by="creation desc",
				limit=10
			)

			return {
				"purchase_receipts": purchase_receipts,
				"count": len(purchase_receipts)
			}

		except Exception as e:
			frappe.log_error(f"Error getting purchase receipt data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve purchase receipt information"}

	def _get_employee_data(self, entities, user_context):
		"""Get employee information"""
		try:
			if entities.get("users"):
				# Search for specific employees
				employee_filters = []
				for user_query in entities["users"]:
					employee_filters.append(["employee_name", "like", f"%{user_query}%"])

				employees = frappe.get_all("Employee",
					filters=employee_filters,
					fields=["name", "employee_name", "department", "designation", "company"],
					limit=10
				)
			else:
				# Return current user's employee info
				if user_context.get("employee_info"):
					employees = [user_context["employee_info"]]
				else:
					return {"message": "No employee information found"}

			return {
				"employees": employees,
				"count": len(employees)
			}

		except Exception as e:
			frappe.log_error(f"Error getting employee data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve employee information"}

	def _get_workflow_status_data(self, entities, user_context):
		"""Get workflow status information"""
		try:
			# Get documents with pending workflows for the user
			pending_docs = []

			# Check common doctypes with workflows
			workflow_doctypes = ["Material Request", "Purchase Order", "Leave Application"]

			for doctype in workflow_doctypes:
				if not frappe.has_permission(doctype, "read"):
					continue

				try:
					# Get documents where user is in workflow
					docs = frappe.get_all(doctype,
						filters={"docstatus": 0},  # Draft documents
						fields=["name", "status", "owner", "modified"],
						limit=5
					)

					for doc in docs:
						pending_docs.append({
							"doctype": doctype,
							"name": doc.name,
							"status": doc.status,
							"owner": doc.owner,
							"modified": doc.modified
						})
				except Exception:
					continue

			return {
				"pending_workflows": pending_docs,
				"count": len(pending_docs)
			}

		except Exception as e:
			frappe.log_error(f"Error getting workflow status: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve workflow status information"}

	def get_budget_data(self, filters=None, cost_center=None, project=None, fiscal_year=None):
		"""Get comprehensive budget data with real-time analysis"""
		try:
			if not frappe.has_permission("Budget", "read"):
				return {"error": "No permission to access budget data"}

			# Build dynamic filters
			budget_filters = {"docstatus": 1}  # Only submitted budgets
			if cost_center:
				budget_filters["cost_center"] = cost_center
			if fiscal_year:
				budget_filters["fiscal_year"] = fiscal_year

			# Get budget records
			budgets = frappe.get_all("Budget",
				filters=budget_filters,
				fields=["name", "cost_center", "fiscal_year", "budget_against", "project", "company"],
				order_by="creation desc"
			)

			budget_analysis = []
			total_allocated = 0
			total_actual = 0

			for budget in budgets:
				# Get budget accounts for this budget
				budget_accounts = frappe.get_all("Budget Account",
					filters={"parent": budget.name},
					fields=["account", "budget_amount"]
				)

				budget_detail = {
					"budget_name": budget.name,
					"cost_center": budget.cost_center,
					"fiscal_year": budget.fiscal_year,
					"project": budget.project,
					"company": budget.company,
					"accounts": [],
					"total_budget": 0,
					"total_actual": 0,
					"utilization_percent": 0,
					"remaining_budget": 0
				}

				for account in budget_accounts:
					# Calculate actual spending for this account
					actual_amount = self._get_actual_spending(
						account.account,
						budget.cost_center,
						budget.project,
						budget.fiscal_year
					)

					account_data = {
						"account": account.account,
						"budget_amount": account.budget_amount or 0,
						"actual_amount": actual_amount,
						"variance": (account.budget_amount or 0) - actual_amount,
						"utilization_percent": (actual_amount / (account.budget_amount or 1)) * 100 if account.budget_amount else 0
					}

					budget_detail["accounts"].append(account_data)
					budget_detail["total_budget"] += account.budget_amount or 0
					budget_detail["total_actual"] += actual_amount

				# Calculate overall utilization
				if budget_detail["total_budget"] > 0:
					budget_detail["utilization_percent"] = (budget_detail["total_actual"] / budget_detail["total_budget"]) * 100
					budget_detail["remaining_budget"] = budget_detail["total_budget"] - budget_detail["total_actual"]

				budget_analysis.append(budget_detail)
				total_allocated += budget_detail["total_budget"]
				total_actual += budget_detail["total_actual"]

			return {
				"budgets": budget_analysis,
				"summary": {
					"total_budgets": len(budgets),
					"total_allocated": total_allocated,
					"total_actual": total_actual,
					"overall_utilization": (total_actual / total_allocated * 100) if total_allocated > 0 else 0,
					"total_remaining": total_allocated - total_actual
				}
			}

		except Exception as e:
			frappe.log_error(f"Error getting budget data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve budget information"}

	def _get_actual_spending(self, account, cost_center=None, project=None, fiscal_year=None):
		"""Calculate actual spending from GL Entry for specific account and filters"""
		try:
			if not frappe.has_permission("GL Entry", "read"):
				return 0

			# Build filters for GL Entry
			gl_filters = {
				"account": account,
				"is_cancelled": 0
			}

			if cost_center:
				gl_filters["cost_center"] = cost_center
			if project:
				gl_filters["project"] = project

			# Get fiscal year dates if specified
			if fiscal_year:
				fy_doc = frappe.get_doc("Fiscal Year", fiscal_year)
				gl_filters["posting_date"] = ["between", [fy_doc.year_start_date, fy_doc.year_end_date]]

			# Sum debit amounts (expenses) for the account
			result = frappe.db.sql("""
				SELECT SUM(debit) as total_debit, SUM(credit) as total_credit
				FROM `tabGL Entry`
				WHERE account = %(account)s
				AND is_cancelled = 0
				{cost_center_condition}
				{project_condition}
				{date_condition}
			""".format(
				cost_center_condition="AND cost_center = %(cost_center)s" if cost_center else "",
				project_condition="AND project = %(project)s" if project else "",
				date_condition="AND posting_date BETWEEN %(start_date)s AND %(end_date)s" if fiscal_year else ""
			), {
				"account": account,
				"cost_center": cost_center,
				"project": project,
				"start_date": fy_doc.year_start_date if fiscal_year else None,
				"end_date": fy_doc.year_end_date if fiscal_year else None
			}, as_dict=True)

			if result and result[0]:
				# For expense accounts, debit is spending; for income accounts, credit is earning
				total_debit = result[0].get("total_debit") or 0
				total_credit = result[0].get("total_credit") or 0
				return total_debit - total_credit  # Net spending

			return 0

		except Exception as e:
			frappe.log_error(f"Error calculating actual spending: {str(e)}", "Context Service")
			return 0

	def get_cost_center_budget_analysis(self, cost_center=None, fiscal_year=None):
		"""Get budget analysis by cost center"""
		try:
			if not frappe.has_permission("Cost Center", "read"):
				return {"error": "No permission to access cost center data"}

			# Get cost centers
			cc_filters = {}
			if cost_center:
				cc_filters["name"] = cost_center

			cost_centers = frappe.get_all("Cost Center",
				filters=cc_filters,
				fields=["name", "cost_center_name", "parent_cost_center", "company"]
			)

			cc_analysis = []
			for cc in cost_centers:
				# Get budget data for this cost center
				budget_data = self.get_budget_data(cost_center=cc.name, fiscal_year=fiscal_year)

				cc_info = {
					"cost_center": cc.name,
					"cost_center_name": cc.cost_center_name,
					"parent_cost_center": cc.parent_cost_center,
					"company": cc.company,
					"budget_summary": budget_data.get("summary", {}),
					"budget_count": len(budget_data.get("budgets", []))
				}
				cc_analysis.append(cc_info)

			return {
				"cost_centers": cc_analysis,
				"total_cost_centers": len(cc_analysis)
			}

		except Exception as e:
			frappe.log_error(f"Error getting cost center budget analysis: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve cost center budget information"}

	def get_project_budget_analysis(self, project=None, fiscal_year=None):
		"""Get budget analysis by project"""
		try:
			if not frappe.has_permission("Project", "read"):
				return {"error": "No permission to access project data"}

			# Get projects
			project_filters = {"status": ["!=", "Cancelled"]}
			if project:
				project_filters["name"] = project

			projects = frappe.get_all("Project",
				filters=project_filters,
				fields=["name", "project_name", "status", "project_type", "company", "expected_start_date", "expected_end_date"],
				limit=20
			)

			project_analysis = []
			for proj in projects:
				# Get budget data for this project
				budget_data = self.get_budget_data(project=proj.name, fiscal_year=fiscal_year)

				proj_info = {
					"project": proj.name,
					"project_name": proj.project_name,
					"status": proj.status,
					"project_type": proj.project_type,
					"company": proj.company,
					"expected_start_date": proj.expected_start_date,
					"expected_end_date": proj.expected_end_date,
					"budget_summary": budget_data.get("summary", {}),
					"budget_count": len(budget_data.get("budgets", []))
				}
				project_analysis.append(proj_info)

			return {
				"projects": project_analysis,
				"total_projects": len(project_analysis)
			}

		except Exception as e:
			frappe.log_error(f"Error getting project budget analysis: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve project budget information"}

	def get_account_wise_spending(self, account=None, cost_center=None, project=None, fiscal_year=None, limit=50):
		"""Get detailed account-wise spending analysis"""
		try:
			if not frappe.has_permission("Account", "read"):
				return {"error": "No permission to access account data"}

			# Build account filters
			account_filters = {"is_group": 0}  # Only leaf accounts
			if account:
				account_filters["name"] = account

			accounts = frappe.get_all("Account",
				filters=account_filters,
				fields=["name", "account_name", "account_type", "root_type", "company"],
				limit=limit
			)

			account_analysis = []
			for acc in accounts:
				# Get actual spending for this account
				actual_spending = self._get_actual_spending(
					acc.name, cost_center, project, fiscal_year
				)

				# Get budget allocation for this account
				budget_amount = self._get_budget_allocation(
					acc.name, cost_center, project, fiscal_year
				)

				acc_info = {
					"account": acc.name,
					"account_name": acc.account_name,
					"account_type": acc.account_type,
					"root_type": acc.root_type,
					"company": acc.company,
					"budget_amount": budget_amount,
					"actual_spending": actual_spending,
					"variance": budget_amount - actual_spending,
					"utilization_percent": (actual_spending / budget_amount * 100) if budget_amount > 0 else 0
				}
				account_analysis.append(acc_info)

			# Sort by actual spending (highest first)
			account_analysis.sort(key=lambda x: x["actual_spending"], reverse=True)

			return {
				"accounts": account_analysis,
				"total_accounts": len(account_analysis),
				"summary": {
					"total_budget": sum(acc["budget_amount"] for acc in account_analysis),
					"total_actual": sum(acc["actual_spending"] for acc in account_analysis),
					"total_variance": sum(acc["variance"] for acc in account_analysis)
				}
			}

		except Exception as e:
			frappe.log_error(f"Error getting account-wise spending: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve account spending information"}

	def _get_budget_allocation(self, account, cost_center=None, project=None, fiscal_year=None):
		"""Get budget allocation for a specific account"""
		try:
			# Build filters for budget search
			budget_filters = {"docstatus": 1}
			if cost_center:
				budget_filters["cost_center"] = cost_center
			if project:
				budget_filters["project"] = project
			if fiscal_year:
				budget_filters["fiscal_year"] = fiscal_year

			# Get budgets matching the criteria
			budgets = frappe.get_all("Budget", filters=budget_filters, fields=["name"])

			total_allocation = 0
			for budget in budgets:
				# Get budget account allocation
				budget_account = frappe.db.get_value("Budget Account",
					{"parent": budget.name, "account": account},
					"budget_amount"
				)
				if budget_account:
					total_allocation += budget_account

			return total_allocation

		except Exception as e:
			frappe.log_error(f"Error getting budget allocation: {str(e)}", "Context Service")
			return 0

	def _get_budget_inquiry_data(self, entities, user_context):
		"""Get budget inquiry data based on entities"""
		try:
			# Extract filters from entities
			filters = {}
			if entities.get("document_names"):
				# Check if any document names are cost centers, projects, etc.
				for doc_name in entities["document_names"]:
					if frappe.db.exists("Cost Center", doc_name):
						filters["cost_center"] = doc_name
					elif frappe.db.exists("Project", doc_name):
						filters["project"] = doc_name

			# Get budget data
			budget_data = self.get_budget_data(filters)

			# Add contextual message
			if budget_data.get("budgets"):
				budget_data["message"] = f"Found {len(budget_data['budgets'])} budget(s) matching your criteria."
			else:
				budget_data["message"] = "No budgets found matching your criteria."

			return budget_data

		except Exception as e:
			frappe.log_error(f"Error getting budget inquiry data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve budget information"}

	def _get_spending_analysis_data(self, entities, user_context):
		"""Get spending analysis data"""
		try:
			# Get account-wise spending
			spending_data = self.get_account_wise_spending(limit=20)

			# Add summary message
			if spending_data.get("accounts"):
				total_spending = spending_data.get("summary", {}).get("total_actual", 0)
				spending_data["message"] = f"Total spending across {len(spending_data['accounts'])} accounts: {total_spending:,.2f}"
			else:
				spending_data["message"] = "No spending data found."

			return spending_data

		except Exception as e:
			frappe.log_error(f"Error getting spending analysis data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve spending information"}

	def _get_budget_comparison_data(self, entities, user_context):
		"""Get budget vs actual comparison data"""
		try:
			# Use assistant_crm's own budget analysis service
			from assistant_crm.assistant_crm.services.budget_analysis_service import BudgetAnalysisService

			budget_service = BudgetAnalysisService()
			analysis_result = budget_service.analyze_budget_performance()

			if "error" in analysis_result:
				return analysis_result

			# Format for chat response
			kpis = analysis_result.get("kpis", {})
			comparison_data = {
				"budget_vs_actual": {
					"total_budget": kpis.get("total_budget_amount", 0),
					"total_actual": kpis.get("total_actual_spending", 0),
					"variance": kpis.get("total_variance", 0),
					"utilization_percent": kpis.get("overall_utilization_percent", 0)
				},
				"insights": analysis_result.get("insights", []),
				"alerts": analysis_result.get("alerts", []),
				"message": f"Budget utilization: {kpis.get('overall_utilization_percent', 0):.1f}%"
			}

			return comparison_data

		except Exception as e:
			frappe.log_error(f"Error getting budget comparison data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve budget comparison"}

	def _get_financial_kpis_data(self, entities, user_context):
		"""Get financial KPIs data"""
		try:
			# Use assistant_crm's own budget analysis service
			from assistant_crm.assistant_crm.services.budget_analysis_service import BudgetAnalysisService

			budget_service = BudgetAnalysisService()
			analysis_result = budget_service.analyze_budget_performance()

			if "error" in analysis_result:
				return analysis_result

			kpis = analysis_result.get("kpis", {})

			# Format KPIs for chat response
			kpi_data = {
				"financial_kpis": kpis,
				"summary": {
					"total_budgets": kpis.get("total_budget_lines", 0),
					"overall_performance": "Good" if kpis.get("overall_utilization_percent", 0) < 90 else "Needs Attention",
					"savings_achieved": kpis.get("savings_achieved", 0),
					"overspend_amount": kpis.get("overspend_amount", 0)
				},
				"message": f"Financial overview: {kpis.get('total_budget_lines', 0)} budget lines with {kpis.get('overall_utilization_percent', 0):.1f}% utilization"
			}

			return kpi_data

		except Exception as e:
			frappe.log_error(f"Error getting financial KPIs data: {str(e)}", "Context Service")
			return {"error": "Failed to retrieve financial KPIs"}

def get_enhanced_user_context(self, include_persona=True, include_preferences=True):
	"""Get enhanced user context with persona-specific data"""
	try:
		# Get base user context
		base_context = self.get_user_context()

		# Add persona-specific enhancements
		if include_persona:
			persona_data = self.get_user_persona_data()
			base_context["persona_data"] = persona_data

		if include_preferences:
			preferences = self.get_user_preferences()
			base_context["preferences"] = preferences

		# Add conversation context
		conversation_context = self.get_conversation_context()
		base_context["conversation_context"] = conversation_context

		# Add persona-specific recent activity
		if include_persona and persona_data.get("detected_persona"):
			persona_activity = self.get_persona_specific_activity(persona_data["detected_persona"])
			base_context["persona_activity"] = persona_activity

		return base_context

	except Exception as e:
		frappe.log_error(f"Error getting enhanced user context: {str(e)}", "Context Service")
		return self.get_user_context()  # Fallback to base context

def get_user_persona_data(self):
	"""Get user persona detection data and history - deprecated"""
	# Persona Detection Log doctype has been deprecated
	# Return empty persona data
	return {"detected_persona": None, "confidence": 0.0, "recent_detections": []}

def get_user_preferences(self):
	"""Get user preferences and learned behaviors"""
	try:
		# Check cache first
		cache_key = f"preferences_{self.user}"
		if cache_key in self.preference_cache:
			return self.preference_cache[cache_key]

		preferences = {
			"communication_style": self._analyze_communication_preferences(),
			"information_depth": self._analyze_information_preferences(),
			"response_timing": self._analyze_timing_preferences(),
			"preferred_channels": self._analyze_channel_preferences(),
			"language_preference": self._get_language_preference(),
			"interaction_patterns": self._analyze_interaction_patterns()
		}

		# Cache the result
		self.preference_cache[cache_key] = preferences

		return preferences

	except Exception as e:
		frappe.log_error(f"Error getting user preferences: {str(e)}", "Context Service")
		return {}

def get_conversation_context(self):
	"""Get current conversation context"""
	try:
		# Get recent chat history for this user
		recent_chats = frappe.get_all(
			"Chat History",
			fields=["message", "response", "timestamp", "session_id"],
			filters={
				"user": self.user,
				"creation": [">=", frappe.utils.add_hours(frappe.utils.now(), -24)]
			},
			order_by="timestamp desc",
			limit=20
		)

		if not recent_chats:
			return {"recent_topics": [], "conversation_flow": [], "active_sessions": 0}

		# Analyze conversation topics
		recent_topics = self._extract_conversation_topics(recent_chats)

		# Analyze conversation flow
		conversation_flow = self._analyze_conversation_flow(recent_chats)

		# Count active sessions
		active_sessions = len(set(chat.get("session_id") for chat in recent_chats if chat.get("session_id")))

		return {
			"recent_topics": recent_topics,
			"conversation_flow": conversation_flow,
			"active_sessions": active_sessions,
			"last_interaction": recent_chats[0]["timestamp"] if recent_chats else None,
			"total_interactions_24h": len(recent_chats)
		}

	except Exception as e:
		frappe.log_error(f"Error getting conversation context: {str(e)}", "Context Service")
		return {"recent_topics": [], "conversation_flow": [], "active_sessions": 0}

def get_persona_specific_activity(self, persona):
	"""Get persona-specific recent activity"""
	try:
		activity_queries = {
			"employer": self._get_employer_activity,
			"beneficiary": self._get_beneficiary_activity,
			"supplier": self._get_supplier_activity,
			"wcfcb_staff": self._get_staff_activity
		}

		if persona in activity_queries:
			return activity_queries[persona]()
		else:
			return self._get_general_activity()

	except Exception as e:
		frappe.log_error(f"Error getting persona-specific activity: {str(e)}", "Context Service")
		return []

def _analyze_communication_preferences(self):
	"""Analyze user's communication style preferences"""
	try:
		# Get recent chat interactions
		recent_chats = frappe.get_all(
			"Chat History",
			fields=["message", "response", "timestamp"],
			filters={
				"user": self.user,
				"creation": [">=", frappe.utils.add_days(frappe.utils.now(), -30)]
			},
			order_by="timestamp desc",
			limit=50
		)

		if not recent_chats:
			return {"style": "neutral", "confidence": 0.0}

		# Analyze message patterns
		formal_indicators = ["please", "thank you", "could you", "would you", "sir", "madam"]
		casual_indicators = ["hi", "hey", "thanks", "ok", "yeah", "sure"]
		technical_indicators = ["system", "configuration", "parameter", "function", "process"]

		formal_count = 0
		casual_count = 0
		technical_count = 0

		for chat in recent_chats:
			message = chat.get("message", "").lower()
			formal_count += sum(1 for indicator in formal_indicators if indicator in message)
			casual_count += sum(1 for indicator in casual_indicators if indicator in message)
			technical_count += sum(1 for indicator in technical_indicators if indicator in message)

		total_indicators = formal_count + casual_count + technical_count

		if total_indicators == 0:
			return {"style": "neutral", "confidence": 0.0}

		# Determine dominant style
		if formal_count > casual_count and formal_count > technical_count:
			style = "formal"
			confidence = formal_count / total_indicators
		elif technical_count > casual_count and technical_count > formal_count:
			style = "technical"
			confidence = technical_count / total_indicators
		elif casual_count > 0:
			style = "casual"
			confidence = casual_count / total_indicators
		else:
			style = "neutral"
			confidence = 0.5

		return {"style": style, "confidence": confidence}

	except Exception as e:
		frappe.log_error(f"Error analyzing communication preferences: {str(e)}", "Context Service")
		return {"style": "neutral", "confidence": 0.0}

def _get_employer_activity(self):
	"""Get employer-specific recent activity"""
	try:
		# Look for business-related activities
		activities = []

		# Check for recent business registrations or updates
		# This would integrate with actual business systems
		activities.append({
			"type": "business_inquiry",
			"description": "Recent business-related inquiries",
			"timestamp": frappe.utils.now(),
			"relevance": "high"
		})

		return activities
	except Exception:
		return []

def _get_beneficiary_activity(self):
	"""Get beneficiary-specific recent activity"""
	try:
		activities = []

		# Check for recent benefit-related activities
		activities.append({
			"type": "benefit_inquiry",
			"description": "Recent benefit status inquiries",
			"timestamp": frappe.utils.now(),
			"relevance": "high"
		})

		return activities
	except Exception:
		return []

def _get_supplier_activity(self):
	"""Get supplier-specific recent activity"""
	try:
		activities = []

		# Check for recent supplier-related activities
		activities.append({
			"type": "vendor_inquiry",
			"description": "Recent vendor payment inquiries",
			"timestamp": frappe.utils.now(),
			"relevance": "high"
		})

		return activities
	except Exception:
		return []

def _get_staff_activity(self):
	"""Get staff-specific recent activity"""
	try:
		activities = []

		# Check for recent internal activities
		activities.append({
			"type": "internal_inquiry",
			"description": "Recent internal system inquiries",
			"timestamp": frappe.utils.now(),
			"relevance": "high"
		})

		return activities
	except Exception:
		return []

def _get_general_activity(self):
	"""Get general recent activity"""
	try:
		activities = []

		# Check for general activities
		activities.append({
			"type": "general_inquiry",
			"description": "Recent general inquiries",
			"timestamp": frappe.utils.now(),
			"relevance": "medium"
		})

		return activities
	except Exception:
		return []

def clear_persona_cache(self, user=None):
	"""Clear persona cache for user or all users"""
	if user:
		cache_keys = [k for k in self.persona_cache.keys() if k.endswith(user)]
		for key in cache_keys:
			del self.persona_cache[key]
	else:
		self.persona_cache.clear()

def clear_preference_cache(self, user=None):
	"""Clear preference cache for user or all users"""
	if user:
		cache_keys = [k for k in self.preference_cache.keys() if k.endswith(user)]
		for key in cache_keys:
			del self.preference_cache[key]
	else:
		self.preference_cache.clear()

def update_user_persona_preference(self, persona, confidence=1.0):
	"""Update user's persona preference based on validation"""
	try:
		# This could be used to improve persona detection accuracy
		# by learning from user feedback or validation

		# Clear cache to force refresh
		self.clear_persona_cache(self.user)

		# Log the preference update
		frappe.log_error(
			f"Persona preference updated for {self.user}: {persona} (confidence: {confidence})",
			"Context Service - Persona Learning"
		)

	except Exception as e:
		frappe.log_error(f"Error updating persona preference: {str(e)}", "Context Service")
