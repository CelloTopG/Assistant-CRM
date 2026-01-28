import frappe
import json
import os
from datetime import datetime

def run_migration_audit():
    """Run comprehensive migration audit for WCFCB Assistant CRM"""
    
    print("🔍 WCFCB ASSISTANT CRM - MIGRATION AUDIT")
    print("=" * 50)
    
    audit_results = {
        "timestamp": datetime.now().isoformat(),
        "doctypes": {},
        "services": {},
        "api_endpoints": {},
        "configuration_records": {},
        "dependencies": {},
        "overall_status": {}
    }
    
    # 1. Check Database Schema Updates - DocTypes
    print("\n1. DATABASE SCHEMA UPDATES - DOCTYPES:")
    print("-" * 40)
    
    phase_doctypes = [
        # Phase A DocTypes
        ("VoIP Settings", "Phase A"),
        ("Call Log", "Phase A"), 
        ("Social Media Settings", "Phase A"),
        ("CoreBusiness Settings", "Phase A"),
        
        # Phase B DocTypes
        ("Advanced Social Media Settings", "Phase B"),
        ("Enhanced AI Settings", "Phase B"),
        ("Cross Platform Broadcasting Settings", "Phase B"),
        ("Advanced Analytics Settings", "Phase B"),
        
        # Phase C DocTypes
        ("Advanced Automation Settings", "Phase C"),
        ("Automation Rule", "Phase C"),
        ("Automation Execution Log", "Phase C"),
        ("Regulatory Compliance Settings", "Phase C"),
        ("Compliance Report", "Phase C"),
        ("Audit Log", "Phase C")
    ]
    
    doctype_status = {}
    for doctype_name, phase in phase_doctypes:
        try:
            exists = frappe.db.exists("DocType", doctype_name)
            if exists:
                print(f"   ✅ {doctype_name} ({phase}): EXISTS")
                doctype_status[doctype_name] = {"status": "EXISTS", "phase": phase}
            else:
                print(f"   ❌ {doctype_name} ({phase}): MISSING")
                doctype_status[doctype_name] = {"status": "MISSING", "phase": phase}
        except Exception as e:
            print(f"   ⚠️ {doctype_name} ({phase}): ERROR - {str(e)}")
            doctype_status[doctype_name] = {"status": "ERROR", "phase": phase, "error": str(e)}
    
    audit_results["doctypes"] = doctype_status
    existing_doctypes = sum(1 for dt in doctype_status.values() if dt["status"] == "EXISTS")
    print(f"\nDocType Summary: {existing_doctypes}/{len(phase_doctypes)} created")
    
    # 2. Check Service Files Existence
    print("\n2. SERVICE FILES:")
    print("-" * 40)
    
    service_files = [
        # Phase A Services
        ("voip_service.py", "Phase A"),
        ("social_media_integration_service.py", "Phase A"),
        ("corebusiness_integration_service.py", "Phase A"),
        
        # Phase B Services
        ("advanced_social_media_service.py", "Phase B"),
        ("enhanced_ai_service.py", "Phase B"),
        ("cross_platform_broadcasting_service.py", "Phase B"),
        ("advanced_analytics_service.py", "Phase B"),
        
        # Phase C Services
        ("advanced_automation_service.py", "Phase C"),
        ("regulatory_compliance_service.py", "Phase C"),
        ("workflow_optimization_service.py", "Phase C")
    ]
    
    service_file_status = {}
    services_path = "/workspace/development/frappe-bench/apps/assistant_crm/assistant_crm/services"
    
    for service_file, phase in service_files:
        file_path = os.path.join(services_path, service_file)
        if os.path.exists(file_path):
            print(f"   ✅ {service_file} ({phase}): EXISTS")
            service_file_status[service_file] = {"status": "EXISTS", "phase": phase}
        else:
            print(f"   ❌ {service_file} ({phase}): MISSING")
            service_file_status[service_file] = {"status": "MISSING", "phase": phase}
    
    existing_services = sum(1 for sf in service_file_status.values() if sf["status"] == "EXISTS")
    print(f"\nService Files Summary: {existing_services}/{len(service_files)} exist")
    
    # 3. Check API Endpoint Files
    print("\n3. API ENDPOINT FILES:")
    print("-" * 40)
    
    api_files = [
        ("voip_api.py", "Phase A"),
        ("social_media_api.py", "Phase A"),
        ("phase_b_api.py", "Phase B"),
        ("phase_c_api.py", "Phase C")
    ]
    
    api_file_status = {}
    api_path = "/workspace/development/frappe-bench/apps/assistant_crm/assistant_crm/api"
    
    for api_file, phase in api_files:
        file_path = os.path.join(api_path, api_file)
        if os.path.exists(file_path):
            print(f"   ✅ {api_file} ({phase}): EXISTS")
            api_file_status[api_file] = {"status": "EXISTS", "phase": phase}
        else:
            print(f"   ❌ {api_file} ({phase}): MISSING")
            api_file_status[api_file] = {"status": "MISSING", "phase": phase}
    
    audit_results["api_endpoints"] = api_file_status
    existing_apis = sum(1 for af in api_file_status.values() if af["status"] == "EXISTS")
    print(f"\nAPI Files Summary: {existing_apis}/{len(api_files)} exist")
    
    # 4. Check Configuration Records
    print("\n4. CONFIGURATION RECORDS:")
    print("-" * 40)
    
    config_doctypes = [
        ("VoIP Settings", "Phase A"),
        ("Social Media Settings", "Phase A"),
        ("CoreBusiness Settings", "Phase A"),
        ("Advanced Social Media Settings", "Phase B"),
        ("Enhanced AI Settings", "Phase B"),
        ("Advanced Automation Settings", "Phase C"),
        ("Regulatory Compliance Settings", "Phase C")
    ]
    
    config_status = {}
    for config_doctype, phase in config_doctypes:
        try:
            if frappe.db.exists("DocType", config_doctype):
                # Check if configuration record exists
                record_exists = frappe.db.exists(config_doctype, config_doctype)
                if record_exists:
                    print(f"   ✅ {config_doctype} ({phase}): CONFIGURED")
                    config_status[config_doctype] = {"status": "CONFIGURED", "phase": phase}
                else:
                    print(f"   ⚠️ {config_doctype} ({phase}): DOCTYPE EXISTS, NO CONFIG")
                    config_status[config_doctype] = {"status": "NO_CONFIG", "phase": phase}
            else:
                print(f"   ❌ {config_doctype} ({phase}): DOCTYPE MISSING")
                config_status[config_doctype] = {"status": "DOCTYPE_MISSING", "phase": phase}
        except Exception as e:
            print(f"   ⚠️ {config_doctype} ({phase}): ERROR - {str(e)}")
            config_status[config_doctype] = {"status": "ERROR", "phase": phase, "error": str(e)}
    
    audit_results["configuration_records"] = config_status
    configured_settings = sum(1 for cs in config_status.values() if cs["status"] == "CONFIGURED")
    print(f"\nConfiguration Summary: {configured_settings}/{len(config_doctypes)} configured")
    
    # 5. Check Python Dependencies
    print("\n5. PYTHON DEPENDENCIES:")
    print("-" * 40)
    
    required_packages = [
        ("pandas", "pandas", "Phase B/C - Data analysis"),
        ("numpy", "numpy", "Phase B/C - Numerical computing"),
        ("scikit-learn", "sklearn", "Phase B/C - Machine learning"),
        ("requests", "requests", "All Phases - HTTP requests"),
        ("schedule", "schedule", "Phase C - Task scheduling"),
        ("openai", "openai", "Phase B - AI services"),
        ("textstat", "textstat", "Phase B - Text analysis")
    ]

    dependency_status = {}
    for package_name, import_name, description in required_packages:
        try:
            __import__(import_name)
            print(f"   ✅ {package_name}: INSTALLED ({description})")
            dependency_status[package_name] = {"status": "INSTALLED", "description": description}
        except ImportError:
            print(f"   ❌ {package_name}: MISSING ({description})")
            dependency_status[package_name] = {"status": "MISSING", "description": description}
    
    audit_results["dependencies"] = dependency_status
    installed_packages = sum(1 for ds in dependency_status.values() if ds["status"] == "INSTALLED")
    print(f"\nDependency Summary: {installed_packages}/{len(required_packages)} installed")
    
    # 6. Overall Status Summary
    print("\n6. OVERALL STATUS SUMMARY:")
    print("-" * 40)
    
    phase_summary = {
        "Phase A": {
            "doctypes": sum(1 for dt, info in doctype_status.items() if info["phase"] == "Phase A" and info["status"] == "EXISTS"),
            "total_doctypes": sum(1 for dt, info in doctype_status.items() if info["phase"] == "Phase A"),
            "services": sum(1 for sf, info in service_file_status.items() if info["phase"] == "Phase A" and info["status"] == "EXISTS"),
            "total_services": sum(1 for sf, info in service_file_status.items() if info["phase"] == "Phase A"),
            "configs": sum(1 for cs, info in config_status.items() if info["phase"] == "Phase A" and info["status"] == "CONFIGURED"),
            "total_configs": sum(1 for cs, info in config_status.items() if info["phase"] == "Phase A")
        },
        "Phase B": {
            "doctypes": sum(1 for dt, info in doctype_status.items() if info["phase"] == "Phase B" and info["status"] == "EXISTS"),
            "total_doctypes": sum(1 for dt, info in doctype_status.items() if info["phase"] == "Phase B"),
            "services": sum(1 for sf, info in service_file_status.items() if info["phase"] == "Phase B" and info["status"] == "EXISTS"),
            "total_services": sum(1 for sf, info in service_file_status.items() if info["phase"] == "Phase B"),
            "configs": sum(1 for cs, info in config_status.items() if info["phase"] == "Phase B" and info["status"] == "CONFIGURED"),
            "total_configs": sum(1 for cs, info in config_status.items() if info["phase"] == "Phase B")
        },
        "Phase C": {
            "doctypes": sum(1 for dt, info in doctype_status.items() if info["phase"] == "Phase C" and info["status"] == "EXISTS"),
            "total_doctypes": sum(1 for dt, info in doctype_status.items() if info["phase"] == "Phase C"),
            "services": sum(1 for sf, info in service_file_status.items() if info["phase"] == "Phase C" and info["status"] == "EXISTS"),
            "total_services": sum(1 for sf, info in service_file_status.items() if info["phase"] == "Phase C"),
            "configs": sum(1 for cs, info in config_status.items() if info["phase"] == "Phase C" and info["status"] == "CONFIGURED"),
            "total_configs": sum(1 for cs, info in config_status.items() if info["phase"] == "Phase C")
        }
    }
    
    for phase, stats in phase_summary.items():
        doctype_pct = (stats["doctypes"] / max(1, stats["total_doctypes"])) * 100
        service_pct = (stats["services"] / max(1, stats["total_services"])) * 100
        config_pct = (stats["configs"] / max(1, stats["total_configs"])) * 100
        overall_pct = (doctype_pct + service_pct + config_pct) / 3
        
        status_icon = "✅" if overall_pct >= 80 else "⚠️" if overall_pct >= 50 else "❌"
        
        print(f"   {status_icon} {phase}: {overall_pct:.1f}% complete")
        print(f"      - DocTypes: {stats['doctypes']}/{stats['total_doctypes']} ({doctype_pct:.1f}%)")
        print(f"      - Services: {stats['services']}/{stats['total_services']} ({service_pct:.1f}%)")
        print(f"      - Configs: {stats['configs']}/{stats['total_configs']} ({config_pct:.1f}%)")
    
    # Calculate overall system readiness
    total_doctypes = len(phase_doctypes)
    total_services = len(service_files)
    total_configs = len(config_doctypes)
    total_dependencies = len(required_packages)
    
    overall_readiness = (
        (existing_doctypes / total_doctypes) * 0.3 +
        (existing_services / total_services) * 0.3 +
        (configured_settings / total_configs) * 0.2 +
        (installed_packages / total_dependencies) * 0.2
    ) * 100
    
    print(f"\n🎯 OVERALL SYSTEM READINESS: {overall_readiness:.1f}%")
    
    if overall_readiness >= 90:
        print("🎉 System is PRODUCTION READY!")
    elif overall_readiness >= 70:
        print("⚠️ System needs minor setup to be production ready")
    else:
        print("❌ System requires significant setup before production deployment")
    
    audit_results["overall_status"] = {
        "readiness_percentage": overall_readiness,
        "phase_summary": phase_summary,
        "total_doctypes": total_doctypes,
        "existing_doctypes": existing_doctypes,
        "total_services": total_services,
        "existing_services": existing_services,
        "total_configs": total_configs,
        "configured_settings": configured_settings,
        "total_dependencies": total_dependencies,
        "installed_packages": installed_packages
    }
    
    return audit_results

if __name__ == "__main__":
    run_migration_audit()
