#!/usr/bin/env python3

import frappe
from frappe import _
import json
from datetime import datetime, timedelta

def create_trending_analysis_api():
    """Create API for trending query analysis"""
    
    trending_api_code = '''
@frappe.whitelist()
def analyze_query_trends(period="30", category=None):
    """Analyze query trends and patterns"""
    
    try:
        conditions = []
        if category:
            conditions.append(f"query_category = '{category}'")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get trending queries
        trending_queries = frappe.db.sql(f"""
            SELECT 
                query_category,
                COUNT(*) as query_count,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(confidence_score) as avg_confidence,
                DATE(creation) as query_date
            FROM `tabAI Response Feedback`
            WHERE {where_clause}
            AND creation >= DATE_SUB(NOW(), INTERVAL {period} DAY)
            GROUP BY query_category, DATE(creation)
            ORDER BY query_date DESC, query_count DESC
        """, as_dict=True)
        
        # Get emerging topics
        emerging_topics = frappe.db.sql(f"""
            SELECT 
                query_category,
                COUNT(*) as recent_count,
                (
                    SELECT COUNT(*) 
                    FROM `tabAI Response Feedback` f2 
                    WHERE f2.query_category = f1.query_category
                    AND f2.creation >= DATE_SUB(NOW(), INTERVAL {int(period)*2} DAY)
                    AND f2.creation < DATE_SUB(NOW(), INTERVAL {period} DAY)
                ) as previous_count
            FROM `tabAI Response Feedback` f1
            WHERE {where_clause}
            AND creation >= DATE_SUB(NOW(), INTERVAL {period} DAY)
            GROUP BY query_category
            HAVING recent_count > previous_count * 1.5
            ORDER BY (recent_count - previous_count) DESC
        """, as_dict=True)
        
        # Calculate growth rates
        for topic in emerging_topics:
            if topic['previous_count'] > 0:
                topic['growth_rate'] = ((topic['recent_count'] - topic['previous_count']) / topic['previous_count']) * 100
            else:
                topic['growth_rate'] = 100  # New topic
        
        # Get seasonal patterns
        seasonal_patterns = analyze_seasonal_patterns(period)
        
        return {
            "status": "success",
            "trending_queries": trending_queries,
            "emerging_topics": emerging_topics,
            "seasonal_patterns": seasonal_patterns
        }
        
    except Exception as e:
        frappe.log_error(f"Trend analysis error: {str(e)}", "Trend Analysis")
        return {"status": "error", "message": "Failed to analyze trends"}

def analyze_seasonal_patterns(period):
    """Analyze seasonal query patterns"""
    
    try:
        # Get hourly patterns
        hourly_patterns = frappe.db.sql(f"""
            SELECT 
                HOUR(creation) as hour,
                COUNT(*) as query_count,
                AVG(confidence_score) as avg_confidence
            FROM `tabAI Response Feedback`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL {period} DAY)
            GROUP BY HOUR(creation)
            ORDER BY hour
        """, as_dict=True)
        
        # Get daily patterns
        daily_patterns = frappe.db.sql(f"""
            SELECT 
                DAYOFWEEK(creation) as day_of_week,
                COUNT(*) as query_count,
                AVG(confidence_score) as avg_confidence
            FROM `tabAI Response Feedback`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL {period} DAY)
            GROUP BY DAYOFWEEK(creation)
            ORDER BY day_of_week
        """, as_dict=True)
        
        return {
            "hourly_patterns": hourly_patterns,
            "daily_patterns": daily_patterns
        }
        
    except Exception as e:
        frappe.log_error(f"Seasonal pattern analysis error: {str(e)}", "Seasonal Analysis")
        return {}

@frappe.whitelist()
def detect_new_query_patterns():
    """Detect new query patterns that exceed thresholds"""
    
    try:
        # Get recent query patterns
        recent_patterns = frappe.db.sql("""
            SELECT 
                query_category,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(confidence_score) as avg_confidence
            FROM `tabAI Response Feedback`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY query_category
            HAVING count >= 10  -- Threshold for pattern detection
            ORDER BY count DESC
        """, as_dict=True)
        
        alerts = []
        
        for pattern in recent_patterns:
            # Check if this is a new pattern or significant increase
            historical_count = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabAI Response Feedback`
                WHERE query_category = %s
                AND creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                AND creation < DATE_SUB(NOW(), INTERVAL 7 DAY)
            """, (pattern['query_category'],), as_dict=True)
            
            historical = historical_count[0]['count'] if historical_count else 0
            
            # Create alert if significant increase
            if pattern['count'] > historical * 2:  # 100% increase threshold
                alerts.append({
                    "category": pattern['query_category'],
                    "current_count": pattern['count'],
                    "historical_count": historical,
                    "growth_rate": ((pattern['count'] - historical) / max(historical, 1)) * 100,
                    "unique_users": pattern['unique_users'],
                    "avg_confidence": pattern['avg_confidence'],
                    "alert_type": "significant_increase"
                })
        
        # Create pattern analysis records for new patterns
        for alert in alerts:
            create_or_update_pattern_analysis(alert)
        
        return {
            "status": "success",
            "alerts": alerts,
            "patterns_detected": len(alerts)
        }
        
    except Exception as e:
        frappe.log_error(f"Pattern detection error: {str(e)}", "Pattern Detection")
        return {"status": "error", "message": "Failed to detect patterns"}

def create_or_update_pattern_analysis(alert):
    """Create or update query pattern analysis record"""
    
    try:
        pattern_name = f"pattern-{alert['category']}-trending"
        
        existing_pattern = frappe.db.exists("Query Pattern Analysis", {"name": pattern_name})
        
        if existing_pattern:
            pattern = frappe.get_doc("Query Pattern Analysis", existing_pattern)
            pattern.query_count = alert['current_count']
            pattern.unique_users = alert['unique_users']
            pattern.last_occurrence = frappe.utils.now()
            pattern.growth_rate = alert['growth_rate']
            pattern.trend_direction = "increasing"
            pattern.average_confidence = alert['avg_confidence']
        else:
            pattern = frappe.new_doc("Query Pattern Analysis")
            pattern.name = pattern_name
            pattern.pattern_text = f"Trending queries in {alert['category']}"
            pattern.pattern_category = alert['category']
            pattern.query_count = alert['current_count']
            pattern.unique_users = alert['unique_users']
            pattern.first_occurrence = frappe.utils.add_days(frappe.utils.now(), -7)
            pattern.last_occurrence = frappe.utils.now()
            pattern.trend_direction = "increasing"
            pattern.growth_rate = alert['growth_rate']
            pattern.average_confidence = alert['avg_confidence']
        
        # Calculate business impact and recommendations
        pattern.business_impact_score = calculate_business_impact_score(alert)
        pattern.recommended_action = generate_recommended_action(alert)
        
        pattern.save()
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Pattern analysis creation error: {str(e)}", "Pattern Analysis Creation")

def calculate_business_impact_score(alert):
    """Calculate business impact score for trending pattern"""
    
    base_score = 50
    
    # Volume factor
    volume_score = min(alert['current_count'] * 2, 30)
    
    # Growth rate factor
    growth_score = min(alert['growth_rate'] / 10, 20)
    
    # User diversity factor
    user_diversity = min(alert['unique_users'] * 3, 15)
    
    # Category importance
    category_importance = {
        'claims': 20, 'contributions': 18, 'registration': 15,
        'beneficiary': 17, 'policy': 12, 'technical': 10, 'general': 8
    }
    category_score = category_importance.get(alert['category'], 8)
    
    # Confidence factor (lower confidence = higher impact)
    confidence_factor = (1 - alert['avg_confidence']) * 10
    
    total_score = base_score + volume_score + growth_score + user_diversity + category_score + confidence_factor
    
    return min(total_score, 100)

def generate_recommended_action(alert):
    """Generate recommended action for trending pattern"""
    
    if alert['growth_rate'] > 200:
        return "Urgent: Create comprehensive knowledge base content"
    elif alert['growth_rate'] > 100:
        return "High Priority: Develop targeted FAQ and articles"
    elif alert['avg_confidence'] < 0.7:
        return "Medium Priority: Improve existing content quality"
    else:
        return "Monitor: Track pattern development"
'''
    
    # Write trending API to file
    trending_file = "development/frappe-bench/apps/assistant_crm/assistant_crm/api/trending_analysis.py"
    try:
        with open(trending_file, 'w') as f:
            f.write('#!/usr/bin/env python3\n\nimport frappe\nfrom frappe import _\nimport json\nfrom datetime import datetime, timedelta\n\n')
            f.write(trending_api_code)
        print("✅ Trending analysis API created")
    except Exception as e:
        print(f"⚠️  Error creating trending analysis API: {str(e)}")

