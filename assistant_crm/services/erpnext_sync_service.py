import frappe
from frappe import _
from typing import Optional, Dict
from datetime import date


def _get_default_company() -> Optional[str]:
    # Try system default company first
    default_company = frappe.defaults.get_global_default("company")
    if default_company:
        return default_company
    # Fallback to first available Company
    companies = frappe.get_all("Company", pluck="name")
    return companies[0] if companies else None


def _map_gender(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = (value or "").strip().title()
    if v in {"Male", "Female", "Other"}:
        return v
    return None


def _ensure_department(dept_name: Optional[str]) -> Optional[str]:
    if not dept_name:
        return None
    # Create Department if it doesn't exist
    if not frappe.db.exists("Department", dept_name):
        try:
            d = frappe.new_doc("Department")
            d.department_name = dept_name
            d.save(ignore_permissions=True)
        except Exception:
            # Ignore creation failures; let Employee save without department
            return None
    return dept_name


@frappe.whitelist()
def upsert_erpnext_employee_from_employee_profile(profile_name: str, company: Optional[str] = None) -> Dict:
    """Create or update ERPNext Employee from Assistant CRM Employee Profile.

    DEPRECATED: Employee Profile doctype has been removed.
    Use ERPNext Employee directly.

    Returns {"name": None, "created": False, "deprecated": True}
    """
    # NOTE: Employee Profile doctype has been removed - use ERPNext Employee directly
    _ = profile_name  # Unused - doctype removed
    _ = company  # Unused - doctype removed
    return {"name": None, "created": False, "deprecated": True, "message": "Employee Profile doctype removed - use ERPNext Employee directly"}


@frappe.whitelist()
def sync_all_employee_profiles_to_erpnext(company: Optional[str] = None, limit: Optional[int] = None) -> Dict:
    """Bulk sync all Assistant CRM Employee Profile records into ERPNext Employee.

    DEPRECATED: Employee Profile doctype has been removed.
    Use ERPNext Employee directly.

    Returns summary: {"synced": 0, "created": 0, "updated": 0, "deprecated": True}
    """
    # NOTE: Employee Profile doctype has been removed - use ERPNext Employee directly
    _ = company  # Unused - doctype removed
    _ = limit  # Unused - doctype removed
    return {"synced": 0, "created": 0, "updated": 0, "deprecated": True, "message": "Employee Profile doctype removed - use ERPNext Employee directly"}




@frappe.whitelist()
def setup_minimal_benefit_structure_and_assign(
    employee: str,
    company: Optional[str] = None,
    structure_name: Optional[str] = None,
    component_name: Optional[str] = None,
    max_benefits: Optional[float] = None,
    currency: Optional[str] = None,
) -> Dict:
    """Create a minimal Salary Structure with one flexible benefit component and assign it to employee.

    - Ensures a Salary Component exists (flexible benefit, payable against benefit claim)
    - Creates/Submits a Salary Structure with max_benefits > 0 and adds the component
    - Creates/Submits a Salary Structure Assignment for the given employee starting today

    Returns: {"salary_structure": name, "salary_component": comp_name, "assignment": ssa_name}
    """
    emp_company = company or frappe.db.get_value("Employee", employee, "company") or _get_default_company()
    if not emp_company:
        frappe.throw(_("No Company found for Employee {0}").format(employee))

    comp_name = (component_name or "Flexi Benefit").strip()
    default_max = max_benefits or 10000

    # Ensure Salary Component
    if not frappe.db.exists("Salary Component", comp_name):
        sc = frappe.new_doc("Salary Component")
        sc.salary_component = comp_name
        sc.type = "Earning"
        sc.is_flexible_benefit = 1
        sc.pay_against_benefit_claim = 1
        sc.max_benefit_amount = default_max
        sc.save(ignore_permissions=True)
    else:
        sc = frappe.get_doc("Salary Component", comp_name)
        updated = False
        if getattr(sc, "type", None) != "Earning":
            sc.type = "Earning"
            updated = True
        if getattr(sc, "is_flexible_benefit", 0) != 1:
            sc.is_flexible_benefit = 1
            updated = True
        if getattr(sc, "pay_against_benefit_claim", 0) != 1:
            sc.pay_against_benefit_claim = 1
            updated = True
        if not getattr(sc, "max_benefit_amount", None) or sc.max_benefit_amount <= 0:
            sc.max_benefit_amount = default_max
            updated = True
        if updated:
            sc.save(ignore_permissions=True)

    # Ensure Salary Structure
    struct_name = (structure_name or f"DEFAULT BENEFITS - {emp_company}").strip()
    ss = None
    if frappe.db.exists("Salary Structure", struct_name):
        ss = frappe.get_doc("Salary Structure", struct_name)
        changed = False
        if not ss.max_benefits or ss.max_benefits <= 0:
            ss.max_benefits = default_max
            changed = True
        if not any(getattr(e, "salary_component", None) == comp_name for e in (ss.earnings or [])):
            ss.append("earnings", {"salary_component": comp_name, "is_flexible_benefit": 1})
            changed = True
        if ss.docstatus == 0:
            if changed:
                ss.save(ignore_permissions=True)
            ss.submit()
        elif changed:
            ss.save(ignore_permissions=True)
    else:
        ss = frappe.new_doc("Salary Structure")
        # Try to name it as requested; if autoname applies, the framework will override
        ss.name = struct_name
        ss.company = emp_company
        ss.currency = currency or frappe.db.get_value("Company", emp_company, "default_currency")
        ss.max_benefits = default_max
        ss.append("earnings", {"salary_component": comp_name, "is_flexible_benefit": 1})
        ss.save(ignore_permissions=True)
        ss.submit()

    # Create SSA if not exists (submitted)
    from datetime import date as _date

    ssa_name = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee, "salary_structure": ss.name, "docstatus": 1},
        "name",
    )
    if not ssa_name:
        ssa = frappe.new_doc("Salary Structure Assignment")
        ssa.employee = employee
        ssa.company = emp_company
        ssa.salary_structure = ss.name
        ssa.currency = ss.currency
        ssa.from_date = _date.today().isoformat()
        ssa.insert(ignore_permissions=True)
        ssa.submit()
        ssa_name = ssa.name

    return {"salary_structure": ss.name, "salary_component": comp_name, "assignment": ssa_name}
