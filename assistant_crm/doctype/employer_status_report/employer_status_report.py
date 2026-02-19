import json
from datetime import date, timedelta
from typing import Dict, Any, List, Tuple, Optional

import frappe
from frappe.model.document import Document


class EmployerStatusReport(Document):
    @frappe.whitelist()
    def run_generation(self):
        """Aggregate metrics and populate fields. Safe even if dependent doctypes don't exist."""
        df = frappe.utils.getdate(self.date_from)
        dt = frappe.utils.getdate(self.date_to)

        summary = _aggregate_employer_summary(df, dt)
        contrib = _aggregate_contributions(df, dt)
        cases = _aggregate_cases(df, dt)
        top_claims = _aggregate_top_claims(df, dt)

        # Set employer status fields
        self.total_employers = summary.get("total_employers", 0)
        self.active_count = summary.get("active", 0)
        self.inactive_count = summary.get("inactive", 0)
        self.suspended_count = summary.get("suspended", 0)
        self.pending_count = summary.get("pending", 0)
        self.blacklisted_count = summary.get("blacklisted", 0)
        self.compliant_count = summary.get("compliant", 0)
        self.non_compliant_count = summary.get("non_compliant", 0)
        self.overdue_contributions_count = contrib.get("overdue_count", 0)

        # Set contribution fields
        self.total_expected_contributions = contrib.get("expected_total", 0.0)
        self.total_paid_contributions = contrib.get("paid_total", 0.0)
        self.total_outstanding_contributions = contrib.get("outstanding_total", 0.0)

        # Calculate collection rate
        expected = float(self.total_expected_contributions or 0)
        paid = float(self.total_paid_contributions or 0)
        self.collection_rate = (paid / expected * 100) if expected > 0 else 0.0

        self.total_cases_logged = cases.get("logged", 0)
        self.total_cases_resolved = cases.get("resolved", 0)
        self.total_cases_pending = cases.get("pending", 0)

        # Charts (match Frappe Chart config shape used in Complaints Status Report)
        self.status_chart_json = json.dumps({
            "data": {
                "labels": ["Active", "Inactive", "Suspended", "Pending", "Blacklisted"],
                "datasets": [{
                    "name": "Employers by Status",
                    "values": [
                        int(self.active_count or 0),
                        int(self.inactive_count or 0),
                        int(self.suspended_count or 0),
                        int(self.pending_count or 0),
                        int(self.blacklisted_count or 0),
                    ],
                }],
            },
            "type": "bar",
            "colors": ["#28a745", "#6c757d", "#ffc107", "#17a2b8", "#dc3545"],
        })
        self.compliance_chart_json = json.dumps({
            "data": {
                "labels": ["Compliant", "Non-Compliant"],
                "datasets": [{
                    "name": "Compliance",
                    "values": [
                        int(self.compliant_count or 0),
                        int(self.non_compliant_count or 0),
                    ],
                }],
            },
            "type": "pie",
        })
        self.contributions_chart_json = json.dumps({
            "data": {
                "labels": ["Expected", "Paid", "Outstanding"],
                "datasets": [{
                    "name": "Contributions (period)",
                    "values": [
                        float(self.total_expected_contributions or 0),
                        float(self.total_paid_contributions or 0),
                        float(self.total_outstanding_contributions or 0),
                    ],
                }],
            },
            "type": "bar",
        })
        self.trend_chart_json = json.dumps({
            "data": {
                "labels": [frappe.utils.format_date(df), frappe.utils.format_date(dt)],
                "datasets": [{
                    "name": "Cases",
                    "values": [
                        int(self.total_cases_logged or 0),
                        int(self.total_cases_resolved or 0),
                    ],
                }],
            },
            "type": "line",
        })

        self.top_claims_json = json.dumps(top_claims)

        # Build dashboard HTML with metric cards and top claims table
        self.report_html = build_report_html(self, top_claims)
        self.rows_json = json.dumps({"summary": summary, "contributions": contrib, "cases": cases})
        self.filters_json = json.dumps({"period_type": self.period_type})

        self.generated_at = frappe.utils.now_datetime()
        try:
            self.generated_by = frappe.session.user
        except Exception:
            self.generated_by = None

        self.save(ignore_permissions=True)


