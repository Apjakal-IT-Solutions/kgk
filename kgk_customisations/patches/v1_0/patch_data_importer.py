"""
Custom Data Importer that handles time values in date fields.
This patches the core importer to convert datetime.time objects to date strings.
"""

from frappe.core.doctype.data_import.importer import Row
from datetime import time, datetime, date as datetime_date
import frappe

# Store the original get_date method
_original_get_date = Row.get_date

def patched_get_date(self, value, col):
    """
    Patched version of get_date that handles datetime.time objects.
    If a time object is passed, convert it to a date string before parsing.
    """
    # If it's already a time object, convert to date
    if isinstance(value, time):
        value = datetime_date.today().isoformat()
        frappe.log_error(f"[Data Import Patch] Converted time object to date: {value}")
    
    # If it's a datetime with time component, extract just the date
    elif isinstance(value, datetime):
        if value.hour > 0 or value.minute > 0 or value.second > 0:
            value = value.date().isoformat()
            frappe.log_error(f"[Data Import Patch] Converted datetime with time to date: {value}")
        else:
            # Convert to string in YYYY-MM-DD format
            value = value.date().isoformat()
    
    # Convert date object to string
    elif isinstance(value, datetime_date):
        value = value.isoformat()
    
    # Now call the original method with the fixed value
    return _original_get_date(self, value, col)

# Apply the patch
Row.get_date = patched_get_date

frappe.logger().info("[kgk_customisations] Patched Row.get_date to handle time values in date fields")
