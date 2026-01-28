# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
from typing import Dict, List, Optional


class PersonaDetectionService:
    """
    Advanced persona detection service for WCFCB Assistant CRM chatbot.
    
    This service analyzes user context, conversation history, and query patterns
    to classify users into one of four personas:
    - Employer (Business Owner / HR Manager)
    - Beneficiary (Pensioner / Dependent) 
    - Supplier (Vendor / Service Provider)
    - WCFCB Staff (Internal Agent / Employee)
    
    Features:
    - Multi-factor persona classification
    - Confidence scoring with fallback mechanisms
    - Learning from conversation patterns
    - Role-based context enhancement
    """
    
    def __init__(self):
        """Initialize the persona detection service"""
        self.confidence_threshold = 0.7
        self.fallback_persona = "general"
        self.classification_rules = {}
        self.persona_keywords = {}
        self.load_classification_rules()
        self.load_persona_keywords()
    
    def load_classification_rules(self):
        """Load persona classification rules - uses defaults"""
        # Persona Classification Rule doctype has been deprecated - use default rules
        self._set_default_classification_rules()
    
    def load_persona_keywords(self):
        """Load persona-specific keywords for pattern matching - uses defaults"""
        # Persona Keyword doctype has been deprecated - use default keywords
        self._set_default_persona_keywords()
    
    def detect_persona(self, user_context: Dict, conversation_history: List = None, 
                      current_message: str = None) -> Dict:
        """
        Main persona detection method that analyzes multiple factors
        
        Args:
            user_context (Dict): User information and context
            conversation_history (List): Previous conversation turns
            current_message (str): Current user message
            
        Returns:
            Dict: Persona detection result with confidence score
        """
        try:
            # Initialize scoring for each persona
            persona_scores = {
                "employer": 0.0,
                "beneficiary": 0.0, 
                "supplier": 0.0,
                "wcfcb_staff": 0.0
            }
            
            # Factor 1: User role and profile analysis (40% weight)
            role_scores = self._analyze_user_roles(user_context)
            for persona, score in role_scores.items():
                persona_scores[persona] += score * 0.4
            
            # Factor 2: Conversation pattern analysis (30% weight)
            if conversation_history:
                pattern_scores = self._analyze_conversation_patterns(conversation_history)
                for persona, score in pattern_scores.items():
                    persona_scores[persona] += score * 0.3
            
            # Factor 3: Current message keyword analysis (20% weight)
            if current_message:
                keyword_scores = self._analyze_message_keywords(current_message)
                for persona, score in keyword_scores.items():
                    persona_scores[persona] += score * 0.2
            
            # Factor 4: Historical persona preference (10% weight)
            history_scores = self._get_historical_persona_preference(user_context)
            for persona, score in history_scores.items():
                persona_scores[persona] += score * 0.1
            
            # Determine best persona match
            best_persona = max(persona_scores, key=persona_scores.get)
            confidence = persona_scores[best_persona]
            
            # Apply confidence threshold and fallback logic
            if confidence < self.confidence_threshold:
                fallback_result = self._apply_fallback_logic(
                    persona_scores, user_context, current_message
                )
                if fallback_result:
                    best_persona = fallback_result["persona"]
                    confidence = fallback_result["confidence"]
            
            # Log persona detection for learning
            self._log_persona_detection(user_context, best_persona, confidence, persona_scores)
            
            return {
                "success": True,
                "persona": best_persona,
                "confidence": confidence,
                "all_scores": persona_scores,
                "factors_analyzed": {
                    "user_roles": bool(user_context),
                    "conversation_history": bool(conversation_history),
                    "message_keywords": bool(current_message),
                    "historical_preference": True
                },
                "timestamp": frappe.utils.now()
            }
            
        except Exception as e:
            frappe.log_error(f"Persona detection error: {str(e)}", "Persona Detection Service")
            return {
                "success": False,
                "error": str(e),
                "persona": self.fallback_persona,
                "confidence": 0.0,
                "timestamp": frappe.utils.now()
            }

    def _analyze_user_roles(self, user_context: Dict) -> Dict:
        """Analyze user roles and profile to determine persona likelihood"""
        scores = {"employer": 0.0, "beneficiary": 0.0, "supplier": 0.0, "wcfcb_staff": 0.0}

        if not user_context:
            return scores

        # Check user roles
        roles = user_context.get("roles", [])

        # WCFCB Staff indicators
        staff_roles = ["System Manager", "Assistant CRM Admin", "Assistant CRM User",
                      "HR Manager", "Employee", "Administrator"]
        if any(role in staff_roles for role in roles):
            scores["wcfcb_staff"] += 0.8

        # Check employee information
        employee_info = user_context.get("employee_info")
        if employee_info:
            scores["wcfcb_staff"] += 0.6
            # Check department for more specific classification
            department = employee_info.get("department", "").lower()
            if any(dept in department for dept in ["hr", "human", "admin", "management"]):
                scores["wcfcb_staff"] += 0.2

        # Check company information for employer indicators
        company = user_context.get("company")
        if company and company != "WCFCB":
            scores["employer"] += 0.5

        # Check email domain for organization type
        email = user_context.get("email", "")
        if email:
            domain = email.split("@")[-1].lower() if "@" in email else ""
            if "wcfcb" in domain or "gov" in domain:
                scores["wcfcb_staff"] += 0.4
            elif any(ext in domain for ext in [".com", ".org", ".biz"]):
                scores["employer"] += 0.3

        return scores

    def _analyze_conversation_patterns(self, conversation_history: List) -> Dict:
        """Analyze conversation patterns to identify persona characteristics"""
        scores = {"employer": 0.0, "beneficiary": 0.0, "supplier": 0.0, "wcfcb_staff": 0.0}

        if not conversation_history:
            return scores

        # Analyze recent conversation topics
        recent_messages = conversation_history[-10:]  # Last 10 messages
        all_text = " ".join([msg.get("message", "") for msg in recent_messages]).lower()

        # Employer conversation patterns
        employer_patterns = [
            "employee", "payroll", "contribution", "register", "business",
            "company", "staff", "workers", "monthly", "annual return"
        ]
        employer_matches = sum(1 for pattern in employer_patterns if pattern in all_text)
        scores["employer"] = min(employer_matches * 0.15, 1.0)

        # Beneficiary conversation patterns
        beneficiary_patterns = [
            "pension", "payment", "benefit", "claim", "life certificate",
            "medical", "disability", "dependent", "widow", "survivor"
        ]
        beneficiary_matches = sum(1 for pattern in beneficiary_patterns if pattern in all_text)
        scores["beneficiary"] = min(beneficiary_matches * 0.15, 1.0)

        # Supplier conversation patterns
        supplier_patterns = [
            "invoice", "payment", "procurement", "vendor", "supplier",
            "contract", "purchase", "delivery", "service", "goods"
        ]
        supplier_matches = sum(1 for pattern in supplier_patterns if pattern in all_text)
        scores["supplier"] = min(supplier_matches * 0.15, 1.0)

        # WCFCB Staff conversation patterns
        staff_patterns = [
            "system", "admin", "user", "help", "support", "internal",
            "process", "workflow", "policy", "procedure", "training"
        ]
        staff_matches = sum(1 for pattern in staff_patterns if pattern in all_text)
        scores["wcfcb_staff"] = min(staff_matches * 0.15, 1.0)

        return scores

    def _analyze_message_keywords(self, message: str) -> Dict:
        """Analyze current message keywords for persona indicators"""
        scores = {"employer": 0.0, "beneficiary": 0.0, "supplier": 0.0, "wcfcb_staff": 0.0}

        if not message:
            return scores

        message_lower = message.lower()

        # Use loaded persona keywords if available
        for persona, keywords in self.persona_keywords.items():
            total_weight = 0
            matched_weight = 0

            for kw_data in keywords:
                keyword = kw_data["keyword"].lower()
                weight = kw_data.get("weight", 1.0)
                total_weight += weight

                if keyword in message_lower:
                    matched_weight += weight

            if total_weight > 0:
                scores[persona] = matched_weight / total_weight

        # Fallback to default keyword analysis if no keywords loaded
        if not self.persona_keywords:
            scores = self._default_keyword_analysis(message_lower)

        return scores

    def _get_historical_persona_preference(self, user_context: Dict) -> Dict:
        """Get historical persona preference for this user"""
        # Persona Detection Log doctype has been deprecated - return empty scores
        return {"employer": 0.0, "beneficiary": 0.0, "supplier": 0.0, "wcfcb_staff": 0.0}

    def _apply_fallback_logic(self, persona_scores: Dict, user_context: Dict,
                             current_message: str) -> Optional[Dict]:
        """Apply fallback logic when confidence is below threshold"""

        # Sort personas by score
        sorted_personas = sorted(persona_scores.items(), key=lambda x: x[1], reverse=True)

        # If top two scores are close, use additional heuristics
        if len(sorted_personas) >= 2:
            top_persona, top_score = sorted_personas[0]
            second_persona, second_score = sorted_personas[1]

            # If scores are very close (within 0.1), use heuristics
            if abs(top_score - second_score) < 0.1:
                heuristic_result = self._apply_heuristic_classification(
                    user_context, current_message
                )
                if heuristic_result:
                    return heuristic_result

        # If still no clear winner, use default persona based on context
        if user_context.get("user") == "Guest":
            return {"persona": "beneficiary", "confidence": 0.6}  # Most common public user

        return None

    def _apply_heuristic_classification(self, user_context: Dict,
                                      current_message: str) -> Optional[Dict]:
        """Apply simple heuristic rules for edge cases"""

        # Check for obvious staff indicators
        if user_context.get("user") != "Guest":
            roles = user_context.get("roles", [])
            if any("Manager" in role or "Admin" in role for role in roles):
                return {"persona": "wcfcb_staff", "confidence": 0.65}

        # Check message for urgent/specific indicators
        if current_message:
            message_lower = current_message.lower()

            # Strong employer indicators
            if any(word in message_lower for word in ["register business", "add employee", "payroll"]):
                return {"persona": "employer", "confidence": 0.65}

            # Strong beneficiary indicators
            if any(word in message_lower for word in ["my pension", "life certificate", "payment status"]):
                return {"persona": "beneficiary", "confidence": 0.65}

            # Strong supplier indicators
            if any(word in message_lower for word in ["invoice payment", "procurement", "vendor"]):
                return {"persona": "supplier", "confidence": 0.65}

        return None

    def _default_keyword_analysis(self, message_lower: str) -> Dict:
        """Default keyword analysis when database keywords are not available"""
        scores = {"employer": 0.0, "beneficiary": 0.0, "supplier": 0.0, "wcfcb_staff": 0.0}

        # Employer keywords
        employer_keywords = ["business", "company", "employee", "payroll", "contribution",
                           "register", "employer", "staff", "workers", "monthly return"]
        employer_matches = sum(1 for kw in employer_keywords if kw in message_lower)
        scores["employer"] = min(employer_matches * 0.1, 1.0)

        # Beneficiary keywords
        beneficiary_keywords = ["pension", "benefit", "payment", "claim", "life certificate",
                              "medical", "disability", "widow", "survivor", "dependent"]
        beneficiary_matches = sum(1 for kw in beneficiary_keywords if kw in message_lower)
        scores["beneficiary"] = min(beneficiary_matches * 0.1, 1.0)

        # Supplier keywords
        supplier_keywords = ["invoice", "payment", "vendor", "supplier", "procurement",
                           "contract", "delivery", "goods", "services", "purchase"]
        supplier_matches = sum(1 for kw in supplier_keywords if kw in message_lower)
        scores["supplier"] = min(supplier_matches * 0.1, 1.0)

        # Staff keywords
        staff_keywords = ["system", "admin", "help", "support", "internal", "policy",
                        "procedure", "workflow", "training", "user management"]
        staff_matches = sum(1 for kw in staff_keywords if kw in message_lower)
        scores["wcfcb_staff"] = min(staff_matches * 0.1, 1.0)

        return scores

    def _log_persona_detection(self, user_context: Dict, detected_persona: str,
                              confidence: float, all_scores: Dict):
        """Log persona detection for learning and analytics - deprecated"""
        # Persona Detection Log doctype has been deprecated - skip logging
        pass

    def _set_default_classification_rules(self):
        """Set default classification rules when database is not available"""
        self.classification_rules = {
            "employer": [
                {"rule_type": "role", "rule_condition": "contains:Manager", "weight": 0.8},
                {"rule_type": "email", "rule_condition": "domain:company", "weight": 0.6}
            ],
            "beneficiary": [
                {"rule_type": "user", "rule_condition": "equals:Guest", "weight": 0.7},
                {"rule_type": "role", "rule_condition": "contains:Customer", "weight": 0.5}
            ],
            "supplier": [
                {"rule_type": "role", "rule_condition": "contains:Supplier", "weight": 0.9},
                {"rule_type": "email", "rule_condition": "domain:vendor", "weight": 0.6}
            ],
            "wcfcb_staff": [
                {"rule_type": "role", "rule_condition": "contains:Admin", "weight": 0.9},
                {"rule_type": "employee", "rule_condition": "exists", "weight": 0.8}
            ]
        }

    def _set_default_persona_keywords(self):
        """Set default persona keywords when database is not available"""
        self.persona_keywords = {
            "employer": [
                {"keyword": "business registration", "weight": 1.0, "category": "process"},
                {"keyword": "employee contribution", "weight": 0.9, "category": "payment"},
                {"keyword": "payroll", "weight": 0.8, "category": "process"},
                {"keyword": "monthly return", "weight": 0.8, "category": "compliance"}
            ],
            "beneficiary": [
                {"keyword": "pension payment", "weight": 1.0, "category": "payment"},
                {"keyword": "life certificate", "weight": 0.9, "category": "document"},
                {"keyword": "medical claim", "weight": 0.8, "category": "claim"},
                {"keyword": "disability benefit", "weight": 0.8, "category": "benefit"}
            ],
            "supplier": [
                {"keyword": "invoice payment", "weight": 1.0, "category": "payment"},
                {"keyword": "procurement", "weight": 0.9, "category": "process"},
                {"keyword": "vendor registration", "weight": 0.8, "category": "registration"},
                {"keyword": "contract", "weight": 0.7, "category": "legal"}
            ],
            "wcfcb_staff": [
                {"keyword": "system administration", "weight": 1.0, "category": "admin"},
                {"keyword": "user management", "weight": 0.9, "category": "admin"},
                {"keyword": "policy", "weight": 0.8, "category": "governance"},
                {"keyword": "internal process", "weight": 0.7, "category": "process"}
            ]
        }

    def get_persona_characteristics(self, persona: str) -> Dict:
        """Get characteristics and preferences for a specific persona"""
        characteristics = {
            "employer": {
                "primary_concerns": ["compliance", "cost_efficiency", "process_simplicity"],
                "preferred_communication": "formal",
                "typical_queries": ["registration", "contributions", "reporting"],
                "urgency_level": "medium",
                "information_depth": "detailed"
            },
            "beneficiary": {
                "primary_concerns": ["payment_status", "benefit_access", "documentation"],
                "preferred_communication": "supportive",
                "typical_queries": ["payments", "claims", "certificates"],
                "urgency_level": "high",
                "information_depth": "simple"
            },
            "supplier": {
                "primary_concerns": ["payment_timing", "contract_status", "requirements"],
                "preferred_communication": "business_formal",
                "typical_queries": ["payments", "procurement", "contracts"],
                "urgency_level": "medium",
                "information_depth": "specific"
            },
            "wcfcb_staff": {
                "primary_concerns": ["efficiency", "accuracy", "policy_compliance"],
                "preferred_communication": "technical",
                "typical_queries": ["procedures", "systems", "policies"],
                "urgency_level": "variable",
                "information_depth": "comprehensive"
            }
        }

        return characteristics.get(persona, characteristics["beneficiary"])  # Default fallback