# ---- Aggregators (defensive: handle missing doctypes/fields) ----

def _aggregate_employer_summary(df: date, dt: date) -> Dict[str, int]:
    """Aggregate employer summary using the Employer doctype.

    Returns counts for:
    - total_employers: All employers regardless of status
    - active: Employers with status = 'Active'
    - compliant: From Compliance Report doctype (if exists)
    - non_compliant: From Compliance Report doctype (if exists)
    - inactive: Employers with status = 'Inactive'
    - suspended: Employers with status = 'Suspended'
    - pending: Employers with status = 'Pending Verification'
    - blacklisted: Employers with status = 'Blacklisted'
    """
    res = {
        "total_employers": 0,
        "active": 0,
        "compliant": 0,
        "non_compliant": 0,
        "inactive": 0,
        "suspended": 0,
        "pending": 0,
        "blacklisted": 0,
    }
    try:
        if not frappe.db.exists("DocType", "Employer"):
            return res

        # Total employers (all statuses)
        total = frappe.db.count("Employer")

        # Count by status
        active = frappe.db.count("Employer", filters={"status": "Active"})
        inactive = frappe.db.count("Employer", filters={"status": "Inactive"})
        suspended = frappe.db.count("Employer", filters={"status": "Suspended"})
        pending = frappe.db.count("Employer", filters={"status": "Pending Verification"})
        blacklisted = frappe.db.count("Employer", filters={"status": "Blacklisted"})

        # Compliance data comes from Compliance Report doctype (if exists)
        # The Compliance Report stores compliant_rules and non_compliant_rules as integers
        compliant = 0
        non_compliant = 0
        if frappe.db.exists("DocType", "Compliance Report"):
            try:
                # Sum up compliant and non-compliant rules across all reports
                result = frappe.db.sql("""
                    SELECT
                        COALESCE(SUM(compliant_rules), 0) as compliant,
                        COALESCE(SUM(non_compliant_rules), 0) as non_compliant
                    FROM `tabCompliance Report`
                    WHERE docstatus < 2
                """, as_dict=True)
                if result:
                    compliant = int(result[0].get("compliant") or 0)
                    non_compliant = int(result[0].get("non_compliant") or 0)
            except Exception:
                # Field structure may differ - ignore compliance data
                pass

        res.update({
            "total_employers": total or 0,
            "active": active or 0,
            "compliant": compliant or 0,
            "non_compliant": non_compliant or 0,
            "inactive": inactive or 0,
            "suspended": suspended or 0,
            "pending": pending or 0,
            "blacklisted": blacklisted or 0,
        })
    except Exception as e:
        frappe.log_error(f"Error aggregating employer summary: {e}", "Employer Status Report")
    return res


