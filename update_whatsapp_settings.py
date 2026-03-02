
import frappe

def update_whatsapp_settings():
    try:
        settings = frappe.get_doc("Social Media Settings")
        settings.whatsapp_enabled = 1
        settings.whatsapp_phone_number_id = "976550555544825"
        settings.whatsapp_business_account_id = "1164602115584411"
        settings.whatsapp_access_token = "EAAQmwwxjxDsBQ9gdEtY14KfWm3uIC5aNMDZCZBGtpToksQV9hfQYpcGsvZCaTSy9pn88NCZAPy63kj45BsLmZCStJKUcuEamtYxCqGnJy3mNzHhrFcVOhZAM6k7vnyXDwSSrT2Qe13LDrbaF5v48bTo9mqdDYP5r5TSH8zn1iH08vkp5qZBAsmu4OiP5I4XotmiX7PH2JVC3alxHrIDDPA39QRZBu7573TDPcAfqhU1kIbIADE94TwvVZAlZCKVZCiqOcZCFlFkOaN3zC0ZACLfzZACRXN8lJala7NeAG1LZCEZD"
        settings.whatsapp_webhook_verify_token = "wcfcb_webhook_verify_token"
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        print("WhatsApp settings updated successfully.")
    except Exception as e:
        print(f"Error updating WhatsApp settings: {str(e)}")

if __name__ == "__main__":
    update_whatsapp_settings()
