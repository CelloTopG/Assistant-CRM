#!/usr/bin/env python3

import frappe
from frappe import _
import json
from datetime import datetime, timedelta

def setup_ml_integration():
    """Setup machine learning integration system"""
    
    print("\n🤖 Setting up ML Integration System...")
    
    # Create ML training data pipeline
    create_ml_training_pipeline()
    
    # Setup A/B testing framework
    create_ab_testing_framework()
    
    # Create model performance tracking
    create_model_performance_tracking()
    
    print("✅ ML Integration System setup completed!")

def create_ml_training_pipeline():
    """Create ML training data pipeline"""
    
    ml_pipeline_code = '''
@frappe.whitelist()
def collect_ml_training_data(interaction_id, user_query, ai_response, user_feedback,
                            feedback_score, context_features=None, response_features=None,
                            confidence_score=None, response_time=None, knowledge_articles_used=None,
                            user_type=None, query_category=None, session_context=None):
    """Collect data for ML model training - ML Training Data doctype has been deprecated"""

    # ML Training Data doctype has been removed
    # Return success to avoid breaking callers
    return {
        "status": "deprecated",
        "message": "ML Training Data collection has been deprecated"
    }

def determine_outcome_label(user_feedback, feedback_score, confidence_score):
    """Determine the outcome label for ML training"""
    
    if user_feedback == "yes" and feedback_score >= 4:
        return "highly_successful"
    elif user_feedback == "yes" and feedback_score >= 3:
        return "successful"
    elif user_feedback == "partially" or feedback_score == 2:
        return "partially_successful"
    elif user_feedback == "no" or feedback_score <= 1:
        return "unsuccessful"
    elif confidence_score and confidence_score < 0.5:
        return "low_confidence"
    else:
        return "neutral"

def calculate_training_weight(training_data):
    """Calculate training weight based on data characteristics"""
    
    base_weight = 1.0
    
    # Quality factor
    quality_factor = (training_data.data_quality_score or 50) / 100
    
    # Feedback reliability factor
    feedback_weights = {
        "highly_successful": 1.2,
        "successful": 1.0,
        "partially_successful": 0.8,
        "unsuccessful": 1.1,  # Negative examples are valuable
        "low_confidence": 0.6,
        "neutral": 0.5
    }
    feedback_weight = feedback_weights.get(training_data.outcome_label, 1.0)
    
    # Category importance factor
    category_weights = {
        "claims": 1.2, "contributions": 1.1, "registration": 1.0,
        "beneficiary": 1.1, "policy": 0.9, "technical": 0.8, "general": 0.7
    }
    category_weight = category_weights.get(training_data.query_category, 1.0)
    
    # User type factor
    user_weights = {
        "employer": 1.1, "beneficiary": 1.2, "agent": 1.0, "unknown": 0.8
    }
    user_weight = user_weights.get(training_data.user_type, 1.0)
    
    final_weight = base_weight * quality_factor * feedback_weight * category_weight * user_weight
    
    return min(max(final_weight, 0.1), 2.0)  # Clamp between 0.1 and 2.0

def assess_data_quality(training_data):
    """Assess the quality of training data"""
    
    quality_score = 100
    
    # Check for missing critical fields
    if not training_data.user_query:
        quality_score -= 30
    if not training_data.ai_response:
        quality_score -= 30
    if not training_data.user_feedback:
        quality_score -= 20
    
    # Check query length (too short or too long may be low quality)
    if training_data.user_query:
        query_length = len(training_data.user_query.split())
        if query_length < 3:
            quality_score -= 15
        elif query_length > 100:
            quality_score -= 10
    
    # Check response length
    if training_data.ai_response:
        response_length = len(training_data.ai_response.split())
        if response_length < 5:
            quality_score -= 10
        elif response_length > 500:
            quality_score -= 5
    
    # Check confidence score consistency
    if training_data.confidence_score and training_data.user_feedback:
        if training_data.confidence_score > 0.8 and training_data.user_feedback == "no":
            quality_score -= 15  # Inconsistent data
        elif training_data.confidence_score < 0.3 and training_data.user_feedback == "yes":
            quality_score -= 15  # Inconsistent data
    
    # Bonus for rich context
    if training_data.context_features:
        quality_score += 5
    if training_data.response_features:
        quality_score += 5
    if training_data.knowledge_articles_used:
        quality_score += 5
    
    return max(quality_score, 0)

def check_training_batch_threshold():
    """Check if training batch threshold is reached - deprecated"""
    # ML Training Data doctype has been removed
    pass

def create_training_batch():
    """Create a new training batch - deprecated"""
    # ML Training Data doctype has been removed
    pass

@frappe.whitelist()
def get_training_data_export(batch_id=None, format="json"):
    """Export training data for ML model training - deprecated"""
    # ML Training Data doctype has been removed
    return {
        "status": "deprecated",
        "message": "ML Training Data export has been deprecated",
        "data": [],
        "record_count": 0
    }

@frappe.whitelist()
def update_model_performance(model_version, performance_metrics, validation_results=None):
    """Update model performance metrics"""
    
    try:
        # Create performance record
        performance = frappe.new_doc("Model Performance")
        performance.model_version = model_version
        performance.evaluation_date = frappe.utils.today()
        performance.performance_metrics = json.dumps(performance_metrics)
        performance.validation_results = json.dumps(validation_results) if validation_results else None
        
        # Extract key metrics
        if isinstance(performance_metrics, dict):
            performance.accuracy = performance_metrics.get('accuracy')
            performance.precision = performance_metrics.get('precision')
            performance.recall = performance_metrics.get('recall')
            performance.f1_score = performance_metrics.get('f1_score')
            performance.confidence_correlation = performance_metrics.get('confidence_correlation')
        
        performance.insert()
        frappe.db.commit()
        
        # Update learning metrics
        create_model_learning_metrics(model_version, performance_metrics)
        
        return {
            "status": "success",
            "performance_id": performance.name,
            "model_version": model_version
        }
        
    except Exception as e:
        frappe.log_error(f"Model performance update error: {str(e)}", "Model Performance")
        return {"status": "error", "message": "Failed to update model performance"}

def create_model_learning_metrics(model_version, metrics):
    """Create learning metrics from model performance"""
    
    try:
        today = frappe.utils.today()
        
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                metric = frappe.new_doc("Learning Metrics")
                metric.metric_date = today
                metric.metric_type = f"model_{metric_name}"
                metric.metric_category = "ml_performance"
                metric.metric_value = value
                metric.metric_unit = "score" if metric_name in ['accuracy', 'precision', 'recall', 'f1_score'] else "value"
                metric.data_source = f"model_{model_version}"
                metric.quality_score = 95  # High quality for model metrics
                
                metric.insert()
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Model learning metrics error: {str(e)}", "Model Learning Metrics")
'''
    
    # Write ML pipeline to file
    ml_file = "development/frappe-bench/apps/assistant_crm/assistant_crm/api/ml_training_pipeline.py"
    try:
        with open(ml_file, 'w') as f:
            f.write('#!/usr/bin/env python3\n\nimport frappe\nfrom frappe import _\nimport json\nfrom datetime import datetime, timedelta\n\n')
            f.write(ml_pipeline_code)
        print("✅ ML training pipeline created")
    except Exception as e:
        print(f"⚠️  Error creating ML pipeline: {str(e)}")