def _aggregate_contributions(df: date, dt: date) -> Dict[str, Any]:
    res = {"expected_total": 0.0, "paid_total": 0.0, "outstanding_total": 0.0, "overdue_count": 0}
    try:
        if frappe.db.exists("DocType", "Employer Contributions"):
            # expected: due_date in [df, dt]
            expected = frappe.db.sql(
                """
                select coalesce(sum(contribution_amount), 0)
                from `tabEmployer Contributions`
                where ifnull(due_date, '0001-01-01') between %s and %s
                and ifnull(docstatus,0) < 2
                """,
                (df, dt),
            )[0][0] or 0
            # paid: payment_date in [df, dt]
            paid = frappe.db.sql(
                """
                select coalesce(sum(amount_paid), 0)
                from `tabEmployer Contributions`
                where ifnull(payment_date, '0001-01-01') between %s and %s
                and ifnull(docstatus,0) < 2
                """,
                (df, dt),
            )[0][0] or 0
            # outstanding and overdue count (as of dt)
            outstanding = frappe.db.sql(
                """
                select coalesce(sum(outstanding_amount), 0)
                from `tabEmployer Contributions`
                where ifnull(docstatus,0) < 2
                """,
            )[0][0] or 0
            overdue_count = frappe.db.sql(
                """
                select count(1)
                from `tabEmployer Contributions`
                where ifnull(docstatus,0) < 2
                  and ifnull(outstanding_amount, 0) > 0
                  and ifnull(due_date, '0001-01-01') < %s
                """,
                (dt,),
            )[0][0] or 0
            res.update({
                "expected_total": float(expected or 0),
                "paid_total": float(paid or 0),
                "outstanding_total": float(outstanding or 0),
                "overdue_count": int(overdue_count or 0),
            })
        elif frappe.db.exists("DocType", "Employer Contribution"):
            # Backward-compatible fallback to singular DocType/fields
            expected = frappe.db.sql(
                """
                select coalesce(sum(amount), 0)
                from `tabEmployer Contribution`
                where ifnull(due_date, '0001-01-01') between %s and %s
                and ifnull(docstatus,0) < 2
                """,
                (df, dt),
            )[0][0] or 0
            paid = frappe.db.sql(
                """
                select coalesce(sum(paid_amount), 0)
                from `tabEmployer Contribution`
                where ifnull(payment_date, '0001-01-01') between %s and %s
                and ifnull(docstatus,0) < 2
                """,
                (df, dt),
            )[0][0] or 0
            outstanding = frappe.db.sql(
                """
                select coalesce(sum(outstanding_amount), 0)
                from `tabEmployer Contribution`
                where ifnull(docstatus,0) < 2
                """,
            )[0][0] or 0
            overdue_count = frappe.db.sql(
                """
                select count(1)
                from `tabEmployer Contribution`
                where ifnull(docstatus,0) < 2
                  and ifnull(outstanding_amount, 0) > 0
                  and ifnull(due_date, '0001-01-01') < %s
                """,
                (dt,),
            )[0][0] or 0
            res.update({
                "expected_total": float(expected or 0),
                "paid_total": float(paid or 0),
                "outstanding_total": float(outstanding or 0),
                "overdue_count": int(overdue_count or 0),
            })
    except Exception:
        pass
    return res


def _aggregate_cases(df: date, dt: date) -> Dict[str, int]:
    # v1: define cases as Issues windowed by creation; resolved ~= status in ('Closed','Resolved')
    res = {"logged": 0, "resolved": 0, "pending": 0}
    try:
        if not frappe.db.exists("DocType", "Issue"):
            return res
        logged = frappe.db.sql(
            """
            select count(1) from `tabIssue`
            where ifnull(docstatus,0) < 2
              and ifnull(creation, '0001-01-01') between %s and %s
            """,
            (df, dt),
        )[0][0] or 0
        resolved = frappe.db.sql(
            """
            select count(1) from `tabIssue`
            where ifnull(docstatus,0) < 2
              and ifnull(status,'') in ('Closed','Resolved')
              and ifnull(modified, '0001-01-01') between %s and %s
            """,
            (df, dt),
        )[0][0] or 0
        pending = max(int(logged) - int(resolved), 0)
        res.update({"logged": int(logged), "resolved": int(resolved), "pending": int(pending)})
    except Exception:
        pass
    return res