def create_trend_detection_system():
    """Create automated trend detection system"""
    
    detection_code = '''
def run_automated_trend_detection():
    """Run automated trend detection (called by scheduler)"""
    
    try:
        # Detect new patterns
        pattern_results = detect_new_query_patterns()
        
        # Generate knowledge base suggestions
        suggestions = generate_knowledge_base_suggestions()
        
        # Update learning metrics
        update_trend_learning_metrics()
        
        # Send alerts if needed
        send_trend_alerts(pattern_results, suggestions)
        
        return {
            "status": "success",
            "patterns_detected": len(pattern_results.get('alerts', [])),
            "suggestions_generated": len(suggestions.get('suggestions', []))
        }
        
    except Exception as e:
        frappe.log_error(f"Automated trend detection error: {str(e)}", "Automated Trend Detection")
        return {"status": "error", "message": str(e)}

def generate_knowledge_base_suggestions():
    """Generate suggestions for new knowledge base articles"""
    
    try:
        # Get high-impact trending patterns
        trending_patterns = frappe.db.sql("""
            SELECT 
                pattern_category,
                pattern_text,
                query_count,
                business_impact_score,
                recommended_action
            FROM `tabQuery Pattern Analysis`
            WHERE trend_direction = 'increasing'
            AND business_impact_score >= 70
            AND last_occurrence >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY business_impact_score DESC
            LIMIT 10
        """, as_dict=True)
        
        suggestions = []
        
        for pattern in trending_patterns:
            # Get sample queries for this pattern
            sample_queries = frappe.db.sql("""
                SELECT query_text
                FROM `tabAI Response Feedback`
                WHERE query_category = %s
                AND creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY creation DESC
                LIMIT 5
            """, (pattern['pattern_category'],), as_dict=True)
            
            suggestion = {
                "category": pattern['pattern_category'],
                "title": f"FAQ: {pattern['pattern_category'].title()} Questions",
                "priority": "high" if pattern['business_impact_score'] >= 85 else "medium",
                "impact_score": pattern['business_impact_score'],
                "query_volume": pattern['query_count'],
                "sample_queries": [q['query_text'] for q in sample_queries],
                "recommended_action": pattern['recommended_action'],
                "suggested_content_type": determine_content_type(pattern)
            }
            
            suggestions.append(suggestion)
        
        return {"status": "success", "suggestions": suggestions}
        
    except Exception as e:
        frappe.log_error(f"Knowledge base suggestions error: {str(e)}", "KB Suggestions")
        return {"status": "error", "suggestions": []}

def determine_content_type(pattern):
    """Determine the best content type for a pattern"""
    
    if pattern['query_count'] > 50:
        return "comprehensive_guide"
    elif pattern['business_impact_score'] > 80:
        return "detailed_faq"
    else:
        return "quick_reference"

def update_trend_learning_metrics():
    """Update learning metrics related to trends"""
    
    try:
        today = frappe.utils.today()
        
        # Pattern detection rate
        patterns_detected = frappe.db.count("Query Pattern Analysis", {
            "creation": [">=", today]
        })
        
        create_learning_metric("pattern_detection_rate", patterns_detected, "count", today)
        
        # Trend accuracy (patterns that led to successful content creation)
        successful_patterns = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabQuery Pattern Analysis`
            WHERE action_taken IS NOT NULL
            AND effectiveness_score >= 70
            AND creation >= %s
        """, (today,), as_dict=True)
        
        accuracy = successful_patterns[0]['count'] if successful_patterns else 0
        create_learning_metric("trend_prediction_accuracy", accuracy, "percentage", today)
        
        # Knowledge gap resolution rate
        resolved_gaps = frappe.db.count("Knowledge Gap Analysis", {
            "status": "resolved",
            "modified": [">=", today]
        })
        
        create_learning_metric("knowledge_gap_resolution_rate", resolved_gaps, "count", today)
        
    except Exception as e:
        frappe.log_error(f"Trend metrics update error: {str(e)}", "Trend Metrics")

def create_learning_metric(metric_type, value, unit, date):
    """Create a learning metric record"""
    
    try:
        metric = frappe.new_doc("Learning Metrics")
        metric.metric_date = date
        metric.metric_type = metric_type
        metric.metric_category = "trending_analysis"
        metric.metric_value = value
        metric.metric_unit = unit
        metric.data_source = "automated_trend_detection"
        metric.quality_score = 85  # Default quality score for automated metrics
        
        metric.insert()
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Learning metric creation error: {str(e)}", "Learning Metrics")
'''
    
    # Write detection system to file
    detection_file = "development/frappe-bench/apps/assistant_crm/assistant_crm/api/trend_detection.py"
    try:
        with open(detection_file, 'w') as f:
            f.write('#!/usr/bin/env python3\n\nimport frappe\nfrom frappe import _\nimport json\nfrom datetime import datetime, timedelta\n\n')
            f.write(detection_code)
        print("✅ Trend detection system created")
    except Exception as e:
        print(f"⚠️  Error creating trend detection system: {str(e)}")

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    print("🚀 Advanced Continuous Learning Components Ready!")
