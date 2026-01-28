import frappe
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import re
from openai import OpenAI
from textstat import flesch_reading_ease, flesch_kincaid_grade


class EnhancedAIService:
    """
    Enhanced AI Service for WCFCB Assistant CRM
    Phase B: Advanced tone/grammar adjustment and style optimization
    Compliance Target: 98/100 score
    """

    def __init__(self):
        self.config = self.get_ai_configuration()
        self.openai_client = self.initialize_openai_client()
        self.tone_profiles = self.load_tone_profiles()
        self.grammar_rules = self.load_grammar_rules()

    def get_ai_configuration(self) -> Dict[str, Any]:
        """Get AI service configuration from Enhanced AI Settings.

        We support two logical models sharing the same API key:
        - openai_model: primary model used for analytical/report-style Antoine flows
        - chat_model: optional model used for Anna / Unified Inbox chat. If not set,
          we fall back to openai_model.
        """
        try:
            settings = frappe.get_single("Enhanced AI Settings")
            # Use get_password to retrieve the decrypted OpenAI key from the Password field
            api_key = (settings.get_password("openai_api_key") or "").strip()
            return {
                "openai_api_key": api_key,
                "openai_model": settings.get("openai_model", "gpt-4"),
                "chat_model": (settings.get("chat_model") or ""),
                "tone_adjustment_enabled": settings.get("tone_adjustment_enabled", 1),
                "grammar_correction_enabled": settings.get("grammar_correction_enabled", 1),
                "style_optimization_enabled": settings.get("style_optimization_enabled", 1),
                "auto_translate_enabled": settings.get("auto_translate_enabled", 0),
                "readability_target": settings.get("readability_target", "professional"),
                "max_tokens": settings.get("max_tokens", 1000),
                "temperature": settings.get("temperature", 0.7),
            }
        except Exception:
            return {
                "openai_api_key": "",
                "openai_model": "gpt-4",
                "chat_model": "",
                "tone_adjustment_enabled": 1,
                "grammar_correction_enabled": 1,
                "style_optimization_enabled": 1,
                "auto_translate_enabled": 0,
                "readability_target": "professional",
                "max_tokens": 1000,
                "temperature": 0.7,
            }

    def initialize_openai_client(self):
        """Initialize OpenAI client using the new OpenAI Python SDK (>=1.0)."""
        try:
            api_key = (self.config.get("openai_api_key") or "").strip()
            # Debug log without exposing the full secret
            masked = f"***{api_key[-4:]}" if api_key else "None"
            frappe.log_error(
                f"Initializing OpenAI client (len={len(api_key)}, key={masked})",
                "Key Debug",
            )
            if api_key:
                return OpenAI(api_key=api_key)
            return None
        except Exception as e:
            frappe.log_error(f"Error initializing OpenAI client: {str(e)}")
            return None

    def load_tone_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined tone profiles for different communication contexts"""
        return {
            "professional": {
                "description": "Formal, respectful, and authoritative tone suitable for official communications",
                "characteristics": ["formal", "respectful", "clear", "authoritative"],
                "avoid": ["slang", "contractions", "casual expressions"],
                "example_phrases": [
                    "We appreciate your inquiry regarding...",
                    "Please be advised that...",
                    "We are pleased to inform you that..."
                ]
            },
            "friendly": {
                "description": "Warm, approachable, and helpful tone for customer service",
                "characteristics": ["warm", "approachable", "helpful", "empathetic"],
                "avoid": ["overly formal", "cold", "robotic"],
                "example_phrases": [
                    "Thanks for reaching out!",
                    "I'd be happy to help you with...",
                    "Let me see what I can do for you..."
                ]
            },
            "urgent": {
                "description": "Direct, clear, and action-oriented tone for urgent matters",
                "characteristics": ["direct", "clear", "action-oriented", "concise"],
                "avoid": ["lengthy explanations", "ambiguity"],
                "example_phrases": [
                    "Immediate action required:",
                    "Please respond by...",
                    "This requires your urgent attention..."
                ]
            },
            "empathetic": {
                "description": "Understanding, supportive, and compassionate tone for sensitive issues",
                "characteristics": ["understanding", "supportive", "compassionate", "patient"],
                "avoid": ["dismissive", "rushed", "impersonal"],
                "example_phrases": [
                    "I understand this must be frustrating...",
                    "We're here to support you through...",
                    "Your concerns are completely valid..."
                ]
            },
            "informative": {
                "description": "Educational, detailed, and explanatory tone for complex information",
                "characteristics": ["educational", "detailed", "clear", "structured"],
                "avoid": ["jargon", "assumptions", "oversimplification"],
                "example_phrases": [
                    "Let me explain how this works...",
                    "Here's what you need to know...",
                    "The process involves the following steps..."
                ]
            }
        }

    def load_grammar_rules(self) -> Dict[str, List[Dict[str, str]]]:
        """Load grammar correction rules specific to Zambian English and WCFCB context"""
        return {
            "common_errors": [
                {
                    "pattern": r"\bbeneficiarys\b",
                    "correction": "beneficiaries",
                    "explanation": "Plural of beneficiary"
                },
                {
                    "pattern": r"\bemployers\s+contribution\b",
                    "correction": "employer's contribution",
                    "explanation": "Possessive form required"
                },
                {
                    "pattern": r"\bpayment\s+are\b",
                    "correction": "payments are",
                    "explanation": "Subject-verb agreement"
                },
                {
                    "pattern": r"\bcompensation\s+fund\s+board\b",
                    "correction": "Compensation Fund Board",
                    "explanation": "Proper noun capitalization"
                }
            ],
            "wcfcb_terminology": [
                {
                    "pattern": r"\bworkers\s+comp\b",
                    "correction": "workers' compensation",
                    "explanation": "WCFCB preferred terminology"
                },
                {
                    "pattern": r"\bwork\s+injury\b",
                    "correction": "workplace injury",
                    "explanation": "Standard terminology"
                },
                {
                    "pattern": r"\bemployer\s+number\b",
                    "correction": "employer registration number",
                    "explanation": "Full terminology preferred"
                }
            ]
        }

    def enhance_message_quality(self, message_text: str, target_tone: str = "professional",
                              platform: str = "general", customer_context: Dict = None) -> Dict[str, Any]:
        """
        Enhance message quality with tone adjustment, grammar correction, and style optimization

        Args:
            message_text: Original message text
            target_tone: Desired tone (professional, friendly, urgent, empathetic, informative)
            platform: Target platform (email, sms, whatsapp, facebook, instagram, telegram, linkedin, twitter)
            customer_context: Customer information for personalization

        Returns:
            Dict containing enhanced message and analysis
        """
        try:
            if not self.config["tone_adjustment_enabled"]:
                return {
                    "success": True,
                    "original_message": message_text,
                    "enhanced_message": message_text,
                    "improvements": [],
                    "analysis": {"readability_score": 0, "tone_match": 100}
                }

            # Step 1: Grammar and spelling correction
            corrected_message = self.correct_grammar_and_spelling(message_text)

            # Step 2: Tone adjustment
            tone_adjusted_message = self.adjust_tone(corrected_message, target_tone, platform)

            # Step 3: Style optimization for platform
            optimized_message = self.optimize_for_platform(tone_adjusted_message, platform)

            # Step 4: Personalization based on customer context
            personalized_message = self.personalize_message(optimized_message, customer_context)

            # Step 5: Readability optimization
            final_message = self.optimize_readability(personalized_message, target_tone)

            # Step 6: Quality analysis
            analysis = self.analyze_message_quality(message_text, final_message, target_tone)

            # Step 7: Generate improvement suggestions
            improvements = self.generate_improvement_suggestions(message_text, final_message)

            return {
                "success": True,
                "original_message": message_text,
                "enhanced_message": final_message,
                "improvements": improvements,
                "analysis": analysis,
                "tone_profile": self.tone_profiles.get(target_tone, {}),
                "platform_optimizations": self.get_platform_optimizations(platform)
            }

        except Exception as e:
            frappe.log_error(f"Error enhancing message quality: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "original_message": message_text,
                "enhanced_message": message_text
            }

    def correct_grammar_and_spelling(self, text: str) -> str:
        """Correct grammar and spelling using AI and predefined rules"""
        try:
            if not self.config["grammar_correction_enabled"]:
                return text

            # Apply predefined grammar rules
            corrected_text = text

            # Apply common error corrections
            for rule in self.grammar_rules["common_errors"]:
                corrected_text = re.sub(rule["pattern"], rule["correction"], corrected_text, flags=re.IGNORECASE)

            # Apply WCFCB terminology corrections
            for rule in self.grammar_rules["wcfcb_terminology"]:
                corrected_text = re.sub(rule["pattern"], rule["correction"], corrected_text, flags=re.IGNORECASE)

            # Use AI for advanced grammar correction if OpenAI is available
            if self.openai_client:
                corrected_text = self.ai_grammar_correction(corrected_text)

            return corrected_text

        except Exception as e:
            frappe.log_error(f"Error in grammar correction: {str(e)}")
            return text

    def ai_grammar_correction(self, text: str) -> str:
        """Use AI for advanced grammar and spelling correction"""
        try:
            prompt = f"""
            Please correct any grammar, spelling, and punctuation errors in the following text while maintaining the original meaning and tone. Focus on:
            1. Subject-verb agreement
            2. Proper punctuation
            3. Spelling corrections
            4. Sentence structure improvements
            5. WCFCB-specific terminology accuracy

            Original text: "{text}"

            Return only the corrected text without explanations.
            """

            response = self.openai_client.chat.completions.create(
                model=self.config["openai_model"],
                messages=[
                    {"role": "system", "content": "You are a professional editor specializing in business communications for a workers' compensation fund."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=0.3  # Lower temperature for more consistent corrections
            )

            corrected_text = response.choices[0].message.content.strip()
            return corrected_text if corrected_text else text

        except Exception as e:
            frappe.log_error(f"Error in AI grammar correction: {str(e)}")
            return text

    def adjust_tone(self, text: str, target_tone: str, platform: str) -> str:
        """Adjust message tone to match target tone profile"""
        try:
            if target_tone not in self.tone_profiles:
                return text

            tone_profile = self.tone_profiles[target_tone]

            if self.openai_client:
                prompt = f"""
                Please adjust the tone of the following message to be {target_tone}.

                Tone characteristics to emphasize: {', '.join(tone_profile['characteristics'])}
                Avoid: {', '.join(tone_profile['avoid'])}
                Platform: {platform}

                Example phrases for this tone:
                {chr(10).join(f'- {phrase}' for phrase in tone_profile['example_phrases'])}

                Original message: "{text}"

                Return the message with adjusted tone while maintaining the core information and meaning.
                """

                response = self.openai_client.chat.completions.create(
                    model=self.config["openai_model"],
                    messages=[
                        {"role": "system", "content": f"You are a communication specialist for WCFCB, expert in adjusting tone for {platform} communications."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.config["max_tokens"],
                    temperature=self.config["temperature"]
                )

                adjusted_text = response.choices[0].message.content.strip()
                return adjusted_text if adjusted_text else text

            return text

        except Exception as e:
            frappe.log_error(f"Error adjusting tone: {str(e)}")
            return text

    def optimize_for_platform(self, text: str, platform: str) -> str:
        """Optimize message for specific platform requirements"""
        try:
            platform_rules = {
                "sms": {
                    "max_length": 160,
                    "avoid": ["links", "formatting"],
                    "prefer": ["abbreviations", "concise language"]
                },
                "whatsapp": {
                    "max_length": 4096,
                    "allow": ["emojis", "formatting"],
                    "prefer": ["conversational tone"]
                },
                "email": {
                    "max_length": None,
                    "require": ["subject line", "formal greeting", "signature"],
                    "prefer": ["structured format", "professional tone"]
                },
                "facebook": {
                    "max_length": 8000,
                    "allow": ["hashtags", "mentions"],
                    "prefer": ["engaging tone", "call-to-action"]
                },
                "instagram": {
                    "max_length": 2200,
                    "allow": ["hashtags", "emojis"],
                    "prefer": ["visual language", "engaging tone"]
                },
                "telegram": {
                    "max_length": 4096,
                    "allow": ["markdown", "links"],
                    "prefer": ["clear formatting"]
                },
                "linkedin": {
                    "max_length": 3000,
                    "prefer": ["professional tone", "industry terminology"],
                    "avoid": ["casual language", "excessive emojis"]
                },
                "twitter": {
                    "max_length": 280,
                    "allow": ["hashtags", "mentions"],
                    "prefer": ["concise language", "engaging tone"]
                }
            }

            rules = platform_rules.get(platform, {})
            max_length = rules.get("max_length")

            # Truncate if necessary
            if max_length and len(text) > max_length:
                text = text[:max_length-3] + "..."

            # Platform-specific optimizations using AI
            if self.openai_client and platform in platform_rules:
                optimized_text = self.ai_platform_optimization(text, platform, rules)
                return optimized_text

            return text

        except Exception as e:
            frappe.log_error(f"Error optimizing for platform: {str(e)}")
            return text

    def ai_platform_optimization(self, text: str, platform: str, rules: Dict) -> str:
        """Use AI to optimize message for specific platform"""
        try:
            prompt = f"""
            Optimize the following message for {platform} while maintaining the core information:

            Platform rules:
            - Max length: {rules.get('max_length', 'No limit')}
            - Allowed features: {', '.join(rules.get('allow', []))}
            - Preferred style: {', '.join(rules.get('prefer', []))}
            - Avoid: {', '.join(rules.get('avoid', []))}

            Original message: "{text}"

            Return the optimized message that follows {platform} best practices.
            """

            response = self.openai_client.chat.completions.create(
                model=self.config["openai_model"],
                messages=[
                    {"role": "system", "content": f"You are a social media specialist optimizing content for {platform}."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"]
            )

            optimized_text = response.choices[0].message.content.strip()
            return optimized_text if optimized_text else text

        except Exception as e:
            frappe.log_error(f"Error in AI platform optimization: {str(e)}")
            return text

    def personalize_message(self, text: str, customer_context: Dict = None) -> str:
        """Personalize message based on customer context"""
        try:
            if not customer_context:
                return text

            # Extract customer information
            customer_name = customer_context.get("customer_name", "")
            customer_type = customer_context.get("customer_type", "")
            previous_interactions = customer_context.get("previous_interactions", [])
            preferences = customer_context.get("preferences", {})

            # Simple personalization without AI
            personalized_text = text

            # Add customer name if available and not already present
            if customer_name and customer_name.lower() not in text.lower():
                if text.startswith("Dear") or text.startswith("Hello"):
                    personalized_text = text
                else:
                    personalized_text = f"Dear {customer_name},\n\n{text}"

            # Use AI for advanced personalization if available
            if self.openai_client and customer_context:
                personalized_text = self.ai_personalization(text, customer_context)

            return personalized_text

        except Exception as e:
            frappe.log_error(f"Error personalizing message: {str(e)}")
            return text

    def ai_personalization(self, text: str, customer_context: Dict) -> str:
        """Use AI for advanced message personalization"""
        try:
            context_summary = json.dumps(customer_context, indent=2)

            prompt = f"""
            Personalize the following message based on the customer context provided:

            Customer Context:
            {context_summary}

            Original message: "{text}"

            Guidelines:
            1. Use appropriate salutation with customer name if available
            2. Reference relevant previous interactions if applicable
            3. Adjust tone based on customer type (employer, beneficiary, etc.)
            4. Maintain professional WCFCB standards
            5. Keep the core message intact

            Return the personalized message.
            """

            response = self.openai_client.chat.completions.create(
                model=self.config["openai_model"],
                messages=[
                    {"role": "system", "content": "You are a customer service specialist for WCFCB, expert in personalizing communications."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"]
            )

            personalized_text = response.choices[0].message.content.strip()
            return personalized_text if personalized_text else text

        except Exception as e:
            frappe.log_error(f"Error in AI personalization: {str(e)}")
            return text

    def optimize_readability(self, text: str, target_tone: str) -> str:
        """Optimize message readability based on target audience"""
        try:
            if not self.config["style_optimization_enabled"]:
                return text

            # Calculate current readability scores
            try:
                flesch_score = flesch_reading_ease(text)
                grade_level = flesch_kincaid_grade(text)
            except:
                flesch_score = 50  # Default moderate score
                grade_level = 10   # Default grade level

            # Determine target readability based on tone and audience
            target_readability = self.get_target_readability(target_tone)

            # If readability is already good, return as is
            if target_readability["min_flesch"] <= flesch_score <= target_readability["max_flesch"]:
                return text

            # Use AI to improve readability if needed
            if self.openai_client:
                return self.ai_readability_optimization(text, target_readability, flesch_score, grade_level)

            return text

        except Exception as e:
            frappe.log_error(f"Error optimizing readability: {str(e)}")
            return text

    def get_target_readability(self, tone: str) -> Dict[str, float]:
        """Get target readability scores for different tones"""
        readability_targets = {
            "professional": {"min_flesch": 40, "max_flesch": 60, "max_grade": 12},
            "friendly": {"min_flesch": 60, "max_flesch": 80, "max_grade": 10},
            "urgent": {"min_flesch": 70, "max_flesch": 90, "max_grade": 8},
            "empathetic": {"min_flesch": 60, "max_flesch": 80, "max_grade": 10},
            "informative": {"min_flesch": 50, "max_flesch": 70, "max_grade": 11}
        }

        return readability_targets.get(tone, {"min_flesch": 50, "max_flesch": 70, "max_grade": 10})

    def ai_readability_optimization(self, text: str, target: Dict, current_flesch: float, current_grade: float) -> str:
        """Use AI to optimize readability"""
        try:
            prompt = f"""
            Improve the readability of the following text to meet these targets:

            Current readability:
            - Flesch Reading Ease: {current_flesch:.1f}
            - Grade Level: {current_grade:.1f}

            Target readability:
            - Flesch Reading Ease: {target['min_flesch']}-{target['max_flesch']}
            - Maximum Grade Level: {target['max_grade']}

            Guidelines for improvement:
            1. Use shorter sentences if grade level is too high
            2. Replace complex words with simpler alternatives
            3. Improve sentence structure for clarity
            4. Maintain professional tone and accuracy
            5. Keep all important information

            Original text: "{text}"

            Return the improved text with better readability.
            """

            response = self.openai_client.chat.completions.create(
                model=self.config["openai_model"],
                messages=[
                    {"role": "system", "content": "You are a writing specialist focused on improving readability while maintaining professional standards."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config["max_tokens"],
                temperature=0.5
            )

            optimized_text = response.choices[0].message.content.strip()
            return optimized_text if optimized_text else text

        except Exception as e:
            frappe.log_error(f"Error in AI readability optimization: {str(e)}")
            return text

    def analyze_message_quality(self, original: str, enhanced: str, target_tone: str) -> Dict[str, Any]:
        """Analyze message quality improvements"""
        try:
            analysis = {
                "readability_improvement": 0,
                "tone_match_score": 0,
                "length_change": 0,
                "complexity_reduction": 0,
                "professional_score": 0
            }

            # Calculate readability scores
            try:
                original_flesch = flesch_reading_ease(original)
                enhanced_flesch = flesch_reading_ease(enhanced)
                analysis["readability_improvement"] = enhanced_flesch - original_flesch

                original_grade = flesch_kincaid_grade(original)
                enhanced_grade = flesch_kincaid_grade(enhanced)
                analysis["complexity_reduction"] = original_grade - enhanced_grade
            except:
                pass

            # Calculate length change
            analysis["length_change"] = len(enhanced) - len(original)

            # Estimate tone match score (simplified)
            tone_keywords = self.get_tone_keywords(target_tone)
            tone_matches = sum(1 for keyword in tone_keywords if keyword.lower() in enhanced.lower())
            analysis["tone_match_score"] = min(100, (tone_matches / len(tone_keywords)) * 100)

            # Calculate professional score based on various factors
            analysis["professional_score"] = self.calculate_professional_score(enhanced)

            return analysis

        except Exception as e:
            frappe.log_error(f"Error analyzing message quality: {str(e)}")
            return {}

    def get_tone_keywords(self, tone: str) -> List[str]:
        """Get keywords associated with specific tones"""
        tone_keywords = {
            "professional": ["please", "kindly", "appreciate", "inform", "regarding", "sincerely"],
            "friendly": ["happy", "help", "thanks", "welcome", "glad", "pleasure"],
            "urgent": ["immediate", "urgent", "asap", "priority", "deadline", "action"],
            "empathetic": ["understand", "sorry", "support", "concern", "care", "assist"],
            "informative": ["explain", "details", "information", "process", "steps", "guide"]
        }

        return tone_keywords.get(tone, [])

    def calculate_professional_score(self, text: str) -> float:
        """Calculate professional communication score"""
        try:
            score = 100.0

            # Deduct points for unprofessional elements
            if re.search(r'\b(gonna|wanna|gotta)\b', text, re.IGNORECASE):
                score -= 10

            if re.search(r'[!]{2,}', text):  # Multiple exclamation marks
                score -= 5

            if re.search(r'[A-Z]{3,}', text):  # All caps words
                score -= 5

            if len(re.findall(r'[.!?]', text)) == 0:  # No proper punctuation
                score -= 10

            # Add points for professional elements
            if re.search(r'\b(please|thank you|sincerely|regards)\b', text, re.IGNORECASE):
                score += 5

            if re.search(r'^(Dear|Hello)', text):  # Proper greeting
                score += 5

            return max(0, min(100, score))

        except Exception:
            return 75.0  # Default score

    def generate_improvement_suggestions(self, original: str, enhanced: str) -> List[Dict[str, str]]:
        """Generate suggestions for message improvements"""
        try:
            suggestions = []

            # Length comparison
            if len(enhanced) < len(original):
                suggestions.append({
                    "type": "conciseness",
                    "description": f"Message shortened by {len(original) - len(enhanced)} characters for better clarity"
                })

            # Tone improvements
            if "please" in enhanced.lower() and "please" not in original.lower():
                suggestions.append({
                    "type": "politeness",
                    "description": "Added polite language to improve professional tone"
                })

            # Grammar improvements
            if enhanced != original:
                suggestions.append({
                    "type": "grammar",
                    "description": "Applied grammar and style corrections"
                })

            return suggestions

        except Exception as e:
            frappe.log_error(f"Error generating improvement suggestions: {str(e)}")
            return []

    def generate_claims_status_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Claims Status Report using OpenAI.

        Context is expected to contain:
        - window: {"from": date_from, "to": date_to}
        - current: high-level KPI counts for the current window
        - history: previous windows with the same fields
        - optionally status_breakdown: per-status counts for the lifecycle
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            # Serialize context so Antoine can see the exact numbers
            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- A reporting window
- Aggregated KPI counts for claims in this window
- A short history of previous windows
- Optional full lifecycle status breakdowns (Submitted, Under Review, Pending Documentation, Medical Review, Validated, Approved, Rejected, Closed, Appealed, Settled, Reopened, Escalated)

Your job is to answer the user's question about claims performance using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight 2–4 key insights: trends, spikes/drops, risk signals (rejections/escalations), and throughput (Validated/Approved vs Submitted).
- If history is present, comment on trend vs previous periods.
- If lifecycle breakdown is present, comment on any bottlenecks (for example many "Under Review" or "Pending Documentation" claims).
- Be specific and numeric where possible (for example "Validated increased from 120 to 145 (+21%)").
- Keep the answer concise: 3–6 bullet points plus a one-line summary.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                # Antoine / report model
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB claims analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."

        except Exception as e:
            # Log with key length for debugging configuration issues
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating claims status report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )

    def generate_unified_inbox_reply(self, message: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style conversational reply for Unified Inbox / direct social channels.

        The context is expected to mirror the structure built by SimplifiedChatAPI._generate_ai_response,
        including intent, confidence, data_source, live_data (if any), conversation_history, and
        auth_context.
        """
        try:
            if not self.openai_client:
                return (
                    "Our AI assistant is temporarily unavailable. "
                    "Please try again later or ask to speak with a human agent."
                )

            # Serialize context so Antoine can see the exact structure
            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, the AI engine behind WCFCB's Anna omnichannel assistant.

