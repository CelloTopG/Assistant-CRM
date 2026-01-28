# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
import re
from frappe import _


class ResponseModeDetector:
	"""Service to detect whether user wants direct data or instructions"""
	
	def __init__(self):
		self.user = frappe.session.user
	
	def detect_response_mode(self, query):
		"""
		Detect if user wants direct data retrieval or instructions
		
		Returns:
			dict: {
				"mode": "direct_data" | "instructions" | "mixed",
				"confidence": float (0-1),
				"data_type": "employee" | "budget" | "project" | "general",
				"override_detected": bool,
				"reasoning": str
			}
		"""
		try:
			query_lower = query.lower().strip()
			
			# Check for explicit user preference override
			override_detected = self._detect_user_override(query_lower)
			
			# Analyze query patterns
			direct_data_indicators = self._analyze_direct_data_patterns(query_lower)
			instruction_indicators = self._analyze_instruction_patterns(query_lower)
			
			# Determine data type
			data_type = self._determine_data_type(query_lower)
			
			# Calculate confidence and mode
			mode_result = self._calculate_mode_and_confidence(
				direct_data_indicators, 
				instruction_indicators, 
				override_detected
			)
			
			return {
				"mode": mode_result["mode"],
				"confidence": mode_result["confidence"],
				"data_type": data_type,
				"override_detected": override_detected,
				"reasoning": mode_result["reasoning"],
				"direct_indicators": direct_data_indicators,
				"instruction_indicators": instruction_indicators
			}
			
		except Exception as e:
			frappe.log_error(f"Error detecting response mode: {str(e)}", "Response Mode Detector")
			return {
				"mode": "instructions",
				"confidence": 0.5,
				"data_type": "general",
				"override_detected": False,
				"reasoning": "Error in detection, defaulting to instructions"
			}
	
	def _detect_user_override(self, query):
		"""Detect explicit user preference for data vs instructions"""
		override_patterns = [
			# User explicitly wants data, not instructions
			r"(?:no|don't|dont)\s+(?:want|need|give me)\s+(?:instructions|steps|how to)",
			r"just\s+(?:give me|show me|tell me)\s+(?:the|actual)\s+(?:data|information|answer)",
			r"(?:directly|straight)\s+(?:give|show|tell)",
			r"(?:skip|without)\s+(?:the\s+)?(?:instructions|steps|tutorial)",
			r"(?:actual|real)\s+(?:data|information|answer|result)",
			r"(?:quick|immediate)\s+(?:answer|result|data)",
			
			# User explicitly wants instructions
			r"(?:how\s+(?:do|can)\s+i|show me how to|teach me|guide me)",
			r"(?:steps|instructions|tutorial|walkthrough)",
			r"(?:where\s+(?:do|can)\s+i\s+find|how\s+to\s+(?:find|access|locate))",
			r"(?:explain|show me the process|walk me through)"
		]
		
		data_override_patterns = override_patterns[:6]
		instruction_override_patterns = override_patterns[6:]
		
		# Check for data override
		for pattern in data_override_patterns:
			if re.search(pattern, query, re.IGNORECASE):
				return "force_data"
		
		# Check for instruction override
		for pattern in instruction_override_patterns:
			if re.search(pattern, query, re.IGNORECASE):
				return "force_instructions"
		
		return False
	
	def _analyze_direct_data_patterns(self, query):
		"""Analyze patterns that indicate user wants direct data"""
		patterns = {
			# Question words asking for specific information
			"specific_questions": [
				r"what\s+is\s+\w+(?:'s)?\s+(?:position|id|employee|designation|department|salary)",
				r"what\s+(?:position|role|job|title)\s+(?:does|is)\s+\w+",
				r"who\s+is\s+(?:the\s+)?(?:manager|supervisor|head)\s+of",
				r"what\s+(?:department|team|division)\s+(?:does|is)\s+\w+",
				r"when\s+(?:did|does)\s+\w+\s+(?:join|start|begin)",
				r"how\s+much\s+(?:budget|money|amount)\s+(?:is|do we have|remains?)",
				r"what\s+(?:budget|amount|allocation)\s+(?:do we have|is allocated)"
			],
			
			# Direct information requests
			"direct_requests": [
				r"(?:show|give|tell)\s+me\s+(?:the\s+)?(?:details|information|data)\s+(?:about|for|of)",
				r"(?:display|list|provide)\s+(?:the\s+)?(?:details|information|data)",
				r"i\s+(?:want|need)\s+(?:to\s+(?:know|see|get))\s+(?:the\s+)?(?:details|information|data)",
				r"(?:get|fetch|retrieve)\s+(?:the\s+)?(?:details|information|data)"
			],
			
			# Specific data point requests
			"data_point_requests": [
				r"(?:employee\s+)?id\s+(?:of|for)\s+\w+",
				r"\w+(?:'s)?\s+(?:id|employee\s+id|emp\s+id)",
				r"(?:budget\s+)?(?:amount|allocation)\s+(?:for|of)\s+\w+",
				r"(?:remaining|left)\s+(?:budget|amount|money)",
				r"(?:current|total)\s+(?:budget|spending|expenses?)",
				r"(?:status|progress)\s+(?:of|for)\s+(?:project|task)\s+\w+"
			],
			
			# Possessive and specific entity queries
			"entity_specific": [
				r"\w+(?:'s)\s+(?:position|role|job|title|department|manager|salary|id)",
				r"(?:project|budget|employee|department)\s+\w+(?:'s)?\s+(?:status|details|information)",
				r"(?:details|information|data)\s+(?:about|for|of)\s+(?:employee|project|budget)\s+\w+"
			]
		}
		
		indicators = {"total_score": 0, "matches": []}
		
		for category, pattern_list in patterns.items():
			for pattern in pattern_list:
				matches = re.findall(pattern, query, re.IGNORECASE)
				if matches:
					score = len(matches) * self._get_pattern_weight(category)
					indicators["total_score"] += score
					indicators["matches"].append({
						"category": category,
						"pattern": pattern,
						"matches": matches,
						"score": score
					})
		
		return indicators
	
	def _analyze_instruction_patterns(self, query):
		"""Analyze patterns that indicate user wants instructions"""
		patterns = {
			# How-to questions
			"how_to_questions": [
				r"how\s+(?:do|can)\s+i\s+(?:find|get|access|see|view|check)",
				r"how\s+to\s+(?:find|get|access|see|view|check|locate)",
				r"where\s+(?:do|can)\s+i\s+(?:find|get|access|see|view)",
				r"where\s+is\s+(?:the\s+)?(?:employee|budget|project)\s+(?:information|data|details)"
			],
			
			# Process/procedure requests
			"process_requests": [
				r"(?:show|tell|explain)\s+me\s+how\s+to",
				r"(?:steps|process|procedure|method)\s+(?:to|for)",
				r"(?:guide|walk)\s+me\s+through",
				r"(?:tutorial|instructions)\s+(?:on|for|to)"
			],
			
			# Learning/guidance requests
			"learning_requests": [
				r"(?:teach|show|explain)\s+me\s+(?:how|the way)",
				r"i\s+(?:don't\s+know|need\s+to\s+learn)\s+how\s+to",
				r"(?:help|assist)\s+me\s+(?:with|to)",
				r"(?:guidance|direction)\s+(?:on|for|about)"
			],
			
			# Navigation/location requests
			"navigation_requests": [
				r"where\s+(?:do|can)\s+i\s+(?:go|navigate|click)",
				r"which\s+(?:menu|module|section|page)",
				r"(?:navigate|go)\s+to\s+(?:the\s+)?(?:employee|budget|project)",
				r"(?:access|reach)\s+(?:the\s+)?(?:employee|budget|project)\s+(?:section|module|page)"
			]
		}
		
		indicators = {"total_score": 0, "matches": []}
		
		for category, pattern_list in patterns.items():
			for pattern in pattern_list:
				matches = re.findall(pattern, query, re.IGNORECASE)
				if matches:
					score = len(matches) * self._get_pattern_weight(category)
					indicators["total_score"] += score
					indicators["matches"].append({
						"category": category,
						"pattern": pattern,
						"matches": matches,
						"score": score
					})
		
		return indicators
	
	def _get_pattern_weight(self, category):
		"""Get weight for different pattern categories"""
		weights = {
			# Direct data patterns
			"specific_questions": 3.0,
			"direct_requests": 2.5,
			"data_point_requests": 3.5,
			"entity_specific": 3.0,
			
			# Instruction patterns
			"how_to_questions": 3.0,
			"process_requests": 2.5,
			"learning_requests": 2.0,
			"navigation_requests": 2.5
		}
		
		return weights.get(category, 1.0)
	
	def _determine_data_type(self, query):
		"""Determine what type of data the user is asking about"""
		data_type_patterns = {
			"employee": [
				r"employee|staff|colleague|worker|person|team member",
				r"position|designation|role|job|title",
				r"department|manager|supervisor|reports to",
				r"salary|compensation|pay|wage",
				r"joining|start date|hire date"
			],
			"budget": [
				r"budget|allocation|funding|money|amount",
				r"spending|expenses?|expenditure|cost",
				r"remaining|left|balance|available",
				r"utilization|used|spent|consumed"
			],
			"project": [
				r"project|task|initiative|work",
				r"status|progress|completion|percent",
				r"timeline|schedule|dates|deadline",
				r"team|members|assigned|resources"
			],
			"financial": [
				r"financial|accounting|finance|fiscal",
				r"revenue|income|profit|loss",
				r"kpi|metrics|performance|indicators"
			]
		}
		
		scores = {}
		for data_type, patterns in data_type_patterns.items():
			score = 0
			for pattern in patterns:
				matches = len(re.findall(pattern, query, re.IGNORECASE))
				score += matches
			scores[data_type] = score
		
		# Return the data type with highest score, or "general" if no clear winner
		if max(scores.values()) > 0:
			return max(scores, key=scores.get)
		else:
			return "general"
	
	def _calculate_mode_and_confidence(self, direct_indicators, instruction_indicators, override):
		"""Calculate the response mode and confidence level"""
		# Handle explicit overrides first
		if override == "force_data":
			return {
				"mode": "direct_data",
				"confidence": 0.95,
				"reasoning": "User explicitly requested data instead of instructions"
			}
		elif override == "force_instructions":
			return {
				"mode": "instructions",
				"confidence": 0.95,
				"reasoning": "User explicitly requested instructions"
			}
		
		# Calculate scores
		direct_score = direct_indicators["total_score"]
		instruction_score = instruction_indicators["total_score"]
		total_score = direct_score + instruction_score
		
		# Determine mode based on scores
		if total_score == 0:
			return {
				"mode": "instructions",
				"confidence": 0.5,
				"reasoning": "No clear indicators found, defaulting to instructions"
			}
		
		# Calculate confidence based on score difference
		score_difference = abs(direct_score - instruction_score)
		confidence = min(0.95, 0.6 + (score_difference / max(total_score, 1)) * 0.35)
		
		if direct_score > instruction_score:
			mode = "direct_data"
			reasoning = f"Direct data indicators stronger (score: {direct_score} vs {instruction_score})"
		elif instruction_score > direct_score:
			mode = "instructions"
			reasoning = f"Instruction indicators stronger (score: {instruction_score} vs {direct_score})"
		else:
			mode = "mixed"
			reasoning = f"Equal indicators (score: {direct_score} vs {instruction_score})"
			confidence = 0.5
		
		return {
			"mode": mode,
			"confidence": confidence,
			"reasoning": reasoning
		}
	
	def should_provide_direct_data(self, query):
		"""Simple method to determine if direct data should be provided"""
		mode_result = self.detect_response_mode(query)
		
		# Provide direct data if:
		# 1. Mode is explicitly direct_data with high confidence
		# 2. User override detected for data
		# 3. Mixed mode but with data type that's easily retrievable
		
		if mode_result["mode"] == "direct_data" and mode_result["confidence"] > 0.7:
			return True
		elif mode_result["override_detected"] == "force_data":
			return True
		elif (mode_result["mode"] == "mixed" and 
			  mode_result["data_type"] in ["employee", "budget", "project"] and
			  mode_result["confidence"] > 0.6):
			return True
		
		return False
