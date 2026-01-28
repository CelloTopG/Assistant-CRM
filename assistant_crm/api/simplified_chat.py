#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WCFCB Assistant CRM - Simplified Single Dataflow Chat API
=========================================================

CLEAN, SINGLE DATAFLOW IMPLEMENTATION
- One API endpoint: send_message()
- Direct flow: Message → Intent Router → Live Data → AI Response
- No session management, no authentication, no response assembler
- No redundant endpoints, no duplicate logic
- Direct to Gemini AI for response generation

Author: WCFCB Development Team
Created: 2025-09-09 (Dataflow Cleanup Phase)
License: MIT
"""

import json
import time
import re
from typing import Dict, Any, Optional

# Safe frappe import with fallbacks
try:
    import frappe
    from frappe.utils import now
    from frappe import _
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    from datetime import datetime
    now = lambda: datetime.now().isoformat()
    _ = lambda x: x
    FRAPPE_AVAILABLE = False

# Import core services for single dataflow
try:
    from assistant_crm.services.intent_router import get_intent_router
    from assistant_crm.services.gemini_service import GeminiService
    from assistant_crm.services.enhanced_authentication_service import EnhancedAuthenticationService
    from assistant_crm.services.enhanced_ai_service import EnhancedAIService
except ImportError:
    # Fallback for development
    get_intent_router = lambda: None
    GeminiService = None
    EnhancedAuthenticationService = None
    EnhancedAIService = None

def safe_log_error(message: str, title: str = "Error") -> None:
    """Safe error logging with fallback"""
    if FRAPPE_AVAILABLE and frappe:
        try:
            frappe.log_error(message, title)
        except:
            pass

class SimplifiedChatAPI:
    """
    Simplified single dataflow chat API

    SINGLE FLOW: Message → Intent Detection → Live Data → AI Response
    NO: Session management, authentication, response assembler, redundant endpoints
    """

    def __init__(self):
        """Initialize simplified chat API"""
        self.intent_router = None
        self.gemini_service = None
        self.ai_service = None
        self.auth_service = None
        # Lightweight in-memory conversation store keyed by session id
        self._conv_store = {}
        self._initialize_services()

    def _initialize_services(self) -> None:
        """Initialize required services for single dataflow"""
        try:
            # Initialize intent router (handles caching and live data routing)
            self.intent_router = get_intent_router()

            # Initialize Gemini service for AI responses (kept for backward compatibility/fallbacks)
            if GeminiService:
                self.gemini_service = GeminiService()

            # Initialize Antoine/OpenAI service for conversational replies
            if EnhancedAIService:
                try:
                    self.ai_service = EnhancedAIService()
                except Exception as ae:
                    safe_log_error(f"AI service init failed: {str(ae)}", "SimplifiedChat Init")
                    self.ai_service = None

            # Authentication Gate temporarily disabled: all messages go directly to AI.
            # We deliberately do NOT initialize EnhancedAuthenticationService here so that
            # the chat flow remains fully AI-driven without backend NRC/claim gating.
            self.auth_service = None

        except Exception as e:
            safe_log_error(f"Service initialization error: {str(e)}", "SimplifiedChat Init")

    def process_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        SINGLE DATAFLOW with Authentication Gate:
        Message → Intent Router → (Auth Gate for live data) → Live Data → AI Response
        """
        start_time = time.time()
        try:
            # Step 1: Basic validation
            if not message or not message.strip():
                return self._error_response("Message cannot be empty")

            # Step 2: Ensure router
            if not self.intent_router:
                return self._error_response("Intent router not available")

            # Base user context (unauthenticated guest)
            user_context = {
                'user_id': 'guest',
                'user_role': 'guest',
                'authenticated': False
            }

            # Establish a stable session id up-front for continuity
            sid = self._derive_session_id(session_id)
            try:
                self._debug_log(f"turn:start sid={sid} msg='{(message or '')[:80]}'")
            except Exception:
                pass

            # Record user message in conversation history from the very first turn
            self._append_history(sid, role="user", text=message)

            # If we have an auth service, hydrate context from any existing session state
            auth_ctx = None
            if self.auth_service and sid:
                try:
                    auth_ctx = self.auth_service.get_auth_context(sid)
                except Exception:
                    auth_ctx = None

            # If already authenticated in this session, carry that context forward
            if auth_ctx and auth_ctx.get('authenticated'):
                user_profile = auth_ctx.get('user_profile')
                if isinstance(user_profile, dict) and user_profile:
                    user_context = dict(user_profile)
                    user_context['authenticated'] = True

            # Conversation state for history and any in-flight flows (e.g. claim choices)
            conv_state = self._get_conversation_state(sid)

            # Initial routing without any session-level intent locking
            routing_result = self.intent_router.route_request(
                message,
                user_context,
            )
            intent = routing_result.get('intent', 'unknown')
            try:
                self._debug_log(
                    f"route: post sid={sid} intent={intent} "
                    f"conf={routing_result.get('confidence')} "
                    f"source={routing_result.get('source')}"
                )
            except Exception:
                pass

            # Live intents set
            live_intents = set()
            try:
                live_intents = set(self.intent_router.get_live_data_intents())
            except Exception:
                pass

            if intent in live_intents and self.auth_service:
                # keep existing sid derived earlier
                # Debug: Auth Gate trigger
                try:
                    self._debug_log(f"AuthGate: triggered intent={intent}, session_id={sid}, looks_like_credentials={self._looks_like_credentials(message)}")
                except Exception:
                    pass

                # If auth is in progress or message looks like credentials, process it
                if self.auth_service.is_authentication_in_progress(sid) or self._looks_like_credentials(message):
                    auth_res = self.auth_service.process_authentication_input(message, intent, sid, user_context) or {}
                    try:
                        self._debug_log(f"AuthGate: result sid={sid} next={(auth_res or {}).get('next_action')} success={(auth_res or {}).get('success')} step={(self.auth_service.get_auth_context(sid) or {}).get('step')}")
                    except Exception:
                        pass

                    # If authenticated, update context and proceed to live data + AI
                    authenticated_user = auth_res.get('authenticated_user')
                    if authenticated_user and isinstance(authenticated_user, dict):
                        # Debug: Auth completion
                        try:
                            self._debug_log(f"AuthGate: authenticated user={authenticated_user.get('user_id')} intent={intent} — proceeding to live data")
                        except Exception:
                            pass

                        user_context = authenticated_user
                        user_context['authenticated'] = True
                        # Re-route with authenticated context to get live data for the same intent
                        routing_result = self.intent_router.route_request(
                            message, user_context, forced_intent=intent
                        )
                        # Debug: re-route after auth completion
                        try:
                            rr_i = (routing_result or {}).get('intent') if isinstance(routing_result, dict) else None
                            rr_s = (routing_result or {}).get('source') if isinstance(routing_result, dict) else None
                            self._debug_log(f"route: post-auth sid={sid} intent={rr_i} source={rr_s} null={routing_result is None}")
                        except Exception:
                            pass
                        # Ultra-verbose: log live data type and claim count right after post-auth re-route
                        try:
                            if isinstance(routing_result, dict) and routing_result.get('source') == 'live_data':
                                _data = routing_result.get('data') or {}
                                # Unwrap if nested under 'data'
                                if isinstance(_data, dict) and 'type' not in _data and isinstance(_data.get('data'), dict):
                                    _data = _data.get('data')
                                _dtype = _data.get('type') if isinstance(_data, dict) else None
                                _claims = _data.get('claims') if isinstance(_data, dict) else None
                                _count = len(_claims) if isinstance(_claims, list) else 0 if _claims is not None else None
                                _keys = list(_data.keys())[:6] if isinstance(_data, dict) else []
                                self._debug_log(f"route: post-auth-live sid={sid} type={_dtype} claims={_count} keys={_keys}")
                        except Exception:
                            pass

                        # If multiple claims found, prompt the user to choose one before proceeding
                        try:
                            if routing_result.get('source') == 'live_data':
                                data = routing_result.get('data') or {}
                                # Backward-compat: unwrap if router returned a nested 'data'
                                if isinstance(data, dict) and 'type' not in data and isinstance(data.get('data'), dict):
                                    data = data.get('data')
                                if isinstance(data, dict) and data.get('type') == 'claim_data':
                                    claims = data.get('claims') or []
                                    if isinstance(claims, list) and len(claims) > 1:
                                        # Build a concise list (up to 5)
                                        lines = []
                                        claim_ids = []
                                        for i, cl in enumerate(claims[:5], 1):
                                            cid = (cl.get('claim_id') or f"Claim {i}")
                                            status = cl.get('status') or 'Unknown'
                                            stage = cl.get('current_stage') or ''
                                            suffix = f" · {stage}" if stage else ''
                                            lines.append(f"{i}) {cid} — {status}{suffix}")
                                            claim_ids.append(cl.get('claim_id'))
                                        prompt = (
                                            "I found multiple claims on your profile:\n\n" +
                                            "\n".join(lines) +
                                            "\n\nPlease reply with the number (1-5) or the claim ID you want details on."
                                        )
                                        self._set_pending_claim_choices(sid, claim_ids)
                                        # Record assistant prompt in history and return immediately
                                        self._append_history(sid, role="assistant", text=prompt)
                                        return {
                                            'success': True,
                                            'message': prompt,
                                            'response': prompt,
                                            'reply': prompt,
                                            'metadata': {
                                                'intent': routing_result.get('intent', intent),
                                                'confidence': routing_result.get('confidence', 0),
                                                'source': routing_result.get('source', 'live_data'),
                                                'live_data_used': True,
                                                'authenticated': True
                                            },
                                            'session_id': sid,
                                            'timestamp': now()
                                        }
                        except Exception:
                            pass


                        # If live data is available and we don't need disambiguation, return it directly (no AI)
                        try:
                            if routing_result.get('source') == 'live_data' and isinstance(routing_result.get('data'), dict):
                                data = routing_result.get('data') or {}
                                # Backward-compat: unwrap if router returned a nested 'data'
                                if isinstance(data, dict) and 'type' not in data and isinstance(data.get('data'), dict):
                                    data = data.get('data')
                                # When there is 0 or 1 claim, respond deterministically without calling Gemini
                                if data.get('type') == 'claim_data':
                                    claims = data.get('claims') or []
                                    if len(claims) <= 1:
                                        direct_reply = self._format_live_data_response(intent, data)
                                        # Record assistant reply in history and return immediately
                                        self._append_history(sid, role="assistant", text=direct_reply)
                                        response_time = time.time() - start_time
                                        return {
                                            'success': True,
                                            'message': direct_reply,
                                            'response': direct_reply,
                                            'reply': direct_reply,
                                            'metadata': {
                                                'intent': routing_result.get('intent', intent),
                                                'confidence': routing_result.get('confidence', 0),
                                                'source': routing_result.get('source', 'live_data'),
                                                'live_data_used': True,
                                                'authenticated': True,
                                                'response_time': round(response_time, 3)
                                            },
                                            'session_id': sid,
                                            'timestamp': now()
                                        }
                        except Exception:
                            pass

                        ai_response = self._generate_ai_response(message, routing_result, sid=sid)
                        response_time = time.time() - start_time
                        # Record assistant reply in history
                        self._append_history(sid, role="assistant", text=ai_response)
                        return {
                            'success': True,
                            'message': ai_response,
                            'response': ai_response,
                            'reply': ai_response,
                            'metadata': {
                                'intent': routing_result.get('intent', intent),
                                'confidence': routing_result.get('confidence', 0),
                                'source': routing_result.get('source', 'unknown'),
                                'live_data_used': routing_result.get('source') == 'live_data',
                                'authenticated': True,
                                'response_time': round(response_time, 3)
                            },
                            'session_id': sid,
                            'timestamp': now()
                        }

                    # Not yet complete - keep auth state updated but let Antoine phrase the next step.
                    # We deliberately do NOT return the static auth_res.message here; instead we fall
                    # through so _generate_ai_response can use auth_context to ask for NRC / Full Name
                    # or other credentials in a natural way.
                    try:
                        self._debug_log(
                            f"AuthGate: in_progress sid={sid} intent={intent} "
                            f"next={auth_res.get('next_action')} authed_user=False"
                        )
                    except Exception:
                        pass
                else:
                    # Start authentication flow silently; Antoine will handle the wording.
                    try:
                        prompt = self.auth_service.get_authentication_prompt(
                            intent, message, user_context, sid
                        )
                    except Exception:
                        prompt = None
                    try:
                        self._debug_log(
                            f"AuthGate: start sid={sid} intent={intent} "
                            f"prompt_preview='{(prompt or '')[:80]}'"
                        )
                    except Exception:
                        pass
                    # Do not append the raw prompt to history or return it directly here.
                    # We fall through so _generate_ai_response can craft the visible message.

            # Step 3: Generate AI response using Gemini (no auth needed or non-live intent)
            ai_response = self._generate_ai_response(message, routing_result, sid=sid)

            # Step 4: Return clean response
            response_time = time.time() - start_time
            # Record assistant reply in history
            self._append_history(sid, role="assistant", text=ai_response)
            return {
                'success': True,
                'message': ai_response,
                'response': ai_response,
                'reply': ai_response,
                'metadata': {
                    'intent': routing_result.get('intent', 'unknown'),
                    'confidence': routing_result.get('confidence', 0),
                    'source': routing_result.get('source', 'unknown'),
                    'live_data_used': routing_result.get('source') == 'live_data',
                    'cache_hit': routing_result.get('cache_hit', False),
                    'response_time': round(response_time, 3)
                },
                'session_id': sid,
                'timestamp': now()
            }
        except Exception as e:
            safe_log_error(f"Message processing error: {str(e)}", "SimplifiedChat Error")
            return self._error_response(f"Processing error: {str(e)}")
    def _debug_log(self, msg: str) -> None:
        """Lightweight debug logger to Frappe logs (and stdout/bench logs + webhook_debug.log)."""
        try:
            # Always try to log to standard Frappe log for visibility
            if FRAPPE_AVAILABLE and frappe:
                try:
                    frappe.logger("SimplifiedChat").info(msg)
                except Exception:
                    pass
            # Also append to webhook_debug.log for easy tailing alongside platform events
            try:
                with open("/workspace/development/frappe-bench/logs/webhook_debug.log", "a") as f:
                    f.write(f"[SimplifiedChat] {msg}\n")
            except Exception:
                pass
                try:
                    frappe.log_error(msg, "SimplifiedChat Debug")
                except Exception:
                    pass
            # Also print so worker.log captures it during background jobs
            print(f"[SimplifiedChat] {msg}")
        except Exception:
            pass


    def _looks_like_credentials(self, text: str) -> bool:
        """Detect credential-like input using known patterns, not word length."""
        try:
            if not text:
                return False
            # Only treat as name credentials if user explicitly provides a name phrase
            # e.g., "my name is First Last" or "I am First Last"
            if re.search(r"(?:^|\b)(?:my\s+name\s+is|i\s+am|i'm|im|name\s*:)[\s:]*([A-Za-z][A-Za-z\-\.' ]{1,50}\s+[A-Za-z][A-Za-z\-\.' ]{1,50})\b", text, re.IGNORECASE):
                return True
            tokens = re.findall(r"[A-Za-z0-9/\-]+", text)
            if not tokens:
                return False
            patterns = [
                r"^[0-9]{9}$",                    # National ID (digits only) - strict 9 digits
                r"^[0-9]{6,8}/[0-9]{2}/[0-9]{1}$",# Zambian NRC with slashes (still totals 9 digits)
                r"^(CL|WC)-[0-9]{4}-[0-9]{4,6}$", # Claim number
                r"^ACC[0-9]{6,12}$",              # Account number
                r"^BN-[0-9]{4,6}$",               # Beneficiary number
                r"^EMP-[0-9]{4,6}$",              # Employer ID
            ]
            for tok in tokens:
                for pat in patterns:
                    if re.match(pat, tok, re.IGNORECASE):
                        return True
            return False
        except Exception:
            return False

    def _ensure_session_id(self) -> str:
        """Create a minimal ephemeral session id when none is supplied."""
        return f"sess-{int(time.time()*1000)}"


    def _derive_session_id(self, provided: Optional[str]) -> str:
        """Derive a stable session id. Prefer provided; else use Frappe's session sid; else generate one."""
        if provided and isinstance(provided, str) and provided.strip():
            return provided.strip()
        try:
            if FRAPPE_AVAILABLE and frappe and getattr(frappe, 'session', None):
                sid = getattr(frappe.session, 'sid', None)
                if sid:
                    return sid
        except Exception:
            pass
        return self._ensure_session_id()

    def _get_conversation_state(self, sid: str) -> Dict[str, Any]:
        """Get or initialize lightweight conversation state for a session (30 min TTL).

        This holds only lightweight, non-locking state such as rolling history and
        any pending claim choices for disambiguation.
        """
        ttl_seconds = 30 * 60
        now_ts = time.time()
        try:
            if FRAPPE_AVAILABLE and frappe:
                key = f"assistant_crm:conv:{sid}"
                state = frappe.cache().get_value(key)
                if not state or (now_ts - state.get('last_update_ts', now_ts)) > ttl_seconds:
                    state = {
                        'created_ts': now_ts,
                        'last_update_ts': now_ts,
                        'history': [],
                        'pending_claim_choices': None,
                    }
                # Write back to refresh TTL
                frappe.cache().set_value(key, state, expires_in_sec=ttl_seconds)
                return state
        except Exception:
            pass
        # Fallback to in-process store
        state = self._conv_store.get(sid)
        if not state or (now_ts - state.get('last_update_ts', now_ts)) > ttl_seconds:
            state = {
                'created_ts': now_ts,
                'last_update_ts': now_ts,
                'history': [],
                'pending_claim_choices': None,
            }
            self._conv_store[sid] = state
        return state

    def _append_history(self, sid: str, role: str, text: str) -> None:
        """Append a message to conversation history, keeping a small rolling window."""
        try:
            if not sid:
                return
            state = self._get_conversation_state(sid)
            entry = {
                'role': role,
                'text': (text or '')[:2000],
                'ts': now()
            }
            state['history'].append(entry)
            if len(state['history']) > 20:
                state['history'] = state['history'][-20:]
            state['last_update_ts'] = time.time()
            # Persist when possible
            if FRAPPE_AVAILABLE and frappe:
                try:
                    key = f"assistant_crm:conv:{sid}"
                    frappe.cache().set_value(key, state, expires_in_sec=30*60)
                except Exception:
                    pass
            else:
                self._conv_store[sid] = state
        except Exception:
            pass

    def _format_live_data_response(self, intent: str, data: Dict[str, Any]) -> str:
        """Deterministic, context-aware reply builder for live data results.
        Keeps tone consistent with Anna while avoiding re-prompts for NRC.
        """
        try:
            if intent == 'claim_status' and data.get('type') == 'claim_data':
                claims = data.get('claims') or []
                person = (data.get('erpnext_data') or {}).get('person') or {}
                name_hint = person.get('full_name') or data.get('primary_name') or ''
                nrc_hint = data.get('nrc_number') or ''

                if not claims:
                    header = f"I couldn't find any claims linked to NRC {nrc_hint}." if nrc_hint else "I couldn't find any claims on your profile."
                    return (f"{header}\n\n"
                            f"If you have a claim number, please share it and I’ll look it up immediately. "
                            f"Otherwise, we can escalate this to a human agent to investigate further.")

                # Single-claim summary
                c = claims[0]
                status = c.get('status') or c.get('current_status') or 'Unknown'
                stage = c.get('current_stage') or c.get('stage') or '—'
                cid = c.get('claim_id') or c.get('claim_number') or c.get('id') or '—'
                filed = c.get('date_filed') or c.get('created') or ''

                lines = []
                if name_hint:
                    lines.append(f"Beneficiary: {name_hint}")
                if nrc_hint:
                    lines.append(f"NRC: {nrc_hint}")
                lines.append(f"Claim: {cid}")
                lines.append(f"Status: {status}")
                if stage and stage != '—':
                    lines.append(f"Stage: {stage}")
                if filed:
                    lines.append(f"Filed: {filed}")

                return "Here are your claim details:\n\n• " + "\n• ".join(lines)

            # Default safe text when intent-specific format is missing
            return "I’ve retrieved your information successfully. How would you like me to proceed with these details?"
        except Exception:
            return "I’ve retrieved your information. How would you like me to proceed with these details?"

    def _set_pending_claim_choices(self, sid: str, choices: list) -> None:
        """Store pending claim choices for selection in the next user turn."""
        try:
            state = self._get_conversation_state(sid)
            state['pending_claim_choices'] = choices
            state['last_update_ts'] = time.time()
            if FRAPPE_AVAILABLE and frappe:
                key = f"assistant_crm:conv:{sid}"
                frappe.cache().set_value(key, state, expires_in_sec=30*60)
            else:
                self._conv_store[sid] = state
        except Exception:
            pass

    def _generate_ai_response(self, message: str, routing_result: Dict[str, Any], sid: Optional[str] = None) -> str:
        """
        Generate AI response using Gemini with live data and conversation context

        Args:
            message (str): User's message
            routing_result (Dict): Result from intent router
            sid (str): Session id used to fetch conversation/auth context

        Returns:
            str: AI-generated response
        """
        try:
            # Null-safe routing_result
            if not isinstance(routing_result, dict):
                try:
                    self._debug_log(f"route: ai-input sid={sid} routing_result_is_dict={isinstance(routing_result, dict)} null={routing_result is None}")
                except Exception:
                    pass
                routing_result = {} if routing_result is None else dict(routing_result) if hasattr(routing_result, 'get') else {}
            # Prepare context for AI
            context = {
                'user_message': message,
                'intent': routing_result.get('intent', 'unknown'),
                'confidence': routing_result.get('confidence', 0),
                'data_source': routing_result.get('source', 'unknown')
            }

            # Add live data if available
            if routing_result.get('source') == 'live_data' and routing_result.get('data'):
                _ld = routing_result.get('data')
                # Unwrap nested 'data' if present so Gemini sees raw structure
                if isinstance(_ld, dict) and 'type' not in _ld and isinstance(_ld.get('data'), dict):
                    _ld = _ld.get('data')
                context['live_data'] = _ld
                context['has_live_data'] = True
            else:
                context['has_live_data'] = False

            # Add conversation memory (last few turns) and auth context if available
            try:
                if sid:
                    conv = self._get_conversation_state(sid)
                    # Use a slightly longer window for richer context without overwhelming the model
                    history = conv.get('history', [])[-12:]
                    if history:
                        context['conversation_history'] = history
                if self.auth_service and sid:
                    auth_ctx = self.auth_service.get_auth_context(sid)
                    if auth_ctx:
                        context['auth_context'] = {
                            'in_progress': auth_ctx.get('in_progress'),
                            'step': auth_ctx.get('step'),
                            'intent': auth_ctx.get('intent'),
                            'collected_credentials': auth_ctx.get('collected_credentials'),
                            'authenticated': auth_ctx.get('authenticated')
                        }
                # Debug: log AI context essentials
                try:
                    self._debug_log(
                        f"AI: ctx has_live_data={context.get('has_live_data')} auth={(context.get('auth_context') or {}).get('authenticated')} intent={context.get('intent')}"
                    )
                except Exception:
                    pass

            except Exception:
                pass

            # Prefer post-auth, no-live-data deterministic message over generic AI fallback
            try:
                _authed = (context.get('auth_context') or {}).get('authenticated')
                if routing_result.get('intent') == 'claim_status' and _authed and not context.get('has_live_data'):
                    return ("I couldn’t retrieve your claim details with the provided information. "
                            "If you have a claim number, please share it, or I can escalate this to a human agent.")
            except Exception:
                pass

            # Generate AI response (Antoine/OpenAI first, Gemini as legacy fallback)
            ai_response = ""

            # Preferred path: Antoine via EnhancedAIService using Unified Inbox context
            if self.ai_service:
                try:
                    ai_response = self.ai_service.generate_unified_inbox_reply(
                        message=message,
                        context=context,
                    )
                    # Log engine usage when Antoine returns a non-empty response
                    if isinstance(ai_response, str) and ai_response.strip():
                        try:
                            cfg = getattr(self.ai_service, "config", {}) or {}
                            model_used = (cfg.get("chat_model") or "").strip() or cfg.get("openai_model")
                            self._debug_log(
                                f"AI: engine=Antoine model={model_used} intent={context.get('intent')} "
                                f"has_live_data={context.get('has_live_data')} len={len(ai_response or '')}"
                            )
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        self._debug_log(f"AI (Antoine) exception sid={sid} err={str(e)[:200]}")
                    except Exception:
                        pass
                    ai_response = ""

            # Backward-compatible Gemini fallback if Antoine is unavailable or misconfigured
            if (not ai_response or not isinstance(ai_response, str) or not ai_response.strip()) and self.gemini_service:
                try:
                    if hasattr(self.gemini_service, "generate_response_with_context"):
                        ai_response = self.gemini_service.generate_response_with_context(
                            message=message,
                            context=context,
                        )
                    else:
                        # Graceful fallback to generic path if context method is unavailable
                        ai_response = self.gemini_service.process_message(
                            message,
                            user_context=context,
                            chat_history=context.get('conversation_history') if isinstance(context, dict) else None,
                        ).get("response", "")
                    # Log engine usage when Gemini returns a non-empty response
                    if isinstance(ai_response, str) and ai_response.strip():
                        try:
                            self._debug_log(
                                f"AI: engine=Gemini intent={context.get('intent')} "
                                f"has_live_data={context.get('has_live_data')} len={len(ai_response or '')}"
                            )
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        self._debug_log(f"AI (Gemini) exception sid={sid} err={str(e)[:200]}")
                    except Exception:
                        pass
                    ai_response = ""

            if ai_response and isinstance(ai_response, str) and ai_response.strip():
                return ai_response.strip()

            # Post-auth aware fallback to avoid re-prompting for NRC
            if context.get('auth_context', {}).get('authenticated') and routing_result.get('intent') == 'claim_status':
                return ("I couldn’t retrieve your claim details with the provided information. "
                        "If you have a claim number, please share it, or I can escalate this to a human agent.")
            return self._get_fallback_response(routing_result.get('intent', 'unknown'))

        except Exception as e:
            try:
                self._debug_log(f"AI: exception sid={sid} err={str(e)[:200]}")
            except Exception:
                pass
            safe_log_error(f"AI response generation error: {str(e)}", "SimplifiedChat AI Error")
            return self._get_fallback_response('error')

    def _get_fallback_response(self, intent: str) -> str:
        """Get fallback response based on intent"""
        fallback_responses = {
            'greeting': "Hi! I'm Anna from WCFCB. How can I help you today? 😊",
            'goodbye': "Thank you for contacting WCFCB. Have a great day!",
            'claim_status': "I can help you check your claim status. Please provide your claim number or NRC.",
            'payment_status': "I can help you check your payment information. Please provide your NRC or reference number.",
            'pension_inquiry': "I can help you with pension inquiries. Please provide your NRC for personalized information.",
            'account_info': "I can help you with your account information. Please provide your NRC.",
            'agent_request': "I'll connect you with one of our agents. Please hold on.",
            'technical_help': "I'm here to help with technical issues. What specific problem are you experiencing?",
            'error': "I'm sorry, I'm having trouble processing your request. Please try again or contact our support team.",
            'unknown': "I'm Anna from WCFCB. I can help you with claims, payments, pensions, and more. What would you like to know?"
        }

        return fallback_responses.get(intent, fallback_responses['unknown'])

    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            'success': False,
            'error': error_message,
            'message': "I'm sorry, I'm having trouble processing your request. Please try again.",
            'response': "I'm sorry, I'm having trouble processing your request. Please try again.",
            'reply': "I'm sorry, I'm having trouble processing your request. Please try again.",
            'metadata': {
                'error': True,
                'error_message': error_message
            },
            'timestamp': now()
        }

