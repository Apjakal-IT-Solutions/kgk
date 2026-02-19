from frappe.model.document import Document
from datetime import datetime, time, date
import frappe
import re

def handle_time_in_date_field(data_import):
    """
    Hook for Data Import to handle cases where time values are in date fields.
    This runs before parsing and converts datetime.time objects to dates.
    """
    if data_import.reference_doctype != "Invoice Processing":
        return
    
    try:
        # Get the file and process payloads
        import_file = data_import.import_file
        if not import_file:
            return
        
        from frappe.core.doctype.data_import.importer import Importer
        importer = Importer(
            doctype=data_import.reference_doctype,
            file_doc_name=import_file,
            data_import_doc=data_import,
            submit_after_import=data_import.submit_after_import,
            mute_emails=data_import.mute_emails,
        )
        
        # Get raw data and fix any time values in date columns
        if hasattr(importer, 'data'):
            for row_data in importer.data:
                if isinstance(row_data, dict) and 'invoice_date' in row_data:
                    val = row_data['invoice_date']
                    # If it's a time object, use current date
                    if isinstance(val, time):
                        row_data['invoice_date'] = date.today().isoformat()
                    # If it's a datetime object with no actual date component
                    elif isinstance(val, datetime) and val.hour > 0:
                        row_data['invoice_date'] = val.date().isoformat()
                        
    except Exception as e:
        frappe.log_error(f"Error in handle_time_in_date_field: {str(e)}", frappe.get_traceback())

def fix_time_in_date_field(doc, method):
    """
    Handler called before validation to fix time values in invoice_date field.
    If invoice_date is a time object (from Excel import), convert it to a date string.
    """
    if not doc.invoice_date:
        return
    
    try:
        invoice_date = doc.invoice_date
        
        # Check if it's a time object (from time-formatted Excel cells)
        if isinstance(invoice_date, time):
            # Convert time to a date (use today's date as fallback)
            doc.invoice_date = date.today().isoformat()
            frappe.log_error(f"Converted time value to date for {doc.name}: {invoice_date} -> {doc.invoice_date}")
            
        # Check if it's a datetime with hour component (likely a time-only value)
        elif isinstance(invoice_date, datetime) and (invoice_date.hour > 0 or invoice_date.minute > 0 or invoice_date.second > 0):
            # Use just the date component
            doc.invoice_date = invoice_date.date().isoformat()
            frappe.log_error(f"Converted datetime to date for {doc.name}: {invoice_date} -> {doc.invoice_date}")
            
    except Exception as e:
        frappe.log_error(f"Error fixing time in date field for {doc.name}: {str(e)}", frappe.get_traceback())

def fix_date_after_insert(doc, method):
    """Fix invoice_date immediately after insert during import - only if flag is set"""
    # Check if the reformat flag is enabled
    should_reformat = doc.get('reformat_date', 0)
    
    if not should_reformat:
        return
    
    if doc.invoice_date:
        try:
            date_value = doc.invoice_date
            
            # If it's a datetime.date or datetime object, swap month and day
            if hasattr(date_value, 'day') and hasattr(date_value, 'month') and hasattr(date_value, 'year'):
                original_month = date_value.month
                original_day = date_value.day
                original_year = date_value.year
                
                # Validate that swap is possible (day must be valid month)
                if original_day > 12:
                    frappe.log_error(f"Cannot swap date for {doc.name}: day={original_day} > 12, already in correct format")
                    return
                
                # Swap month and day
                corrected = datetime(original_year, original_day, original_month)
                corrected_str = corrected.strftime('%Y-%m-%d')
                
                # Update directly in database
                frappe.db.set_value(
                    "Invoice Processing",
                    doc.name,
                    "invoice_date",
                    corrected_str,
                    update_modified=False
                )
                
                frappe.log_error(f"Fixed date after insert for {doc.name}: {original_year}-{original_month:02d}-{original_day:02d} -> {corrected_str}")
                
        except Exception as e:
            frappe.log_error(f"Error fixing date after insert for {doc.name}: {str(e)}", frappe.get_traceback())

