import json
from datetime import date
from typing import Any, Dict, List, Tuple

import frappe
from frappe.model.document import Document

from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class PayoutSummaryReport(Document):
    def before_insert(self):
        self._ensure_period_window()

    def validate(self):
        self._ensure_period_window()

    def _ensure_period_window(self):
        # Default to last full month if Monthly and fields are missing
        if not getattr(self, "period_type", None):
            self.period_type = "Monthly"

        if self.period_type == "Monthly":
            today = frappe.utils.getdate()
            if not self.month or not self.year:
                # use previous month as default window
                prev = frappe.utils.add_months(today, -1)
                self.month = MONTHS[prev.month - 1]
                self.year = prev.year
            # compute first and last day of selected month
            month_idx = MONTHS.index(self.month) + 1 if self.month in MONTHS else today.month
            first_day = frappe.utils.get_first_day(date(int(self.year), month_idx, 1))
            last_day = frappe.utils.get_last_day(first_day)
            self.date_from = first_day
            self.date_to = last_day
        else:
            # Custom - ensure dates are present
            if not self.date_from or not self.date_to:
                today = frappe.utils.getdate()
                self.date_from = self.date_from or today
                self.date_to = self.date_to or today

    def run_generation(self):
        df = frappe.utils.getdate(self.date_from)
        dt = frappe.utils.getdate(self.date_to)

        totals, rows = aggregate_payouts(df, dt, self.period_type)

        # Totals
        self.total_beneficiaries_paid = totals.get("total_beneficiaries_paid", 0)
        self.total_gross_payout = totals.get("total_gross_payout", 0.0)
        self.total_deductions = totals.get("total_deductions", 0.0)
        self.total_net_payout = totals.get("total_net_payout", 0.0)
        self.exceptions_count = totals.get("exceptions_count", 0)

        # Metadata
        self.generated_at = frappe.utils.now_datetime()
        self.generated_by = frappe.session.user

        # Snapshot JSON
        self.rows_json = json.dumps(rows)

        # Child table rows (truncate to 2000 for safety)
        self.set("payout_rows", [])
        for r in rows[:2000]:
            self.append("payout_rows", {
                "beneficiary_number": r.get("beneficiary_number"),
                "beneficiary_name": r.get("beneficiary_name"),
                "nrc_number": r.get("nrc_number"),
                "employee_number": r.get("employee_number"),
                "employer_code": r.get("employer_code"),
                "employer_name": r.get("employer_name"),
                "benefit_type": r.get("benefit_type"),
                "opening_balance": r.get("opening_balance", 0.0),
                "gross_payout": r.get("gross_payout", 0.0),
                "deductions_total": r.get("deductions_total", 0.0),
                "net_payout": r.get("net_payout", 0.0),
                "closing_balance": r.get("closing_balance", 0.0),
                "deduction_breakdown_json": json.dumps(r.get("deduction_breakdown", {})),
                "exceptions_flag": 1 if r.get("exceptions") else 0,
                "exception_codes": ",".join(r.get("exception_codes", [])) if r.get("exception_codes") else "",
                "exception_note": r.get("exception_note", ""),
                "payment_count": r.get("payment_count", 0),
            })

        # HTML table and a tiny chart
        self.report_html = build_rows_table(rows)
        self.chart_json = json.dumps({
            "type": "bar",
            "data": {
                "labels": ["Gross", "Deductions", "Net"],
                "datasets": [{
                    "name": "Totals (ZMW)",
                    "values": [
                        float(self.total_gross_payout or 0),
                        float(self.total_deductions or 0),
                        float(self.total_net_payout or 0)
                    ]
                }]
            }
        })

        # Alias summary fields (as requested): beneficiariesCount, payrollMonth, totalPaid
        self.beneficiaries_count = int(self.total_beneficiaries_paid or 0)
        self.total_paid = float(self.total_net_payout or 0)
        if (self.period_type or "Monthly") == "Monthly":
            self.payroll_month = f"{self.month} {self.year}"
        else:
            self.payroll_month = f"{self.date_from}..{self.date_to}"

        # Dependant summary (Son/Daughter/Husband/Wife) for the selected window
        pm_label = self.payroll_month
        dep_rows = build_dependant_summary(rows, pm_label)
        self.set("dependant_summary", [])
        for d in dep_rows:
            self.append("dependant_summary", d)