# Global instance
_simplified_chat_api = None

def get_simplified_chat_api() -> SimplifiedChatAPI:
    """Get global simplified chat API instance"""
    global _simplified_chat_api
    if _simplified_chat_api is None:
        _simplified_chat_api = SimplifiedChatAPI()
    return _simplified_chat_api

# SINGLE API ENDPOINT - This replaces all other chat endpoints
if FRAPPE_AVAILABLE and frappe:
    @frappe.whitelist(allow_guest=True)
    def send_message(message=None, session_id=None, **kwargs):
        """
        SINGLE SIMPLIFIED CHAT ENDPOINT

        This is the ONLY chat endpoint needed. All other endpoints are redundant.

        Args:
            message (str): User's message
            session_id (str): Optional session id for authentication flows
            **kwargs: Ignored for simplicity

        Returns:
            Dict[str, Any]: AI response with metadata
        """
        try:
            # Get fields from form data if not provided
            if not message:
                message = frappe.form_dict.get('message')
            if not session_id:
                session_id = frappe.form_dict.get('session_id')
            if not session_id and getattr(frappe, 'session', None):
                try:
                    session_id = getattr(frappe.session, 'sid', None)
                except Exception:
                    session_id = None

            if not message:
                return {
                    'success': False,
                    'error': 'Message is required',
                    'message': 'Please provide a message.',
                    'timestamp': now()
                }

            # Process through simplified dataflow
            api = get_simplified_chat_api()
            return api.process_message(message, session_id=session_id)

        except Exception as e:
            safe_log_error(f"Simplified chat endpoint error: {str(e)}", "SimplifiedChat Endpoint")
            return {
                'success': False,
                'error': str(e),
                'message': "I'm sorry, I'm having trouble processing your request. Please try again.",
                'timestamp': now()
            }

    # Health check endpoint
    @frappe.whitelist(allow_guest=True)
    def get_chat_status():
        """Get simplified chat API status"""
        return {
            'success': True,
            'status': 'operational',
            'api_version': 'simplified_v1.0',
            'features': {
                'single_dataflow': True,
                'intent_detection': True,
                'live_data_integration': True,
                'ai_responses': True,
                'caching': True,
                'session_management': False,
                'authentication': False,
                'response_assembler': False
            },
            'timestamp': now()
        }

else:
    # Fallback functions for testing without frappe
    def send_message(message=None, **kwargs):
        """Fallback send_message for testing"""
        try:
            api = SimplifiedChatAPI()
            return api.process_message(message or "")
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': "Error processing message",
                'timestamp': now()
            }

    def get_chat_status():
        """Fallback get_chat_status for testing"""
        return {
            'success': True,
            'status': 'operational',
            'api_version': 'simplified_v1.0_fallback',
            'features': {
                'single_dataflow': True,
                'intent_detection': True,
                'live_data_integration': True,
                'ai_responses': True,
                'caching': True,
                'session_management': False,
                'authentication': False,
                'response_assembler': False
            },
            'timestamp': now()
        }
