#!/usr/bin/env python3
"""
WCFCB URL Routing Hooks
SEO-optimized URL routing for WCFCB DocTypes
"""

import frappe
from frappe import _

# SEO-optimized URL routing patterns
url_patterns = [
    # Claims Management URLs
    {
        "pattern": r"^/workers-compensation-claims/(?P<claim_slug>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.claim_handler.render_claim_page",
        "doctype": "Claim"
    },
    {
        "pattern": r"^/claim-processing/(?P<claim_id>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.claim_handler.render_claim_processing",
        "doctype": "Claim"
    },
    
    # Employer Services URLs
    {
        "pattern": r"^/employer-services/(?P<employer_slug>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.employer_handler.render_employer_page",
        "doctype": "Employee"
    },
    {
        "pattern": r"^/employer-compliance/(?P<employer_id>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.employer_handler.render_compliance_page",
        "doctype": "Employee"
    },
    
    # Beneficiary Services URLs
    {
        "pattern": r"^/beneficiary-services/(?P<beneficiary_slug>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.beneficiary_handler.render_beneficiary_page",
        "doctype": "Beneficiary"
    },
    {
        "pattern": r"^/disability-benefits/(?P<beneficiary_id>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.beneficiary_handler.render_benefits_page",
        "doctype": "Beneficiary"
    },

    # Chat Support URLs
    {
        "pattern": r"^/chat-support/?$",
        "handler": "assistant_crm.www.handlers.chat_handler.render_chat_page",
        "doctype": "Conversation"
    },
    {
        "pattern": r"^/customer-support/(?P<conversation_id>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.chat_handler.render_conversation_page",
        "doctype": "Conversation"
    },
    
    # Medical Provider URLs
    {
        "pattern": r"^/medical-providers/(?P<provider_slug>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.medical_handler.render_provider_page",
        "doctype": "Medical Provider"
    },
    {
        "pattern": r"^/healthcare-network/(?P<provider_id>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.medical_handler.render_network_page",
        "doctype": "Medical Provider"
    },
    
    # Campaign URLs
    {
        "pattern": r"^/awareness-campaigns/(?P<campaign_slug>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.campaign_handler.render_campaign_page",
        "doctype": "Campaign"
    },
    {
        "pattern": r"^/safety-awareness/(?P<campaign_id>[\w-]+)/?$",
        "handler": "assistant_crm.www.handlers.campaign_handler.render_safety_page",
        "doctype": "Campaign"
    },
    
    # Dashboard URLs - REMOVED to prevent interference with other pages
    
    # API URLs with SEO-friendly paths - DASHBOARD ANALYTICS REMOVED
    {
        "pattern": r"^/api/real-time/data/?$",
        "handler": "assistant_crm.api.real_time_refresh_api.get_real_time_data",
        "doctype": None
    }
]

# SEO metadata for different page types
seo_metadata = {
    "claim_page": {
        "title_template": "Workers' Compensation Claim {claim_id} | WCFCB",
        "description_template": "Track and manage workers' compensation claim {claim_id} with WCFCB. Fast processing and comprehensive support for workplace injury claims in Zambia.",
        "keywords": ["workers compensation", "claim processing", "workplace injury", "WCFCB", "Zambia"]
    },
    
    "employer_page": {
        "title_template": "Employer Services - {company_name} | WCFCB",
        "description_template": "Comprehensive employer services for {company_name} including compliance management, safety training, and premium calculations with WCFCB.",
        "keywords": ["employer services", "workplace safety", "compliance", "premium payments", "WCFCB"]
    },
    
    "beneficiary_page": {
        "title_template": "Beneficiary Services - {beneficiary_name} | WCFCB",
        "description_template": "Access disability benefits, medical coverage, and rehabilitation services for {beneficiary_name} through WCFCB's comprehensive support programs.",
        "keywords": ["disability benefits", "medical coverage", "rehabilitation", "beneficiary services", "WCFCB"]
    },

    "chat_support": {
        "title_template": "Chat Support - Get Instant Help | WCFCB WorkCom Assistant",
        "description_template": "Get instant support through WCFCB's AI-powered chat assistant WorkCom. 24/7 help for claims, benefits, compliance, and general inquiries.",
        "keywords": ["chat support", "customer service", "AI assistant", "instant help", "WCFCB WorkCom"]
    },
    
    "medical_provider": {
        "title_template": "Medical Provider - {provider_name} | WCFCB Network",
        "description_template": "Find information about {provider_name} in WCFCB's authorized medical provider network for workers' compensation treatment and services.",
        "keywords": ["medical provider", "healthcare network", "treatment services", "authorized providers", "WCFCB"]
    },
    
    "campaign": {
        "title_template": "Safety Campaign - {campaign_name} | WCFCB",
        "description_template": "Learn about {campaign_name} safety awareness campaign from WCFCB. Workplace education and injury prevention initiatives.",
        "keywords": ["safety campaign", "workplace education", "injury prevention", "awareness program", "WCFCB"]
    }
}

def get_seo_metadata(page_type, context_data):
    """
    Generate SEO metadata for a specific page type and context.
    """
    metadata = seo_metadata.get(page_type, {})
    
    title = metadata.get("title_template", "WCFCB - Workers' Compensation Fund of Zambia")
    description = metadata.get("description_template", "WCFCB provides comprehensive workers' compensation services in Zambia.")
    keywords = metadata.get("keywords", ["WCFCB", "workers compensation", "Zambia"])
    
    # Format templates with context data
    if context_data:
        try:
            title = title.format(**context_data)
            description = description.format(**context_data)
        except KeyError:
            pass  # Use default if formatting fails
    
    return {
        "title": title,
        "description": description,
        "keywords": ", ".join(keywords),
        "og_title": title,
        "og_description": description,
        "og_type": "website",
        "og_site_name": "WCFCB - Workers' Compensation Fund of Zambia"
    }

