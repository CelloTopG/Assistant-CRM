import frappe

def check_print_formats():
    print_formats = frappe.get_all("Print Format", fields=["name", "doc_type", "print_format_type"])
    for pf in print_formats:
        print(f"PF: {pf.name} | DocType: {pf.doc_type} | Type: {pf.print_format_type}")

if __name__ == "__main__":
    check_print_formats()
