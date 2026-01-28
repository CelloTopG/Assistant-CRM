# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _


class SentimentAnalysisService:
	"""Enhanced sentiment analysis service for WCFCB CRM messages with Phase 2 features"""

	def __init__(self):
		self.positive_words = self._load_positive_words()
		self.negative_words = self._load_negative_words()
		self.intensifiers = self._load_intensifiers()
		self.negation_words = self._load_negation_words()

		# Phase 2 enhancements - emotion detection
		self.emotion_patterns = {
			'frustration': ['frustrated', 'annoyed', 'irritated', 'fed up', 'angry'],
			'confusion': ['confused', 'lost', 'unclear', 'don\'t understand', 'what does this mean'],
			'urgency': ['urgent', 'asap', 'immediately', 'right now', 'emergency'],
			'satisfaction': ['satisfied', 'happy', 'pleased', 'great', 'perfect'],
			'gratitude': ['thank', 'thanks', 'appreciate', 'grateful', 'helpful']
		}

		# Anna's response adjustments based on detected emotions
		self.anna_adjustments = {
			'frustration': {'tone': 'empathetic', 'urgency': 'high', 'escalation': True},
			'confusion': {'tone': 'patient', 'detail_level': 'high', 'examples': True},
			'urgency': {'tone': 'professional', 'response_speed': 'immediate', 'priority': 'high'},
			'satisfaction': {'tone': 'warm', 'celebration': True, 'follow_up': 'light'},
			'gratitude': {'tone': 'appreciative', 'warmth': 'high', 'offer_more_help': True}
		}
	
	def analyze_sentiment(self, text):
		"""Analyze sentiment of text message"""
		try:
			if not text or not isinstance(text, str):
				return self._get_neutral_sentiment()
			
			# Clean and preprocess text
			cleaned_text = self._preprocess_text(text)
			words = cleaned_text.split()
			
			if not words:
				return self._get_neutral_sentiment()
			
			# Calculate sentiment scores
			positive_score = self._calculate_positive_score(words)
			negative_score = self._calculate_negative_score(words)
			neutral_score = max(0, len(words) - positive_score - negative_score)
			
			# Normalize scores
			total_words = len(words)
			pos_normalized = positive_score / total_words if total_words > 0 else 0
			neg_normalized = negative_score / total_words if total_words > 0 else 0
			neu_normalized = neutral_score / total_words if total_words > 0 else 1
			
			# Calculate compound score
			compound_score = self._calculate_compound_score(pos_normalized, neg_normalized)
			
			# Determine overall sentiment
			sentiment_label = self._get_sentiment_label(compound_score)
			
			# Check for escalation triggers
			escalation_needed = self._check_escalation_triggers(text, compound_score)
			
			return {
				"success": True,
				"positive": round(pos_normalized, 3),
				"negative": round(neg_normalized, 3),
				"neutral": round(neu_normalized, 3),
				"compound_score": round(compound_score, 3),
				"sentiment": sentiment_label,
				"sentiment_label": sentiment_label,  # For integration test compatibility
				"escalation_needed": escalation_needed,
				"confidence": self._calculate_confidence(pos_normalized, neg_normalized, neu_normalized)
			}
			
		except Exception as e:
			frappe.log_error(f"Error in sentiment analysis: {str(e)}", "Sentiment Analysis Service")
			return self._get_neutral_sentiment()
	
	def _preprocess_text(self, text):
		"""Clean and preprocess text for analysis"""
		# Convert to lowercase
		text = text.lower()
		
		# Remove URLs
		text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
		
		# Remove email addresses
		text = re.sub(r'\S+@\S+', '', text)
		
		# Remove phone numbers
		text = re.sub(r'[\+]?[1-9]?[0-9]{7,15}', '', text)
		
		# Remove extra whitespace and punctuation
		text = re.sub(r'[^\w\s]', ' ', text)
		text = re.sub(r'\s+', ' ', text)
		
		return text.strip()
	
	def _calculate_positive_score(self, words):
		"""Calculate positive sentiment score"""
		score = 0
		negation_active = False
		
		for i, word in enumerate(words):
			if word in self.negation_words:
				negation_active = True
				continue
			
			if word in self.positive_words:
				word_score = 1
				
				# Check for intensifiers
				if i > 0 and words[i-1] in self.intensifiers:
					word_score *= self.intensifiers[words[i-1]]
				
				# Apply negation
				if negation_active:
					word_score *= -0.5
					negation_active = False
				
				score += word_score
			
			# Reset negation after 2 words
			if negation_active and i > 0 and words[i-1] not in self.negation_words:
				negation_active = False
		
		return max(0, score)
	
	def _calculate_negative_score(self, words):
		"""Calculate negative sentiment score"""
		score = 0
		negation_active = False
		
		for i, word in enumerate(words):
			if word in self.negation_words:
				negation_active = True
				continue
			
			if word in self.negative_words:
				word_score = 1
				
				# Check for intensifiers
				if i > 0 and words[i-1] in self.intensifiers:
					word_score *= self.intensifiers[words[i-1]]
				
				# Apply negation
				if negation_active:
					word_score *= -0.5
					negation_active = False
				
				score += word_score
			
			# Reset negation after 2 words
			if negation_active and i > 0 and words[i-1] not in self.negation_words:
				negation_active = False
		
		return max(0, score)
	
	def _calculate_compound_score(self, pos_score, neg_score):
		"""Calculate compound sentiment score"""
		if pos_score == 0 and neg_score == 0:
			return 0.0
		
		# Simple compound calculation
		compound = pos_score - neg_score
		
		# Normalize to -1 to 1 range
		if compound > 0:
			compound = min(compound, 1.0)
		else:
			compound = max(compound, -1.0)
		
		return compound
	
	def _get_sentiment_label(self, compound_score):
		"""Get sentiment label from compound score"""
		if compound_score >= 0.05:
			return "positive"
		elif compound_score <= -0.05:
			return "negative"
		else:
			return "neutral"
	
	def _calculate_confidence(self, pos_score, neg_score, neu_score):
		"""Calculate confidence level of sentiment analysis"""
		# Higher confidence when one sentiment dominates
		max_score = max(pos_score, neg_score, neu_score)
		if max_score > 0.6:
			return "high"
		elif max_score > 0.4:
			return "medium"
		else:
			return "low"
	
	def _check_escalation_triggers(self, text, compound_score):
		"""Check if message should trigger escalation"""
		# Very negative sentiment
		if compound_score < -0.6:
			return True
		
		# Escalation keywords
		escalation_keywords = [
			"complaint", "complain", "angry", "furious", "upset", "frustrated",
			"terrible", "awful", "horrible", "worst", "hate", "disgusted",
			"unacceptable", "outrageous", "ridiculous", "pathetic",
			"manager", "supervisor", "escalate", "legal", "lawyer",
			"sue", "court", "media", "newspaper", "report"
		]
		
		text_lower = text.lower()
		for keyword in escalation_keywords:
			if keyword in text_lower:
				return True
		
		return False
	
	def _get_neutral_sentiment(self):
		"""Get neutral sentiment response"""
		return {
			"success": True,
			"positive": 0.0,
			"negative": 0.0,
			"neutral": 1.0,
			"compound_score": 0.0,
			"sentiment": "neutral",
			"sentiment_label": "neutral",  # For integration test compatibility
			"escalation_needed": False,
			"confidence": "low"
		}
	
	def _load_positive_words(self):
		"""Load positive sentiment words"""
		return {
			# English positive words
			"good", "great", "excellent", "amazing", "wonderful", "fantastic",
			"awesome", "brilliant", "perfect", "outstanding", "superb",
			"happy", "pleased", "satisfied", "delighted", "thrilled",
			"love", "like", "enjoy", "appreciate", "thank", "thanks",
			"helpful", "useful", "efficient", "quick", "fast", "easy",
			"professional", "friendly", "polite", "courteous", "kind",
			
			# Bemba positive words
			"bwino", "ukusuma", "ukufwa", "ukusangalala", "ukutotela",
			"ukutemwa", "ukupenda", "ukusuma", "bwino sana",
			
			# Nyanja positive words
			"bwino", "kusangalala", "kukondwa", "kutamanda", "kuyamika",
			"kukonda", "kusangalala", "bwino kwambiri",
			
			# Tonga positive words
			"botu", "kusangalala", "kukondwa", "kutenda", "kuyanda"
		}
	
	def _load_negative_words(self):
		"""Load negative sentiment words"""
		return {
			# English negative words
			"bad", "terrible", "awful", "horrible", "worst", "hate",
			"angry", "mad", "furious", "upset", "frustrated", "annoyed",
			"disappointed", "dissatisfied", "unhappy", "sad", "disgusted",
			"useless", "worthless", "pathetic", "ridiculous", "stupid",
			"slow", "difficult", "hard", "impossible", "broken",
			"rude", "unprofessional", "incompetent", "lazy", "careless",
			"complaint", "complain", "problem", "issue", "trouble",
			
			# Bemba negative words
			"icibi", "ukusulila", "ukukalipa", "ukufwaya", "ukusunga",
			"icibi sana", "ukukalipila", "ukufwayafwaya",
			
			# Nyanja negative words
			"choipa", "kukwiya", "kupsya mtima", "kusauka", "kunyoza",
			"choipa kwambiri", "kukwiyakwiya", "kupsyapsya",
			
			# Tonga negative words
			"bibi", "kukalipa", "kufwaya", "kusulila", "kunyema"
		}
	
	def _load_intensifiers(self):
		"""Load intensifier words with their multipliers"""
		return {
			"very": 1.5,
			"extremely": 2.0,
			"really": 1.3,
			"absolutely": 1.8,
			"completely": 1.7,
			"totally": 1.6,
			"quite": 1.2,
			"rather": 1.1,
			"so": 1.4,
			"too": 1.3,
			"highly": 1.5,
			"incredibly": 1.9,
			"amazingly": 1.8,
			"exceptionally": 2.0,
			
			# Multi-language intensifiers
			"sana": 1.5,  # Bemba/Nyanja/Tonga
			"kwambiri": 1.6,  # Nyanja
			"muno": 1.4  # Tonga
		}
	
	def _load_negation_words(self):
		"""Load negation words"""
		return {
			"not", "no", "never", "nothing", "nobody", "nowhere",
			"neither", "nor", "none", "without", "lack", "lacking",
			"absent", "missing", "fail", "failed", "unable", "cannot",
			"can't", "won't", "wouldn't", "shouldn't", "couldn't",
			"don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",

			# Multi-language negations
			"tabu",  # Bemba - no
			"awe",   # Bemba - no
			"iyayi", # Nyanja - no
			"ayi",   # Nyanja - no
			"pe",    # Tonga - no
			"kana"   # Tonga - no
		}

	def analyze_urgency(self, text, customer_data=None):
		"""Enhanced urgency detection for smart routing"""
		try:
			if not text or not isinstance(text, str):
				return self._get_neutral_urgency()

			urgency_indicators = self._load_urgency_indicators()
			text_lower = text.lower()

			# Calculate urgency scores
			urgency_scores = {
				'critical': 0,
				'high': 0,
				'medium': 0,
				'low': 0
			}

			# Check for urgency keywords
			for level, keywords in urgency_indicators.items():
				for keyword in keywords:
					if keyword in text_lower:
						urgency_scores[level] += 1

			# Apply customer context
			if customer_data:
				urgency_scores = self._apply_customer_context(urgency_scores, customer_data)

			# Determine overall urgency level
			max_score = max(urgency_scores.values())
			if max_score == 0:
				urgency_level = 'low'
			else:
				urgency_level = max(urgency_scores, key=urgency_scores.get)

			# Calculate confidence
			total_indicators = sum(urgency_scores.values())
			confidence = min(max_score / max(total_indicators, 1), 1.0)

			# Determine routing priority
			routing_priority = self._calculate_routing_priority(urgency_level, urgency_scores)

			return {
				'urgency_level': urgency_level,
				'urgency_scores': urgency_scores,
				'confidence': round(confidence, 3),
				'routing_priority': routing_priority,
				'escalation_needed': urgency_level in ['critical', 'high'],
				'estimated_response_time': self._estimate_response_time(urgency_level),
				'recommended_agent_skills': self._recommend_agent_skills(text_lower, urgency_level)
			}

		except Exception as e:
			frappe.log_error(f"Error in urgency analysis: {str(e)}", "Sentiment Analysis Service")
			return self._get_neutral_urgency()

	def analyze_emotion(self, text):
		"""Advanced emotion detection for better routing"""
		try:
			if not text or not isinstance(text, str):
				return self._get_neutral_emotion()

			emotion_indicators = self._load_emotion_indicators()
			text_lower = text.lower()

			emotion_scores = {}
			for emotion, keywords in emotion_indicators.items():
				score = sum(1 for keyword in keywords if keyword in text_lower)
				if score > 0:
					emotion_scores[emotion] = score

			# Determine primary emotion
			if emotion_scores:
				primary_emotion = max(emotion_scores, key=emotion_scores.get)
				confidence = emotion_scores[primary_emotion] / len(text_lower.split())
			else:
				primary_emotion = 'neutral'
				confidence = 0.5

			# Determine routing implications
			routing_implications = self._get_emotion_routing_implications(primary_emotion)

			return {
				'primary_emotion': primary_emotion,
				'emotion_scores': emotion_scores,
				'confidence': round(min(confidence, 1.0), 3),
				'routing_implications': routing_implications
			}

		except Exception as e:
			frappe.log_error(f"Error in emotion analysis: {str(e)}", "Sentiment Analysis Service")
			return self._get_neutral_emotion()

	def get_comprehensive_analysis(self, text, customer_data=None):
		"""Get comprehensive sentiment, urgency, and emotion analysis"""
		try:
			# Get basic sentiment analysis
			sentiment_result = self.analyze_sentiment(text)

			# Get urgency analysis
			urgency_result = self.analyze_urgency(text, customer_data)

			# Get emotion analysis
			emotion_result = self.analyze_emotion(text)

			# Combine results for routing decision
			routing_recommendation = self._generate_routing_recommendation(
				sentiment_result, urgency_result, emotion_result, customer_data
			)

			return {
				'sentiment': sentiment_result,
				'urgency': urgency_result,
				'emotion': emotion_result,
				'routing_recommendation': routing_recommendation,
				'analysis_timestamp': frappe.utils.now()
			}

		except Exception as e:
			frappe.log_error(f"Error in comprehensive analysis: {str(e)}", "Sentiment Analysis Service")
			return {
				'sentiment': self._get_neutral_sentiment(),
				'urgency': self._get_neutral_urgency(),
				'emotion': self._get_neutral_emotion(),
				'routing_recommendation': self._get_default_routing(),
				'analysis_timestamp': frappe.utils.now()
			}

	def _load_urgency_indicators(self):
		"""Load urgency indicator keywords by level"""
		return {
			'critical': [
				'emergency', 'urgent', 'immediately', 'asap', 'critical', 'crisis',
				'deadline', 'overdue', 'expired', 'suspended', 'terminated',
				'legal action', 'court', 'lawsuit', 'penalty', 'fine',
				'injury', 'accident', 'death', 'hospital', 'medical emergency',
				'fire', 'flood', 'disaster', 'catastrophe'
			],
			'high': [
				'important', 'priority', 'soon', 'quickly', 'fast',
				'payment due', 'submission due', 'compliance', 'audit',
				'investigation', 'inspection', 'review', 'escalation',
				'complaint', 'dispute', 'problem', 'issue', 'concern'
			],
			'medium': [
				'question', 'inquiry', 'information', 'clarification',
				'update', 'status', 'progress', 'follow up', 'reminder',
				'request', 'application', 'registration', 'renewal'
			],
			'low': [
				'general', 'routine', 'standard', 'normal', 'regular',
				'when convenient', 'no rush', 'whenever', 'eventually'
			]
		}

	def _load_emotion_indicators(self):
		"""Load emotion indicator keywords"""
		return {
			'anger': [
				'angry', 'mad', 'furious', 'outraged', 'livid', 'enraged',
				'irritated', 'annoyed', 'frustrated', 'fed up', 'disgusted'
			],
			'fear': [
				'worried', 'concerned', 'anxious', 'nervous', 'scared',
				'afraid', 'terrified', 'panic', 'stress', 'overwhelmed'
			],
			'sadness': [
				'sad', 'disappointed', 'upset', 'depressed', 'devastated',
				'heartbroken', 'miserable', 'unhappy', 'dejected'
			],
			'joy': [
				'happy', 'pleased', 'satisfied', 'delighted', 'thrilled',
				'excited', 'grateful', 'thankful', 'appreciate', 'love'
			],
			'confusion': [
				'confused', 'unclear', 'don\'t understand', 'puzzled',
				'lost', 'bewildered', 'perplexed', 'baffled'
			],
			'trust': [
				'confident', 'trust', 'reliable', 'dependable', 'faith',
				'believe', 'count on', 'rely on'
			]
		}

	def _apply_customer_context(self, urgency_scores, customer_data):
		"""Apply customer context to urgency scoring"""
		try:
			# High-value customers get priority boost
			if customer_data.get('customer_tier') == 'premium':
				urgency_scores['high'] += 1

			# Previous escalations increase urgency
			if customer_data.get('recent_escalations', 0) > 0:
				urgency_scores['critical'] += customer_data['recent_escalations']

			# Overdue payments increase urgency
			if customer_data.get('overdue_payments', 0) > 0:
				urgency_scores['high'] += 1

			# Compliance issues increase urgency
			if customer_data.get('compliance_issues', False):
				urgency_scores['critical'] += 1

			return urgency_scores

		except Exception as e:
			frappe.log_error(f"Error applying customer context: {str(e)}")
			return urgency_scores

	def _calculate_routing_priority(self, urgency_level, urgency_scores):
		"""Calculate routing priority score"""
		priority_weights = {
			'critical': 100,
			'high': 75,
			'medium': 50,
			'low': 25
		}

		total_score = sum(urgency_scores[level] * priority_weights[level]
						for level in urgency_scores)

		return min(total_score, 100)  # Cap at 100

	def _estimate_response_time(self, urgency_level):
		"""Estimate required response time based on urgency"""
		response_times = {
			'critical': '15 minutes',
			'high': '1 hour',
			'medium': '4 hours',
			'low': '24 hours'
		}
		return response_times.get(urgency_level, '4 hours')

	def _recommend_agent_skills(self, text_lower, urgency_level):
		"""Recommend required agent skills based on message content"""
		skills = []

		# Technical skills
		if any(word in text_lower for word in ['payment', 'premium', 'billing', 'invoice']):
			skills.append('payments')

		if any(word in text_lower for word in ['claim', 'injury', 'accident', 'compensation']):
			skills.append('claims')

		if any(word in text_lower for word in ['registration', 'employer', 'company']):
			skills.append('registration')

		if any(word in text_lower for word in ['returns', 'submission', 'filing']):
			skills.append('compliance')

		# Soft skills based on urgency
		if urgency_level in ['critical', 'high']:
			skills.append('crisis_management')

		if any(word in text_lower for word in ['angry', 'frustrated', 'complaint']):
			skills.append('conflict_resolution')

		return skills

	def _get_emotion_routing_implications(self, emotion):
		"""Get routing implications based on detected emotion"""
		implications = {
			'anger': {
				'priority_boost': 2,
				'required_skills': ['conflict_resolution', 'de_escalation'],
				'avoid_skills': ['trainee'],
				'response_tone': 'empathetic_professional'
			},
			'fear': {
				'priority_boost': 1,
				'required_skills': ['reassurance', 'patience'],
				'response_tone': 'calm_supportive'
			},
			'sadness': {
				'priority_boost': 1,
				'required_skills': ['empathy', 'support'],
				'response_tone': 'compassionate'
			},
			'joy': {
				'priority_boost': 0,
				'required_skills': ['standard'],
				'response_tone': 'friendly_professional'
			},
			'confusion': {
				'priority_boost': 0,
				'required_skills': ['explanation', 'patience', 'clarity'],
				'response_tone': 'clear_helpful'
			},
			'trust': {
				'priority_boost': 0,
				'required_skills': ['standard'],
				'response_tone': 'professional_confident'
			}
		}

		return implications.get(emotion, {
			'priority_boost': 0,
			'required_skills': ['standard'],
			'response_tone': 'professional'
		})

	def _generate_routing_recommendation(self, sentiment_result, urgency_result,
										emotion_result, customer_data):
		"""Generate comprehensive routing recommendation"""
		try:
			recommendation = {
				'priority_score': 50,  # Base priority
				'required_skills': [],
				'avoid_skills': [],
				'response_tone': 'professional',
				'escalation_needed': False,
				'estimated_handle_time': '15 minutes',
				'special_instructions': []
			}

			# Apply sentiment factors
			if sentiment_result['sentiment'] == 'negative':
				recommendation['priority_score'] += 20
				recommendation['required_skills'].append('conflict_resolution')

			# Apply urgency factors
			urgency_boost = {
				'critical': 40,
				'high': 25,
				'medium': 10,
				'low': 0
			}
			recommendation['priority_score'] += urgency_boost.get(urgency_result['urgency_level'], 0)
			recommendation['required_skills'].extend(urgency_result['recommended_agent_skills'])
			recommendation['escalation_needed'] = urgency_result['escalation_needed']

			# Apply emotion factors
			emotion_implications = emotion_result['routing_implications']
			recommendation['priority_score'] += emotion_implications.get('priority_boost', 0)
			recommendation['required_skills'].extend(emotion_implications.get('required_skills', []))
			recommendation['avoid_skills'].extend(emotion_implications.get('avoid_skills', []))
			recommendation['response_tone'] = emotion_implications.get('response_tone', 'professional')

			# Apply customer context
			if customer_data:
				if customer_data.get('customer_tier') == 'premium':
					recommendation['priority_score'] += 15
					recommendation['special_instructions'].append('Premium customer - priority handling')

				if customer_data.get('recent_escalations', 0) > 0:
					recommendation['priority_score'] += 10
					recommendation['special_instructions'].append('Customer has recent escalations - handle with care')

			# Cap priority score
			recommendation['priority_score'] = min(recommendation['priority_score'], 100)

			# Remove duplicates from skills
			recommendation['required_skills'] = list(set(recommendation['required_skills']))
			recommendation['avoid_skills'] = list(set(recommendation['avoid_skills']))

			return recommendation

		except Exception as e:
			frappe.log_error(f"Error generating routing recommendation: {str(e)}")
			return self._get_default_routing()

	def _get_neutral_urgency(self):
		"""Get neutral urgency response"""
		return {
			'urgency_level': 'medium',
			'urgency_scores': {'critical': 0, 'high': 0, 'medium': 1, 'low': 0},
			'confidence': 0.5,
			'routing_priority': 50,
			'escalation_needed': False,
			'estimated_response_time': '4 hours',
			'recommended_agent_skills': ['standard']
		}

	def _get_neutral_emotion(self):
		"""Get neutral emotion response"""
		return {
			'primary_emotion': 'neutral',
			'emotion_scores': {},
			'confidence': 0.5,
			'routing_implications': {
				'priority_boost': 0,
				'required_skills': ['standard'],
				'response_tone': 'professional'
			}
		}

	def _get_default_routing(self):
		"""Get default routing recommendation"""
		return {
			'priority_score': 50,
			'required_skills': ['standard'],
			'avoid_skills': [],
			'response_tone': 'professional',
			'escalation_needed': False,
			'estimated_handle_time': '15 minutes',
			'special_instructions': []
		}

