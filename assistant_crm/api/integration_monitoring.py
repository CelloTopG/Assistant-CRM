import frappe
from frappe import _
from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService
from datetime import datetime, timedelta
import json

@frappe.whitelist(allow_guest=False)
def get_integration_dashboard():
    """Get comprehensive integration dashboard data"""
    try:
        # Get all active integrations
        integrations = frappe.db.sql("""
            SELECT name, system_name, system_type, sync_status, 
                   last_sync_time, is_active, last_error_message
            FROM `tabExternal System Integration`
            WHERE is_active = 1
            ORDER BY system_name
        """, as_dict=True)

        # Get health status for each integration
        integration_health = []
        for integration in integrations:
            if integration['system_type'] == 'CoreBusiness':
                service = CoreBusinessIntegrationService()
                health = service.get_integration_health_status()
                integration['health_status'] = health
            else:
                integration['health_status'] = {'status': 'Unknown'}
            
            integration_health.append(integration)

        # Get sync statistics for the last 30 days
        sync_stats = get_sync_statistics(30)

        # Get data quality metrics
        data_quality = get_data_quality_metrics()

        # Get recent sync logs
        recent_logs = get_recent_sync_logs(10)

        return {
            'success': True,
            'integrations': integration_health,
            'sync_statistics': sync_stats,
            'data_quality': data_quality,
            'recent_logs': recent_logs,
            'dashboard_updated': frappe.utils.now()
        }

    except Exception as e:
        frappe.log_error(f"Failed to get integration dashboard: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_sync_statistics(days=30):
    """Get synchronization statistics for the specified period"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get sync frequency data
    sync_data = frappe.db.sql("""
        SELECT system_name, sync_status, 
               DATE(last_sync_time) as sync_date,
               COUNT(*) as sync_count
        FROM `tabExternal System Integration`
        WHERE last_sync_time BETWEEN %s AND %s
        GROUP BY system_name, sync_status, DATE(last_sync_time)
        ORDER BY sync_date DESC
    """, (start_date, end_date), as_dict=True)

    # Calculate success rates
    success_rates = {}
    for integration in frappe.db.get_all('External System Integration', 
                                       filters={'is_active': 1}, 
                                       fields=['system_name']):
        system_name = integration['system_name']
        
        total_syncs = len([s for s in sync_data if s['system_name'] == system_name])
        successful_syncs = len([s for s in sync_data 
                              if s['system_name'] == system_name and s['sync_status'] == 'Success'])
        
        success_rates[system_name] = {
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'success_rate': (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
        }

    return {
        'period_days': days,
        'sync_timeline': sync_data,
        'success_rates': success_rates
    }

def get_data_quality_metrics():
    """Get data quality assessment metrics"""
    try:
        # Check for duplicate contacts
        duplicate_contacts = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM (
                SELECT corebusiness_id, COUNT(*) as cnt
                FROM `tabContact`
                WHERE corebusiness_id IS NOT NULL AND corebusiness_id != ''
                GROUP BY corebusiness_id
                HAVING cnt > 1
            ) as duplicates
        """, as_dict=True)[0]['count']

        # Check for missing required fields
        missing_email = frappe.db.count('Contact', {
            'stakeholder_type': ['in', ['Employer', 'Beneficiary']],
            'email_id': ['in', ['', None]]
        })

        missing_phone = frappe.db.count('Contact', {
            'stakeholder_type': ['in', ['Employer', 'Beneficiary']],
            'mobile_no': ['in', ['', None]],
            'phone': ['in', ['', None]]
        })

        # Check for outdated records (not synced in last 7 days)
        outdated_records = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabContact`
            WHERE stakeholder_type IN ('Employer', 'Beneficiary')
            AND (modified < DATE_SUB(NOW(), INTERVAL 7 DAY) OR modified IS NULL)
        """, as_dict=True)[0]['count']

        # Calculate data completeness score
        total_contacts = frappe.db.count('Contact', {
            'stakeholder_type': ['in', ['Employer', 'Beneficiary']]
        })

        completeness_score = 0
        if total_contacts > 0:
            complete_records = total_contacts - missing_email - missing_phone - duplicate_contacts
            completeness_score = (complete_records / total_contacts) * 100

        return {
            'total_contacts': total_contacts,
            'duplicate_contacts': duplicate_contacts,
            'missing_email': missing_email,
            'missing_phone': missing_phone,
            'outdated_records': outdated_records,
            'completeness_score': completeness_score,
            'quality_issues': [
                {'type': 'Duplicates', 'count': duplicate_contacts, 'severity': 'High'},
                {'type': 'Missing Email', 'count': missing_email, 'severity': 'Medium'},
                {'type': 'Missing Phone', 'count': missing_phone, 'severity': 'Medium'},
                {'type': 'Outdated Records', 'count': outdated_records, 'severity': 'Low'}
            ]
        }

    except Exception as e:
        frappe.log_error(f"Failed to get data quality metrics: {str(e)}")
        return {
            'error': str(e),
            'completeness_score': 0
        }

def get_recent_sync_logs(limit=10):
    """Get recent synchronization logs"""
    logs = frappe.db.sql("""
        SELECT system_name, sync_status, last_sync_time, 
               last_error_message, modified
        FROM `tabExternal System Integration`
        WHERE last_sync_time IS NOT NULL
        ORDER BY last_sync_time DESC
        LIMIT %s
    """, (limit,), as_dict=True)

    return logs

@frappe.whitelist(allow_guest=False)
def get_integration_health_report():
    """Get detailed health report for all integrations"""
    try:
        health_report = []
        
        integrations = frappe.db.get_all('External System Integration',
                                       filters={'is_active': 1},
                                       fields=['name', 'system_name', 'system_type'])

        for integration in integrations:
            if integration['system_type'] == 'CoreBusiness':
                service = CoreBusinessIntegrationService()
                health = service.get_integration_health_status()
            else:
                health = {'status': 'Unknown', 'message': 'Health check not implemented'}

            # Get recent sync history
            sync_history = frappe.db.sql("""
                SELECT sync_status, last_sync_time, last_error_message
                FROM `tabExternal System Integration`
                WHERE name = %s
            """, (integration['name'],), as_dict=True)

            health_report.append({
                'integration_name': integration['system_name'],
                'system_type': integration['system_type'],
                'health_status': health,
                'sync_history': sync_history[0] if sync_history else {}
            })

        return {
            'success': True,
            'health_report': health_report,
            'report_generated': frappe.utils.now()
        }

    except Exception as e:
        frappe.log_error(f"Failed to generate health report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@frappe.whitelist(allow_guest=False)
def run_data_quality_assessment():
    """Run comprehensive data quality assessment"""
    try:
        assessment_results = {
            'assessment_time': frappe.utils.now(),
            'checks_performed': []
        }

        # Check 1: Duplicate detection
        duplicates = frappe.db.sql("""
            SELECT corebusiness_id, COUNT(*) as count, 
                   GROUP_CONCAT(name) as contact_ids
            FROM `tabContact`
            WHERE corebusiness_id IS NOT NULL AND corebusiness_id != ''
            GROUP BY corebusiness_id
            HAVING count > 1
        """, as_dict=True)

        assessment_results['checks_performed'].append({
            'check_name': 'Duplicate Detection',
            'status': 'Completed',
            'issues_found': len(duplicates),
            'details': duplicates[:10]  # Limit to first 10 for display
        })

        # Check 2: Data completeness
        incomplete_records = frappe.db.sql("""
            SELECT name, first_name, last_name, email_id, mobile_no, stakeholder_type
            FROM `tabContact`
            WHERE stakeholder_type IN ('Employer', 'Beneficiary')
            AND (email_id IS NULL OR email_id = '' OR mobile_no IS NULL OR mobile_no = '')
        """, as_dict=True)

        assessment_results['checks_performed'].append({
            'check_name': 'Data Completeness',
            'status': 'Completed',
            'issues_found': len(incomplete_records),
            'details': incomplete_records[:10]
        })

        # Check 3: Data freshness
        stale_records = frappe.db.sql("""
            SELECT name, first_name, last_name, modified, stakeholder_type
            FROM `tabContact`
            WHERE stakeholder_type IN ('Employer', 'Beneficiary')
            AND modified < DATE_SUB(NOW(), INTERVAL 30 DAY)
        """, as_dict=True)

        assessment_results['checks_performed'].append({
            'check_name': 'Data Freshness',
            'status': 'Completed',
            'issues_found': len(stale_records),
            'details': stale_records[:10]
        })

        # Check 4: Data format validation
        format_issues = frappe.db.sql("""
            SELECT name, email_id, mobile_no
            FROM `tabContact`
            WHERE stakeholder_type IN ('Employer', 'Beneficiary')
            AND (
                (email_id IS NOT NULL AND email_id != '' AND email_id NOT REGEXP '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
                OR (mobile_no IS NOT NULL AND mobile_no != '' AND mobile_no NOT REGEXP '^[0-9+\\-\\s()]{10,15}$')
            )
        """, as_dict=True)

        assessment_results['checks_performed'].append({
            'check_name': 'Data Format Validation',
            'status': 'Completed',
            'issues_found': len(format_issues),
            'details': format_issues[:10]
        })

        # Generate recommendations
        recommendations = generate_data_quality_recommendations(assessment_results)
        assessment_results['recommendations'] = recommendations

        return {
            'success': True,
            'assessment_results': assessment_results
        }

    except Exception as e:
        frappe.log_error(f"Data quality assessment failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def generate_data_quality_recommendations(assessment_results):
    """Generate recommendations based on data quality assessment"""
    recommendations = []

    for check in assessment_results['checks_performed']:
        if check['issues_found'] > 0:
            if check['check_name'] == 'Duplicate Detection':
                recommendations.append({
                    'priority': 'High',
                    'issue': f"{check['issues_found']} duplicate records found",
                    'recommendation': 'Review and merge duplicate contact records',
                    'action': 'manual_review'
                })
            
            elif check['check_name'] == 'Data Completeness':
                recommendations.append({
                    'priority': 'Medium',
                    'issue': f"{check['issues_found']} records with missing required fields",
                    'recommendation': 'Update missing email and phone information',
                    'action': 'data_enrichment'
                })
            
            elif check['check_name'] == 'Data Freshness':
                recommendations.append({
                    'priority': 'Low',
                    'issue': f"{check['issues_found']} records not updated in 30+ days",
                    'recommendation': 'Schedule regular data synchronization',
                    'action': 'sync_schedule'
                })
            
            elif check['check_name'] == 'Data Format Validation':
                recommendations.append({
                    'priority': 'Medium',
                    'issue': f"{check['issues_found']} records with invalid data formats",
                    'recommendation': 'Validate and correct email/phone formats',
                    'action': 'format_correction'
                })

    return recommendations

@frappe.whitelist(allow_guest=False)
def get_sync_performance_metrics(days=7):
    """Get synchronization performance metrics"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get sync performance data
        performance_data = frappe.db.sql("""
            SELECT system_name, 
                   COUNT(*) as total_syncs,
                   SUM(CASE WHEN sync_status = 'Success' THEN 1 ELSE 0 END) as successful_syncs,
                   AVG(TIMESTAMPDIFF(SECOND, 
                       DATE_SUB(last_sync_time, INTERVAL 1 HOUR), 
                       last_sync_time)) as avg_sync_duration
            FROM `tabExternal System Integration`
            WHERE last_sync_time BETWEEN %s AND %s
            GROUP BY system_name
        """, (start_date, end_date), as_dict=True)

        # Calculate performance metrics
        metrics = []
        for data in performance_data:
            success_rate = (data['successful_syncs'] / data['total_syncs'] * 100) if data['total_syncs'] > 0 else 0
            
            metrics.append({
                'system_name': data['system_name'],
                'total_syncs': data['total_syncs'],
                'success_rate': success_rate,
                'avg_sync_duration': data['avg_sync_duration'] or 0,
                'performance_grade': get_performance_grade(success_rate, data['avg_sync_duration'] or 0)
            })

        return {
            'success': True,
            'period_days': days,
            'performance_metrics': metrics,
            'generated_at': frappe.utils.now()
        }

    except Exception as e:
        frappe.log_error(f"Failed to get sync performance metrics: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def get_performance_grade(success_rate, avg_duration):
    """Calculate performance grade based on success rate and duration"""
    if success_rate >= 95 and avg_duration <= 60:
        return 'A'
    elif success_rate >= 90 and avg_duration <= 120:
        return 'B'
    elif success_rate >= 80 and avg_duration <= 300:
        return 'C'
    elif success_rate >= 70:
        return 'D'
    else:
        return 'F'

@frappe.whitelist(allow_guest=False)
def export_integration_report(report_type='comprehensive', format='json'):
    """Export integration monitoring report"""
    try:
        report_data = {
            'report_type': report_type,
            'generated_at': frappe.utils.now(),
            'generated_by': frappe.session.user
        }

        if report_type == 'comprehensive':
            # Include all monitoring data
            report_data.update({
                'dashboard_data': get_integration_dashboard(),
                'health_report': get_integration_health_report(),
                'data_quality': run_data_quality_assessment(),
                'performance_metrics': get_sync_performance_metrics(30)
            })
        
        elif report_type == 'health_only':
            report_data['health_report'] = get_integration_health_report()
        
        elif report_type == 'performance_only':
            report_data['performance_metrics'] = get_sync_performance_metrics(30)

        if format == 'csv':
            # Convert to CSV format (simplified)
            import csv
            import io
            
            output = io.StringIO()
            # This would need more complex logic to flatten the nested data
            # For now, return JSON with CSV indicator
            return {
                'success': True,
                'format': 'csv',
                'message': 'CSV export not fully implemented - returning JSON',
                'data': json.dumps(report_data, indent=2)
            }

        return {
            'success': True,
            'format': 'json',
            'data': report_data
        }

    except Exception as e:
        frappe.log_error(f"Failed to export integration report: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
