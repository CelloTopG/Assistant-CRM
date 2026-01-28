# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
import re
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

# Safe imports
try:
    from frappe.utils import now, add_to_date
    from frappe import _
except ImportError:
    now = lambda: datetime.now().isoformat()
    add_to_date = lambda date, **kwargs: date + timedelta(**kwargs)
    _ = lambda x: x

def safe_log_error(message: str, title: str = "Enhanced Authentication Service"):
    """Safe error logging function"""
    try:
        if frappe:
            frappe.log_error(message, title)
        else:
            print(f"[{title}] {message}")
    except:
        print(f"[{title}] {message}")



class EnhancedAuthenticationService:
    """
    Phase 2: Enhanced Authentication Service
    Provides multi-step authentication workflows, advanced credential collection,
    and secure session management for WCFCB Assistant CRM.
    """

    def __init__(self):
        self.authentication_steps = {
            'initial_prompt': 1,
            'credential_collection': 2,
            'validation': 3,
            'confirmation': 4,
            'completion': 5
        }

        # Phase 2: Initialize real user database service
        self.real_db_service = None
        try:
            from .real_user_database_service import RealUserDatabaseService
            self.real_db_service = RealUserDatabaseService()
        except ImportError:
            safe_log_error("Real user database service not available, using simulated authentication")

        # Phase 2: Initialize enhanced security service
        self.security_service = None
        try:
            from .enhanced_security_service import EnhancedSecurityService
            self.security_service = EnhancedSecurityService()
        except ImportError:
            safe_log_error("Enhanced security service not available, using basic security")

        # Phase 1: Initialize Session Context Manager for persistent storage
        self.session_manager = None
        try:
            from .session_context_manager import SessionContextManager
            self.session_manager = SessionContextManager()
        except ImportError:
            safe_log_error("SessionContextManager not available, using fallback storage")
        except Exception as e:
            safe_log_error(f"Error initializing SessionContextManager: {str(e)}")


        self.credential_patterns = {
            'national_id': r'^([0-9]{6,12}|[0-9]{6,8}/[0-9]{2}/[0-9]{1})$',
            'claim_number': r'^(CL|WC)-[0-9]{4}-[0-9]{4,6}$',
            'account_number': r'^[A-Z0-9]{8,12}$',
            'beneficiary_number': r'^(BN|PEN)-[0-9]{6,10}$',
            'employer_id': r'^(EMP|BUS)-[0-9]{6,10}$',
            # Accept a person's full name: First Last (allow hyphens, apostrophes, spaces)
            'full_name': r"^[A-Za-z][A-Za-z\-\.' ]{1,50}\s+[A-Za-z][A-Za-z\-\.' ]{1,50}$",
            # Accept an employer/organization name (len 3-80, letters/numbers/space/&/.'-)
            'employer_name': r"^[A-Za-z0-9][A-Za-z0-9 &\-\.'()]{2,80}$",
            # Selector that can be either claim_number OR full_name OR employer_name (used in step 2 for claim_status)
            'claim_selector': r"((^(CL|WC)-[0-9]{4}-[0-9]{4,6}$)|(^[A-Za-z][A-Za-z\-\.' ]{1,50}\s+[A-Za-z][A-Za-z\-\.' ]{1,50}$)|(^[A-Za-z0-9][A-Za-z0-9 &\-\.'()]{2,80}$))"
        }

        self.intent_requirements = {
            # Guardrail: For claim_status we require BOTH NRC and Full Name to avoid early authentication
            'claim_status': ['national_id', 'full_name'],
            'payment_status': ['national_id', 'account_number'],
            'pension_inquiry': ['national_id', 'beneficiary_number'],
            'claim_submission': ['national_id'],
            'account_info': ['national_id', 'account_number'],
            'payment_history': ['national_id', 'account_number'],
            'document_status': ['national_id', 'claim_number'],
            'technical_help': ['national_id'],
            'employer_services': ['national_id', 'employer_id']
        }

        self.max_authentication_attempts = 3
        self.session_timeout_minutes = 30
        self.session_timeout_seconds = self.session_timeout_minutes * 60

    def get_authentication_prompt(self, intent: str, message: str, user_context: Dict, session_id: str) -> str:
        """
        Phase 2: Generate enhanced authentication prompt with step-by-step guidance.
        """
        try:
            # Get authentication state for this session
            auth_state = self._get_authentication_state(session_id)

            # Determine current authentication step
            current_step = auth_state.get('step', 1)

            if current_step == 1:
                return self._generate_initial_prompt(intent, message, user_context)
            elif current_step == 2:
                return self._generate_credential_collection_prompt(intent, auth_state)
            elif current_step == 3:
                return self._generate_validation_prompt(intent, auth_state)
            else:
                return self._generate_completion_prompt(intent, auth_state)

        except Exception as e:
            safe_log_error(f"Authentication prompt generation error: {str(e)}")
            return self._get_fallback_prompt(intent)

    def _generate_initial_prompt(self, intent: str, message: str, user_context: Dict) -> str:
        """Generate the initial authentication prompt with clear instructions."""

        # Intent-specific prompts with enhanced guidance
        enhanced_prompts = {
            'claim_status': {
                'greeting': "Hi! I'm Anna from WCFCB.",
                'purpose': "To check your claim status securely",
                'requirements': "I need BOTH your National ID (NRC) and your Full Name (First Last). NRC must be 9 digits in total; slashes are allowed.",
                'format': "Examples: 123456/78/9 Jane Doe — or — 123456789 Jane Doe",
                'security': "I'll search ERPNext using these details. If the name returns multiple matches, I'll ask a quick follow-up to pick the right one."
            },
            'payment_status': {
                'greeting': "Hi! I'm Anna from WCFCB.",
                'purpose': "To access your payment information",
                'requirements': "I'll need your National ID number and Account number",
                'format': "Please provide them like this: 123456789 ACC12345678",
                'security': "This ensures I can securely access your payment details."
            },
            'pension_inquiry': {
                'greeting': "Hi! I'm Anna from WCFCB.",
                'purpose': "To check your pension details",
                'requirements': "I'll need your National ID number and Beneficiary number",
                'format': "Please provide them like this: 123456789 BN-123456",
                'security': "This helps me access your pension information safely."
            },
            'account_info': {
                'greeting': "Hi! I'm Anna from WCFCB.",
                'purpose': "To access your account information",
                'requirements': "I'll need your National ID number and Account number",
                'format': "Please provide them like this: 123456789 ACC12345678",
                'security': "This ensures secure access to your account details."
            }
        }

        prompt_data = enhanced_prompts.get(intent, {
            'greeting': "Hi! I'm Anna from WCFCB.",
            'purpose': "To access your personal information",
            'requirements': "I'll need to verify your identity first",
            'format': "Please provide your National ID number and relevant reference number",
            'security': "This helps me provide secure, personalized assistance."
        })

        return (f"{prompt_data['greeting']} {prompt_data['purpose']}, "
                f"{prompt_data['requirements']}.\n\n"
                f"📝 **Format:** {prompt_data['format']}\n"
                f"🔒 **Why:** {prompt_data['security']}\n\n"
                f"You can also type 'help' if you need assistance finding these numbers.")

    def _generate_credential_collection_prompt(self, intent: str, auth_state: Dict) -> str:
        """Generate prompts for collecting missing credentials."""

        missing_credentials = auth_state.get('missing_credentials', [])
        collected_credentials = auth_state.get('collected_credentials', {})

        if not missing_credentials:
            return "Thank you! I have all the information I need. Let me verify your details..."

        credential_names = {
            'national_id': 'National ID number',
            'claim_number': 'Claim reference number (format: CL-2024-001234)',
            'account_number': 'Account number (format: ACC12345678)',
            'beneficiary_number': 'Beneficiary number (format: BN-123456)',
            'employer_id': 'Employer ID (format: EMP-123456)',
            'claim_selector': 'Claim reference number OR your Full Name (First Last) OR Employer name'
        }

        next_credential = missing_credentials[0]
        credential_name = credential_names.get(next_credential, next_credential)

        progress = f"({len(collected_credentials)}/{len(collected_credentials) + len(missing_credentials)})"

        collected_list = [credential_names.get(k, k) for k in collected_credentials.keys()]
        prefix = ("Great! I have " + ", ".join(collected_list) + ".") if collected_list else "Thanks!"
        return (f"{prefix} "
                f"\n\n📋 **Step {progress}:** Now I need your {credential_name}.\n\n"
                f"Please provide just the {credential_name}, or type 'start over' to begin again.")

    def _generate_validation_prompt(self, intent: str, auth_state: Dict) -> str:
        """Generate validation confirmation prompt."""

        collected = auth_state.get('collected_credentials', {})

        credential_display = {
            'national_id': f"National ID: {collected.get('national_id', 'N/A')}",
            'claim_number': f"Claim Number: {collected.get('claim_number', 'N/A')}",
            'account_number': f"Account Number: {collected.get('account_number', 'N/A')}",
            'beneficiary_number': f"Beneficiary Number: {collected.get('beneficiary_number', 'N/A')}",
            'employer_id': f"Employer ID: {collected.get('employer_id', 'N/A')}"
        }

        display_items = [credential_display[k] for k in collected.keys() if k in credential_display]

        return (f"Perfect! Let me confirm your details:\n\n"
                f"✅ {chr(10).join(display_items)}\n\n"
                f"Is this information correct? Please reply 'yes' to continue or 'no' to start over.")

    def _generate_completion_prompt(self, intent: str, auth_state: Dict) -> str:
        """Generate authentication completion prompt."""

        return ("Thank you! I've verified your identity successfully. "
                "Let me now help you with your original request...")

    def process_authentication_input(self, user_input: str, intent: str, session_id: str, user_context: Dict) -> Dict[str, Any]:
        """
        Phase 2: Process user input during authentication flow.
        Returns authentication state and next action.
        """
        try:
            auth_state = self._get_authentication_state(session_id)
            current_step = auth_state.get('step', 1)

            # Handle special commands
            if user_input.lower().strip() in ['help', 'assistance']:
                return self._handle_help_request(intent, auth_state)
            elif user_input.lower().strip() in ['start over', 'restart', 'begin again']:
                return self._reset_authentication(session_id, intent)
            elif user_input.lower().strip() in ['cancel', 'stop', 'exit']:
                return self._cancel_authentication(session_id)

            # Guardrail: if state claims completion but required credentials are missing, downgrade to collection
            try:
                required = self.intent_requirements.get(intent, [])
                creds = (auth_state.get('collected_credentials') or {})
                if current_step >= 4 and required:
                    missing_req = [k for k in required if k not in creds]
                    if missing_req:
                        auth_state.update({
                            'step': 2,
                            'intent': intent,
                            'missing_credentials': missing_req,
                            'last_update': now(),
                            'last_update_ts': time.time(),
                        })
                        self._save_authentication_state(session_id, auth_state)
                        return {
                            'success': True,
                            'next_action': 'collect_more',
                            'message': self._generate_credential_collection_prompt(intent, auth_state)
                        }
            except Exception:
                pass

            # Process based on current step
            if current_step == 1:
                return self._process_initial_input(user_input, intent, session_id, auth_state)
            elif current_step == 2:
                return self._process_credential_input(user_input, intent, session_id, auth_state)
            elif current_step == 3:
                return self._process_validation_input(user_input, intent, session_id, auth_state)
            else:
                return self._complete_authentication(session_id, auth_state)

        except Exception as e:
            safe_log_error(f"Authentication input processing error: {str(e)}")
            return {
                'success': False,
                'error': 'Authentication processing error',
                'next_action': 'restart',
                'message': "I'm sorry, there was an error processing your authentication. Please try again."
            }

    def _process_initial_input(self, user_input: str, intent: str, session_id: str, auth_state: Dict) -> Dict[str, Any]:
        """Process the initial credential input.
        Updated: Accept NRC and/or Full Name in Step 1 for a smoother UX on claim_status.
        - If both provided in one message, collect both and complete auth immediately (claim_status).
        - If only one provided, complete auth for claim_status as well, so we can retrieve live data.
        - Otherwise, prompt clearly for NRC or Full Name.
        """
        txt = (user_input or '').strip()

        # Extract NRC: allow slashes but require exactly 9 digits total
        nrc_match = re.search(r'([0-9/]{5,15})', txt)
        nrc_value = None
        if nrc_match:
            candidate = nrc_match.group(1)
            digits_only = re.sub(r'[^0-9]', '', candidate)
            if len(digits_only) == 9:
                nrc_value = digits_only

        # Extract Full Name ONLY when explicitly indicated (guardrail)
        name_phrase = re.search(r"(?:^|\b)(?:my\s+name\s+is|i\s+am|i'm|im|name\s*:)[\s:]*([A-Za-z][A-Za-z\-\.' ]{1,50}\s+[A-Za-z][A-Za-z\-\.' ]{1,50})\b", txt, re.IGNORECASE)
        full_name = name_phrase.group(1).strip() if name_phrase else None

        if intent == 'claim_status':
            # Initialize state and merge any partials, but DO NOT complete until both present
            collected = auth_state.get('collected_credentials', {}) or {}
            if nrc_value:
                collected['national_id'] = nrc_value
            if full_name:
                collected['full_name'] = full_name

            missing = []
            if 'national_id' not in collected:
                missing.append('national_id')
            if 'full_name' not in collected:
                missing.append('full_name')

            if not missing:
                # Both present: complete
                auth_state.update({
                    'step': 4,
                    'intent': intent,
                    'last_update': now(),
                    'last_update_ts': time.time(),
                    'collected_credentials': collected
                })
                user_profile = self._create_authenticated_user_context(auth_state)
                auth_state['user_profile'] = user_profile
                self._save_authentication_state(session_id, auth_state)
                return {
                    'success': True,
                    'next_action': 'complete',
                    'message': "Thanks! I've got your NRC and Full Name. Fetching your claim status now...",
                    'authenticated_user': user_profile
                }
            else:
                # Wait for the remaining credential(s)
                auth_state.update({
                    'step': 2,
                    'intent': intent,
                    'last_update': now(),
                    'last_update_ts': time.time(),
                    'collected_credentials': collected,
                    'missing_credentials': missing
                })
                self._save_authentication_state(session_id, auth_state)
                # Friendly, explicit prompt examples (training)
                need = ' and '.join(['NRC' if m=='national_id' else 'Full Name' for m in missing])
                return {
                    'success': True,
                    'next_action': 'collect_more',
                    'message': (f"Great — I still need your {need}.\n"
                                "NRC is 9 digits (slashes allowed).\n"
                                "You can send, for example:\n"
                                "- 123456/78/9\n"
                                "- 123456789\n"
                                "- my name is Jane Doe")
                }

        # Default behavior for non-claim_status intents
        auth_state.update({
            'step': 1,
            'intent': intent,
            'last_update': now(),
            'last_update_ts': time.time(),
            'missing_credentials': ['national_id']
        })
        self._save_authentication_state(session_id, auth_state)
        return {
            'success': True,
            'next_action': 'collect_more',
            'message': ("Please provide your National ID (NRC) to continue.")
        }

    def _parse_credentials(self, user_input: str, required_credentials: List[str]) -> Dict[str, str]:
        """Parse credentials from user input using strict validation and normalization."""

        parsed = {}
        input_parts = user_input.strip().split()

        for part in input_parts:
            token = part.strip()
            if 'national_id' in required_credentials:
                # Normalize NRC: remove non-digits and require exactly 9 digits
                digits_only = re.sub(r'[^0-9]', '', token)
                if len(digits_only) == 9 and digits_only.isdigit():
                    parsed['national_id'] = digits_only
            if 'full_name' in required_credentials and 'full_name' not in parsed:
                # Only accept explicit name phrases handled elsewhere; fallback here is conservative
                m_name = re.match(r"^[A-Za-z][A-Za-z\-\.' ]{1,50}\s+[A-Za-z][A-Za-z\-\.' ]{1,50}$", token)
                if m_name:
                    # Do not capture unless the entire user_input was an explicit name; leave to _process_initial_input
                    pass
            # Other credentials keep existing pattern-based parsing
            for cred_type, pattern in self.credential_patterns.items():
                if cred_type in required_credentials and cred_type not in parsed and cred_type not in ['national_id', 'full_name']:
                    if re.match(pattern, token, re.IGNORECASE):
                        parsed[cred_type] = token.upper()
        return parsed

    def _get_authentication_state(self, session_id: str) -> Dict[str, Any]:
        """
        Phase 1: Get authentication state for session using Session Context Manager.
        Falls back to in-memory storage if Session Context Manager is unavailable.
        Includes inactivity timeout to auto-reset stale sessions.
        """
        now_ts = time.time()
        try:
            if self.session_manager:
                # Use Session Context Manager for persistent storage
                session_state = self.session_manager.get_session_state(session_id) or {}
                auth_state = session_state.get('authentication_state', {}) if isinstance(session_state, dict) else {}
            else:
                # Prefer frappe.cache as cross-process store when available
                try:
                    import frappe  # local import to avoid hard dependency at module import time
                    cache_key = f"assistant_crm:auth:{session_id}"
                    cached = frappe.cache().get_value(cache_key) or {}
                    auth_state = cached if isinstance(cached, dict) else {}
                except Exception:
                    auth_state = None

            # If no authentication state exists, create default
            if not auth_state:
                auth_state = {
                    'step': 1,
                    'collected_credentials': {},
                    'missing_credentials': [],
                    'attempts': 0,
                    'created': now(),
                    'created_ts': now_ts,
                    'last_update': now(),
                    'last_update_ts': now_ts
                }
            else:
                # Inactivity timeout check
                last_ts = auth_state.get('last_update_ts') or auth_state.get('created_ts') or now_ts
                if (now_ts - last_ts) > self.session_timeout_seconds:
                    auth_state = {
                        'step': 1,
                        'collected_credentials': {},
                        'missing_credentials': [],
                        'attempts': 0,
                        'created': now(),
                        'created_ts': now_ts,
                        'last_update': now(),
                        'last_update_ts': now_ts
                    }


            return auth_state
        except Exception as e:
            safe_log_error(f"Error getting authentication state: {str(e)}")
            return {
                'step': 1,
                'collected_credentials': {},
                'missing_credentials': [],
                'attempts': 0,
                'created': now(),
                'created_ts': now_ts,
                'last_update': now(),
                'last_update_ts': now_ts
            }

    def _save_authentication_state(self, session_id: str, auth_state: Dict[str, Any]):
        """
        Phase 1: Save authentication state for session using Session Context Manager.
        Falls back to in-memory storage if Session Context Manager is unavailable.
        """
        try:
            if self.session_manager:
                # Use Session Context Manager for persistent storage
                updates = {'authentication_state': auth_state}

                # If authentication is complete, also save user profile
                if auth_state.get('step') == 4 and auth_state.get('user_profile'):
                    updates['user_profile'] = auth_state['user_profile']
                    updates['status'] = 'authenticated'

                success = self.session_manager.update_session_state(session_id, updates)
                if not success:
                    safe_log_error(f"Failed to save authentication state to database for session {session_id}")
            else:
                # Prefer frappe.cache as cross-process store when available; fallback to in-memory
                saved = False
                try:
                    import frappe
                    cache_key = f"assistant_crm:auth:{session_id}"
                    # Default expiry aligns with session timeout
                    frappe.cache().set_value(cache_key, auth_state, expires_in_sec=self.session_timeout_seconds)
                    saved = True
                except Exception:
                    saved = False
                if not saved:
                    if not hasattr(self, '_auth_states'):
                        self._auth_states = {}
                    self._auth_states[session_id] = auth_state


        except Exception as e:
            safe_log_error(f"Failed to save authentication state: {str(e)}")

    def _process_credential_input(self, user_input: str, intent: str, session_id: str, auth_state: Dict) -> Dict[str, Any]:
        """Process additional credential input."""

        missing_credentials = auth_state.get('missing_credentials', [])
        if not missing_credentials:
            return {
                'success': True,
                'next_action': 'validate',
                'message': self._generate_validation_prompt(intent, auth_state)
            }

        next_credential = missing_credentials[0]


        # Special handling for claim_selector: accept claim number OR full name OR employer name
        if next_credential == 'claim_selector':
            txt = user_input.strip()
            added_key = None
            # 1) Try to find a claim number anywhere in the text
            m_claim = re.search(r'(CL|WC)-\d{4}-\d{4,6}', txt, re.IGNORECASE)
            if m_claim:
                auth_state['collected_credentials']['claim_number'] = m_claim.group(0).upper()
                added_key = 'claim_number'
            else:
                # 2) Try to find a full name (two words) anywhere in the text
                # Prefer patterns like "my name is First Last" or "I am First Last"
                m_name_phrase = re.search(r"(?:^|\b)(?:my\s+name\s+is|i\s+am|i'm|im|name\s*:)\s+([A-Za-z][A-Za-z\-\.\' ]{1,50}\s+[A-Za-z][A-Za-z\-\.\' ]{1,50})", txt, re.IGNORECASE)
                if m_name_phrase:
                    auth_state['collected_credentials']['full_name'] = m_name_phrase.group(1).strip()
                    added_key = 'full_name'
                else:
                    # Do NOT accept generic two-word names here; require explicit phrase to reduce false positives
                    # 3) Try to find employer name after the word employer or with a business suffix
                    m_emp_kw = re.search(r"employer[^A-Za-z0-9]*([A-Za-z0-9][A-Za-z0-9 &\-\.\'()]{2,80})", txt, re.IGNORECASE)
                    m_emp_suf = re.search(r"\b([A-Za-z0-9][A-Za-z0-9 &\-\.\'()]{2,80}\s+(Ltd|Limited|Inc|PLC|Company|Enterprises|Enterprise|Mining|Construction))\b", txt, re.IGNORECASE)
                    if m_emp_kw:
                        auth_state['collected_credentials']['employer_name'] = m_emp_kw.group(1).strip()
                        added_key = 'employer_name'
                    elif m_emp_suf:
                        auth_state['collected_credentials']['employer_name'] = m_emp_suf.group(1).strip()
                        added_key = 'employer_name'
            if not added_key:
                return {
                    'success': False,
                    'next_action': 'retry',
                    'message': ("Please provide either your Claim number (e.g., CL-2024-001234), "
                               "or your Full Name (First Last), or your Employer name.")
                }
            # Remove the placeholder requirement
            auth_state['missing_credentials'].remove('claim_selector')

            # Continue flow
            if not auth_state['missing_credentials']:
                # All required credentials collected.
                if intent == 'claim_status':
                    # Guardrail: require BOTH NRC and Full Name before completing
                    creds = auth_state.get('collected_credentials', {}) or {}
                    required = ['national_id', 'full_name']
                    missing_req = [k for k in required if k not in creds]
                    if not missing_req:
                        auth_state['step'] = 4
                        auth_state['last_update'] = now()
                        auth_state['last_update_ts'] = time.time()
                        # Build lightweight authenticated user profile from collected credentials
                        user_profile = self._create_authenticated_user_context(auth_state)
                        auth_state['user_profile'] = user_profile
                        self._save_authentication_state(session_id, auth_state)
                        return {
                            'success': True,
                            'next_action': 'complete',
                            'message': "Thanks! I've got your NRC and Full Name. Fetching your claim status now...",
                            'authenticated_user': user_profile
                        }
                    else:
                        # Still missing required claim_status fields; continue collecting
                        auth_state['missing_credentials'] = missing_req
                        auth_state['last_update'] = now()
                        auth_state['last_update_ts'] = time.time()
                        self._save_authentication_state(session_id, auth_state)
                        return {
                            'success': True,
                            'next_action': 'collect_more',
                            'message': self._generate_credential_collection_prompt(intent, auth_state)
                        }
                else:
                    # Default behavior for other intents: move to validation
                    auth_state['step'] = 3
                    auth_state['last_update'] = now()
                    auth_state['last_update_ts'] = time.time()
                    self._save_authentication_state(session_id, auth_state)
                    return {
                        'success': True,
                        'next_action': 'validate',
                        'message': self._generate_validation_prompt(intent, auth_state)
                    }
            else:
                auth_state['last_update'] = now()
                auth_state['last_update_ts'] = time.time()
                self._save_authentication_state(session_id, auth_state)
                return {
                    'success': True,
                    'next_action': 'collect_more',
                    'message': self._generate_credential_collection_prompt(intent, auth_state)
                }

        # Validate the input against the expected pattern
        if next_credential == 'national_id':
            # Normalize: allow slashes but require exactly 9 digits total
            digits_only = re.sub(r'[^0-9]', '', user_input)
            if len(digits_only) != 9:
                return {
                    'success': False,
                    'next_action': 'retry',
                    'message': "The NRC must be 9 digits in total (slashes allowed). Examples: 123456/78/9 or 123456789"
                }
            auth_state['collected_credentials'][next_credential] = digits_only
            auth_state['missing_credentials'].remove(next_credential)

            # Decide next step after capturing NRC
            if not auth_state['missing_credentials']:
                # All credentials collected
                if intent == 'claim_status':
                    # Guardrail: complete immediately for claim_status once NRC and Full Name are present
                    auth_state['step'] = 4
                    auth_state['last_update'] = now()
                    auth_state['last_update_ts'] = time.time()
                    user_profile = self._create_authenticated_user_context(auth_state)
                    auth_state['user_profile'] = user_profile
                    self._save_authentication_state(session_id, auth_state)
                    return {
                        'success': True,
                        'next_action': 'complete',
                        'message': "Thanks! I've got your NRC and Full Name. Fetching your claim status now...",
                        'authenticated_user': user_profile
                    }
                else:
                    # Default behavior for other intents: move to validation
                    auth_state['step'] = 3
                    auth_state['last_update'] = now()
                    auth_state['last_update_ts'] = time.time()
                    self._save_authentication_state(session_id, auth_state)
                    return {
                        'success': True,
                        'next_action': 'validate',
                        'message': self._generate_validation_prompt(intent, auth_state)
                    }
            else:
                # Still need more credentials
                auth_state['last_update'] = now()
                auth_state['last_update_ts'] = time.time()
                self._save_authentication_state(session_id, auth_state)
                return {
                    'success': True,
                    'next_action': 'collect_more',
                    'message': self._generate_credential_collection_prompt(intent, auth_state)
                }

        elif next_credential == 'full_name':
            # Accept Full Name only when explicitly indicated to avoid false positives
            m_name_phrase = re.search(r"(?:^|\b)(?:my\s+name\s+is|i\s+am|i'm|im|name\s*:)", user_input.strip(), re.IGNORECASE)
            if m_name_phrase:
                # Extract the name portion after the phrase
                m_name = re.search(r"(?:^|\b)(?:my\s+name\s+is|i\s+am|i'm|im|name\s*:)[\s:]*([A-Za-z][A-Za-z\-\.' ]{1,50}\s+[A-Za-z][A-Za-z\-\.' ]{1,50})\b", user_input.strip(), re.IGNORECASE)
                if m_name:
                    auth_state['collected_credentials']['full_name'] = m_name.group(1).strip()
                    auth_state['missing_credentials'].remove(next_credential)

                    # Decide next step after capturing Full Name
                    if not auth_state['missing_credentials']:
                        # All credentials collected
                        if intent == 'claim_status':
                            # Guardrail: complete immediately for claim_status once NRC and Full Name are present
                            auth_state['step'] = 4
                            auth_state['last_update'] = now()
                            auth_state['last_update_ts'] = time.time()
                            user_profile = self._create_authenticated_user_context(auth_state)
                            auth_state['user_profile'] = user_profile
                            self._save_authentication_state(session_id, auth_state)
                            return {
                                'success': True,
                                'next_action': 'complete',
                                'message': "Thanks! I've got your NRC and Full Name. Fetching your claim status now...",
                                'authenticated_user': user_profile
                            }
                        else:
                            # Default behavior for other intents: move to validation
                            auth_state['step'] = 3
                            auth_state['last_update'] = now()
                            auth_state['last_update_ts'] = time.time()
                            self._save_authentication_state(session_id, auth_state)
                            return {
                                'success': True,
                                'next_action': 'validate',
                                'message': self._generate_validation_prompt(intent, auth_state)
                            }
                    else:
                        # Still need more credentials
                        auth_state['last_update'] = now()
                        auth_state['last_update_ts'] = time.time()
                        self._save_authentication_state(session_id, auth_state)
                        return {
                            'success': True,
                            'next_action': 'collect_more',
                            'message': self._generate_credential_collection_prompt(intent, auth_state)
                        }
                else:
                    return {
                        'success': False,
                        'next_action': 'retry',
                        'message': "Please provide your Full Name in this format: 'my name is First Last'."
                    }
            else:
                return {
                    'success': False,
                    'next_action': 'retry',
                    'message': "Please provide your Full Name in this format: 'my name is First Last'."
                }
        elif re.match(self.credential_patterns.get(next_credential, '.*'), user_input.strip(), re.IGNORECASE):
            # Add to collected credentials
            auth_state['collected_credentials'][next_credential] = user_input.strip().upper()
            auth_state['missing_credentials'].remove(next_credential)

            if not auth_state['missing_credentials']:
                # All credentials collected
                if intent == 'claim_status':
                    # Guardrail: complete immediately for claim_status once NRC and Full Name are present
                    auth_state['step'] = 4
                    auth_state['last_update'] = now()
                    auth_state['last_update_ts'] = time.time()
                    user_profile = self._create_authenticated_user_context(auth_state)
                    auth_state['user_profile'] = user_profile
                    self._save_authentication_state(session_id, auth_state)
                    return {
                        'success': True,
                        'next_action': 'complete',
                        'message': "Thanks! I've got your NRC and Full Name. Fetching your claim status now...",
                        'authenticated_user': user_profile
                    }
                else:
                    # Default behavior for other intents: move to validation
                    auth_state['step'] = 3
                    auth_state['last_update'] = now()
                    auth_state['last_update_ts'] = time.time()
                    self._save_authentication_state(session_id, auth_state)
                    return {
                        'success': True,
                        'next_action': 'validate',
                        'message': self._generate_validation_prompt(intent, auth_state)
                    }
            else:
                # Still need more credentials
                auth_state['last_update'] = now()
                auth_state['last_update_ts'] = time.time()
                self._save_authentication_state(session_id, auth_state)
                return {
                    'success': True,
                    'next_action': 'collect_more',
                    'message': self._generate_credential_collection_prompt(intent, auth_state)
                }
        else:
            # Invalid format
            credential_names = {
                'national_id': 'National ID number (6-12 digits)',
                'claim_number': 'Claim reference number (format: CL-2024-001234)',
                'account_number': 'Account number (format: ACC12345678)',
                'beneficiary_number': 'Beneficiary number (format: BN-123456)',
                'employer_id': 'Employer ID (format: EMP-123456)',
                'claim_selector': 'Claim reference number OR your Full Name (First Last) OR Employer name'
            }

            expected_format = credential_names.get(next_credential, next_credential)

            return {
                'success': False,
                'next_action': 'retry',
                'message': f"The format doesn't look right. I need your {expected_format}. Please try again."
            }

    def _process_validation_input(self, user_input: str, intent: str, session_id: str, auth_state: Dict) -> Dict[str, Any]:
        """Process validation confirmation input with real database verification."""

        user_response = user_input.lower().strip()

        if user_response in ['yes', 'y', 'correct', 'confirm', 'ok', 'okay']:
            # Phase 2: Perform real database authentication
            credentials = auth_state.get('collected_credentials', {})

            if self.real_db_service and credentials:
                # Attempt real database authentication
                national_id = credentials.get('national_id')
                reference_number = (credentials.get('claim_number') or
                                  credentials.get('account_number') or
                                  credentials.get('beneficiary_number') or
                                  credentials.get('employer_id'))

                if national_id and reference_number:
                    # Determine user type based on reference number
                    user_type = self._determine_user_type(reference_number)

                    auth_result = self.real_db_service.authenticate_user(
                        national_id, reference_number, user_type
                    )

                    if auth_result['success']:
                        # Real authentication successful
                        auth_state['step'] = 4
                        auth_state['database_verified'] = True
                        auth_state['user_profile'] = auth_result['user_profile']
                        auth_state['last_update'] = now()
                        auth_state['last_update_ts'] = time.time()
                        self._save_authentication_state(session_id, auth_state)

                        return {
                            'success': True,
                            'next_action': 'complete',
                            'message': "Perfect! I've verified your identity with our secure database. Let me help you with your request.",
                            'authenticated_user': auth_result['user_profile']
                        }
                    else:
                        # Real authentication failed
                        return {
                            'success': False,
                            'next_action': 'retry',
                            'message': "I wasn't able to verify those credentials in our system. Please double-check your information and try again, or contact our office for assistance."
                        }

            # Fallback to simulated authentication
            auth_state['step'] = 4
            auth_state['last_update'] = now()
            auth_state['last_update_ts'] = time.time()
            self._save_authentication_state(session_id, auth_state)

            return {
                'success': True,
                'next_action': 'complete',
                'message': self._generate_completion_prompt(intent, auth_state),
                'authenticated_user': self._create_authenticated_user_context(auth_state)
            }
        elif user_response in ['no', 'n', 'incorrect', 'wrong', 'start over']:
            # Reset authentication
            return self._reset_authentication(session_id, intent)
        else:
            return {
                'success': False,
                'next_action': 'retry',
                'message': "Please reply 'yes' if the information is correct, or 'no' to start over."
            }

    def _determine_user_type(self, reference_number: str) -> str:
        """Determine user type based on reference number format."""

        if reference_number.startswith(('CL-', 'ACC-', 'BN-')):
            return 'beneficiary'
        elif reference_number.startswith(('EMP-', 'BUS-')):
            return 'employer'
        elif reference_number.startswith('VEN-'):
            return 'supplier'
        elif reference_number.startswith('STAFF-'):
            return 'wcfcb_staff'
        else:
            return 'beneficiary'  # Default

    def _complete_authentication(self, session_id: str, auth_state: Dict) -> Dict[str, Any]:
        """Complete the authentication process."""

        return {
            'success': True,
            'next_action': 'proceed',
            'message': "Authentication completed successfully. Processing your request...",
            'authenticated_user': self._create_authenticated_user_context(auth_state)
        }

    def _create_authenticated_user_context(self, auth_state: Dict) -> Dict[str, Any]:
        """Create authenticated user context from collected credentials."""

        credentials = auth_state.get('collected_credentials', {})

        # Use National ID as primary user identifier
        user_id = credentials.get('national_id', 'authenticated_user')

        # Determine user role based on credentials
        user_role = 'beneficiary'  # Default role
        if 'employer_id' in credentials:
            user_role = 'employer'

        # Build context with additional fields to help live-data search
        context = {
            'user_id': user_id,
            'user_role': user_role,
            'user_type': 'authenticated',
            'permissions': ['view_own_data', 'submit_claims', 'view_payments'],
            'authenticated': True,
            'authentication_method': 'enhanced_multi_step',
            'credentials': credentials,
            'session_authenticated': True,
            'nrc_number': credentials.get('national_id')
        }
        # Optional selectors
        if credentials.get('claim_number'):
            context['claim_number'] = credentials.get('claim_number')
        if credentials.get('full_name'):
            context['full_name'] = credentials.get('full_name')
        if credentials.get('employer_name'):
            context['employer_name'] = credentials.get('employer_name')

        return context

    def _handle_help_request(self, intent: str, auth_state: Dict) -> Dict[str, Any]:
        """Handle help requests during authentication."""

        help_messages = {
            'claim_status': "To check your claim status, I need:\n• Your National ID (NRC) — 9 digits total (slashes allowed)\n• Your Full Name (First Last)\n\nExamples: 123456/78/9 Jane Doe or 123456789 Jane Doe",
            'payment_status': "To check your payment status, I need:\n• Your National ID (9 digits)\n• Your Account number (format: ACC12345678)\n\nYour account number is on your WCFCB member card or statements.",
            'pension_inquiry': "To check your pension details, I need:\n• Your National ID (9 digits)\n• Your Beneficiary number (format: BN-123456)\n\nYour beneficiary number is on your pension documentation."
        }

        help_message = help_messages.get(intent,
            "I need to verify your identity to access your personal information. "
            "Please provide your National ID number and relevant reference number.")

        return {
            'success': True,
            'next_action': 'continue',
            'message': f"📋 **Help Information:**\n\n{help_message}\n\nPlease provide these details when you're ready."
        }

    def _reset_authentication(self, session_id: str, intent: str) -> Dict[str, Any]:
        """Reset authentication process and clear persisted state."""

        # Clear in-memory fallback state
        if hasattr(self, '_auth_states') and session_id in self._auth_states:
            try:
                del self._auth_states[session_id]
            except Exception:
                pass

        # Clear persisted state in DB/cache when available
        try:
            default_state = {
                'step': 1,
                'collected_credentials': {},
                'missing_credentials': [],
                'attempts': 0,
                'created': now(),
                'created_ts': time.time(),
                'last_update': now(),
                'last_update_ts': time.time()
            }
            if self.session_manager:
                self.session_manager.update_session_state(session_id, {
                    'authentication_state': default_state,
                    'status': 'unauthenticated',
                    'user_profile': None
                })
            else:
                try:
                    import frappe
                    cache_key = f"assistant_crm:auth:{session_id}"
                    # Delete if supported; else overwrite with default
                    try:
                        frappe.cache().delete_value(cache_key)
                    except Exception:
                        frappe.cache().set_value(cache_key, default_state, expires_in_sec=self.session_timeout_seconds)
                except Exception:
                    pass
        except Exception:
            pass

        return {
            'success': True,
            'next_action': 'restart',
            'message': "No problem! Let's start over.\n\n" + self._generate_initial_prompt(intent, "", {})
        }

    def _cancel_authentication(self, session_id: str) -> Dict[str, Any]:
        """Cancel authentication process."""

        # Clear authentication state
        if hasattr(self, '_auth_states') and session_id in self._auth_states:
            del self._auth_states[session_id]

        return {
            'success': True,
            'next_action': 'cancel',
            'message': "Authentication cancelled. I'm still here to help with general questions about WCFCB services. What would you like to know?"
        }

    def is_authentication_in_progress(self, session_id: str) -> bool:
        """Check if authentication is in progress for a session."""

        auth_state = self._get_authentication_state(session_id)
        return auth_state.get('step', 0) > 0 and auth_state.get('step', 0) < 5

    def get_authentication_step(self, session_id: str) -> int:
        """Get current authentication step for a session."""

        auth_state = self._get_authentication_state(session_id)
        return auth_state.get('step', 0)


    def get_auth_context(self, session_id: str) -> Dict[str, Any]:
        """Public accessor: return lightweight authentication context for a session."""
        try:
            state = self._get_authentication_state(session_id) or {}
            step = int(state.get('step', 1) or 1)
            context = {
                'in_progress': step > 0 and step < 5,
                'step': step,
                'intent': state.get('intent'),
                'collected_credentials': state.get('collected_credentials', {}),
                'authenticated': step >= 4,
                'user_profile': state.get('user_profile')
            }
            return context
        except Exception:
            return {
                'in_progress': False,
                'step': 1,
                'intent': None,
                'collected_credentials': {},
                'authenticated': False,
                'user_profile': None
            }

    def _get_fallback_prompt(self, intent: str) -> str:
        """Generate fallback authentication prompt."""
        return ("Hi! I'm Anna from WCFCB. To access your personal information, "
                "I'll need to verify your identity. Please provide your National ID number "
                "and relevant reference number for secure access.")