You receive:
- The latest user message from a beneficiary, employer, supplier, or staff member.
- A JSON context describing the detected intent, confidence, any live claim/beneficiary/employer data,
  authentication status, and a short conversation history.

Your job is to respond as *Anna* in a warm, professional Zambian-English tone.

GUIDELINES:
- If live_data is present, use it to answer precisely (for example, claim status or payment details).
- If authentication is incomplete for intents that require NRC or claim number, clearly but politely ask
  for the missing details without repeating yourself unnecessarily.
- Respect the user's intent; avoid changing topic unless they clearly ask to switch.
- Keep responses concise (2-3 short paragraphs or bullet lists).
- For sensitive topics (injury, death, complaints) be explicitly empathetic.
- If you are unsure, suggest escalating to a human agent rather than guessing.
- Use the JSON auth_context object when it is present:
    - If auth_context.authenticated is false for intents like "claim_status", "payment_status",
      "pension_inquiry", "account_info", "payment_history", or "employer_services", do NOT reveal
      any personal data yet.
    - Instead, ask clearly for the missing credentials before answering. For example:
        - claim_status: always request BOTH National ID (NRC, 9 digits, slashes allowed) AND Full Name.
        - payment_status or payment_history: request NRC and Account number.
        - pension_inquiry: request NRC and Beneficiary number.
        - employer_services: request NRC and Employer ID or Employer name, depending on context.
    - When auth_context.collected_credentials already contains some fields, acknowledge them and
      only ask for what is still missing, rather than asking for everything again.