# Phase 2 Enhancement Methods
def detect_emotions_enhanced(self, text, conversation_history=None):
	"""Enhanced emotion detection with conversation context"""
	try:
		emotions = {}
		text_lower = text.lower()

		# Detect emotions using pattern matching
		for emotion, patterns in self.emotion_patterns.items():
			score = 0
			for pattern in patterns:
				if pattern in text_lower:
					score += 1
			emotions[emotion] = min(score / len(patterns), 1.0)

		# Analyze conversation context if available
		if conversation_history:
			context_emotions = self._analyze_conversation_emotion_trend(conversation_history)
			emotions.update(context_emotions)

		# Determine primary emotion
		primary_emotion = max(emotions.items(), key=lambda x: x[1])[0] if emotions else 'neutral'

		# Generate Anna's response adjustments
		anna_adjustments = self.anna_adjustments.get(primary_emotion, {})

		return {
			'success': True,
			'primary_emotion': primary_emotion,
			'emotion_scores': emotions,
			'anna_adjustments': anna_adjustments,
			'confidence': emotions.get(primary_emotion, 0.0),
			'conversation_context': conversation_history is not None
		}

	except Exception as e:
		frappe.log_error(f"Enhanced emotion detection error: {str(e)}", "SentimentAnalysisService")
		return self._get_neutral_emotion()

	def _analyze_conversation_emotion_trend(self, conversation_history):
		"""Analyze emotion trends in conversation history"""
		emotion_trend = {}

		# Look at last 3 messages for trend analysis
		recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history

		for msg in recent_messages:
			content = msg.get('content', '')
			if content:
				msg_emotions = {}
				content_lower = content.lower()

				for emotion, patterns in self.emotion_patterns.items():
					score = sum(1 for pattern in patterns if pattern in content_lower)
					if score > 0:
						msg_emotions[emotion] = score

				# Add to trend
				for emotion, score in msg_emotions.items():
					emotion_trend[f'{emotion}_trend'] = emotion_trend.get(f'{emotion}_trend', 0) + score

		return emotion_trend

	def get_anna_response_style(self, sentiment_analysis, emotion_analysis):
		"""Get Anna's response style based on sentiment and emotion analysis"""
		try:
			# Base style from sentiment
			base_style = {
				'tone': 'professional',
				'empathy_level': 'moderate',
				'urgency': 'normal',
				'detail_level': 'standard'
			}

			# Adjust based on sentiment
			if sentiment_analysis.get('sentiment_label') == 'negative':
				base_style.update({
					'tone': 'empathetic',
					'empathy_level': 'high',
					'urgency': 'high'
				})
			elif sentiment_analysis.get('sentiment_label') == 'positive':
				base_style.update({
					'tone': 'warm',
					'empathy_level': 'moderate',
					'celebration': True
				})

			# Apply emotion-specific adjustments
			emotion_adjustments = emotion_analysis.get('anna_adjustments', {})
			base_style.update(emotion_adjustments)

			# Add specific Anna personality traits
			base_style.update({
				'personality_traits': ['helpful', 'professional', 'empathetic', 'solution_focused'],
				'communication_style': 'clear_and_supportive',
				'brand_alignment': 'wcfcb_values'
			})

			return base_style

		except Exception as e:
			frappe.log_error(f"Error getting Anna response style: {str(e)}", "SentimentAnalysisService")
			return base_style
