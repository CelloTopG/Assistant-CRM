# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.utils import flt, getdate
from assistant_crm.services.context_service import ContextService
from assistant_crm.services.budget_analysis_service import BudgetAnalysisService
from assistant_crm.services.financial_query_parser import FinancialQueryParser
from assistant_crm.services.security_service import SecurityService


@frappe.whitelist()
def get_budget_analysis(filters=None):
	"""
	Get comprehensive budget analysis with real-time data
	
	Args:
		filters (dict): Optional filters for cost_center, project, fiscal_year, company
	
	Returns:
		dict: Budget analysis data with performance metrics
	"""
	try:
		# Initialize services
		security_service = SecurityService()
		budget_service = BudgetAnalysisService()
		
		# Validate user access
		access_check = security_service.validate_user_access()
		if not access_check["valid"]:
			return {
				"success": False,
				"error": access_check["error"]
			}
		
		# Check budget permissions
		if not frappe.has_permission("Budget", "read"):
			return {
				"success": False,
				"error": _("No permission to access budget data")
			}
		
		# Parse filters
		if isinstance(filters, str):
			filters = json.loads(filters)
		filters = filters or {}
		
		# Get budget analysis
		analysis_result = budget_service.analyze_budget_performance(filters)
		
		if "error" in analysis_result:
			return {
				"success": False,
				"error": analysis_result["error"]
			}
		
		return {
			"success": True,
			"data": analysis_result,
			"timestamp": frappe.utils.now()
		}
		
	except Exception as e:
		frappe.log_error(f"Budget Analysis API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to retrieve budget analysis")
		}


@frappe.whitelist()
def query_financial_data(query, query_type=None):
	"""
	Process natural language financial queries and return structured data
	
	Args:
		query (str): Natural language query about budgets/finances
		query_type (str): Optional hint about query type
	
	Returns:
		dict: Structured financial data response
	"""
	try:
		# Initialize services
		security_service = SecurityService()
		context_service = ContextService()
		query_parser = FinancialQueryParser()
		budget_service = BudgetAnalysisService()
		
		# Validate user access
		access_check = security_service.validate_user_access()
		if not access_check["valid"]:
			return {
				"success": False,
				"error": access_check["error"]
			}
		
		# Sanitize query
		query = security_service.sanitize_input(query)
		if not query:
			return {
				"success": False,
				"error": _("Invalid or empty query")
			}
		
		# Parse the financial query
		parsed_query = query_parser.parse_financial_query(query)
		
		# Validate entities
		validated_entities = query_parser.validate_entities(parsed_query["entities"])
		parsed_query["validated_entities"] = validated_entities
		
		# Process based on query type
		result_data = _process_financial_query(parsed_query, context_service, budget_service)
		
		return {
			"success": True,
			"query_analysis": {
				"intent": parsed_query["intent"],
				"confidence": parsed_query["confidence"],
				"query_type": parsed_query["query_type"],
				"entities": validated_entities,
				"time_context": parsed_query["time_context"]
			},
			"data": result_data,
			"timestamp": frappe.utils.now()
		}
		
	except Exception as e:
		frappe.log_error(f"Financial Query API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to process financial query")
		}


def _process_financial_query(parsed_query, context_service, budget_service):
	"""Process parsed financial query and return appropriate data"""
	try:
		query_type = parsed_query["query_type"]
		filters = parsed_query["filters"]
		validated_entities = parsed_query.get("validated_entities", {})
		
		# Update filters with validated entities
		filters.update(validated_entities)
		
		if query_type == "general_budget":
			return context_service.get_budget_data(filters)
		
		elif query_type == "cost_center_budget":
			cost_center = filters.get("cost_center")
			fiscal_year = filters.get("fiscal_year")
			return context_service.get_cost_center_budget_analysis(cost_center, fiscal_year)
		
		elif query_type == "project_budget":
			project = filters.get("project")
			fiscal_year = filters.get("fiscal_year")
			return context_service.get_project_budget_analysis(project, fiscal_year)
		
		elif query_type == "account_budget":
			return context_service.get_account_wise_spending(
				account=filters.get("account"),
				cost_center=filters.get("cost_center"),
				project=filters.get("project"),
				fiscal_year=filters.get("fiscal_year")
			)
		
		elif query_type == "spending_analysis":
			return budget_service.analyze_budget_performance(filters)
		
		elif query_type == "budget_vs_actual":
			return budget_service.analyze_budget_performance(filters)
		
		elif query_type == "time_based_budget":
			return context_service.get_budget_data(filters)
		
		else:
			# Default to general budget data
			return context_service.get_budget_data(filters)
		
	except Exception as e:
		frappe.log_error(f"Error processing financial query: {str(e)}", "Financial Query Processing")
		return {"error": "Failed to process query"}


@frappe.whitelist()
def get_budget_summary(cost_center=None, project=None, fiscal_year=None):
	"""
	Get budget summary for specific filters
	
	Args:
		cost_center (str): Optional cost center filter
		project (str): Optional project filter
		fiscal_year (str): Optional fiscal year filter
	
	Returns:
		dict: Budget summary data
	"""
	try:
		# Check permissions
		if not frappe.has_permission("Budget", "read"):
			return {
				"success": False,
				"error": _("No permission to access budget data")
			}
		
		context_service = ContextService()
		
		# Build filters
		filters = {}
		if cost_center:
			filters["cost_center"] = cost_center
		if project:
			filters["project"] = project
		if fiscal_year:
			filters["fiscal_year"] = fiscal_year
		
		# Get budget data
		budget_data = context_service.get_budget_data(filters)
		
		return {
			"success": True,
			"data": budget_data,
			"filters_applied": filters
		}
		
	except Exception as e:
		frappe.log_error(f"Budget Summary API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to retrieve budget summary")
		}


