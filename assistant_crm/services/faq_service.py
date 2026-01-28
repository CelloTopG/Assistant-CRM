# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
import json
from difflib import SequenceMatcher
import math


class FAQService:
    """FAQ matching service for automated responses

    Note: Knowledge Base Article doctype has been deprecated.
    This service now returns empty results as a placeholder.
    """

    def __init__(self):
        self.confidence_threshold = 0.7
        self.articles = []
        # Knowledge Base Article doctype has been removed
        # Skip loading knowledge base as it no longer exists

    def load_knowledge_base(self):
        """Load knowledge base articles and keywords

        Note: Knowledge Base Article doctype has been deprecated.
        This method now does nothing.
        """
        # Knowledge Base Article doctype has been removed
        self.articles = []
    
    def get_article_keywords(self, article_name):
        """Get keywords for a specific article"""
        try:
            keywords = frappe.db.sql("""
                SELECT keyword, weight
                FROM `tabArticle Keyword`
                WHERE parent = %s
                ORDER BY weight DESC
            """, (article_name,), as_dict=True)
            return keywords
        except:
            return []
    
    def process_keywords(self, keywords):
        """Process keywords for matching"""
        processed = []
        for kw in keywords:
            processed.append({
                'keyword': kw['keyword'].lower().strip(),
                'weight': kw.get('weight', 1.0)
            })
        return processed
    
    def find_best_match(self, user_message, language='en', context=None):
        """Find best matching FAQ article"""
        if not self.articles:
            self.load_knowledge_base()
        
        user_tokens = self.preprocess_message(user_message)
        best_match = None
        best_score = 0
        
        # Filter articles by language
        language_articles = [a for a in self.articles if a['language'] == language]
        if not language_articles and language != 'en':
            # Fallback to English if no articles in requested language
            language_articles = [a for a in self.articles if a['language'] == 'en']
        
        for article in language_articles:
            # Calculate similarity score
            score = self.calculate_similarity(user_tokens, article, user_message)
            
            # Apply article-specific confidence threshold
            threshold = article.get('confidence_threshold', self.confidence_threshold)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = article
        
        return best_match, best_score
    
    def preprocess_message(self, message):
        """Preprocess user message for matching"""
        # Convert to lowercase and remove punctuation
        message = re.sub(r'[^\w\s]', '', message.lower())
        
        # Tokenize and filter short words
        tokens = [word for word in message.split() if len(word) > 2]
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
            'did', 'she', 'use', 'way', 'will', 'with', 'what', 'when', 'where',
            'why', 'this', 'that', 'they', 'them', 'there', 'their', 'then'
        }
        
        tokens = [token for token in tokens if token not in stop_words]
        return tokens
    
    def calculate_similarity(self, user_tokens, article, original_message):
        """Calculate similarity between user message and article"""
        # Title similarity (40% weight)
        title_tokens = self.preprocess_message(article['title'])
        title_score = self.token_similarity(user_tokens, title_tokens) * 0.4
        
        # Keyword similarity (50% weight)
        keyword_score = self.keyword_similarity(user_tokens, article['processed_keywords']) * 0.5
        
        # Content similarity (10% weight) - for exact phrase matching
        content_score = self.content_similarity(original_message, article['content']) * 0.1
        
        total_score = title_score + keyword_score + content_score
        
        # Boost score based on article effectiveness
        effectiveness_boost = (article.get('effectiveness_score', 0) / 10)  # Small boost
        
        return min(total_score + effectiveness_boost, 1.0)  # Cap at 1.0
    
    def token_similarity(self, tokens1, tokens2):
        """Calculate token-based similarity using Jaccard similarity"""
        if not tokens1 or not tokens2:
            return 0
        
        set1 = set(tokens1)
        set2 = set(tokens2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0
    
    def keyword_similarity(self, user_tokens, article_keywords):
        """Calculate weighted keyword similarity"""
        if not article_keywords:
            return 0
        
        total_weight = sum(kw['weight'] for kw in article_keywords)
        matched_weight = 0
        
        for keyword_data in article_keywords:
            keyword = keyword_data['keyword']
            weight = keyword_data['weight']
            
            # Check for exact keyword match
            if keyword in user_tokens:
                matched_weight += weight
            else:
                # Check for partial matches
                for token in user_tokens:
                    if keyword in token or token in keyword:
                        matched_weight += weight * 0.5  # Partial match gets half weight
                        break
        
        return matched_weight / total_weight if total_weight > 0 else 0
    
    def content_similarity(self, user_message, article_content):
        """Check for exact phrase matches in content"""
        if not article_content:
            return 0
        
        # Remove HTML tags from content
        clean_content = re.sub(r'<[^>]+>', '', article_content).lower()
        user_lower = user_message.lower()
        
        # Look for exact phrase matches (3+ words)
        user_phrases = self.extract_phrases(user_lower, min_length=3)
        
        for phrase in user_phrases:
            if phrase in clean_content:
                return 0.8  # High score for exact phrase match
        
        return 0
    
    def extract_phrases(self, text, min_length=3):
        """Extract phrases of minimum length from text"""
        words = text.split()
        phrases = []
        
        for i in range(len(words) - min_length + 1):
            phrase = ' '.join(words[i:i + min_length])
            phrases.append(phrase)
        
        return phrases
    
    def get_auto_response(self, user_message, language='en', context=None):
        """Generate automatic response based on FAQ matching"""
        try:
            best_match, confidence = self.find_best_match(user_message, language, context)
            
            if best_match:
                # Update usage statistics
                self.update_article_usage(best_match['name'])
                
                # Get quick replies
                quick_replies = self.get_quick_replies(best_match['name'])
                
                response = {
                    'success': True,
                    'response': best_match['content'],
                    'confidence': confidence,
                    'article_id': best_match['name'],
                    'article_title': best_match['title'],
                    'category': best_match['category'],
                    'is_automated': True,
                    'source': 'knowledge_base'
                }
                
                if quick_replies:
                    response['quick_replies'] = quick_replies
                
                return response
            else:
                return {
                    'success': False,
                    'confidence': 0,
                    'escalate': True,
                    'message': self.get_no_match_message(language),
                    'source': 'faq_service'
                }
                
        except Exception as e:
            frappe.log_error(f"Error in FAQ auto response: {str(e)}", "FAQ Service")
            return {
                'success': False,
                'error': str(e),
                'message': 'I encountered an error while searching for an answer. Please try again.'
            }
    
    def get_no_match_message(self, language='en'):
        """Get no match message in specified language"""
        messages = {
            'en': "I couldn't find a specific answer to your question. Let me connect you with a human agent who can help you better.",
            'bem': "Nshilafwaya icakufwaya. Nga nkwafye umuntu uyo angakwafya bwino.",
            'ny': "Sindinapeze yankho lenileni ku funso lanu. Ndilumikizeni ndi munthu amene angakuthandizeni bwino.",
            'to': "Takwe ndakazwide cakufuuna. Nga ndikuunganisye amuntu uyo angakubwezye bwino."
        }
        return messages.get(language, messages['en'])
    
    def update_article_usage(self, article_name):
        """Update article usage statistics

        Note: Knowledge Base Article doctype has been deprecated.
        This method now does nothing.
        """
        # Knowledge Base Article doctype has been removed
        pass
    
    def get_quick_replies(self, article_name):
        """Get quick reply options for article"""
        try:
            return frappe.db.sql("""
                SELECT reply_text, action_type, action_value
                FROM `tabQuick Reply Option`
                WHERE parent = %s
                ORDER BY idx
            """, (article_name,), as_dict=True)
        except:
            return []


@frappe.whitelist()
def test_article_match(article_name, test_message):
    """Test API endpoint for article matching

    Note: Knowledge Base Article doctype has been deprecated.
    This endpoint now returns an error.
    """
    # Knowledge Base Article doctype has been removed
    frappe.throw(_("Knowledge Base Article doctype has been deprecated"))


@frappe.whitelist()
def extract_keywords(title, content):
    """Extract keywords from title and content"""
    try:
        # Combine title and content
        text = f"{title} {content}"
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
            'did', 'she', 'use', 'way', 'will', 'with'
        }
        
        # Get unique keywords, filter stop words and short words
        keywords = list(set([word for word in words if word not in stop_words and len(word) > 3]))
        
        # Sort by length (longer words might be more specific)
        keywords.sort(key=len, reverse=True)
        
        return keywords[:15]  # Return top 15 keywords
        
    except Exception as e:
        frappe.log_error(f"Error extracting keywords: {str(e)}", "FAQ Service")
        return []
