import frappe
import json

def setup_phase4():
    """Setup Phase 4 components for WCFCB system"""
    
    print("🚀 Setting up Phase 4 components...")
    
    # Create Agent Profile DocType
    create_agent_profile_doctype()
    
    # Create sample message templates
    create_sample_templates()
    
    # Create sample agent profiles
    create_sample_agents()
    
    frappe.db.commit()
    print("✅ Phase 4 setup complete!")

def create_agent_profile_doctype():
    """Create Agent Profile DocType"""
    
    if frappe.db.exists("DocType", "Agent Profile"):
        print("⚠️ Agent Profile DocType already exists")
        return
    
    agent_profile = {
        "doctype": "DocType",
        "name": "Agent Profile",
        "module": "Assistant CRM",
        "custom": 1,
        "is_submittable": 0,
        "track_changes": 1,
        "fields": [
            {
                "fieldname": "user",
                "label": "User",
                "fieldtype": "Link",
                "options": "User",
                "reqd": 1,
                "unique": 1
            },
            {
                "fieldname": "full_name",
                "label": "Full Name",
                "fieldtype": "Data",
                "reqd": 1
            },
            {
                "fieldname": "skills",
                "label": "Skills (JSON)",
                "fieldtype": "Long Text",
                "description": "JSON array of agent skills"
            },
            {
                "fieldname": "languages",
                "label": "Languages (JSON)",
                "fieldtype": "Long Text",
                "description": "JSON array of supported languages"
            },
            {
                "fieldname": "experience_level",
                "label": "Experience Level",
                "fieldtype": "Select",
                "options": "Trainee\nJunior\nIntermediate\nSenior\nExpert",
                "default": "Intermediate"
            },
            {
                "fieldname": "max_concurrent_conversations",
                "label": "Max Concurrent Conversations",
                "fieldtype": "Int",
                "default": 5
            },
            {
                "fieldname": "current_workload",
                "label": "Current Workload",
                "fieldtype": "Int",
                "default": 0
            },
            {
                "fieldname": "availability_status",
                "label": "Availability Status",
                "fieldtype": "Select",
                "options": "Available\nBusy\nAway\nOffline",
                "default": "Available"
            },
            {
                "fieldname": "performance_rating",
                "label": "Performance Rating",
                "fieldtype": "Float",
                "default": 4.0
            },
            {
                "fieldname": "is_active",
                "label": "Is Active",
                "fieldtype": "Check",
                "default": 1
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1
            }
        ]
    }
    
    try:
        doc = frappe.get_doc(agent_profile)
        doc.insert()
        print("✅ Created Agent Profile DocType")
    except Exception as e:
        print(f"❌ Failed to create Agent Profile DocType: {str(e)}")

def create_sample_templates():
    """Create sample message templates"""
    
    templates = [
        {
            "template_name": "Payment Reminder - 30 Days Advance",
            "template_type": "Payment Reminder Advance",
            "language": "en",
            "subject": "WCFCB Payment Due in 30 Days - Employer {employer_number}",
            "content": """Dear {employer_name},

This is a friendly reminder that your Workers' Compensation premium payment is due in 30 days.

**Payment Details:**
- Employer Number: {employer_number}
- Amount Due: K{amount_due}
- Due Date: {due_date}

**Payment Options:**
1. Online Banking Transfer
2. Bank Deposit at any WCFCB approved bank
3. Mobile Money (MTN, Airtel, Zamtel)
4. Visit our offices for cash payment

Best regards,
Anna - WCFCB Virtual Assistant
Workers' Compensation Fund Control Board""",
            "is_active": 1
        },
        {
            "template_name": "Payment Reminder - Overdue",
            "template_type": "Payment Reminder Overdue",
            "language": "en",
            "subject": "OVERDUE: WCFCB Payment - Immediate Action Required",
            "content": """Dear {employer_name},

**PAYMENT OVERDUE NOTICE**

Your Workers' Compensation premium payment is now {days_overdue} days overdue.

**URGENT ACTION REQUIRED:**
1. Pay the full amount immediately
2. Contact us to discuss payment arrangements
3. Provide proof of payment within 24 hours

This is a serious matter requiring immediate attention.

Best regards,
Anna - WCFCB Virtual Assistant
Workers' Compensation Fund Control Board""",
            "is_active": 1
        }
    ]
    
    created_count = 0
    for template_data in templates:
        try:
            if not frappe.db.exists("Message Template", template_data["template_name"]):
                template_doc = frappe.get_doc({
                    "doctype": "Message Template",
                    **template_data
                })
                template_doc.insert()
                created_count += 1
                print(f"   ✅ Created template: {template_data['template_name']}")
            else:
                print(f"   ⚠️ Template already exists: {template_data['template_name']}")
        except Exception as e:
            print(f"   ❌ Failed to create template {template_data['template_name']}: {str(e)}")
    
    print(f"📝 Created {created_count} message templates")

