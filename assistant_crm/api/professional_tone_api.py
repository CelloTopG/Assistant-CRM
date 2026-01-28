#!/usr/bin/env python3
"""
WCFCB Professional Tone Keywords API
Comprehensive professional tone keyword database with context-aware suggestions
"""

import frappe
from frappe import _
import json
import re
from datetime import datetime

class ProfessionalToneManager:
    """
    Manages professional tone keywords and context-aware suggestions for WCFCB communications.
    """
    
    def __init__(self):
        self.professional_keywords = {
            # Formal Greetings and Openings
            "greetings": [
                "Good morning", "Good afternoon", "Good evening", "Dear valued client",
                "Thank you for contacting", "We appreciate your inquiry", "I hope this message finds you well",
                "Thank you for reaching out", "We are pleased to assist", "It is our pleasure to help",
                "We acknowledge receipt of", "Thank you for your patience", "We value your business",
                "We are committed to helping", "Your inquiry is important to us", "We understand your concern"
            ],
            
            # Professional Acknowledgments
            "acknowledgments": [
                "We acknowledge", "We have received", "We understand", "We recognize",
                "We appreciate", "We are aware", "We confirm", "We validate",
                "We take note of", "We have reviewed", "We comprehend", "We realize",
                "We are mindful of", "We accept", "We concur", "We agree"
            ],
            
            # Empathetic Responses
            "empathy": [
                "We understand your concern", "We appreciate your situation", "We recognize the importance",
                "We are sensitive to", "We empathize with", "We acknowledge the difficulty",
                "We are aware of the challenges", "We understand this may be frustrating",
                "We recognize your urgency", "We appreciate your patience", "We understand your needs",
                "We are committed to resolving", "We take your concerns seriously", "We value your feedback",
                "We understand the impact", "We recognize the significance"
            ],
            
            # Professional Explanations
            "explanations": [
                "Please allow me to explain", "I would like to clarify", "Let me provide details",
                "To elaborate further", "For your information", "As per our policy",
                "According to regulations", "In accordance with", "Based on our assessment",
                "Following our review", "Upon careful consideration", "After thorough evaluation",
                "In compliance with", "As outlined in", "Per our procedures", "In line with standards"
            ],
            
            # Solution-Oriented Language
            "solutions": [
                "We will work to resolve", "We are committed to finding", "We will investigate",
                "We will review and address", "We will take appropriate action", "We will ensure",
                "We will coordinate", "We will facilitate", "We will expedite",
                "We will prioritize", "We will implement", "We will arrange",
                "We will process", "We will handle", "We will manage", "We will oversee"
            ],
            
            # Professional Closings
            "closings": [
                "Thank you for your understanding", "We appreciate your cooperation", "Please feel free to contact",
                "Should you have any questions", "We remain at your service", "Thank you for choosing WCFCB",
                "We look forward to serving you", "Please do not hesitate to reach out", "We are here to help",
                "Your satisfaction is our priority", "We value your continued trust", "Thank you for your patience",
                "We appreciate your business", "Please let us know if you need", "We are committed to excellence"
            ],
            
            # Claims Processing Language
            "claims": [
                "claim assessment", "thorough evaluation", "comprehensive review", "detailed analysis",
                "medical documentation", "supporting evidence", "claim determination", "benefit calculation",
                "processing timeline", "status update", "claim resolution", "final determination",
                "appeal process", "review procedure", "documentation requirements", "eligibility criteria",
                "coverage verification", "benefit entitlement", "claim approval", "payment authorization"
            ],
            
            # Medical and Healthcare Terms
            "medical": [
                "medical evaluation", "healthcare provider", "treatment authorization", "medical necessity",
                "clinical assessment", "diagnostic procedures", "therapeutic intervention", "rehabilitation services",
                "medical documentation", "physician recommendation", "treatment plan", "recovery process",
                "medical opinion", "healthcare services", "medical care", "treatment options",
                "medical review", "clinical findings", "medical records", "healthcare coverage"
            ],
            
            # Legal and Compliance Terms
            "legal": [
                "regulatory compliance", "legal requirements", "statutory obligations", "policy adherence",
                "procedural guidelines", "regulatory framework", "compliance standards", "legal provisions",
                "statutory entitlements", "regulatory oversight", "compliance monitoring", "legal documentation",
                "regulatory requirements", "policy implementation", "compliance verification", "legal obligations",
                "statutory compliance", "regulatory adherence", "policy enforcement", "legal framework"
            ],
            
            # Employer Services Language
            "employer": [
                "workplace safety", "occupational health", "safety compliance", "risk management",
                "safety training", "workplace assessment", "safety protocols", "hazard identification",
                "safety measures", "preventive strategies", "safety standards", "workplace inspection",
                "safety implementation", "risk mitigation", "safety procedures", "workplace protection",
                "safety monitoring", "compliance verification", "safety education", "workplace wellness"
            ],
            
            # Beneficiary Services Language
            "beneficiary": [
                "benefit eligibility", "entitlement verification", "benefit calculation", "payment processing",
                "benefit determination", "eligibility assessment", "benefit administration", "payment authorization",
                "benefit coverage", "entitlement review", "benefit provision", "payment schedule",
                "benefit coordination", "eligibility confirmation", "benefit management", "payment distribution",
                "benefit optimization", "entitlement protection", "benefit enhancement", "payment security"
            ],
            
            # Technical and Digital Terms
            "technical": [
                "system functionality", "technical support", "digital services", "online portal",
                "system maintenance", "technical assistance", "digital platform", "system optimization",
                "technical resolution", "system enhancement", "digital accessibility", "technical guidance",
                "system reliability", "technical implementation", "digital innovation", "system security",
                "technical expertise", "system integration", "digital transformation", "technical excellence"
            ],
            
            # Quality and Service Terms
            "quality": [
                "service excellence", "quality assurance", "continuous improvement", "service delivery",
                "quality standards", "service optimization", "performance excellence", "service enhancement",
                "quality management", "service reliability", "excellence in service", "quality commitment",
                "service innovation", "quality control", "service effectiveness", "quality improvement",
                "service satisfaction", "quality monitoring", "service excellence", "quality achievement"
            ]
        }
        
        # Context-specific keyword mappings
        self.context_mappings = {
            "claim_inquiry": ["claims", "medical", "legal", "acknowledgments", "empathy", "solutions"],
            "employer_services": ["employer", "legal", "quality", "professional", "solutions"],
            "beneficiary_support": ["beneficiary", "medical", "empathy", "solutions", "quality"],
            "technical_support": ["technical", "solutions", "quality", "acknowledgments"],
            "general_inquiry": ["greetings", "acknowledgments", "explanations", "solutions", "closings"],
            "complaint_handling": ["empathy", "acknowledgments", "solutions", "quality", "closings"],
            "policy_explanation": ["legal", "explanations", "quality", "professional"],
            "medical_authorization": ["medical", "legal", "solutions", "quality"]
        }
        
        # Tone validation patterns
        self.tone_patterns = {
            "professional": r'\b(please|thank you|appreciate|understand|assist|support|help)\b',
            "empathetic": r'\b(understand|recognize|appreciate|acknowledge|empathize|concern)\b',
            "solution_focused": r'\b(resolve|address|implement|coordinate|facilitate|ensure)\b',
            "formal": r'\b(pursuant|accordance|compliance|regulation|procedure|protocol)\b',
            "respectful": r'\b(valued|respected|esteemed|honored|privilege|courtesy)\b'
        }
    
    def get_context_keywords(self, context_type, limit=20):
        """
        Get professional keywords for a specific context.
        """
        try:
            if context_type not in self.context_mappings:
                context_type = "general_inquiry"
            
            keyword_categories = self.context_mappings[context_type]
            context_keywords = []
            
            for category in keyword_categories:
                if category in self.professional_keywords:
                    context_keywords.extend(self.professional_keywords[category])
            
            # Return limited set with variety
            if len(context_keywords) > limit:
                # Ensure variety by taking from each category
                keywords_per_category = max(1, limit // len(keyword_categories))
                selected_keywords = []
                
                for category in keyword_categories:
                    if category in self.professional_keywords:
                        category_keywords = self.professional_keywords[category][:keywords_per_category]
                        selected_keywords.extend(category_keywords)
                
                return selected_keywords[:limit]
            
            return context_keywords
            
        except Exception as e:
            frappe.log_error(f"Context keywords error: {str(e)}")
            return self.professional_keywords["greetings"][:limit]
    
    def suggest_professional_phrases(self, user_input, context_type="general_inquiry"):
        """
        Suggest professional phrases based on user input and context.
        """
        try:
            suggestions = []
            user_input_lower = user_input.lower()
            
            # Analyze user input for intent
            if any(word in user_input_lower for word in ["claim", "injury", "accident"]):
                context_type = "claim_inquiry"
            elif any(word in user_input_lower for word in ["employer", "company", "workplace"]):
                context_type = "employer_services"
            elif any(word in user_input_lower for word in ["benefit", "payment", "disability"]):
                context_type = "beneficiary_support"
            elif any(word in user_input_lower for word in ["technical", "system", "portal"]):
                context_type = "technical_support"
            elif any(word in user_input_lower for word in ["complaint", "problem", "issue"]):
                context_type = "complaint_handling"
            
            # Get context-appropriate keywords
            context_keywords = self.get_context_keywords(context_type, 15)
            
            # Generate suggestions based on input analysis
            if "?" in user_input:
                # Question - provide explanatory phrases
                suggestions.extend([
                    "Thank you for your inquiry regarding",
                    "I would be happy to explain",
                    "Please allow me to provide information about",
                    "Let me clarify this matter for you"
                ])
            
            if any(word in user_input_lower for word in ["help", "assist", "support"]):
                # Help request - provide assistance phrases
                suggestions.extend([
                    "I am here to assist you with",
                    "We are committed to helping you",
                    "Please allow me to support you in",
                    "We will work together to resolve"
                ])
            
            if any(word in user_input_lower for word in ["urgent", "emergency", "immediate"]):
                # Urgent request - provide priority phrases
                suggestions.extend([
                    "We understand the urgency of your request",
                    "We will prioritize your matter",
                    "We recognize the time-sensitive nature",
                    "We will expedite the process"
                ])
            
            # Add context-specific suggestions
            suggestions.extend(context_keywords[:5])
            
            return {
                "suggestions": suggestions[:10],
                "context_type": context_type,
                "tone_score": self.calculate_tone_score(user_input)
            }
            
        except Exception as e:
            frappe.log_error(f"Professional phrase suggestion error: {str(e)}")
            return {
                "suggestions": ["Thank you for contacting WCFCB", "We appreciate your inquiry"],
                "context_type": "general_inquiry",
                "tone_score": 0.5
            }
    
    def calculate_tone_score(self, text):
        """
        Calculate professional tone score for given text.
        """
        try:
            text_lower = text.lower()
            total_score = 0
            pattern_count = 0
            
            for tone_type, pattern in self.tone_patterns.items():
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    total_score += matches
                    pattern_count += 1
            
            # Calculate score (0-1 scale)
            if pattern_count > 0:
                score = min(1.0, total_score / (len(text.split()) * 0.1))
            else:
                score = 0.0
            
            return round(score, 2)
            
        except Exception as e:
            frappe.log_error(f"Tone score calculation error: {str(e)}")
            return 0.5
    
    def enhance_message_tone(self, message, target_context="general_inquiry"):
        """
        Enhance message with professional tone improvements.
        """
        try:
            enhanced_message = message
            suggestions = []
            
            # Check for common informal patterns and suggest improvements
            informal_patterns = {
                r'\bhi\b': "Good morning/afternoon",
                r'\bhey\b': "Hello",
                r'\bthanks\b': "Thank you",
                r'\bokay\b': "Understood",
                r'\bsure\b': "Certainly",
                r'\bno problem\b': "You're welcome",
                r'\bcan\'t\b': "cannot",
                r'\bwon\'t\b': "will not",
                r'\bdon\'t\b': "do not"
            }
            
            for pattern, replacement in informal_patterns.items():
                if re.search(pattern, enhanced_message, re.IGNORECASE):
                    suggestions.append(f"Consider replacing '{pattern}' with '{replacement}'")
            
            # Add professional opening if missing
            if not any(greeting in enhanced_message.lower() for greeting in ["thank you", "good morning", "dear", "hello"]):
                context_keywords = self.get_context_keywords(target_context, 5)
                if context_keywords:
                    enhanced_message = f"{context_keywords[0]}, {enhanced_message}"
                    suggestions.append("Added professional greeting")
            
            # Add professional closing if missing
            if not any(closing in enhanced_message.lower() for closing in ["thank you", "please", "sincerely", "regards"]):
                closings = self.professional_keywords["closings"]
                enhanced_message = f"{enhanced_message} {closings[0]}."
                suggestions.append("Added professional closing")
            
            return {
                "original_message": message,
                "enhanced_message": enhanced_message,
                "suggestions": suggestions,
                "tone_score_before": self.calculate_tone_score(message),
                "tone_score_after": self.calculate_tone_score(enhanced_message)
            }
            
        except Exception as e:
            frappe.log_error(f"Message enhancement error: {str(e)}")
            return {
                "original_message": message,
                "enhanced_message": message,
                "suggestions": [],
                "tone_score_before": 0.5,
                "tone_score_after": 0.5
            }

# Global instance
tone_manager = ProfessionalToneManager()

@frappe.whitelist()
def get_professional_keywords(context_type="general_inquiry", limit=20):
    """
    API endpoint to get professional keywords for a specific context.
    """
    try:
        keywords = tone_manager.get_context_keywords(context_type, int(limit))
        
        return {
            "success": True,
            "data": {
                "keywords": keywords,
                "context_type": context_type,
                "total_keywords": len(keywords),
                "available_contexts": list(tone_manager.context_mappings.keys())
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Professional keywords API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def suggest_professional_tone(user_input, context_type="general_inquiry"):
    """
    API endpoint to get professional tone suggestions.
    """
    try:
        if not user_input:
            return {
                "success": False,
                "error": "User input is required"
            }
        
        suggestions = tone_manager.suggest_professional_phrases(user_input, context_type)
        
        return {
            "success": True,
            "data": suggestions
        }
        
    except Exception as e:
        frappe.log_error(f"Professional tone suggestion API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def enhance_message_tone(message, target_context="general_inquiry"):
    """
    API endpoint to enhance message with professional tone.
    """
    try:
        if not message:
            return {
                "success": False,
                "error": "Message is required"
            }
        
        enhancement = tone_manager.enhance_message_tone(message, target_context)
        
        return {
            "success": True,
            "data": enhancement
        }
        
    except Exception as e:
        frappe.log_error(f"Message enhancement API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def validate_tone_quality(text):
    """
    API endpoint to validate tone quality of text.
    """
    try:
        if not text:
            return {
                "success": False,
                "error": "Text is required"
            }
        
        tone_score = tone_manager.calculate_tone_score(text)
        
        # Provide tone quality assessment
        if tone_score >= 0.8:
            quality = "Excellent"
            feedback = "Your message demonstrates excellent professional tone."
        elif tone_score >= 0.6:
            quality = "Good"
            feedback = "Your message has good professional tone with room for minor improvements."
        elif tone_score >= 0.4:
            quality = "Fair"
            feedback = "Your message could benefit from more professional language."
        else:
            quality = "Needs Improvement"
            feedback = "Consider using more professional and formal language."
        
        return {
            "success": True,
            "data": {
                "tone_score": tone_score,
                "quality_rating": quality,
                "feedback": feedback,
                "word_count": len(text.split()),
                "character_count": len(text)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Tone validation API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_tone_statistics():
    """
    API endpoint to get tone usage statistics.
    """
    try:
        # Get conversation tone statistics
        conversations = frappe.get_all("Conversation", 
            fields=["message", "response", "creation"],
            limit=100)
        
        total_conversations = len(conversations)
        tone_scores = []
        
        for conv in conversations:
            if conv.response:
                score = tone_manager.calculate_tone_score(conv.response)
                tone_scores.append(score)
        
        avg_tone_score = sum(tone_scores) / len(tone_scores) if tone_scores else 0
        
        # Categorize tone quality
        excellent_count = len([s for s in tone_scores if s >= 0.8])
        good_count = len([s for s in tone_scores if 0.6 <= s < 0.8])
        fair_count = len([s for s in tone_scores if 0.4 <= s < 0.6])
        poor_count = len([s for s in tone_scores if s < 0.4])
        
        return {
            "success": True,
            "data": {
                "total_conversations_analyzed": total_conversations,
                "average_tone_score": round(avg_tone_score, 2),
                "tone_distribution": {
                    "excellent": excellent_count,
                    "good": good_count,
                    "fair": fair_count,
                    "needs_improvement": poor_count
                },
                "total_keywords_available": sum(len(keywords) for keywords in tone_manager.professional_keywords.values()),
                "available_contexts": len(tone_manager.context_mappings),
                "analysis_date": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Tone statistics API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
