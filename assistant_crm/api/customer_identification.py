import frappe
import re

def extract_customer_metadata_from_message(message_name):
    """
    Background job triggered when a new inbound message is received.
    Extracts Zambian NRC format autonomously to pass into the database lookup system.
    """
    try:
        msg = frappe.get_doc("Unified Inbox Message", message_name)
        if msg.direction != "Inbound" or not msg.message_content:
            return

        conv = frappe.get_doc("Unified Inbox Conversation", msg.conversation)
        
        # If already fully populated, skip to save resources
        if conv.customer_nrc and conv.customer_id:
            return

        updated = False
        text = msg.message_content.lower()

        # Extract NRC mathematically matching Zambian Format (e.g. 252924/67/1)
        if not conv.customer_nrc:
            nrc_match = re.search(r'\b\d{6}/\d{2}/\d{1}\b', msg.message_content)
            if nrc_match:
                conv.db_set("customer_nrc", nrc_match.group(0))
                updated = True
            else:
                # If they explicitly provide an employer number 
                emp_match = re.search(r'employer\s*(?:number|no|#)?\s*[:=\-]?\s*([a-zA-Z0-9]+)\b', msg.message_content, re.IGNORECASE)
                if emp_match:
                    conv.db_set("customer_nrc", emp_match.group(1))
                    updated = True

        # Reload the doc to see if we now have the required lookup criteria
        if updated:
            conv.reload()

        if conv.customer_nrc and not conv.customer_id:
            frappe.enqueue("assistant_crm.api.customer_identification.link_customer_profile", conversation_name=conv.name, queue="default")

    except Exception as e:
        import traceback
        error_msg = f"Error extracting metadata from message {message_name}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        frappe.log_error(error_msg, "Assistant CRM NRC Lookup - Extraction")


def link_customer_profile(conversation_name):
    """
    Background job that aggressively queries the CRM database using only the NRC/Employer ID, 
    populating ALL context fields definitively out of the source of truth profile.
    """
    try:
        conv = frappe.get_doc("Unified Inbox Conversation", conversation_name)
        
        if not conv.customer_nrc or conv.customer_id:
            return
            
        # Query the core Customer/Beneficiary doctype strictly using custom_nrc_number
        customer_candidates = frappe.get_all(
            "Customer", 
            filters={"custom_nrc_number": conv.customer_nrc}, 
            limit=1
        )
        
        if customer_candidates:
            # Full structured Document load to capture granular metadata across schema custom fields
            profile = frappe.get_doc("Customer", customer_candidates[0].name)
            
            # Map core identity
            conv.db_set("customer_id", profile.name)
            if profile.customer_name:
                conv.db_set("customer_name", profile.customer_name)
                
            # Autonomously Pull Telephone Configuration
            phone = profile.get("mobile_no") or profile.get("phone") or profile.get("custom_primary_phone_number") or profile.get("primary_mobile_number")
            if phone:
                conv.db_set("customer_phone", phone)

            # Autonomously infer Customer Type strictly based on backend truth
            backend_type = str(profile.get("customer_group") or profile.get("custom_customer_type") or profile.get("customer_type") or "Beneficiary").lower()
            normalized_type = "Beneficiary" # default fallback
            
            if "pension" in backend_type:
                normalized_type = "Pensioner"
            elif "employ" in backend_type:
                normalized_type = "Employer"
                
            conv.db_set("customer_type", normalized_type)
                
            # Autonomously Pull CBS / PAS number down into the conversation
            pas = profile.get("custom_pas_number")
            if pas:
                conv.db_set("customer_pas_number", pas)
                
            # Log successful sync audit trail for agents
            conv.add_comment("Comment", f"✅ **System Auth Match**: Autonomously linked to verified system Profile ({profile.name}).\nNRC: {conv.customer_nrc}\nType: {normalized_type}")
            
        else:
            # Document Unverified Visitor cleanly for agents
            conv.add_comment("Comment", f"⚠️ **System Alert**: Visitor indicated NRC/Employer ID `{conv.customer_nrc}`, but no exact match is present in our database.")
            
    except Exception as e:
        import traceback
        error_msg = f"Error linking profile for conv {conversation_name}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        frappe.log_error(error_msg, "Assistant CRM NRC Lookup - Linking")
