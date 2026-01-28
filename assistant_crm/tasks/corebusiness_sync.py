# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, get_datetime, add_to_date
from datetime import datetime, timedelta
import time


def execute_scheduled_sync():
    """Main scheduled sync job - runs every 5 minutes by default"""
    try:
        # Check if sync is enabled
        settings = frappe.get_single("CoreBusiness Settings")
        if not settings.enabled or not settings.real_time_sync:
            return
        
        # Check if it's time for sync based on interval
        last_sync = settings.last_sync_time
        sync_interval = settings.sync_interval_minutes or 15
        
        if last_sync:
            next_sync_time = add_to_date(last_sync, minutes=sync_interval)
            if datetime.now() < get_datetime(next_sync_time):
                return  # Not time for sync yet
        
        # Update sync status
        settings.sync_status = "In Progress"
        settings.last_sync_time = now()
        settings.save()
        frappe.db.commit()
        
        # Execute sync operations
        sync_results = {
            "employers": 0,
            "beneficiaries": 0,
            "claims": 0,
            "payments": 0,
            "errors": []
        }
        
        try:
            # Sync employers
            employer_result = sync_employers_incremental()
            sync_results["employers"] = employer_result.get("success_count", 0)
            sync_results["errors"].extend(employer_result.get("errors", []))
            
            # Sync beneficiaries
            beneficiary_result = sync_beneficiaries_incremental()
            sync_results["beneficiaries"] = beneficiary_result.get("success_count", 0)
            sync_results["errors"].extend(beneficiary_result.get("errors", []))
            
            # Sync claims
            claims_result = sync_claims_incremental()
            sync_results["claims"] = claims_result.get("success_count", 0)
            sync_results["errors"].extend(claims_result.get("errors", []))
            
            # Sync payments
            payments_result = sync_payments_incremental()
            sync_results["payments"] = payments_result.get("success_count", 0)
            sync_results["errors"].extend(payments_result.get("errors", []))
            
            # Update sync status
            total_synced = sum([
                sync_results["employers"],
                sync_results["beneficiaries"], 
                sync_results["claims"],
                sync_results["payments"]
            ])
            
            settings.sync_status = "Completed" if len(sync_results["errors"]) == 0 else "Completed with Errors"
            settings.last_successful_sync = now()
            settings.total_records_synced = (settings.total_records_synced or 0) + total_synced
            
            if sync_results["errors"]:
                settings.failed_sync_count = (settings.failed_sync_count or 0) + len(sync_results["errors"])
                settings.last_error_message = "; ".join(sync_results["errors"][:3])  # First 3 errors
            
            settings.save()
            frappe.db.commit()
            
            frappe.log_error(f"Scheduled sync completed: {sync_results}")
            
        except Exception as e:
            # Update sync status on failure
            settings.sync_status = "Failed"
            settings.failed_sync_count = (settings.failed_sync_count or 0) + 1
            settings.last_error_message = str(e)
            settings.save()
            frappe.db.commit()
            raise e
            
    except Exception as e:
        frappe.log_error(f"Scheduled sync error: {str(e)}")


def sync_employers_incremental():
    """Sync employers that have been updated since last sync.

    NOTE: Employer Profile doctype has been removed - using ERPNext Customer instead.
    """
    # NOTE: Employer Profile doctype has been removed
    # This sync function is deprecated as employers are now managed via ERPNext Customer
    return {
        "success_count": 0,
        "errors": ["Employer Profile doctype has been removed - use ERPNext Customer instead"]
    }


def sync_beneficiaries_incremental():
    """Sync beneficiaries that have been updated since last sync.

    NOTE: Beneficiary Profile doctype has been removed - beneficiary data is managed externally.
    """
    # NOTE: Beneficiary Profile doctype has been removed
    # This sync function is deprecated as beneficiaries are now managed externally
    return {
        "success_count": 0,
        "errors": ["Beneficiary Profile doctype has been removed - beneficiary data managed externally"]
    }


