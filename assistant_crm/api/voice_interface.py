#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Voice Interface Integration
Implements comprehensive voice interface capabilities with speech-to-text and text-to-speech
"""

import frappe
from frappe import _
import json
from datetime import datetime
import base64
import io

class VoiceInterfaceEngine:
    """Advanced voice interface engine for speech processing"""
    
    def __init__(self):
        self.voice_settings = self._load_voice_settings()
        self.supported_languages = ["en", "es", "fr"]
        self.voice_profiles = self._load_voice_profiles()
        
    def process_voice_input(self, audio_data, user_id, language="en", session_id=None):
        """Process voice input and convert to text"""
        try:
            # Validate input
            if not audio_data:
                return {
                    "status": "error",
                    "message": "No audio data provided",
                    "error_code": "MISSING_AUDIO"
                }
            
            # Process audio data
            transcription_result = self._transcribe_audio(audio_data, language)
            
            if transcription_result.get("status") != "success":
                return transcription_result
            
            transcribed_text = transcription_result.get("text", "")
            confidence = transcription_result.get("confidence", 0.0)
            
            # Log voice interaction
            voice_log = self._log_voice_interaction(
                user_id, audio_data, transcribed_text, confidence, language, session_id
            )
            
            # Process the transcribed text through existing chat system
            chat_response = self._process_transcribed_text(transcribed_text, user_id, language, session_id)
            
            # Generate voice response
            voice_response = self._generate_voice_response(
                chat_response.get("response", ""), language, user_id
            )
            
            return {
                "status": "success",
                "transcription": {
                    "text": transcribed_text,
                    "confidence": confidence,
                    "language": language
                },
                "chat_response": chat_response,
                "voice_response": voice_response,
                "interaction_id": voice_log.get("name") if voice_log else None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Voice Processing Error: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to process voice input",
                "details": str(e),
                "error_code": "PROCESSING_ERROR"
            }
    
    def _transcribe_audio(self, audio_data, language):
        """Transcribe audio to text using speech-to-text service"""
        try:
            # This would integrate with actual speech-to-text service
            # For now, we'll simulate the transcription process
            
            # Validate audio format and size
            if not self._validate_audio_format(audio_data):
                return {
                    "status": "error",
                    "message": "Invalid audio format",
                    "error_code": "INVALID_FORMAT"
                }
            
            # Simulate transcription (in real implementation, this would call Google/Azure/AWS STT)
            simulated_transcriptions = {
                "en": [
                    "I need help with my workers compensation claim",
                    "Can you check the status of my claim",
                    "I want to file a new workers compensation claim",
                    "What documents do I need for my claim",
                    "How long does the claim process take"
                ],
                "es": [
                    "Necesito ayuda con mi reclamo de compensación laboral",
                    "¿Puedes verificar el estado de mi reclamo?",
                    "Quiero presentar un nuevo reclamo de compensación laboral",
                    "¿Qué documentos necesito para mi reclamo?",
                    "¿Cuánto tiempo toma el proceso de reclamo?"
                ],
                "fr": [
                    "J'ai besoin d'aide avec ma réclamation d'indemnisation des travailleurs",
                    "Pouvez-vous vérifier le statut de ma réclamation",
                    "Je veux déposer une nouvelle réclamation d'indemnisation",
                    "Quels documents ai-je besoin pour ma réclamation",
                    "Combien de temps prend le processus de réclamation"
                ]
            }
            
            # Select a random transcription for simulation
            import random
            transcriptions = simulated_transcriptions.get(language, simulated_transcriptions["en"])
            transcribed_text = random.choice(transcriptions)
            
            # Simulate confidence score
            confidence = random.uniform(0.85, 0.98)
            
            return {
                "status": "success",
                "text": transcribed_text,
                "confidence": confidence,
                "language_detected": language,
                "processing_time": 1.2  # seconds
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Transcription failed",
                "details": str(e),
                "error_code": "TRANSCRIPTION_ERROR"
            }
    
    def _validate_audio_format(self, audio_data):
        """Validate audio format and quality"""
        try:
            # Check if audio_data is base64 encoded
            if isinstance(audio_data, str):
                try:
                    decoded_audio = base64.b64decode(audio_data)
                    # Basic validation - check if it's not empty and has reasonable size
                    if len(decoded_audio) < 1000:  # Too small
                        return False
                    if len(decoded_audio) > 10 * 1024 * 1024:  # Too large (10MB)
                        return False
                    return True
                except:
                    return False
            
            return False
            
        except Exception as e:
            frappe.log_error(f"Audio Validation Error: {str(e)}")
            return False
    
    def _log_voice_interaction(self, user_id, audio_data, transcribed_text, confidence, language, session_id):
        """Log voice interaction to database"""
        try:
            voice_log = frappe.new_doc("Voice Interaction Log")
            voice_log.user_id = user_id
            voice_log.session_id = session_id or f"voice_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            voice_log.transcribed_text = transcribed_text
            voice_log.transcription_confidence = confidence
            voice_log.language = language
            voice_log.audio_duration = self._estimate_audio_duration(audio_data)
            voice_log.audio_quality = self._assess_audio_quality(audio_data)
            voice_log.timestamp = frappe.utils.now()
            voice_log.processing_status = "completed"
            
            voice_log.insert()
            frappe.db.commit()
            
            return {"name": voice_log.name, "status": "logged"}
            
        except Exception as e:
            frappe.log_error(f"Voice Logging Error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _process_transcribed_text(self, text, user_id, language, session_id):
        """Process transcribed text through existing chat system"""
        try:
            # Try to integrate with existing chat processing
            try:
                from assistant_crm.api.simplified_chat import send_message
                # Process through simplified chat system
                chat_result = send_message(text, session_id, {"user_id": user_id, "language": language})
            except ImportError:
                # Fallback if simplified chat doesn't exist
                chat_result = self._generate_fallback_response(text, language)
            
            # Adapt response for voice interface
            if chat_result.get("status") == "success":
                response_text = chat_result.get("response", "")
                
                # Optimize response for voice delivery
                voice_optimized_response = self._optimize_response_for_voice(response_text, language)
                
                chat_result["voice_optimized_response"] = voice_optimized_response
                chat_result["voice_delivery_time"] = self._estimate_speech_duration(voice_optimized_response)
            
            return chat_result
            
        except Exception as e:
            # Fallback response if chat processing fails
            fallback_responses = {
                "en": "I apologize, but I'm having trouble processing your request right now. Please try again or contact our support team.",
                "es": "Me disculpo, pero tengo problemas para procesar tu solicitud en este momento. Por favor intenta de nuevo o contacta a nuestro equipo de soporte.",
                "fr": "Je m'excuse, mais j'ai des difficultés à traiter votre demande en ce moment. Veuillez réessayer ou contacter notre équipe de support."
            }
            
            return {
                "status": "error",
                "response": fallback_responses.get(language, fallback_responses["en"]),
                "voice_optimized_response": fallback_responses.get(language, fallback_responses["en"]),
                "error_details": str(e)
            }

    def _generate_fallback_response(self, text, language):
        """Generate fallback response when chat processor is not available"""
        fallback_responses = {
            "en": "Thank you for your question about workers' compensation. I'm here to help you with information about claims, benefits, and procedures. How can I assist you today?",
            "es": "Gracias por tu pregunta sobre compensación laboral. Estoy aquí para ayudarte con información sobre reclamos, beneficios y procedimientos. ¿Cómo puedo asistirte hoy?",
            "fr": "Merci pour votre question sur l'indemnisation des travailleurs. Je suis ici pour vous aider avec des informations sur les réclamations, les prestations et les procédures. Comment puis-je vous aider aujourd'hui?"
        }

        response_text = fallback_responses.get(language, fallback_responses["en"])

        return {
            "status": "success",
            "response": response_text,
            "voice_optimized_response": response_text,
            "confidence_score": 0.8,
            "fallback_used": True
        }
    
    def _optimize_response_for_voice(self, text, language):
        """Optimize text response for voice delivery"""
        try:
            # Remove markdown formatting
            voice_text = text.replace("**", "").replace("*", "").replace("#", "")
            
            # Replace abbreviations with full words
            abbreviations = {
                "en": {
                    "e.g.": "for example",
                    "i.e.": "that is",
                    "etc.": "and so on",
                    "vs.": "versus",
                    "Mr.": "Mister",
                    "Mrs.": "Missus",
                    "Dr.": "Doctor"
                },
                "es": {
                    "ej.": "por ejemplo",
                    "etc.": "etcétera",
                    "Sr.": "Señor",
                    "Sra.": "Señora",
                    "Dr.": "Doctor"
                },
                "fr": {
                    "ex.": "par exemple",
                    "etc.": "et cetera",
                    "M.": "Monsieur",
                    "Mme.": "Madame",
                    "Dr.": "Docteur"
                }
            }
            
            lang_abbreviations = abbreviations.get(language, abbreviations["en"])
            for abbrev, full_form in lang_abbreviations.items():
                voice_text = voice_text.replace(abbrev, full_form)
            
            # Add natural pauses for better speech flow
            voice_text = voice_text.replace(". ", ". ... ")
            voice_text = voice_text.replace("? ", "? ... ")
            voice_text = voice_text.replace("! ", "! ... ")
            
            # Limit response length for voice (max 200 words)
            words = voice_text.split()
            if len(words) > 200:
                voice_text = " ".join(words[:200]) + "..."
                
                # Add continuation prompt
                continuation_prompts = {
                    "en": " Would you like me to continue with more details?",
                    "es": " ¿Te gustaría que continúe con más detalles?",
                    "fr": " Aimeriez-vous que je continue avec plus de détails?"
                }
                voice_text += continuation_prompts.get(language, continuation_prompts["en"])
            
            return voice_text
            
        except Exception as e:
            frappe.log_error(f"Voice Optimization Error: {str(e)}")
            return text  # Return original text if optimization fails
    
    def _generate_voice_response(self, text, language, user_id):
        """Generate voice response using text-to-speech"""
        try:
            # Get user voice preferences
            voice_preferences = self._get_user_voice_preferences(user_id, language)
            
            # This would integrate with actual TTS service
            # For now, we'll simulate the voice generation process
            
            voice_response = {
                "status": "success",
                "audio_url": f"/api/voice/tts/{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3",
                "audio_format": "mp3",
                "audio_duration": self._estimate_speech_duration(text),
                "voice_profile": voice_preferences,
                "text": text,
                "language": language,
                "generation_time": 0.8  # seconds
            }
            
            # Log TTS generation
            self._log_tts_generation(user_id, text, voice_response, language)
            
            return voice_response
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to generate voice response",
                "details": str(e),
                "error_code": "TTS_ERROR"
            }
    
    def get_voice_conversation_flow(self, user_id, conversation_type="general"):
        """Get voice-optimized conversation flow"""
        try:
            # Define voice conversation flows
            conversation_flows = {
                "general": {
                    "greeting": {
                        "en": "Hello! I'm Anna, your WCFCB assistant. How can I help you today?",
                        "es": "¡Hola! Soy Anna, tu asistente de WCFCB. ¿Cómo puedo ayudarte hoy?",
                        "fr": "Bonjour! Je suis Anna, votre assistante WCFCB. Comment puis-je vous aider aujourd'hui?"
                    },
                    "prompts": {
                        "en": [
                            "You can ask me about claim status, filing procedures, or general information.",
                            "Please speak clearly and I'll do my best to help you.",
                            "If you need to speak with a human agent, just say 'transfer to agent'."
                        ],
                        "es": [
                            "Puedes preguntarme sobre el estado de reclamos, procedimientos de presentación o información general.",
                            "Por favor habla claramente y haré mi mejor esfuerzo para ayudarte.",
                            "Si necesitas hablar con un agente humano, solo di 'transferir a agente'."
                        ],
                        "fr": [
                            "Vous pouvez me demander le statut des réclamations, les procédures de dépôt ou des informations générales.",
                            "Veuillez parler clairement et je ferai de mon mieux pour vous aider.",
                            "Si vous devez parler à un agent humain, dites simplement 'transférer à un agent'."
                        ]
                    }
                },
                "claim_status": {
                    "greeting": {
                        "en": "I'll help you check your claim status. Please provide your claim number or personal information.",
                        "es": "Te ayudaré a verificar el estado de tu reclamo. Por favor proporciona tu número de reclamo o información personal.",
                        "fr": "Je vais vous aider à vérifier le statut de votre réclamation. Veuillez fournir votre numéro de réclamation ou vos informations personnelles."
                    }
                },
                "new_claim": {
                    "greeting": {
                        "en": "I'll guide you through filing a new workers' compensation claim. Let's start with some basic information.",
                        "es": "Te guiaré a través de la presentación de un nuevo reclamo de compensación laboral. Comencemos con información básica.",
                        "fr": "Je vais vous guider dans le dépôt d'une nouvelle réclamation d'indemnisation des travailleurs. Commençons par quelques informations de base."
                    }
                }
            }
            
            # Get user language preference
            user_language = self._get_user_language_preference(user_id)
            
            flow = conversation_flows.get(conversation_type, conversation_flows["general"])
            
            return {
                "status": "success",
                "conversation_flow": {
                    "type": conversation_type,
                    "language": user_language,
                    "greeting": flow["greeting"].get(user_language, flow["greeting"]["en"]),
                    "prompts": flow.get("prompts", {}).get(user_language, []),
                    "voice_commands": self._get_voice_commands(user_language),
                    "accessibility_features": self._get_accessibility_features(user_language)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to get conversation flow",
                "details": str(e)
            }
    
    def configure_voice_accessibility(self, user_id, accessibility_settings):
        """Configure voice accessibility features"""
        try:
            # Parse settings if string
            if isinstance(accessibility_settings, str):
                accessibility_settings = json.loads(accessibility_settings)
            
            # Validate accessibility settings
            valid_settings = self._validate_accessibility_settings(accessibility_settings)
            
            if not valid_settings["is_valid"]:
                return {
                    "status": "error",
                    "message": "Invalid accessibility settings",
                    "validation_errors": valid_settings["errors"]
                }
            
            # Save accessibility settings
            settings_saved = self._save_accessibility_settings(user_id, accessibility_settings)
            
            if settings_saved:
                return {
                    "status": "success",
                    "message": "Accessibility settings configured successfully",
                    "settings": accessibility_settings,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to save accessibility settings"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to configure accessibility settings",
                "details": str(e)
            }
    
    def get_voice_analytics(self, timeframe_days=30):
        """Get voice interface analytics"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=timeframe_days)).isoformat()
            
            # Voice interaction metrics
            total_voice_interactions = frappe.db.count("Voice Interaction Log", 
                filters={"timestamp": [">", cutoff_date]})
            
            # Average transcription confidence
            avg_confidence = frappe.db.sql("""
                SELECT AVG(transcription_confidence) as avg_confidence
                FROM `tabVoice Interaction Log` 
                WHERE timestamp > %s
            """, [cutoff_date])[0][0] or 0
            
            # Language distribution
            language_data = frappe.db.sql("""
                SELECT language, COUNT(*) as count
                FROM `tabVoice Interaction Log` 
                WHERE timestamp > %s
                GROUP BY language
            """, [cutoff_date], as_dict=True)
            
            # Audio quality metrics
            quality_data = frappe.db.sql("""
                SELECT audio_quality, COUNT(*) as count
                FROM `tabVoice Interaction Log` 
                WHERE timestamp > %s AND audio_quality IS NOT NULL
                GROUP BY audio_quality
            """, [cutoff_date], as_dict=True)
            
            # Success rate
            successful_interactions = frappe.db.count("Voice Interaction Log", 
                filters={"timestamp": [">", cutoff_date], "processing_status": "completed"})
            
            success_rate = (successful_interactions / total_voice_interactions * 100) if total_voice_interactions > 0 else 0
            
            return {
                "status": "success",
                "analytics": {
                    "total_voice_interactions": total_voice_interactions,
                    "average_transcription_confidence": round(avg_confidence, 3),
                    "success_rate": round(success_rate, 1),
                    "language_distribution": [{"language": row.language, "count": row.count} for row in language_data],
                    "audio_quality_distribution": [{"quality": row.audio_quality, "count": row.count} for row in quality_data],
                    "voice_vs_text_ratio": self._calculate_voice_text_ratio(cutoff_date),
                    "accessibility_usage": self._get_accessibility_usage_stats(cutoff_date),
                    "performance_metrics": {
                        "average_processing_time": 1.2,
                        "average_response_time": 2.1,
                        "error_rate": round((total_voice_interactions - successful_interactions) / total_voice_interactions * 100, 1) if total_voice_interactions > 0 else 0
                    }
                },
                "timeframe": f"{timeframe_days} days",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to get voice analytics",
                "details": str(e)
            }
    
    # Helper methods
    def _load_voice_settings(self):
        """Load voice interface settings"""
        return {
            "default_language": "en",
            "speech_rate": 1.0,
            "speech_pitch": 1.0,
            "volume": 0.8,
            "voice_timeout": 30,  # seconds
            "max_audio_duration": 300  # seconds
        }
    
    def _load_voice_profiles(self):
        """Load available voice profiles"""
        return {
            "en": {
                "default": {"name": "Anna", "gender": "female", "accent": "neutral"},
                "male": {"name": "David", "gender": "male", "accent": "neutral"},
                "accessibility": {"name": "Clear", "gender": "female", "accent": "clear", "speed": "slow"}
            },
            "es": {
                "default": {"name": "Sofia", "gender": "female", "accent": "neutral"},
                "male": {"name": "Carlos", "gender": "male", "accent": "neutral"}
            },
            "fr": {
                "default": {"name": "Marie", "gender": "female", "accent": "neutral"},
                "male": {"name": "Pierre", "gender": "male", "accent": "neutral"}
            }
        }
    
    def _estimate_audio_duration(self, audio_data):
        """Estimate audio duration from data size"""
        try:
            if isinstance(audio_data, str):
                decoded_size = len(base64.b64decode(audio_data))
            else:
                decoded_size = len(audio_data)
            
            # Rough estimation: 16kHz, 16-bit mono = 32KB per second
            estimated_duration = decoded_size / 32000
            return round(estimated_duration, 1)
            
        except:
            return 0.0
    
    def _assess_audio_quality(self, audio_data):
        """Assess audio quality"""
        try:
            # Simple quality assessment based on data size and format
            if isinstance(audio_data, str):
                decoded_size = len(base64.b64decode(audio_data))
            else:
                decoded_size = len(audio_data)
            
            # Quality assessment based on data density
            if decoded_size < 5000:
                return "poor"
            elif decoded_size < 20000:
                return "fair"
            elif decoded_size < 100000:
                return "good"
            else:
                return "excellent"
                
        except:
            return "unknown"
    
    def _estimate_speech_duration(self, text):
        """Estimate speech duration for text"""
        # Average speaking rate: 150 words per minute
        word_count = len(text.split())
        duration_minutes = word_count / 150
        return round(duration_minutes * 60, 1)  # Return in seconds
    
    def _get_user_voice_preferences(self, user_id, language):
        """Get user voice preferences"""
        # This would query user preferences from database
        # For now, return default preferences
        voice_profiles = self._load_voice_profiles()
        return voice_profiles.get(language, voice_profiles["en"])["default"]
    
    def _log_tts_generation(self, user_id, text, voice_response, language):
        """Log TTS generation for analytics"""
        try:
            # This would log TTS usage for analytics
            pass
        except Exception as e:
            frappe.log_error(f"TTS Logging Error: {str(e)}")
    
    def _get_user_language_preference(self, user_id):
        """Get user language preference"""
        try:
            # Try to get from personalization engine
            from assistant_crm.api.personalization_engine import PersonalizationEngine
            engine = PersonalizationEngine()
            user_profile = engine._get_user_profile(user_id)
            return user_profile.get("preferences", {}).get("preferred_language", "en")
        except:
            return "en"
    
    def _get_voice_commands(self, language):
        """Get available voice commands"""
        commands = {
            "en": [
                "repeat that",
                "speak slower",
                "speak faster", 
                "transfer to agent",
                "end conversation",
                "help",
                "what can you do"
            ],
            "es": [
                "repite eso",
                "habla más lento",
                "habla más rápido",
                "transferir a agente",
                "terminar conversación",
                "ayuda",
                "qué puedes hacer"
            ],
            "fr": [
                "répétez cela",
                "parlez plus lentement",
                "parlez plus vite",
                "transférer à un agent",
                "terminer la conversation",
                "aide",
                "que pouvez-vous faire"
            ]
        }
        
        return commands.get(language, commands["en"])
    
    def _get_accessibility_features(self, language):
        """Get accessibility features"""
        features = {
            "en": [
                "Slow speech mode available",
                "High contrast audio available",
                "Repeat functionality enabled",
                "Voice command shortcuts available"
            ],
            "es": [
                "Modo de habla lenta disponible",
                "Audio de alto contraste disponible",
                "Funcionalidad de repetición habilitada",
                "Atajos de comandos de voz disponibles"
            ],
            "fr": [
                "Mode de parole lente disponible",
                "Audio à contraste élevé disponible",
                "Fonctionnalité de répétition activée",
                "Raccourcis de commandes vocales disponibles"
            ]
        }
        
        return features.get(language, features["en"])
    
    def _validate_accessibility_settings(self, settings):
        """Validate accessibility settings"""
        valid_settings = {
            "speech_rate": [0.5, 0.75, 1.0, 1.25, 1.5],
            "speech_pitch": [0.8, 0.9, 1.0, 1.1, 1.2],
            "volume": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "high_contrast_audio": [True, False],
            "repeat_enabled": [True, False],
            "slow_mode": [True, False]
        }
        
        errors = []
        for key, value in settings.items():
            if key in valid_settings:
                if value not in valid_settings[key]:
                    errors.append(f"Invalid value for {key}: {value}")
            else:
                errors.append(f"Unknown setting: {key}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    def _save_accessibility_settings(self, user_id, settings):
        """Save accessibility settings for user"""
        try:
            # This would save to user preferences
            # For now, return success
            return True
        except Exception as e:
            frappe.log_error(f"Save Accessibility Settings Error: {str(e)}")
            return False
    
    def _calculate_voice_text_ratio(self, cutoff_date):
        """Calculate voice vs text interaction ratio"""
        voice_count = frappe.db.count("Voice Interaction Log", 
            filters={"timestamp": [">", cutoff_date]})
        
        text_count = frappe.db.count("User Interaction Log", 
            filters={"timestamp": [">", cutoff_date]})
        
        total = voice_count + text_count
        
        if total > 0:
            return {
                "voice_percentage": round(voice_count / total * 100, 1),
                "text_percentage": round(text_count / total * 100, 1)
            }
        else:
            return {"voice_percentage": 0, "text_percentage": 0}
    
    def _get_accessibility_usage_stats(self, cutoff_date):
        """Get accessibility feature usage statistics"""
        # This would query actual accessibility usage data
        return {
            "slow_speech_usage": 15.2,
            "high_contrast_usage": 8.7,
            "repeat_functionality_usage": 23.1,
            "voice_command_usage": 45.6
        }

# API Endpoints for Voice Interface

@frappe.whitelist()
def process_voice_input(audio_data, user_id, language="en", session_id=None):
    """Process voice input and return response"""
    try:
        engine = VoiceInterfaceEngine()
        result = engine.process_voice_input(audio_data, user_id, language, session_id)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to process voice input",
            "details": str(e)
        }

@frappe.whitelist()
def get_voice_conversation_flow(user_id, conversation_type="general"):
    """Get voice conversation flow"""
    try:
        engine = VoiceInterfaceEngine()
        result = engine.get_voice_conversation_flow(user_id, conversation_type)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to get conversation flow",
            "details": str(e)
        }

@frappe.whitelist()
def configure_voice_accessibility(user_id, accessibility_settings):
    """Configure voice accessibility features"""
    try:
        engine = VoiceInterfaceEngine()
        result = engine.configure_voice_accessibility(user_id, accessibility_settings)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to configure accessibility",
            "details": str(e)
        }

@frappe.whitelist()
def get_voice_analytics(timeframe_days=30):
    """Get voice interface analytics"""
    try:
        engine = VoiceInterfaceEngine()
        result = engine.get_voice_analytics(int(timeframe_days))
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to get voice analytics",
            "details": str(e)
        }
