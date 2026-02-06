from frappe.model.document import Document
from datetime import datetime
import frappe
import re

def fix_date_after_insert(doc, method):
    """Fix invoice_date immediately after insert during import"""
    if doc.invoice_date:
        try:
            date_value = doc.invoice_date
            
            # If it's a datetime.date or datetime object, swap month and day
            if hasattr(date_value, 'day') and hasattr(date_value, 'month') and hasattr(date_value, 'year'):
                original_month = date_value.month
                original_day = date_value.day
                original_year = date_value.year
                
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
        self.validate_composite_key()
        self.process_item_description()
        self.trigger_derived_fields()
    
    def validate_composite_key(self):
        """Ensure unique combination of invoice_number, job_number, control_number, item_description, service_description"""
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