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
        if conv.customer_nrc and getattr(conv, "customer_name", None) and getattr(conv, "customer_type", None) and getattr(conv, "customer_pas_number", getattr(conv, "custom_pas_number", None)):
            return

        updated = False
        text = msg.message_content.lower()

        # --- NRC extraction ---
        # Always attempt to match a properly-formatted Zambian NRC (XXXXXX/YY/Z).
        # A valid NRC match takes priority over any previously stored value, so
        # a junk value written by the employer fallback does not block the real NRC.
        nrc_match = re.search(r'\b\d{6}/\d{2}/\d{1}\b', msg.message_content)
        if nrc_match:
            proper_nrc = nrc_match.group(0)
            if conv.customer_nrc != proper_nrc:
                conv.db_set("customer_nrc", proper_nrc)
                updated = True
        elif not conv.customer_nrc:
            # Employer-number fallback — only fires when no NRC is stored yet.
            # Captured value MUST contain at least one digit so that common English
            # words like "and", "the", "is" are never saved as employer IDs.
            emp_match = re.search(
                r'employer\s*(?:number|no|#|id|code)?\s*[:=\-]?\s*([A-Za-z0-9]{2,})\b',
                msg.message_content, re.IGNORECASE
            )
            if emp_match:
                captured = emp_match.group(1)
                if re.search(r'\d', captured):          # must contain a digit
                    conv.db_set("customer_nrc", captured)
                    updated = True

        # Reload the doc to see if we now have the required lookup criteria
        if updated:
            conv.reload()

        if conv.customer_nrc:
            # link_customer_profile does DB lookups — keep async but add sync fallback
            try:
                link_customer_profile(conv.name)
            except Exception:
                frappe.enqueue(
                    "assistant_crm.api.customer_identification.link_customer_profile",
                    conversation_name=conv.name,
                    queue="default",
                )

    except Exception as e:
        import traceback
        error_msg = f"Error extracting metadata from message {message_name}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        frappe.log_error(error_msg, "Assistant CRM NRC Lookup - Extraction")


def extract_contact_details_from_messages(conversation_name):
    """
    Background job triggered on each inbound message.

    Scans all inbound messages in the conversation for:
      - A valid Zambian mobile phone number in the format +260 9x xxxxxxx
        (covers all major operators: Airtel 097, MTN 096/076, Zamtel 095/075)
      - A valid email address

    Behaviour:
      - If either customer_phone or customer_email is already populated the
        job exits immediately — nothing more needs to be found.
      - If both are already populated the job also exits immediately.
      - In a single scan pass, if BOTH phone and email are found, both fields
        are written.  Once at least one field is written the worker stops;
        subsequent message arrivals will find the field already set and exit
        early without re-scanning.
    """
    try:
        conv = frappe.get_doc("Unified Inbox Conversation", conversation_name)

        # Early exit: phone/email already captured AND customer_type already set
        contact_done = bool(conv.customer_phone or conv.customer_email)
        type_done = bool(conv.customer_type)
        if contact_done and type_done:
            return

        # Fetch all inbound message text for this conversation
        messages = frappe.get_all(
            "Unified Inbox Message",
            filters={"conversation": conversation_name, "direction": "Inbound"},
            fields=["message_content"],
            order_by="creation asc",
        )

        if not messages:
            return

        full_text = " ".join(m.message_content for m in messages if m.message_content)
        lower_text = full_text.lower()

        found_phone = None
        found_email = None
        found_type = None

        # --- Contact detail extraction (skip if already done) ---
        if not contact_done:
            # Zambian mobile: +260, optional separator, 2-digit prefix starting
            # with 7 or 9 (covers 75/76/77/95/96/97), optional separator, 7 digits.
            # Examples matched: +260971234567 | +260 97 1234567 | +260-96-7654321
            phone_match = re.search(
                r'\+260[\s\-]?[79]\d[\s\-]?\d{7}\b',
                full_text
            )
            if phone_match:
                # Normalise to +260XXXXXXXXX (strip internal spaces/hyphens)
                found_phone = re.sub(r'[\s\-]', '', phone_match.group(0))

            # Standard email address
            email_match = re.search(
                r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
                full_text
            )
            if email_match:
                found_email = email_match.group(0).lower()

        # --- Customer type keyword detection (skip if already set) ---
        # Order matters: check "general inquiry" before "general" to avoid
        # partial match. Check longer/more specific terms first throughout.
        if not type_done:
            if re.search(r'\bgeneral\s+inquiry\b', lower_text):
                found_type = "General Inquiry"
            elif re.search(r'\bbeneficiar(?:y|ies)\b', lower_text):
                found_type = "Beneficiary"
            elif re.search(r'\bclaimants?\b', lower_text):
                found_type = "Claimant"
            elif re.search(r'\bemployers?\b', lower_text):
                found_type = "Employer"
            elif re.search(r'\bgeneral\b', lower_text):
                found_type = "General Inquiry"

        # Nothing new to write
        if not found_phone and not found_email and not found_type:
            return

        populated = []

        if found_phone:
            conv.db_set("customer_phone", found_phone)
            populated.append(f"Phone: {found_phone}")

        if found_email:
            conv.db_set("customer_email", found_email)
            populated.append(f"Email: {found_email}")

        if found_type:
            conv.db_set("customer_type", found_type)
            populated.append(f"Type: {found_type}")

        conv.add_comment(
            "Comment",
            f"📞 **Contact Details Extracted**: {', '.join(populated)}"
        )

    except Exception as e:
        import traceback
        frappe.log_error(
            f"Error extracting contact details for conversation {conversation_name}: "
            f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}",
            "Assistant CRM - Contact Detail Extraction"
        )


