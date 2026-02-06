"""
Patch to fix invoice_date format from DD/MM/YYYY back to MM/DD/YYYY
Swaps month and day to correct dates imported as MM/DD/YYYY
"""
import frappe
from datetime import datetime

def execute():
    """Fix all Invoice Processing dates by swapping month and day"""
    
    # Get all Invoice Processing documents
    invoices = frappe.db.get_list("Invoice Processing", fields=['name', 'invoice_date'])
    
    print(f"Fixing dates for {len(invoices)} invoices")
    fixed_count = 0
    
    for invoice in invoices:
        try:
            invoice_name = invoice['name']
            db_date = invoice['invoice_date']
            
            if db_date:
                # Parse the date stored in YYYY-MM-DD format
                parsed = datetime.strptime(str(db_date), '%Y-%m-%d')
                
                # Swap month and day: if stored as 2026-09-01, make it 2026-01-09
                # Original input was 01/09/2026 (MM/DD/YYYY = January 9)
                # But it got stored as 2026-09-01 (September 1)
                corrected = datetime(parsed.year, parsed.day, parsed.month)
                corrected_str = corrected.strftime('%Y-%m-%d')
                
                # Update in database
                frappe.db.set_value(
                    "Invoice Processing",
                    invoice_name,
                    "invoice_date",
                    corrected_str,
                    update_modified=False
                )
                
                print(f"Fixed {invoice_name}: {db_date} -> {corrected_str}")
                fixed_count += 1
                
        except Exception as e:
            print(f"Error fixing {invoice_name}: {str(e)}")
    
    frappe.db.commit()
    print(f"Date fix patch completed: Fixed {fixed_count} records")
