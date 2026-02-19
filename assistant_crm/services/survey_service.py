import frappe
from frappe import _
import json
from datetime import datetime

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
        Falls back to local Contact/Customer doctype filtering if CoreBusiness is not available.
        """
        contact_names = set()

        # First try CoreBusiness if available
        try:
            try:
                cbs_settings = frappe.get_single('CoreBusiness Settings')
                if cbs_settings.enabled:
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

                    cbs_columns = field_map.get(filter_field, [])
                    if cbs_columns:
                        where_clauses = []
                        for col in cbs_columns:
                            if filter_operator == 'equals':
                                where_clauses.append(f"LOWER({col}) = LOWER('{filter_value}')")
                            elif filter_operator == 'contains':
                                where_clauses.append(f"LOWER({col}) LIKE LOWER('%{filter_value}%')")
                            elif filter_operator == 'in':
                                values = [f"'{v.strip()}'" for v in filter_value.split(',')]
                                where_clauses.append(f"LOWER({col}) IN ({','.join(values)})")

                        if where_clauses:
                            where_condition = ' OR '.join(where_clauses)
                            query = f"""
                                SELECT BENEFICIARY_ID, FIRST_NAME, LAST_NAME, EMAIL_ADDRESS, PHONE_NUMBER, NRC_NUMBER
                                FROM BENEFICIARIES
                                WHERE STATUS = 'ACTIVE' AND ({where_condition})
                            """
                            results = connector.execute_query(query)
                            connector.close_connection()

                            if results:
                                for beneficiary in results:
                                    email = beneficiary.get('EMAIL_ADDRESS', '').strip()
                                    phone = beneficiary.get('PHONE_NUMBER', '').strip()
                                    if email:
                                        contacts = frappe.db.get_list('Contact', filters={'email_id': email}, fields=['name'])
                                        for contact in contacts:
                                            contact_names.add(contact['name'])
                                    if phone:
                                        contacts = frappe.db.get_list('Contact', filters={'mobile_no': phone}, fields=['name'])
                                        for contact in contacts:
                                            contact_names.add(contact['name'])
                                if contact_names:
                                    return contact_names
            except Exception:
                pass  # Fall through to local filtering
        except Exception:
            pass

        # Fall back to local ERPNext Contact doctype filtering (beneficiary = Customer type Individual)
        return self._get_beneficiary_contacts_from_erpnext(filter_field, filter_operator, filter_value)

    def _get_beneficiary_contacts_from_erpnext(self, filter_field, filter_operator, filter_value):
        """
        Query ERPNext Contact doctype for beneficiaries (individuals) matching the filter conditions.
        Beneficiaries are represented as Contacts linked to Customers of type 'Individual'.
        Returns a set of Contact names matching the filter criteria.
        """
        contact_names = set()

        try:
            # Map filter field to Contact/Customer fields
            contact_field_map = {
                'full_name': 'full_name',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'email': 'email_id',
                'email_id': 'email_id',
                'mobile': 'mobile_no',
                'mobile_no': 'mobile_no',
                'phone': 'phone',
            }

            # Fields that need to query Customer table
            customer_field_map = {
                'customer_name': 'customer_name',
                'beneficiary_number': 'name',  # Customer.name as beneficiary ID
                'nrc_number': 'tax_id',  # Tax ID can be used for NRC
                'territory': 'territory',
                'customer_group': 'customer_group',
            }

            # Build query based on field type
            if filter_field in contact_field_map:
                # Direct Contact field filtering
                db_field = contact_field_map[filter_field]
                contact_names = self._query_contacts_by_field(db_field, filter_operator, filter_value)

            elif filter_field in customer_field_map:
                # Customer field filtering - get contacts linked to matching customers
                db_field = customer_field_map[filter_field]
                contact_names = self._query_contacts_via_customer(db_field, filter_operator, filter_value, customer_type='Individual')
            else:
                # Try as a custom field on Contact
                contact_names = self._query_contacts_by_field(filter_field, filter_operator, filter_value)

        except Exception as e:
            frappe.log_error(f"Error in _get_beneficiary_contacts_from_erpnext: {str(e)}")

        return contact_names

    def _query_contacts_by_field(self, field_name, operator, value):
        """Query Contact doctype by a specific field with given operator and value."""
        contact_names = set()

        try:
            # Build SQL condition based on operator
            if operator == 'equals':
                condition = f"LOWER(TRIM(`{field_name}`)) = LOWER(TRIM(%s))"
                params = [value]
            elif operator == 'contains':
                condition = f"LOWER(`{field_name}`) LIKE LOWER(%s)"
                params = [f"%{value}%"]
            elif operator == 'in':
                parts = [p.strip() for p in value.split(',') if p.strip()]
                if not parts:
                    return contact_names
                placeholders = ', '.join(['LOWER(%s)'] * len(parts))
                condition = f"LOWER(`{field_name}`) IN ({placeholders})"
                params = parts
            elif operator == 'greater_than':
                condition = f"`{field_name}` > %s"
                params = [value]
            elif operator == 'less_than':
                condition = f"`{field_name}` < %s"
                params = [value]
            elif operator in ('is_set', 'is not null'):
                condition = f"COALESCE(`{field_name}`, '') <> ''"
                params = []
            elif operator in ('is_not_set', 'is null'):
                condition = f"COALESCE(`{field_name}`, '') = ''"
                params = []
            else:
                return contact_names

            query = f"SELECT name FROM `tabContact` WHERE {condition}"
            results = frappe.db.sql(query, params, as_dict=True)

            for row in results:
                contact_names.add(row['name'])

        except Exception as e:
            frappe.log_error(f"Error in _query_contacts_by_field: {str(e)}")

        return contact_names

    def _query_contacts_via_customer(self, customer_field, operator, value, customer_type=None):
        """Query Contacts linked to Customers matching the filter criteria via Dynamic Link."""
        contact_names = set()

        try:
            # Build customer filter condition
            if operator == 'equals':
                cust_condition = f"LOWER(TRIM(c.`{customer_field}`)) = LOWER(TRIM(%s))"
                params = [value]
            elif operator == 'contains':
                cust_condition = f"LOWER(c.`{customer_field}`) LIKE LOWER(%s)"
                params = [f"%{value}%"]
            elif operator == 'in':
                parts = [p.strip() for p in value.split(',') if p.strip()]
                if not parts:
                    return contact_names
                placeholders = ', '.join(['LOWER(%s)'] * len(parts))
                cust_condition = f"LOWER(c.`{customer_field}`) IN ({placeholders})"
                params = parts
            elif operator == 'greater_than':
                cust_condition = f"c.`{customer_field}` > %s"
                params = [value]
            elif operator == 'less_than':
                cust_condition = f"c.`{customer_field}` < %s"
                params = [value]
            else:
                return contact_names

            # Add customer type filter if specified
            type_condition = ""
            if customer_type:
                type_condition = "AND c.customer_type = %s"
                params.append(customer_type)

            # Query contacts linked to matching customers via Dynamic Link
            query = f"""
                SELECT DISTINCT ct.name
                FROM `tabContact` ct
                INNER JOIN `tabDynamic Link` dl ON dl.parent = ct.name
                    AND dl.parenttype = 'Contact'
                    AND dl.link_doctype = 'Customer'
                INNER JOIN `tabCustomer` c ON c.name = dl.link_name
                WHERE {cust_condition} {type_condition}
            """
            results = frappe.db.sql(query, params, as_dict=True)

            for row in results:
                contact_names.add(row['name'])

        except Exception as e:
            frappe.log_error(f"Error in _query_contacts_via_customer: {str(e)}")

        return contact_names

    def _get_employer_contacts_from_corebusiness(self, filter_field, filter_operator, filter_value):
        """
        Query CoreBusiness for employers matching the filter conditions,
        then find corresponding Contact records by email or mobile.
        Falls back to ERPNext Customer doctype (type Company) if CoreBusiness is not available.
        Returns a set of Contact names that match the employer filters.
        """
        contact_names = set()

        # First try CoreBusiness if available
        try:
            try:
                cbs_settings = frappe.get_single('CoreBusiness Settings')
                if cbs_settings.enabled:
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

                    cbs_columns = field_map.get(filter_field, [])
                    if cbs_columns:
                        where_clauses = []
                        for col in cbs_columns:
                            if filter_operator == 'equals':
                                where_clauses.append(f"LOWER({col}) = LOWER('{filter_value}')")
                            elif filter_operator == 'contains':
                                where_clauses.append(f"LOWER({col}) LIKE LOWER('%{filter_value}%')")
                            elif filter_operator == 'in':
                                values = [f"'{v.strip()}'" for v in filter_value.split(',')]
                                where_clauses.append(f"LOWER({col}) IN ({','.join(values)})")

                        if where_clauses:
                            where_condition = ' OR '.join(where_clauses)
                            query = f"""
                                SELECT DISTINCT EMPLOYER_NAME, EMPLOYER_EMAIL, EMPLOYER_PHONE
                                FROM BENEFICIARIES
                                WHERE STATUS = 'ACTIVE' AND ({where_condition})
                            """
                            results = connector.execute_query(query)
                            connector.close_connection()

                            if results:
                                for employer in results:
                                    email = employer.get('EMPLOYER_EMAIL', '').strip()
                                    phone = employer.get('EMPLOYER_PHONE', '').strip()
                                    if email:
                                        contacts = frappe.db.get_list('Contact', filters={'email_id': email}, fields=['name'])
                                        for contact in contacts:
                                            contact_names.add(contact['name'])
                                    if phone:
                                        contacts = frappe.db.get_list('Contact', filters={'mobile_no': phone}, fields=['name'])
                                        for contact in contacts:
                                            contact_names.add(contact['name'])
                                if contact_names:
                                    return contact_names
            except Exception:
                pass  # Fall through to local filtering
        except Exception:
            pass

        # Fall back to ERPNext Customer doctype (employers = Customers of type Company)
        return self._get_employer_contacts_from_erpnext(filter_field, filter_operator, filter_value)

    def _get_employer_contacts_from_erpnext(self, filter_field, filter_operator, filter_value):
        """
        Query ERPNext Customer doctype for employers (companies) matching the filter conditions.
        Employers are represented as Customers of type 'Company'.
        Returns Contacts linked to matching Customers via Dynamic Link.
        """
        contact_names = set()

        try:
            # Map filter field to Customer doctype fields
            customer_field_map = {
                'employer_name': 'customer_name',
                'customer_name': 'customer_name',
                'name': 'name',
                'employer_code': 'name',  # Customer name serves as employer code
                'email': 'email_id',
                'email_id': 'email_id',
                'mobile': 'mobile_no',
                'mobile_no': 'mobile_no',
                'phone': 'mobile_no',
                'territory': 'territory',
                'customer_group': 'customer_group',
                'industry': 'industry',
                'tax_id': 'tax_id',
            }

            db_field = customer_field_map.get(filter_field)

            if db_field:
                # Query contacts linked to matching Company-type customers
                contact_names = self._query_contacts_via_customer(db_field, filter_operator, filter_value, customer_type='Company')
            else:
                # Try as a custom field on Customer
                contact_names = self._query_contacts_via_customer(filter_field, filter_operator, filter_value, customer_type='Company')

        except Exception as e:
            frappe.log_error(f"Error in _get_employer_contacts_from_erpnext: {str(e)}")

        return contact_names

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

                # Try ALL active channels for this recipient (skip failures, continue to next)
                recipient_delivered = False
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
                                recipient_delivered = True
                            else:
                                # Record failure reason if available
                                reason = None
                                if isinstance(res, dict):
                                    reason = res.get('reason') or (res.get('send_result') or {}).get('error_details', {}).get('policy') or (res.get('send_result') or {}).get('message')
                                reason = reason or 'send_failed'
                                channel_stats[ch_name]['failures'] += 1
                                channel_stats[ch_name]['reasons'][reason] = channel_stats[ch_name]['reasons'].get(reason, 0) + 1
                        except Exception as _exc:
                            channel_stats[ch_name]['failures'] += 1
                            channel_stats[ch_name]['reasons']['exception'] = channel_stats[ch_name]['reasons'].get('exception', 0) + 1
                        continue  # Conversational channel handled; move to next channel

                    # Standard invite for non-conversational channels (Email, SMS, etc.)
                    success = self.send_survey_invitation(recipient, campaign, ch_name, survey_response.name)
                    if success:
                        channel_stats[ch_name]['success'] += 1
                        recipient_delivered = True
                    else:
                        # Classify common failure reasons for non-conversational paths
                        reason = 'not_supported'
                        if ch_name == 'Email' and not recipient.get('email_id'):
                            reason = 'no_email'
                        elif ch_name in ('WhatsApp', 'SMS') and not recipient.get('mobile_no'):
                            reason = 'no_mobile'
                        channel_stats[ch_name]['failures'] += 1
                        channel_stats[ch_name]['reasons'][reason] = channel_stats[ch_name]['reasons'].get(reason, 0) + 1

                if recipient_delivered:
                    delivered_count += 1

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
            log_title = "Survey Service: Distribution Fatal Error"
            log_message = (
                f"Campaign: {campaign.name if campaign else 'Unknown'}\n"
                f"Error: {str(e)}\n"
                f"Traceback:\n{frappe.get_traceback()}"
            )
            frappe.log_error(log_message, log_title)
            return {
                'success': False,
                'error': "A fatal error occurred during survey distribution. System logs have been captured."
            }

    def get_survey_recipients(self, campaign):
        """Get recipients based on target audience filters"""
        # Dynamically include optional social ID fields if present on Contact
        try:
            meta = frappe.get_meta('Contact')
        except Exception:
            meta = None

        # NOTE: Beneficiary filtering uses ERPNext Contact/Customer (type Individual)
        # Employer filtering uses ERPNext Customer (type Company)
        # Both are handled by _get_beneficiary_contacts_from_erpnext() and
        # _get_employer_contacts_from_erpnext() methods respectively

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

        def _norm_key(s: str) -> str:
            return (s or '').strip().lower().replace(' ', '_').replace('-', '_')

        def _map_beneficiary_field(key: str) -> str:
            """Map user-friendly field names to ERPNext Contact/Customer fields for beneficiaries."""
            k = _norm_key(key)
            # ID mappings - mapped to Customer.name for Individual customers
            if k in ('id', 'beneficiary_id', 'beneficiary_number', 'number'):
                return 'beneficiary_number'
            # Name mappings - mapped to Contact.full_name or Contact.first_name/last_name
            if k in ('name', 'full_name', 'fullname', 'customer_name', 'customer name'):
                return 'full_name'
            if k in ('first_name', 'first name', 'fname'):
                return 'first_name'
            if k in ('last_name', 'last name', 'lname'):
                return 'last_name'
            # Contact mappings - mapped to Contact.email_id, Contact.mobile_no
            if k in ('email', 'email_address', 'email address', 'email_id'):
                return 'email'
            if k in ('phone', 'phone_number', 'phone number', 'telephone'):
                return 'phone'
            if k in ('mobile', 'mobile_no', 'mobile number', 'cell', 'cellphone'):
                return 'mobile'
            # NRC mapping - mapped to Customer.tax_id for Individual customers
            if k in ('nrc', 'nrc_number', 'nrc number', 'national_id', 'tax_id'):
                return 'nrc_number'
            # Territory and group mappings
            if k in ('territory', 'region', 'area'):
                return 'territory'
            if k in ('customer_group', 'group', 'category'):
                return 'customer_group'
            return k

        def _map_employer_field(key: str) -> str:
            """Map user-friendly field names to ERPNext Customer fields for employers (Company type)."""
            k = _norm_key(key)
            # ID mappings - mapped to Customer.name
            if k in ('id', 'code', 'employer_id', 'employer_number', 'employer_code'):
                return 'employer_code'
            # Name mappings - mapped to Customer.customer_name
            if k in ('name', 'employer_name', 'company_name', 'company name', 'customer_name'):
                return 'employer_name'
            # Contact mappings - mapped to Customer.email_id, Customer.mobile_no
            if k in ('email', 'email_address', 'email address', 'email_id'):
                return 'email'
            if k in ('phone', 'phone_number', 'phone number', 'telephone'):
                return 'phone'
            if k in ('mobile', 'mobile_no', 'mobile number', 'cell', 'cellphone'):
                return 'mobile'
            # Business mappings - mapped to Customer fields
            if k in ('territory', 'region', 'area'):
                return 'territory'
            if k in ('customer_group', 'group', 'category'):
                return 'customer_group'
            if k in ('industry', 'sector', 'business_type'):
                return 'industry'
            if k in ('tax_id', 'registration_number', 'company_number'):
                return 'tax_id'
            return k

        conditions = []
        values = []

        # Track beneficiary and employer filter items for later processing
        beneficiary_filters = []
        employer_filters = []

        # Process target audience filters
        for filter_item in campaign.target_audience:
            ftype = (filter_item.filter_type or '').strip()
            fop = (filter_item.filter_operator or '').strip()
            fval = (filter_item.filter_value or '').strip()
            ffield = (filter_item.filter_field or '').strip()

            # Beneficiary filters - use ERPNext Contact/Customer (type Individual)
            if ftype == 'Beneficiary':
                fkey = _map_beneficiary_field(ffield)
                beneficiary_filters.append({'field': fkey, 'operator': fop, 'value': fval})

            # Employer filters - use ERPNext Customer (type Company)
            elif ftype == 'Employer':
                fkey = _map_employer_field(ffield)
                employer_filters.append({'field': fkey, 'operator': fop, 'value': fval})

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

        # Apply beneficiary filtering using ERPNext Contact/Customer (type Individual)
        # Uses CoreBusiness first, then falls back to native ERPNext doctypes
        beneficiary_contacts = set()
        beneficiary_filter_applied = False
        if beneficiary_filters:
            for bf in beneficiary_filters:
                if bf['field'] and bf['operator'] and bf['value']:
                    beneficiary_filter_applied = True
                    try:
                        # Get beneficiary contacts - tries CoreBusiness first, then ERPNext fallback
                        bf_result = self._get_beneficiary_contacts_from_corebusiness(
                            bf['field'], bf['operator'], bf['value']
                        )
                        beneficiary_contacts.update(bf_result)
                    except Exception:
                        pass

            # If beneficiary filters were applied but found no matches, return empty
            if beneficiary_filter_applied and not beneficiary_contacts:
                return []

            # Add condition for matching contacts
            if beneficiary_contacts:
                placeholders = ', '.join(['%s'] * len(beneficiary_contacts))
                conditions.append(f"`tabContact`.name IN ({placeholders})")
                values.extend(list(beneficiary_contacts))

        # Apply employer filtering using ERPNext Customer (type Company)
        # Uses CoreBusiness first, then falls back to native ERPNext doctypes
        employer_contacts = set()
        employer_filter_applied = False
        if employer_filters:
            for ef in employer_filters:
                if ef['field'] and ef['operator'] and ef['value']:
                    employer_filter_applied = True
                    try:
                        # Get employer contacts - tries CoreBusiness first, then ERPNext fallback
                        ef_result = self._get_employer_contacts_from_corebusiness(
                            ef['field'], ef['operator'], ef['value']
                        )
                        employer_contacts.update(ef_result)
                    except Exception:
                        pass

            # If employer filters were applied but found no matches, return empty
            if employer_filter_applied and not employer_contacts:
                return []

            # Add condition for matching contacts
            if employer_contacts:
                placeholders = ', '.join(['%s'] * len(employer_contacts))
                conditions.append(f"`tabContact`.name IN ({placeholders})")
                values.extend(list(employer_contacts))

        # If no filters were applied at all, return empty list - require explicit targeting
        has_any_filters = bool(
            conditions or
            beneficiary_filter_applied or
            employer_filter_applied
        )
        if not has_any_filters:
            return []

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
        """Send a survey invitation link via unified inbox.
        Returns a diagnostics dict: { ok: bool, reason?: str, send_result?: dict }.

        Behavior depends on the campaign's is_campaign flag:
        - If is_campaign is False (default): One-way survey - conversation is immediately
          marked as Resolved after sending, subsequent inbound messages are parsed as normal chats.
        - If is_campaign is True: Two-way campaign - conversation remains open to receive
          responses from users (bidirectional communication).
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
                # Check if this is a two-way campaign (is_campaign=True) or one-way survey (is_campaign=False/default)
                is_two_way_campaign = False
                try:
                    is_two_way_campaign = bool(campaign.get('is_campaign') if isinstance(campaign, dict) else getattr(campaign, 'is_campaign', False))
                except Exception:
                    is_two_way_campaign = False

                # For one-way surveys (default), immediately mark conversation as resolved
                # For two-way campaigns, keep conversation open for user responses
                if not is_two_way_campaign:
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
                # else: Two-way campaign - keep conversation open for user responses

                return {'ok': True, 'send_result': send_res, 'is_campaign': is_two_way_campaign}
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
        from assistant_crm.utils import get_public_url
        site_url = get_public_url()
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
