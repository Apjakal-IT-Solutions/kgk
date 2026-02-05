from frappe.model.document import Document
from datetime import datetime
import frappe
import re

class InvoiceProcessing(Document):
    def validate(self):
        """Runs before save - works for both regular save and bulk import"""
        self.convert_date_formats()
        self.process_item_description()
        self.trigger_derived_fields()
    
    def convert_date_formats(self):
        """Convert date fields from MM/DD/YYYY to DD-MM-YYYY format"""
        date_fields = ['date_field_name']  # Replace with your actual date field names
        
        for field in date_fields:
            if hasattr(self, field) and self.get(field):
                try:
                    date_value = self.get(field)
                    
                    if isinstance(date_value, str) and '/' in date_value:
                        parsed_date = datetime.strptime(date_value, '%m/%d/%Y')
                        formatted_date = parsed_date.strftime('%d-%m-%Y')
                        self.set(field, formatted_date)
                except Exception as e:
                    frappe.log_error(f"Date conversion error for {field}: {str(e)}")
    
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