def sync_claims_incremental():
    """Sync claims that have been updated since last sync"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
        
        live_service = LiveDataRetrievalService()
        success_count = 0
        errors = []
        
        # Get claims that need status updates
        cutoff_time = datetime.now() - timedelta(hours=6)  # More frequent for claims
        
        claims_to_sync = frappe.db.sql("""
            SELECT claim_number 
            FROM `tabClaims Tracking` 
            WHERE (last_updated IS NULL OR last_updated < %s)
            AND status NOT IN ('Paid', 'Rejected', 'Closed')
            LIMIT 30
        """, (cutoff_time,), as_dict=True)
        
        for claim in claims_to_sync:
            try:
                result = live_service.get_claim_status(claim.claim_number)
                if result.get("success"):
                    success_count += 1
                else:
                    errors.append(f"Claim {claim.claim_number}: {result.get('error')}")
                    
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                errors.append(f"Claim {claim.claim_number}: {str(e)}")
        
        return {
            "success_count": success_count,
            "errors": errors
        }
        
    except Exception as e:
        return {
            "success_count": 0,
            "errors": [f"Claims sync error: {str(e)}"]
        }


def sync_payments_incremental():
    """Sync payments that have been updated since last sync"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
        
        live_service = LiveDataRetrievalService()
        success_count = 0
        errors = []
        
        # Get payments that need status updates
        cutoff_time = datetime.now() - timedelta(hours=2)  # Very frequent for payments
        
        payments_to_sync = frappe.db.sql("""
            SELECT payment_reference 
            FROM `tabPayment Status` 
            WHERE (last_updated IS NULL OR last_updated < %s)
            AND status NOT IN ('Processed', 'Failed', 'Cancelled')
            LIMIT 20
        """, (cutoff_time,), as_dict=True)
        
        for payment in payments_to_sync:
            try:
                result = live_service.get_payment_status(payment.payment_reference)
                if result.get("success"):
                    success_count += 1
                else:
                    errors.append(f"Payment {payment.payment_reference}: {result.get('error')}")
                    
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                errors.append(f"Payment {payment.payment_reference}: {str(e)}")
        
        return {
            "success_count": success_count,
            "errors": errors
        }
        
    except Exception as e:
        return {
            "success_count": 0,
            "errors": [f"Payments sync error: {str(e)}"]
        }


def execute_full_sync():
    """Execute full sync of all data - runs daily"""
    try:
        frappe.log_error("Starting full sync of CoreBusiness data")
        
        # Check if sync is enabled
        settings = frappe.get_single("CoreBusiness Settings")
        if not settings.enabled:
            return
        
        # Update sync status
        settings.sync_status = "In Progress"
        settings.save()
        frappe.db.commit()
        
        # Execute full sync
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
        live_service = LiveDataRetrievalService()
        
        result = live_service.refresh_all_cache()
        
        # Update sync status
        if result.get("success"):
            settings.sync_status = "Completed"
            settings.last_successful_sync = now()
            settings.total_records_synced = result.get("total_refreshed", 0)
            if result.get("error_count", 0) > 0:
                settings.failed_sync_count = result.get("error_count")
                settings.last_error_message = f"{result.get('error_count')} errors during full sync"
        else:
            settings.sync_status = "Failed"
            settings.failed_sync_count = (settings.failed_sync_count or 0) + 1
            settings.last_error_message = result.get("error", "Full sync failed")
        
        settings.save()
        frappe.db.commit()
        
        frappe.log_error(f"Full sync completed: {result}")
        
    except Exception as e:
        frappe.log_error(f"Full sync error: {str(e)}")


def retry_failed_syncs():
    """Retry failed sync operations.

    NOTE: Employer Profile and Beneficiary Profile doctypes have been removed.
    This function is now deprecated.
    """
    # NOTE: Employer Profile and Beneficiary Profile doctypes have been removed
    # This retry function is deprecated
    pass
