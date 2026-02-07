/**
 * Company → Employer UI Rename
 * 
 * This script renames all instances of "Company" to "Employer" in the UI
 * without modifying core ERPNext doctypes.
 */

frappe.provide("assistant_crm");

// Company → Employer translation mappings
assistant_crm.employer_translations = {
    "Company": "Employer",
    "Companies": "Employers",
    "Select Company": "Select Employer",
    "Company Name": "Employer Name",
    "Company Settings": "Employer Settings",
    "Default Company": "Default Employer",
    "Parent Company": "Parent Employer",
    "Company Description": "Employer Description",
    "Company Address": "Employer Address",
    "Company Info": "Employer Info",
    "Company Details": "Employer Details",
    "Company Abbreviation": "Employer Abbreviation",
    "All Companies": "All Employers",
    "New Company": "New Employer",
    "Edit Company": "Edit Employer",
    "Delete Company": "Delete Employer",
    "Company is mandatory": "Employer is mandatory",
    "Please select a Company": "Please select an Employer",
    "Please select Company": "Please select Employer",
    "No Company found": "No Employer found",
    "Company not found": "Employer not found",
    "Company Tree": "Employer Tree",
    "Create Company": "Create Employer",
    "Setup Company": "Setup Employer",
    "Company Setup": "Employer Setup",
    "Company Information": "Employer Information",
    "Company Overview": "Employer Overview",
    "Company Dashboard": "Employer Dashboard",
    "Company List": "Employer List",
    "For Company": "For Employer",
    "for company": "for employer",
    "of Company": "of Employer",
    "in Company": "in Employer",
    "by Company": "by Employer",
    "per Company": "per Employer",
    "this Company": "this Employer",
    "the Company": "the Employer",
    "a Company": "an Employer",
    "your Company": "your Employer",
    "Filter by Company": "Filter by Employer",
    "Group by Company": "Group by Employer"
};

// Override the translation function to apply Company → Employer rename
(function() {
    // Store original __ function
    const original_translate = window.__;
    
    // Override __ function
    window.__ = function(txt, replace, context) {
        // First apply original translation
        let result = original_translate ? original_translate(txt, replace, context) : txt;
        
        // Then apply Company → Employer mapping
        if (typeof result === 'string') {
            // Check exact match first
            if (assistant_crm.employer_translations[result]) {
                result = assistant_crm.employer_translations[result];
            }
            // Also replace standalone "Company" with "Employer" 
            // but be careful not to replace partial matches like "Accompanying"
            else if (result.includes("Company") || result.includes("Companies")) {
                // Replace "Companies" first (to avoid double replacement)
                result = result.replace(/\bCompanies\b/g, "Employers");
                result = result.replace(/\bCompany\b/g, "Employer");
            }
        }
        
        return result;
    };
})();

// Apply translations to existing DOM elements on page load
frappe.ready(function() {
    assistant_crm.apply_employer_rename();
});

// Function to apply employer rename to DOM
assistant_crm.apply_employer_rename = function() {
    // Update page title if it contains "Company"
    if (document.title.includes("Company")) {
        document.title = document.title.replace(/\bCompanies\b/g, "Employers").replace(/\bCompany\b/g, "Employer");
    }
    
    // Update sidebar module label
    setTimeout(function() {
        // Update module sidebar
        $('[data-doctype="Company"] .sidebar-menu-label, [data-doctype="Company"] .desk-sidebar-item-label').each(function() {
            let $el = $(this);
            let text = $el.text();
            if (text.includes("Company")) {
                $el.text(text.replace(/\bCompanies\b/g, "Employers").replace(/\bCompany\b/g, "Employer"));
            }
        });
        
        // Update breadcrumbs
        $('.breadcrumb-container a, .breadcrumb a').each(function() {
            let $el = $(this);
            let text = $el.text();
            if (text.includes("Company")) {
                $el.text(text.replace(/\bCompanies\b/g, "Employers").replace(/\bCompany\b/g, "Employer"));
            }
        });
        
        // Update page title
        $('.page-title, .title-text, h1, h2, h3').each(function() {
            let $el = $(this);
            let text = $el.text();
            if (text.includes("Company") && !$el.find('*').length) {
                $el.text(text.replace(/\bCompanies\b/g, "Employers").replace(/\bCompany\b/g, "Employer"));
            }
        });
        
        // Update field labels
        $('.frappe-control label, .control-label').each(function() {
            let $el = $(this);
            let text = $el.text();
            if (text.includes("Company")) {
                $el.text(text.replace(/\bCompanies\b/g, "Employers").replace(/\bCompany\b/g, "Employer"));
            }
        });
        
        // Update button text
        $('.btn').each(function() {
            let $el = $(this);
            let text = $el.text();
            if (text.includes("Company") && !$el.find('*').length) {
                $el.text(text.replace(/\bCompanies\b/g, "Employers").replace(/\bCompany\b/g, "Employer"));
            }
        });
        
    }, 500);
};

// Re-apply on route change
$(document).on('page-change', function() {
    setTimeout(assistant_crm.apply_employer_rename, 300);
});

// Re-apply when forms are rendered
$(document).on('form-load form-refresh', function() {
    setTimeout(assistant_crm.apply_employer_rename, 300);
});

