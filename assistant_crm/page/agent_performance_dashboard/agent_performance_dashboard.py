"""Agent Performance Dashboard - Backend API"""
import frappe
from frappe.utils import now, get_datetime, add_days, getdate, nowdate, time_diff_in_seconds


def get_context(context):
    """Get context for Agent Performance Dashboard page."""
    context.no_cache = 1
    context.title = "Agent Performance Dashboard"
    return context


@frappe.whitelist()
def get_customer_service_agents():
    """Get all agents with Customer Service roles."""
    customer_service_roles = [
        "WCF Customer Service Officer",
        "WCF Customer Service Assistant"
    ]
    
    agents = frappe.db.sql("""
        SELECT DISTINCT 
            u.name as user_id, 
            u.full_name,
            u.user_image,
            u.enabled
        FROM `tabUser` u
        INNER JOIN `tabHas Role` hr ON hr.parent = u.name
        WHERE hr.role IN %(roles)s
        AND u.enabled = 1
        AND u.name NOT IN ('Administrator', 'Guest')
        ORDER BY u.full_name
    """, {"roles": customer_service_roles}, as_dict=True)
    
    # Get roles for each agent
    for agent in agents:
        roles = frappe.db.sql("""
            SELECT role FROM `tabHas Role` 
            WHERE parent = %(user)s AND role IN %(roles)s
        """, {"user": agent.user_id, "roles": customer_service_roles}, as_dict=True)
        agent["roles"] = [r.role for r in roles]
    
    return agents


@frappe.whitelist()
def get_agent_performance_metrics(agent_id=None, date_from=None, date_to=None):
    """Get performance metrics for agents."""
    if not date_from:
        date_from = add_days(nowdate(), -30)
    if not date_to:
        date_to = nowdate()
    
    filters = {
        "creation": ["between", [date_from, date_to]]
    }
    
    if agent_id:
        filters["assigned_agent"] = agent_id
    
    # Get conversation metrics
    conversations = frappe.db.sql("""
        SELECT 
            assigned_agent,
            status,
            platform,
            creation,
            first_response_time,
            response_time_sla,
            ai_handled,
            requires_human_intervention
        FROM `tabUnified Inbox Conversation`
        WHERE assigned_agent IS NOT NULL
        AND creation BETWEEN %(date_from)s AND %(date_to)s
        {agent_filter}
    """.format(
        agent_filter="AND assigned_agent = %(agent_id)s" if agent_id else ""
    ), {
        "date_from": date_from,
        "date_to": date_to,
        "agent_id": agent_id
    }, as_dict=True)
    
    return conversations


@frappe.whitelist()
def get_dashboard_summary(date_from=None, date_to=None):
    """Get summary metrics for the dashboard."""
    if not date_from:
        date_from = add_days(nowdate(), -30)
    if not date_to:
        date_to = nowdate()
    
    # Get all customer service agents
    agents = get_customer_service_agents()
    agent_ids = [a["user_id"] for a in agents]
    
    if not agent_ids:
        return {
            "total_agents": 0,
            "total_conversations": 0,
            "resolved_conversations": 0,
            "avg_response_time": 0,
            "agents_online": 0,
            "active_conversations": 0
        }
    
    # Total conversations assigned to CS agents
    total_conversations = frappe.db.count(
        "Unified Inbox Conversation",
        {
            "assigned_agent": ["in", agent_ids],
            "creation": ["between", [date_from, date_to]]
        }
    )
    
    # Resolved conversations
    resolved_conversations = frappe.db.count(
        "Unified Inbox Conversation",
        {
            "assigned_agent": ["in", agent_ids],
            "status": ["in", ["Resolved", "Closed"]],
            "creation": ["between", [date_from, date_to]]
        }
    )
    
    # Active conversations (not resolved/closed)
    active_conversations = frappe.db.count(
        "Unified Inbox Conversation",
        {
            "assigned_agent": ["in", agent_ids],
            "status": ["not in", ["Resolved", "Closed"]]
        }
    )
    
    # Average response time
    avg_response = frappe.db.sql("""
        SELECT AVG(response_time_sla) as avg_time
        FROM `tabUnified Inbox Conversation`
        WHERE assigned_agent IN %(agents)s
        AND response_time_sla > 0
        AND creation BETWEEN %(date_from)s AND %(date_to)s
    """, {"agents": agent_ids, "date_from": date_from, "date_to": date_to}, as_dict=True)
    
    avg_response_time = avg_response[0].avg_time if avg_response and avg_response[0].avg_time else 0
    
    return {
        "total_agents": len(agents),
        "total_conversations": total_conversations,
        "resolved_conversations": resolved_conversations,
        "resolution_rate": round((resolved_conversations / total_conversations * 100) if total_conversations > 0 else 0, 1),
        "avg_response_time": round(avg_response_time, 2),
        "active_conversations": active_conversations
    }


