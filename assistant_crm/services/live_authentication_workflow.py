# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

# Safe imports
try:
    import frappe
    from frappe.utils import now, add_to_date
    from frappe import _
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    now = lambda: datetime.now().isoformat()
    add_to_date = lambda date, **kwargs: date + timedelta(**kwargs)
    _ = lambda x: x
    FRAPPE_AVAILABLE = False

def safe_log_error(message: str, title: str = "Live Authentication Workflow"):
    """Safe error logging function"""
    try:
        if frappe:
            frappe.log_error(message, title)
        else:
            print(f"[{title}] {message}")
    except:
        print(f"[{title}] {message}")

class LiveAuthenticationWorkflow:
    """
    Live Authentication Workflow Implementation
    
    Implements the exact authentication sequence required:
    1. Intent Detection
    2. Authentication Gate (validate against live database)
    3. Intent Lock-In (maintain session context)
    4. Personalized Response (using real-time data)
    """
    
    def __init__(self):
        self.authentication_required_intents = [
            'payment_status', 'pension_inquiry', 'claim_status', 'account_info',
            'contribution_status', 'employment_info', 'employer_services',
            'compliance_status', 'employee_management', 'payment_history',
            'claim_submission', 'document_status', 'technical_help'
        ]
        
        self.intent_descriptions = {
            'payment_status': 'check your payment status and history',
            'pension_inquiry': 'access your pension information',
            'claim_status': 'view your claim status and progress',
            'account_info': 'access your account information',
            'contribution_status': 'check your contribution status',
            'employment_info': 'view your employment details',
            'employer_services': 'access employer services',
            'compliance_status': 'check compliance status',
            'employee_management': 'manage employee information',
            'payment_history': 'view your payment history',
            'claim_submission': 'submit a new claim',
            'document_status': 'check document status',
            'technical_help': 'get technical assistance'
        }
        
        # Initialize comprehensive database service
        try:
            from .comprehensive_database_service import ComprehensiveDatabaseService
            self.db_service = ComprehensiveDatabaseService()
        except ImportError:
            safe_log_error("Comprehensive database service not available")
            self.db_service = None

        # Phase 3: Initialize real-time data response system
        try:
            from .realtime_data_response_system import RealTimeDataResponseSystem
            self.response_system = RealTimeDataResponseSystem()
            safe_log_error("Real-time data response system initialized", "Live Authentication Workflow")
        except ImportError:
            safe_log_error("Real-time data response system not available", "Live Authentication Workflow")
            self.response_system = None

    def process_user_request(self, message: str, user_context: Dict, session_id: str) -> Dict[str, Any]:
        """
        Process user request following the exact authentication workflow:
        1. Intent Detection
        2. Authentication Gate
        3. Intent Lock-In
        4. Personalized Response
        """
        try:
            # Step 1: Intent Detection
            intent, confidence = self._detect_intent(message)

            # CRITICAL FIX: Ensure session exists before lookup
            # Initialize session storage if needed
            if not hasattr(self, '_sessions'):
                self._sessions = {}

            # Create basic session if it doesn't exist
            if session_id not in self._sessions:
                self._sessions[session_id] = {
                    'created_at': now(),
                    'authenticated': False,
                    'session_id': session_id
                }

            # Check if user is already authenticated for this session
            session_data = self._get_session_data(session_id)
            is_authenticated = session_data.get('authenticated', False)
            locked_intent = session_data.get('locked_intent')

            # CRITICAL FIX: Check for existing live data in user context
            # If we have live data, the user is already authenticated
            if user_context.get('has_live_data') and user_context.get('live_data', {}).get('found'):
                live_data = user_context['live_data']
                beneficiary_data = live_data.get('beneficiary_data', {})

                if beneficiary_data:
                    # Auto-authenticate user based on live data
                    user_profile = {
                        'user_id': beneficiary_data.get('nrc', beneficiary_data.get('name')),
                        'user_type': 'beneficiary',
                        'full_name': f"{beneficiary_data.get('first_name', '')} {beneficiary_data.get('last_name', '')}".strip(),
                        'nrc': beneficiary_data.get('nrc'),
                        'email': beneficiary_data.get('email'),
                        'phone': beneficiary_data.get('phone'),
                        'authenticated_via': 'live_data'
                    }

                    # Update session with authentication
                    self._update_session(session_id, {
                        'authenticated': True,
                        'user_profile': user_profile,
                        'locked_intent': intent,
                        'authentication_method': 'live_data_auto',
                        'authenticated_at': now()
                    })

                    safe_log_error(f"✅ Auto-authenticated user via live data: {user_profile.get('full_name')}", "Live Authentication")

                    # Generate immediate response with live data
                    return self._generate_authenticated_response(intent, message, user_profile, session_id, live_data)

            # Step 2: Authentication Gate
            if intent in self.authentication_required_intents and not is_authenticated:
                return self._initiate_authentication_gate(intent, message, session_id)
            
            # Step 3: Intent Lock-In (if authenticated)
            if is_authenticated and locked_intent:
                # Continue with locked intent unless user explicitly requests different assistance
                if self._is_intent_change_request(message):
                    # User wants to change intent - require re-authentication if needed
                    new_intent, _ = self._detect_intent(message)
                    if new_intent in self.authentication_required_intents:
                        return self._initiate_authentication_gate(new_intent, message, session_id)
                    else:
                        # Clear session for non-authenticated intent
                        self._clear_session(session_id)
                        return self._handle_general_query(message, user_context, session_id)
                else:
                    # Continue with locked intent
                    intent = locked_intent
            
            # Step 4: Personalized Response (for authenticated users)
            if is_authenticated:
                return self._generate_personalized_response(intent, message, session_data, session_id)
            else:
                # Handle general queries that don't require authentication
                return self._handle_general_query(message, user_context, session_id)
                
        except Exception as e:
            safe_log_error(f"Authentication workflow error: {str(e)}")
            return {
                'success': False,
                'error': 'workflow_error',
                'reply': "I'm experiencing technical difficulties. Please try again in a moment."
            }

    def _detect_intent(self, message: str) -> Tuple[str, float]:
        """Detect user intent from message."""
        
        message_lower = message.lower()
        
        # Intent patterns with keywords
        intent_patterns = {
            'payment_status': ['payment', 'pay', 'money', 'salary', 'wage', 'benefit', 'pension payment'],
            'pension_inquiry': ['pension', 'retirement', 'monthly benefit', 'pension status'],
            'claim_status': ['claim', 'compensation', 'injury', 'accident', 'medical'],
            'account_info': ['account', 'profile', 'information', 'details', 'personal'],
            'contribution_status': ['contribution', 'deduction', 'premium', 'monthly deduction'],
            'employment_info': ['employment', 'job', 'work', 'employer', 'employee'],
            'employer_services': ['employer', 'company', 'business', 'registration'],
            'compliance_status': ['compliance', 'return', 'submission', 'filing'],
            'employee_management': ['employee', 'staff', 'worker', 'manage'],
            'payment_history': ['history', 'past payments', 'previous', 'records'],
            'claim_submission': ['submit', 'file', 'new claim', 'report'],
            'document_status': ['document', 'certificate', 'report', 'paperwork'],
            'technical_help': ['help', 'support', 'problem', 'issue', 'error']
        }
        
        # Calculate confidence scores
        intent_scores = {}
        for intent, keywords in intent_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in message_lower:
                    score += 1
            if score > 0:
                intent_scores[intent] = score / len(keywords)
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            return best_intent, confidence
        
        return 'general', 0.0

    def _initiate_authentication_gate(self, intent: str, message: str, session_id: str) -> Dict[str, Any]:
        """Initiate authentication gate for protected intents."""
        
        intent_description = self.intent_descriptions.get(intent, 'access your information')
        
        # Store pending intent in session
        self._update_session(session_id, {
            'pending_intent': intent,
            'pending_message': message,
            'authentication_initiated': now(),
            'authenticated': False
        })
        
        # Generate authentication prompt
        auth_prompt = self._generate_authentication_prompt(intent, intent_description)
        
        return {
            'success': True,
            'authentication_required': True,
            'intent': intent,
            'reply': auth_prompt,
            'session_id': session_id
        }

    def _generate_authentication_prompt(self, intent: str, intent_description: str) -> str:
        """Generate comprehensive authentication prompt."""
        
        return (f"Hi! I'm WorkCom from WCFCB. To {intent_description}, I need to verify your identity first.\n\n"
                f"🔐 **Authentication Required**\n"
                f"Please provide:\n"
                f"• Your **NRC Number** (National Registration Card)\n"
                f"• Your **Reference Number** (one of the following):\n"
                f"  - Beneficiary Number (for pension recipients)\n"
                f"  - Employee Number (for current/former employees)\n"
                f"  - Employer Code (for registered employers)\n"
                f"  - Claim Number (for claim inquiries)\n\n"
                f"📝 **Format:** NRC_Number Reference_Number\n"
                f"**Example:** 123456789 BN-123456\n\n"
                f"🔒 This helps me provide you with accurate, personalized information while keeping your data secure.\n\n"
                f"You can also type 'help' if you need assistance finding these numbers.")

    def process_authentication_input(self, message: str, session_id: str) -> Dict[str, Any]:
        """Process authentication input and validate against live database."""
        
        try:
            session_data = self._get_session_data(session_id)
            pending_intent = session_data.get('pending_intent')
            
            if not pending_intent:
                return {
                    'success': False,
                    'error': 'no_pending_authentication',
                    'reply': "No authentication request found. Please start over with your request."
                }
            
            # Handle special commands
            if message.lower().strip() in ['help', 'assistance']:
                return self._handle_authentication_help(pending_intent)
            elif message.lower().strip() in ['cancel', 'stop', 'exit']:
                self._clear_session(session_id)
                return {
                    'success': True,
                    'reply': "Authentication cancelled. I'm still here to help with general questions about WCFCB services. What would you like to know?"
                }
            
            # Parse credentials
            credentials = self._parse_authentication_input(message)
            if not credentials:
                # Enhanced error handling with case-insensitive detection
                import re

                # Check if user provided only NRC
                if re.search(r'\d{6}/\d{2}/\d|\d{9,}', message):
                    return {
                        'success': False,
                        'error': 'missing_reference',
                        'reply': "Great! I can see your NRC number. Now I also need your Reference Number.\n\n🔐 Please provide both:\n• Your NRC: (I can see this)\n• Your Reference Number: Examples below\n\n📝 Reference Number Examples:\n• PEN-1234567 or pen_1234567 (Pension)\n• BN-123456 or bn_123456 (Beneficiary)\n• EMP-123456 or emp_123456 (Employee)\n\n💡 Format: NRC_Number Reference_Number\nExample: 123456/78/9 PEN_1234567\n\n✨ Note: Case doesn't matter - you can use PEN, pen, Pen, etc."
                    }

                # Check if user provided only reference
                elif re.search(r'(pen|bn|emp|beneficiary|pension|employee)[-_]?\d+', message.lower()):
                    return {
                        'success': False,
                        'error': 'missing_nrc',
                        'reply': "Great! I can see your Reference Number. Now I also need your NRC Number.\n\n🔐 Please provide both:\n• Your NRC Number: (from your National Registration Card)\n• Your Reference Number: (I can see this)\n\n📝 NRC Examples:\n• 123456/78/9 (standard format)\n• 123456789 (9-digit format)\n\n💡 Format: NRC_Number Reference_Number\nExample: 123456/78/9 PEN_1234567\n\n✨ Note: Case doesn't matter for reference numbers"
                    }

                else:
                    return {
                        'success': False,
                        'error': 'invalid_format',
                        'reply': "I couldn't recognize the format. Please provide your credentials as:\n\n📝 NRC_Number Reference_Number\n\n✅ Examples (case doesn't matter):\n• 123456/78/9 PEN_1234567\n• 123456/78/9 pen-1234567\n• 123456789 BN-123456\n• 123456/78/9 emp_123456\n\n🔍 Where to find:\n• NRC: Your National Registration Card\n• Reference: Depends on your relationship with WCFCB\n  - Pension recipients: PEN-xxxxxxx\n  - Beneficiaries: BN-xxxxxx\n  - Employees: EMP-xxxxxx\n\n💡 Tip: You can type in any case (PEN, pen, Pen all work!)"
                    }
            
            national_id, reference_number = credentials
            
            # Authenticate against live database
            if self.db_service:
                auth_result = self.db_service.authenticate_user_comprehensive(
                    national_id=national_id,
                    reference_number=reference_number,
                    intent=pending_intent
                )
                
                if auth_result['success']:
                    # Authentication successful - lock intent and create/update session
                    user_profile = auth_result['user_profile']

                    # ENHANCED SESSION CREATION: Comprehensive session data for new users
                    session_update_data = {
                        'authenticated': True,
                        'locked_intent': pending_intent,
                        'user_profile': user_profile,
                        'authentication_timestamp': now(),
                        'national_id': national_id,
                        'user_type': user_profile.get('user_type'),
                        'pending_intent': None,
                        'pending_message': None,
                        'first_authentication': True,  # Track if this is first auth in session
                        'conversation_context': {
                            'authenticated_at': now(),
                            'authentication_method': 'nrc_reference',
                            'user_preferences': {},
                            'interaction_history': []
                        }
                    }

                    # Update session with comprehensive data
                    self._update_session(session_id, session_update_data)

                    # Verify session was created successfully in database
                    try:
                        from assistant_crm.assistant_crm.services.session_context_manager import SessionContextManager
                        session_manager = SessionContextManager()

                        # Ensure session exists and is properly configured
                        db_session = session_manager.get_session_state(session_id)
                        if not db_session or not db_session.get('is_authenticated'):
                            # Force session creation if it doesn't exist
                            safe_log_error(f"Creating new database session for authenticated user {session_id}", "Session Creation")

                            # Create session with full user context
                            session_manager.set_authentication_state(session_id, {
                                'national_id': national_id,
                                'authenticated_at': now(),
                                'user_type': user_profile.get('user_type'),
                                'authentication_method': 'nrc_reference'
                            }, user_profile)

                            # Lock the intent
                            session_manager.lock_primary_intent(session_id, pending_intent)

                    except Exception as e:
                        safe_log_error(f"Session verification/creation error for {session_id}: {str(e)}", "Session Creation Error")

                    # Generate personalized welcome message
                    full_name = user_profile.get('full_name', 'valued member')
                    user_type = user_profile.get('user_type', 'member')

                    # Check if returning user based on profile data
                    is_returning_user = user_profile.get('last_login_date') is not None

                    if is_returning_user:
                        welcome_message = (f"Perfect! Welcome back, {full_name}. "
                                         f"I've verified your identity as a WCFCB {user_type}.\n\n"
                                         f"Now let me help you with your original request...")
                    else:
                        welcome_message = (f"Perfect! Welcome to WCFCB digital services, {full_name}. "
                                         f"I've verified your identity as a WCFCB {user_type}.\n\n"
                                         f"I'm WorkCom, your personal assistant. Let me help you with your request...")

                    # Phase 3: Generate immediate live data response for the pending intent
                    live_data_response = ""
                    live_data_used = False

                    if self.response_system and pending_intent:
                        try:
                            # Create session context for live response
                            session_context = {
                                'authenticated': True,
                                'user_profile': user_profile,
                                'locked_intent': pending_intent,
                                'session_id': session_id
                            }

                            # Get the original pending message if available
                            pending_message = session_data.get('pending_message', f'Help with {pending_intent}')

                            live_response = self.response_system.generate_live_response(
                                intent=pending_intent,
                                user_profile=user_profile,
                                message=pending_message,
                                session_context=session_context
                            )

                            if live_response.get('success'):
                                live_data_response = f"\n\n{live_response.get('reply', live_response.get('response', ''))}"
                                live_data_used = True
                                safe_log_error(f"Live data response generated for {pending_intent}", "Authentication Success")
                            else:
                                safe_log_error(f"Live response generation failed: {live_response.get('error')}", "Authentication Success")

                        except Exception as e:
                            safe_log_error(f"Error generating live response during authentication: {str(e)}", "Authentication Success")

                    # Combine welcome message with live data response
                    complete_response = welcome_message + live_data_response

                    return {
                        'success': True,
                        'authenticated': True,
                        'user_profile': user_profile,
                        'locked_intent': pending_intent,
                        'reply': complete_response,
                        'session_created': True,
                        'is_returning_user': is_returning_user,
                        'live_data_used': live_data_used,
                        'intent': pending_intent
                    }
                else:
                    # Authentication failed
                    error_message = auth_result.get('message', 'Unable to verify your credentials.')
                    return {
                        'success': False,
                        'error': 'authentication_failed',
                        'reply': f"{error_message}\n\nPlease double-check your information and try again, or contact our office for assistance."
                    }
            else:
                return {
                    'success': False,
                    'error': 'database_unavailable',
                    'reply': "Authentication system temporarily unavailable. Please try again later."
                }
                
        except Exception as e:
            safe_log_error(f"Authentication input processing error: {str(e)}")
            return {
                'success': False,
                'error': 'processing_error',
                'reply': "I'm sorry, there was an error processing your authentication. Please try again."
            }

    def _parse_authentication_input(self, message: str) -> Optional[Tuple[str, str]]:
        """
        Parse authentication input to extract NRC and reference number.

        ENHANCED: Case-insensitive parsing with comprehensive format support
        """
        import re

        # Clean the message (preserve original case for NRC, normalize for parsing)
        original_message = message.strip()
        message_lower = message.strip().lower()

        # Remove common prefixes (case-insensitive)
        message_lower = re.sub(r'^(nrc|reference|number|id|pension|pen|beneficiary|bn)\s+', '', message_lower)

        # Try different parsing strategies

        # Strategy 1: Standard format "NRC_Number Reference_Number" (any order)
        parts = original_message.split()
        if len(parts) >= 2:
            # Try both orders: NRC first, then reference first
            for i in range(len(parts)):
                for j in range(len(parts)):
                    if i != j:
                        potential_nrc = parts[i].strip()
                        potential_ref = parts[j].strip()

                        # Validate NRC format and reference format
                        if self._is_valid_nrc_format(potential_nrc) and self._is_valid_reference_format(potential_ref):
                            return (potential_nrc, potential_ref.upper())

        # Strategy 2: Single input that might be just NRC
        if len(parts) == 1:
            potential_input = parts[0].strip()
            if self._is_valid_nrc_format(potential_input):
                # Just NRC provided - ask for reference
                return None
            elif self._is_valid_reference_format(potential_input):
                # Just reference provided - ask for NRC
                return None

        # Strategy 3: Look for patterns anywhere in the message (case-insensitive)
        # NRC patterns
        nrc_patterns = [
            r'(\d{6}/\d{2}/\d)',  # 228597/62/1
            r'(\d{9,})',          # 123456789
            r'(\d{6}/\d{2}/\d{1,2})'  # Alternative formats
        ]

        # Reference patterns (case-insensitive)
        ref_patterns = [
            r'(pen[-_]?\d{7,})',      # PEN_0005000168, pen-1234567
            r'(pension[-_]?\d{4,})',   # PENSION_123456
            r'(bn[-_]?\d{4,})',        # BN-123456, bn_123456
            r'(emp[-_]?\d{4,})',       # EMP-123456
            r'(beneficiary[-_]?\d{4,})', # BENEFICIARY_123456
            r'([a-z]{2,3}[-_]?\d{4,})'  # Generic format
        ]

        nrc_match = None
        ref_match = None

        # Find NRC
        for pattern in nrc_patterns:
            match = re.search(pattern, original_message)
            if match:
                nrc_match = match.group(1)
                break

        # Find reference (case-insensitive)
        for pattern in ref_patterns:
            match = re.search(pattern, message_lower)
            if match:
                ref_match = match.group(1).upper()
                break

        if nrc_match and ref_match:
            return (nrc_match, ref_match)
        elif nrc_match:
            # Found NRC but no reference - guide user
            return None
        elif ref_match:
            # Found reference but no NRC - guide user
            return None

        return None

    def _is_valid_reference_format(self, ref: str) -> bool:
        """Validate reference number format (case-insensitive)."""
        import re

        ref_lower = ref.lower()

        # Pension number formats
        if re.match(r'^pen[-_]?\d{4,}$', ref_lower):
            return True

        # Beneficiary number formats
        if re.match(r'^bn[-_]?\d{4,}$', ref_lower):
            return True

        # Employee number formats
        if re.match(r'^emp[-_]?\d{4,}$', ref_lower):
            return True

        # Generic reference formats
        if re.match(r'^[a-z]{2,3}[-_]?\d{4,}$', ref_lower):
            return True

        # Pure numeric (at least 4 digits)
        if re.match(r'^\d{4,}$', ref):
            return True

        return False

    def _is_valid_nrc_format(self, nrc: str) -> bool:
        """Validate NRC format - supports multiple formats."""
        import re

        # Format 1: 228597/62/1 (standard Zambian NRC)
        if re.match(r'^\d{6}/\d{2}/\d$', nrc):
            return True

        # Format 2: 123456789 (9+ digits)
        if re.match(r'^\d{9,}$', nrc):
            return True

        # Format 3: 123456/78/9 (alternative format)
        if re.match(r'^\d{6}/\d{2}/\d{1,2}$', nrc):
            return True

        return False

    def _handle_authentication_help(self, intent: str) -> Dict[str, Any]:
        """Handle help requests during authentication."""
        
        help_messages = {
            'payment_status': "To check your payment status, I need:\n• Your NRC Number (on your National Registration Card)\n• Your Beneficiary Number (format: BN-123456) or Account Number",
            'claim_status': "To check your claim status, I need:\n• Your NRC Number\n• Your Claim Number (format: CL-2024-001234) or Beneficiary Number",
            'employment_info': "To access your employment information, I need:\n• Your NRC Number\n• Your Employee Number (format: EMP-123456) or Employer Code",
            'employer_services': "To access employer services, I need:\n• Your NRC Number (as contact person)\n• Your Employer Code (format: EMP-2024-001)"
        }
        
        help_message = help_messages.get(intent, 
            "I need to verify your identity to access your personal information. "
            "Please provide your NRC Number and relevant reference number.")
        
        return {
            'success': True,
            'reply': f"📋 **Authentication Help:**\n\n{help_message}\n\nPlease provide these details when you're ready."
        }

    def _is_intent_change_request(self, message: str) -> bool:
        """Check if user is requesting a different intent."""
        
        change_indicators = [
            'different', 'other', 'instead', 'rather', 'actually',
            'change', 'switch', 'new request', 'something else'
        ]
        
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in change_indicators)

    def _generate_personalized_response(self, intent: str, message: str,
                                      session_data: Dict, session_id: str) -> Dict[str, Any]:
        """Generate personalized response using real-time data."""

        try:
            user_profile = session_data.get('user_profile', {})
            user_type = user_profile.get('user_type')

            # Phase 3: Connect to RealTimeDataResponseSystem for live data
            if self.response_system:
                # Generate live response using the real-time data response system
                response_result = self.response_system.generate_live_response(
                    intent=intent,
                    user_profile=user_profile,
                    message=message,
                    session_context=session_data
                )

                if response_result.get('success'):
                    return {
                        'success': True,
                        'authenticated': True,
                        'intent': intent,
                        'user_profile': user_profile,
                        'reply': response_result.get('reply', response_result.get('response', 'Live data response generated')),
                        'live_data_used': True,
                        'data_sources': response_result.get('data_sources', ['live_database']),
                        'session_id': session_id
                    }
                else:
                    # Fallback if live response generation fails
                    safe_log_error(f"Live response generation failed for {intent}: {response_result.get('error')}", "Live Response")

            # Fallback: Generate basic personalized response if live system unavailable
            full_name = user_profile.get('full_name', 'valued member')

            fallback_responses = {
                'payment_status': f"Hello {full_name}, I'm checking your payment information. Please note that live data services are temporarily limited.",
                'pension_inquiry': f"Hello {full_name}, I'm looking up your pension details. Please note that live data services are temporarily limited.",
                'claim_status': f"Hello {full_name}, I'm checking your claim status. Please note that live data services are temporarily limited.",
                'account_info': f"Hello {full_name}, I'm retrieving your account information. Please note that live data services are temporarily limited."
            }

            fallback_reply = fallback_responses.get(intent,
                f"Hello {full_name}, I'm processing your {intent} request. Please note that live data services are temporarily limited.")

            return {
                'success': True,
                'authenticated': True,
                'intent': intent,
                'user_profile': user_profile,
                'reply': fallback_reply,
                'live_data_used': False,
                'fallback_response': True,
                'session_id': session_id
            }

        except Exception as e:
            safe_log_error(f"Error generating personalized response: {str(e)}", "Personalized Response")
            return {
                'success': False,
                'error': 'response_generation_failed',
                'reply': "I apologize, but I encountered an issue generating your personalized response. Please try again.",
                'session_id': session_id
            }

    def is_authentication_in_progress(self, session_id: str) -> bool:
        """Check if authentication is currently in progress for a session."""
        try:
            session_data = self._get_session_data(session_id)

            # Check if there's a pending intent (authentication initiated but not completed)
            has_pending_intent = session_data.get('pending_intent') is not None
            is_authenticated = session_data.get('authenticated', False)

            # Authentication is in progress if there's a pending intent and user is not yet authenticated
            return has_pending_intent and not is_authenticated

        except Exception as e:
            safe_log_error(f"Error checking authentication progress for {session_id}: {str(e)}", "Auth Progress Check")
            return False

    def _handle_general_query(self, message: str, user_context: Dict, session_id: str) -> Dict[str, Any]:
        """Handle general queries that don't require authentication."""

        # This will use the existing knowledge base system
        return {
            'success': True,
            'authenticated': False,
            'reply': "I can help you with general information about WCFCB services. For personalized information, I'll need to verify your identity first.",
            'requires_knowledge_base': True
        }

    def _get_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Get session data with synchronized storage support.

        CRITICAL FIX: Checks memory first for performance, then database as fallback.
        This resolves the "Conversation Session not found" error by ensuring
        session data is available from either storage system.
        """

        if not hasattr(self, '_sessions'):
            self._sessions = {}

        # Try memory first for performance
        memory_session = self._sessions.get(session_id, {})

        # If no memory session or incomplete data, try database fallback
        if not memory_session or not memory_session.get('synchronized_with_db'):
            try:
                # Import here to avoid circular imports
                from assistant_crm.assistant_crm.services.session_context_manager import SessionContextManager
                session_manager = SessionContextManager()
                db_session = session_manager.get_session_state(session_id)

                # Convert database session to memory format if authenticated
                if db_session and db_session.get('is_authenticated'):
                    memory_session = {
                        'authenticated': True,
                        'locked_intent': db_session.get('primary_intent'),
                        'user_profile': db_session.get('user_profile', {}),
                        'authentication_timestamp': db_session.get('last_activity'),
                        'user_type': db_session.get('user_profile', {}).get('user_type'),
                        'national_id': db_session.get('authentication_state', {}).get('national_id'),
                        'synchronized_with_db': True
                    }
                    # Cache in memory for subsequent requests
                    self._sessions[session_id] = memory_session
                    safe_log_error(f"Session {session_id} restored from database", "Session Sync Recovery")
                elif db_session and not db_session.get('is_authenticated'):
                    # Session exists but not authenticated - check for pending authentication
                    pending_intent = db_session.get('session_metadata', {}).get('pending_intent')
                    if pending_intent:
                        memory_session = {
                            'pending_intent': pending_intent,
                            'authenticated': False,
                            'synchronized_with_db': True
                        }
                        self._sessions[session_id] = memory_session

            except Exception as e:
                safe_log_error(f"Session retrieval error for {session_id}: {str(e)}", "Authentication Session Retrieval")
                # Continue with memory session even if database fails

        return memory_session

    def _update_session(self, session_id: str, data: Dict[str, Any]):
        """
        Update session data with synchronized storage.

        CRITICAL FIX: Updates both memory AND database to ensure session persistence.
        This prevents the "Conversation Session not found" error by maintaining
        session data in both storage systems.
        """

        if not hasattr(self, '_sessions'):
            self._sessions = {}

        if session_id not in self._sessions:
            self._sessions[session_id] = {}

        # Update memory cache for immediate access
        self._sessions[session_id].update(data)

        # CRITICAL FIX: Synchronize with database session
        try:
            # Import here to avoid circular imports
            from assistant_crm.assistant_crm.services.session_context_manager import SessionContextManager
            session_manager = SessionContextManager()

            # Get or create session in database
            session_state = session_manager.get_session_state(session_id)

            # Ensure session_state is not None
            if session_state is None:
                session_state = {}

            # Prepare database updates based on authentication data
            db_updates = {}

            # Handle authentication state changes
            if data.get('authenticated'):
                db_updates['status'] = 'authenticated'

            # Handle intent locking
            if data.get('locked_intent'):
                db_updates['primary_intent'] = data['locked_intent']

            # Handle user profile storage
            if data.get('user_profile'):
                db_updates['user_profile'] = data['user_profile']

            # Handle authentication metadata
            if data.get('national_id') or data.get('authentication_timestamp') or data.get('user_type'):
                auth_state = session_state.get('authentication_state', {})
                if data.get('national_id'):
                    auth_state['national_id'] = data['national_id']
                if data.get('authentication_timestamp'):
                    auth_state['authenticated_at'] = data['authentication_timestamp']
                if data.get('user_type'):
                    auth_state['user_type'] = data['user_type']
                db_updates['authentication_state'] = auth_state

            # Handle pending authentication state
            if data.get('pending_intent') or data.get('authentication_initiated'):
                session_metadata = session_state.get('session_metadata', {})
                if data.get('pending_intent'):
                    session_metadata['pending_intent'] = data['pending_intent']
                if data.get('authentication_initiated'):
                    session_metadata['authentication_initiated'] = data['authentication_initiated']
                if data.get('pending_message'):
                    session_metadata['pending_message'] = data['pending_message']
                db_updates['session_metadata'] = session_metadata

            # Apply database updates if any
            if db_updates:
                success = session_manager.update_session_state(session_id, db_updates)
                if success:
                    # Mark as synchronized in memory
                    self._sessions[session_id]['synchronized_with_db'] = True
                    safe_log_error(f"Session {session_id} synchronized to database successfully", "Session Sync Success")
                else:
                    safe_log_error(f"Failed to synchronize session {session_id} to database", "Session Sync Warning")

        except Exception as e:
            # Log error but don't fail authentication - graceful degradation
            safe_log_error(f"Session sync error for {session_id}: {str(e)}", "Authentication Session Sync")
            # Mark as not synchronized so we can retry later
            if session_id in self._sessions:
                self._sessions[session_id]['synchronized_with_db'] = False

    def _clear_session(self, session_id: str):
        """
        Clear session data from both memory and database.

        Enhanced to maintain synchronization between storage systems.
        """

        # Clear from memory
        if hasattr(self, '_sessions') and session_id in self._sessions:
            del self._sessions[session_id]

        # Clear from database (mark as inactive rather than delete for audit trail)
        try:
            from assistant_crm.assistant_crm.services.session_context_manager import SessionContextManager
            session_manager = SessionContextManager()

            # Update session status to inactive instead of deleting
            session_manager.update_session_state(session_id, {
                'status': 'inactive',
                'primary_intent': None,
                'authentication_state': {},
                'session_metadata': {'cleared_at': now(), 'reason': 'user_requested'}
            })

            safe_log_error(f"Session {session_id} cleared and marked inactive", "Session Clear")

        except Exception as e:
            safe_log_error(f"Error clearing session {session_id} from database: {str(e)}", "Session Clear Error")

    def is_authentication_in_progress(self, session_id: str) -> bool:
        """Check if authentication is in progress for a session."""
        
        session_data = self._get_session_data(session_id)
        return session_data.get('pending_intent') is not None and not session_data.get('authenticated', False)

    def is_user_authenticated(self, session_id: str) -> bool:
        """Check if user is authenticated for a session."""

        session_data = self._get_session_data(session_id)
        return session_data.get('authenticated', False)

    def recover_session_from_database(self, session_id: str) -> bool:
        """
        Attempt to recover session data from database if memory is lost.

        This method provides session recovery capabilities for cases where
        the authentication workflow memory is cleared but database session exists.
        """
        try:
            from assistant_crm.assistant_crm.services.session_context_manager import SessionContextManager
            session_manager = SessionContextManager()

            # Get session from database
            db_session = session_manager.get_session_state(session_id)

            if db_session and db_session.get('is_authenticated'):
                # Restore session to memory
                recovered_data = {
                    'authenticated': True,
                    'locked_intent': db_session.get('primary_intent'),
                    'user_profile': db_session.get('user_profile', {}),
                    'authentication_timestamp': db_session.get('last_activity'),
                    'user_type': db_session.get('user_profile', {}).get('user_type'),
                    'national_id': db_session.get('authentication_state', {}).get('national_id'),
                    'synchronized_with_db': True,
                    'recovered_from_db': True
                }

                # Initialize memory storage if needed
                if not hasattr(self, '_sessions'):
                    self._sessions = {}

                self._sessions[session_id] = recovered_data

                safe_log_error(f"Session {session_id} successfully recovered from database", "Session Recovery Success")
                return True

            return False

        except Exception as e:
            safe_log_error(f"Session recovery failed for {session_id}: {str(e)}", "Session Recovery Error")
            return False

    def ensure_session_consistency(self, session_id: str) -> Dict[str, Any]:
        """
        Ensure session consistency between memory and database.

        This method validates and repairs session data inconsistencies
        that might cause "session not found" errors.
        """
        try:
            memory_session = self._sessions.get(session_id, {}) if hasattr(self, '_sessions') else {}

            from assistant_crm.assistant_crm.services.session_context_manager import SessionContextManager
            session_manager = SessionContextManager()
            db_session = session_manager.get_session_state(session_id)

            consistency_report = {
                'session_id': session_id,
                'memory_exists': bool(memory_session),
                'database_exists': bool(db_session),
                'memory_authenticated': memory_session.get('authenticated', False),
                'database_authenticated': db_session.get('is_authenticated', False) if db_session else False,
                'consistent': False,
                'action_taken': None
            }

            # Check for inconsistencies
            if memory_session.get('authenticated') and not (db_session and db_session.get('is_authenticated')):
                # Memory says authenticated but database doesn't - sync to database
                self._update_session(session_id, memory_session)
                consistency_report['action_taken'] = 'synced_memory_to_database'

            elif not memory_session.get('authenticated') and db_session and db_session.get('is_authenticated'):
                # Database says authenticated but memory doesn't - recover from database
                self.recover_session_from_database(session_id)
                consistency_report['action_taken'] = 'recovered_from_database'

            elif memory_session.get('authenticated') and db_session and db_session.get('is_authenticated'):
                # Both authenticated - check data consistency
                if memory_session.get('locked_intent') != db_session.get('primary_intent'):
                    # Sync intent to database
                    self._update_session(session_id, {'locked_intent': memory_session.get('locked_intent')})
                    consistency_report['action_taken'] = 'synced_intent_to_database'

            consistency_report['consistent'] = True
            return consistency_report

        except Exception as e:
            safe_log_error(f"Session consistency check failed for {session_id}: {str(e)}", "Session Consistency Error")
            return {
                'session_id': session_id,
                'consistent': False,
                'error': str(e),
                'action_taken': 'error_occurred'
            }

    def _generate_authenticated_response(self, intent: str, message: str, user_profile: Dict, session_id: str, live_data: Dict) -> Dict[str, Any]:
        """Generate immediate authenticated response using live data"""
        try:
            beneficiary_data = live_data.get('beneficiary_data', {})
            pension_data = live_data.get('pension_data', {})
            claims_data = live_data.get('claims_data', [])
            payment_data = live_data.get('payment_data', [])

            full_name = user_profile.get('full_name', 'Valued Member')

            # Generate personalized response based on intent and live data
            if intent == 'claim_status':
                if claims_data:
                    claim = claims_data[0]  # Get the first/most recent claim
                    response = f"Hello {full_name}! I've found your claim information.\n\n"
                    response += f"📋 **Claim Status Update**\n"
                    response += f"• Claim Number: {claim.get('claim_number', 'N/A')}\n"
                    response += f"• Status: {claim.get('status', 'N/A')}\n"
                    response += f"• Claim Type: {claim.get('claim_type', 'N/A')}\n"
                    response += f"• Amount: K{claim.get('amount', 0):,.2f}\n"
                    response += f"• Date Submitted: {claim.get('date_submitted', 'N/A')}\n\n"
                    response += "Is there anything specific about your claim you'd like to know more about?"
                else:
                    response = f"Hello {full_name}! I've accessed your account.\n\n"
                    response += "📋 **Claim Status**\n"
                    response += "You currently have no active claims in our system.\n\n"
                    response += "If you need to submit a new claim or have questions about previous claims, I'm here to help!"

            elif intent == 'pension_inquiry':
                if pension_data:
                    response = f"Hello {full_name}! Here's your pension information.\n\n"
                    response += f"💰 **Pension Details**\n"
                    response += f"• Monthly Amount: K{pension_data.get('pension_amount', 0):,.2f}\n"
                    response += f"• Status: {pension_data.get('pension_status', 'N/A')}\n"
                    response += f"• Start Date: {pension_data.get('pension_start_date', 'N/A')}\n\n"
                    response += "Would you like information about your next payment or payment history?"
                else:
                    response = f"Hello {full_name}! I've accessed your account.\n\n"
                    response += "I don't see any active pension information. If you believe this is an error, please contact our office."

            elif intent == 'payment_status':
                if payment_data:
                    payment = payment_data[0]  # Get the most recent payment
                    response = f"Hello {full_name}! Here's your latest payment information.\n\n"
                    response += f"💳 **Recent Payment**\n"
                    response += f"• Date: {payment.get('payment_date', 'N/A')}\n"
                    response += f"• Amount: K{payment.get('amount', 0):,.2f}\n"
                    response += f"• Method: {payment.get('payment_method', 'N/A')}\n"
                    response += f"• Status: {payment.get('status', 'N/A')}\n\n"
                    response += "Would you like to see your payment history or have questions about upcoming payments?"
                else:
                    response = f"Hello {full_name}! I've accessed your account.\n\n"
                    response += "I don't see any recent payment records. If you're expecting a payment, please contact our office."
            else:
                # General authenticated response
                response = f"Hello {full_name}! I've successfully verified your identity.\n\n"
                response += "I can help you with:\n"
                response += "• Claim status and updates\n"
                response += "• Pension information\n"
                response += "• Payment history\n"
                response += "• Account details\n\n"
                response += "What would you like to know about?"

            return {
                'success': True,
                'authenticated': True,
                'user_profile': user_profile,
                'reply': response,
                'live_data_used': True,
                'intent': intent,
                'session_id': session_id,
                'authentication_method': 'live_data_auto'
            }

        except Exception as e:
            safe_log_error(f"Error generating authenticated response: {str(e)}", "Live Authentication")
            return {
                'success': False,
                'error': str(e),
                'reply': f"Hello {user_profile.get('full_name', 'Valued Member')}! I've verified your identity but encountered an error retrieving your information. Please try again."
            }

