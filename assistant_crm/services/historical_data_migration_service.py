# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
import csv
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class HistoricalDataMigrationService:
    """
    Comprehensive service for migrating historical data from legacy systems
    to the new WCFCB Assistant CRM stakeholder management system

    DEPRECATED: The following doctypes have been removed:
    - Employer Profile (replaced by ERPNext Customer)
    - Employee Profile (replaced by ERPNext Employee)
    - Beneficiary Profile (removed - beneficiary data managed externally)
    - Assessment Record (replaced by Compliance Report)

    Migration functions for these doctypes are now no-ops.
    Use ERPNext standard import tools for Customer and Employee data.
    """

    def __init__(self):
        self.batch_size = 1000
        self.max_workers = 4
        self.migration_log = []
        self.rollback_data = {}
        self.validation_errors = []
        # Flag to indicate deprecated doctypes
        self._deprecated_doctypes = [
            "Employer Profile", "Employee Profile",
            "Beneficiary Profile", "Assessment Record"
        ]
        
    # ==================== MAIN MIGRATION ORCHESTRATOR ====================
    
    def run_full_migration(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete historical data migration"""
        try:
            migration_id = f"MIGRATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.log_migration_event(migration_id, "STARTED", "Full migration initiated")
            
            # Migration phases
            phases = [
                ("employers", self.migrate_employer_data),
                ("employees", self.migrate_employee_data),
                ("beneficiaries", self.migrate_beneficiary_data),
                ("assessments", self.migrate_assessment_data),
                ("certificates", self.migrate_certificate_data)
            ]
            
            results = {
                "migration_id": migration_id,
                "start_time": datetime.now().isoformat(),
                "phases": {},
                "overall_status": "IN_PROGRESS"
            }
            
            for phase_name, migration_func in phases:
                self.log_migration_event(migration_id, "PHASE_START", f"Starting {phase_name} migration")
                
                phase_result = migration_func(source_config.get(phase_name, {}))
                results["phases"][phase_name] = phase_result
                
                if not phase_result.get("success", False):
                    self.log_migration_event(migration_id, "PHASE_FAILED", f"{phase_name} migration failed")
                    results["overall_status"] = "FAILED"
                    break
                
                self.log_migration_event(migration_id, "PHASE_COMPLETE", f"{phase_name} migration completed")
            
            results["end_time"] = datetime.now().isoformat()
            results["overall_status"] = "COMPLETED" if results["overall_status"] != "FAILED" else "FAILED"
            
            self.log_migration_event(migration_id, "COMPLETED", f"Migration {results['overall_status']}")
            
            return results
            
        except Exception as e:
            frappe.log_error(f"Migration failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ==================== EMPLOYER DATA MIGRATION ====================

    def migrate_employer_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate employer records from legacy system.

        DEPRECATED: Employer Profile doctype has been removed.
        Use ERPNext Customer import tools instead.
        """
        # NOTE: Employer Profile doctype has been removed - use ERPNext Customer instead
        _ = config  # Unused - doctype removed
        return {
            "success": False,
            "deprecated": True,
            "message": "Employer Profile doctype removed. Use ERPNext Customer import instead.",
            "total_records": 0,
            "processed": 0,
            "failed": 0,
            "validation_errors": 0
        }
    
    def validate_employer_data(self, data: List[Dict]) -> List[Dict]:
        """Validate and cleanse employer data"""
        validated_data = []
        
        for record in data:
            try:
                # Required field validation
                if not record.get("employer_code"):
                    self.validation_errors.append(f"Missing employer_code: {record}")
                    continue
                
                if not record.get("employer_name"):
                    self.validation_errors.append(f"Missing employer_name: {record}")
                    continue
                
                # Data cleansing
                cleaned_record = {
                    "employer_code": str(record["employer_code"]).strip(),
                    "employer_name": str(record["employer_name"]).strip(),
                    "registration_status": record.get("registration_status", "Active"),
                    "registration_date": self.parse_date(record.get("registration_date")),
                    "business_type": record.get("business_type", ""),
                    "industry_sector": record.get("industry_sector", ""),
                    "contact_person": record.get("contact_person", ""),
                    "email": self.validate_email(record.get("email", "")),
                    "phone": self.clean_phone_number(record.get("phone", "")),
                    "physical_address": record.get("physical_address", ""),
                    "city": record.get("city", ""),
                    "province": self.validate_province(record.get("province", "")),
                    "tax_identification_number": record.get("tax_identification_number", ""),
                    "business_registration_number": record.get("business_registration_number", ""),
                    "total_employees": int(record.get("total_employees", 0)),
                    "compliance_status": record.get("compliance_status", "Compliant"),
                    "outstanding_contributions": float(record.get("outstanding_contributions", 0))
                }
                
                validated_data.append(cleaned_record)
                
            except Exception as e:
                self.validation_errors.append(f"Validation error for {record}: {str(e)}")
                continue
        
        return validated_data
    
    def create_employer_record(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create individual employer record"""
        try:
            # Check if employer already exists
            if frappe.db.exists("Employer Profile", data["employer_code"]):
                return False, f"Employer {data['employer_code']} already exists"
            
            # Create new employer profile
            employer_doc = frappe.new_doc("Employer Profile")
            
            for field, value in data.items():
                if hasattr(employer_doc, field):
                    setattr(employer_doc, field, value)
            
            # Set sync status to indicate migrated data
            employer_doc.sync_status = "Synced"
            employer_doc.last_sync_datetime = frappe.utils.now()
            
            employer_doc.insert()
            
            # Store rollback data
            self.rollback_data[f"Employer Profile:{data['employer_code']}"] = {
                "doctype": "Employer Profile",
                "name": data["employer_code"],
                "action": "DELETE"
            }
            
            return True, f"Employer {data['employer_code']} created successfully"
            
        except Exception as e:
            return False, f"Failed to create employer {data.get('employer_code', 'Unknown')}: {str(e)}"
    
    # ==================== EMPLOYEE DATA MIGRATION ====================

    def migrate_employee_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate employee records from legacy system.

        DEPRECATED: Employee Profile doctype has been removed.
        Use ERPNext Employee import tools instead.
        """
        # NOTE: Employee Profile doctype has been removed - use ERPNext Employee instead
        _ = config  # Unused - doctype removed
        return {
            "success": False,
            "deprecated": True,
            "message": "Employee Profile doctype removed. Use ERPNext Employee import instead.",
            "total_records": 0,
            "processed": 0,
            "failed": 0,
            "validation_errors": 0
        }
    
    def validate_employee_data(self, data: List[Dict]) -> List[Dict]:
        """Validate and cleanse employee data"""
        validated_data = []
        
        for record in data:
            try:
                # Required field validation
                if not record.get("employee_number"):
                    self.validation_errors.append(f"Missing employee_number: {record}")
                    continue
                
                if not record.get("nrc_number"):
                    self.validation_errors.append(f"Missing nrc_number: {record}")
                    continue
                
                # Validate employer exists
                employer_code = record.get("employer_code")
                if employer_code and not frappe.db.exists("Employer Profile", employer_code):
                    self.validation_errors.append(f"Employer {employer_code} not found for employee {record.get('employee_number')}")
                    continue
                
                # Data cleansing
                cleaned_record = {
                    "employee_number": str(record["employee_number"]).strip(),
                    "nrc_number": str(record["nrc_number"]).strip(),
                    "first_name": str(record.get("first_name", "")).strip(),
                    "last_name": str(record.get("last_name", "")).strip(),
                    "employer_code": employer_code,
                    "employment_status": record.get("employment_status", "Active"),
                    "employment_start_date": self.parse_date(record.get("employment_start_date")),
                    "employment_end_date": self.parse_date(record.get("employment_end_date")),
                    "job_title": record.get("job_title", ""),
                    "department": record.get("department", ""),
                    "monthly_salary": float(record.get("monthly_salary", 0)),
                    "contribution_rate": float(record.get("contribution_rate", 5.0)),
                    "date_of_birth": self.parse_date(record.get("date_of_birth")),
                    "gender": record.get("gender", ""),
                    "email": self.validate_email(record.get("email", "")),
                    "phone": self.clean_phone_number(record.get("phone", "")),
                    "physical_address": record.get("physical_address", ""),
                    "city": record.get("city", ""),
                    "province": self.validate_province(record.get("province", "")),
                    "total_contributions": float(record.get("total_contributions", 0)),
                    "benefit_status": record.get("benefit_status", "Eligible")
                }
                
                validated_data.append(cleaned_record)
                
            except Exception as e:
                self.validation_errors.append(f"Validation error for employee {record}: {str(e)}")
                continue
        
        return validated_data
    
    def create_employee_record(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create individual employee record"""
        try:
            # Check if employee already exists
            if frappe.db.exists("Employee Profile", data["employee_number"]):
                return False, f"Employee {data['employee_number']} already exists"
            
            # Create new employee profile
            employee_doc = frappe.new_doc("Employee Profile")
            
            for field, value in data.items():
                if hasattr(employee_doc, field):
                    setattr(employee_doc, field, value)
            
            # Set sync status to indicate migrated data
            employee_doc.sync_status = "Synced"
            employee_doc.last_sync_datetime = frappe.utils.now()
            
            employee_doc.insert()
            
            # Store rollback data
            self.rollback_data[f"Employee Profile:{data['employee_number']}"] = {
                "doctype": "Employee Profile",
                "name": data["employee_number"],
                "action": "DELETE"
            }
            
            return True, f"Employee {data['employee_number']} created successfully"
            
        except Exception as e:
            return False, f"Failed to create employee {data.get('employee_number', 'Unknown')}: {str(e)}"

    # ==================== BENEFICIARY DATA MIGRATION ====================

    def migrate_beneficiary_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate beneficiary records from legacy system.

        DEPRECATED: Beneficiary Profile doctype has been removed.
        Beneficiary data is now managed externally.
        """
        # NOTE: Beneficiary Profile doctype has been removed - beneficiary data managed externally
        _ = config  # Unused - doctype removed
        return {
            "success": False,
            "deprecated": True,
            "message": "Beneficiary Profile doctype removed. Beneficiary data is now managed externally.",
            "total_records": 0,
            "processed": 0,
            "failed": 0
        }

    def validate_beneficiary_data(self, data: List[Dict]) -> List[Dict]:
        """Validate and cleanse beneficiary data"""
        validated_data = []

        for record in data:
            try:
                if not record.get("beneficiary_number") or not record.get("nrc_number"):
                    self.validation_errors.append(f"Missing required fields: {record}")
                    continue

                cleaned_record = {
                    "beneficiary_number": str(record["beneficiary_number"]).strip(),
                    "nrc_number": str(record["nrc_number"]).strip(),
                    "first_name": str(record.get("first_name", "")).strip(),
                    "last_name": str(record.get("last_name", "")).strip(),
                    "employee_number": record.get("employee_number"),
                    "relationship_to_employee": record.get("relationship_to_employee", ""),
                    "benefit_type": record.get("benefit_type", ""),
                    "benefit_status": record.get("benefit_status", "Active"),
                    "benefit_start_date": self.parse_date(record.get("benefit_start_date")),
                    "monthly_benefit_amount": float(record.get("monthly_benefit_amount", 0)),
                    "date_of_birth": self.parse_date(record.get("date_of_birth")),
                    "gender": record.get("gender", ""),
                    "email": self.validate_email(record.get("email", "")),
                    "phone": self.clean_phone_number(record.get("phone", "")),
                    "city": record.get("city", ""),
                    "province": self.validate_province(record.get("province", "")),
                    "total_benefits_received": float(record.get("total_benefits_received", 0))
                }

                validated_data.append(cleaned_record)

            except Exception as e:
                self.validation_errors.append(f"Beneficiary validation error: {str(e)}")
                continue

        return validated_data

    def create_beneficiary_record(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create individual beneficiary record"""
        try:
            if frappe.db.exists("Beneficiary Profile", data["beneficiary_number"]):
                return False, f"Beneficiary {data['beneficiary_number']} already exists"

            beneficiary_doc = frappe.new_doc("Beneficiary Profile")

            for field, value in data.items():
                if hasattr(beneficiary_doc, field):
                    setattr(beneficiary_doc, field, value)

            beneficiary_doc.sync_status = "Synced"
            beneficiary_doc.last_sync_datetime = frappe.utils.now()
            beneficiary_doc.insert()

            self.rollback_data[f"Beneficiary Profile:{data['beneficiary_number']}"] = {
                "doctype": "Beneficiary Profile",
                "name": data["beneficiary_number"],
                "action": "DELETE"
            }

            return True, f"Beneficiary {data['beneficiary_number']} created successfully"

        except Exception as e:
            return False, f"Failed to create beneficiary: {str(e)}"

    # ==================== ASSESSMENT DATA MIGRATION ====================

    def migrate_assessment_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate assessment records from legacy system.

        DEPRECATED: Assessment Record doctype has been removed.
        Use Compliance Report doctype instead.
        """
        # NOTE: Assessment Record doctype has been removed - use Compliance Report instead
        _ = config  # Unused - doctype removed
        return {
            "success": False,
            "deprecated": True,
            "message": "Assessment Record doctype removed. Use Compliance Report instead.",
            "total_records": 0,
            "processed": 0,
            "failed": 0
        }

    def validate_assessment_data(self, data: List[Dict]) -> List[Dict]:
        """Validate and cleanse assessment data"""
        validated_data = []

        for record in data:
            try:
                if not record.get("employer_code") or not record.get("assessment_date"):
                    self.validation_errors.append(f"Missing required assessment fields: {record}")
                    continue

                cleaned_record = {
                    "assessment_date": self.parse_date(record["assessment_date"]),
                    "assessment_type": record.get("assessment_type", "Regular"),
                    "assessment_status": record.get("assessment_status", "Completed"),
                    "employer_code": record["employer_code"],
                    "assessment_period_from": self.parse_date(record.get("assessment_period_from")),
                    "assessment_period_to": self.parse_date(record.get("assessment_period_to")),
                    "total_employees_assessed": int(record.get("total_employees_assessed", 0)),
                    "total_contributions_assessed": float(record.get("total_contributions_assessed", 0)),
                    "penalty_amount": float(record.get("penalty_amount", 0)),
                    "interest_amount": float(record.get("interest_amount", 0)),
                    "assessment_officer": record.get("assessment_officer", ""),
                    "payment_status": record.get("payment_status", "Unpaid"),
                    "payment_due_date": self.parse_date(record.get("payment_due_date")),
                    "amount_paid": float(record.get("amount_paid", 0))
                }

                validated_data.append(cleaned_record)

            except Exception as e:
                self.validation_errors.append(f"Assessment validation error: {str(e)}")
                continue

        return validated_data

    def create_assessment_record(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create individual assessment record"""
        try:
            assessment_doc = frappe.new_doc("Assessment Record")

            for field, value in data.items():
                if hasattr(assessment_doc, field):
                    setattr(assessment_doc, field, value)

            assessment_doc.sync_status = "Synced"
            assessment_doc.last_sync_datetime = frappe.utils.now()
            assessment_doc.insert()

            self.rollback_data[f"Assessment Record:{assessment_doc.name}"] = {
                "doctype": "Assessment Record",
                "name": assessment_doc.name,
                "action": "DELETE"
            }

            return True, f"Assessment {assessment_doc.name} created successfully"

        except Exception as e:
            return False, f"Failed to create assessment: {str(e)}"

    # ==================== CERTIFICATE DATA MIGRATION ====================

    def migrate_certificate_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate certificate records from legacy system"""
        try:
            source_data = self.load_source_data(config)
            validated_data = self.validate_certificate_data(source_data)

            results = self.process_data_in_batches(
                validated_data,
                self.create_certificate_record,
                "Certificate Status"
            )

            return {
                "success": True,
                "total_records": len(source_data),
                "processed": results["processed"],
                "failed": results["failed"]
            }

        except Exception as e:
            frappe.log_error(f"Certificate migration failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def validate_certificate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate and cleanse certificate data"""
        validated_data = []

        for record in data:
            try:
                if not record.get("certificate_number") or not record.get("issue_date"):
                    self.validation_errors.append(f"Missing required certificate fields: {record}")
                    continue

                cleaned_record = {
                    "certificate_number": str(record["certificate_number"]).strip(),
                    "certificate_type": record.get("certificate_type", "Compliance Certificate"),
                    "certificate_status": record.get("certificate_status", "Valid"),
                    "issue_date": self.parse_date(record["issue_date"]),
                    "expiry_date": self.parse_date(record.get("expiry_date")),
                    "employer_code": record.get("employer_code"),
                    "employee_number": record.get("employee_number"),
                    "issued_by": record.get("issued_by", "WCFCB"),
                    "issued_for_purpose": record.get("issued_for_purpose", ""),
                    "validity_period_months": int(record.get("validity_period_months", 12)),
                    "renewal_required": bool(record.get("renewal_required", False))
                }

                validated_data.append(cleaned_record)

            except Exception as e:
                self.validation_errors.append(f"Certificate validation error: {str(e)}")
                continue

        return validated_data

    def create_certificate_record(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create individual certificate record"""
        try:
            if frappe.db.exists("Certificate Status", data["certificate_number"]):
                return False, f"Certificate {data['certificate_number']} already exists"

            certificate_doc = frappe.new_doc("Certificate Status")

            for field, value in data.items():
                if hasattr(certificate_doc, field):
                    setattr(certificate_doc, field, value)

            certificate_doc.sync_status = "Synced"
            certificate_doc.last_sync_datetime = frappe.utils.now()
            certificate_doc.insert()

            self.rollback_data[f"Certificate Status:{data['certificate_number']}"] = {
                "doctype": "Certificate Status",
                "name": data["certificate_number"],
                "action": "DELETE"
            }

            return True, f"Certificate {data['certificate_number']} created successfully"

        except Exception as e:
            return False, f"Failed to create certificate: {str(e)}"

    # ==================== UTILITY METHODS ====================

    def load_source_data(self, config: Dict[str, Any]) -> List[Dict]:
        """Load source data from various formats"""
        try:
            source_type = config.get("source_type", "csv")
            source_path = config.get("source_path", "")

            if source_type == "csv":
                return self.load_csv_data(source_path)
            elif source_type == "json":
                return self.load_json_data(source_path)
            elif source_type == "excel":
                return self.load_excel_data(source_path)
            elif source_type == "database":
                return self.load_database_data(config)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

        except Exception as e:
            frappe.log_error(f"Error loading source data: {str(e)}")
            return []

    def load_csv_data(self, file_path: str) -> List[Dict]:
        """Load data from CSV file"""
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                data = list(reader)
        except Exception as e:
            frappe.log_error(f"Error loading CSV data: {str(e)}")
        return data

    def load_json_data(self, file_path: str) -> List[Dict]:
        """Load data from JSON file"""
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            frappe.log_error(f"Error loading JSON data: {str(e)}")
        return data

    def load_excel_data(self, file_path: str) -> List[Dict]:
        """Load data from Excel file"""
        data = []
        try:
            df = pd.read_excel(file_path)
            data = df.to_dict('records')
        except Exception as e:
            frappe.log_error(f"Error loading Excel data: {str(e)}")
        return data

    def load_database_data(self, config: Dict[str, Any]) -> List[Dict]:
        """Load data from database query"""
        data = []
        try:
            query = config.get("query", "")
            if query:
                data = frappe.db.sql(query, as_dict=True)
        except Exception as e:
            frappe.log_error(f"Error loading database data: {str(e)}")
        return data

    def process_data_in_batches(self, data: List[Dict], process_func, doctype: str) -> Dict[str, int]:
        """Process data in batches with parallel processing"""
        total_records = len(data)
        processed = 0
        failed = 0

        # Process in batches
        for i in range(0, total_records, self.batch_size):
            batch = data[i:i + self.batch_size]

            # Parallel processing within batch
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(process_func, record) for record in batch]

                for future in as_completed(futures):
                    try:
                        success, message = future.result()
                        if success:
                            processed += 1
                        else:
                            failed += 1
                            self.log_migration_event("BATCH", "RECORD_FAILED", message)
                    except Exception as e:
                        failed += 1
                        self.log_migration_event("BATCH", "RECORD_ERROR", str(e))

            # Progress logging
            progress = ((i + len(batch)) / total_records) * 100
            self.log_migration_event("BATCH", "PROGRESS", f"{doctype}: {progress:.1f}% complete")

            # Commit batch
            frappe.db.commit()

            # Brief pause to prevent system overload
            time.sleep(0.1)

        return {"processed": processed, "failed": failed}

    # ==================== DATA VALIDATION UTILITIES ====================

    def parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to Frappe date format"""
        if not date_str:
            return None

        try:
            # Try multiple date formats
            date_formats = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%Y/%m/%d"
            ]

            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(str(date_str), fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            # If no format matches, try pandas date parser
            try:
                parsed_date = pd.to_datetime(date_str)
                return parsed_date.strftime("%Y-%m-%d")
            except:
                pass

            return None

        except Exception:
            return None

    def validate_email(self, email: str) -> str:
        """Validate and clean email address"""
        if not email:
            return ""

        email = str(email).strip().lower()

        # Basic email validation
        if "@" in email and "." in email.split("@")[1]:
            return email

        return ""

    def clean_phone_number(self, phone: str) -> str:
        """Clean and standardize phone number"""
        if not phone:
            return ""

        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in str(phone) if c.isdigit() or c == '+')

        # Add Zambia country code if missing
        if cleaned and not cleaned.startswith('+'):
            if cleaned.startswith('260'):
                cleaned = '+' + cleaned
            elif len(cleaned) == 9:  # Local number
                cleaned = '+260' + cleaned

        return cleaned

    def validate_province(self, province: str) -> str:
        """Validate Zambian province"""
        if not province:
            return ""

        valid_provinces = [
            "Central", "Copperbelt", "Eastern", "Luapula", "Lusaka",
            "Muchinga", "Northern", "North-Western", "Southern", "Western"
        ]

        province = str(province).strip().title()

        # Exact match
        if province in valid_provinces:
            return province

        # Fuzzy matching
        for valid_province in valid_provinces:
            if province.lower() in valid_province.lower() or valid_province.lower() in province.lower():
                return valid_province

        return province  # Return original if no match found

    # ==================== ROLLBACK FUNCTIONALITY ====================

    def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """Rollback migration changes"""
        try:
            self.log_migration_event(migration_id, "ROLLBACK_START", "Starting migration rollback")

            rollback_results = {
                "migration_id": migration_id,
                "rollback_start": datetime.now().isoformat(),
                "deleted_records": 0,
                "failed_deletions": 0,
                "errors": []
            }

            # Process rollback data
            for record_key, rollback_info in self.rollback_data.items():
                try:
                    if rollback_info["action"] == "DELETE":
                        doctype = rollback_info["doctype"]
                        name = rollback_info["name"]

                        if frappe.db.exists(doctype, name):
                            frappe.delete_doc(doctype, name)
                            rollback_results["deleted_records"] += 1
                            self.log_migration_event(migration_id, "ROLLBACK_DELETE", f"Deleted {doctype}: {name}")

                except Exception as e:
                    rollback_results["failed_deletions"] += 1
                    rollback_results["errors"].append(f"Failed to delete {record_key}: {str(e)}")
                    self.log_migration_event(migration_id, "ROLLBACK_ERROR", f"Failed to delete {record_key}: {str(e)}")

            rollback_results["rollback_end"] = datetime.now().isoformat()

            # Commit rollback changes
            frappe.db.commit()

            self.log_migration_event(migration_id, "ROLLBACK_COMPLETE", "Migration rollback completed")

            return {"success": True, "results": rollback_results}

        except Exception as e:
            frappe.log_error(f"Rollback failed: {str(e)}")
            return {"success": False, "error": str(e)}

    # ==================== LOGGING AND MONITORING ====================

    def log_migration_event(self, migration_id: str, event_type: str, message: str):
        """Log migration events for monitoring and debugging"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "migration_id": migration_id,
            "event_type": event_type,
            "message": message
        }

        self.migration_log.append(log_entry)

        # Also log to Frappe error log for persistence
        frappe.log_error(f"[{migration_id}] {event_type}: {message}", "Migration Log")

    def get_migration_progress(self, migration_id: str) -> Dict[str, Any]:
        """Get current migration progress"""
        try:
            # Filter logs for this migration
            migration_logs = [log for log in self.migration_log if log["migration_id"] == migration_id]

            # Calculate progress based on phase completion
            phases = ["employers", "employees", "beneficiaries", "assessments", "certificates"]
            completed_phases = 0

            for phase in phases:
                phase_complete = any(
                    log["event_type"] == "PHASE_COMPLETE" and phase in log["message"].lower()
                    for log in migration_logs
                )
                if phase_complete:
                    completed_phases += 1

            progress_percentage = (completed_phases / len(phases)) * 100

            # Get latest status
            latest_log = migration_logs[-1] if migration_logs else None
            current_status = latest_log["event_type"] if latest_log else "NOT_STARTED"

            return {
                "migration_id": migration_id,
                "progress_percentage": progress_percentage,
                "completed_phases": completed_phases,
                "total_phases": len(phases),
                "current_status": current_status,
                "total_events": len(migration_logs),
                "validation_errors": len(self.validation_errors),
                "last_update": latest_log["timestamp"] if latest_log else None
            }

        except Exception as e:
            frappe.log_error(f"Error getting migration progress: {str(e)}")
            return {"error": str(e)}

    def generate_migration_report(self, migration_id: str) -> Dict[str, Any]:
        """Generate comprehensive migration report"""
        try:
            progress = self.get_migration_progress(migration_id)

            # Get record counts for each DocType
            # NOTE: Several doctypes have been removed:
            # - Employer Profile (removed - use ERPNext Customer)
            # - Employee Profile (removed - use ERPNext Employee)
            # - Beneficiary Profile (removed - beneficiary data managed externally)
            # - Assessment Record (removed - use Compliance Report)
            record_counts = {}
            doctypes = ["Customer", "Employee", "Compliance Report", "Certificate Status"]

            for doctype in doctypes:
                try:
                    record_counts[doctype] = frappe.db.count(doctype)
                except Exception:
                    record_counts[doctype] = 0

            # Get validation errors summary
            error_summary = {}
            for error in self.validation_errors:
                error_type = error.split(":")[0] if ":" in error else "General"
                error_summary[error_type] = error_summary.get(error_type, 0) + 1

            return {
                "migration_id": migration_id,
                "progress": progress,
                "record_counts": record_counts,
                "validation_errors": {
                    "total": len(self.validation_errors),
                    "by_type": error_summary
                },
                "rollback_data_available": len(self.rollback_data) > 0,
                "report_generated": datetime.now().isoformat()
            }

        except Exception as e:
            frappe.log_error(f"Error generating migration report: {str(e)}")
            return {"error": str(e)}
