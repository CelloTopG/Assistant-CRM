# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import hashlib
import secrets
import time
import json
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

def safe_log_error(message: str, title: str = "Enhanced Security Service"):
    """Safe error logging function"""
    try:
        if frappe:
            frappe.log_error(message, title)
        else:
            print(f"[{title}] {message}")
    except:
        print(f"[{title}] {message}")

class EnhancedSecurityService:
    """
    Phase 2: Enhanced Security Validation Service
    
    Provides advanced security features including:
    - Multi-factor authentication (MFA)
    - Advanced verification mechanisms
    - Comprehensive audit logging
    - Risk-based authentication
    - Session security monitoring
    - Fraud detection
    """
    
    def __init__(self):
        self.mfa_methods = {
            'sms': {'enabled': True, 'timeout': 300},  # 5 minutes
            'email': {'enabled': True, 'timeout': 600},  # 10 minutes
            'security_questions': {'enabled': True, 'timeout': 300},
            'biometric': {'enabled': False, 'timeout': 60}  # Future implementation
        }
        
        self.security_levels = {
            'basic': {'score': 1, 'requirements': ['password']},
            'standard': {'score': 2, 'requirements': ['password', 'reference_verification']},
            'enhanced': {'score': 3, 'requirements': ['password', 'reference_verification', 'mfa']},
            'maximum': {'score': 4, 'requirements': ['password', 'reference_verification', 'mfa', 'biometric']}
        }
        
        self.risk_factors = {
            'new_device': 2,
            'unusual_location': 3,
            'multiple_failed_attempts': 4,
            'suspicious_patterns': 5,
            'high_value_transaction': 3
        }
        
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30
        self.session_monitoring_enabled = True

    def initiate_mfa_challenge(self, user_id: str, user_profile: Dict[str, Any], 
                              preferred_method: str = 'sms') -> Dict[str, Any]:
        """
        Initiate multi-factor authentication challenge.
        
        Args:
            user_id (str): User identifier
            user_profile (dict): User profile information
            preferred_method (str): Preferred MFA method
        
        Returns:
            Dict containing MFA challenge details
        """
        try:
            # Check if MFA is required for this user
            if not self._is_mfa_required(user_profile):
                return {
                    'success': True,
                    'mfa_required': False,
                    'message': 'MFA not required for this authentication level.'
                }
            
            # Validate MFA method
            if preferred_method not in self.mfa_methods or not self.mfa_methods[preferred_method]['enabled']:
                preferred_method = 'sms'  # Default fallback
            
            # Generate MFA challenge
            challenge_data = self._generate_mfa_challenge(user_id, user_profile, preferred_method)
            
            if challenge_data['success']:
                # Log MFA initiation
                self._log_security_event(user_id, 'mfa_initiated', {
                    'method': preferred_method,
                    'challenge_id': challenge_data['challenge_id']
                })
                
                return {
                    'success': True,
                    'mfa_required': True,
                    'challenge_id': challenge_data['challenge_id'],
                    'method': preferred_method,
                    'message': challenge_data['message'],
                    'expires_at': challenge_data['expires_at']
                }
            else:
                return {
                    'success': False,
                    'error': 'mfa_generation_failed',
                    'message': 'Unable to generate MFA challenge. Please try again.'
                }
                
        except Exception as e:
            safe_log_error(f"MFA initiation error for user {user_id}: {str(e)}")
            return {
                'success': False,
                'error': 'mfa_system_error',
                'message': 'MFA system temporarily unavailable.'
            }

    def verify_mfa_response(self, challenge_id: str, user_response: str, user_id: str) -> Dict[str, Any]:
        """
        Verify MFA response from user.
        
        Args:
            challenge_id (str): MFA challenge identifier
            user_response (str): User's MFA response
            user_id (str): User identifier
        
        Returns:
            Dict containing verification result
        """
        try:
            # Retrieve challenge data
            challenge_data = self._get_mfa_challenge(challenge_id)
            
            if not challenge_data:
                return {
                    'success': False,
                    'error': 'invalid_challenge',
                    'message': 'Invalid or expired MFA challenge.'
                }
            
            # Check expiration
            if self._is_challenge_expired(challenge_data):
                self._cleanup_mfa_challenge(challenge_id)
                return {
                    'success': False,
                    'error': 'challenge_expired',
                    'message': 'MFA challenge has expired. Please request a new one.'
                }
            
            # Verify response
            verification_result = self._verify_mfa_code(challenge_data, user_response)
            
            if verification_result['success']:
                # MFA successful
                self._cleanup_mfa_challenge(challenge_id)
                self._log_security_event(user_id, 'mfa_success', {
                    'challenge_id': challenge_id,
                    'method': challenge_data['method']
                })
                
                return {
                    'success': True,
                    'message': 'MFA verification successful.',
                    'security_level': 'enhanced'
                }
            else:
                # MFA failed
                self._increment_failed_attempts(challenge_id)
                self._log_security_event(user_id, 'mfa_failed', {
                    'challenge_id': challenge_id,
                    'method': challenge_data['method'],
                    'reason': verification_result.get('reason', 'invalid_code')
                })
                
                return {
                    'success': False,
                    'error': 'verification_failed',
                    'message': 'Invalid verification code. Please try again.',
                    'attempts_remaining': self._get_remaining_attempts(challenge_id)
                }
                
        except Exception as e:
            safe_log_error(f"MFA verification error: {str(e)}")
            return {
                'success': False,
                'error': 'verification_system_error',
                'message': 'Verification system temporarily unavailable.'
            }

    def assess_authentication_risk(self, user_id: str, request_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess authentication risk based on various factors.
        
        Args:
            user_id (str): User identifier
            request_context (dict): Request context (IP, device, etc.)
        
        Returns:
            Dict containing risk assessment
        """
        try:
            risk_score = 0
            risk_factors_detected = []
            
            # Check for new device
            if self._is_new_device(user_id, request_context):
                risk_score += self.risk_factors['new_device']
                risk_factors_detected.append('new_device')
            
            # Check for unusual location
            if self._is_unusual_location(user_id, request_context):
                risk_score += self.risk_factors['unusual_location']
                risk_factors_detected.append('unusual_location')
            
            # Check for multiple failed attempts
            if self._has_multiple_failed_attempts(user_id):
                risk_score += self.risk_factors['multiple_failed_attempts']
                risk_factors_detected.append('multiple_failed_attempts')
            
            # Check for suspicious patterns
            if self._detect_suspicious_patterns(user_id, request_context):
                risk_score += self.risk_factors['suspicious_patterns']
                risk_factors_detected.append('suspicious_patterns')
            
            # Determine risk level
            if risk_score >= 8:
                risk_level = 'high'
                recommended_action = 'require_enhanced_verification'
            elif risk_score >= 5:
                risk_level = 'medium'
                recommended_action = 'require_mfa'
            elif risk_score >= 2:
                risk_level = 'low'
                recommended_action = 'standard_verification'
            else:
                risk_level = 'minimal'
                recommended_action = 'proceed'
            
            # Log risk assessment
            self._log_security_event(user_id, 'risk_assessment', {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'factors': risk_factors_detected,
                'recommended_action': recommended_action
            })
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_factors': risk_factors_detected,
                'recommended_action': recommended_action,
                'requires_mfa': risk_score >= 5,
                'requires_enhanced_verification': risk_score >= 8
            }
            
        except Exception as e:
            safe_log_error(f"Risk assessment error for user {user_id}: {str(e)}")
            return {
                'risk_score': 10,  # High risk on error
                'risk_level': 'high',
                'risk_factors': ['system_error'],
                'recommended_action': 'require_enhanced_verification',
                'requires_mfa': True,
                'requires_enhanced_verification': True
            }

    def _generate_mfa_challenge(self, user_id: str, user_profile: Dict[str, Any], method: str) -> Dict[str, Any]:
        """Generate MFA challenge based on method."""
        
        challenge_id = self._generate_challenge_id()
        
        if method == 'sms':
            return self._generate_sms_challenge(challenge_id, user_id, user_profile)
        elif method == 'email':
            return self._generate_email_challenge(challenge_id, user_id, user_profile)
        elif method == 'security_questions':
            return self._generate_security_question_challenge(challenge_id, user_id, user_profile)
        else:
            return {'success': False, 'error': 'unsupported_method'}

    def _generate_sms_challenge(self, challenge_id: str, user_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SMS-based MFA challenge."""
        
        # Generate 6-digit code
        verification_code = f"{secrets.randbelow(900000) + 100000:06d}"
        
        # Get phone number (masked for display)
        phone = user_profile.get('phone', '+260-97-XXXXXXX')
        masked_phone = phone[:8] + 'XXX' + phone[-3:] if len(phone) > 10 else 'XXX-XXX-XXXX'
        
        # Store challenge data
        challenge_data = {
            'challenge_id': challenge_id,
            'user_id': user_id,
            'method': 'sms',
            'code': verification_code,
            'phone': phone,
            'created_at': now(),
            'expires_at': add_to_date(datetime.now(), minutes=5).isoformat(),
            'attempts': 0
        }
        
        self._store_mfa_challenge(challenge_id, challenge_data)
        
        # In production: Send actual SMS
        # For development: Log the code
        safe_log_error(f"SMS MFA code for {user_id}: {verification_code}", "MFA Development")
        
        return {
            'success': True,
            'challenge_id': challenge_id,
            'message': f"I've sent a 6-digit verification code to your phone number ending in {masked_phone[-4:]}. Please enter the code to complete your authentication.",
            'expires_at': challenge_data['expires_at']
        }

    def _generate_email_challenge(self, challenge_id: str, user_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate email-based MFA challenge."""
        
        # Generate 8-character alphanumeric code
        verification_code = secrets.token_urlsafe(6)[:8].upper()
        
        # Get email (masked for display)
        email = user_profile.get('email', 'user@example.com')
        masked_email = email[:3] + '***@' + email.split('@')[1] if '@' in email else 'user***@example.com'
        
        # Store challenge data
        challenge_data = {
            'challenge_id': challenge_id,
            'user_id': user_id,
            'method': 'email',
            'code': verification_code,
            'email': email,
            'created_at': now(),
            'expires_at': add_to_date(datetime.now(), minutes=10).isoformat(),
            'attempts': 0
        }
        
        self._store_mfa_challenge(challenge_id, challenge_data)
        
        # In production: Send actual email
        # For development: Log the code
        safe_log_error(f"Email MFA code for {user_id}: {verification_code}", "MFA Development")
        
        return {
            'success': True,
            'challenge_id': challenge_id,
            'message': f"I've sent a verification code to your email address {masked_email}. Please check your email and enter the code to complete your authentication.",
            'expires_at': challenge_data['expires_at']
        }

    def _generate_security_question_challenge(self, challenge_id: str, user_id: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate security question-based MFA challenge."""
        
        # Predefined security questions for development
        security_questions = [
            "What was the name of your first employer?",
            "In which city were you born?",
            "What is your mother's maiden name?",
            "What was the name of your first school?"
        ]
        
        # Select a random question
        question = secrets.choice(security_questions)
        
        # For development: Use a simple answer pattern
        expected_answer = f"answer_{user_id[-3:]}"
        
        challenge_data = {
            'challenge_id': challenge_id,
            'user_id': user_id,
            'method': 'security_questions',
            'question': question,
            'expected_answer': expected_answer.lower(),
            'created_at': now(),
            'expires_at': add_to_date(datetime.now(), minutes=5).isoformat(),
            'attempts': 0
        }
        
        self._store_mfa_challenge(challenge_id, challenge_data)
        
        # For development: Log the expected answer
        safe_log_error(f"Security question answer for {user_id}: {expected_answer}", "MFA Development")
        
        return {
            'success': True,
            'challenge_id': challenge_id,
            'message': f"Please answer this security question to verify your identity:\n\n**{question}**",
            'expires_at': challenge_data['expires_at']
        }

    def _verify_mfa_code(self, challenge_data: Dict[str, Any], user_response: str) -> Dict[str, Any]:
        """Verify MFA code based on challenge method."""
        
        method = challenge_data['method']
        
        if method in ['sms', 'email']:
            expected_code = challenge_data['code']
            return {
                'success': user_response.strip() == expected_code,
                'reason': 'invalid_code' if user_response.strip() != expected_code else None
            }
        elif method == 'security_questions':
            expected_answer = challenge_data['expected_answer']
            user_answer = user_response.strip().lower()
            return {
                'success': user_answer == expected_answer,
                'reason': 'incorrect_answer' if user_answer != expected_answer else None
            }
        else:
            return {'success': False, 'reason': 'unsupported_method'}

    def _is_mfa_required(self, user_profile: Dict[str, Any]) -> bool:
        """Determine if MFA is required for this user."""
        
        # MFA required for high-value accounts or sensitive roles
        user_role = user_profile.get('user_role', 'beneficiary')
        verification_level = user_profile.get('verification_level', 'basic')
        
        return (user_role in ['wcfcb_staff', 'employer'] or 
                verification_level in ['full', 'business_verified', 'staff_verified'])

    def _generate_challenge_id(self) -> str:
        """Generate unique challenge ID."""
        import uuid
        return f"mfa_{int(time.time())}_{str(uuid.uuid4())[:8]}"

    def _store_mfa_challenge(self, challenge_id: str, challenge_data: Dict[str, Any]):
        """Store MFA challenge data securely."""
        if not hasattr(self, '_mfa_challenges'):
            self._mfa_challenges = {}
        self._mfa_challenges[challenge_id] = challenge_data

    def _get_mfa_challenge(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve MFA challenge data."""
        if not hasattr(self, '_mfa_challenges'):
            return None
        return self._mfa_challenges.get(challenge_id)

    def _is_challenge_expired(self, challenge_data: Dict[str, Any]) -> bool:
        """Check if MFA challenge has expired."""
        expires_at = datetime.fromisoformat(challenge_data['expires_at'])
        return datetime.now() > expires_at

    def _cleanup_mfa_challenge(self, challenge_id: str):
        """Clean up MFA challenge data."""
        if hasattr(self, '_mfa_challenges') and challenge_id in self._mfa_challenges:
            del self._mfa_challenges[challenge_id]

    def _increment_failed_attempts(self, challenge_id: str):
        """Increment failed attempts for MFA challenge."""
        if hasattr(self, '_mfa_challenges') and challenge_id in self._mfa_challenges:
            self._mfa_challenges[challenge_id]['attempts'] += 1

    def _get_remaining_attempts(self, challenge_id: str) -> int:
        """Get remaining MFA attempts."""
        if hasattr(self, '_mfa_challenges') and challenge_id in self._mfa_challenges:
            attempts = self._mfa_challenges[challenge_id]['attempts']
            return max(0, 3 - attempts)
        return 0

    def _is_new_device(self, user_id: str, request_context: Dict[str, Any]) -> bool:
        """Check if this is a new device for the user."""
        # Simplified implementation for development
        return request_context.get('device_fingerprint') not in ['known_device_1', 'known_device_2']

    def _is_unusual_location(self, user_id: str, request_context: Dict[str, Any]) -> bool:
        """Check if this is an unusual location for the user."""
        # Simplified implementation for development
        ip_address = request_context.get('ip_address', '')
        return not ip_address.startswith(('192.168.', '10.', '172.'))

    def _has_multiple_failed_attempts(self, user_id: str) -> bool:
        """Check if user has multiple recent failed attempts."""
        # Simplified implementation for development
        return False  # Would check authentication logs in production

    def _detect_suspicious_patterns(self, user_id: str, request_context: Dict[str, Any]) -> bool:
        """Detect suspicious authentication patterns."""
        # Simplified implementation for development
        return False  # Would analyze patterns in production

    def _log_security_event(self, user_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log security events for audit trail."""
        try:
            log_entry = {
                'timestamp': now(),
                'user_id_hash': hashlib.sha256(user_id.encode()).hexdigest()[:16],
                'event_type': event_type,
                'event_data': event_data
            }
            safe_log_error(f"Security event: {json.dumps(log_entry)}", "Security Audit")
        except Exception as e:
            safe_log_error(f"Failed to log security event: {str(e)}")