def create_sample_agents():
    """Create sample agent profiles"""
    
    # Check if Agent Profile DocType exists
    if not frappe.db.exists("DocType", "Agent Profile"):
        print("❌ Agent Profile DocType not found, skipping agent creation")
        return
    
    agents = [
        {
            "user": "sarah.mwanza@wcfcb.gov.zm",
            "full_name": "Sarah Mwanza",
            "skills": json.dumps(["payments", "billing", "conflict_resolution"]),
            "languages": json.dumps(["en", "bem", "ny"]),
            "experience_level": "Senior",
            "max_concurrent_conversations": 8,
            "current_workload": 0,
            "availability_status": "Available",
            "performance_rating": 4.8,
            "is_active": 1
        },
        {
            "user": "john.banda@wcfcb.gov.zm",
            "full_name": "John Banda",
            "skills": json.dumps(["claims", "injury_assessment", "empathy"]),
            "languages": json.dumps(["en", "ny", "to"]),
            "experience_level": "Intermediate",
            "max_concurrent_conversations": 6,
            "current_workload": 0,
            "availability_status": "Available",
            "performance_rating": 4.5,
            "is_active": 1
        }
    ]
    
    created_count = 0
    for agent_data in agents:
        try:
            if not frappe.db.exists("Agent Profile", {"user": agent_data["user"]}):
                agent_doc = frappe.get_doc({
                    "doctype": "Agent Profile",
                    **agent_data
                })
                agent_doc.insert()
                created_count += 1
                print(f"   ✅ Created agent: {agent_data['full_name']}")
            else:
                print(f"   ⚠️ Agent already exists: {agent_data['full_name']}")
        except Exception as e:
            print(f"   ❌ Failed to create agent {agent_data['full_name']}: {str(e)}")
    
    print(f"👥 Created {created_count} agent profiles")

def test_phase4_services():
    """Test Phase 4 services"""
    
    print("\n🧪 Testing Phase 4 services...")
    
    # Test 1: Auto-Reminder Service
    try:
        from assistant_crm.services.auto_reminder_service import AutoReminderService
        reminder_service = AutoReminderService()
        print("   ✅ Auto-Reminder Service: Available")
    except Exception as e:
        print(f"   ❌ Auto-Reminder Service: {str(e)}")
    
    # Test 2: Agent Skill Matching
    try:
        from assistant_crm.services.agent_skill_matching_service import AgentSkillMatchingService
        agent_service = AgentSkillMatchingService()
        print("   ✅ Agent Skill Matching Service: Available")
    except Exception as e:
        print(f"   ❌ Agent Skill Matching Service: {str(e)}")
    
    # Test 3: Predictive Analytics
    try:
        from assistant_crm.services.predictive_analytics_service import PredictiveAnalyticsService
        analytics_service = PredictiveAnalyticsService()
        print("   ✅ Predictive Analytics Service: Available")
    except Exception as e:
        print(f"   ❌ Predictive Analytics Service: {str(e)}")
    
    # Test 4: Enhanced Sentiment Analysis
    try:
        from assistant_crm.services.sentiment_analysis_service import SentimentAnalysisService
        sentiment_service = SentimentAnalysisService()
        if hasattr(sentiment_service, 'analyze_urgency'):
            print("   ✅ Enhanced Sentiment Analysis: Available")
        else:
            print("   ⚠️ Enhanced Sentiment Analysis: Basic version only")
    except Exception as e:
        print(f"   ❌ Enhanced Sentiment Analysis: {str(e)}")
    
    print("🎯 Phase 4 service testing complete!")

if __name__ == "__main__":
    setup_phase4()
    test_phase4_services()