@frappe.whitelist()
def generate_report(name: str) -> Dict[str, Any]:
    doc = frappe.get_doc("Payout Summary Report", name)
    doc.run_generation()
    doc.save(ignore_permissions=True)
    return {
        "name": doc.name,
        "period_type": doc.period_type,
        "date_from": str(doc.date_from),
        "date_to": str(doc.date_to),
        "total_beneficiaries_paid": doc.total_beneficiaries_paid,
        "total_gross_payout": doc.total_gross_payout,
        "total_deductions": doc.total_deductions,
        "total_net_payout": doc.total_net_payout,
        "exceptions_count": doc.exceptions_count,
        "generated_at": doc.generated_at,
    }


@frappe.whitelist()
def create_and_generate(period_type: str = "Monthly", month: str | None = None, year: int | None = None,
                        date_from: str | None = None, date_to: str | None = None, title: str | None = None) -> Dict[str, Any]:
    # Helper to create and generate quickly (useful for smoke tests and schedulers later)
    kwargs: Dict[str, Any] = {"doctype": "Payout Summary Report", "period_type": period_type}
    if period_type == "Monthly":
        # Default to previous month if not provided
        today = frappe.utils.getdate()
        prev = frappe.utils.add_months(today, -1)
        kwargs["month"] = month or MONTHS[prev.month - 1]
        kwargs["year"] = int(year or prev.year)
    else:
        df, dt = _ensure_dates_for_period(date_from, date_to)
        kwargs["date_from"], kwargs["date_to"] = df, dt
    kwargs["title"] = title or f"Payouts {kwargs.get('month', '')} {kwargs.get('year', '')}".strip()

    doc = frappe.get_doc(kwargs)
    doc.insert(ignore_permissions=True)
    doc.run_generation()
    doc.save(ignore_permissions=True)
    return {
        "name": doc.name,
        "period_type": doc.period_type,
        "date_from": str(doc.date_from),
        "date_to": str(doc.date_to),
        "total_beneficiaries_paid": doc.total_beneficiaries_paid,
        "total_gross_payout": doc.total_gross_payout,
        "total_deductions": doc.total_deductions,
        "total_net_payout": doc.total_net_payout,
        "exceptions_count": doc.exceptions_count,
    }


def _ensure_dates_for_period(date_from: str | None, date_to: str | None) -> Tuple[Any, Any]:
    if date_from and date_to:
        return frappe.utils.getdate(date_from), frappe.utils.getdate(date_to)
    today = frappe.utils.getdate()
    return today, today


