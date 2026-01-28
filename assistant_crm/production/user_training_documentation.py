#!/usr/bin/env python3
"""
WCFCB Assistant CRM - User Training & Documentation System
Production Deployment Phase: Comprehensive user guides and training materials
Creates persona-specific documentation, in-app help, and training resources
"""

import frappe
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

@dataclass
class DocumentationSection:
    """Documentation section structure"""
    id: str
    title: str
    content: str
    persona: str
    category: str
    difficulty: str
    estimated_time: int
    prerequisites: List[str]
    related_sections: List[str]

@dataclass
class TrainingModule:
    """Training module structure"""
    id: str
    title: str
    description: str
    persona: str
    sections: List[DocumentationSection]
    completion_criteria: Dict
    assessment_questions: List[Dict]

class UserTrainingDocumentationSystem:
    """
    Comprehensive user training and documentation system
    Provides persona-specific guides, in-app help, and training materials
    """
    
    def __init__(self):
        self.documentation_sections = {}
        self.training_modules = {}
        self.user_progress = {}
        self.feedback_data = {}
        
        # Initialize documentation
        self.initialize_documentation()
        self.initialize_training_modules()
        
    def initialize_documentation(self) -> None:
        """Initialize comprehensive documentation sections"""
        try:
            # Beneficiary documentation
            self.create_beneficiary_documentation()
            
            # Employer documentation
            self.create_employer_documentation()
            
            # Supplier documentation
            self.create_supplier_documentation()
            
            # WCFCB Staff documentation
            self.create_staff_documentation()
            
            # Administrator documentation
            self.create_administrator_documentation()
            
            logging.info("Documentation sections initialized")
            
        except Exception as e:
            logging.error(f"Documentation initialization error: {str(e)}")
            raise
    
    def create_beneficiary_documentation(self) -> None:
        """Create documentation for beneficiaries"""
        sections = [
            DocumentationSection(
                id="beneficiary_getting_started",
                title="Getting Started with Anna - Your WCFCB Assistant",
                content="""
# Welcome to Anna - Your Personal WCFCB Assistant! 😊

Anna is here to help you with all your Workers' Compensation Fund questions and needs. She's available 24/7 and can assist you with:

## What Anna Can Help You With:
- **Check Your Claim Status**: Get real-time updates on your claim progress
- **View Payment Information**: See your benefit payments and schedules
- **Update Your Contact Details**: Keep your information current
- **Find Medical Providers**: Locate approved healthcare providers
- **Get Process Guidance**: Understand WCFCB procedures step-by-step
- **Answer Questions**: Get instant answers about workers' compensation

## How to Talk to Anna:
Anna understands natural language, so you can talk to her just like you would talk to a person:

✅ **Good Examples:**
- "Hi Anna, can you check my claim status?"
- "When will I receive my next payment?"
- "I need to update my phone number"
- "What documents do I need for my claim?"

❌ **Avoid:**
- Very long messages with multiple questions
- Technical jargon or abbreviations
- Sharing sensitive information in public areas

## Getting the Best Help:
1. **Be Specific**: The more details you provide, the better Anna can help
2. **One Question at a Time**: Ask one main question per message
3. **Use Your Claim Number**: Have your claim number ready (format: WC-YYYY-XXXXXX)
4. **Be Patient**: Anna may need to verify your identity for security

## Security and Privacy:
- Anna will verify your identity before sharing personal information
- Your conversations are encrypted and secure
- Never share your verification details with others
- Contact support if you notice any suspicious activity

Ready to get started? Just say "Hi Anna!" and she'll guide you through everything! 🌟
                """,
                persona="beneficiary",
                category="getting_started",
                difficulty="beginner",
                estimated_time=5,
                prerequisites=[],
                related_sections=["beneficiary_claim_status", "beneficiary_authentication"]
            ),
            
            DocumentationSection(
                id="beneficiary_claim_status",
                title="Checking Your Claim Status with Anna",
                content="""
# How to Check Your Claim Status 📋

Anna can provide you with real-time updates on your workers' compensation claim. Here's how:

## Step-by-Step Guide:

### 1. Start the Conversation
Simply say: "Hi Anna, I'd like to check my claim status"

### 2. Identity Verification
For your security, Anna will verify your identity:
- **Claim Number**: Provide your claim number (WC-YYYY-XXXXXX)
- **Personal Details**: Confirm your name and date of birth
- **SMS Verification**: You may receive a text message with a verification code

### 3. View Your Status
Once verified, Anna will show you:
- **Current Status**: Where your claim stands in the process
- **Current Stage**: What's happening right now
- **Next Steps**: What will happen next
- **Expected Timeline**: When to expect updates
- **Case Manager**: Your assigned case manager's contact information

## Understanding Your Claim Status:

### Common Status Updates:
- **"Under Review"**: Your claim is being evaluated
- **"Medical Assessment"**: Medical reports are being reviewed
- **"Disability Rating"**: Determining your disability percentage
- **"Approved"**: Your claim has been approved
- **"Additional Information Needed"**: More documents required

### What Each Stage Means:
1. **Initial Review** (1-2 weeks): Basic claim validation
2. **Medical Assessment** (2-4 weeks): Medical evidence review
3. **Investigation** (1-3 weeks): Incident verification if needed
4. **Disability Rating** (1-2 weeks): Determining compensation level
5. **Final Decision** (1 week): Claim approval or denial

## Tips for Faster Processing:
- Submit all required documents promptly
- Attend all medical appointments
- Respond quickly to requests for information
- Keep your contact information updated

## If You Need Help:
- Ask Anna: "What documents are still needed?"
- Request: "Can I speak to my case manager?"
- Say: "I don't understand my claim status"

Anna is here to help you understand every step of the process! 💙
                """,
                persona="beneficiary",
                category="claim_management",
                difficulty="beginner",
                estimated_time=8,
                prerequisites=["beneficiary_getting_started"],
                related_sections=["beneficiary_payments", "beneficiary_documents"]
            ),
            
            DocumentationSection(
                id="beneficiary_payments",
                title="Understanding Your Benefit Payments",
                content="""
# Your Benefit Payments Explained 💰

Anna can help you understand and track your workers' compensation benefit payments.

## Types of Benefits:

### Temporary Disability Benefits
- **Purpose**: Replace lost wages while you recover
- **Amount**: Typically 66.67% of your average weekly wage
- **Duration**: Until you return to work or reach maximum medical improvement
- **Payment Schedule**: Usually weekly or bi-weekly

### Permanent Disability Benefits
- **Purpose**: Compensation for permanent impairment
- **Amount**: Based on disability rating and wage level
- **Duration**: Varies based on disability percentage
- **Payment Schedule**: May be lump sum or periodic payments

### Medical Benefits
- **Coverage**: All necessary medical treatment
- **Providers**: Must use approved healthcare providers
- **Direct Payment**: WCFCB pays providers directly
- **No Co-pays**: You don't pay out-of-pocket for approved treatment

## Checking Your Payment Information:

### Ask Anna:
- "When is my next payment?"
- "How much will I receive?"
- "Show me my payment history"
- "Why was my payment delayed?"

### What Anna Will Show You:
- **Next Payment Date**: When to expect your next benefit
- **Payment Amount**: How much you'll receive
- **Payment History**: Your last several payments
- **Payment Method**: How you receive payments (direct deposit/check)
- **Year-to-Date Total**: Total benefits received this year

## Payment Schedule:
- **Regular Benefits**: Paid every two weeks
- **First Payment**: May take 2-3 weeks after approval
- **Holiday Delays**: Payments may be delayed during holidays
- **Direct Deposit**: Faster than mailed checks

## If There's a Problem:
- **Missing Payment**: Ask Anna "Where is my payment?"
- **Wrong Amount**: Say "My payment amount seems incorrect"
- **Payment Method**: Request "I want to change to direct deposit"

## Important Notes:
- Benefits are subject to state and federal taxes
- You'll receive tax documents at year-end
- Report any return to work immediately
- Keep WCFCB updated on your recovery progress

Anna can answer any questions about your specific payment situation! 📊
                """,
                persona="beneficiary",
                category="payments",
                difficulty="intermediate",
                estimated_time=10,
                prerequisites=["beneficiary_claim_status"],
                related_sections=["beneficiary_return_to_work", "beneficiary_tax_info"]
            )
        ]
        
        for section in sections:
            self.documentation_sections[section.id] = section
    
    def create_employer_documentation(self) -> None:
        """Create documentation for employers"""
        sections = [
            DocumentationSection(
                id="employer_getting_started",
                title="Employer Guide to WCFCB Assistant CRM",
                content="""
# WCFCB Assistant CRM for Employers 🏢

Welcome to the enhanced WCFCB Assistant CRM system. Anna can now help you manage your workers' compensation responsibilities more efficiently.

## What Anna Can Help Employers With:

### Claim Management:
- **View Employee Claims**: See all claims for your employees
- **Track Claim Progress**: Monitor claim status and timelines
- **Submit Incident Reports**: Report workplace injuries quickly
- **Manage Documentation**: Upload and track required documents

### Compliance Monitoring:
- **Premium Payments**: Check payment status and schedules
- **Safety Training**: Track employee safety training completion
- **Audit Preparation**: Get audit-ready reports and documentation
- **Compliance Scores**: Monitor your compliance rating

### Reporting and Analytics:
- **Claims Analytics**: Understand your claims patterns
- **Cost Analysis**: Track workers' compensation costs
- **Safety Metrics**: Monitor workplace safety performance
- **Trend Reports**: Identify areas for improvement

## Getting Started:

### 1. Authentication
Anna will verify your employer account:
- **Company Registration Number**
- **Authorized Representative Details**
- **Multi-factor Authentication**

### 2. Dashboard Overview
Once authenticated, you'll have access to:
- **Active Claims Summary**
- **Compliance Status**
- **Recent Activity**
- **Action Items**

### 3. Common Commands:
- "Show me all active claims"
- "What's my compliance status?"
- "I need to report an incident"
- "Generate a claims report"

## Best Practices:
- Report incidents within 24 hours
- Keep employee information updated
- Submit required documentation promptly
- Review safety training regularly

Anna is here to make workers' compensation management easier for your business! 📈
                """,
                persona="employer",
                category="getting_started",
                difficulty="intermediate",
                estimated_time=12,
                prerequisites=[],
                related_sections=["employer_claims", "employer_compliance"]
            )
        ]
        
        for section in sections:
            self.documentation_sections[section.id] = section
    
    def create_supplier_documentation(self) -> None:
        """Create documentation for suppliers"""
        sections = [
            DocumentationSection(
                id="supplier_getting_started",
                title="Medical Provider Guide to WCFCB Assistant",
                content="""
# WCFCB Assistant for Medical Providers 🏥

Anna can help medical providers navigate the WCFCB system efficiently and ensure proper patient care coordination.

## What Anna Can Help Providers With:

### Patient Management:
- **Verify Patient Coverage**: Confirm workers' compensation coverage
- **Check Authorization**: Verify treatment authorizations
- **Submit Treatment Plans**: Request approval for treatment protocols
- **Track Patient Progress**: Monitor recovery milestones

### Billing and Claims:
- **Submit Bills**: Electronic billing submission
- **Check Payment Status**: Track payment processing
- **Resolve Billing Issues**: Get help with claim rejections
- **Fee Schedule**: Access current fee schedules

### Documentation:
- **Medical Reports**: Submit required medical reports
- **Progress Notes**: Update patient progress
- **Return-to-Work Assessments**: Submit work capacity evaluations
- **Disability Ratings**: Provide impairment assessments

## Getting Started:

### 1. Provider Registration
Ensure your provider account is active:
- **Provider License Number**
- **WCFCB Provider ID**
- **Authorized Staff Access**

### 2. Patient Verification
Before treatment, verify coverage:
- "Verify coverage for claim WC-2024-001234"
- "Check authorization for John Doe"
- "What treatments are approved?"

### 3. Common Workflows:
- **New Patient**: Verify coverage → Check authorizations → Begin treatment
- **Ongoing Care**: Submit progress notes → Request continued authorization
- **Billing**: Submit bills → Track payments → Resolve issues

## Important Guidelines:
- Always verify coverage before treatment
- Submit reports within required timeframes
- Use approved treatment protocols
- Maintain detailed documentation

Anna ensures you have the information needed to provide excellent patient care! 🩺
                """,
                persona="supplier",
                category="getting_started",
                difficulty="intermediate",
                estimated_time=10,
                prerequisites=[],
                related_sections=["supplier_billing", "supplier_authorization"]
            )
        ]
        
        for section in sections:
            self.documentation_sections[section.id] = section
    
    def create_staff_documentation(self) -> None:
        """Create documentation for WCFCB staff"""
        sections = [
            DocumentationSection(
                id="staff_getting_started",
                title="WCFCB Staff Guide to Enhanced Assistant CRM",
                content="""
# Enhanced Assistant CRM for WCFCB Staff 👥

The enhanced Assistant CRM system provides powerful tools for case management, analytics, and customer service.

## Core Integration Phase Features:

### Enhanced Case Management:
- **Intelligent Case Routing**: AI-powered case assignment
- **Real-time Status Updates**: Live case status tracking
- **Automated Workflows**: Streamlined processing steps
- **Performance Analytics**: Case processing metrics

### Advanced Search and Analytics:
- **Multi-criteria Search**: Find cases using various parameters
- **Predictive Analytics**: Identify potential issues early
- **Performance Dashboards**: Monitor team and individual metrics
- **Trend Analysis**: Understand patterns and trends

### Customer Service Tools:
- **Conversation History**: Full interaction tracking
- **Escalation Management**: Seamless escalation workflows
- **Knowledge Base**: Instant access to policies and procedures
- **Response Templates**: Consistent communication

## Getting Started:

### 1. Staff Authentication
Access your enhanced dashboard:
- **Staff ID and Password**
- **Role-based Permissions**
- **Multi-factor Authentication**

### 2. Dashboard Overview:
- **My Cases**: Cases assigned to you
- **Team Performance**: Department metrics
- **System Alerts**: Important notifications
- **Quick Actions**: Common tasks

### 3. Advanced Features:
- **Bulk Operations**: Process multiple cases
- **Advanced Reporting**: Custom report generation
- **System Administration**: Configuration management
- **User Management**: Manage user accounts

## Key Workflows:

### Case Processing:
1. **Case Assignment**: Automatic or manual assignment
2. **Initial Review**: Comprehensive case evaluation
3. **Decision Making**: Evidence-based decisions
4. **Communication**: Stakeholder notifications
5. **Closure**: Final case resolution

### Quality Assurance:
- **Case Reviews**: Systematic quality checks
- **Performance Monitoring**: Individual and team metrics
- **Training Identification**: Skill gap analysis
- **Process Improvement**: Continuous enhancement

## Best Practices:
- Use standardized procedures
- Document all decisions thoroughly
- Communicate proactively with stakeholders
- Leverage analytics for insights

The enhanced system empowers you to provide exceptional service! ⚡
                """,
                persona="staff",
                category="getting_started",
                difficulty="advanced",
                estimated_time=15,
                prerequisites=[],
                related_sections=["staff_case_management", "staff_analytics"]
            )
        ]
        
        for section in sections:
            self.documentation_sections[section.id] = section
    
    def create_administrator_documentation(self) -> None:
        """Create documentation for system administrators"""
        sections = [
            DocumentationSection(
                id="admin_system_overview",
                title="System Administrator Guide - Production Deployment",
                content="""
# WCFCB Assistant CRM - System Administration Guide 🔧

This guide covers the production deployment architecture and administrative procedures for the enhanced WCFCB Assistant CRM system.

## System Architecture:

### Production Environment:
- **Load Balancers**: High availability configuration
- **Application Servers**: Auto-scaling instances
- **Database Cluster**: Primary/replica setup with failover
- **Cache Layer**: Redis cluster for performance
- **Monitoring**: Comprehensive system monitoring

### Core Integration Components:
1. **Enhanced Intent Classifier**: AI-powered intent recognition
2. **Live Data Response Assembler**: Real-time data integration
3. **Conversation Flow Optimizer**: Seamless user workflows
4. **Performance Optimizer**: Intelligent caching and async processing
5. **UX Refinement Engine**: Persona-optimized experiences

### Security Hardening:
- **Encryption**: Data at rest and in transit
- **Authentication**: Multi-factor authentication
- **Access Control**: Role-based permissions
- **Threat Detection**: Real-time security monitoring
- **Audit Logging**: Comprehensive audit trails

## Administrative Tasks:

### Daily Operations:
- **Health Checks**: Monitor system health
- **Performance Review**: Check response times and throughput
- **Security Monitoring**: Review security alerts
- **Backup Verification**: Ensure backups completed successfully

### Weekly Operations:
- **Performance Analysis**: Review weekly metrics
- **Capacity Planning**: Monitor resource utilization
- **Security Review**: Analyze security events
- **User Feedback**: Review user satisfaction metrics

### Monthly Operations:
- **System Updates**: Apply security patches and updates
- **Performance Optimization**: Tune system parameters
- **Disaster Recovery Testing**: Test backup and recovery procedures
- **Compliance Review**: Ensure regulatory compliance

## Monitoring and Alerting:

### Key Metrics:
- **Response Times**: <2 seconds for live data queries
- **Availability**: >99.9% uptime
- **Error Rates**: <1% error rate
- **Cache Hit Rate**: >60% cache efficiency

### Alert Thresholds:
- **Critical**: Response time >5 seconds, availability <99%
- **Warning**: Response time >2 seconds, error rate >1%
- **Info**: Cache hit rate <60%, high resource utilization

### Escalation Procedures:
1. **Level 1**: Automated alerts to operations team
2. **Level 2**: Manager notification for persistent issues
3. **Level 3**: Executive escalation for critical outages

## Troubleshooting:

### Common Issues:
- **High Response Times**: Check database performance, cache hit rates
- **Authentication Failures**: Verify authentication service status
- **Data Inconsistencies**: Check data synchronization processes
- **Security Alerts**: Investigate and respond to security events

### Emergency Procedures:
- **System Outage**: Follow disaster recovery plan
- **Security Incident**: Activate incident response team
- **Data Corruption**: Restore from verified backups
- **Performance Degradation**: Scale resources and investigate

## Configuration Management:
- **Environment Variables**: Secure configuration management
- **Feature Flags**: Controlled feature rollouts
- **Database Migrations**: Version-controlled schema changes
- **Deployment Automation**: CI/CD pipeline management

The system is designed for enterprise-grade reliability and performance! 🚀
                """,
                persona="administrator",
                category="system_administration",
                difficulty="expert",
                estimated_time=30,
                prerequisites=[],
                related_sections=["admin_monitoring", "admin_security", "admin_troubleshooting"]
            )
        ]
        
        for section in sections:
            self.documentation_sections[section.id] = section
    
    def initialize_training_modules(self) -> None:
        """Initialize training modules for each persona"""
        try:
            # Create training modules
            self.create_beneficiary_training()
            self.create_employer_training()
            self.create_supplier_training()
            self.create_staff_training()
            
            logging.info("Training modules initialized")
            
        except Exception as e:
            logging.error(f"Training modules initialization error: {str(e)}")
            raise
    
    def create_beneficiary_training(self) -> None:
        """Create training module for beneficiaries"""
        module = TrainingModule(
            id="beneficiary_basic_training",
            title="Getting Started with Anna - Your WCFCB Assistant",
            description="Learn how to use Anna to manage your workers' compensation claim and benefits",
            persona="beneficiary",
            sections=[
                self.documentation_sections["beneficiary_getting_started"],
                self.documentation_sections["beneficiary_claim_status"],
                self.documentation_sections["beneficiary_payments"]
            ],
            completion_criteria={
                "sections_completed": 3,
                "assessment_score": 80,
                "practical_exercise": True
            },
            assessment_questions=[
                {
                    "question": "What information do you need to check your claim status with Anna?",
                    "type": "multiple_choice",
                    "options": [
                        "Just your name",
                        "Claim number and personal details",
                        "Only your phone number",
                        "Your employer's information"
                    ],
                    "correct_answer": 1,
                    "explanation": "Anna needs your claim number and personal details to verify your identity securely."
                },
                {
                    "question": "How often are temporary disability benefits typically paid?",
                    "type": "multiple_choice",
                    "options": [
                        "Monthly",
                        "Every two weeks",
                        "Daily",
                        "Once a year"
                    ],
                    "correct_answer": 1,
                    "explanation": "Temporary disability benefits are usually paid every two weeks."
                }
            ]
        )
        
        self.training_modules[module.id] = module
    
    def create_employer_training(self) -> None:
        """Create training module for employers"""
        module = TrainingModule(
            id="employer_basic_training",
            title="WCFCB Assistant CRM for Employers",
            description="Learn how to manage workers' compensation responsibilities using the enhanced CRM system",
            persona="employer",
            sections=[
                self.documentation_sections["employer_getting_started"]
            ],
            completion_criteria={
                "sections_completed": 1,
                "assessment_score": 85,
                "practical_exercise": True
            },
            assessment_questions=[
                {
                    "question": "Within how many hours should workplace incidents be reported?",
                    "type": "multiple_choice",
                    "options": [
                        "72 hours",
                        "48 hours", 
                        "24 hours",
                        "1 week"
                    ],
                    "correct_answer": 2,
                    "explanation": "Workplace incidents should be reported within 24 hours for proper claim processing."
                }
            ]
        )
        
        self.training_modules[module.id] = module
    
    def create_supplier_training(self) -> None:
        """Create training module for suppliers"""
        module = TrainingModule(
            id="supplier_basic_training",
            title="WCFCB Assistant for Medical Providers",
            description="Learn how to use the WCFCB system for patient care coordination and billing",
            persona="supplier",
            sections=[
                self.documentation_sections["supplier_getting_started"]
            ],
            completion_criteria={
                "sections_completed": 1,
                "assessment_score": 90,
                "practical_exercise": True
            },
            assessment_questions=[
                {
                    "question": "What should you do before providing treatment to a workers' compensation patient?",
                    "type": "multiple_choice",
                    "options": [
                        "Start treatment immediately",
                        "Verify coverage and check authorizations",
                        "Contact the employer first",
                        "Wait for payment"
                    ],
                    "correct_answer": 1,
                    "explanation": "Always verify coverage and check authorizations before providing treatment."
                }
            ]
        )
        
        self.training_modules[module.id] = module
    
    def create_staff_training(self) -> None:
        """Create training module for staff"""
        module = TrainingModule(
            id="staff_advanced_training",
            title="Enhanced Assistant CRM for WCFCB Staff",
            description="Master the enhanced CRM system features for efficient case management",
            persona="staff",
            sections=[
                self.documentation_sections["staff_getting_started"]
            ],
            completion_criteria={
                "sections_completed": 1,
                "assessment_score": 95,
                "practical_exercise": True
            },
            assessment_questions=[
                {
                    "question": "What is the primary benefit of the Enhanced Intent Classifier?",
                    "type": "multiple_choice",
                    "options": [
                        "Faster typing",
                        "AI-powered intent recognition for better case routing",
                        "Automatic case closure",
                        "Email notifications"
                    ],
                    "correct_answer": 1,
                    "explanation": "The Enhanced Intent Classifier uses AI to better understand and route cases automatically."
                }
            ]
        )
        
        self.training_modules[module.id] = module
    
    def get_documentation_for_persona(self, persona: str, category: str = None) -> List[DocumentationSection]:
        """Get documentation sections for specific persona"""
        try:
            sections = [
                section for section in self.documentation_sections.values()
                if section.persona == persona
            ]
            
            if category:
                sections = [section for section in sections if section.category == category]
            
            # Sort by difficulty and prerequisites
            sections.sort(key=lambda x: (x.difficulty, len(x.prerequisites)))
            
            return sections
            
        except Exception as e:
            logging.error(f"Documentation retrieval error: {str(e)}")
            return []
    
    def get_training_module(self, module_id: str) -> Optional[TrainingModule]:
        """Get specific training module"""
        return self.training_modules.get(module_id)
    
    def get_training_modules_for_persona(self, persona: str) -> List[TrainingModule]:
        """Get training modules for specific persona"""
        return [
            module for module in self.training_modules.values()
            if module.persona == persona
        ]
    
    def track_user_progress(self, user_id: str, module_id: str, section_id: str, 
                          completion_data: Dict) -> None:
        """Track user training progress"""
        try:
            if user_id not in self.user_progress:
                self.user_progress[user_id] = {}
            
            if module_id not in self.user_progress[user_id]:
                self.user_progress[user_id][module_id] = {
                    "started_at": datetime.now().isoformat(),
                    "sections_completed": [],
                    "assessment_scores": {},
                    "completion_status": "in_progress"
                }
            
            module_progress = self.user_progress[user_id][module_id]
            
            # Track section completion
            if section_id not in module_progress["sections_completed"]:
                module_progress["sections_completed"].append(section_id)
                module_progress["last_activity"] = datetime.now().isoformat()
            
            # Track assessment scores
            if completion_data.get("assessment_score"):
                module_progress["assessment_scores"][section_id] = completion_data["assessment_score"]
            
            # Check module completion
            module = self.training_modules.get(module_id)
            if module:
                criteria = module.completion_criteria
                sections_required = criteria.get("sections_completed", 0)
                score_required = criteria.get("assessment_score", 0)
                
                sections_done = len(module_progress["sections_completed"])
                avg_score = sum(module_progress["assessment_scores"].values()) / len(module_progress["assessment_scores"]) if module_progress["assessment_scores"] else 0
                
                if sections_done >= sections_required and avg_score >= score_required:
                    module_progress["completion_status"] = "completed"
                    module_progress["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            logging.error(f"User progress tracking error: {str(e)}")
    
    def get_user_progress(self, user_id: str) -> Dict:
        """Get user training progress"""
        return self.user_progress.get(user_id, {})
    
    def collect_feedback(self, user_id: str, feedback_type: str, content: str, 
                        rating: int, section_id: str = None) -> None:
        """Collect user feedback on documentation and training"""
        try:
            feedback_entry = {
                "user_id": user_id,
                "feedback_type": feedback_type,
                "content": content,
                "rating": rating,
                "section_id": section_id,
                "timestamp": datetime.now().isoformat()
            }
            
            if feedback_type not in self.feedback_data:
                self.feedback_data[feedback_type] = []
            
            self.feedback_data[feedback_type].append(feedback_entry)
            
            # Log feedback for analysis
            logging.info(f"User feedback collected: {feedback_entry}")
            
        except Exception as e:
            logging.error(f"Feedback collection error: {str(e)}")
    
    def generate_training_analytics(self) -> Dict:
        """Generate training and documentation analytics"""
        try:
            analytics = {
                "total_users": len(self.user_progress),
                "completion_rates": {},
                "average_scores": {},
                "feedback_summary": {},
                "popular_sections": {},
                "improvement_areas": []
            }
            
            # Calculate completion rates by module
            for module_id, module in self.training_modules.items():
                completed_users = len([
                    progress for progress in self.user_progress.values()
                    if progress.get(module_id, {}).get("completion_status") == "completed"
                ])
                total_users = len([
                    progress for progress in self.user_progress.values()
                    if module_id in progress
                ])
                
                if total_users > 0:
                    analytics["completion_rates"][module_id] = (completed_users / total_users) * 100
            
            # Calculate average assessment scores
            for module_id in self.training_modules:
                scores = []
                for user_progress in self.user_progress.values():
                    if module_id in user_progress:
                        module_scores = user_progress[module_id].get("assessment_scores", {})
                        scores.extend(module_scores.values())
                
                if scores:
                    analytics["average_scores"][module_id] = sum(scores) / len(scores)
            
            # Analyze feedback
            for feedback_type, feedback_list in self.feedback_data.items():
                if feedback_list:
                    avg_rating = sum(f["rating"] for f in feedback_list) / len(feedback_list)
                    analytics["feedback_summary"][feedback_type] = {
                        "average_rating": avg_rating,
                        "total_feedback": len(feedback_list)
                    }
            
            return analytics
            
        except Exception as e:
            logging.error(f"Training analytics generation error: {str(e)}")
            return {}
    
    def get_contextual_help(self, user_context: Dict) -> Dict:
        """Get contextual help based on user's current context"""
        try:
            persona = user_context.get("user_type", "beneficiary")
            current_action = user_context.get("current_action", "")
            
            # Find relevant help content
            relevant_sections = []
            
            for section in self.documentation_sections.values():
                if section.persona == persona:
                    # Check if section is relevant to current action
                    if current_action.lower() in section.content.lower():
                        relevant_sections.append(section)
            
            # Sort by relevance and difficulty
            relevant_sections.sort(key=lambda x: x.difficulty)
            
            return {
                "relevant_sections": relevant_sections[:3],  # Top 3 most relevant
                "quick_tips": self.get_quick_tips(persona, current_action),
                "related_training": self.get_related_training(persona, current_action)
            }
            
        except Exception as e:
            logging.error(f"Contextual help error: {str(e)}")
            return {}
    
    def get_quick_tips(self, persona: str, action: str) -> List[str]:
        """Get quick tips based on persona and action"""
        tips_map = {
            "beneficiary": {
                "claim_status": [
                    "Have your claim number ready (WC-YYYY-XXXXXX)",
                    "Anna will verify your identity for security",
                    "Ask specific questions for better help"
                ],
                "payments": [
                    "Payments are typically made every two weeks",
                    "Direct deposit is faster than mailed checks",
                    "Report any return to work immediately"
                ]
            },
            "employer": {
                "incident_report": [
                    "Report incidents within 24 hours",
                    "Gather all relevant documentation",
                    "Ensure employee receives proper medical care"
                ]
            },
            "supplier": {
                "billing": [
                    "Always verify coverage before treatment",
                    "Submit bills within required timeframes",
                    "Use current fee schedules"
                ]
            }
        }
        
        persona_tips = tips_map.get(persona, {})
        return persona_tips.get(action, ["Ask Anna for help with any questions!"])
    
    def get_related_training(self, persona: str, action: str) -> List[str]:
        """Get related training modules"""
        modules = self.get_training_modules_for_persona(persona)
        return [module.title for module in modules[:2]]  # Top 2 related modules

# Global documentation system instance
documentation_system = None

def get_documentation_system() -> UserTrainingDocumentationSystem:
    """Get global documentation system instance"""
    global documentation_system
    if documentation_system is None:
        documentation_system = UserTrainingDocumentationSystem()
    return documentation_system

# API Endpoints

@frappe.whitelist()
def get_documentation():
    """API endpoint to get documentation for user's persona"""
    try:
        data = frappe.local.form_dict
        persona = data.get("persona", "beneficiary")
        category = data.get("category")
        
        system = get_documentation_system()
        sections = system.get_documentation_for_persona(persona, category)
        
        return {
            "success": True,
            "data": {
                "sections": [
                    {
                        "id": section.id,
                        "title": section.title,
                        "content": section.content,
                        "category": section.category,
                        "difficulty": section.difficulty,
                        "estimated_time": section.estimated_time
                    }
                    for section in sections
                ]
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Documentation API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_training_modules():
    """API endpoint to get training modules for user's persona"""
    try:
        data = frappe.local.form_dict
        persona = data.get("persona", "beneficiary")
        
        system = get_documentation_system()
        modules = system.get_training_modules_for_persona(persona)
        
        return {
            "success": True,
            "data": {
                "modules": [
                    {
                        "id": module.id,
                        "title": module.title,
                        "description": module.description,
                        "sections_count": len(module.sections),
                        "estimated_time": sum(section.estimated_time for section in module.sections)
                    }
                    for module in modules
                ]
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Training modules API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_contextual_help():
    """API endpoint for contextual help"""
    try:
        data = frappe.local.form_dict
        user_context = {
            "user_type": data.get("user_type", "beneficiary"),
            "current_action": data.get("current_action", ""),
            "current_page": data.get("current_page", "")
        }
        
        system = get_documentation_system()
        help_content = system.get_contextual_help(user_context)
        
        return {
            "success": True,
            "data": help_content
        }
        
    except Exception as e:
        frappe.log_error(f"Contextual help API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