@frappe.whitelist()
def get_agent_details(date_from=None, date_to=None):
    """Get detailed metrics for each agent."""
    if not date_from:
        date_from = add_days(nowdate(), -30)
    if not date_to:
        date_to = nowdate()

    agents = get_customer_service_agents()
    agent_details = []

    for agent in agents:
        user_id = agent["user_id"]

        # Total assigned conversations
        total_assigned = frappe.db.count(
            "Unified Inbox Conversation",
            {
                "assigned_agent": user_id,
                "creation": ["between", [date_from, date_to]]
            }
        )

        # Resolved conversations
        resolved = frappe.db.count(
            "Unified Inbox Conversation",
            {
                "assigned_agent": user_id,
                "status": ["in", ["Resolved", "Closed"]],
                "creation": ["between", [date_from, date_to]]
            }
        )

        # Active conversations
        active = frappe.db.count(
            "Unified Inbox Conversation",
            {
                "assigned_agent": user_id,
                "status": ["not in", ["Resolved", "Closed"]]
            }
        )

        # Average response time
        avg_resp = frappe.db.sql("""
            SELECT AVG(response_time_sla) as avg_time
            FROM `tabUnified Inbox Conversation`
            WHERE assigned_agent = %(agent)s
            AND response_time_sla > 0
            AND creation BETWEEN %(date_from)s AND %(date_to)s
        """, {"agent": user_id, "date_from": date_from, "date_to": date_to}, as_dict=True)

        avg_response_time = avg_resp[0].avg_time if avg_resp and avg_resp[0].avg_time else 0

        # Platform breakdown
        platform_breakdown = frappe.db.sql("""
            SELECT platform, COUNT(*) as count
            FROM `tabUnified Inbox Conversation`
            WHERE assigned_agent = %(agent)s
            AND creation BETWEEN %(date_from)s AND %(date_to)s
            GROUP BY platform
        """, {"agent": user_id, "date_from": date_from, "date_to": date_to}, as_dict=True)

        agent_details.append({
            "user_id": user_id,
            "full_name": agent["full_name"],
            "user_image": agent.get("user_image"),
            "roles": agent.get("roles", []),
            "total_assigned": total_assigned,
            "resolved": resolved,
            "active": active,
            "resolution_rate": round((resolved / total_assigned * 100) if total_assigned > 0 else 0, 1),
            "avg_response_time": round(avg_response_time, 2),
            "platform_breakdown": {p["platform"]: p["count"] for p in platform_breakdown}
        })

    # Sort by total assigned (most active first)
    agent_details.sort(key=lambda x: x["total_assigned"], reverse=True)

    return agent_details


@frappe.whitelist()
def get_performance_trends(date_from=None, date_to=None, agent_id=None):
    """Get daily performance trends."""
    if not date_from:
        date_from = add_days(nowdate(), -30)
    if not date_to:
        date_to = nowdate()

    agents = get_customer_service_agents()
    agent_ids = [a["user_id"] for a in agents]

    if agent_id:
        agent_ids = [agent_id]

    if not agent_ids:
        return []

    # Daily conversation counts
    daily_data = frappe.db.sql("""
        SELECT
            DATE(creation) as date,
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved,
            AVG(CASE WHEN response_time_sla > 0 THEN response_time_sla ELSE NULL END) as avg_response
        FROM `tabUnified Inbox Conversation`
        WHERE assigned_agent IN %(agents)s
        AND creation BETWEEN %(date_from)s AND %(date_to)s
        GROUP BY DATE(creation)
        ORDER BY DATE(creation)
    """, {"agents": agent_ids, "date_from": date_from, "date_to": date_to}, as_dict=True)

    return daily_data


@frappe.whitelist()
def get_platform_distribution(date_from=None, date_to=None):
    """Get conversation distribution by platform."""
    if not date_from:
        date_from = add_days(nowdate(), -30)
    if not date_to:
        date_to = nowdate()

    agents = get_customer_service_agents()
    agent_ids = [a["user_id"] for a in agents]

    if not agent_ids:
        return []

    platform_data = frappe.db.sql("""
        SELECT
            platform,
            COUNT(*) as count,
            SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved
        FROM `tabUnified Inbox Conversation`
        WHERE assigned_agent IN %(agents)s
        AND creation BETWEEN %(date_from)s AND %(date_to)s
        GROUP BY platform
        ORDER BY count DESC
    """, {"agents": agent_ids, "date_from": date_from, "date_to": date_to}, as_dict=True)

    return platform_data


@frappe.whitelist()
def get_live_activity():
    """Get real-time activity data for live updates."""
    agents = get_customer_service_agents()
    agent_ids = [a["user_id"] for a in agents]

    if not agent_ids:
        return {
            "active_conversations": 0,
            "agents_with_active": 0,
            "recent_assignments": []
        }

    # Active conversations count
    active_count = frappe.db.count(
        "Unified Inbox Conversation",
        {
            "assigned_agent": ["in", agent_ids],
            "status": ["not in", ["Resolved", "Closed"]]
        }
    )

    # Agents with active conversations
    agents_with_active = frappe.db.sql("""
        SELECT COUNT(DISTINCT assigned_agent) as count
        FROM `tabUnified Inbox Conversation`
        WHERE assigned_agent IN %(agents)s
        AND status NOT IN ('Resolved', 'Closed')
    """, {"agents": agent_ids}, as_dict=True)

    # Recent assignments (last 10)
    recent = frappe.db.sql("""
        SELECT
            name,
            assigned_agent,
            customer_name,
            platform,
            status,
            agent_assigned_at
        FROM `tabUnified Inbox Conversation`
        WHERE assigned_agent IN %(agents)s
        AND agent_assigned_at IS NOT NULL
        ORDER BY agent_assigned_at DESC
        LIMIT 10
    """, {"agents": agent_ids}, as_dict=True)

    # Get agent names
    for r in recent:
        user = frappe.db.get_value("User", r.assigned_agent, "full_name")
        r["agent_name"] = user or r.assigned_agent

    return {
        "active_conversations": active_count,
        "agents_with_active": agents_with_active[0].count if agents_with_active else 0,
        "recent_assignments": recent
    }