JSON CONTEXT:
{context_json}

USER MESSAGE:
{message}
"""

            # Choose chat model (Anna) if configured, otherwise fall back to the
            # primary Antoine/report model for backwards compatibility.
            chat_model = (self.config.get("chat_model") or "").strip() or self.config.get("openai_model", "gpt-4")

            response = self.openai_client.chat.completions.create(
                model=chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, the AI engine behind WCFCB's Anna chatbot. "
                            "Respond as 'Anna' in a warm, professional tone, using only the provided context."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = (response.choices[0].message.content or "").strip()
            return text or (
                "I'm here to help, but I couldn't generate a detailed response. "
                "Please try again in a moment or ask to speak with a human agent."
            )

        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating unified inbox reply (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Unified Reply",
            )
            return (
                "Our AI assistant is temporarily unavailable. "
                "Please try again later or ask to speak with a human agent."
            )



    def generate_employer_status_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Employer Status Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: employer counts, compliance and contribution metrics, service case KPIs
        - history: list of previous Employer Status Reports with comparable fields
        - top_employers_by_claims: ranking of employers by claim volumes / amounts
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- A reporting window
- Aggregated employer KPIs (total employers, active, compliant vs non-compliant)
- Contribution metrics (expected, paid, outstanding, overdue)
- Service case metrics (cases logged, resolved, pending)
- A history of previous employer status reports
- Optionally a list of top employers by claims

Your job is to answer the user's question about employer performance, compliance, and contribution behaviour using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight 2-4 key insights: compliance levels, contribution risks (overdue/outstanding), employer engagement (active vs total) and service pressure (cases logged/pending).
- If history is present, comment on trend vs previous periods (improving, stable, deteriorating).
- Use the top employers by claims where available to call out specific employers that drive risk or volume.
- Be specific and numeric where possible (for example "Compliant employers increased from 420 to 455 (+8%) while overdue contributions fell by 16%").
- Keep the answer concise: 3-6 bullet points plus a one-line summary tailored for management.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                # Antoine / report model
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB employer analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."

        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating employer status report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Employer Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )

    def generate_inbox_status_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Inbox Status Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: inbox KPIs (conversations, messages, inbound/outbound split, escalated/resolved/open, AI usage, FRT/RT metrics)
        - history: list of previous Inbox Status Reports with comparable fields
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation
Fund Control Board (WCFCB) in Zambia.

You are given:
- A reporting window
- Aggregated inbox KPIs (conversations, messages, inbound vs outbound)
- Escalation and resolution metrics (escalated, resolved, open)
- AI usage metrics (AI first responses, AI-handled conversations)
- First-response-time and resolution-time statistics (average and P90)
- A short history of previous inbox status reports

Your job is to answer the user's question about inbox performance and service
pressure using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight 2-4 key insights: volume trends, channel mix, escalation/resolution
  risks, and impact of AI handling (e.g. faster responses).
- If history is present, comment on trend vs previous periods (improving,
  stable, deteriorating).
- Be specific and numeric where possible (for example "Average first response
  time improved from 18.5 to 12.3 minutes (-34%) while escalations dropped
  by 22%").
- Keep the answer concise: 3-6 bullet points plus a one-line summary tailored
  for operational management.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB inbox analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."

        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating inbox status report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Inbox Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )
    def generate_survey_feedback_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Survey Feedback Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: survey KPIs (campaigns, sent, responses, response rate, sentiment mix, interactions, FRT metrics)
        - history: list of previous Survey Feedback Reports with comparable fields
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation
Fund Control Board (WCFCB) in Zambia.

You are given:
- A reporting window
- Aggregated survey KPIs (number of campaigns, surveys sent, responses,
  response rate)
- Sentiment metrics (average sentiment and distribution across very positive
  to very negative)
- Channel/interactions metrics (inbound/outbound and total interactions)
- First-response-time metrics (average and high-percentile FRT)
- A short history of previous survey feedback reports

Your job is to answer the user's question about survey performance,
customer satisfaction, and channel effectiveness using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight 2-4 key insights: survey volume and response rates, sentiment mix
  (e.g. share of negative vs positive), any notable channel load, and FRT
  performance.
- If history is present, comment on trend vs previous periods (improving,
  stable, deteriorating) for response rate and sentiment.
- Be specific and numeric where possible (for example "Response rate improved
  from 32% to 41% (+9 p.p.) while the share of negative responses dropped
  from 21% to 14%").
- Keep the answer concise: 3-6 bullet points plus a one-line summary tailored
  for management.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB survey analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."

        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating survey feedback report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Survey Feedback Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )


    def generate_ai_automation_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for AI Automation Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: AI automation KPIs (total automations, after-hours, documents, data quality, failures, system health)
        - history: list of previous AI Automation Reports with comparable fields
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation
Fund Control Board (WCFCB) in Zambia.

You are given:
- A reporting window
- Aggregated AI automation KPIs (total automations, after-hours tickets and AI handling)
- Document validation metrics (total validations and failed/warning documents)
- Data quality metrics (issues and AI failures)
- System health metrics (score and status)
- A short history of previous AI Automation Reports

Your job is to answer the user's question about AI automation performance, reliability,
after-hours coverage, data quality, and system health using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight 2-4 key insights: automation volume and success, after-hours coverage,
  the relationship between data quality issues and AI failures, and any system health risks.
- If history is present, comment on trend vs previous periods (improving, stable, deteriorating).
- Be specific and numeric where possible (for example "AI failures dropped from 42 to 17 (-60%) while
  data quality issues fell by 25%").
- Keep the answer concise: 3-6 bullet points plus a one-line summary tailored for management.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB AI automation and data quality analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."

        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating AI automation report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine AI Automation Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )




    def generate_branch_performance_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Branch Performance Reports using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: KPIs for the current window including totals, SLA %, average
          resolution days, and per-branch rows with metrics
        - history: previous windows with comparable aggregated metrics
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- A reporting window (monthly or quarterly)
- Aggregated KPIs for branch performance in this window (claims, complaints, escalations, SLA %, resolution times)
- Per-branch rows with metrics
- A short history of previous windows at the same aggregation level

Your job is to answer the user's question about branch performance using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight 2	3 key insights: best / worst performing branches, SLA risks, complaint hotspots, and any resolution time issues.
- Use the per-branch rows where available to call out specific branches and regions.
- If history is present, compare current performance vs previous periods and call out improving or deteriorating trends.
- Be specific and numeric where possible (for example "Branch A's SLA is 72%, below the 75% threshold, with 15 complaints").
- Keep the answer concise: 3	6 bullet points plus a one-line summary tailored for senior management.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB branch performance analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."
        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating branch performance report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Branch Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )

    def generate_complaints_status_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Complaints Status Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: complaint KPIs for the current window (totals, categories,
          escalated/resolved/open counts)
        - platforms: per-channel complaint volumes
        - sample_rows: example rows with platform, category and escalation flags
        - history: previous windows with comparable aggregated metrics
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- A complaints reporting window (weekly or monthly)
- Aggregated KPIs: total complaints and counts by category (Claims, Compliance, General)
- Escalated, resolved and open complaint counts
- Per-platform complaint volumes (e.g. WhatsApp, Facebook, Telegram, Email, etc.)
- A sample of complaint rows with platform, final category and escalation status
- A short history of previous windows

Your job is to answer the user's question about complaints performance and risk using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight key insights: which categories and platforms are driving complaints, where escalations are concentrated,
  and whether resolution performance is improving or deteriorating.
- Call out any risk hotspots (for example, high escalations on a specific channel or category).
- Use history where present to compare current performance vs previous periods with numeric deltas where possible.
- Keep the answer concise: a few bullet points plus a one-line summary for Customer Service and Corporate Affairs.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB complaints analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."
        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating complaints status report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Complaints Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )

    def generate_sla_compliance_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for SLA Compliance Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: SLA KPIs for the current window (total items, within/breached,
          compliance %, FRT/RT metrics, escalations, AI first responses)
        - history: previous windows with comparable aggregated metrics
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- An SLA reporting window (typically monthly)
- Aggregated KPIs: total items, within/breached SLA counts, overall compliance %, first response time (FRT)
  and resolution time (RT) averages and percentiles, escalation behaviour, and AI first responses.
- A short history of previous windows.

Your job is to answer the user's question about SLA compliance performance and risk using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight key insights: overall compliance %, where SLA breaches are concentrated, and how FRT/RT are behaving.
- Comment on escalation patterns and the impact / utilisation of AI first responses where visible.
- Use history where present to compare current performance vs previous periods with numeric deltas where possible.
- Keep the answer concise: a few bullet points plus a one-line summary for Customer Service and Corporate Affairs.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB SLA compliance analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."
        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating SLA compliance report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine SLA Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )

    def generate_beneficiary_status_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Beneficiary Status Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "from": ..., "to": ...}
        - current: beneficiary counts for the current window (total, active,
          suspended, deceased, pending verification, terminated)
        - distributions: status/province/benefit-type charts or aggregates
        - history: previous windows with comparable aggregated metrics
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- A beneficiary reporting window (typically monthly)
- Aggregated counts of beneficiaries by status (Active, Suspended, Deceased, Pending Verification, Terminated)
- Distributions across provinces and benefit types
- A short history of previous windows with the same metrics

Your job is to answer the user's question about beneficiary portfolio health and risk using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight key insights: overall portfolio size, status mix (especially deceased and pending verification),
  and any noticeable concentration by province or benefit type.
- Use history where present to comment on trends (for example growth/shrinkage in active vs suspended or pending).
- Call out any risk or data-quality flags that management should be aware of.
- Keep the answer concise: a few bullet points plus a one-line summary for Management and Finance.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB beneficiary portfolio analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."
        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating beneficiary status report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Beneficiary Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )

    def generate_payout_summary_report_insights(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Antoine-style insights for Payout Summary Report using OpenAI.

        Context is expected to contain:
        - window: {"period_type": ..., "date_from": ..., "date_to": ..., "payroll_month": ...}
        - current: payout KPIs for the current window (beneficiaries paid, gross,
          deductions, net, exceptions_count)
        - sample_rows: example payout rows with beneficiary/employer/amounts
        - history: previous payout windows with comparable aggregated metrics
        """
        try:
            if not self.openai_client:
                return (
                    "AI insights are not available because OpenAI is not configured. "
                    "Please configure Enhanced AI Settings with a valid OpenAI API key."
                )

            context_json = json.dumps(context or {}, default=str, ensure_ascii=False)

            prompt = f"""
You are Antoine, a senior analytics specialist for the Workers' Compensation Fund Control Board (WCFCB) in Zambia.

You are given:
- A payout reporting window (monthly or custom)
- Aggregated metrics: total beneficiaries paid, gross payout, total deductions, net payout,
  and the count of beneficiaries with payout exceptions
- A sample of beneficiary payout rows (beneficiary, employer, net/gross amounts, deduction totals, exception codes)
- A short history of previous payout windows with the same metrics

Your job is to answer the user's question about payout performance, risks and trends using this data only.

REQUIREMENTS:
- First, briefly anchor your answer to the reporting window described in the JSON.
- Highlight key insights: payout volumes, deduction patterns, average payout per beneficiary,
  and where exceptions are concentrated.
- Use history where present to comment on trends (for example growth/shrinkage in total paid or exceptions).
- Call out any notable employer, benefit-type or exception patterns if visible from the sample rows.
- Keep the answer concise: a few bullet points plus a one-line summary for Management and Finance.

DATA (JSON):
{context_json}

USER QUESTION:
{query}
"""

            response = self.openai_client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Antoine, a WCFCB payout analytics specialist. "
                            "Respond with concise, numeric, executive-level insights based only on the provided JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=int(self.config.get("max_tokens", 800) or 800),
                temperature=float(self.config.get("temperature", 0.7) or 0.7),
            )

            text = response.choices[0].message.content.strip()
            return text or "No insights generated."
        except Exception as e:
            key = (self.config.get("openai_api_key") or "")
            key_len = len(key)
            frappe.log_error(
                f"Error generating payout summary report insights (key_len={key_len}): {str(e)}",
                "EnhancedAI Antoine Payout Insights",
            )
            return (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to verify the Antoine/OpenAI configuration in Enhanced AI Settings."
            )

    def get_platform_optimizations(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific optimization information"""
        optimizations = {
            "sms": {"character_limit": 160, "features": ["concise_language"]},
            "whatsapp": {"character_limit": 4096, "features": ["emojis", "formatting"]},
            "email": {"character_limit": None, "features": ["formal_structure", "signature"]},
            "facebook": {"character_limit": 8000, "features": ["hashtags", "engagement"]},
            "instagram": {"character_limit": 2200, "features": ["visual_language", "hashtags"]},
            "telegram": {"character_limit": 4096, "features": ["markdown", "links"]},
            "linkedin": {"character_limit": 3000, "features": ["professional_tone"]},
            "twitter": {"character_limit": 280, "features": ["hashtags", "conciseness"]}
        }

        return optimizations.get(platform, {"character_limit": None, "features": []})
