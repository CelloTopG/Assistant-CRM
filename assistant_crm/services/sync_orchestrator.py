import frappe
from typing import Dict


@frappe.whitelist()
def pilot_corebusiness_employee_sync(limit: int = 25) -> Dict:
    """Pilot: pull employees from CoreBusiness into Assistant CRM Employee Profile.

    Returns a small summary dict of successes and failures.
    """
    from assistant_crm.assistant_crm.services.wcfcb_integration_service import WCFCBIntegrationService

    svc = WCFCBIntegrationService()
    # Use the class's bulk method to fetch employees with a limit
    result = svc.bulk_sync_from_corebusiness(entity_type="employees", limit=int(limit))
    return result.get("employees") if isinstance(result, dict) else {"success": 0, "failed": 0}