def aggregate_payouts(date_from, date_to, period_type: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Aggregate payouts from ERPNext (Payment Status) and CoreBusiness (CBS).
    Returns (totals, rows list) where rows contain per-beneficiary summary.
    """
    rows_by_beneficiary: Dict[str, Dict[str, Any]] = {}
    exceptions_count = 0

    # 1) ERPNext source: Payment Status
    if frappe.db.table_exists("Payment Status"):
        erp_rows = frappe.get_all(
            "Payment Status",
            filters={
                "status": "Paid",
                "payment_date": ["between", [date_from, date_to]],
            },
            fields=["name", "payment_id", "payment_date", "amount", "beneficiary", "reference_number", "currency"],
            limit=5000,
        )
        for p in erp_rows:
            _apply_payment_to_rows(rows_by_beneficiary, _normalize_erp_payment(p))

    # 2) CBS source: via integration service
    try:
        cbs = CoreBusinessIntegrationService()
        cbs_rows = cbs.get_payments(date_from=str(date_from), date_to=str(date_to), status="Paid", limit=5000) or []
        for p in cbs_rows:
            _apply_payment_to_rows(rows_by_beneficiary, _normalize_cbs_payment(p))
    except Exception as e:
        frappe.log_error(f"CBS payouts aggregation error: {str(e)}", "Payout Summary Report")

    # Enrich with Beneficiary + Employer & compute exceptions
    totals = {"total_beneficiaries_paid": 0, "total_gross_payout": 0.0, "total_deductions": 0.0, "total_net_payout": 0.0}
    out_rows: List[Dict[str, Any]] = []

    for key, r in rows_by_beneficiary.items():
        enrich_beneficiary_and_employer(r)
        compute_balances_and_exceptions(r, period_type)
        if r.get("exceptions"):
            exceptions_count += 1
        totals["total_beneficiaries_paid"] += 1
        totals["total_gross_payout"] += float(r.get("gross_payout", 0) or 0)
        totals["total_deductions"] += float(r.get("deductions_total", 0) or 0)
        totals["total_net_payout"] += float(r.get("net_payout", 0) or 0)
        out_rows.append(r)

    totals["exceptions_count"] = exceptions_count
    # Sort rows by net payout desc for readability
    out_rows.sort(key=lambda x: float(x.get("net_payout", 0) or 0), reverse=True)
    return totals, out_rows


def _apply_payment_to_rows(agg: Dict[str, Dict[str, Any]], pay: Dict[str, Any]):
    if not pay:
        return
    key = pay.get("beneficiary_key") or pay.get("beneficiary_number") or pay.get("beneficiary") or pay.get("nrc_number") or "UNKNOWN"
    row = agg.setdefault(key, {
        "beneficiary_key": key,
        "beneficiary_number": None,
        "beneficiary_name": None,
        "nrc_number": None,
        "employee_number": None,
        "employer_code": None,
        "employer_name": None,
        "benefit_type": None,
        "opening_balance": 0.0,
        "gross_payout": 0.0,
        "deductions_total": 0.0,
        "net_payout": 0.0,
        "closing_balance": 0.0,
        "deduction_breakdown": {},
        "exceptions": False,
        "exception_codes": [],
        "exception_note": "",
        "payment_count": 0,
    })

    gross = float(pay.get("gross_amount", 0) or 0)
    net = float(pay.get("net_amount", pay.get("amount", 0) or 0))
    ded = float(pay.get("deductions_total", 0) or 0)
    # If only net is present, treat gross = net + deductions when sensible
    if not gross and (net or ded):
        gross = max(0.0, net + ded)

    row["gross_payout"] += gross
    row["deductions_total"] += ded
    row["net_payout"] += net
    row["payment_count"] += 1

    # carry forward obvious identity hints
    for f in ("beneficiary_number", "nrc_number", "beneficiary_name"):
        if pay.get(f) and not row.get(f):
            row[f] = pay.get(f)

    # deduction breakdown merge (best-effort)
    if isinstance(pay.get("deduction_breakdown"), dict):
        for k, v in pay["deduction_breakdown"].items():
            row["deduction_breakdown"][k] = float(row["deduction_breakdown"].get(k, 0) or 0) + float(v or 0)


def _normalize_erp_payment(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "payment_id": p.get("payment_id") or p.get("name"),
        "amount": p.get("amount"),  # treat as net (ERP Payment Status has single amount)
        "currency": p.get("currency"),
        "date": p.get("payment_date"),
        "beneficiary": p.get("beneficiary"),
        "reference": p.get("reference_number"),
        "beneficiary_key": p.get("beneficiary"),
        # ERP row doesn't track deductions; set to 0
        "deductions_total": 0.0,
    }


def _normalize_cbs_payment(p: Dict[str, Any]) -> Dict[str, Any]:
    # Flexible mapping for CBS responses (handles common shapes)
    deductions_total = 0.0
    breakdown = {}
    if isinstance(p.get("deductions"), list):
        for d in p["deductions"]:
            amt = float(d.get("amount", 0) or 0)
            code = (d.get("type") or d.get("code") or "other").lower()
            deductions_total += amt
            breakdown[code] = float(breakdown.get(code, 0) or 0) + amt
    elif isinstance(p.get("deductions"), dict):
        for k, v in p["deductions"].items():
            amt = float(v or 0)
            deductions_total += amt
            breakdown[k] = float(breakdown.get(k, 0) or 0) + amt

    return {
        "payment_id": p.get("payment_id") or p.get("id") or p.get("reference") or p.get("transaction_id"),
        "gross_amount": p.get("gross_amount"),
        "net_amount": p.get("net_amount") or p.get("amount"),
        "deductions_total": deductions_total or p.get("deductions_total", 0),
        "date": p.get("date") or p.get("payment_date"),
        "beneficiary_number": p.get("beneficiary_number") or p.get("beneficiary_id"),
        "nrc_number": p.get("nrc") or p.get("nrc_number"),
        "beneficiary": p.get("beneficiary_name"),
        "beneficiary_key": p.get("beneficiary_number") or p.get("beneficiary_id") or p.get("nrc") or p.get("nrc_number") or p.get("beneficiary_name"),
        "deduction_breakdown": breakdown,
    }


def enrich_beneficiary_and_employer(row: Dict[str, Any]):
    """Attach beneficiary + employer metadata to an aggregated payout row.

    We try multiple keys in order of reliability:
    - beneficiary_number (explicit key)
    - nrc_number
    - beneficiary_name (full_name contains)
    - beneficiary_key (generic key coming from ERP/CBS payments)

    NOTE: Beneficiary Profile and Employee Profile doctypes have been removed.
    This function now returns early without enrichment.
    """
    # Beneficiary Profile doctype has been removed - skip enrichment
    if not frappe.db.table_exists("tabBeneficiary Profile"):
        return

    bp = None
    if row.get("beneficiary_number"):
        bp = frappe.get_all(
            "Beneficiary Profile",
            filters={"beneficiary_number": row["beneficiary_number"]},
            fields=[
                "beneficiary_number",
                "nrc_number",
                "first_name",
                "last_name",
                "full_name",
                "employee_number",
                "monthly_benefit_amount",
                "benefit_type",
                "benefit_status",
                "gender",
                "relationship_to_employee",
            ],
            limit=1,
        )
    if not bp and row.get("nrc_number"):
        bp = frappe.get_all(
            "Beneficiary Profile",
            filters={"nrc_number": row["nrc_number"]},
            fields=[
                "beneficiary_number",
                "nrc_number",
                "first_name",
                "last_name",
                "full_name",
                "employee_number",
                "monthly_benefit_amount",
                "benefit_type",
                "benefit_status",
                "gender",
                "relationship_to_employee",
            ],
            limit=1,
        )
    if not bp and row.get("beneficiary_name"):
        bp = frappe.get_all(
            "Beneficiary Profile",
            filters={"full_name": ["like", f"%{row['beneficiary_name']}%"]},
            fields=[
                "beneficiary_number",
                "nrc_number",
                "first_name",
                "last_name",
                "full_name",
                "employee_number",
                "monthly_benefit_amount",
                "benefit_type",
                "benefit_status",
                "gender",
                "relationship_to_employee",
            ],
            limit=1,
        )
    # Fallback: try generic beneficiary_key, which may hold a number, NRC or name
    if not bp and row.get("beneficiary_key"):
        key = row["beneficiary_key"]
        bp = frappe.get_all(
            "Beneficiary Profile",
            filters={"beneficiary_number": key},
            fields=[
                "beneficiary_number",
                "nrc_number",
                "first_name",
                "last_name",
                "full_name",
                "employee_number",
                "monthly_benefit_amount",
                "benefit_type",
                "benefit_status",
                "gender",
                "relationship_to_employee",
            ],
            limit=1,
        )
        if not bp:
            bp = frappe.get_all(
                "Beneficiary Profile",
                filters={"nrc_number": key},
                fields=[
                    "beneficiary_number",
                    "nrc_number",
                    "first_name",
                    "last_name",
                    "full_name",
                    "employee_number",
                    "monthly_benefit_amount",
                    "benefit_type",
                    "benefit_status",
                    "gender",
                    "relationship_to_employee",
                ],
                limit=1,
            )
        if not bp:
            bp = frappe.get_all(
                "Beneficiary Profile",
                filters={"full_name": ["like", f"%{key}%"]},
                fields=[
                    "beneficiary_number",
                    "nrc_number",
                    "first_name",
                    "last_name",
                    "full_name",
                    "employee_number",
                    "monthly_benefit_amount",
                    "benefit_type",
                    "benefit_status",
                    "gender",
                    "relationship_to_employee",
                ],
                limit=1,
            )

    bp_doc = bp[0] if bp else None
    if bp_doc:
        row["beneficiary_number"] = row.get("beneficiary_number") or bp_doc.get("beneficiary_number")
        row["nrc_number"] = row.get("nrc_number") or bp_doc.get("nrc_number")
        row["beneficiary_name"] = row.get("beneficiary_name") or (
            bp_doc.get("full_name")
            or f"{bp_doc.get('first_name','')} {bp_doc.get('last_name','')}"
        ).strip()
        row["benefit_type"] = row.get("benefit_type") or bp_doc.get("benefit_type")
        row["monthly_benefit_amount"] = bp_doc.get("monthly_benefit_amount") or 0.0
        row["benefit_status"] = bp_doc.get("benefit_status")
        row["employee_number"] = row.get("employee_number") or bp_doc.get("employee_number")
        # capture attributes needed for dependant classification
        row["gender"] = row.get("gender") or bp_doc.get("gender")
        row["relationship_to_employee"] = row.get("relationship_to_employee") or bp_doc.get(
            "relationship_to_employee"
        )

    # Employer via ERPNext Employee (Employee Profile has been removed)
    if row.get("employee_number") and frappe.db.table_exists("tabEmployee"):
        emp = frappe.get_all("Employee", filters={"name": row["employee_number"]},
                             fields=["company", "employee_name"], limit=1)
        if emp:
            row["employer_code"] = row.get("employer_code") or emp[0].get("company")
            row["employer_name"] = row.get("employer_name") or emp[0].get("company")




def compute_balances_and_exceptions(row: Dict[str, Any], period_type: str):
    # Placeholder for CBS arrears ledger integration (Phase 3). Keep balances at 0 for now.
    row["opening_balance"] = float(row.get("opening_balance", 0) or 0)
    row["closing_balance"] = float(row.get("closing_balance", 0) or 0)

    # Exceptions
    exception_codes: List[str] = []

    # Missing payment if active beneficiary with positive entitlement but no payout
    expected = None
    if row.get("benefit_status") == "Active" and (row.get("monthly_benefit_amount") or 0) > 0:
        if period_type == "Monthly":
            expected = float(row.get("monthly_benefit_amount") or 0)
            if float(row.get("net_payout", 0) or 0) <= 0:
                exception_codes.append("MISSING_PAYMENT")
        # Custom windows: skip expectation until rules are finalized

    if expected is not None:
        net = float(row.get("net_payout", 0) or 0)
        if net < expected:
            exception_codes.append("UNDER_PAID")
        if net > expected:
            exception_codes.append("OVER_PAID")

    if float(row.get("deductions_total", 0) or 0) > float(row.get("gross_payout", 0) or 0):
        exception_codes.append("DEDUCTION_EXCEEDS_GROSS")
    if float(row.get("net_payout", 0) or 0) < 0:
        exception_codes.append("NEGATIVE_NET")
    if int(row.get("payment_count", 0) or 0) > 1:
        exception_codes.append("MULTIPLE_PAYMENTS")

    row["exceptions"] = bool(exception_codes)
    row["exception_codes"] = exception_codes
    if exception_codes and not row.get("exception_note"):
        row["exception_note"] = ", ".join(exception_codes)


def build_rows_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return '<div class="text-muted">No payouts found in this period.</div>'
    header = (
        "<table class=\"table table-bordered table-sm\">"
        "<thead><tr>"
        "<th>Beneficiary</th><th>NRC</th><th>Employer</th>"
        "<th>Gross</th><th>Deductions</th><th>Net</th><th>Payments</th><th>Exceptions</th>"
        "</tr></thead><tbody>"
    )
    body_parts: List[str] = []
    for r in rows[:500]:
        body_parts.append(
            f"<tr><td>{frappe.utils.escape_html(r.get('beneficiary_name') or r.get('beneficiary_number') or '')}</td>"
            f"<td>{frappe.utils.escape_html(r.get('nrc_number') or '')}</td>"
            f"<td>{frappe.utils.escape_html((r.get('employer_name') or r.get('employer_code') or '') )}</td>"
            f"<td style='text-align:right'>{frappe.utils.fmt_money(r.get('gross_payout') or 0)}</td>"
            f"<td style='text-align:right'>{frappe.utils.fmt_money(r.get('deductions_total') or 0)}</td>"
            f"<td style='text-align:right'>{frappe.utils.fmt_money(r.get('net_payout') or 0)}</td>"
            f"<td style='text-align:center'>{int(r.get('payment_count') or 0)}</td>"
            f"<td>{frappe.utils.escape_html(','.join(r.get('exception_codes') or []))}</td></tr>"
        )
    return header + "".join(body_parts) + "</tbody></table>"

# --- Dependant summarization helpers ---

def _map_dependant_relation(relationship: Any, gender: Any) -> str | None:
    r = (relationship or "").strip().lower()
    g = (gender or "").strip().lower()
    if r == "child":
        if g == "male":
            return "Son"
        if g == "female":
            return "Daughter"
        return None
    if r == "spouse":
        if g == "male":
            return "Husband"
        if g == "female":
            return "Wife"
        return None
    return None


def build_dependant_summary(rows: List[Dict[str, Any]], payroll_month_label: str) -> List[Dict[str, Any]]:
    allowed = ("Son", "Daughter", "Husband", "Wife")
    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows or []:
        rel = _map_dependant_relation(r.get("relationship_to_employee"), r.get("gender"))
        if rel not in allowed:
            continue
        a = agg.setdefault(rel, {"total_amount": 0.0, "total_count": 0})
        a["total_amount"] = float(a.get("total_amount", 0) or 0) + float(r.get("net_payout", 0) or 0)
        a["total_count"] = int(a.get("total_count", 0) or 0) + 1

    out: List[Dict[str, Any]] = []
    for rel, a in agg.items():
        out.append({
            "dependant_relation": rel,
            "payroll_month": payroll_month_label,
            "total_amount": float(a.get("total_amount", 0) or 0),
            "total_count": int(a.get("total_count", 0) or 0),
        })
    order = {"Husband": 0, "Wife": 1, "Son": 2, "Daughter": 3}
    out.sort(key=lambda x: order.get(x.get("dependant_relation"), 99))
    return out



# ============ Phase 3: AI, PDF, Email ============


@frappe.whitelist()
def get_ai_insights(name: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for a Payout Summary Report.

    Mirrors the Claims Status Report Antoine integration pattern:
    - builds a compact JSON context with the current window
    - includes high-level payout KPIs and a sample of beneficiary rows
    - adds a short history of previous payout reports
    - passes everything to Antoine via EnhancedAIService
    """

    doc = frappe.get_doc("Payout Summary Report", name)

    # Recent payout reports with the same period_type for trend analysis
    history = frappe.get_all(
        "Payout Summary Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "total_beneficiaries_paid",
            "total_gross_payout",
            "total_deductions",
            "total_net_payout",
            "exceptions_count",
        ],
        order_by="date_from desc",
        limit=12,
    )

    # Re-aggregate using the latest payout logic so Antoine sees up-to-date
    # totals and a fresh sample of payout rows.
    try:
        totals, rows = aggregate_payouts(doc.date_from, doc.date_to, doc.period_type)
    except Exception:
        totals = {
            "total_beneficiaries_paid": int(doc.total_beneficiaries_paid or 0),
            "total_gross_payout": float(doc.total_gross_payout or 0),
            "total_deductions": float(doc.total_deductions or 0),
            "total_net_payout": float(doc.total_net_payout or 0),
            "exceptions_count": int(doc.exceptions_count or 0),
        }
        try:
            rows = json.loads(doc.rows_json or "[]")
        except Exception:
            rows = []

    context = {
        "window": {
            "from": str(doc.date_from),
            "to": str(doc.date_to),
            "period_type": doc.period_type,
            "payroll_month": getattr(doc, "payroll_month", None),
        },
        "current": {
            "total_beneficiaries_paid": totals.get("total_beneficiaries_paid", int(doc.total_beneficiaries_paid or 0)),
            "total_gross_payout": totals.get("total_gross_payout", float(doc.total_gross_payout or 0)),
            "total_deductions": totals.get("total_deductions", float(doc.total_deductions or 0)),
            "total_net_payout": totals.get("total_net_payout", float(doc.total_net_payout or 0)),
            "exceptions_count": totals.get("exceptions_count", int(doc.exceptions_count or 0)),
        },
        "sample_rows": rows[:200],
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_payout_summary_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Payout Summary Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


def _build_pdf_html(doc: "PayoutSummaryReport") -> str:
    style = """
    <style>
    body { font-family: Inter, Arial, sans-serif; font-size:12px; color:#1f2937; }
    h1 { font-size: 18px; margin: 0 0 4px 0; }
    h2 { font-size: 14px; margin: 16px 0 8px 0; }
    .meta { color:#6b7280; font-size:11px; }
    .cards { display:flex; gap:8px; margin:12px 0; flex-wrap: wrap; }
    .card { border:1px solid #e5e7eb; border-radius:6px; padding:10px; min-width:150px; }
    .label { font-size:11px; color:#6b7280; }
    .value { font-size:16px; font-weight:600; }
    .table { margin-top:10px; }
    </style>
    """
    gen_at = getattr(doc, "generated_at", None) or frappe.utils.now_datetime()
    header = f"""
    <div>
      <h1>WCFCB Payout Summary Report</h1>
      <div class=meta>
        Period: {frappe.utils.formatdate(doc.date_from)} to {frappe.utils.formatdate(doc.date_to)}
        &nbsp;&nbsp;|&nbsp;&nbsp; Type: {frappe.utils.escape_html(doc.period_type)}
        &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {frappe.utils.format_datetime(gen_at)}
      </div>
    </div>
    """
    cards = f"""
    <div class=cards>
      <div class=card><div class=label>Beneficiaries Count</div><div class=value>{getattr(doc, 'beneficiaries_count', getattr(doc, 'total_beneficiaries_paid', 0)) or 0}</div></div>
      <div class=card><div class=label>Payroll Month</div><div class=value>{frappe.utils.escape_html(getattr(doc, 'payroll_month', '') or (str(getattr(doc, 'month','')) + ' ' + str(getattr(doc,'year',''))))}</div></div>
      <div class=card><div class=label>Total Paid (ZMW)</div><div class=value>{frappe.utils.fmt_money(getattr(doc, 'total_paid', getattr(doc, 'total_net_payout', 0)) or 0)}</div></div>
    </div>
    """
    # Dependant breakdown table
    dep_rows = getattr(doc, 'dependant_summary', [])
    dep_html_body = ''
    for d in dep_rows:
        dep_html_body += (
            f"<tr>"
            f"<td>{frappe.utils.escape_html(d.get('dependant_relation') or '')}</td>"
            f"<td style='text-align:center'>{int(d.get('total_count') or 0)}</td>"
            f"<td style='text-align:right'>{frappe.utils.fmt_money(d.get('total_amount') or 0)}</td>"
            f"<td>{frappe.utils.escape_html(d.get('payroll_month') or '')}</td>"
            f"</tr>"
        )
    if not dep_html_body:
        dep_table = '<div class="text-muted">No dependant breakdown available.</div>'
    else:
        dep_table = (
            "<h2>Dependant Breakdown</h2>"
            "<div class=table>"
            "<table class=\"table table-bordered table-sm\">"
            "<thead><tr><th>Relation</th><th>Total Count</th><th>Total Amount (ZMW)</th><th>Payroll Month</th></tr></thead>"
            f"<tbody>{dep_html_body}</tbody></table></div>"
        )

    html_table = getattr(doc, 'report_html', None) or '<div class="text-muted">No payouts in this period.</div>'
    table = f"""
    <h2>Beneficiary Payouts</h2>
    <div class=table>{html_table}</div>
    """
    return style + header + cards + dep_table + table


def _build_pdf_bytes(doc: "PayoutSummaryReport") -> tuple[str, bytes]:
    from frappe.utils.pdf import get_pdf
    html = _build_pdf_html(doc)
    # Use month name in filename when Monthly
    if (doc.period_type or "Monthly") == "Monthly":
        fname = f"Payout_Summary_{getattr(doc, 'month', '')}_{getattr(doc, 'year', '')}.pdf".replace(' ', '_')
    else:
        fname = f"Payout_Summary_{doc.date_from}_{doc.date_to}.pdf"
    return fname, get_pdf(html)



@frappe.whitelist()
def generate_pdf(name: str) -> Dict[str, Any]:
    doc = frappe.get_doc("Payout Summary Report", name)
    fname, pdf_bytes = _build_pdf_bytes(doc)
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "attached_to_doctype": "Payout Summary Report",
        "attached_to_name": doc.name,
        "is_private": 1,
        "content": pdf_bytes,
    })
    file_doc.save(ignore_permissions=True)
    return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}