def _aggregate_top_claims(df: date, dt: date, top_n: int = 10) -> List[Dict[str, Any]]:
    """Aggregate top employers by claim count and total amount.

    Attempts to join with Employer doctype for proper employer names.
    Falls back to raw employer field value if join fails or Employer doesn't exist.
    """
    rows: List[Dict[str, Any]] = []
    try:
        if not frappe.db.exists("DocType", "Claim"):
            return rows

        # Check if we can join with Employer doctype
        has_employer_doctype = frappe.db.exists("DocType", "Employer")

        if has_employer_doctype:
            # Try to join with Employer doctype for proper names
            sql = """
                SELECT
                    COALESCE(e.employer_name, UPPER(TRIM(c.employer)), 'UNKNOWN') as employer_name,
                    COALESCE(e.employer_code, '') as employer_code,
                    c.employer as employer_ref,
                    COUNT(1) as claim_count,
                    COALESCE(SUM(c.amount), 0) as total_amount
                FROM `tabClaim` c
                LEFT JOIN `tabEmployer` e ON c.employer = e.name
                WHERE (c.submitted_date BETWEEN %s AND %s)
                  AND IFNULL(c.docstatus, 0) < 2
                GROUP BY c.employer, e.employer_name, e.employer_code
                ORDER BY claim_count DESC, total_amount DESC
                LIMIT %s
            """
        else:
            # Fallback: no Employer doctype, use raw employer field
            sql = """
                SELECT
                    UPPER(TRIM(COALESCE(employer, 'UNKNOWN'))) as employer_name,
                    '' as employer_code,
                    employer as employer_ref,
                    COUNT(1) as claim_count,
                    COALESCE(SUM(amount), 0) as total_amount
                FROM `tabClaim`
                WHERE (submitted_date BETWEEN %s AND %s)
                  AND IFNULL(docstatus, 0) < 2
                GROUP BY employer
                ORDER BY claim_count DESC, total_amount DESC
                LIMIT %s
            """

        data = frappe.db.sql(sql, (df, dt, top_n), as_dict=True) or []

        for d in data:
            rows.append({
                "employer": d.get("employer_name") or "UNKNOWN",
                "employer_code": d.get("employer_code") or "",
                "employer_ref": d.get("employer_ref") or "",
                "claims": int(d.get("claim_count") or 0),
                "amount": float(d.get("total_amount") or 0),
            })
    except Exception as e:
        frappe.log_error(f"Error aggregating top claims: {e}", "Employer Status Report")
    return rows


# ----- Dashboard HTML Builder -----

def build_report_html(doc: "EmployerStatusReport", top_claims: List[Dict[str, Any]]) -> str:
    """Build rich dashboard HTML with metric cards, charts placeholder, and top claims table."""
    def card(label: str, value: Any, style: str = ""):
        return f"<div style='display:inline-block;margin:6px;padding:10px;border:1px solid #ddd;border-radius:6px{style}'><div style='font-size:12px;color:#666'>{label}</div><div style='font-size:18px;font-weight:600'>{value}</div></div>"

    # Employer status cards - all statuses
    status_cards = "".join([
        card("Total Employers", int(doc.total_employers or 0), style=";background:#e3f2fd"),
        card("Active", int(doc.active_count or 0), style=";background:#e8f5e9"),
        card("Inactive", int(doc.inactive_count or 0), style=";background:#f5f5f5"),
        card("Suspended", int(doc.suspended_count or 0), style=";background:#fff3e0"),
        card("Pending", int(doc.pending_count or 0), style=";background:#e3f2fd"),
        card("Blacklisted", int(doc.blacklisted_count or 0), style=";background:#ffebee"),
    ])

    # Compliance cards
    compliance_cards = "".join([
        card("Compliant", int(doc.compliant_count or 0), style=";background:#e8f5e9"),
        card("Non-Compliant", int(doc.non_compliant_count or 0), style=";background:#ffebee"),
        card("Overdue Contributions", int(doc.overdue_contributions_count or 0), style=";background:#fff3e0"),
    ])

    # Contributions summary with collection rate
    collection_rate = float(doc.collection_rate or 0)
    rate_color = "#e8f5e9" if collection_rate >= 80 else ("#fff3e0" if collection_rate >= 50 else "#ffebee")
    contrib_cards = "".join([
        card("Expected", f"{float(doc.total_expected_contributions or 0):,.2f}"),
        card("Paid", f"{float(doc.total_paid_contributions or 0):,.2f}", style=";background:#e8f5e9"),
        card("Outstanding", f"{float(doc.total_outstanding_contributions or 0):,.2f}", style=";background:#ffebee"),
        card("Collection Rate", f"{collection_rate:.1f}%", style=f";background:{rate_color}"),
    ])

    # Cases summary
    cases_cards = "".join([
        card("Cases Logged", int(doc.total_cases_logged or 0)),
        card("Resolved", int(doc.total_cases_resolved or 0), style=";background:#e8f5e9"),
        card("Pending", int(doc.total_cases_pending or 0), style=";background:#fff3e0"),
    ])

    # Top claims table
    top_claims_html = ""
    if top_claims:
        rows_html = ""
        for r in top_claims[:20]:
            employer = frappe.utils.escape_html(str(r.get("employer") or ""))
            claims = int(r.get("claims") or 0)
            amount = float(r.get("amount") or 0)
            rows_html += f"<tr><td>{employer}</td><td style='text-align:right'>{claims}</td><td style='text-align:right'>{amount:,.2f}</td></tr>"

        top_claims_html = f"""
        <div style='margin-top:20px'>
            <h4 style='margin-bottom:10px'>Top Employers by Claims</h4>
            <table class='table table-bordered table-condensed' style='width:100%;border-collapse:collapse'>
                <thead style='background:#f5f5f5'>
                    <tr>
                        <th style='padding:8px;border:1px solid #ddd'>Employer</th>
                        <th style='padding:8px;border:1px solid #ddd;text-align:right'>Claims</th>
                        <th style='padding:8px;border:1px solid #ddd;text-align:right'>Amount</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """

    html = f"""
    <div style='font-family:Inter,Arial,sans-serif'>
        <h3 style='margin-bottom:10px'>Employer Status Dashboard</h3>
        <div style='color:#666;margin-bottom:20px'>Period: {frappe.utils.format_date(doc.date_from)} to {frappe.utils.format_date(doc.date_to)}</div>

        <div style='margin-bottom:20px'>
            <h4 style='margin-bottom:8px'>Employer Status Breakdown</h4>
            {status_cards}
        </div>

        <div style='margin-bottom:20px'>
            <h4 style='margin-bottom:8px'>Compliance</h4>
            {compliance_cards}
        </div>

        <div style='margin-bottom:20px'>
            <h4 style='margin-bottom:8px'>Contributions</h4>
            {contrib_cards}
        </div>

        <div style='margin-bottom:20px'>
            <h4 style='margin-bottom:8px'>Cases</h4>
            {cases_cards}
        </div>

        {top_claims_html}

        <div style='margin-top:20px;padding:10px;background:#f9f9f9;border-radius:6px'>
            <p style='margin:0;font-size:12px;color:#666'><strong>Note:</strong> Charts are rendered dynamically in the form view. Use the Actions menu to download PDF or email this report.</p>
        </div>
    </div>
    """
    return html


