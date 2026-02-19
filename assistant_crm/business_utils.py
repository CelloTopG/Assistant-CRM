import frappe
from datetime import datetime, time, timedelta
import pytz

def get_business_hours():
    """
    Get business hours configuration from Assistant CRM Settings.
    """
    settings = frappe.get_single("Assistant CRM Settings")
    
    start_str = settings.business_hours_start or "09:00:00"
    end_str = settings.business_hours_end or "17:00:00"
    business_days_str = settings.business_days or "Monday, Tuesday, Wednesday, Thursday, Friday"
    
    # Convert business days to a set of day names and index (0=Mon, 6=Sun)
    day_name_to_idx = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    
    business_days_names = {day.strip() for day in business_days_str.split(",")}
    business_days_idx = {day_name_to_idx[day] for day in business_days_names if day in day_name_to_idx}
    
    try:
        start_time = datetime.strptime(start_str, "%H:%M:%S").time()
        end_time = datetime.strptime(end_str, "%H:%M:%S").time()
    except ValueError:
        try:
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
        except ValueError:
            start_time = time(9, 0)
            end_time = time(17, 0)
            
    return {
        "start": start_time,
        "end": end_time,
        "days_names": business_days_names,
        "days_idx": business_days_idx
    }

def is_business_hours(ts=None):
    """
    Check if a given timestamp (or now) is within business hours.
    """
    config = get_business_hours()
    
    if ts:
        if isinstance(ts, str):
            from frappe.utils import get_datetime
            now = get_datetime(ts)
        else:
            now = ts
    else:
        from frappe.utils import now_datetime
        now = now_datetime()
        
    current_day_idx = now.weekday()
    current_time = now.time()
    
    if current_day_idx not in config["days_idx"]:
        return False
        
    return config["start"] <= current_time <= config["end"]

def get_out_of_hours_message():
    """
    Get the out of hours message from settings.
    """
    settings = frappe.get_single("Assistant CRM Settings")
    return settings.out_of_hours_message or "We are currently closed. Our business hours are from 09:00 to 17:00, Monday to Friday. We will respond to your message as soon as possible."

def get_business_minutes_between(start, end):
    """
    Calculate business minutes between two timestamps.
    """
    if not start or not end or end <= start:
        return 0.0

    config = get_business_hours()
    business_days = config["days_idx"]
    business_start = config["start"]
    business_end = config["end"]

    total_seconds = 0.0
    curr = start
    
    while curr.date() <= end.date():
        if curr.weekday() in business_days:
            day_start = datetime.combine(curr.date(), business_start)
            day_end = datetime.combine(curr.date(), business_end)
            
            # Intersection of [start, end] and [day_start, day_end]
            s = max(curr, day_start)
            e = min(end, day_end)
            
            if e > s:
                total_seconds += (e - s).total_seconds()
        
        # Move to next day at 00:00
        curr = datetime.combine(curr.date() + timedelta(days=1), time(0, 0))
        
    return total_seconds / 60.0