def _get_role_emails(roles: List[str]) -> List[str]:
    emails: List[str] = []
    for role in roles or []:
        try:
            role_users = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"], limit=1000)
            for ru in role_users:
                user = frappe.db.get_value("User", ru["parent"], ["name", "email", "enabled"], as_dict=True)
                if user and int(user.get("enabled") or 0) == 1:
                    emails.append(user.get("email") or user.get("name"))
        except Exception:
            continue
    # Deduplicate
    uniq = []
    for e in emails:
        if e and e not in uniq:
            uniq.append(e)
    return uniq


@frappe.whitelist()
def email_report(name: str, recipients: List[str] | None = None, roles: List[str] | None = None) -> Dict[str, Any]:
    doc = frappe.get_doc("Payout Summary Report", name)
    fname, pdf_bytes = _build_pdf_bytes(doc)
    recips = recipients or _get_role_emails(roles or ["WCFCB Manager", "WCFCB Staff"])
    subject = f"WCFCB Payout Summary - {frappe.utils.escape_html(doc.period_type)} ({frappe.utils.formatdate(doc.date_from)} to {frappe.utils.formatdate(doc.date_to)})"
    message = f"""
        Dear Team,<br><br>
        Please find attached the {frappe.utils.escape_html(doc.period_type)} Payout Summary Report for the period
        {frappe.utils.formatdate(doc.date_from)} to {frappe.utils.formatdate(doc.date_to)}.<br><br>
        Beneficiaries Paid: <b>{doc.total_beneficiaries_paid or 0}</b>
        &nbsp; Gross: <b>{frappe.utils.fmt_money(doc.total_gross_payout or 0)}</b>
        &nbsp; Deductions: <b>{frappe.utils.fmt_money(doc.total_deductions or 0)}</b>
        &nbsp; Net: <b>{frappe.utils.fmt_money(doc.total_net_payout or 0)}</b>
        &nbsp; Exceptions: <b>{doc.exceptions_count or 0}</b>
        <br><br>Regards,<br>WCFCB Assistant CRM
    """
    frappe.sendmail(
        recipients=recips,
        subject=subject,
        message=message,
        attachments=[{"fname": fname, "fcontent": pdf_bytes}]
    )
    return {"sent_to": recips, "subject": subject}



