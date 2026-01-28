import frappe
from frappe import _
from datetime import datetime, timedelta
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from assistant_crm.services.performance_tracking_service import PerformanceTrackingService


class PredictiveAnalyticsService:
    """Advanced predictive analytics engine for WCFCB customer insights and operational forecasting"""
    
    def __init__(self):
        self.performance_tracker = PerformanceTrackingService()
        self.prediction_models = self.load_prediction_models()
        self.analytics_cache = {}
    
    def load_prediction_models(self) -> Dict[str, Any]:
        """Load prediction model configurations"""
        return {
            'churn_prediction': {
                'features': [
                    'days_since_last_interaction',
                    'total_interactions',
                    'negative_sentiment_ratio',
                    'escalation_count',
                    'resolution_time_avg',
                    'payment_delays',
                    'compliance_issues'
                ],
                'weights': {
                    'days_since_last_interaction': 0.25,
                    'negative_sentiment_ratio': 0.20,
                    'escalation_count': 0.15,
                    'payment_delays': 0.15,
                    'compliance_issues': 0.10,
                    'resolution_time_avg': 0.10,
                    'total_interactions': 0.05
                },
                'thresholds': {
                    'high_risk': 0.7,
                    'medium_risk': 0.4,
                    'low_risk': 0.2
                }
            },
            'volume_forecasting': {
                'seasonal_factors': {
                    'monday': 1.2,
                    'tuesday': 1.1,
                    'wednesday': 1.0,
                    'thursday': 1.1,
                    'friday': 1.3,
                    'saturday': 0.6,
                    'sunday': 0.4
                },
                'monthly_factors': {
                    1: 1.1,  # January - New year inquiries
                    2: 0.9,  # February
                    3: 1.2,  # March - End of quarter
                    4: 1.0,  # April
                    5: 1.0,  # May
                    6: 1.3,  # June - Mid year
                    7: 1.1,  # July
                    8: 1.0,  # August
                    9: 1.2,  # September - End of quarter
                    10: 1.0, # October
                    11: 1.1, # November
                    12: 1.4  # December - Year end
                },
                'trend_window_days': 30
            }
        }
    
    def predict_customer_churn(self, customer_id: str = None, limit: int = 100) -> Dict[str, Any]:
        """Predict customer churn risk using interaction patterns and behavior analysis"""
        try:
            if customer_id:
                # Predict for specific customer
                customers = [{'customer_id': customer_id}]
            else:
                # Get all active customers for batch prediction
                customers = self.get_active_customers(limit)
            
            churn_predictions = []
            
            for customer in customers:
                try:
                    # Extract customer features
                    features = self.extract_customer_features(customer['customer_id'])
                    
                    # Calculate churn probability
                    churn_probability = self.calculate_churn_probability(features)
                    
                    # Determine risk level
                    risk_level = self.determine_risk_level(churn_probability)
                    
                    # Generate recommendations
                    recommendations = self.generate_churn_prevention_recommendations(features, risk_level)
                    
                    prediction = {
                        'customer_id': customer['customer_id'],
                        'churn_probability': round(churn_probability, 3),
                        'risk_level': risk_level,
                        'features': features,
                        'recommendations': recommendations,
                        'prediction_date': frappe.utils.today()
                    }
                    
                    churn_predictions.append(prediction)
                    
                except Exception as e:
                    frappe.log_error(f"Error predicting churn for customer {customer['customer_id']}: {str(e)}")
                    continue
            
            # Sort by churn probability (highest first)
            churn_predictions.sort(key=lambda x: x['churn_probability'], reverse=True)
            
            # Calculate summary statistics
            summary = self.calculate_churn_summary(churn_predictions)
            
            return {
                'success': True,
                'predictions': churn_predictions,
                'summary': summary,
                'total_customers_analyzed': len(churn_predictions),
                'analysis_date': frappe.utils.now()
            }
            
        except Exception as e:
            frappe.log_error(f"Error in customer churn prediction: {str(e)}", "Predictive Analytics")
            return {
                'success': False,
                'error': str(e),
                'predictions': []
            }
    
    def forecast_conversation_volume(self, forecast_days: int = 30) -> Dict[str, Any]:
        """Forecast conversation volume for capacity planning"""
        try:
            # Get historical conversation data
            historical_data = self.get_historical_conversation_data(90)  # 90 days of history
            
            if not historical_data:
                return {
                    'success': False,
                    'error': 'Insufficient historical data for forecasting',
                    'forecast': []
                }
            
            # Calculate base trends
            base_trend = self.calculate_base_trend(historical_data)
            
            # Generate forecast
            forecast_data = []
            today = datetime.now().date()
            
            for i in range(forecast_days):
                forecast_date = today + timedelta(days=i)
                
                # Apply seasonal factors
                seasonal_volume = self.apply_seasonal_factors(base_trend, forecast_date)
                
                # Apply trend adjustments
                trend_adjusted_volume = self.apply_trend_adjustments(seasonal_volume, i, historical_data)
                
                # Calculate confidence intervals
                confidence_intervals = self.calculate_confidence_intervals(trend_adjusted_volume, i)
                
                forecast_entry = {
                    'date': forecast_date.strftime('%Y-%m-%d'),
                    'predicted_volume': round(trend_adjusted_volume),
                    'confidence_low': round(confidence_intervals['low']),
                    'confidence_high': round(confidence_intervals['high']),
                    'day_of_week': forecast_date.strftime('%A').lower(),
                    'month': forecast_date.month
                }
                
                forecast_data.append(forecast_entry)
            
            # Calculate capacity recommendations
            capacity_recommendations = self.generate_capacity_recommendations(forecast_data)
            
            return {
                'success': True,
                'forecast': forecast_data,
                'capacity_recommendations': capacity_recommendations,
                'forecast_period_days': forecast_days,
                'historical_data_points': len(historical_data),
                'forecast_generated': frappe.utils.now()
            }
            
        except Exception as e:
            frappe.log_error(f"Error in conversation volume forecasting: {str(e)}", "Predictive Analytics")
            return {
                'success': False,
                'error': str(e),
                'forecast': []
            }
    
    def generate_operational_insights(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive operational insights and recommendations"""
        try:
            end_date = frappe.utils.today()
            start_date = frappe.utils.add_days(end_date, -period_days)
            
            # Get performance trends
            performance_trends = self.analyze_performance_trends(start_date, end_date)
            
            # Get efficiency insights
            efficiency_insights = self.analyze_efficiency_patterns(start_date, end_date)
            
            # Get customer satisfaction trends
            satisfaction_trends = self.analyze_satisfaction_trends(start_date, end_date)
            
            # Get resource utilization insights
            resource_insights = self.analyze_resource_utilization(start_date, end_date)
            
            # Generate actionable recommendations
            recommendations = self.generate_operational_recommendations(
                performance_trends, efficiency_insights, satisfaction_trends, resource_insights
            )
            
            return {
                'success': True,
                'analysis_period': {'start': start_date, 'end': end_date},
                'performance_trends': performance_trends,
                'efficiency_insights': efficiency_insights,
                'satisfaction_trends': satisfaction_trends,
                'resource_insights': resource_insights,
                'recommendations': recommendations,
                'insights_generated': frappe.utils.now()
            }
            
        except Exception as e:
            frappe.log_error(f"Error generating operational insights: {str(e)}", "Predictive Analytics")
            return {
                'success': False,
                'error': str(e),
                'insights': {}
            }
    
    def get_active_customers(self, limit: int) -> List[Dict[str, Any]]:
        """Get list of active customers for analysis"""
        try:
            customers = frappe.db.sql("""
                SELECT DISTINCT sender_id as customer_id
                FROM `tabMessage`
                WHERE creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                AND sender_id IS NOT NULL
                ORDER BY MAX(creation) DESC
                LIMIT %s
            """, (limit,), as_dict=True)
            
            return customers
            
        except Exception as e:
            frappe.log_error(f"Error getting active customers: {str(e)}")
            return []
    
    def extract_customer_features(self, customer_id: str) -> Dict[str, float]:
        """Extract features for churn prediction model"""
        try:
            # Get customer interaction data
            interaction_data = frappe.db.sql("""
                SELECT 
                    COUNT(*) as total_interactions,
                    MAX(creation) as last_interaction,
                    AVG(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) as negative_sentiment_ratio,
                    SUM(CASE WHEN escalated = 1 THEN 1 ELSE 0 END) as escalation_count,
                    AVG(TIMESTAMPDIFF(HOUR, creation, resolved_time)) as avg_resolution_hours
                FROM `tabMessage`
                WHERE sender_id = %s
                AND creation >= DATE_SUB(NOW(), INTERVAL 180 DAY)
            """, (customer_id,), as_dict=True)
            
            if not interaction_data or not interaction_data[0]['total_interactions']:
                return self.get_default_features()
            
            data = interaction_data[0]
            
            # Calculate days since last interaction
            if data['last_interaction']:
                last_interaction = data['last_interaction']
                days_since_last = (datetime.now() - last_interaction).days
            else:
                days_since_last = 180  # Max value if no interactions
            
            # Get payment and compliance data (simulated for now)
            payment_delays = self.get_customer_payment_delays(customer_id)
            compliance_issues = self.get_customer_compliance_issues(customer_id)
            
            features = {
                'days_since_last_interaction': min(days_since_last, 180),
                'total_interactions': min(data['total_interactions'] or 0, 100),
                'negative_sentiment_ratio': data['negative_sentiment_ratio'] or 0,
                'escalation_count': min(data['escalation_count'] or 0, 10),
                'resolution_time_avg': min(data['avg_resolution_hours'] or 24, 168),  # Cap at 1 week
                'payment_delays': payment_delays,
                'compliance_issues': compliance_issues
            }
            
            return features
            
        except Exception as e:
            frappe.log_error(f"Error extracting customer features: {str(e)}")
            return self.get_default_features()
    
    def get_default_features(self) -> Dict[str, float]:
        """Get default feature values for new customers"""
        return {
            'days_since_last_interaction': 30,
            'total_interactions': 1,
            'negative_sentiment_ratio': 0.1,
            'escalation_count': 0,
            'resolution_time_avg': 24,
            'payment_delays': 0,
            'compliance_issues': 0
        }
    
    def calculate_churn_probability(self, features: Dict[str, float]) -> float:
        """Calculate churn probability using weighted feature model"""
        try:
            model = self.prediction_models['churn_prediction']
            weights = model['weights']
            
            # Normalize features to 0-1 scale
            normalized_features = self.normalize_features(features)
            
            # Calculate weighted score
            churn_score = 0.0
            for feature, value in normalized_features.items():
                if feature in weights:
                    churn_score += value * weights[feature]
            
            # Apply sigmoid function to get probability
            churn_probability = 1 / (1 + math.exp(-5 * (churn_score - 0.5)))
            
            return min(max(churn_probability, 0.0), 1.0)
            
        except Exception as e:
            frappe.log_error(f"Error calculating churn probability: {str(e)}")
            return 0.5  # Default medium risk

    def normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Normalize features to 0-1 scale for model input"""
        try:
            # Define normalization ranges for each feature
            normalization_ranges = {
                'days_since_last_interaction': (0, 180),  # 0-180 days
                'total_interactions': (0, 100),           # 0-100 interactions
                'negative_sentiment_ratio': (0, 1),       # Already 0-1
                'escalation_count': (0, 10),              # 0-10 escalations
                'resolution_time_avg': (0, 168),          # 0-168 hours (1 week)
                'payment_delays': (0, 5),                 # 0-5 delays
                'compliance_issues': (0, 3)               # 0-3 issues
            }

            normalized = {}
            for feature, value in features.items():
                if feature in normalization_ranges:
                    min_val, max_val = normalization_ranges[feature]
                    # Normalize to 0-1 range
                    normalized[feature] = min(max((value - min_val) / (max_val - min_val), 0), 1)
                else:
                    normalized[feature] = value

            return normalized

        except Exception as e:
            frappe.log_error(f"Error normalizing features: {str(e)}")
            return features

    def determine_risk_level(self, churn_probability: float) -> str:
        """Determine risk level based on churn probability"""
        thresholds = self.prediction_models['churn_prediction']['thresholds']

        if churn_probability >= thresholds['high_risk']:
            return 'High'
        elif churn_probability >= thresholds['medium_risk']:
            return 'Medium'
        else:
            return 'Low'

    def generate_churn_prevention_recommendations(self, features: Dict[str, float], risk_level: str) -> List[str]:
        """Generate personalized churn prevention recommendations"""
        recommendations = []

        try:
            if features['days_since_last_interaction'] > 30:
                recommendations.append("Proactive outreach - Customer hasn't interacted recently")

            if features['negative_sentiment_ratio'] > 0.3:
                recommendations.append("Sentiment improvement - Address customer satisfaction issues")

            if features['escalation_count'] > 2:
                recommendations.append("Escalation review - Investigate recurring issues")

            if features['resolution_time_avg'] > 48:
                recommendations.append("Response time improvement - Reduce resolution delays")

            if features['payment_delays'] > 1:
                recommendations.append("Payment support - Offer payment assistance or reminders")

            if features['compliance_issues'] > 0:
                recommendations.append("Compliance assistance - Provide guidance on requirements")

            if risk_level == 'High':
                recommendations.append("Priority attention - Assign dedicated account manager")
                recommendations.append("Immediate follow-up - Contact within 24 hours")

            if not recommendations:
                recommendations.append("Maintain engagement - Continue regular communication")

            return recommendations

        except Exception as e:
            frappe.log_error(f"Error generating churn prevention recommendations: {str(e)}")
            return ["Review customer account and provide personalized support"]

    def calculate_churn_summary(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for churn predictions"""
        try:
            if not predictions:
                return {
                    'total_customers': 0,
                    'high_risk_count': 0,
                    'medium_risk_count': 0,
                    'low_risk_count': 0,
                    'avg_churn_probability': 0
                }

            high_risk = sum(1 for p in predictions if p['risk_level'] == 'High')
            medium_risk = sum(1 for p in predictions if p['risk_level'] == 'Medium')
            low_risk = sum(1 for p in predictions if p['risk_level'] == 'Low')
            avg_probability = sum(p['churn_probability'] for p in predictions) / len(predictions)

            return {
                'total_customers': len(predictions),
                'high_risk_count': high_risk,
                'medium_risk_count': medium_risk,
                'low_risk_count': low_risk,
                'high_risk_percentage': round((high_risk / len(predictions)) * 100, 1),
                'medium_risk_percentage': round((medium_risk / len(predictions)) * 100, 1),
                'low_risk_percentage': round((low_risk / len(predictions)) * 100, 1),
                'avg_churn_probability': round(avg_probability, 3)
            }

        except Exception as e:
            frappe.log_error(f"Error calculating churn summary: {str(e)}")
            return {'total_customers': 0}

    def get_customer_payment_delays(self, customer_id: str) -> int:
        """Get number of payment delays for customer (simulated)"""
        try:
            # This would integrate with actual payment system
            # For now, return simulated data based on customer activity
            delays = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabMessage`
                WHERE sender_id = %s
                AND message_content LIKE '%payment%'
                AND message_content LIKE '%overdue%'
                AND creation >= DATE_SUB(NOW(), INTERVAL 180 DAY)
            """, (customer_id,), as_dict=True)

            return min(delays[0]['count'] if delays else 0, 5)

        except Exception as e:
            frappe.log_error(f"Error getting payment delays: {str(e)}")
            return 0

    def get_customer_compliance_issues(self, customer_id: str) -> int:
        """Get number of compliance issues for customer (simulated)"""
        try:
            # This would integrate with actual compliance system
            # For now, return simulated data based on customer activity
            issues = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabMessage`
                WHERE sender_id = %s
                AND (message_content LIKE '%compliance%' OR message_content LIKE '%violation%')
                AND creation >= DATE_SUB(NOW(), INTERVAL 180 DAY)
            """, (customer_id,), as_dict=True)

            return min(issues[0]['count'] if issues else 0, 3)

        except Exception as e:
            frappe.log_error(f"Error getting compliance issues: {str(e)}")
            return 0

    def get_historical_conversation_data(self, days: int) -> List[Dict[str, Any]]:
        """Get historical conversation volume data"""
        try:
            end_date = frappe.utils.today()
            start_date = frappe.utils.add_days(end_date, -days)

            data = frappe.db.sql("""
                SELECT
                    DATE(creation) as date,
                    COUNT(*) as conversation_count,
                    DAYOFWEEK(creation) as day_of_week,
                    MONTH(creation) as month
                FROM `tabMessage`
                WHERE DATE(creation) BETWEEN %s AND %s
                GROUP BY DATE(creation)
                ORDER BY date
            """, (start_date, end_date), as_dict=True)

            return data

        except Exception as e:
            frappe.log_error(f"Error getting historical conversation data: {str(e)}")
            return []

    def calculate_base_trend(self, historical_data: List[Dict[str, Any]]) -> float:
        """Calculate base trend from historical data"""
        try:
            if not historical_data:
                return 50  # Default base volume

            # Calculate average daily volume
            total_conversations = sum(d['conversation_count'] for d in historical_data)
            avg_daily_volume = total_conversations / len(historical_data)

            return avg_daily_volume

        except Exception as e:
            frappe.log_error(f"Error calculating base trend: {str(e)}")
            return 50

    def apply_seasonal_factors(self, base_volume: float, forecast_date: datetime.date) -> float:
        """Apply seasonal factors to base volume"""
        try:
            model = self.prediction_models['volume_forecasting']

            # Apply day of week factor
            day_name = forecast_date.strftime('%A').lower()
            day_factor = model['seasonal_factors'].get(day_name, 1.0)

            # Apply monthly factor
            month_factor = model['monthly_factors'].get(forecast_date.month, 1.0)

            # Combine factors
            seasonal_volume = base_volume * day_factor * month_factor

            return seasonal_volume

        except Exception as e:
            frappe.log_error(f"Error applying seasonal factors: {str(e)}")
            return base_volume