class InvoiceProcessing(Document):
    def validate(self):
        """Runs before save"""
        # During data import, only do minimal processing
        if frappe.flags.in_import:
            # Only process fields, skip validation
            self.process_item_description()
            self.trigger_derived_fields()
            return
        
        # Normal validation
        self.validate_composite_key()
        self.process_item_description()
        self.trigger_derived_fields()
    
    def after_insert(self):
        """Runs after insert - skip expensive operations during import"""
        # Skip after_insert processing during import to speed up bulk operations
        if frappe.flags.in_import:
            return
        
        # Normal after_insert operations for manual entry
        pass
    
    def validate_composite_key(self):
        """Ensure unique combination - DISABLED during import for performance"""
        # Skip entirely during import to avoid database queries for each row
        if frappe.flags.in_import:
            return
        
        if not all([self.invoice_number, self.job_number, self.control_number, self.item_description, self.service_description]):
            return  # Skip validation if any field is empty
        
        # Check for existing record with same composite key
        filters = {
            "invoice_number": self.invoice_number,
            "job_number": self.job_number,
            "control_number": self.control_number,
            "item_description": self.item_description,
            "service_description": self.service_description
        }
        
        # Exclude current document if updating
        if not self.is_new():
            filters["name"] = ["!=", self.name]
        
        existing = frappe.db.exists("Invoice Processing", filters)
        
        if existing:
            frappe.throw(
                f"Duplicate entry: A record with Invoice Number <b>{self.invoice_number}</b>, "
                f"Job Number <b>{self.job_number}</b>, Control Number <b>{self.control_number}</b>, "
                f"Item Description <b>{self.item_description}</b>, and Service Description <b>{self.service_description}</b> already exists.",
                title="Duplicate Record"
            )
    
    def on_submit(self):
        """Runs when document is submitted - fix dates here"""
        frappe.log_error(f"on_submit called for {self.name}")
        self.fix_date_format()
    
    def fix_date_format(self):
        """Swap month and day in invoice_date"""
        if self.invoice_date:
            try:
                date_value = self.invoice_date
                
                # Get the raw database value to see what's actually stored
                db_date = frappe.db.get_value("Invoice Processing", self.name, "invoice_date")
                frappe.log_error(f"DEBUG {self.name}: invoice_date object = {date_value}, db value = {db_date}")
                
                # If it's a datetime.date or datetime object
                if hasattr(date_value, 'day') and hasattr(date_value, 'month') and hasattr(date_value, 'year'):
                    original_month = date_value.month
                    original_day = date_value.day
                    original_year = date_value.year
                    
                    try:
                        # Always swap month and day
                        corrected = datetime(original_year, original_day, original_month)
                        corrected_str = corrected.strftime('%Y-%m-%d')
                        
                        # Update the database directly
                        frappe.db.set_value(
                            "Invoice Processing",
                            self.name,
                            "invoice_date",
                            corrected_str,
                            update_modified=False
                        )
                        
                        frappe.log_error(f"Fixed date on submit for {self.name}: {original_year}-{original_month:02d}-{original_day:02d} -> {corrected_str}")
                        
                    except ValueError as ve:
                        # If swap creates invalid date, log it
                        frappe.log_error(f"Cannot swap date for {self.name}: month={original_month}, day={original_day} - {str(ve)}")
                    
            except Exception as e:
                frappe.log_error(f"Error fixing date on submit for {self.name}: {str(e)}", frappe.get_traceback())
    
    def process_item_description(self):
        """Extract numerical value, shape, and lot ID from item_description"""
        description = self.item_description or ""
        
        if not description:
            return
        
        # Extract numerical value after "/" and before "CT"
        # Pattern: "XXXXXX / X.XX CT RBC / XXXXXXX" -> X.XX
        match = re.search(r'\/\s*([\d.]+)\s*CT', description)
        if match and match.group(1):
            self.size = float(match.group(1))
        
        # Extract shape (RBC) after "CT" and before next "/"
        # Pattern: "XXXXXX / X.XX CT RBC / XXXXXXX" -> RBC
        shape_match = re.search(r'CT\s+([A-Z]+)\s*\/', description)
        if shape_match and shape_match.group(1):
            self.shape = shape_match.group(1)
        
        # Extract lot ID (last element after final "/")
        # Pattern: "XXXXXX / X.XX CT RBC / XXXXXXX" -> XXXXXXX
        lot_id_match = re.search(r'\/\s*(\d+)\s*$', description)
        if lot_id_match and lot_id_match.group(1):
            self.lot_id = lot_id_match.group(1)
    
    def trigger_derived_fields(self):
        """Trigger calculations for derived fields"""
        # Fee -> Ticker
        if self.fee is not None:
            self.ticker = 0 if self.fee == 0 else 1
        
        # VAT -> Pula, Dollar, Con_Dollar
        if self.vat is not None:
            self.pula = 0 if self.vat == 0 else (self.fee or 0)
            self.dollar = (self.fee or 0) if self.vat == 0 else 0
            self.con_dollar = (self.pula * 0.0726) if self.dollar == 0 else self.dollar
        
        # Type -> Type_2
        if self.type:
            self.type_2 = "Org" if self.type == "Normal" else "Re Chk"
        
        # Size -> Size_Group
        if self.size is not None and self.size > 0:
            self.size_group = self.get_size_group(self.size)
    
    def get_size_group(self, size):
        """Calculate size_group based on size value"""
        try:
            size = float(size)
            if size > 0 and size <= 0.29:
                return "30 DN"
            elif size >= 0.3 and size <= 0.499:
                return "30 TO 50 POINTER"
            elif size >= 0.5 and size <= 0.699:
                return "50 TO 70 POINTER"
            elif size >= 0.7 and size <= 0.899:
                return "70 TO 89 POINTER"
            elif size >= 0.9 and size <= 0.999:
                return "90 TO 99 POINTER"
            elif size >= 1.0 and size <= 1.99:
                return "1 CT TO 2 CTS"
            elif size >= 2.0 and size <= 4.99:
                return "2 CT TO 5 CTS"
            elif size >= 5 and size <= 49.99:
                return "5 CTS & UP"
        except (ValueError, TypeError):
            pass
        
        return ""