def generate_canonical_url(request_path):
    """
    Generate canonical URL for the current page.
    """
    from assistant_crm.utils import get_public_url
    base_url = get_public_url()
    canonical = f"{base_url}{request_path}"
    
    # Remove query parameters for canonical URL
    if '?' in canonical:
        canonical = canonical.split('?')[0]
    
    # Ensure trailing slash consistency
    if not canonical.endswith('/') and '.' not in canonical.split('/')[-1]:
        canonical += '/'
    
    return canonical

def get_breadcrumb_data(doctype, doc_name, doc_data=None):
    """
    Generate breadcrumb data for SEO and navigation.
    """
    breadcrumbs = [
        {"name": "Home", "url": "/", "position": 1}
    ]
    
    # Add doctype-specific breadcrumbs
    if doctype == "Claim":
        breadcrumbs.extend([
            {"name": "Claims", "url": "/workers-compensation-claims/", "position": 2},
            {"name": f"Claim {doc_name}", "url": f"/workers-compensation-claims/{doc_name}/", "position": 3}
        ])
    elif doctype == "Employee":
        breadcrumbs.extend([
            {"name": "Employer Services", "url": "/employer-services/", "position": 2},
            {"name": doc_data.get("company_name", doc_name), "url": f"/employer-services/{doc_name}/", "position": 3}
        ])
    # Add more doctype-specific breadcrumbs as needed
    
    return breadcrumbs

def generate_structured_data(page_type, doc_data, breadcrumbs):
    """
    Generate JSON-LD structured data for SEO.
    """
    base_data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": doc_data.get("title", "WCFCB Page"),
        "description": doc_data.get("description", "WCFCB - Workers' Compensation Fund of Zambia"),
        "url": generate_canonical_url(frappe.request.path),
        "publisher": {
            "@type": "Organization",
            "name": "Workers' Compensation Fund Control Board",
            "url": "https://wcfcb.gov.zm"
        }
    }
    
    # Add breadcrumb structured data
    if breadcrumbs:
        base_data["breadcrumb"] = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": crumb["position"],
                    "name": crumb["name"],
                    "item": crumb["url"]
                }
                for crumb in breadcrumbs
            ]
        }
    
    # Add page-specific structured data
    if page_type == "medical_provider":
        base_data["@type"] = "MedicalOrganization"
        base_data["medicalSpecialty"] = "Occupational Medicine"
    
    return base_data

# URL rewrite rules for legacy URLs
url_redirects = {
    "/old-claims": "/workers-compensation-claims/",
    "/employers": "/employer-services/",
    "/kb": "/knowledge-base/",
    "/chat": "/chat-support/",
    "/providers": "/medical-providers/",
    "/campaigns": "/awareness-campaigns/"
}

def handle_url_redirect(path):
    """
    Handle URL redirects for legacy URLs.
    """
    if path in url_redirects:
        return url_redirects[path]
    
    # Handle pattern-based redirects
    for old_pattern, new_pattern in url_redirects.items():
        if path.startswith(old_pattern):
            return path.replace(old_pattern, new_pattern, 1)
    
    return None

# Performance tracking for URLs
def track_url_performance(request_path, response_time, status_code):
    """
    Track URL performance for SEO optimization.
    """
    try:
        # Create or update URL performance record
        frappe.get_doc({
            "doctype": "Web Page View",
            "request_url": request_path,
            "response_time": response_time,
            "status_code": status_code,
            "user_agent": frappe.request.headers.get("User-Agent", ""),
            "ip_address": frappe.local.request_ip,
            "creation": frappe.utils.now()
        }).insert(ignore_permissions=True)
        
    except Exception as e:
        frappe.log_error(f"URL performance tracking error: {str(e)}")

# Sitemap generation for SEO
def generate_sitemap_xml():
    """
    Generate XML sitemap for search engines.
    """
    sitemap_urls = []
    
    # Add static pages
    static_pages = [
        {"url": "/", "priority": "1.0", "changefreq": "daily"},
        {"url": "/workers-compensation-claims/", "priority": "0.9", "changefreq": "daily"},
        {"url": "/employer-services/", "priority": "0.9", "changefreq": "weekly"},
        {"url": "/beneficiary-services/", "priority": "0.9", "changefreq": "weekly"},
        {"url": "/knowledge-base/", "priority": "0.8", "changefreq": "weekly"},
        {"url": "/chat-support/", "priority": "0.7", "changefreq": "always"},
        {"url": "/medical-providers/", "priority": "0.6", "changefreq": "monthly"}
    ]
    
    sitemap_urls.extend(static_pages)
    
    # Add dynamic pages
    doctypes_for_sitemap = ["Campaign", "Medical Provider"]

    for doctype in doctypes_for_sitemap:
        try:
            docs = frappe.get_all(doctype,
                fields=["name", "modified"],
                limit=1000)
            
            for doc in docs:
                url_path = f"/{doctype.lower().replace(' ', '-')}/{doc.name}/"
                sitemap_urls.append({
                    "url": url_path,
                    "priority": "0.6",
                    "changefreq": "weekly",
                    "lastmod": doc.modified.strftime("%Y-%m-%d") if doc.modified else None
                })
        except Exception as e:
            frappe.log_error(f"Sitemap generation error for {doctype}: {str(e)}")
    
    return sitemap_urls

