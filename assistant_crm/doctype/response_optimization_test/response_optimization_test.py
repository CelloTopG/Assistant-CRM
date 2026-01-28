# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
import json

class ResponseOptimizationTest(Document):
    """
    DocType for managing A/B tests and response optimization experiments.
    """
    
    def before_insert(self):
        """Set default values before inserting the document."""
        if not self.start_date:
            self.start_date = now()
        
        if not self.status:
            self.status = "active"
        
        if not self.split_ratio:
            self.split_ratio = 0.5
        
        if not self.min_sample_size:
            self.min_sample_size = 50
    
    def before_save(self):
        """Validate and process data before saving."""
        # Update test results if available
        if self.status == "completed":
            self._calculate_final_results()
    
    def _calculate_final_results(self):
        """Calculate final test results."""
        try:
            # Get metrics for both variants
            variant_a_metrics = frappe.get_all("Response Optimization Metric",
                filters={"test_name": self.test_name, "variant": "A"},
                fields=["response_quality_score", "user_satisfaction_score", "conversion"]
            )
            
            variant_b_metrics = frappe.get_all("Response Optimization Metric",
                filters={"test_name": self.test_name, "variant": "B"},
                fields=["response_quality_score", "user_satisfaction_score", "conversion"]
            )
            
            # Calculate performance metrics
            results = {
                "variant_a": self._calculate_variant_performance(variant_a_metrics),
                "variant_b": self._calculate_variant_performance(variant_b_metrics)
            }
            
            # Determine winner
            winner = self._determine_winner(results)
            
            # Update fields
            self.test_results = json.dumps(results)
            self.current_winner = winner["winner"]
            self.confidence_level = winner.get("confidence", 0)
            self.statistical_significance = winner.get("significant", False)
            
        except Exception as e:
            frappe.log_error(f"Error calculating test results: {str(e)}")
    
    def _calculate_variant_performance(self, metrics):
        """Calculate performance metrics for a variant."""
        if not metrics:
            return {"sample_size": 0, "avg_quality": 0, "avg_satisfaction": 0, "conversion_rate": 0}
        
        quality_scores = [m.response_quality_score for m in metrics if m.response_quality_score]
        satisfaction_scores = [m.user_satisfaction_score for m in metrics if m.user_satisfaction_score]
        conversions = [m.conversion for m in metrics if m.conversion]
        
        return {
            "sample_size": len(metrics),
            "avg_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            "avg_satisfaction": sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
            "conversion_rate": (sum(conversions) / len(metrics)) * 100 if metrics else 0
        }
    
    def _determine_winner(self, results):
        """Determine the winning variant."""
        variant_a = results["variant_a"]
        variant_b = results["variant_b"]
        
        # Calculate composite scores
        a_score = (
            variant_a["avg_quality"] * 0.4 +
            variant_a["avg_satisfaction"] * 0.4 +
            variant_a["conversion_rate"] / 100 * 0.2
        )
        
        b_score = (
            variant_b["avg_quality"] * 0.4 +
            variant_b["avg_satisfaction"] * 0.4 +
            variant_b["conversion_rate"] / 100 * 0.2
        )
        
        # Determine winner
        if abs(a_score - b_score) < 0.05:
            return {"winner": "inconclusive", "confidence": 50, "significant": False}
        elif a_score > b_score:
            confidence = min(95, 50 + (a_score - b_score) * 100)
            return {"winner": "A", "confidence": confidence, "significant": confidence > 80}
        else:
            confidence = min(95, 50 + (b_score - a_score) * 100)
            return {"winner": "B", "confidence": confidence, "significant": confidence > 80}


@frappe.whitelist()
def get_active_tests():
    """Get active optimization tests."""
    tests = frappe.get_all("Response Optimization Test",
        filters={"status": "active"},
        fields=["*"],
        order_by="start_date desc"
    )
    
    return tests


@frappe.whitelist()
def get_test_results(test_name):
    """Get results for a specific test."""
    try:
        test = frappe.get_doc("Response Optimization Test", test_name)
        
        # Get latest metrics
        metrics = frappe.get_all("Response Optimization Metric",
            filters={"test_name": test_name},
            fields=["*"],
            order_by="timestamp desc"
        )
        
        return {
            "test_info": {
                "test_name": test.test_name,
                "status": test.status,
                "start_date": test.start_date,
                "end_date": test.end_date,
                "target_metric": test.target_metric
            },
            "current_results": json.loads(test.test_results) if test.test_results else {},
            "winner": test.current_winner,
            "confidence": test.confidence_level,
            "significant": test.statistical_significance,
            "total_samples": len(metrics)
        }
        
    except frappe.DoesNotExistError:
        return {"error": "Test not found"}
    except Exception as e:
        return {"error": str(e)}
