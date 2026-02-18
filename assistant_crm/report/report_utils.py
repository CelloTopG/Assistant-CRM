import frappe
from frappe.utils import getdate, add_months, add_days, get_first_day

def get_period_dates(filters):
    """
    Update filters with date_from and date_to if missing, based on period_type.
    """
    if not filters.get("date_from") or not filters.get("date_to"):
        period_type = filters.get("period_type")
        date_to = getdate()
        
        if period_type == "Weekly":
            # Start of current week (Monday)
            date_from = add_days(date_to, -date_to.weekday())
        elif period_type == "Monthly":
            date_from = get_first_day(date_to)
        elif period_type == "Quarterly":
            month = date_to.month
            quarter_start_month = ((month - 1) // 3) * 3 + 1
            date_from = getdate(f"{date_to.year}-{quarter_start_month:02d}-01")
        elif period_type == "Annual":
            date_from = getdate(f"{date_to.year}-01-01")
        else:
            # Default fallback for Custom or others: last 30 days
            date_from = add_days(date_to, -29)
            
        filters.date_from = date_from
        filters.date_to = date_to
    
    return filters
