# Escalation Rules & Logic

This document details the automated and manual escalation logic used by WCFCB Assistant CRM to transition conversations from AI (Anna) to human agents.

## 1. Automated Escalation Triggers

The system continuously monitors every interaction to determine if a human intervention is required. Escalation is suggested when one or more of the following patterns are detected.

### A. Sentiment & Emotion Triggers
The `SentimentAnalysisService` evaluates the emotional state of the user.
- **Negative Sentiment**: Any compound sentiment score below **-0.6** triggers an immediate escalation.
- **Aggressive Language**: Keywords such as "legal", "sue", "court", "lawyer", or "manager" trigger escalation to prevent further frustration.
- **High Frustration**: Detection of multiple "frustration" patterns (e.g., "annoyed", "useless", "ridiculous") over a short period.

### B. Intent & Confidence Triggers
The `IntentRecognitionService` ensures the AI only handles requests it understands with high confidence.
- **Low Confidence**: If the best matching intent score falls below the specific `escalation_threshold` defined for that intent.
- **Unknown Intent**: If no active intent meets the baseline `confidence_threshold` (default 0.8), the system falls back to escalation.
- **Repeated Failure**: If the AI fails to recognize intent twice in a row, a "High Priority" escalation is triggered.

### C. Urgency & Priority Triggers
The `SentimentAnalysisService` also performs urgency detection.
- **Critical Status**: Use of words like "emergency", "immediately", "accident", or "injury".
- **Business Deadlines**: Mention of "overdue", "deadline", or "penalties".
- **Priority Customers**: Automatic boost for "Premium" tier employers or users with active compliance issues.

## 2. Escalation Logic (Routing)

Once a trigger is hit, the `omnichannel_router.py` handles the handoff:

| Trigger Level | Priority | Target Queue | Estimated Response Time |
|---------------|----------|--------------|-------------------------|
| **Critical**  | 100      | Crisis/Manager| < 15 Minutes            |
| **High**      | 75       | Senior Agent | < 1 Hour                |
| **Medium**    | 50       | Standard Inbox| < 4 Hours               |
| **Low**       | 25       | Standard Inbox| < 24 Hours              |

### Required Agent Skills
The system suggests specific skills for the escalating agent:
- **Conflict Resolution**: For negative sentiment or anger.
- **Claims Expertise**: For keywords related to injuries or compensation.
- **Compliance Specialist**: For overdue contributions or employer registration issues.

## 3. Manual Escalation
At any point, a user can manually request a human agent by using phrases such as:
- "Talk to a human"
- "Speak to an agent"
- "Transfer me"
- "I want to speak to your manager"

## 4. Configuration
Administrators can tune these rules in the following locations within the Desk:
1. **Assistant CRM Settings**: Global `escalation_threshold` and `auto_escalation_enabled`.
2. **Intent Definition**: Individual thresholds per intent for surgical control.
3. **Unified Inbox Settings**: Custom escalation rules and notification preferences for managers.
