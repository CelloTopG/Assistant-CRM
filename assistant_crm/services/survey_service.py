import frappe
from frappe import _
import json
from datetime import datetime, timedelta

class SurveyService:
    def __init__(self):
        self.sentiment_analyzer = self.load_sentiment_analyzer()

    def load_sentiment_analyzer(self):
        """Load sentiment analysis configuration"""
        return {
            'positive_keywords': [
                'excellent', 'great', 'good', 'satisfied', 'happy', 'pleased',
                'wonderful', 'amazing', 'fantastic', 'helpful', 'professional',
                'quick', 'fast', 'efficient', 'friendly', 'polite', 'courteous'
            ],
            'negative_keywords': [
                'bad', 'poor', 'terrible', 'awful', 'horrible', 'unsatisfied',
                'unhappy', 'disappointed', 'frustrated', 'angry', 'rude',
                'slow', 'delayed', 'unprofessional', 'useless', 'waste'
            ]
        }

    def _get_beneficiary_contacts_from_corebusiness(self, filter_field, filter_operator, filter_value):
        """
        Query CoreBusiness for beneficiaries matching the filter conditions,
        then find corresponding Contact records by email or mobile.
        Returns a set of Contact names that match the beneficiary filters.
        Returns empty set if CoreBusiness is not available.
        """
        try:
            # Check if CoreBusiness is enabled
            try:
                cbs_settings = frappe.get_single('CoreBusiness Settings')
                if not cbs_settings.enabled:
                    return set()
            except Exception:
                return set()

            from assistant_crm.api.corebusiness_integration import CoreBusinessConnector

            connector = CoreBusinessConnector()

            # Map filter field to CoreBusiness column names
            field_map = {
                'full_name': ['FIRST_NAME', 'LAST_NAME'],
                'first_name': ['FIRST_NAME'],
                'last_name': ['LAST_NAME'],
                'email': ['EMAIL_ADDRESS'],
                'mobile': ['PHONE_NUMBER'],
                'nrc_number': ['NRC_NUMBER'],
                'beneficiary_number': ['BENEFICIARY_ID'],
            }

            # Get the CoreBusiness columns for this field
            cbs_columns = field_map.get(filter_field, [])
            if not cbs_columns:
                return set()

            # Build the WHERE clause based on filter operator
            where_clauses = []
            for col in cbs_columns:
                if filter_operator == 'equals':
                    where_clauses.append(f"LOWER({col}) = LOWER('{filter_value}')")
                elif filter_operator == 'contains':
                    where_clauses.append(f"LOWER({col}) LIKE LOWER('%{filter_value}%')")
                elif filter_operator == 'in':
                    values = [f"'{v.strip()}'" for v in filter_value.split(',')]
                    where_clauses.append(f"LOWER({col}) IN ({','.join(values)})")

            if not where_clauses:
                return set()

            where_condition = ' OR '.join(where_clauses)

            # Get all active beneficiaries from CoreBusiness matching the filter
            query = f"""
                SELECT
                    BENEFICIARY_ID,
                    FIRST_NAME,
                    LAST_NAME,
                    EMAIL_ADDRESS,
                    PHONE_NUMBER,
                    NRC_NUMBER
                FROM BENEFICIARIES
                WHERE STATUS = 'ACTIVE'
                AND ({where_condition})
            """

            results = connector.execute_query(query)
            connector.close_connection()

            if not results:
                return set()

            # Find Contact records that match these beneficiaries by email or mobile
            contact_names = set()
            for beneficiary in results:
                email = beneficiary.get('EMAIL_ADDRESS', '').strip()
                phone = beneficiary.get('PHONE_NUMBER', '').strip()

                # Search for contacts by email
                if email:
                    try:
                        contacts = frappe.db.get_list('Contact',
                            filters={'email_id': email},
                            fields=['name']
                        )
                        for contact in contacts:
                            contact_names.add(contact['name'])
                    except Exception:
                        pass

                # Search for contacts by phone
                if phone:
                    try:
                        contacts = frappe.db.get_list('Contact',
                            filters={'mobile_no': phone},
                            fields=['name']
                        )
                        for contact in contacts:
                            contact_names.add(contact['name'])
                    except Exception:
                        pass

            return contact_names

        except Exception:
            # Silently fall back to local table
            return set()

    def _get_employer_contacts_from_corebusiness(self, filter_field, filter_operator, filter_value):
        """
        Query CoreBusiness for employers matching the filter conditions,
        then find corresponding Contact records by email or mobile.
        Returns a set of Contact names that match the employer filters.
        Returns empty set if CoreBusiness is not available.
        """
        try:
            # Check if CoreBusiness is enabled
            try:
                cbs_settings = frappe.get_single('CoreBusiness Settings')
                if not cbs_settings.enabled:
                    return set()
            except Exception:
                return set()

            from assistant_crm.api.corebusiness_integration import CoreBusinessConnector

            connector = CoreBusinessConnector()

            # Map filter field to CoreBusiness column names
            field_map = {
                'employer_name': ['EMPLOYER_NAME'],
                'employer_code': ['EMPLOYER_CODE'],
                'email': ['EMPLOYER_EMAIL'],
                'mobile': ['EMPLOYER_PHONE'],
                'phone': ['EMPLOYER_PHONE'],
            }

            # Get the CoreBusiness columns for this field
            cbs_columns = field_map.get(filter_field, [])
            if not cbs_columns:
                return set()

            # Build the WHERE clause based on filter operator
            where_clauses = []
            for col in cbs_columns:
                if filter_operator == 'equals':
                    where_clauses.append(f"LOWER({col}) = LOWER('{filter_value}')")
                elif filter_operator == 'contains':
                    where_clauses.append(f"LOWER({col}) LIKE LOWER('%{filter_value}%')")
                elif filter_operator == 'in':
                    values = [f"'{v.strip()}'" for v in filter_value.split(',')]
                    where_clauses.append(f"LOWER({col}) IN ({','.join(values)})")

            if not where_clauses:
                return set()

            where_condition = ' OR '.join(where_clauses)

            # Get all active employers from CoreBusiness matching the filter
            # Query beneficiaries by employer
            query = f"""
                SELECT DISTINCT
                    EMPLOYER_NAME,
                    EMPLOYER_EMAIL,
                    EMPLOYER_PHONE
                FROM BENEFICIARIES
                WHERE STATUS = 'ACTIVE'
                AND ({where_condition})
            """

            results = connector.execute_query(query)
            connector.close_connection()

            if not results:
                return set()

            # Find Contact records that match these employers by email or mobile
            contact_names = set()
            for employer in results:
                email = employer.get('EMPLOYER_EMAIL', '').strip()
                phone = employer.get('EMPLOYER_PHONE', '').strip()

                # Search for contacts by email
                if email:
                    try:
                        contacts = frappe.db.get_list('Contact',
                            filters={'email_id': email},
                            fields=['name']
                        )
                        for contact in contacts:
                            contact_names.add(contact['name'])
                    except Exception:
                        pass

                # Search for contacts by phone
                if phone:
                    try:
                        contacts = frappe.db.get_list('Contact',
                            filters={'mobile_no': phone},
                            fields=['name']
                        )
                        for contact in contacts:
                            contact_names.add(contact['name'])
                    except Exception:
                        pass

            return contact_names

        except Exception:
            # Silently fall back to local table
            return set()

    def create_survey_campaign(self, campaign_data):
        """Create new survey campaign"""
        campaign = frappe.get_doc({
            'doctype': 'Survey Campaign',
            **campaign_data
        })
        campaign.insert()

        return campaign.name

    def distribute_survey(self, campaign):
        """Distribute survey to target audience with per-channel diagnostics."""
        try:
            # Get target audience based on filters
            recipients = self.get_survey_recipients(campaign)

            if not recipients:
                return {
                    'success': False,
                    'error': 'No recipients found matching target audience criteria',
                    'targeted_count': 0,
                    'delivered_count': 0,
                    'channel_stats': {}
                }

            # Safety threshold to prevent mass sends on misconfigured filters
            try:
                conf = frappe.get_conf() if hasattr(frappe, 'get_conf') else {}
                SAFE_MAX_TARGET = int((conf or {}).get('survey_safe_max_target', 100))
            except Exception:
                SAFE_MAX_TARGET = 100
            if len(recipients) > SAFE_MAX_TARGET:
                return {
                    'success': False,
                    'error': f'Targeted {len(recipients)} recipients exceeds safety threshold of {SAFE_MAX_TARGET}. Aborting distribution.',
                    'targeted_count': len(recipients),
                    'delivered_count': 0,
                    'channel_stats': {}
                }

            # Initialize channel stats for active channels on this campaign
            active_channels = [ch.channel for ch in (campaign.distribution_channels or []) if ch.is_active]
            channel_stats = {ch: {'attempts': 0, 'success': 0, 'failures': 0, 'reasons': {}} for ch in active_channels}

            delivered_count = 0

            for recipient in recipients:
                # Create survey response record (one per intended recipient)
                survey_response = frappe.get_doc({
                    'doctype': 'Survey Response',
                    'campaign': campaign.name,
                    'recipient_id': recipient.get('name'),
                    'recipient_email': recipient.get('email_id'),
                    'recipient_phone': recipient.get('mobile_no'),
                    'response_token': frappe.generate_hash(24),
                    'status': 'Sent',
                    'sent_time': frappe.utils.now()
                })
                survey_response.insert()

                # Try channels in configured order until one succeeds for this recipient
                for channel in (campaign.distribution_channels or []):
                    if not channel.is_active:
                        continue

                    ch_name = channel.channel
                    if ch_name not in channel_stats:
                        channel_stats[ch_name] = {'attempts': 0, 'success': 0, 'failures': 0, 'reasons': {}}

                    channel_stats[ch_name]['attempts'] += 1

                    # Prefer unified inbox conversational flow for supported social channels
                    conversational_channels = {"WhatsApp", "Facebook", "Instagram", "Telegram", "Twitter", "LinkedIn"}
                    if ch_name in conversational_channels:
                        try:
                            res = self.start_conversational_survey_session(
                                recipient=recipient,
                                campaign=campaign,
                                response_id=survey_response.name,
                                platform=ch_name,
                            )
                            ok = bool(res and isinstance(res, dict) and res.get('ok')) if isinstance(res, dict) else bool(res)
                            if ok:
                                channel_stats[ch_name]['success'] += 1
                                delivered_count += 1
                                break  # Only send via first successful channel
                            # Record failure reason if available
                            reason = None
                            if isinstance(res, dict):
                                reason = res.get('reason') or (res.get('send_result') or {}).get('error_details', {}).get('policy') or (res.get('send_result') or {}).get('message')
                            reason = reason or 'send_failed'
                            channel_stats[ch_name]['failures'] += 1
                            channel_stats[ch_name]['reasons'][reason] = channel_stats[ch_name]['reasons'].get(reason, 0) + 1
                        except Exception as _exc:
                            # Fall back to standard invite on failure path
                            channel_stats[ch_name]['failures'] += 1
                            channel_stats[ch_name]['reasons']['exception'] = channel_stats[ch_name]['reasons'].get('exception', 0) + 1

                    # Fallback: standard invite (email/SMS/unsupported socials)
                    success = self.send_survey_invitation(recipient, campaign, ch_name, survey_response.name)
                    if success:
                        channel_stats[ch_name]['success'] += 1
                        delivered_count += 1
                        break  # Only send via first successful channel
                    else:
                        # Classify common failure reasons for non-conversational paths
                        reason = 'not_supported'
                        if ch_name == 'Email' and not recipient.get('email_id'):
                            reason = 'no_email'
                        elif ch_name in ('WhatsApp', 'SMS') and not recipient.get('mobile_no'):
                            reason = 'no_mobile'
                        channel_stats[ch_name]['failures'] += 1
                        channel_stats[ch_name]['reasons'][reason] = channel_stats[ch_name]['reasons'].get(reason, 0) + 1

            # Update campaign statistics without full save (submitted docs are immutable)
            try:
                campaign.db_set('total_sent', delivered_count, update_modified=False)
            except Exception:
                frappe.db.set_value('Survey Campaign', campaign.name, 'total_sent', delivered_count)

            return {
                'success': True,
                'targeted_count': len(recipients),
                'delivered_count': delivered_count,
                'channel_stats': channel_stats,
            }

        except Exception as e:
            frappe.log_error(f"Survey distribution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_survey_recipients(self, campaign):
        """Get recipients based on target audience filters"""
        # Dynamically include optional social ID fields if present on Contact
        try:
            meta = frappe.get_meta('Contact')
        except Exception:
            meta = None

        # Optional profile metadata (for Beneficiary/Employer filtering)
        # NOTE: Beneficiary Profile and Employer Profile doctypes have been removed
        # Beneficiary Profile - removed, beneficiary data managed externally
        # Employer Profile - replaced by ERPNext Customer
        meta_b = None  # Beneficiary Profile doctype removed
        meta_e = None  # Employer Profile doctype removed - use Customer instead

        def has_field(fn):
            try:
                return bool(meta and meta.get_field(fn))
            except Exception:
                return False

        base_cols = [
            'name', 'email_id', 'mobile_no', 'first_name', 'last_name'
        ]
        optional_cols = []
        if has_field('telegram_chat_id'):
            optional_cols.append('telegram_chat_id')
        if has_field('facebook_psid'):
            optional_cols.append('facebook_psid')
        if has_field('instagram_user_id'):
            optional_cols.append('instagram_user_id')
        if has_field('linkedin_chat_id'):
            optional_cols.append('linkedin_chat_id')
        if has_field('twitter_user_id'):
            optional_cols.append('twitter_user_id')

        select_cols = ", ".join(base_cols + optional_cols)

        base_query_primary = f"""
            SELECT {select_cols}
            FROM `tabContact`
            WHERE is_primary_contact = 1
        """
        base_query_all = f"""
            SELECT {select_cols}
            FROM `tabContact`
            WHERE 1=1
        """

        # Accumulate profile filters to apply via EXISTS subqueries
        b_conds, b_vals = [], []
        e_conds, e_vals = [], []

        def _norm_key(s: str) -> str:
            return (s or '').strip().lower().replace(' ', '_').replace('-', '_')

        def _map_beneficiary_field(key: str) -> str:
            k = _norm_key(key)
            # ID mappings
            if k in ('id', 'beneficiary_id', 'beneficiary_number', 'number'):
                return 'beneficiary_number'
            # Name mappings
            if k in ('name', 'full_name', 'fullname', 'customer_name', 'customer name'):
                return 'full_name'
            if k in ('first_name', 'first name', 'fname'):
                return 'first_name'
            if k in ('last_name', 'last name', 'lname'):
                return 'last_name'
            # Contact mappings
            if k in ('email', 'email_address', 'email address', 'email_id'):
                return 'email'
            if k in ('phone', 'phone_number', 'phone number', 'telephone'):
                return 'phone'
            if k in ('mobile', 'mobile_no', 'mobile number', 'cell', 'cellphone'):
                return 'mobile'
            # Benefit mappings
            if k in ('benefit_type', 'benefit type', 'type'):
                return 'benefit_type'
            if k in ('benefit_status', 'benefit status', 'status'):
                return 'benefit_status'
            # NRC mapping
            if k in ('nrc', 'nrc_number', 'nrc number', 'national_id'):
                return 'nrc_number'
            return k

        def _map_employer_field(key: str) -> str:
            k = _norm_key(key)
            # ID mappings
            if k in ('id', 'code', 'employer_id', 'employer_number', 'employer_code'):
                return 'employer_code'
            # Name mappings
            if k in ('name', 'employer_name', 'company_name', 'company name'):
                return 'employer_name'
            # Contact mappings
            if k in ('email', 'email_address', 'email address', 'email_id'):
                return 'email'
            if k in ('phone', 'phone_number', 'phone number', 'telephone'):
                return 'phone'
            if k in ('mobile', 'mobile_no', 'mobile number', 'cell', 'cellphone'):
                return 'mobile'
            return k

        def _add_profile_cond(meta_dt, fieldname: str, op: str, val: str, out_sql: list, out_vals: list, alias: str):
            try:
                # verify field exists on target doctype
                if not meta_dt:
                    frappe.log_warning(f"Survey filter: DocType metadata not available for alias '{alias}'")
                    return
                if not meta_dt.get_field(fieldname):
                    dt_name = meta_dt.name if hasattr(meta_dt, 'name') else 'Unknown'
                    frappe.log_warning(f"Survey filter: Field '{fieldname}' not found on {dt_name}. Check your filter field name.")
                    return
                if not val:
                    return
                if op == 'equals':
                    out_sql.append(f"LOWER(TRIM({alias}.`{fieldname}`)) = LOWER(TRIM(%s))")
                    out_vals.append(val)
                elif op == 'contains':
                    out_sql.append(f"LOWER(TRIM({alias}.`{fieldname}`)) LIKE LOWER(%s)")
                    out_vals.append(f"%{val}%")
                elif op == 'in':
                    parts = [p.strip() for p in (val or '').split(',') if p.strip()]
                    if parts:
                        placeholders = ', '.join(['LOWER(%s)'] * len(parts))
                        out_sql.append(f"LOWER({alias}.`{fieldname}`) IN ({placeholders})")
                        out_vals.extend(parts)
                elif op == 'greater_than':
                    out_sql.append(f"{alias}.`{fieldname}` > %s")
                    out_vals.append(val)
                elif op == 'less_than':
                    out_sql.append(f"{alias}.`{fieldname}` < %s")
                    out_vals.append(val)
            except Exception as e:
                frappe.log_warning(f"Survey filter error: {str(e)}")
                return

        conditions = []
        values = []

        # Detect optional fields on Contact used for filtering
        has_stakeholder_type = False
        try:
            has_stakeholder_type = bool(meta and meta.get_field('stakeholder_type'))
        except Exception:
            has_stakeholder_type = False

        # Process target audience filters
        for filter_item in campaign.target_audience:
            ftype = (filter_item.filter_type or '').strip()
            fop = (filter_item.filter_operator or '').strip()
            fval = (filter_item.filter_value or '').strip()
            ffield = (filter_item.filter_field or '').strip()


            # Beneficiary / Employer profile-driven filters
            if ftype == 'Beneficiary':
                # Map alias labels to real fields; then add a profile condition
                fkey = _map_beneficiary_field(ffield)
                _add_profile_cond(meta_b, fkey, fop, fval, b_conds, b_vals, 'bp')
            elif ftype == 'Employer':
                fkey = _map_employer_field(ffield)
                _add_profile_cond(meta_e, fkey, fop, fval, e_conds, e_vals, 'ep')

            elif ftype == 'Date Range':
                # Filter by creation date (or another provided field) if present
                field = ffield or 'creation'
                if field not in ('creation',):
                    # Limit to safe field(s) to avoid SQL errors
                    field = 'creation'
                if fop == 'greater_than' and fval:
                    conditions.append(f"{field} > %s")
                    values.append(fval)
                elif fop == 'less_than' and fval:
                    conditions.append(f"{field} < %s")
                    values.append(fval)

            elif ftype == 'Channel':
                # Restrict to contacts that have the required identifier for the channel
                ch = fval
                channel_field_map = {
                    'Telegram': 'telegram_chat_id',
                    'Facebook': 'facebook_psid',
                    'Instagram': 'instagram_user_id',
                    'Email': 'email_id',
                    'WhatsApp': 'mobile_no',
                    'SMS': 'mobile_no',
                }
                field = channel_field_map.get(ch)
                if field and has_field(field):
                    conditions.append(f"COALESCE({field}, '') <> ''")

            elif ftype == 'Custom Field':
                # Allow a safe subset of fields to be filtered directly (case-insensitive with aliases)
                field_map = {
                    'name': 'name',
                    'full_name': "CONCAT_WS(' ', first_name, last_name)",
                    'first_name': 'first_name',
                    'last_name': 'last_name',
                    'email_id': 'email_id',
                    'mobile_no': 'mobile_no',
                    'telegram_chat_id': 'telegram_chat_id',
                    'facebook_psid': 'facebook_psid',
                    'instagram_user_id': 'instagram_user_id',
                }
                # Normalize field key: lower-case and convert spaces/hyphens to underscores
                fkey = (ffield or '').strip().lower().replace(' ', '_').replace('-', '_')
                # Common aliases
                if fkey in ('full name', 'fullname'):
                    fkey = 'full_name'
                field_sql = field_map.get(fkey)
                # Normalize smart quotes in value
                def _norm_val(v: str) -> str:
                    return (v or '').strip().replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
                if field_sql and fval:
                    val = _norm_val(fval)
                    if fop == 'equals':
                        conditions.append(f"LOWER(TRIM({field_sql})) = LOWER(TRIM(%s))")
                        values.append(val)
                    elif fop == 'contains':
                        conditions.append(f"LOWER(TRIM({field_sql})) LIKE LOWER(%s)")
                        values.append(f"%{val}%")
                    elif fop == 'in':
                        vals = [_norm_val(v) for v in fval.split(',') if _norm_val(v)]
                        if vals:
                            placeholders = ', '.join(['LOWER(%s)'] * len(vals))
                            conditions.append(f"LOWER({field_sql}) IN ({placeholders})")
                            values.extend(vals)

        # Apply profile EXISTS constraints if present
        # First, try to get beneficiaries from CoreBusiness if filtering by Beneficiary
        beneficiary_contacts = set()
        if any(fi.filter_type == 'Beneficiary' for fi in (campaign.target_audience or [])):
            # Get the beneficiary filter details
            for filter_item in (campaign.target_audience or []):
                if filter_item.filter_type == 'Beneficiary':
                    ffield = _map_beneficiary_field(filter_item.filter_field or '')
                    fop = filter_item.filter_operator or ''
                    fval = filter_item.filter_value or ''

                    if ffield and fop and fval:
                        try:
                            # Try to get beneficiaries from CoreBusiness
                            beneficiary_contacts = self._get_beneficiary_contacts_from_corebusiness(ffield, fop, fval)
                        except Exception:
                            beneficiary_contacts = set()

                        # If we got beneficiaries from CoreBusiness, use them
                        if beneficiary_contacts:
                            placeholders = ', '.join(['%s'] * len(beneficiary_contacts))
                            conditions.append(f"`tabContact`.name IN ({placeholders})")
                            values.extend(list(beneficiary_contacts))
                            break

            # NOTE: Beneficiary Profile doctype has been removed - beneficiary data managed externally
            # If CoreBusiness didn't return results, skip local Beneficiary Profile table fallback
            if not beneficiary_contacts and b_conds:
                # Beneficiary Profile table no longer exists - skip this fallback
                pass

        # Apply employer filtering from CoreBusiness
        employer_contacts = set()
        if any(fi.filter_type == 'Employer' for fi in (campaign.target_audience or [])):
            # Get the employer filter details
            for filter_item in (campaign.target_audience or []):
                if filter_item.filter_type == 'Employer':
                    ffield = _map_employer_field(filter_item.filter_field or '')
                    fop = filter_item.filter_operator or ''
                    fval = filter_item.filter_value or ''

                    if ffield and fop and fval:
                        try:
                            # Try to get employers from CoreBusiness
                            employer_contacts = self._get_employer_contacts_from_corebusiness(ffield, fop, fval)
                        except Exception:
                            employer_contacts = set()

                        # If we got employers from CoreBusiness, use them
                        if employer_contacts:
                            placeholders = ', '.join(['%s'] * len(employer_contacts))
                            conditions.append(f"`tabContact`.name IN ({placeholders})")
                            values.extend(list(employer_contacts))
                            break

            # NOTE: Employer Profile doctype has been removed - using ERPNext Customer instead
            # If CoreBusiness didn't return results, try ERPNext Customer table fallback
            if not employer_contacts and e_conds:
                # Use ERPNext Customer table instead of Employer Profile
                c_pred = (
                    "(c.name IN (SELECT dl.link_name FROM `tabDynamic Link` dl "
                    "WHERE dl.parenttype='Contact' AND dl.link_doctype='Customer' AND dl.parent = `tabContact`.name) "
                    "OR (COALESCE(c.email_id,'') <> '' AND LOWER(TRIM(c.email_id)) = LOWER(TRIM(`tabContact`.email_id))) "
                    "OR (COALESCE(c.mobile_no,'') <> '' AND TRIM(c.mobile_no) = TRIM(`tabContact`.mobile_no)))"
                )
                # Map e_conds from old Employer Profile fields to Customer fields
                # e_conds references old field names - skip if mapping not possible
                # For now, just use the customer_type filter to ensure we get companies
                conditions.append(f"EXISTS (SELECT 1 FROM `tabCustomer` c WHERE c.customer_type='Company' AND {c_pred})")

        # Build final queries (primary-only first), then fallback to all contacts
        query_primary = base_query_primary + (f" AND {' AND '.join(conditions)}" if conditions else '')
        recipients = frappe.db.sql(query_primary, values, as_dict=True)
        if not recipients:
            query_all = base_query_all + (f" AND {' AND '.join(conditions)}" if conditions else '')
            recipients = frappe.db.sql(query_all, values, as_dict=True)
        return recipients

    def send_survey_invitation(self, recipient, campaign, channel, response_id):
        """Send survey invitation via specified channel"""
        try:
            survey_link = self.generate_survey_link(response_id)

            message = f"""
Dear {recipient.get('first_name', 'Valued Customer')},

We would appreciate your feedback on our services. Please take a few minutes to complete our survey:

{survey_link}

Thank you for your time.

Best regards,
WCFCB Team
            """.strip()

            if channel == 'Email' and recipient.get('email_id'):
                frappe.sendmail(
                    recipients=[recipient.get('email_id')],
                    subject=f"Survey: {campaign.campaign_name}",
                    message=message
                )
                return True

            elif channel == 'WhatsApp' and recipient.get('mobile_no'):
                # For WhatsApp, unified inbox conversational flow is preferred and handled upstream.
                # This fallback sends a simple invite only when conversational start failed.
                from assistant_crm.services.whatsapp_service import WhatsAppService
                whatsapp = WhatsAppService()
                result = whatsapp.send_message(recipient.get('mobile_no'), message)
                return result is not None

            elif channel == 'SMS' and recipient.get('mobile_no'):
                # Implement SMS sending
                # This would integrate with your SMS provider
                return True

            return False

        except Exception as e:
            frappe.log_error(f"Failed to send survey invitation: {str(e)}")
            return False

    def start_conversational_survey_session(self, recipient, campaign, response_id: str, platform: str):
        """Send a survey invitation link via unified inbox and close the conversation.
        Returns a diagnostics dict: { ok: bool, reason?: str, send_result?: dict }.
        - Does NOT keep a conversational survey session active
        - Immediately marks the conversation Resolved after sending
        - Subsequent inbound messages are parsed as normal chats
        """
        try:
            from frappe.utils import now
            from assistant_crm.api.social_media_ports import get_platform_integration, send_social_media_message
            import json as _json

            # Resolve platform recipient identifier and normalize
            dest_id = None
            if platform == 'WhatsApp' and recipient.get('mobile_no'):
                dest_id = recipient.get('mobile_no')
            elif platform == 'Telegram':
                # Primary: use chat_id if available on Contact
                dest_id = recipient.get('telegram_chat_id') or None
                # Optional best-effort: phone-based outreach isn't supported by Bot API;
                # keep behavior safe-by-default and fall back if chat_id missing.
                if not dest_id and recipient.get('mobile_no'):
                    # Do NOT attempt to send via phone as Telegram Bot; will be skipped safely
                    dest_id = None
            elif platform == 'Facebook':
                # Prefer PSID if available
                dest_id = recipient.get('facebook_psid') or None
            elif platform == 'Instagram':
                # Prefer Instagram user ID if available
                dest_id = recipient.get('instagram_user_id') or None
            elif platform == 'Twitter':
                dest_id = recipient.get('twitter_user_id') or None
            elif platform == 'LinkedIn':
                dest_id = recipient.get('linkedin_chat_id') or None

            if dest_id is not None:
                try:
                    dest_id = str(dest_id).strip()
                except Exception:
                    pass

            if not dest_id:
                return {'ok': False, 'reason': 'no_identifier'}

            # Create or reuse conversation
            plat = get_platform_integration(platform)
            if not plat or not plat.is_configured:
                return {'ok': False, 'reason': 'platform_not_configured'}

            # Build a safe customer display name
            first = (recipient.get('first_name') or '').strip()
            last = (recipient.get('last_name') or '').strip()
            customer_name = (f"{first} {last}".strip() or (recipient.get('email_id') or '').strip() or (recipient.get('mobile_no') or '').strip() or 'Customer')
            platform_data = {
                "conversation_id": dest_id,
                "customer_name": customer_name,
                "customer_platform_id": dest_id,
                "customer_phone": recipient.get('mobile_no'),
                "customer_email": recipient.get('email_id'),
                "initial_message": f"Survey: {campaign.campaign_name}"
            }
            conversation_name = plat.create_unified_inbox_conversation(
                platform_data,
                force_new=True,
                tags=["Survey"],
                subject=f"Survey: {campaign.campaign_name}",
                survey_label=campaign.campaign_name,
            )
            if not conversation_name:
                return {'ok': False, 'reason': 'conversation_not_created'}

            conversation_doc = frappe.get_doc('Unified Inbox Conversation', conversation_name)

            # Lock AI for this conversation while survey is being sent
            try:
                conversation_doc.db_set('ai_mode', 'Off')
                conversation_doc.db_set('status', 'Survey Active')
            except Exception:
                pass

            # Build survey context
            survey_ctx = {
                "active": True,
                "campaign_name": campaign.name,
                "campaign_label": campaign.campaign_name,
                "response_id": response_id,
                "index": 0,
                "token": frappe.generate_hash(12),
                "expires_at": now(),
            }

            # Merge into conversation context
            try:
                existing_ctx = {}
                if conversation_doc.conversation_context:
                    existing_ctx = _json.loads(conversation_doc.conversation_context) if isinstance(conversation_doc.conversation_context, str) else conversation_doc.conversation_context
                existing_ctx = existing_ctx or {}
                existing_ctx['survey'] = survey_ctx
                conversation_doc.db_set('conversation_context', _json.dumps(existing_ctx), update_modified=True)
            except Exception:
                pass

            # Prepare link-based intro instead of inline Q1
            intro = f"WCFCB Survey: {campaign.campaign_name}\nWe appreciate your time. A few brief questions. Reply STOP at any time to end."
            form_link = self.generate_survey_link(response_id)
            message_text = f"{intro}\n\nPlease complete this short form:\n{form_link}\n\nIf the link doesn't open, reply 'HELP'."

            # Record outbound message in inbox
            try:
                out_doc = frappe.get_doc({
                    'doctype': 'Unified Inbox Message',
                    'conversation': conversation_name,
                    'platform': platform,
                    'direction': 'Outbound',
                    'message_type': 'text',
                    'message_content': message_text,
                    'sender_name': 'Survey Bot',
                    'sender_id': 'survey_bot',
                    'timestamp': now(),
                    'processed_by_ai': 1,
                })
                out_doc.insert(ignore_permissions=True)
            except Exception:
                pass

            # Send via platform
            send_res = send_social_media_message(platform, conversation_name, message_text)
            ok = bool(send_res and send_res.get('status') == 'success')
            if ok:
                # Immediately mark survey not active and close the conversation so
                # subsequent inbound messages are parsed as normal chats.
                try:
                    # Update survey context to inactive
                    try:
                        current_ctx = {}
                        if conversation_doc.conversation_context:
                            current_ctx = _json.loads(conversation_doc.conversation_context) if isinstance(conversation_doc.conversation_context, str) else conversation_doc.conversation_context
                        current_ctx = current_ctx or {}
                    except Exception:
                        current_ctx = {}
                    if 'survey' in current_ctx and isinstance(current_ctx['survey'], dict):
                        try:
                            current_ctx['survey']['active'] = False
                        except Exception:
                            # fallback: remove key
                            try:
                                del current_ctx['survey']
                            except Exception:
                                pass
                    conversation_doc.db_set('conversation_context', _json.dumps(current_ctx), update_modified=True)
                except Exception:
                    pass
                try:
                    conversation_doc.db_set('ai_mode', 'Auto')
                except Exception:
                    pass
                try:
                    if hasattr(conversation_doc, 'mark_resolved'):
                        conversation_doc.mark_resolved("Survey invitation sent; session closed immediately")
                    else:
                        conversation_doc.db_set('status', 'Resolved')
                except Exception:
                    pass
                return {'ok': True, 'send_result': send_res}
            else:
                reason = None
                try:
                    reason = (send_res or {}).get('error_details', {}).get('policy')
                except Exception:
                    pass
                return {'ok': False, 'reason': reason or 'send_failed', 'send_result': send_res}

        except Exception as e:
            frappe.log_error(f"Failed to start conversational survey session: {str(e)}")
            return {'ok': False, 'reason': 'exception', 'error': str(e)}

    def generate_survey_link(self, response_id):
        """Generate unique survey link using per-response token.
        Build a robust URL that avoids double slashes and overly long/fragile paths.
        """
        site_url = (frappe.utils.get_url() or '').rstrip('/')
        try:
            token = frappe.db.get_value('Survey Response', response_id, 'response_token')
        except Exception:
            token = None
        if not token:
            # fallback for legacy records; generate one
            try:
                token = frappe.generate_hash(24)
                frappe.db.set_value('Survey Response', response_id, 'response_token', token)
            except Exception:
                pass
        # Build URL; avoid depending on optional System Settings fields
        if not site_url:
            return f"/survey?t={token}"
        return f"{site_url}/survey?t={token}"

    def process_survey_response(self, response_id, answers):
        """Process submitted survey response"""
        try:
            survey_response = frappe.get_doc('Survey Response', response_id)

            # Update response record
            survey_response.status = 'Completed'
            survey_response.response_time = frappe.utils.now()
            survey_response.answers = json.dumps(answers) if isinstance(answers, (list, dict)) else answers

            # Calculate sentiment for text responses
            text_responses = []
            for answer in answers:
                if answer.get('type') == 'text' and answer.get('value'):
                    text_responses.append(answer['value'])

            if text_responses:
                sentiment_score = self.analyze_sentiment(' '.join(text_responses))
                survey_response.sentiment_score = sentiment_score

            survey_response.save()

            # Update campaign statistics
            self.update_campaign_statistics(survey_response.campaign)

            # Check for follow-up requirements
            self.check_follow_up_requirements(survey_response, answers)

            return {
                'success': True,
                'message': 'Thank you for your response!'
            }

        except Exception as e:
            frappe.log_error(f"Failed to process survey response: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to submit response'
            }

    def analyze_sentiment(self, text):
        """Analyze sentiment of text response"""
        positive_keywords = self.sentiment_analyzer['positive_keywords']
        negative_keywords = self.sentiment_analyzer['negative_keywords']

        text_lower = text.lower()
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)

        if positive_count > negative_count:
            return min(1.0, positive_count * 0.2)  # Positive sentiment
        elif negative_count > positive_count:
            return max(-1.0, negative_count * -0.2)  # Negative sentiment
        else:
            return 0.0  # Neutral

    def update_campaign_statistics(self, campaign_name):
        """Update campaign response statistics"""
        stats = frappe.db.sql("""
            SELECT COUNT(*) as total_responses,
                   COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_responses
            FROM `tabSurvey Response`
            WHERE campaign = %s
        """, (campaign_name,), as_dict=True)[0]

        campaign = frappe.get_doc('Survey Campaign', campaign_name)
        completed = stats.get('completed_responses', 0) or 0
        total_sent = campaign.total_sent or 0

        # Use db_set to update submitted docs safely
        try:
            campaign.db_set('total_responses', completed, update_modified=False)
        except Exception:
            frappe.db.set_value('Survey Campaign', campaign_name, 'total_responses', completed)

        try:
            rate = (completed / total_sent) * 100 if total_sent > 0 else 0
            campaign.db_set('response_rate', rate, update_modified=False)
        except Exception:
            frappe.db.set_value('Survey Campaign', campaign_name, 'response_rate', rate)

        # Calculate average rating
        avg_rating = self.calculate_average_rating(campaign_name) or 0
        try:
            campaign.db_set('average_rating', avg_rating, update_modified=False)
        except Exception:
            frappe.db.set_value('Survey Campaign', campaign_name, 'average_rating', avg_rating)

    def calculate_average_rating(self, campaign_name):
        """Calculate average rating for campaign"""
        responses = frappe.db.sql("""
            SELECT answers
            FROM `tabSurvey Response`
            WHERE campaign = %s AND status = 'Completed'
        """, (campaign_name,), as_dict=True)

        ratings = []
        for response in responses:
            try:
                answers_data = json.loads(response['answers']) if isinstance(response['answers'], str) else response['answers']
                for answer in answers_data:
                    if answer.get('type') == 'rating' and answer.get('value'):
                        ratings.append(float(answer['value']))
            except:
                continue

        return sum(ratings) / len(ratings) if ratings else 0

    def check_follow_up_requirements(self, survey_response, answers):
        """Check if follow-up is required based on responses and create ToDo if needed.
        - Uses per-campaign thresholds when available
        - Respects permissions (no ignore_permissions)
        - Idempotent: won't create duplicates for the same Survey Response
        """
        try:
            # Idempotency: if a ToDo already exists for this response, skip
            if frappe.db.exists('ToDo', {
                'reference_type': 'Survey Response',
                'reference_name': survey_response.name
            }):
                return

            # Defaults
            low_score_default = 2
            negative_sent_default = -0.3
            assignee_default = 'Administrator'

            # Load campaign-specific settings if available
            low_thresh = low_score_default
            neg_thresh = negative_sent_default
            assignee = assignee_default
            try:
                if getattr(survey_response, 'campaign', None):
                    camp = frappe.get_doc('Survey Campaign', survey_response.campaign)
                    low_thresh = int(getattr(camp, 'low_score_threshold', None) or low_score_default)
                    neg_thresh = float(getattr(camp, 'negative_sentiment_threshold', None) or negative_sent_default)
                    assignee = getattr(camp, 'follow_up_assignee', None) or assignee_default
            except Exception:
                pass

            follow_up_required = False

            # Check for low ratings
            for answer in (answers or []):
                try:
                    if answer.get('type') == 'rating' and answer.get('value') is not None:
                        rating = float(answer['value'])
                        if rating <= low_thresh:
                            follow_up_required = True
                            break
                except Exception:
                    continue

            # Check for negative sentiment
            try:
                if survey_response.sentiment_score is not None and float(survey_response.sentiment_score) < neg_thresh:
                    follow_up_required = True
            except Exception:
                pass

            if follow_up_required:
                # Create follow-up task (respects permissions; will fail if caller lacks rights)
                frappe.get_doc({
                    'doctype': 'ToDo',
                    'description': f'Follow-up required for survey response {survey_response.name}',
                    'reference_type': 'Survey Response',
                    'reference_name': survey_response.name,
                    'assigned_by': 'Administrator',
                    'owner': assignee,
                    'priority': 'High'
                }).insert()
        except Exception as e:
            frappe.log_error(f"check_follow_up_requirements failed: {str(e)}", "Survey Follow-up")


    def create_follow_up_from_response(response_name: str, answers=None):
        """Background-safe helper to create follow-up ToDo for a Survey Response.
        Called via enqueue to ensure proper user context.
        """
        try:
            resp = frappe.get_doc('Survey Response', response_name)
            service = SurveyService()
            service.check_follow_up_requirements(resp, answers or [])
        except Exception as e:
            frappe.log_error(f"create_follow_up_from_response failed: {str(e)}", "Survey Follow-up")

    @frappe.whitelist()
    def admin_backfill_low_score_followups(days: int = 7):
        """One-off admin utility to backfill ToDos for low/negative scores in recent responses."""
        try:
            cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -int(days))
            rows = frappe.db.sql(
                """
                SELECT name, answers, sentiment_score, campaign
                FROM `tabSurvey Response`
                WHERE status = 'Completed' AND response_time >= %s
                """,
                (cutoff,),
                as_dict=True,
            )
            service = SurveyService()
            created = 0
            for r in rows:
                # Skip if ToDo already exists for this response
                if frappe.db.exists('ToDo', {'reference_type': 'Survey Response', 'reference_name': r['name']}):
                    continue
                try:
                    ans = json.loads(r['answers']) if isinstance(r['answers'], str) else (r['answers'] or [])
                except Exception:
                    ans = []
                # Build a lightweight doc proxy
                resp = frappe.get_doc('Survey Response', r['name'])
                service.check_follow_up_requirements(resp, ans)
                # If ToDo got created, count it
                if frappe.db.exists('ToDo', {'reference_type': 'Survey Response', 'reference_name': r['name']}):
                    created += 1
            return {"success": True, "created": created, "scanned": len(rows)}
        except Exception as e:
            frappe.log_error(f"admin_backfill_low_score_followups failed: {str(e)}", "Survey Follow-up")
            return {"success": False, "error": str(e)}

    def sweep_low_score_followups(hours: int = 2):
        """Scheduled sweep to catch any missed low-score follow-ups in the last N hours."""
        try:
            cutoff = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-int(hours))
            rows = frappe.db.sql(
                """
                SELECT name, answers
                FROM `tabSurvey Response`
                WHERE status = 'Completed' AND response_time >= %s
                """,
                (cutoff,),
                as_dict=True,
            )
            service = SurveyService()
            created = 0
            for r in rows:
                if frappe.db.exists('ToDo', {'reference_type': 'Survey Response', 'reference_name': r['name']}):
                    continue
                try:
                    ans = json.loads(r['answers']) if isinstance(r['answers'], str) else (r['answers'] or [])
                except Exception:
                    ans = []
                resp = frappe.get_doc('Survey Response', r['name'])
                service.check_follow_up_requirements(resp, ans)
                if frappe.db.exists('ToDo', {'reference_type': 'Survey Response', 'reference_name': r['name']}):
                    created += 1
            return {"success": True, "created": created, "scanned": len(rows)}
        except Exception as e:
            frappe.log_error(f"sweep_low_score_followups failed: {str(e)}", "Survey Follow-up")
            return {"success": False, "error": str(e)}

    def send_reminder_notifications(self):
        """Send reminder notifications to non-responders"""
        # Get campaigns with active reminders
        active_campaigns = frappe.db.sql("""
            SELECT name, campaign_name, reminder_frequency, max_reminders
            FROM `tabSurvey Campaign`
            WHERE start_date <= NOW() AND end_date >= NOW()
            AND reminder_frequency != 'None'
            AND status = 'Active'
        """, as_dict=True)

        for campaign in active_campaigns:
            # Get non-responders who haven't reached max reminders
            non_responders = frappe.db.sql("""
                SELECT name, recipient_email, recipient_phone, reminder_count
                FROM `tabSurvey Response`
                WHERE campaign = %s AND status = 'Sent'
                AND reminder_count < %s
            """, (campaign['name'], campaign['max_reminders']), as_dict=True)

            for responder in non_responders:
                # Check if reminder is due based on frequency
                if self.is_reminder_due(responder, campaign['reminder_frequency']):
                    self.send_survey_reminder(responder, campaign)

    def is_reminder_due(self, responder, frequency):
        """Check if reminder is due based on frequency"""
        last_reminder = frappe.db.get_value('Survey Response', responder['name'], 'modified')

        if frequency == 'Daily':
            return (datetime.now() - last_reminder).days >= 1
        elif frequency == 'Weekly':
            return (datetime.now() - last_reminder).days >= 7

        return False

    def send_survey_reminder(self, responder, campaign):
        """Send reminder for survey response"""
        try:
            survey_link = self.generate_survey_link(responder['name'])

            message = f"""
Reminder: We're still waiting for your feedback!

Please take a few minutes to complete our survey:
{survey_link}

Thank you,
WCFCB Team
            """.strip()

            # Send reminder via email if available
            if responder.get('recipient_email'):
                frappe.sendmail(
                    recipients=[responder['recipient_email']],
                    subject=f"Reminder: {campaign['campaign_name']}",
                    message=message
                )

            # Update reminder count
            frappe.db.set_value('Survey Response', responder['name'], 'reminder_count',
                              responder.get('reminder_count', 0) + 1)

        except Exception as e:
            frappe.log_error(f"Failed to send survey reminder: {str(e)}")

    def generate_survey_analytics(self, campaign_name):
        """Generate comprehensive survey analytics"""
        # Get all responses
        responses = frappe.db.sql("""
            SELECT answers, sentiment_score, response_time
            FROM `tabSurvey Response`
            WHERE campaign = %s AND status = 'Completed'
        """, (campaign_name,), as_dict=True)

        analytics = {
            'total_responses': len(responses),
            'sentiment_distribution': self.calculate_sentiment_distribution(responses),
            'response_trends': self.calculate_response_trends(responses),
            'key_insights': self.extract_key_insights(responses)
        }

        return analytics

    def calculate_sentiment_distribution(self, responses):
        """Calculate sentiment distribution"""
        positive = sum(1 for r in responses if r.get('sentiment_score', 0) > 0.3)
        negative = sum(1 for r in responses if r.get('sentiment_score', 0) < -0.3)
        neutral = len(responses) - positive - negative

        return {
            'positive': positive,
            'negative': negative,
            'neutral': neutral
        }

    def calculate_response_trends(self, responses):
        """Calculate response trends over time"""
        from collections import defaultdict

        daily_responses = defaultdict(int)
        for response in responses:
            if response.get('response_time'):
                date = frappe.utils.getdate(response['response_time'])
                daily_responses[str(date)] += 1

        return [{'date': date, 'count': count} for date, count in sorted(daily_responses.items())]

    def extract_key_insights(self, responses):
        """Extract key insights from survey responses"""
        insights = []

        if not responses:
            return insights

        # Sentiment insights
        sentiment_dist = self.calculate_sentiment_distribution(responses)
        total = len(responses)

        if sentiment_dist['positive'] / total > 0.7:
            insights.append("High customer satisfaction - 70%+ positive responses")
        elif sentiment_dist['negative'] / total > 0.3:
            insights.append("Attention needed - 30%+ negative responses")

        # Response rate insights
        if total > 50:
            insights.append(f"Good response rate with {total} completed surveys")
        elif total < 10:
            insights.append("Low response rate - consider follow-up campaigns")

        return insights