# ----- Exports / Email -----


def _attach_to_doc(doctype: str, name: str, filename: str, content: bytes):
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": doctype,
        "attached_to_name": name,
        "content": content,
        "is_private": 1,
    })
    file_doc.save(ignore_permissions=True)


def _get_role_emails(roles: List[str]) -> List[str]:
    if not roles:
        return []
    has_roles = frappe.get_all(
        "Has Role",
        filters={"role": ["in", roles]},
        fields=["parent"],
        limit=1000,
    )
    user_ids = {r["parent"] for r in has_roles if r.get("parent")}
    if not user_ids:
        return []
    users = frappe.get_all(
        "User",
        filters={"name": ["in", list(user_ids)], "enabled": 1, "user_type": "System User"},
        fields=["name", "email"],
        limit=1000,
    )
    emails = [u.get("email") for u in users if u.get("email")]
    return sorted(set(emails))


def _build_pdf_html(doc: "EmployerStatusReport") -> str:
    subtitle = f"{doc.period_type} | {doc.date_from} → {doc.date_to}"
    header = f"<h2 style='margin:0'>WCFCB Employer Status Report</h2><div style='color:#666'>{subtitle}</div>"
    # Body with key metrics and simple table for top claims if present
    body = [
        "<div>",
        f"<p><strong>Total Employers:</strong> {int(doc.total_employers or 0)}</p>",
        f"<p><strong>Active:</strong> {int(doc.active_count or 0)} | <strong>Compliant:</strong> {int(doc.compliant_count or 0)} | <strong>Non-Compliant:</strong> {int(doc.non_compliant_count or 0)}</p>",
        f"<p><strong>Expected:</strong> {float(doc.total_expected_contributions or 0):,.2f} | <strong>Paid:</strong> {float(doc.total_paid_contributions or 0):,.2f} | <strong>Outstanding:</strong> {float(doc.total_outstanding_contributions or 0):,.2f}</p>",
        f"<p><strong>Cases Logged:</strong> {int(doc.total_cases_logged or 0)} | <strong>Resolved:</strong> {int(doc.total_cases_resolved or 0)} | <strong>Pending:</strong> {int(doc.total_cases_pending or 0)}</p>",
        "</div>",
    ]

    # Top claims table
    try:
        rows = json.loads(doc.top_claims_json or "[]")
    except Exception:
        rows = []
    if rows:
        body.append("<h4 style='margin-top:12px'>Top Employers by Claims</h4>")
        body.append("<table class='table table-bordered table-condensed'><thead><tr><th>Employer</th><th>Claims</th><th>Amount</th></tr></thead><tbody>")
        for r in rows[:20]:
            employer = frappe.utils.escape_html(str(r.get("employer") or ""))
            claims = int(r.get("claims") or 0)
            amount = float(r.get("amount") or 0)
            body.append(f"<tr><td>{employer}</td><td>{claims}</td><td>{amount:,.2f}</td></tr>")
        body.append("</tbody></table>")

    inner = "".join(body)
    return f"<div style='font-family:Inter,Arial,sans-serif'>{header}<hr/>{inner}</div>"