# ============ Phase 4: Scheduler + Permissions ============

def _is_first_business_day(d: date) -> bool:
    # Monday=0..Sunday=6
    wd = d.weekday()
    first = frappe.utils.get_first_day(d)
    # find first weekday (Mon-Fri) of this month
    first_bd = first
    while first_bd.weekday() > 4:  # skip Sat(5), Sun(6)
        first_bd = frappe.utils.add_days(first_bd, 1)
    return d == first_bd


def _previous_month(d: date) -> tuple[str, int]:
    prev = frappe.utils.add_months(d, -1)
    return MONTHS[prev.month - 1], prev.year


def _safe_create_and_email_prev_month():
    today = frappe.utils.getdate()
    mon, yr = _previous_month(today)
    try:
        res = create_and_generate(period_type="Monthly", month=mon, year=yr, title=f"Payouts {mon} {yr}")
        name = res.get("name")
        if name:
            # Attach PDF and email to finance roles
            generate_pdf(name)  # ensures File attachment
            email_report(name)
    except Exception as e:
        frappe.log_error(f"Payout monthly scheduler failed: {str(e)}", "Payout Summary Scheduler")


def schedule_monthly_payout_summary():
    """Run every weekday morning; if today is the first business day, generate previous month's report and email it."""
    today = frappe.utils.getdate()
    if _is_first_business_day(today):
        _safe_create_and_email_prev_month()


