"""
Initialize and apply data importer patch when app loads.
"""

def apply_patches():
    """Apply all custom patches when the app is ready"""
    try:
        from frappe.core.doctype.data_import.importer import Row
        from datetime import time, datetime, date as datetime_date
        import frappe
        
        # Store the original method
        _original_get_date = Row.get_date
        
        def patched_get_date(self, value, col):
            """
            Patched version of get_date that handles datetime.time objects.
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
                    value = value.date().isoformat()
            
            # Convert date object to string
            elif isinstance(value, datetime_date):
                value = value.isoformat()
            
            # Call the original method with the fixed value
            return _original_get_date(self, value, col)
        
        # Apply the patch
        Row.get_date = patched_get_date
        frappe.logger().info("[kgk_customisations] Successfully applied data importer patch for handling time values")
        
    except Exception as e:
        import frappe
        frappe.logger().error(f"[kgk_customisations] Error applying patch: {str(e)}")

def load_optimizations():
    """Load performance optimizations"""
    try:
        from .utils.data_import_optimizer import optimized_save_documents
        import frappe
        frappe.logger().info("[kgk_customisations] Loaded data import optimizations")
    except Exception as e:
        import frappe
        frappe.logger().warning(f"[kgk_customisations] Could not load optimizations: {str(e)}")

def patch_data_import():
    """Patch DataImport.set_payload_count to skip for Invoice Processing"""
    try:
        from frappe.core.doctype.data_import.data_import import DataImport
        import frappe
        import os
        
        _original_set_payload_count = DataImport.set_payload_count
        
        def patched_set_payload_count(self):
            """
            Skip payload_count calculation for Invoice Processing imports.
            The counting is slow for large datasets and will be done in background job.
            """
            if not self.import_file:
                return
            
            # Skip completely for Invoice Processing doctype
            if self.reference_doctype == "Invoice Processing":
                frappe.logger().info(f"[Data Import] Skipping payload count for Invoice Processing import")
                self.payload_count = 0  # Will be calculated in background job
                return
            
            # For other doctypes, try original method but with timeout protection
            try:
                _original_set_payload_count(self)
            except Exception as e:
                # If it times out or fails, just set to 0
                frappe.logger().warning(f"[Data Import] set_payload_count failed, setting to 0: {str(e)}")
                self.payload_count = 0
        
        DataImport.set_payload_count = patched_set_payload_count
        frappe.logger().info("[kgk_customisations] Patched DataImport.set_payload_count to skip Invoice Processing")
    except Exception as e:
        import frappe
        frappe.logger().warning(f"[kgk_customisations] Could not patch DataImport: {str(e)}")

# Execute on import
apply_patches()
load_optimizations()
patch_data_import()