def link_customer_profile(conversation_name):
    """
    Background job that aggressively queries the CRM database using only the NRC/Employer ID, 
    populating ALL context fields definitively out of the source of truth profile.
    """
    try:
        conv = frappe.get_doc("Unified Inbox Conversation", conversation_name)
        
        if not conv.customer_nrc:
            return
            
        from assistant_crm.api.unified_inbox_api import _find_beneficiary_or_employee_by_nrc
        customer_info = _find_beneficiary_or_employee_by_nrc(conv.customer_nrc)
        
        if customer_info and customer_info.get("link_name"):
            # Full structured Document load to capture granular metadata across schema custom fields
            profile = frappe.get_doc("Customer", customer_info["link_name"])
            
            # Map core identity
            conv.db_set("customer_id", profile.name)
            
            # Explicit Field 1: customer_name
            if profile.get("customer_name"):
                conv.db_set("customer_name", profile.get("customer_name"))
                
            # Autonomously Pull Telephone Configuration
            if profile.get("mobile_no"):
                conv.db_set("customer_phone", profile.get("mobile_no"))

            # Autonomously infer Customer Type strictly based on backend truth
            if profile.get("customer_type"):
                conv.db_set("customer_type", profile.get("customer_type"))
                
            # Explicitly Pull Customer Group if custom field exists
            if profile.get("customer_group"):
                conv.db_set("customer_group", profile.get("customer_group"))
                
            # Autonomously Pull CBS / PAS number down into the conversation
            pas = profile.get("custom_pas_number")
            if pas:
                conv.db_set("customer_pas_number", pas)
                
            # Log successful sync audit trail for agents
            conv.add_comment("Comment", f"✅ **System Auth Match**: Autonomously linked to verified system Profile ({profile.name}).\\nNRC: {conv.customer_nrc}\\nType: {profile.get('customer_type', 'Beneficiary')}")
            
        else:
            # Document Unverified Visitor cleanly for agents
            conv.add_comment("Comment", f"⚠️ **System Alert**: Visitor indicated NRC/Employer ID `{conv.customer_nrc}`, but no exact match is present in our database.")
            
    except Exception as e:
        import traceback
        error_msg = f"Error linking profile for conv {conversation_name}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        frappe.log_error(error_msg, "Assistant CRM NRC Lookup - Linking")