# ---- Permissions: restrict Employers to their own rows ----

def _get_user_employer_codes(user: str) -> List[str]:
    """Get employer codes for a user.

    NOTE: Employer Profile doctype has been removed. Using Customer instead.
    """
    try:
        user_doc = frappe.get_doc("User", user)
        emails_to_check = list(filter(None, [user_doc.email, user_doc.name]))
    except Exception:
        emails_to_check = [user]
    codes = []
    # Use ERPNext Customer instead of Employer Profile (which has been removed)
    if frappe.db.table_exists("tabCustomer"):
        customers = frappe.get_all("Customer", filters={
            "customer_type": "Company",
            "email_id": ["in", emails_to_check]
        }, fields=["name"], limit=100)
        for c in customers:
            if c.get("name") and c["name"] not in codes:
                codes.append(c["name"])
    return codes


def _has_any_role(user, role_names):
    user = user or frappe.session.user
    try:
        roles = set(frappe.get_roles(user))
    except Exception:
        roles = set()
    return any(r in roles for r in role_names)


def get_permission_query_conditions(user: str) -> str | None:
    if not user:
        user = frappe.session.user
    # Full access roles
    if _has_any_role(user, ["System Manager", "WCFCB Manager", "WCFCB Staff"]):
        return None
    # Employer scoping
    if _has_any_role(user, ["Employer"]):
        codes = _get_user_employer_codes(user)
        if not codes:
            return "1=0"
        # Quote safely
        quoted = ", ".join(["'" + c.replace("'", "''") + "'" for c in codes])
        return (
            "exists (select 1 from `tabPayout Summary Row` r "
            "where r.parent = `tabPayout Summary Report`.name and r.employer_code in (" + quoted + "))"
        )
    return None


def has_permission(doc: Document, user: str = None) -> bool:
    user = user or frappe.session.user
    if _has_any_role(user, ["System Manager", "WCFCB Manager", "WCFCB Staff"]):
        return True
    if _has_any_role(user, ["Employer"]):
        codes = _get_user_employer_codes(user)
        if not codes:
            return False
        for r in getattr(doc, "payout_rows", []) or []:
            if r.get("employer_code") in codes:
                return True
        return False
    return True