def create_ab_testing_framework():
    """Create A/B testing framework for knowledge base improvements"""

    ab_testing_code = '''
@frappe.whitelist()
def create_ab_test(test_name, description, test_type, control_version, test_version,
                   target_metric, success_criteria, duration_days=30, traffic_split=50):
    """Create a new A/B test for knowledge base improvements"""

    try:
        # Create A/B test record
        ab_test = frappe.new_doc("AB Test")
        ab_test.test_name = test_name
        ab_test.description = description
        ab_test.test_type = test_type  # 'knowledge_base', 'response_algorithm', 'ui_component'
        ab_test.control_version = control_version
        ab_test.test_version = test_version
        ab_test.target_metric = target_metric
        ab_test.success_criteria = success_criteria
        ab_test.duration_days = duration_days
        ab_test.traffic_split = traffic_split
        ab_test.start_date = frappe.utils.today()
        ab_test.end_date = frappe.utils.add_days(frappe.utils.today(), duration_days)
        ab_test.status = "active"

        ab_test.insert()
        frappe.db.commit()

        return {
            "status": "success",
            "test_id": ab_test.name,
            "test_name": test_name,
            "start_date": ab_test.start_date,
            "end_date": ab_test.end_date
        }

    except Exception as e:
        frappe.log_error(f"A/B test creation error: {str(e)}", "AB Test Creation")
        return {"status": "error", "message": "Failed to create A/B test"}

@frappe.whitelist()
def assign_user_to_test_group(user_id, test_id=None):
    """Assign user to A/B test group"""

    try:
        # Get active tests
        active_tests = frappe.db.sql("""
            SELECT name, test_name, traffic_split
            FROM `tabAB Test`
            WHERE status = 'active'
            AND start_date <= CURDATE()
            AND end_date >= CURDATE()
        """, as_dict=True)

        assignments = []

        for test in active_tests:
            if test_id and test['name'] != test_id:
                continue

            # Check if user already assigned
            existing_assignment = frappe.db.exists("AB Test Assignment", {
                "user_id": user_id,
                "test_id": test['name']
            })

            if not existing_assignment:
                # Assign user based on traffic split
                import hashlib
                user_hash = int(hashlib.md5(f"{user_id}{test['name']}".encode()).hexdigest(), 16)
                assignment_group = "test" if (user_hash % 100) < test['traffic_split'] else "control"

                # Create assignment
                assignment = frappe.new_doc("AB Test Assignment")
                assignment.user_id = user_id
                assignment.test_id = test['name']
                assignment.assignment_group = assignment_group
                assignment.assignment_date = frappe.utils.now()

                assignment.insert()

                assignments.append({
                    "test_id": test['name'],
                    "test_name": test['test_name'],
                    "group": assignment_group
                })

        frappe.db.commit()

        return {
            "status": "success",
            "assignments": assignments
        }

    except Exception as e:
        frappe.log_error(f"A/B test assignment error: {str(e)}", "AB Test Assignment")
        return {"status": "error", "message": "Failed to assign user to test"}

@frappe.whitelist()
def record_ab_test_interaction(user_id, test_id, interaction_type, interaction_data,
                              outcome_metric=None, outcome_value=None):
    """Record A/B test interaction"""

    try:
        # Get user's test assignment
        assignment = frappe.db.get_value("AB Test Assignment", {
            "user_id": user_id,
            "test_id": test_id
        }, ["assignment_group"], as_dict=True)

        if not assignment:
            return {"status": "error", "message": "User not assigned to test"}

        # Record interaction
        interaction = frappe.new_doc("AB Test Interaction")
        interaction.user_id = user_id
        interaction.test_id = test_id
        interaction.assignment_group = assignment['assignment_group']
        interaction.interaction_type = interaction_type
        interaction.interaction_data = json.dumps(interaction_data) if isinstance(interaction_data, dict) else interaction_data
        interaction.outcome_metric = outcome_metric
        interaction.outcome_value = outcome_value
        interaction.interaction_timestamp = frappe.utils.now()

        interaction.insert()
        frappe.db.commit()

        return {
            "status": "success",
            "interaction_id": interaction.name,
            "group": assignment['assignment_group']
        }

    except Exception as e:
        frappe.log_error(f"A/B test interaction error: {str(e)}", "AB Test Interaction")
        return {"status": "error", "message": "Failed to record interaction"}

@frappe.whitelist()
def analyze_ab_test_results(test_id):
    """Analyze A/B test results"""

    try:
        # Get test details
        test = frappe.get_doc("AB Test", test_id)

        # Get interaction summary by group
        results = frappe.db.sql("""
            SELECT
                assignment_group,
                COUNT(*) as interaction_count,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(outcome_value) as avg_outcome,
                STDDEV(outcome_value) as outcome_stddev
            FROM `tabAB Test Interaction`
            WHERE test_id = %s
            AND outcome_value IS NOT NULL
            GROUP BY assignment_group
        """, (test_id,), as_dict=True)

        # Calculate statistical significance
        if len(results) == 2:
            control_group = next((r for r in results if r['assignment_group'] == 'control'), None)
            test_group = next((r for r in results if r['assignment_group'] == 'test'), None)

            if control_group and test_group:
                # Simple statistical analysis
                improvement = ((test_group['avg_outcome'] - control_group['avg_outcome']) / control_group['avg_outcome']) * 100

                # Basic significance test (simplified)
                significance = "significant" if abs(improvement) > 5 and test_group['unique_users'] > 30 else "not_significant"

                analysis = {
                    "control_group": control_group,
                    "test_group": test_group,
                    "improvement_percentage": improvement,
                    "statistical_significance": significance,
                    "recommendation": generate_ab_test_recommendation(improvement, significance, test)
                }
            else:
                analysis = {"error": "Insufficient data for both groups"}
        else:
            analysis = {"error": "Invalid group data"}

        return {
            "status": "success",
            "test_name": test.test_name,
            "analysis": analysis,
            "raw_results": results
        }

    except Exception as e:
        frappe.log_error(f"A/B test analysis error: {str(e)}", "AB Test Analysis")
        return {"status": "error", "message": "Failed to analyze test results"}

def generate_ab_test_recommendation(improvement, significance, test):
    """Generate recommendation based on A/B test results"""

    if significance == "significant":
        if improvement > 10:
            return f"Strong recommendation: Implement test version. {improvement:.1f}% improvement detected."
        elif improvement > 5:
            return f"Moderate recommendation: Consider implementing test version. {improvement:.1f}% improvement detected."
        elif improvement < -5:
            return f"Recommendation: Keep control version. Test version shows {abs(improvement):.1f}% decrease."
        else:
            return "Neutral: Minimal difference detected. Consider other factors."
    else:
        return "Inconclusive: Continue test or increase sample size for statistical significance."
'''

    # Write A/B testing framework to file
    ab_file = "development/frappe-bench/apps/assistant_crm/assistant_crm/api/ab_testing.py"
    try:
        with open(ab_file, 'w') as f:
            f.write('#!/usr/bin/env python3\n\nimport frappe\nfrom frappe import _\nimport json\nfrom datetime import datetime, timedelta\n\n')
            f.write(ab_testing_code)
        print("✅ A/B testing framework created")
    except Exception as e:
        print(f"⚠️  Error creating A/B testing framework: {str(e)}")