@frappe.whitelist()
def generate_pdf(name: str) -> str:
    doc = frappe.get_doc("Employer Status Report", name)
    html = _build_pdf_html(doc)
    try:
        from frappe.utils.pdf import get_pdf
        pdf_bytes = get_pdf(html)
    except Exception:
        # Fallback for older frappe versions
        pdf_bytes = frappe.get_print(doc.doctype, doc.name, print_format=None, as_pdf=True)
    filename = f"Employer_Status_Report_{doc.name}.pdf"
    _attach_to_doc(doc.doctype, doc.name, filename, pdf_bytes)
    return filename


@frappe.whitelist()
def email_report(name: str, recipients: Optional[List[str]] = None) -> Dict[str, Any]:
    doc = frappe.get_doc("Employer Status Report", name)
    recipients = recipients or _get_role_emails(["Finance", "Claims"]) or []
    if not recipients:
        return {"message": "no-recipients"}
    try:
        html = _build_pdf_html(doc)
        try:
            from frappe.utils.pdf import get_pdf
            pdf_bytes = get_pdf(html)
        except Exception:
            pdf_bytes = frappe.get_print(doc.doctype, doc.name, print_format=None, as_pdf=True)
        filename = f"Employer_Status_Report_{doc.name}.pdf"
        _attach_to_doc(doc.doctype, doc.name, filename, pdf_bytes)
        frappe.sendmail(
            recipients=recipients,
            subject=f"WCFCB Employer Status Report: {doc.period_type} ({doc.date_from} → {doc.date_to})",
            message="Attached is the latest Employer Status Report.",
            attachments=[{"fname": filename, "fcontent": pdf_bytes}],
        )
        return {"message": "sent", "recipients": recipients}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Employer Status Report: email_report")
        frappe.throw(f"Failed to email report: {e}")


# ----- AI Insights -----
@frappe.whitelist()
def get_ai_insights(name: str, query: str) -> Dict[str, Any]:
    """Return WorkCom-style insights for an Employer Status Report.

    Builds a compact JSON context with the current window, employer KPIs,
    contribution metrics, service case volumes, a short history of previous
    reports, and the top employers by claims. The context is then passed to
    the WorkCom (OpenAI) engine via EnhancedAIService.
    """

    doc = frappe.get_doc("Employer Status Report", name)

    historical = frappe.get_all(
        "Employer Status Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "total_employers",
            "active_count",
            "compliant_count",
            "non_compliant_count",
            "overdue_contributions_count",
            "total_expected_contributions",
            "total_paid_contributions",
            "total_outstanding_contributions",
            "total_cases_logged",
            "total_cases_resolved",
            "total_cases_pending",
        ],
        order_by="date_from desc",
        limit=10,
    )

    context = {
        "window": {
            "period_type": doc.period_type,
            "from": str(doc.date_from),
            "to": str(doc.date_to),
        },
        "current": {
            "total_employers": int(doc.total_employers or 0),
            "active": int(doc.active_count or 0),
            "compliant": int(doc.compliant_count or 0),
            "non_compliant": int(doc.non_compliant_count or 0),
            "overdue_contributions": int(doc.overdue_contributions_count or 0),
            "expected_contributions": float(doc.total_expected_contributions or 0),
            "paid_contributions": float(doc.total_paid_contributions or 0),
            "outstanding_contributions": float(doc.total_outstanding_contributions or 0),
            "cases_logged": int(doc.total_cases_logged or 0),
            "cases_resolved": int(doc.total_cases_resolved or 0),
            "cases_pending": int(doc.total_cases_pending or 0),
        },
        "history": historical,
        "top_employers_by_claims": json.loads(doc.top_claims_json or "[]"),
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_employer_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Employer Status Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
            )
        }


