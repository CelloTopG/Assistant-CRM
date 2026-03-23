import frappe
import re

def extract_customer_metadata_from_message(message_name):
    """
    Background job triggered when a new inbound message is received.
    Extracts Zambian NRC format and keywords indicating user type.
    """
    try:
        msg = frappe.get_doc("Unified Inbox Message", message_name)
        if msg.direction != "Inbound" or not msg.message_content:
            return

        conv = frappe.get_doc("Unified Inbox Conversation", msg.conversation)
        
        # If already fully populated, skip to save resources
        if conv.customer_nrc and conv.customer_type and conv.customer_id:
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
        
        # Identify Customer Type using NLP keywords
        if not conv.customer_type:
            if "pensioner" in text:
                conv.db_set("customer_type", "Pensioner")
                updated = True
            elif "employer" in text:
                conv.db_set("customer_type", "Employer")
                updated = True
            elif "beneficiary" in text:
                conv.db_set("customer_type", "Beneficiary")
                updated = True

        # Reload the doc to see if we now have both fields needed to run the profile lookup
        if updated:
            conv.reload()

        if conv.customer_nrc and conv.customer_type and not conv.customer_id:
            frappe.enqueue("assistant_crm.api.customer_identification.link_customer_profile", conversation_name=conv.name, queue="default")

    except Exception as e:
        frappe.log_error(f"Error extracting metadata from message {message_name}: {str(e)}", "Customer Identification Extraction")


def link_customer_profile(conversation_name):
    """
    Background job that binds the CRM profile once the NRC/Employer classification is acquired.
    """
    try:
        conv = frappe.get_doc("Unified Inbox Conversation", conversation_name)
        
        if not conv.customer_nrc or not conv.customer_type or conv.customer_id:
            return
            
        # Query the core Customer doctype using the exact specific custom_nrc_number field
        customer_candidates = frappe.get_all(
            "Customer", 
            filters={"custom_nrc_number": conv.customer_nrc}, 
            fields=["name", "customer_name", "custom_pas_number"], 
            limit=1
        )
        
        if customer_candidates:
            customer = customer_candidates[0]
            conv.db_set("customer_id", customer.name)
            
            # Align Unified Inbox visual tags to the authentic database record
            if customer.customer_name:
                conv.db_set("customer_name", customer.customer_name)
                
            # Autonomously Pull CBS / PAS number down into the conversation
            if customer.get("custom_pas_number"):
                conv.db_set("customer_pas_number", customer.get("custom_pas_number"))
                
            # Log successful sync audit trail for agents
            conv.add_comment("Comment", f"Autonomously linked to Customer Profile ({customer.name}) via Background Job matching internal NRC/Employer ID.")
            
    except Exception as e:
        frappe.log_error(f"Error linking profile for conv {conversation_name}: {str(e)}", "Customer Identification Mapping")
