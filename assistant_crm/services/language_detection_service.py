# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _


class LanguageDetectionService:
	"""Language detection service for WCFCB multilingual support"""
	
	def __init__(self):
		self.language_patterns = self._load_language_patterns()
		self.common_words = self._load_common_words()
		self.greeting_patterns = self._load_greeting_patterns()
	
	def detect_language(self, text):
		"""Detect language from text message"""
		try:
			if not text or not isinstance(text, str):
				return "en"  # Default to English
			
			# Clean text
			cleaned_text = self._clean_text(text)
			if not cleaned_text:
				return "en"
			
			# Check greeting patterns first (most reliable)
			greeting_lang = self._detect_by_greetings(cleaned_text)
			if greeting_lang:
				return greeting_lang
			
			# Check common words
			word_lang = self._detect_by_common_words(cleaned_text)
			if word_lang:
				return word_lang
			
			# Check character patterns
			pattern_lang = self._detect_by_patterns(cleaned_text)
			if pattern_lang:
				return pattern_lang
			
			# Default to English if no clear detection
			return "en"
			
		except Exception as e:
			frappe.log_error(f"Error in language detection: {str(e)}", "Language Detection Service")
			return "en"
	
	def get_language_confidence(self, text, detected_language):
		"""Get confidence score for detected language"""
		try:
			if not text:
				return 0.0
			
			cleaned_text = self._clean_text(text)
			words = cleaned_text.split()
			
			if not words:
				return 0.0
			
			# Count matches for detected language
			matches = 0
			total_words = len(words)
			
			# Check common words
			common_words = self.common_words.get(detected_language, set())
			for word in words:
				if word.lower() in common_words:
					matches += 1
			
			# Check greeting patterns
			greeting_patterns = self.greeting_patterns.get(detected_language, [])
			for pattern in greeting_patterns:
				if pattern in cleaned_text.lower():
					matches += 2  # Greetings are more reliable
			
			# Calculate confidence
			confidence = min(matches / total_words, 1.0) if total_words > 0 else 0.0
			
			return round(confidence, 2)
			
		except Exception as e:
			frappe.log_error(f"Error calculating language confidence: {str(e)}", "Language Detection Service")
			return 0.0
	
	def _clean_text(self, text):
		"""Clean text for language detection"""
		# Remove URLs, emails, phone numbers
		text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
		text = re.sub(r'\S+@\S+', '', text)
		text = re.sub(r'[\+]?[1-9]?[0-9]{7,15}', '', text)
		
		# Remove excessive punctuation but keep basic structure
		text = re.sub(r'[^\w\s\.\!\?]', ' ', text)
		text = re.sub(r'\s+', ' ', text)
		
		return text.strip()
	
	def _detect_by_greetings(self, text):
		"""Detect language by greeting patterns"""
		text_lower = text.lower()
		
		# Score each language based on greeting matches
		language_scores = {}
		
		for lang, patterns in self.greeting_patterns.items():
			score = 0
			for pattern in patterns:
				if pattern in text_lower:
					score += 2  # High weight for greetings
			language_scores[lang] = score
		
		# Return language with highest score
		if language_scores:
			max_lang = max(language_scores, key=language_scores.get)
			if language_scores[max_lang] > 0:
				return max_lang
		
		return None
	
	def _detect_by_common_words(self, text):
		"""Detect language by common words"""
		words = text.lower().split()
		language_scores = {}
		
		for lang, common_words in self.common_words.items():
			score = 0
			for word in words:
				if word in common_words:
					score += 1
			language_scores[lang] = score
		
		# Return language with highest score (minimum threshold)
		if language_scores:
			max_lang = max(language_scores, key=language_scores.get)
			if language_scores[max_lang] >= 2:  # At least 2 common words
				return max_lang
		
		return None
	
	def _detect_by_patterns(self, text):
		"""Detect language by character patterns"""
		text_lower = text.lower()
		
		for lang, patterns in self.language_patterns.items():
			matches = 0
			for pattern in patterns:
				matches += len(re.findall(pattern, text_lower))
			
			# If significant pattern matches, return language
			if matches >= 3:
				return lang
		
		return None
	
	def _load_greeting_patterns(self):
		"""Load greeting patterns for each language"""
		return {
			"en": [
				"hello", "hi", "hey", "good morning", "good afternoon", 
				"good evening", "greetings", "howdy", "what's up"
			],
			"bem": [
				"muli bwanji", "mulishani", "mwabuka bwanji", "mwaswela bwanji",
				"muli", "bwanji", "mulibwanji", "mwaiseni", "mwabombeni"
			],
			"ny": [
				"muli bwanji", "mulibwanji", "mwadzuka bwanji", "mwatulo bwanji",
				"moni", "bwanji", "takulandirani", "mwabwera bwanji"
			],
			"to": [
				"muli bwanji", "mulibwanji", "mwabuka bwanji", "mwaswela bwanji",
				"muli", "bwanji", "mwaiseni", "mwabombeni", "mwatondezya"
			]
		}
	
	def _load_common_words(self):
		"""Load common words for each language"""
		return {
			"en": {
				"the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
				"with", "by", "from", "about", "into", "through", "during",
				"before", "after", "above", "below", "up", "down", "out", "off",
				"over", "under", "again", "further", "then", "once", "here",
				"there", "when", "where", "why", "how", "all", "any", "both",
				"each", "few", "more", "most", "other", "some", "such", "no",
				"nor", "not", "only", "own", "same", "so", "than", "too", "very",
				"can", "will", "just", "should", "now", "business", "registration",
				"pension", "employer", "claim", "help", "need", "want", "please",
				"thank", "thanks", "sorry", "yes", "no"
			},
			"bem": {
				"na", "ne", "pa", "ku", "mu", "nga", "ukuti", "ati", "kuti",
				"uko", "umo", "apo", "pano", "nomba", "lelo", "mailo", "cindi",
				"bantu", "umuntu", "abantu", "icibi", "icisuma", "ukufwaya",
				"ukupenda", "ukutemwa", "ukusuma", "ukuya", "ukufika", "ukubwela",
				"bwino", "sana", "pantu", "naimwe", "ine", "iwe", "uyu", "aba",
				"business", "ukusungula", "pension", "employer", "claim",
				"ndeelomba", "natotela", "asante", "eya", "awe", "tabu"
			},
			"ny": {
				"ndi", "pa", "ku", "mu", "kuti", "koma", "kapena", "ngati",
				"pamene", "pano", "lero", "mawa", "dzulo", "anthu", "munthu",
				"choipa", "chabwino", "kufuna", "kukonda", "kutamanda", "kupita",
				"kubwera", "kufika", "bwino", "kwambiri", "chifukwa", "inu",
				"ine", "iwe", "uyu", "awa", "business", "kulembetsa", "pension",
				"employer", "claim", "chonde", "zikomo", "pepani", "inde", "ayi"
			},
			"to": {
				"a", "na", "ku", "mu", "pa", "kuti", "pele", "hape", "jwale",
				"hosasa", "maabane", "batho", "motho", "mobe", "molemo", "ho batla",
				"ho rata", "ho leboha", "ho ya", "ho tla", "ho fihla", "hantle",
				"haholo", "hobane", "lona", "nna", "wena", "enwa", "bana",
				"business", "ho ngodisa", "pension", "employer", "claim",
				"ka kopo", "kea leboha", "tshwarelo", "ee", "che"
			}
		}
	
	def _load_language_patterns(self):
		"""Load regex patterns for each language"""
		return {
			"bem": [
				r'\buku\w+',  # Bemba infinitive prefix
				r'\baba\w+',  # Bemba plural prefix
				r'\bici\w+',  # Bemba noun prefix
				r'\bumu\w+',  # Bemba noun prefix
				r'wa\b',      # Bemba possessive
				r'nga\b'      # Bemba conditional
			],
			"ny": [
				r'\bku\w+',   # Nyanja infinitive prefix
				r'\ba\w+',    # Nyanja plural prefix
				r'\bchi\w+',  # Nyanja noun prefix
				r'\bmu\w+',   # Nyanja noun prefix
				r'wa\b',      # Nyanja possessive
				r'ngati\b'    # Nyanja conditional
			],
			"to": [
				r'\bho\w+',   # Tonga infinitive prefix
				r'\bba\w+',   # Tonga plural prefix
				r'\bse\w+',   # Tonga noun prefix
				r'\bmo\w+',   # Tonga noun prefix
				r'wa\b',      # Tonga possessive
				r'haeba\b'    # Tonga conditional
			]
		}
	
	def get_supported_languages(self):
		"""Get list of supported languages"""
		return {
			"en": "English",
			"bem": "Bemba",
			"ny": "Nyanja", 
			"to": "Tonga"
		}
	
	def translate_language_code(self, code):
		"""Translate language code to full name"""
		languages = self.get_supported_languages()
		return languages.get(code, "English")
	
	def is_supported_language(self, language_code):
		"""Check if language is supported"""
		return language_code in self.get_supported_languages()
	
	def get_default_language(self):
		"""Get default language"""
		return "en"
	
	def detect_mixed_language(self, text):
		"""Detect if text contains multiple languages"""
		try:
			if not text:
				return False
			
			cleaned_text = self._clean_text(text)
			words = cleaned_text.split()
			
			if len(words) < 4:  # Too short to be mixed
				return False
			
			# Check for words from different languages
			language_matches = {}
			
			for lang, common_words in self.common_words.items():
				matches = 0
				for word in words:
					if word.lower() in common_words:
						matches += 1
				if matches > 0:
					language_matches[lang] = matches
			
			# If more than one language has significant matches, it's mixed
			significant_languages = [lang for lang, count in language_matches.items() if count >= 2]
			
			return len(significant_languages) > 1
			
		except Exception as e:
			frappe.log_error(f"Error detecting mixed language: {str(e)}", "Language Detection Service")
			return False
