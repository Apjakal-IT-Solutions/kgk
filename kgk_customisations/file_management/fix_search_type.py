"""
Fix File Search Dashboard search_type field
Run with: bench --site [sitename] execute kgk_customisations.file_management.fix_search_type.fix_search_type_value
"""

import frappe

def fix_search_type_value():
    """Fix the search_type field to have proper capitalization"""
    try:
        # Update directly in database to avoid validation
        frappe.db.set_value("File Search Dashboard", "File Search Dashboard", "search_type", "All")
        frappe.db.commit()
        
        print("✓ Fixed search_type to 'All'")
        
        # Verify
        value = frappe.db.get_value("File Search Dashboard", "File Search Dashboard", "search_type")
        print(f"✓ Verified: search_type is now '{value}'")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        frappe.db.rollback()

if __name__ == "__main__":
    fix_search_type_value()
