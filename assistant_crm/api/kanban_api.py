#!/usr/bin/env python3
"""
WCFCB Kanban API
Drag-and-drop interface for claim status management with automated workflows
"""

import frappe
from frappe import _
import json
from datetime import datetime, timedelta

@frappe.whitelist()
def get_claims_kanban_data():
    """
    Get claims data formatted for Kanban board display.
    """
    try:
        # Get claims with relevant fields
        claims = frappe.db.sql("""
            SELECT 
                name as id,
                title,
                status,
                priority,
                claimant_name as claimant,
                assigned_to as assignee,
                creation as created_date,
                modified,
                claim_type,
                claim_amount,
                employer_name
            FROM `tabClaim`
            WHERE status IN ('Pending', 'In Review', 'Approved', 'Rejected', 'Closed')
            ORDER BY 
                CASE status 
                    WHEN 'Pending' THEN 1 
                    WHEN 'In Review' THEN 2 
                    WHEN 'Approved' THEN 3 
                    WHEN 'Rejected' THEN 4 
                    WHEN 'Closed' THEN 5 
                    ELSE 6 
                END,
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Normal' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END,
                creation DESC
        """, as_dict=True)
        
        # Format data for Kanban display
        kanban_data = []
        for claim in claims:
            # Get assignee initials
            assignee_initials = get_user_initials(claim.get('assignee'))
            
            # Format priority
            priority = (claim.get('priority') or 'Normal').lower()
            
            # Format the claim data
            kanban_item = {
                "id": claim.get('id'),
                "title": claim.get('title') or f"Claim - {claim.get('claim_type', 'General')}",
                "status": claim.get('status'),
                "priority": priority,
                "assignee": assignee_initials,
                "created_date": claim.get('created_date').strftime('%Y-%m-%d') if claim.get('created_date') else '',
                "claimant": claim.get('claimant') or 'Unknown',
                "claim_type": claim.get('claim_type'),
                "claim_amount": claim.get('claim_amount'),
                "employer_name": claim.get('employer_name'),
                "modified": claim.get('modified').isoformat() if claim.get('modified') else ''
            }
            
            kanban_data.append(kanban_item)
        
        # Get statistics
        stats = get_kanban_statistics()
        
        return {
            "success": True,
            "data": kanban_data,
            "statistics": stats,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(f"Kanban data error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@frappe.whitelist()
def update_claim_status(claim_id, new_status):
    """
    Update claim status with automated workflow triggers.
    """
    try:
        # Validate inputs
        if not claim_id or not new_status:
            return {
                "success": False,
                "error": "Missing claim_id or new_status"
            }
        
        # Validate status
        valid_statuses = ['Pending', 'In Review', 'Approved', 'Rejected', 'Closed']
        if new_status not in valid_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }
        
        # Get the claim document
        claim_doc = frappe.get_doc("Claim", claim_id)
        old_status = claim_doc.status
        
        # Check permissions
        if not frappe.has_permission("Claim", "write", claim_doc):
            return {
                "success": False,
                "error": "Insufficient permissions to update this claim"
            }
        
        # Update status
        claim_doc.status = new_status
        claim_doc.modified_by = frappe.session.user
        claim_doc.modified = datetime.now()
        
        # Add status change log
        add_status_change_log(claim_doc, old_status, new_status)
        
        # Trigger automated workflows based on status change
        trigger_status_workflows(claim_doc, old_status, new_status)
        
        # Save the document
        claim_doc.save()
        frappe.db.commit()
        
        # Log the status change
        frappe.logger().info(f"Claim {claim_id} status changed from {old_status} to {new_status} by {frappe.session.user}")
        
        return {
            "success": True,
            "message": f"Claim {claim_id} status updated to {new_status}",
            "old_status": old_status,
            "new_status": new_status,
            "updated_by": frappe.session.user,
            "updated_at": datetime.now().isoformat()
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "error": f"Claim {claim_id} not found"
        }
    except Exception as e:
        frappe.log_error(f"Update claim status error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_kanban_statistics():
    """
    Get Kanban board statistics and metrics.
    """
    try:
        # Status distribution
        status_stats = frappe.db.sql("""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(DATEDIFF(NOW(), creation)) as avg_age_days
            FROM `tabClaim`
            GROUP BY status
            ORDER BY 
                CASE status 
                    WHEN 'Pending' THEN 1 
                    WHEN 'In Review' THEN 2 
                    WHEN 'Approved' THEN 3 
                    WHEN 'Rejected' THEN 4 
                    WHEN 'Closed' THEN 5 
                    ELSE 6 
                END
        """, as_dict=True)
        
        # Priority distribution
        priority_stats = frappe.db.sql("""
            SELECT 
                priority,
                COUNT(*) as count
            FROM `tabClaim`
            WHERE status NOT IN ('Closed', 'Rejected')
            GROUP BY priority
            ORDER BY 
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Normal' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END
        """, as_dict=True)
        
        # Recent activity (last 7 days)
        recent_activity = frappe.db.sql("""
            SELECT 
                DATE(creation) as date,
                COUNT(*) as new_claims
            FROM `tabClaim`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(creation)
            ORDER BY date DESC
        """, as_dict=True)
        
        # Processing time metrics
        processing_metrics = frappe.db.sql("""
            SELECT 
                AVG(DATEDIFF(modified, creation)) as avg_processing_days,
                MIN(DATEDIFF(modified, creation)) as min_processing_days,
                MAX(DATEDIFF(modified, creation)) as max_processing_days
            FROM `tabClaim`
            WHERE status IN ('Approved', 'Rejected', 'Closed')
                AND modified > creation
        """, as_dict=True)
        
        # Assignee workload
        assignee_workload = frappe.db.sql("""
            SELECT 
                assigned_to,
                COUNT(*) as active_claims
            FROM `tabClaim`
            WHERE status NOT IN ('Closed', 'Rejected')
                AND assigned_to IS NOT NULL
            GROUP BY assigned_to
            ORDER BY active_claims DESC
            LIMIT 10
        """, as_dict=True)
        
        return {
            "success": True,
            "data": {
                "status_distribution": status_stats,
                "priority_distribution": priority_stats,
                "recent_activity": recent_activity,
                "processing_metrics": processing_metrics[0] if processing_metrics else {},
                "assignee_workload": assignee_workload,
                "total_claims": sum(stat['count'] for stat in status_stats),
                "active_claims": sum(stat['count'] for stat in status_stats if stat['status'] not in ['Closed', 'Rejected']),
                "last_updated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Kanban statistics error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }

@frappe.whitelist()
def bulk_update_claims(claim_ids, new_status):
    """
    Bulk update multiple claims to a new status.
    """
    try:
        if not claim_ids or not new_status:
            return {
                "success": False,
                "error": "Missing claim_ids or new_status"
            }
        
        # Parse claim_ids if it's a string
        if isinstance(claim_ids, str):
            claim_ids = json.loads(claim_ids)
        
        updated_claims = []
        failed_claims = []
        
        for claim_id in claim_ids:
            try:
                result = update_claim_status(claim_id, new_status)
                if result.get("success"):
                    updated_claims.append(claim_id)
                else:
                    failed_claims.append({
                        "claim_id": claim_id,
                        "error": result.get("error")
                    })
            except Exception as e:
                failed_claims.append({
                    "claim_id": claim_id,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Updated {len(updated_claims)} claims successfully",
            "updated_claims": updated_claims,
            "failed_claims": failed_claims,
            "total_processed": len(claim_ids)
        }
        
    except Exception as e:
        frappe.log_error(f"Bulk update error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def get_user_initials(user_email):
    """
    Get user initials from email or full name.
    """
    if not user_email:
        return "UN"
    
    try:
        user = frappe.get_doc("User", user_email)
        if user.full_name:
            names = user.full_name.split()
            if len(names) >= 2:
                return f"{names[0][0]}{names[1][0]}".upper()
            else:
                return names[0][:2].upper()
        else:
            # Use email prefix
            return user_email.split('@')[0][:2].upper()
    except:
        return "UN"

def add_status_change_log(claim_doc, old_status, new_status):
    """
    Add status change to claim history.
    """
    try:
        # Add to claim comments/history
        comment = f"Status changed from {old_status} to {new_status} by {frappe.session.user}"
        
        # Create a comment document
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Claim",
            "reference_name": claim_doc.name,
            "content": comment,
            "comment_email": frappe.session.user
        }).insert(ignore_permissions=True)
        
    except Exception as e:
        frappe.log_error(f"Status change log error: {str(e)}")

def trigger_status_workflows(claim_doc, old_status, new_status):
    """
    Trigger automated workflows based on status changes.
    """
    try:
        # Workflow triggers based on status changes
        if new_status == "Approved":
            # Trigger approval workflow
            trigger_approval_workflow(claim_doc)
        elif new_status == "Rejected":
            # Trigger rejection workflow
            trigger_rejection_workflow(claim_doc)
        elif new_status == "In Review":
            # Assign to reviewer if not already assigned
            if not claim_doc.assigned_to:
                assign_to_reviewer(claim_doc)
        elif new_status == "Closed":
            # Trigger closure workflow
            trigger_closure_workflow(claim_doc)
        
        # Send notifications
        send_status_change_notification(claim_doc, old_status, new_status)
        
    except Exception as e:
        frappe.log_error(f"Workflow trigger error: {str(e)}")

def trigger_approval_workflow(claim_doc):
    """Trigger approval-specific workflows."""
    # Set approval date
    claim_doc.approval_date = datetime.now()
    
    # Calculate benefit amount if not set
    if not claim_doc.benefit_amount and claim_doc.claim_amount:
        claim_doc.benefit_amount = calculate_benefit_amount(claim_doc)

def trigger_rejection_workflow(claim_doc):
    """Trigger rejection-specific workflows."""
    # Set rejection date
    claim_doc.rejection_date = datetime.now()
    
    # Require rejection reason
    if not claim_doc.rejection_reason:
        claim_doc.rejection_reason = "Rejected via Kanban board"

def assign_to_reviewer(claim_doc):
    """Auto-assign claim to available reviewer."""
    # Find available reviewer with least workload
    reviewers = frappe.get_all("User", 
        filters={"role_profile_name": "Claims Reviewer", "enabled": 1},
        fields=["name"])
    
    if reviewers:
        # Simple round-robin assignment
        claim_doc.assigned_to = reviewers[0].name

def trigger_closure_workflow(claim_doc):
    """Trigger closure-specific workflows."""
    # Set closure date
    claim_doc.closure_date = datetime.now()

def calculate_benefit_amount(claim_doc):
    """Calculate benefit amount based on claim details."""
    # Placeholder calculation - implement actual business logic
    base_amount = claim_doc.claim_amount or 0
    return base_amount * 0.8  # 80% of claim amount

def send_status_change_notification(claim_doc, old_status, new_status):
    """Send notification about status change."""
    try:
        # Send email notification to claimant and assigned user
        recipients = []
        
        if claim_doc.claimant_email:
            recipients.append(claim_doc.claimant_email)
        
        if claim_doc.assigned_to:
            recipients.append(claim_doc.assigned_to)
        
        if recipients:
            subject = f"Claim {claim_doc.name} Status Update"
            message = f"""
            Dear User,
            
            The status of claim {claim_doc.name} has been updated:
            
            Previous Status: {old_status}
            New Status: {new_status}
            Updated By: {frappe.session.user}
            Updated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please log in to the WCFCB portal for more details.
            
            Best regards,
            WCFCB Team
            """
            
            frappe.sendmail(
                recipients=recipients,
                subject=subject,
                message=message
            )
            
    except Exception as e:
        frappe.log_error(f"Notification error: {str(e)}")
