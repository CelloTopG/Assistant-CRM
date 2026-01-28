# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
import json

class ResponseOptimizationMetric(Document):
    """
    DocType for storing response optimization metrics and A/B test data.
    """
    
    def before_insert(self):
        """Set default values before inserting the document."""
        if not self.timestamp:
            self.timestamp = now()
    
    def before_save(self):
        """Validate and process data before saving."""
        # Ensure required fields are set
        if not self.test_name or not self.variant:
            frappe.throw("Test name and variant are required")


@frappe.whitelist()
def record_metric(test_name, variant, metric_data):
    """Record a metric for an optimization test."""
    try:
        metric_doc = frappe.new_doc("Response Optimization Metric")
        metric_doc.test_name = test_name
        metric_doc.variant = variant
        metric_doc.timestamp = now()
        
        # Set metric data
        for field, value in metric_data.items():
            if hasattr(metric_doc, field):
                setattr(metric_doc, field, value)
        
        # Store additional data as JSON
        if metric_data.get('additional_data'):
            metric_doc.metrics_data = json.dumps(metric_data['additional_data'])
        
        metric_doc.insert()
        frappe.db.commit()
        
        return {"status": "success", "metric_id": metric_doc.name}
        
    except Exception as e:
        frappe.log_error(f"Error recording metric: {str(e)}")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_test_metrics(test_name, variant=None, limit=1000):
    """Get metrics for a test."""
    filters = {"test_name": test_name}
    if variant:
        filters["variant"] = variant
    
    metrics = frappe.get_all("Response Optimization Metric",
        filters=filters,
        fields=["*"],
        order_by="timestamp desc",
        limit=limit
    )
    
    return metrics