@frappe.whitelist()
def get_spending_analysis(account=None, cost_center=None, project=None, fiscal_year=None):
	"""
	Get detailed spending analysis
	
	Args:
		account (str): Optional account filter
		cost_center (str): Optional cost center filter
		project (str): Optional project filter
		fiscal_year (str): Optional fiscal year filter
	
	Returns:
		dict: Spending analysis data
	"""
	try:
		# Check permissions
		if not frappe.has_permission("GL Entry", "read"):
			return {
				"success": False,
				"error": _("No permission to access financial data")
			}
		
		context_service = ContextService()
		
		# Get account-wise spending
		spending_data = context_service.get_account_wise_spending(
			account=account,
			cost_center=cost_center,
			project=project,
			fiscal_year=fiscal_year
		)
		
		return {
			"success": True,
			"data": spending_data,
			"filters_applied": {
				"account": account,
				"cost_center": cost_center,
				"project": project,
				"fiscal_year": fiscal_year
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Spending Analysis API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to retrieve spending analysis")
		}


@frappe.whitelist()
def get_budget_alerts():
	"""
	Get budget alerts and warnings for current user's accessible data
	
	Returns:
		dict: Budget alerts and warnings
	"""
	try:
		# Check permissions
		if not frappe.has_permission("Budget", "read"):
			return {
				"success": False,
				"error": _("No permission to access budget data")
			}
		
		budget_service = BudgetAnalysisService()
		
		# Get current fiscal year
		current_fy = frappe.db.get_value("Fiscal Year", 
			{"year_start_date": ["<=", getdate()], "year_end_date": [">=", getdate()]}, 
			"name"
		)
		
		filters = {}
		if current_fy:
			filters["fiscal_year"] = current_fy
		
		# Get budget analysis with alerts
		analysis_result = budget_service.analyze_budget_performance(filters)
		
		if "error" in analysis_result:
			return {
				"success": False,
				"error": analysis_result["error"]
			}
		
		return {
			"success": True,
			"alerts": analysis_result.get("alerts", []),
			"insights": analysis_result.get("insights", []),
			"kpis": analysis_result.get("kpis", {}),
			"fiscal_year": current_fy
		}
		
	except Exception as e:
		frappe.log_error(f"Budget Alerts API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to retrieve budget alerts")
		}


@frappe.whitelist()
def get_budget_forecast(account, cost_center=None, project=None, months_ahead=3):
	"""
	Get budget forecast for specific account
	
	Args:
		account (str): Account name
		cost_center (str): Optional cost center filter
		project (str): Optional project filter
		months_ahead (int): Number of months to forecast
	
	Returns:
		dict: Budget forecast data
	"""
	try:
		# Check permissions
		if not frappe.has_permission("GL Entry", "read"):
			return {
				"success": False,
				"error": _("No permission to access financial data")
			}
		
		# Validate account exists
		if not frappe.db.exists("Account", account):
			return {
				"success": False,
				"error": _("Account not found")
			}
		
		budget_service = BudgetAnalysisService()
		
		# Get forecast
		forecast_data = budget_service.get_budget_forecast(
			account=account,
			cost_center=cost_center,
			project=project,
			months_ahead=int(months_ahead)
		)
		
		if "error" in forecast_data:
			return {
				"success": False,
				"error": forecast_data["error"]
			}
		
		return {
			"success": True,
			"data": forecast_data,
			"parameters": {
				"account": account,
				"cost_center": cost_center,
				"project": project,
				"months_ahead": months_ahead
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Budget Forecast API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to generate budget forecast")
		}


@frappe.whitelist()
def get_financial_kpis(fiscal_year=None):
	"""
	Get key financial performance indicators
	
	Args:
		fiscal_year (str): Optional fiscal year filter
	
	Returns:
		dict: Financial KPIs
	"""
	try:
		# Check permissions
		if not frappe.has_permission("Budget", "read"):
			return {
				"success": False,
				"error": _("No permission to access budget data")
			}
		
		budget_service = BudgetAnalysisService()
		
		# Get current fiscal year if not provided
		if not fiscal_year:
			fiscal_year = frappe.db.get_value("Fiscal Year", 
				{"year_start_date": ["<=", getdate()], "year_end_date": [">=", getdate()]}, 
				"name"
			)
		
		filters = {"fiscal_year": fiscal_year} if fiscal_year else {}
		
		# Get budget analysis
		analysis_result = budget_service.analyze_budget_performance(filters)
		
		if "error" in analysis_result:
			return {
				"success": False,
				"error": analysis_result["error"]
			}
		
		return {
			"success": True,
			"kpis": analysis_result.get("kpis", {}),
			"fiscal_year": fiscal_year,
			"summary": {
				"total_budgets": len(analysis_result.get("performance_data", [])),
				"analysis_date": frappe.utils.now()
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Financial KPIs API Error: {str(e)}", "ExN Assistant Financial API")
		return {
			"success": False,
			"error": _("Failed to retrieve financial KPIs")
		}
