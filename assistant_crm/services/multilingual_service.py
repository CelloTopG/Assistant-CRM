# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from assistant_crm.services.language_detection_service import LanguageDetectionService


class MultilingualService:
	"""Multilingual service for WCFCB CRM responses"""
	
	def __init__(self):
		self.language_service = LanguageDetectionService()
		self.templates = self._load_response_templates()
		self.wcfcb_content = self._load_wcfcb_content()
	
	def get_multilingual_response(self, template_key, language="en", **kwargs):
		"""Get response in specified language"""
		try:
			# Get template for the language
			template = self.templates.get(language, {}).get(template_key)
			
			# Fallback to English if not found
			if not template:
				template = self.templates.get("en", {}).get(template_key, "")
			
			# Format template with provided kwargs
			if template and kwargs:
				try:
					return template.format(**kwargs)
				except KeyError:
					# If formatting fails, return template as is
					return template
			
			return template or ""
			
		except Exception as e:
			frappe.log_error(f"Error getting multilingual response: {str(e)}", "Multilingual Service")
			return self._get_fallback_response(language)
	
	def get_greeting_message(self, language="en", time_of_day="general"):
		"""Get greeting message in specified language"""
		greetings = {
			"en": {
				"morning": "Good morning! Welcome to WCFCB. I'm your AI assistant. How can I help you today?",
				"afternoon": "Good afternoon! Welcome to WCFCB. I'm your AI assistant. How can I help you today?",
				"evening": "Good evening! Welcome to WCFCB. I'm your AI assistant. How can I help you today?",
				"general": "Hello! Welcome to WCFCB. I'm your AI assistant. How can I help you today?"
			},
			"bem": {
				"morning": "Mwabuka bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?",
				"afternoon": "Mwaswela bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?",
				"evening": "Mwabusiku bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?",
				"general": "Muli bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?"
			},
			"ny": {
				"morning": "Mwadzuka bwanji! Takulandirani ku WCFCB. Ndine AI assistant wanu. Kodi ndingakuthandizeni bwanji?",
				"afternoon": "Mwatulo bwanji! Takulandirani ku WCFCB. Ndine AI assistant wanu. Kodi ndingakuthandizeni bwanji?",
				"evening": "Mwausiku bwanji! Takulandirani ku WCFCB. Ndine AI assistant wanu. Kodi ndingakuthandizeni bwanji?",
				"general": "Muli bwanji! Takulandirani ku WCFCB. Ndine AI assistant wanu. Kodi ndingakuthandizeni bwanji?"
			},
			"to": {
				"morning": "Mwabuka bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?",
				"afternoon": "Mwaswela bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?",
				"evening": "Mwabusiku bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?",
				"general": "Muli bwanji! Mwaiseni ku WCFCB. Ndi AI assistant yanu. Nshani nganikwatileni lelo?"
			}
		}
		
		return greetings.get(language, greetings["en"]).get(time_of_day, greetings.get(language, greetings["en"])["general"])
	
	def get_wcfcb_service_info(self, service_type, language="en"):
		"""Get WCFCB service information in specified language"""
		return self.wcfcb_content.get(language, {}).get(service_type, 
			self.wcfcb_content.get("en", {}).get(service_type, ""))
	
	def translate_common_phrases(self, phrase_key, language="en"):
		"""Translate common phrases"""
		common_phrases = {
			"en": {
				"thank_you": "Thank you for contacting WCFCB.",
				"please_wait": "Please wait while I process your request.",
				"how_can_help": "How can I help you today?",
				"need_more_info": "I need more information to assist you better.",
				"escalating": "I'm connecting you with one of our agents who can help you further.",
				"business_hours": "Our office hours are Monday to Friday, 08:00 - 17:00.",
				"contact_info": "You can reach us at +260-211-123456 or email info@wcfcb.gov.zm"
			},
			"bem": {
				"thank_you": "Natotela ukutumine ku WCFCB.",
				"please_wait": "Mulindileni ndeprocess request yenu.",
				"how_can_help": "Nshani nganikwatileni lelo?",
				"need_more_info": "Nfwaya information yama ukuti nkwatile bwino.",
				"escalating": "Naleconnect na umuntu wa ku office uyo akakwatileni bwino.",
				"business_hours": "Ma office hours yetu ni Monday to Friday, 08:00 - 17:00.",
				"contact_info": "Mungafikile pa +260-211-123456 or email info@wcfcb.gov.zm"
			},
			"ny": {
				"thank_you": "Zikomo chifukwa chotitumizira ku WCFCB.",
				"please_wait": "Chonde dikirani ndikukonza pempho lanu.",
				"how_can_help": "Kodi ndingakuthandizeni bwanji lero?",
				"need_more_info": "Ndikufuna zambiri kuti ndikuthandizeni bwino.",
				"escalating": "Ndikukulumikizani ndi mmodzi wa anthu athu amene angakuthandizeni bwino.",
				"business_hours": "Maola athu a ntchito ndi Monday mpaka Friday, 08:00 - 17:00.",
				"contact_info": "Mutha kutifunira pa +260-211-123456 kapena email info@wcfcb.gov.zm"
			},
			"to": {
				"thank_you": "Kea leboha ho re romella ho WCFCB.",
				"please_wait": "Ka kopo ema ha ke sebetsa kopo ya hao.",
				"how_can_help": "Nka u thusa jwang kajeno?",
				"need_more_info": "Ke hloka tlhahisoleseding e eketsehileng ho u thusa hantle.",
				"escalating": "Ke u hokahanya le e mong wa rona ya ka u thusang hantle.",
				"business_hours": "Linako tsa rona tsa mosebetsi ke Monday ho isa Friday, 08:00 - 17:00.",
				"contact_info": "U ka re fihlella ho +260-211-123456 kapa email info@wcfcb.gov.zm"
			}
		}
		
		return common_phrases.get(language, common_phrases["en"]).get(phrase_key, 
			common_phrases["en"].get(phrase_key, ""))
	
	def detect_and_respond(self, message, default_language="en"):
		"""Detect language and provide appropriate response language"""
		try:
			# Detect language from message
			detected_language = self.language_service.detect_language(message)
			
			# Get confidence score
			confidence = self.language_service.get_language_confidence(message, detected_language)
			
			# Get settings
			settings = frappe.get_single("Assistant CRM Settings")
			
			# Check if multilingual is enabled
			if not settings.multilingual_enabled:
				return default_language
			
			# Check confidence threshold
			threshold = settings.language_confidence_threshold or 0.7
			if confidence < threshold and settings.fallback_to_default:
				return settings.default_language or default_language
			
			# Check if detected language is supported
			supported_languages = json.loads(settings.supported_languages or '["en"]')
			if detected_language not in supported_languages:
				return settings.default_language or default_language
			
			return detected_language
			
		except Exception as e:
			frappe.log_error(f"Error in detect_and_respond: {str(e)}", "Multilingual Service")
			return default_language
	
	def _load_response_templates(self):
		"""Load response templates for different languages"""
		return {
			"en": {
				"business_registration_help": "To register your business with WCFCB, you'll need: 1) Certificate of Incorporation, 2) Directors' information, 3) Business plan, 4) Registration fee of K{fee}. Visit our office or call {phone} for assistance.",
				"pension_inquiry": "For pension inquiries, please provide your member number. We can help with benefit statements, contribution history, and retirement planning. Contact us at {phone} or email {email}.",
				"employer_registration": "Employers must register within 30 days of starting operations. Required: Business license, employee list, premium payment. Registration fee: K{fee}. Need help? Call {phone}.",
				"claims_process": "To file a claim: 1) Report incident immediately, 2) Get medical attention, 3) Complete claim forms, 4) Submit supporting documents. Processing time: 30-45 days.",
				"escalation_message": "I'm connecting you with one of our specialists who can provide more detailed assistance with your {query_type} inquiry."
			},
			"bem": {
				"business_registration_help": "Ukusungula business na WCFCB, mufwaikwa: 1) Certificate of Incorporation, 2) Ma directors information, 3) Business plan, 4) Registration fee ya K{fee}. Iseni ku office or call {phone} ukupata assistance.",
				"pension_inquiry": "Pa pension inquiries, peelani member number yenu. Tukakwatileni na benefit statements, contribution history, na retirement planning. Contact us pa {phone} or email {email}.",
				"employer_registration": "Ma employers bafwaikwa ukusungulwa mu masiku 30 ukufuma pakutandila operations. Yafwaikwa: Business license, employee list, premium payment. Registration fee: K{fee}. Mufwaya help? Call {phone}.",
				"claims_process": "Ukufile claim: 1) Report incident nomba, 2) Pata medical attention, 3) Complete claim forms, 4) Submit supporting documents. Processing time: masiku 30-45.",
				"escalation_message": "Naleconnect na umuntu wa specialist uyo akakwatileni bwino na {query_type} inquiry yenu."
			},
			"ny": {
				"business_registration_help": "Kulembetsa bizinesi yanu ku WCFCB, mukufuna: 1) Certificate of Incorporation, 2) Zambiri za ma directors, 3) Business plan, 4) Registration fee ya K{fee}. Bwerani ku office kapena imba {phone} kuti muthandizidwe.",
				"pension_inquiry": "Pa mafunso a pension, perekani member number yanu. Tingakuthandizeni ndi benefit statements, contribution history, ndi retirement planning. Tiyimbirani pa {phone} kapena email {email}.",
				"employer_registration": "Ma employers ayenera kulembetsa m'masiku 30 atayamba ntchito. Zofunikira: Business license, mndandanda wa antchito, premium payment. Registration fee: K{fee}. Mukufuna thandizo? Imba {phone}.",
				"claims_process": "Kutumiza claim: 1) Nenani zomwe zinachitika mwachangu, 2) Pitani ku chipatala, 3) Lembani ma claim forms, 4) Tumizani zotsatira. Nthawi yokonza: masiku 30-45.",
				"escalation_message": "Ndikukulumikizani ndi mmodzi wa akatswiri athu amene angakuthandizeni bwino ndi funso lanu la {query_type}."
			},
			"to": {
				"business_registration_help": "Ho ngodisa kgwebo ya hao ho WCFCB, o hloka: 1) Certificate of Incorporation, 2) Tlhahisoleseding ya ma directors, 3) Business plan, 4) Registration fee ya K{fee}. Etela ofisi kapa letsetsa {phone} bakeng sa thuso.",
				"pension_inquiry": "Bakeng sa dipotso tsa pension, fana ka member number ya hao. Re ka u thusa ka benefit statements, contribution history, le retirement planning. Re letsetse ho {phone} kapa email {email}.",
				"employer_registration": "Bahiri ba tlameha ho ngodiswa matsatsing a 30 kamora ho qala mesebetsi. Ho hlokahala: Business license, lenane la basebetsi, premium payment. Registration fee: K{fee}. O hloka thuso? Letsetsa {phone}.",
				"claims_process": "Ho fayela claim: 1) Tlaleha ketsahalo hang-hang, 2) Fumana tlhokomelo ya bongaka, 3) Tlatsa di-claim forms, 4) Romela litokomane tse tšehetsang. Nako ya ho sebetsa: matsatsi 30-45.",
				"escalation_message": "Ke u hokahanya le e mong wa bo-specialist ba rona ya ka u thusang hantle ka potso ya hao ya {query_type}."
			}
		}
	
	def _load_wcfcb_content(self):
		"""Load WCFCB-specific content in multiple languages"""
		return {
			"en": {
				"business_registration": "WCFCB Business Registration: Register your business for workers' compensation coverage. Required documents: Certificate of Incorporation, business plan, directors' information. Processing time: 14 days.",
				"pension_services": "WCFCB Pension Services: Comprehensive retirement planning, benefit calculations, contribution tracking, and payout management for all registered members.",
				"employer_registration": "Employer Registration: All employers must register for workers' compensation insurance. Coverage protects employees and ensures compliance with labor laws.",
				"claims_processing": "Claims Processing: File workplace injury claims, track status, submit medical reports. Our team ensures fair and timely compensation for eligible claims."
			},
			"bem": {
				"business_registration": "WCFCB Business Registration: Sungulani business yenu ukupata workers' compensation coverage. Ma documents yafwaikwa: Certificate of Incorporation, business plan, directors' information. Processing time: masiku 14.",
				"pension_services": "WCFCB Pension Services: Comprehensive retirement planning, benefit calculations, contribution tracking, na payout management ya bonse abasungulwa.",
				"employer_registration": "Employer Registration: Bonse employers bafwaikwa ukusungulwa pa workers' compensation insurance. Coverage yaprotect employees na ensure compliance na labor laws.",
				"claims_processing": "Claims Processing: File workplace injury claims, track status, submit medical reports. Team yetu inaensure fair na timely compensation ya eligible claims."
			},
			"ny": {
				"business_registration": "WCFCB Business Registration: Lembetsani bizinesi yanu kuti mupeze workers' compensation coverage. Zolemba zofunikira: Certificate of Incorporation, business plan, zambiri za ma directors. Nthawi yokonza: masiku 14.",
				"pension_services": "WCFCB Pension Services: Comprehensive retirement planning, benefit calculations, contribution tracking, ndi payout management ya onse olembetsidwa.",
				"employer_registration": "Employer Registration: Onse olemba anthu ayenera kulembetsa pa workers' compensation insurance. Coverage imateteza antchito ndikuonetsetsa kutsatira malamulo a ntchito.",
				"claims_processing": "Claims Processing: Tumizani ma workplace injury claims, track status, tumizani medical reports. Gulu lathu limaonetsetsa chilango choyenera ndi cha nthawi ya eligible claims."
			},
			"to": {
				"business_registration": "WCFCB Business Registration: Ngodisa kgwebo ya hao ho fumana workers' compensation coverage. Litokomane tse hlokahalang: Certificate of Incorporation, business plan, tlhahisoleseding ya ma directors. Nako ya ho sebetsa: matsatsi 14.",
				"pension_services": "WCFCB Pension Services: Comprehensive retirement planning, benefit calculations, contribution tracking, le payout management ya bohle ba ngodisitsweng.",
				"employer_registration": "Employer Registration: Bahiri bohle ba tlameha ho ngodiswa bakeng sa workers' compensation insurance. Coverage e sireletsa basebetsi mme e netefatsa ho latela melao ya basebetsi.",
				"claims_processing": "Claims Processing: Fayela ma workplace injury claims, track status, romela medical reports. Sehlopha sa rona se netefatsa tefo e nepahetseng le ea nako ya eligible claims."
			}
		}
	
	def _get_fallback_response(self, language="en"):
		"""Get fallback response when translation fails"""
		fallbacks = {
			"en": "I apologize for any language difficulties. Please contact WCFCB at +260-211-123456 for assistance.",
			"bem": "Ndeelomba pantu kuli language difficulties. Please contact WCFCB pa +260-211-123456 ukupata assistance.",
			"ny": "Pepani chifukwa cha zovuta za chilankhulo. Chonde contact WCFCB pa +260-211-123456 kuti muthandizidwe.",
			"to": "Ke kopa tshwarelo ka mathata a puo. Ka kopo contact WCFCB ho +260-211-123456 bakeng sa thuso."
		}
		
		return fallbacks.get(language, fallbacks["en"])
	
	def get_supported_languages(self):
		"""Get list of supported languages"""
		return {
			"en": "English",
			"bem": "Bemba",
			"ny": "Nyanja",
			"to": "Tonga"
		}
	
	def is_language_supported(self, language_code):
		"""Check if language is supported"""
		return language_code in self.get_supported_languages()
	
	def get_faq_no_match_message(self, language='en'):
		"""Get message when no FAQ matches are found"""
		messages = {
			'en': "I couldn't find a specific answer to your question. Let me connect you with a human agent who can help you better.",
			'bem': "Nshilafwaya icakufwaya. Nga nkwafye umuntu uyo angakwafya bwino.",
			'ny': "Sindinapeze yankho lenileni ku funso lanu. Ndilumikizeni ndi munthu amene angakuthandizeni bwino.",
			'to': "Takwe ndakazwide cakufuuna. Nga ndikuunganisye amuntu uyo angakubwezye bwino."
		}
		return messages.get(language, messages['en'])

	def get_confidence_message(self, language='en', confidence=0):
		"""Get message about confidence level"""
		if confidence > 0.8:
			messages = {
				'en': "I'm confident this answer will help you.",
				'bem': "Ndi confident ici cakakwafya.",
				'ny': "Ndikutsimikiza kuti yankho ili likuthandizani.",
				'to': "Ke tshepa hore karabo ena e tla u thusa."
			}
		elif confidence > 0.6:
			messages = {
				'en': "This might help answer your question.",
				'bem': "Ici cingakwafya ukuyankhula icifwaya cenu.",
				'ny': "Izi zingakuthandizeni kuyankha funso lanu.",
				'to': "Sena se ka thusa ho araba potso ya hao."
			}
		else:
			messages = {
				'en': "I found some information that might be relevant.",
				'bem': "Nafwaya information iyo ingaba relevant.",
				'ny': "Ndapeza zambiri zomwe zingakhale zofunikira.",
				'to': "Ke fumane tlhahisoleseding e ka bang ea bohlokoa."
			}

		return messages.get(language, messages['en'])

	def translate_content(self, content, target_language, source_language='en'):
		"""Translate content to target language"""
		if target_language == source_language:
			return content

		# For now, return content as-is since we don't have full translation
		# In a production system, this would integrate with translation APIs
		return content

	def get_language_name(self, language_code):
		"""Get language name from code"""
		language_names = {
			'en': 'English',
			'bem': 'Bemba',
			'ny': 'Nyanja',
			'to': 'Tonga'
		}
		return language_names.get(language_code, language_code)

	@staticmethod
	def get_time_of_day():
		"""Get current time of day for appropriate greetings"""
		from frappe.utils import now_datetime

		current_hour = now_datetime().hour

		if 5 <= current_hour < 12:
			return "morning"
		elif 12 <= current_hour < 17:
			return "afternoon"
		elif 17 <= current_hour < 22:
			return "evening"
		else:
			return "general"
