# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error, classification_report
from sklearn.cluster import KMeans
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import joblib
import json
import warnings
warnings.filterwarnings('ignore')


class AdvancedAIService:
    """
    Advanced AI service providing predictive analytics, machine learning,
    and intelligent behavior analysis for WCFCB stakeholder management
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.model_performance = {}
        
    # ==================== CONTRIBUTION COLLECTION FORECASTING ====================
    
    def train_contribution_forecasting_model(self) -> Dict[str, Any]:
        """Train ML model for contribution collection forecasting"""
        try:
            # Get historical contribution data
            contribution_data = self.get_contribution_historical_data()
            
            if len(contribution_data) < 100:
                return {"success": False, "message": "Insufficient data for training (minimum 100 records required)"}
            
            # Prepare features and target
            features, target = self.prepare_contribution_features(contribution_data)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            predictions = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, predictions)
            rmse = np.sqrt(mse)
            
            # Store model and scaler
            self.models['contribution_forecasting'] = model
            self.scalers['contribution_forecasting'] = scaler
            self.model_performance['contribution_forecasting'] = {
                "rmse": rmse,
                "feature_importance": dict(zip(features.columns, model.feature_importances_)),
                "training_date": datetime.now().isoformat(),
                "training_samples": len(X_train)
            }
            
            # Save model to disk
            self.save_model('contribution_forecasting', model, scaler)
            
            return {
                "success": True,
                "model_performance": {
                    "rmse": rmse,
                    "accuracy_score": max(0, 100 - (rmse / np.mean(y_test) * 100)),
                    "training_samples": len(X_train),
                    "test_samples": len(X_test)
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error training contribution forecasting model: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def predict_contribution_collections(self, forecast_months: int = 12) -> Dict[str, Any]:
        """Predict future contribution collections"""
        try:
            # Load model
            model, scaler = self.load_model('contribution_forecasting')
            if not model:
                return {"success": False, "message": "Contribution forecasting model not trained"}
            
            # Generate future features
            future_features = self.generate_future_contribution_features(forecast_months)
            
            # Scale features
            future_features_scaled = scaler.transform(future_features)
            
            # Make predictions
            predictions = model.predict(future_features_scaled)
            
            # Generate forecast dates
            forecast_dates = [
                (datetime.now() + timedelta(days=30*i)).strftime("%Y-%m")
                for i in range(1, forecast_months + 1)
            ]
            
            # Calculate confidence intervals (using model uncertainty)
            prediction_std = np.std(predictions) * 0.1  # Simplified confidence interval
            
            forecast_data = []
            for i, (date, prediction) in enumerate(zip(forecast_dates, predictions)):
                forecast_data.append({
                    "month": date,
                    "predicted_amount": float(prediction),
                    "confidence_lower": float(prediction - prediction_std),
                    "confidence_upper": float(prediction + prediction_std),
                    "trend": "increasing" if i > 0 and prediction > predictions[i-1] else "stable"
                })
            
            return {
                "success": True,
                "forecast": forecast_data,
                "total_predicted": float(np.sum(predictions)),
                "model_accuracy": self.model_performance.get('contribution_forecasting', {}).get('accuracy_score', 0),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Error predicting contributions: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ==================== COMPLIANCE RISK ASSESSMENT ====================
    
    def train_compliance_risk_model(self) -> Dict[str, Any]:
        """Train ML model for compliance risk assessment"""
        try:
            # Get employer compliance data
            compliance_data = self.get_compliance_historical_data()
            
            if len(compliance_data) < 50:
                return {"success": False, "message": "Insufficient compliance data for training"}
            
            # Prepare features and target
            features, target = self.prepare_compliance_features(compliance_data)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest classifier
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            predictions = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, predictions)
            
            # Store model and scaler
            self.models['compliance_risk'] = model
            self.scalers['compliance_risk'] = scaler
            self.model_performance['compliance_risk'] = {
                "accuracy": accuracy,
                "feature_importance": dict(zip(features.columns, model.feature_importances_)),
                "training_date": datetime.now().isoformat(),
                "training_samples": len(X_train)
            }
            
            # Save model to disk
            self.save_model('compliance_risk', model, scaler)
            
            return {
                "success": True,
                "model_performance": {
                    "accuracy": accuracy,
                    "training_samples": len(X_train),
                    "test_samples": len(X_test)
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error training compliance risk model: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def assess_compliance_risk(self, employer_code: str) -> Dict[str, Any]:
        """Assess compliance risk for specific employer"""
        try:
            # Load model
            model, scaler = self.load_model('compliance_risk')
            if not model:
                return {"success": False, "message": "Compliance risk model not trained"}
            
            # Get employer features
            employer_features = self.get_employer_risk_features(employer_code)
            if employer_features is None:
                return {"success": False, "message": "Employer not found"}
            
            # Scale features
            features_scaled = scaler.transform([employer_features])
            
            # Predict risk
            risk_probability = model.predict_proba(features_scaled)[0]
            risk_class = model.predict(features_scaled)[0]
            
            # Get feature importance for explanation
            feature_names = ['outstanding_ratio', 'employee_count', 'industry_risk', 'payment_history', 'assessment_frequency']
            feature_importance = dict(zip(feature_names, employer_features))
            
            risk_level = "Low"
            if risk_probability[1] > 0.7:
                risk_level = "High"
            elif risk_probability[1] > 0.4:
                risk_level = "Medium"
            
            return {
                "success": True,
                "employer_code": employer_code,
                "risk_assessment": {
                    "risk_level": risk_level,
                    "risk_probability": float(risk_probability[1]),
                    "risk_factors": feature_importance,
                    "recommendations": self.generate_compliance_recommendations(risk_level, feature_importance)
                },
                "assessed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Error assessing compliance risk: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ==================== BENEFIT ELIGIBILITY PREDICTION ====================
    
    def train_benefit_eligibility_model(self) -> Dict[str, Any]:
        """Train ML model for benefit eligibility prediction"""
        try:
            # Get employee benefit data
            benefit_data = self.get_benefit_historical_data()
            
            if len(benefit_data) < 100:
                return {"success": False, "message": "Insufficient benefit data for training"}
            
            # Prepare features and target
            features, target = self.prepare_benefit_features(benefit_data)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Logistic Regression model
            model = LogisticRegression(random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            predictions = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, predictions)
            
            # Store model and scaler
            self.models['benefit_eligibility'] = model
            self.scalers['benefit_eligibility'] = scaler
            self.model_performance['benefit_eligibility'] = {
                "accuracy": accuracy,
                "training_date": datetime.now().isoformat(),
                "training_samples": len(X_train)
            }
            
            # Save model to disk
            self.save_model('benefit_eligibility', model, scaler)
            
            return {
                "success": True,
                "model_performance": {
                    "accuracy": accuracy,
                    "training_samples": len(X_train),
                    "test_samples": len(X_test)
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error training benefit eligibility model: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def predict_benefit_eligibility(self, employee_number: str) -> Dict[str, Any]:
        """Predict benefit eligibility for employee"""
        try:
            # Load model
            model, scaler = self.load_model('benefit_eligibility')
            if not model:
                return {"success": False, "message": "Benefit eligibility model not trained"}
            
            # Get employee features
            employee_features = self.get_employee_benefit_features(employee_number)
            if employee_features is None:
                return {"success": False, "message": "Employee not found"}
            
            # Scale features
            features_scaled = scaler.transform([employee_features])
            
            # Predict eligibility
            eligibility_probability = model.predict_proba(features_scaled)[0]
            eligibility_class = model.predict(features_scaled)[0]
            
            eligibility_status = "Eligible" if eligibility_class == 1 else "Not Eligible"
            confidence = float(max(eligibility_probability))
            
            return {
                "success": True,
                "employee_number": employee_number,
                "eligibility_prediction": {
                    "status": eligibility_status,
                    "confidence": confidence,
                    "probability_eligible": float(eligibility_probability[1]),
                    "factors_considered": ["years_of_service", "total_contributions", "employment_status", "age"]
                },
                "predicted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Error predicting benefit eligibility: {str(e)}")
            return {"success": False, "error": str(e)}

    # ==================== STAKEHOLDER BEHAVIOR ANALYSIS ====================

    def analyze_stakeholder_behavior_patterns(self) -> Dict[str, Any]:
        """Analyze stakeholder behavior patterns using clustering"""
        try:
            # Get stakeholder interaction data
            interaction_data = self.get_stakeholder_interaction_data()

            if len(interaction_data) < 50:
                return {"success": False, "message": "Insufficient interaction data for analysis"}

            # Prepare features for clustering
            features = self.prepare_behavior_features(interaction_data)

            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            # Perform K-means clustering
            kmeans = KMeans(n_clusters=5, random_state=42)
            clusters = kmeans.fit_predict(features_scaled)

            # Analyze clusters
            cluster_analysis = self.analyze_behavior_clusters(features, clusters)

            # Store model
            self.models['behavior_clustering'] = kmeans
            self.scalers['behavior_clustering'] = scaler

            return {
                "success": True,
                "behavior_patterns": cluster_analysis,
                "total_stakeholders_analyzed": len(interaction_data),
                "analysis_date": datetime.now().isoformat()
            }

        except Exception as e:
            frappe.log_error(f"Error analyzing behavior patterns: {str(e)}")
            return {"success": False, "error": str(e)}

    # ==================== ANOMALY DETECTION FOR FRAUD PREVENTION ====================

    def train_anomaly_detection_model(self) -> Dict[str, Any]:
        """Train anomaly detection model for fraud prevention"""
        try:
            # Get transaction and interaction data
            transaction_data = self.get_transaction_data_for_anomaly_detection()

            if len(transaction_data) < 100:
                return {"success": False, "message": "Insufficient transaction data for training"}

            # Prepare features
            features = self.prepare_anomaly_features(transaction_data)

            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            # Train Isolation Forest model
            model = IsolationForest(contamination=0.1, random_state=42)
            model.fit(features_scaled)

            # Store model and scaler
            self.models['anomaly_detection'] = model
            self.scalers['anomaly_detection'] = scaler

            # Test on training data to get baseline
            anomaly_scores = model.decision_function(features_scaled)
            anomalies = model.predict(features_scaled)
            anomaly_count = np.sum(anomalies == -1)

            return {
                "success": True,
                "model_performance": {
                    "training_samples": len(transaction_data),
                    "detected_anomalies": int(anomaly_count),
                    "anomaly_rate": float(anomaly_count / len(transaction_data)),
                    "training_date": datetime.now().isoformat()
                }
            }

        except Exception as e:
            frappe.log_error(f"Error training anomaly detection model: {str(e)}")
            return {"success": False, "error": str(e)}

    def detect_anomalies(self, data_type: str = "recent") -> Dict[str, Any]:
        """Detect anomalies in recent transactions or interactions"""
        try:
            # Load model
            model = self.models.get('anomaly_detection')
            scaler = self.scalers.get('anomaly_detection')

            if not model or not scaler:
                return {"success": False, "message": "Anomaly detection model not trained"}

            # Get recent data
            if data_type == "recent":
                recent_data = self.get_recent_transaction_data()
            else:
                recent_data = self.get_transaction_data_for_anomaly_detection()

            if len(recent_data) == 0:
                return {"success": True, "anomalies": [], "message": "No recent data to analyze"}

            # Prepare features
            features = self.prepare_anomaly_features(recent_data)

            # Scale features
            features_scaled = scaler.transform(features)

            # Detect anomalies
            anomaly_scores = model.decision_function(features_scaled)
            anomalies = model.predict(features_scaled)

            # Identify anomalous records
            anomalous_records = []
            for i, (score, is_anomaly) in enumerate(zip(anomaly_scores, anomalies)):
                if is_anomaly == -1:
                    anomalous_records.append({
                        "record_index": i,
                        "anomaly_score": float(score),
                        "severity": "High" if score < -0.5 else "Medium",
                        "record_data": recent_data[i],
                        "potential_issues": self.analyze_anomaly_causes(recent_data[i], features.iloc[i])
                    })

            return {
                "success": True,
                "anomalies": anomalous_records,
                "total_records_analyzed": len(recent_data),
                "anomalies_detected": len(anomalous_records),
                "detection_date": datetime.now().isoformat()
            }

        except Exception as e:
            frappe.log_error(f"Error detecting anomalies: {str(e)}")
            return {"success": False, "error": str(e)}

    # ==================== DATA PREPARATION METHODS ====================

    def get_contribution_historical_data(self) -> pd.DataFrame:
        """Get historical contribution data for training.

        NOTE: Employee Profile and Employer Profile doctypes have been removed.
        Using ERPNext Employee and Customer instead.
        """
        try:
            # NOTE: Using ERPNext Employee and Customer (custom profiles removed)
            # Get employee data from ERPNext Employee table
            sql = """
                SELECT
                    e.company as employer_code,
                    e.status as employment_status,
                    c.customer_group as industry_sector,
                    MONTH(e.creation) as month,
                    YEAR(e.creation) as year
                FROM `tabEmployee` e
                LEFT JOIN `tabCustomer` c ON e.company = c.customer_name
                WHERE e.status = 'Active' AND e.creation >= DATE_SUB(NOW(), INTERVAL 24 MONTH)
            """

            data = frappe.db.sql(sql, as_dict=True)
            return pd.DataFrame(data)

        except Exception as e:
            frappe.log_error(f"Error getting contribution data: {str(e)}")
            return pd.DataFrame()

    def prepare_contribution_features(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for contribution forecasting"""
        try:
            # Create features
            features = pd.DataFrame()

            # Time-based features
            features['month'] = data['month']
            features['year'] = data['year']
            features['quarter'] = ((data['month'] - 1) // 3) + 1

            # Employer features
            features['total_employees'] = data['total_employees'].fillna(0)
            features['industry_risk'] = data['industry_sector'].map({
                'Mining': 3, 'Manufacturing': 2, 'Construction': 3,
                'Agriculture': 2, 'Services': 1, 'Finance': 1
            }).fillna(2)

            # Employee features
            features['avg_salary'] = data['monthly_salary']
            features['contribution_rate'] = data['contribution_rate']

            # Target: monthly contribution amount
            target = data['monthly_salary'] * data['contribution_rate'] / 100

            return features.fillna(0), target.fillna(0)

        except Exception as e:
            frappe.log_error(f"Error preparing contribution features: {str(e)}")
            return pd.DataFrame(), pd.Series()

    def get_compliance_historical_data(self) -> pd.DataFrame:
        """Get historical compliance data for training.

        NOTE: Employer Profile doctype has been removed.
        Using ERPNext Customer and Compliance Report instead.
        """
        try:
            # NOTE: Using ERPNext Customer and Compliance Report (Employer Profile removed)
            sql = """
                SELECT
                    c.name as employer_code,
                    cr.compliance_status,
                    c.customer_group as industry_sector,
                    c.creation as registration_date
                FROM `tabCustomer` c
                LEFT JOIN `tabCompliance Report` cr ON c.name = cr.employer
                WHERE c.customer_type = 'Company'
                AND c.creation >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            """

            data = frappe.db.sql(sql, as_dict=True)
            return pd.DataFrame(data)

        except Exception as e:
            frappe.log_error(f"Error getting compliance data: {str(e)}")
            return pd.DataFrame()

    def prepare_compliance_features(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for compliance risk assessment"""
        try:
            features = pd.DataFrame()

            # Financial features
            features['outstanding_ratio'] = data['outstanding_contributions'] / (data['total_employees'] * 1000 + 1)
            features['employee_count'] = data['total_employees']

            # Industry risk mapping
            features['industry_risk'] = data['industry_sector'].map({
                'Mining': 3, 'Construction': 3, 'Manufacturing': 2,
                'Agriculture': 2, 'Services': 1, 'Finance': 1
            }).fillna(2)

            # Payment history (simplified)
            features['payment_history'] = (data['outstanding_contributions'] == 0).astype(int)

            # Assessment frequency (simplified)
            features['assessment_frequency'] = 1  # Default value

            # Target: compliance status (1 = compliant, 0 = non-compliant)
            target = (data['compliance_status'] == 'Compliant').astype(int)

            return features.fillna(0), target

        except Exception as e:
            frappe.log_error(f"Error preparing compliance features: {str(e)}")
            return pd.DataFrame(), pd.Series()

    def get_benefit_historical_data(self) -> pd.DataFrame:
        """Get historical benefit data for training.

        NOTE: Employee Profile and Beneficiary Profile doctypes have been removed.
        Using ERPNext Employee instead.
        """
        try:
            # NOTE: Using ERPNext Employee (custom profiles removed)
            sql = """
                SELECT
                    e.name as employee_number,
                    e.status as employment_status,
                    e.date_of_joining as employment_start_date,
                    e.date_of_birth
                FROM `tabEmployee` e
                WHERE e.creation >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            """

            data = frappe.db.sql(sql, as_dict=True)
            return pd.DataFrame(data)

        except Exception as e:
            frappe.log_error(f"Error getting benefit data: {str(e)}")
            return pd.DataFrame()

    def prepare_benefit_features(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for benefit eligibility prediction"""
        try:
            features = pd.DataFrame()

            # Calculate years of service
            today = pd.Timestamp.now()
            data['employment_start_date'] = pd.to_datetime(data['employment_start_date'])
            features['years_of_service'] = (today - data['employment_start_date']).dt.days / 365.25

            # Calculate age
            data['date_of_birth'] = pd.to_datetime(data['date_of_birth'])
            features['age'] = (today - data['date_of_birth']).dt.days / 365.25

            # Financial features
            features['total_contributions'] = data['total_contributions']
            features['monthly_salary'] = data['monthly_salary']

            # Employment status
            features['employment_status'] = (data['employment_status'] == 'Active').astype(int)

            # Target: benefit eligibility (1 = eligible, 0 = not eligible)
            target = (data['benefit_status'].isin(['Eligible', 'Active'])).astype(int)

            return features.fillna(0), target

        except Exception as e:
            frappe.log_error(f"Error preparing benefit features: {str(e)}")
            return pd.DataFrame(), pd.Series()

    # ==================== UTILITY METHODS ====================

    def save_model(self, model_name: str, model, scaler=None):
        """Save trained model to disk"""
        try:
            import os
            model_dir = frappe.get_site_path("private", "ai_models")
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)

            # Save model
            model_path = os.path.join(model_dir, f"{model_name}_model.pkl")
            joblib.dump(model, model_path)

            # Save scaler if provided
            if scaler:
                scaler_path = os.path.join(model_dir, f"{model_name}_scaler.pkl")
                joblib.dump(scaler, scaler_path)

        except Exception as e:
            frappe.log_error(f"Error saving model {model_name}: {str(e)}")

    def load_model(self, model_name: str) -> Tuple[Any, Any]:
        """Load trained model from disk"""
        try:
            import os
            model_dir = frappe.get_site_path("private", "ai_models")

            # Load model
            model_path = os.path.join(model_dir, f"{model_name}_model.pkl")
            if os.path.exists(model_path):
                model = joblib.load(model_path)
            else:
                model = self.models.get(model_name)

            # Load scaler
            scaler_path = os.path.join(model_dir, f"{model_name}_scaler.pkl")
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
            else:
                scaler = self.scalers.get(model_name)

            return model, scaler

        except Exception as e:
            frappe.log_error(f"Error loading model {model_name}: {str(e)}")
            return None, None

    def generate_future_contribution_features(self, months: int) -> pd.DataFrame:
        """Generate features for future contribution predictions.

        NOTE: Employer Profile doctype has been removed.
        Using ERPNext Customer and Employee instead.
        """
        try:
            features = []
            current_date = datetime.now()

            for i in range(1, months + 1):
                future_date = current_date + timedelta(days=30*i)

                # Using ERPNext Customer instead of Employer Profile
                total_employers = frappe.db.count("Customer", {"customer_type": "Company"})
                # Get average employee count per company
                avg_employees = frappe.db.sql("""
                    SELECT COUNT(*) / NULLIF(COUNT(DISTINCT company), 0) as avg_emp
                    FROM `tabEmployee`
                    WHERE status = 'Active'
                """)[0][0] or 0

                feature_row = {
                    'month': future_date.month,
                    'year': future_date.year,
                    'quarter': ((future_date.month - 1) // 3) + 1,
                    'total_employees': avg_employees,
                    'industry_risk': 2,  # Average risk
                    'avg_salary': 5000,  # Estimated average
                    'contribution_rate': 5.0
                }

                features.append(feature_row)

            return pd.DataFrame(features)

        except Exception as e:
            frappe.log_error(f"Error generating future features: {str(e)}")
            return pd.DataFrame()

    def get_employer_risk_features(self, employer_code: str) -> List[float]:
        """Get risk assessment features for specific employer.

        NOTE: Employer Profile doctype has been removed.
        Using ERPNext Customer and Compliance Report instead.
        """
        try:
            # Using ERPNext Customer instead of Employer Profile
            employer = frappe.get_doc("Customer", employer_code)

            # Get employee count for this employer
            employee_count = frappe.db.count("Employee", {"company": employer_code, "status": "Active"})

            # Get compliance info from Compliance Report if available
            compliance = frappe.get_all(
                "Compliance Report",
                filters={"employer": employer_code},
                fields=["compliance_status"],
                order_by="creation desc",
                limit=1
            )

            industry_risk_map = {
                'Mining': 3, 'Construction': 3, 'Manufacturing': 2,
                'Agriculture': 2, 'Services': 1, 'Finance': 1
            }
            industry_risk = industry_risk_map.get(employer.customer_group, 2)

            # Simplified features since Employer Profile fields are not available
            outstanding_ratio = 0  # Would need Employer Contributions doctype
            payment_history = 1  # Default to good
            assessment_frequency = 1  # Simplified

            return [outstanding_ratio, employee_count, industry_risk, payment_history, assessment_frequency]

        except Exception as e:
            frappe.log_error(f"Error getting employer risk features: {str(e)}")
            return None

    def get_employee_benefit_features(self, employee_number: str) -> List[float]:
        """Get benefit eligibility features for specific employee.

        NOTE: Employee Profile doctype has been removed.
        Using ERPNext Employee instead.
        """
        try:
            # Using ERPNext Employee instead of Employee Profile
            employee = frappe.get_doc("Employee", employee_number)

            # Calculate years of service
            if employee.date_of_joining:
                years_of_service = (datetime.now().date() - employee.date_of_joining).days / 365.25
            else:
                years_of_service = 0

            # Calculate age
            if employee.date_of_birth:
                age = (datetime.now().date() - employee.date_of_birth).days / 365.25
            else:
                age = 35  # Default age

            # NOTE: contribution and salary fields not available on ERPNext Employee
            # Would need to get from Employer Contributions doctype
            total_contributions = 0
            monthly_salary = 0
            employment_status = 1 if employee.status == 'Active' else 0

            return [years_of_service, age, total_contributions, monthly_salary, employment_status]

        except Exception as e:
            frappe.log_error(f"Error getting employee benefit features: {str(e)}")
            return None

    def generate_compliance_recommendations(self, risk_level: str, risk_factors: Dict) -> List[str]:
        """Generate compliance recommendations based on risk assessment"""
        recommendations = []

        if risk_level == "High":
            recommendations.extend([
                "Immediate compliance review required",
                "Schedule urgent assessment meeting",
                "Implement enhanced monitoring",
                "Consider penalty enforcement"
            ])
        elif risk_level == "Medium":
            recommendations.extend([
                "Schedule compliance review within 30 days",
                "Provide compliance guidance",
                "Monitor payment patterns closely"
            ])
        else:
            recommendations.extend([
                "Continue regular monitoring",
                "Maintain current compliance status"
            ])

        # Add specific recommendations based on risk factors
        if risk_factors.get('outstanding_ratio', 0) > 0.5:
            recommendations.append("Address outstanding contribution payments")

        if risk_factors.get('payment_history', 1) == 0:
            recommendations.append("Improve payment consistency")

        return recommendations

    def get_stakeholder_interaction_data(self) -> List[Dict]:
        """Get stakeholder interaction data for behavior analysis"""
        try:
            # This would integrate with communication logs
            # For now, return sample data structure
            return [
                {
                    "stakeholder_id": "EMP001",
                    "stakeholder_type": "employer",
                    "interaction_frequency": 5,
                    "response_time": 24,
                    "compliance_score": 85,
                    "payment_timeliness": 90
                }
            ]

        except Exception as e:
            frappe.log_error(f"Error getting interaction data: {str(e)}")
            return []

    def prepare_behavior_features(self, data: List[Dict]) -> pd.DataFrame:
        """Prepare features for behavior analysis"""
        try:
            df = pd.DataFrame(data)

            # Select relevant features for clustering
            features = df[['interaction_frequency', 'response_time', 'compliance_score', 'payment_timeliness']]

            return features.fillna(0)

        except Exception as e:
            frappe.log_error(f"Error preparing behavior features: {str(e)}")
            return pd.DataFrame()

    def analyze_behavior_clusters(self, features: pd.DataFrame, clusters: np.ndarray) -> Dict[str, Any]:
        """Analyze behavior clusters and provide insights"""
        try:
            cluster_analysis = {}

            for cluster_id in range(max(clusters) + 1):
                cluster_mask = clusters == cluster_id
                cluster_data = features[cluster_mask]

                cluster_analysis[f"cluster_{cluster_id}"] = {
                    "size": int(np.sum(cluster_mask)),
                    "characteristics": {
                        "avg_interaction_frequency": float(cluster_data['interaction_frequency'].mean()),
                        "avg_response_time": float(cluster_data['response_time'].mean()),
                        "avg_compliance_score": float(cluster_data['compliance_score'].mean()),
                        "avg_payment_timeliness": float(cluster_data['payment_timeliness'].mean())
                    },
                    "profile": self.get_cluster_profile_description(cluster_data)
                }

            return cluster_analysis

        except Exception as e:
            frappe.log_error(f"Error analyzing clusters: {str(e)}")
            return {}

    def get_cluster_profile_description(self, cluster_data: pd.DataFrame) -> str:
        """Get descriptive profile for behavior cluster"""
        try:
            avg_compliance = cluster_data['compliance_score'].mean()
            avg_interaction = cluster_data['interaction_frequency'].mean()

            if avg_compliance > 80 and avg_interaction > 3:
                return "Highly Engaged & Compliant"
            elif avg_compliance > 80:
                return "Compliant but Low Engagement"
            elif avg_interaction > 3:
                return "Engaged but Compliance Issues"
            else:
                return "Low Engagement & Compliance Concerns"

        except Exception as e:
            return "Unknown Profile"

    def get_transaction_data_for_anomaly_detection(self) -> List[Dict]:
        """Get transaction data for anomaly detection training.

        NOTE: Assessment Record doctype has been removed.
        Using Compliance Report instead.
        """
        try:
            # NOTE: Using Compliance Report instead of Assessment Record
            sql = """
                SELECT
                    employer as employer_code,
                    compliance_status,
                    creation as assessment_date
                FROM `tabCompliance Report`
                WHERE creation >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            """

            data = frappe.db.sql(sql, as_dict=True)
            return data

        except Exception as e:
            frappe.log_error(f"Error getting transaction data: {str(e)}")
            return []

    def prepare_anomaly_features(self, data: List[Dict]) -> pd.DataFrame:
        """Prepare features for anomaly detection"""
        try:
            df = pd.DataFrame(data)

            if len(df) == 0:
                return pd.DataFrame()

            features = pd.DataFrame()

            # Financial features
            features['contribution_amount'] = df['total_contributions_assessed'].fillna(0)
            features['payment_ratio'] = df['amount_paid'] / (df['total_contributions_assessed'] + 1)
            features['penalty_ratio'] = df['penalty_amount'] / (df['total_contributions_assessed'] + 1)

            # Time-based features
            df['assessment_date'] = pd.to_datetime(df['assessment_date'])
            features['days_since_assessment'] = (datetime.now() - df['assessment_date']).dt.days

            # Status features
            features['is_paid'] = (df['payment_status'] == 'Fully Paid').astype(int)

            return features.fillna(0)

        except Exception as e:
            frappe.log_error(f"Error preparing anomaly features: {str(e)}")
            return pd.DataFrame()

    def get_recent_transaction_data(self) -> List[Dict]:
        """Get recent transaction data for anomaly detection.

        NOTE: Assessment Record doctype has been removed.
        Using Compliance Report instead.
        """
        try:
            # NOTE: Using Compliance Report instead of Assessment Record
            sql = """
                SELECT
                    employer as employer_code,
                    compliance_status,
                    creation as assessment_date
                FROM `tabCompliance Report`
                WHERE creation >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
                ORDER BY creation DESC
                LIMIT 100
            """

            data = frappe.db.sql(sql, as_dict=True)
            return data

        except Exception as e:
            frappe.log_error(f"Error getting recent transaction data: {str(e)}")
            return []

    def analyze_anomaly_causes(self, record: Dict, features: pd.Series) -> List[str]:
        """Analyze potential causes of detected anomalies"""
        causes = []

        if features.get('payment_ratio', 0) < 0.1:
            causes.append("Unusually low payment ratio")

        if features.get('penalty_ratio', 0) > 0.5:
            causes.append("High penalty amount")

        if features.get('contribution_amount', 0) > 100000:
            causes.append("Unusually high contribution amount")

        if features.get('days_since_assessment', 0) > 90:
            causes.append("Long overdue payment")

        return causes if causes else ["Unknown anomaly pattern"]