# ---- Schedulers ----

@frappe.whitelist()
def schedule_monthly_employer_status_reports():
    try:
        today = frappe.utils.getdate()
        mon, yr = _previous_month(today)
        df = frappe.utils.get_first_day(f"{yr}-{mon}-01")
        dt = frappe.utils.get_last_day(df)
        _create_and_generate(df, dt, title=f"Employer Status Monthly: {df} to {dt}", period_type="Monthly")
    except Exception as e:
        try:
            frappe.log_error(f"schedule_monthly_employer_status_reports error: {e}", "Employer Status Report")
        except Exception:
            pass

@frappe.whitelist()
def smoke_create_and_generate_employer_status_report(period_type: str = "Monthly") -> Dict[str, Any]:
    """Create a test Employer Status Report for the previous period and run aggregation.
    Returns a small summary dict for smoke testing via `bench execute`.
    """
    today = date.today()
    if (period_type or "").lower().startswith("month"):
        first_this_month = date(today.year, today.month, 1)
        last_prev_month = first_this_month - timedelta(days=1)
        df = date(last_prev_month.year, last_prev_month.month, 1)
        dt = last_prev_month
        ptype = "Monthly"
    else:
        df, dt = _previous_quarter_range(today)
        ptype = "Quarterly"

    doc = frappe.get_doc({
        "doctype": "Employer Status Report",
        "period_type": ptype,
        "date_from": df,
        "date_to": dt,
        "title": f"Smoke {ptype} Report {df} to {dt}",
    })
    doc.insert(ignore_permissions=True)
    # Run aggregation
    doc.run_generation()

    return {
        "name": doc.name,
        "period_type": doc.period_type,
        "date_from": str(doc.date_from),
        "date_to": str(doc.date_to),
        "total_employers": getattr(doc, "total_employers", None),
        "active_count": getattr(doc, "active_count", None),
        "compliant_count": getattr(doc, "compliant_count", None),
        "non_compliant_count": getattr(doc, "non_compliant_count", None),
        "total_expected_contributions": getattr(doc, "total_expected_contributions", None),
        "total_paid_contributions": getattr(doc, "total_paid_contributions", None),
        "total_outstanding_contributions": getattr(doc, "total_outstanding_contributions", None),
    }


@frappe.whitelist()
def schedule_quarterly_employer_status_reports():
    today = frappe.utils.getdate()
    # Generate for the previous quarter
    q_df, q_dt = _previous_quarter_range(today)
    _create_and_generate(q_df, q_dt, title=f"Employer Status Quarterly: {q_df} → {q_dt}", period_type="Quarterly")


# ---- Helpers ----

def _create_and_generate(df: date, dt: date, title: str, period_type: str):
    doc = frappe.new_doc("Employer Status Report")
    doc.title = title
    doc.period_type = period_type
    doc.date_from = df
    doc.date_to = dt
    doc.insert(ignore_permissions=True)
    doc.run_generation()


def _previous_month(d: date):
    prev = (d.replace(day=1) - timedelta(days=1))
    return prev.month, prev.year


def _previous_quarter_range(d: date) -> Tuple[date, date]:
    # Find the first day of the current quarter
    q_month = ((d.month - 1) // 3) * 3 + 1
    current_q_start = date(d.year, q_month, 1)
    prev_q_end = current_q_start - timedelta(days=1)
    prev_q_month = ((prev_q_end.month - 1) // 3) * 3 + 1
    prev_q_start = date(prev_q_end.year, prev_q_month, 1)
    return prev_q_start, prev_q_end