def create_model_performance_tracking():
    """Create model performance tracking system"""

    performance_code = '''
@frappe.whitelist()
def track_model_performance_realtime(model_version, prediction_accuracy, response_time,
                                   confidence_distribution, error_rate, throughput):
    """Track real-time model performance metrics"""

    try:
        # Create real-time performance record
        performance = frappe.new_doc("Model Performance Realtime")
        performance.model_version = model_version
        performance.timestamp = frappe.utils.now()
        performance.prediction_accuracy = prediction_accuracy
        performance.response_time = response_time
        performance.confidence_distribution = json.dumps(confidence_distribution)
        performance.error_rate = error_rate
        performance.throughput = throughput

        # Calculate performance score
        performance.performance_score = calculate_overall_performance_score(
            prediction_accuracy, response_time, error_rate, confidence_distribution
        )

        performance.insert()
        frappe.db.commit()

        # Check for performance alerts
        check_performance_alerts(performance)

        return {
            "status": "success",
            "performance_id": performance.name,
            "performance_score": performance.performance_score
        }

    except Exception as e:
        frappe.log_error(f"Real-time performance tracking error: {str(e)}", "Performance Tracking")
        return {"status": "error", "message": "Failed to track performance"}

def calculate_overall_performance_score(accuracy, response_time, error_rate, confidence_dist):
    """Calculate overall performance score"""

    # Accuracy component (40% weight)
    accuracy_score = accuracy * 40

    # Response time component (20% weight) - lower is better
    response_time_score = max(0, (2000 - response_time) / 2000) * 20  # Assuming 2000ms is poor

    # Error rate component (25% weight) - lower is better
    error_rate_score = max(0, (1 - error_rate)) * 25

    # Confidence distribution component (15% weight)
    if isinstance(confidence_dist, dict):
        high_confidence = confidence_dist.get('high', 0)
        confidence_score = high_confidence * 15
    else:
        confidence_score = 10  # Default moderate score

    total_score = accuracy_score + response_time_score + error_rate_score + confidence_score

    return min(total_score, 100)

def check_performance_alerts(performance):
    """Check for performance alerts and notifications"""

    try:
        alerts = []

        # Check accuracy threshold
        if performance.prediction_accuracy < 0.7:
            alerts.append({
                "type": "accuracy_low",
                "message": f"Model accuracy dropped to {performance.prediction_accuracy:.2f}",
                "severity": "high"
            })

        # Check response time threshold
        if performance.response_time > 3000:  # 3 seconds
            alerts.append({
                "type": "response_time_high",
                "message": f"Response time increased to {performance.response_time}ms",
                "severity": "medium"
            })

        # Check error rate threshold
        if performance.error_rate > 0.1:  # 10%
            alerts.append({
                "type": "error_rate_high",
                "message": f"Error rate increased to {performance.error_rate:.2f}",
                "severity": "high"
            })

        # Send alerts if any
        if alerts:
            send_performance_alerts(performance.model_version, alerts)

    except Exception as e:
        frappe.log_error(f"Performance alert check error: {str(e)}", "Performance Alerts")

def send_performance_alerts(model_version, alerts):
    """Send performance alerts to administrators"""

    try:
        # Create alert notification
        for alert in alerts:
            notification = frappe.new_doc("Performance Alert")
            notification.model_version = model_version
            notification.alert_type = alert['type']
            notification.alert_message = alert['message']
            notification.severity = alert['severity']
            notification.alert_timestamp = frappe.utils.now()
            notification.status = "active"

            notification.insert()

        frappe.db.commit()

        # Send email notifications for high severity alerts
        high_severity_alerts = [a for a in alerts if a['severity'] == 'high']
        if high_severity_alerts:
            send_alert_email(model_version, high_severity_alerts)

    except Exception as e:
        frappe.log_error(f"Alert sending error: {str(e)}", "Alert Sending")

def send_alert_email(model_version, alerts):
    """Send email alerts for critical performance issues"""

    try:
        # Get system administrators
        admins = frappe.db.sql("""
            SELECT email
            FROM `tabUser`
            WHERE enabled = 1
            AND name IN (
                SELECT parent
                FROM `tabHas Role`
                WHERE role = 'System Manager'
            )
        """, as_dict=True)

        if admins:
            alert_messages = "\\n".join([alert['message'] for alert in alerts])

            subject = f"WCFCB Assistant CRM - Model Performance Alert ({model_version})"
            message = f"""
            <h3>Model Performance Alert</h3>
            <p><strong>Model Version:</strong> {model_version}</p>
            <p><strong>Alert Time:</strong> {frappe.utils.now()}</p>

            <h4>Issues Detected:</h4>
            <ul>
            """

            for alert in alerts:
                message += f"<li><strong>{alert['type'].replace('_', ' ').title()}:</strong> {alert['message']}</li>"

            message += """
            </ul>

            <p>Please review the model performance dashboard and take appropriate action.</p>
            """

            for admin in admins:
                frappe.sendmail(
                    recipients=[admin['email']],
                    subject=subject,
                    message=message
                )

    except Exception as e:
        frappe.log_error(f"Alert email error: {str(e)}", "Alert Email")
'''

    # Write performance tracking to file
    perf_file = "development/frappe-bench/apps/assistant_crm/assistant_crm/api/model_performance.py"
    try:
        with open(perf_file, 'w') as f:
            f.write('#!/usr/bin/env python3\n\nimport frappe\nfrom frappe import _\nimport json\nfrom datetime import datetime, timedelta\n\n')
            f.write(performance_code)
        print("✅ Model performance tracking created")
    except Exception as e:
        print(f"⚠️  Error creating performance tracking: {str(e)}")

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    setup_ml_integration()
