# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_first_day, get_last_day
from datetime import datetime, timedelta
import json


class BudgetAnalysisService:
	"""Advanced budget analysis and financial data processing service"""
	
	def __init__(self):
		self.user = frappe.session.user
	
	def analyze_budget_performance(self, filters=None):
		"""Comprehensive budget performance analysis"""
		try:
			filters = filters or {}
			
			# Get budget data with performance metrics
			budget_performance = self._get_budget_performance_data(filters)
			
			# Calculate key performance indicators
			kpis = self._calculate_budget_kpis(budget_performance)
			
			# Generate insights and recommendations
			insights = self._generate_budget_insights(budget_performance, kpis)
			
			# Identify budget alerts and warnings
			alerts = self._identify_budget_alerts(budget_performance)
			
			return {
				"performance_data": budget_performance,
				"kpis": kpis,
				"insights": insights,
				"alerts": alerts,
				"analysis_date": frappe.utils.now()
			}
			
		except Exception as e:
			frappe.log_error(f"Error in budget performance analysis: {str(e)}", "Budget Analysis Service")
			return {"error": "Failed to analyze budget performance"}
	
	def _get_budget_performance_data(self, filters):
		"""Get detailed budget performance data"""
		try:
			# Build dynamic query based on filters
			conditions = ["b.docstatus = 1"]
			values = {}
			
			if filters.get("cost_center"):
				conditions.append("b.cost_center = %(cost_center)s")
				values["cost_center"] = filters["cost_center"]
			
			if filters.get("project"):
				conditions.append("b.project = %(project)s")
				values["project"] = filters["project"]
			
			if filters.get("fiscal_year"):
				conditions.append("b.fiscal_year = %(fiscal_year)s")
				values["fiscal_year"] = filters["fiscal_year"]
			
			if filters.get("company"):
				conditions.append("b.company = %(company)s")
				values["company"] = filters["company"]
			
			where_clause = " AND ".join(conditions)
			
			# Get budget data with account details
			budget_data = frappe.db.sql(f"""
				SELECT 
					b.name as budget_name,
					b.cost_center,
					b.project,
					b.fiscal_year,
					b.company,
					b.budget_against,
					ba.account,
					ba.budget_amount,
					acc.account_name,
					acc.account_type,
					acc.root_type,
					cc.cost_center_name,
					fy.year_start_date,
					fy.year_end_date
				FROM `tabBudget` b
				LEFT JOIN `tabBudget Account` ba ON ba.parent = b.name
				LEFT JOIN `tabAccount` acc ON acc.name = ba.account
				LEFT JOIN `tabCost Center` cc ON cc.name = b.cost_center
				LEFT JOIN `tabFiscal Year` fy ON fy.name = b.fiscal_year
				WHERE {where_clause}
				ORDER BY b.creation DESC
			""", values, as_dict=True)
			
			# Enhance with actual spending data
			enhanced_data = []
			for row in budget_data:
				if row.account:  # Only process if account exists
					actual_spending = self._calculate_actual_spending(
						row.account, 
						row.cost_center, 
						row.project,
						row.year_start_date,
						row.year_end_date
					)
					
					budget_amount = flt(row.budget_amount)
					variance = budget_amount - actual_spending
					utilization = (actual_spending / budget_amount * 100) if budget_amount > 0 else 0
					
					enhanced_row = dict(row)
					enhanced_row.update({
						"actual_spending": actual_spending,
						"variance": variance,
						"utilization_percent": utilization,
						"remaining_budget": variance,
						"status": self._get_budget_status(utilization),
						"risk_level": self._assess_risk_level(utilization, variance)
					})
					enhanced_data.append(enhanced_row)
			
			return enhanced_data
			
		except Exception as e:
			frappe.log_error(f"Error getting budget performance data: {str(e)}", "Budget Analysis Service")
			return []
	
	def _calculate_actual_spending(self, account, cost_center=None, project=None, start_date=None, end_date=None):
		"""Calculate actual spending from GL Entry"""
		try:
			conditions = ["gl.account = %(account)s", "gl.is_cancelled = 0"]
			values = {"account": account}
			
			if cost_center:
				conditions.append("gl.cost_center = %(cost_center)s")
				values["cost_center"] = cost_center
			
			if project:
				conditions.append("gl.project = %(project)s")
				values["project"] = project
			
			if start_date and end_date:
				conditions.append("gl.posting_date BETWEEN %(start_date)s AND %(end_date)s")
				values["start_date"] = start_date
				values["end_date"] = end_date
			
			where_clause = " AND ".join(conditions)
			
			result = frappe.db.sql(f"""
				SELECT 
					SUM(gl.debit) as total_debit,
					SUM(gl.credit) as total_credit,
					COUNT(*) as transaction_count
				FROM `tabGL Entry` gl
				WHERE {where_clause}
			""", values, as_dict=True)
			
			if result and result[0]:
				total_debit = flt(result[0].get("total_debit", 0))
				total_credit = flt(result[0].get("total_credit", 0))
				return total_debit - total_credit  # Net spending
			
			return 0
			
		except Exception as e:
			frappe.log_error(f"Error calculating actual spending: {str(e)}", "Budget Analysis Service")
			return 0
	
	def _calculate_budget_kpis(self, budget_data):
		"""Calculate key performance indicators"""
		try:
			if not budget_data:
				return {}
			
			total_budget = sum(flt(row.get("budget_amount", 0)) for row in budget_data)
			total_actual = sum(flt(row.get("actual_spending", 0)) for row in budget_data)
			total_variance = total_budget - total_actual
			
			# Calculate utilization statistics
			utilizations = [row.get("utilization_percent", 0) for row in budget_data if row.get("budget_amount", 0) > 0]
			avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
			
			# Count budget statuses
			status_counts = {}
			risk_counts = {}
			for row in budget_data:
				status = row.get("status", "Unknown")
				risk = row.get("risk_level", "Unknown")
				status_counts[status] = status_counts.get(status, 0) + 1
				risk_counts[risk] = risk_counts.get(risk, 0) + 1
			
			return {
				"total_budget_amount": total_budget,
				"total_actual_spending": total_actual,
				"total_variance": total_variance,
				"overall_utilization_percent": (total_actual / total_budget * 100) if total_budget > 0 else 0,
				"average_utilization_percent": avg_utilization,
				"total_budget_lines": len(budget_data),
				"budget_status_distribution": status_counts,
				"risk_level_distribution": risk_counts,
				"savings_achieved": max(0, total_variance),
				"overspend_amount": abs(min(0, total_variance))
			}
			
		except Exception as e:
			frappe.log_error(f"Error calculating budget KPIs: {str(e)}", "Budget Analysis Service")
			return {}
	
	def _generate_budget_insights(self, budget_data, kpis):
		"""Generate intelligent budget insights and recommendations"""
		try:
			insights = []
			
			# Overall performance insight
			overall_util = kpis.get("overall_utilization_percent", 0)
			if overall_util > 100:
				insights.append({
					"type": "warning",
					"title": "Budget Overrun Detected",
					"message": f"Overall budget utilization is {overall_util:.1f}%, indicating overspending of {kpis.get('overspend_amount', 0):,.2f}",
					"priority": "high"
				})
			elif overall_util > 90:
				insights.append({
					"type": "caution",
					"title": "High Budget Utilization",
					"message": f"Budget utilization is {overall_util:.1f}%, approaching the limit. Monitor spending closely.",
					"priority": "medium"
				})
			elif overall_util < 50:
				insights.append({
					"type": "info",
					"title": "Low Budget Utilization",
					"message": f"Budget utilization is only {overall_util:.1f}%. Consider reallocating unused funds.",
					"priority": "low"
				})
			
			# Top spending accounts
			top_spenders = sorted(budget_data, key=lambda x: x.get("actual_spending", 0), reverse=True)[:5]
			if top_spenders:
				insights.append({
					"type": "info",
					"title": "Top Spending Accounts",
					"message": f"Highest spending: {top_spenders[0].get('account_name', 'Unknown')} ({top_spenders[0].get('actual_spending', 0):,.2f})",
					"priority": "low",
					"details": [{"account": acc.get("account_name"), "amount": acc.get("actual_spending", 0)} for acc in top_spenders]
				})
			
			# Variance analysis
			high_variance = [row for row in budget_data if abs(row.get("variance", 0)) > row.get("budget_amount", 0) * 0.2]
			if high_variance:
				insights.append({
					"type": "warning",
					"title": "High Variance Accounts",
					"message": f"{len(high_variance)} accounts have variance > 20% of budget",
					"priority": "medium",
					"details": [{"account": acc.get("account_name"), "variance": acc.get("variance", 0)} for acc in high_variance[:5]]
				})
			
			return insights
			
		except Exception as e:
			frappe.log_error(f"Error generating budget insights: {str(e)}", "Budget Analysis Service")
			return []
	
	def _identify_budget_alerts(self, budget_data):
		"""Identify budget alerts and warnings"""
		try:
			alerts = []
			
			for row in budget_data:
				utilization = row.get("utilization_percent", 0)
				account_name = row.get("account_name", row.get("account", "Unknown"))
				
				if utilization > 100:
					alerts.append({
						"type": "critical",
						"account": account_name,
						"message": f"Budget exceeded by {utilization - 100:.1f}%",
						"amount_over": row.get("actual_spending", 0) - row.get("budget_amount", 0)
					})
				elif utilization > 90:
					alerts.append({
						"type": "warning",
						"account": account_name,
						"message": f"Budget utilization at {utilization:.1f}%",
						"remaining": row.get("remaining_budget", 0)
					})
			
			return alerts
			
		except Exception as e:
			frappe.log_error(f"Error identifying budget alerts: {str(e)}", "Budget Analysis Service")
			return []
	
	def _get_budget_status(self, utilization):
		"""Determine budget status based on utilization"""
		if utilization > 100:
			return "Over Budget"
		elif utilization > 90:
			return "Near Limit"
		elif utilization > 75:
			return "On Track"
		elif utilization > 50:
			return "Under Utilized"
		else:
			return "Significantly Under Utilized"
	
	def _assess_risk_level(self, utilization, variance):
		"""Assess risk level based on utilization and variance"""
		if utilization > 100:
			return "High Risk"
		elif utilization > 90 or abs(variance) > 10000:  # Configurable threshold
			return "Medium Risk"
		else:
			return "Low Risk"
	
	def get_budget_forecast(self, account, cost_center=None, project=None, months_ahead=3):
		"""Generate budget forecast based on historical spending patterns"""
		try:
			# Get historical spending data
			historical_data = self._get_historical_spending(account, cost_center, project, months_ahead * 2)
			
			if not historical_data:
				return {"error": "Insufficient historical data for forecasting"}
			
			# Calculate average monthly spending
			monthly_avg = sum(historical_data) / len(historical_data)
			
			# Generate forecast
			forecast = []
			current_date = getdate()
			
			for i in range(months_ahead):
				forecast_date = add_months(current_date, i + 1)
				forecast_amount = monthly_avg * (1 + (i * 0.02))  # Slight growth assumption
				
				forecast.append({
					"month": forecast_date.strftime("%Y-%m"),
					"forecasted_amount": forecast_amount,
					"confidence": max(0.5, 1 - (i * 0.1))  # Decreasing confidence
				})
			
			return {
				"account": account,
				"historical_average": monthly_avg,
				"forecast": forecast,
				"total_forecasted": sum(f["forecasted_amount"] for f in forecast)
			}
			
		except Exception as e:
			frappe.log_error(f"Error generating budget forecast: {str(e)}", "Budget Analysis Service")
			return {"error": "Failed to generate budget forecast"}
	
	def _get_historical_spending(self, account, cost_center=None, project=None, months_back=6):
		"""Get historical monthly spending data"""
		try:
			monthly_data = []
			current_date = getdate()
			
			for i in range(months_back):
				month_start = get_first_day(add_months(current_date, -i))
				month_end = get_last_day(add_months(current_date, -i))
				
				spending = self._calculate_actual_spending(
					account, cost_center, project, month_start, month_end
				)
				monthly_data.append(spending)
			
			return monthly_data
			
		except Exception as e:
			frappe.log_error(f"Error getting historical spending: {str(e)}", "Budget Analysis Service")
			return []
