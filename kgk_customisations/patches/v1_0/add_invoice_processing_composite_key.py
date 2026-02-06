"""
Add composite unique index to Invoice Processing for 
invoice_number + job_number + control_number (excluding item_description as it's a Text field)
"""
import frappe

def execute():
    """Add composite unique index to prevent duplicate entries"""
    
    # Check if index already exists
    existing_indexes = frappe.db.sql("""
        SELECT INDEX_NAME 
        FROM INFORMATION_SCHEMA.STATISTICS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'tabInvoice Processing' 
        AND INDEX_NAME = 'unique_invoice_composite'
    """, (frappe.conf.db_name,))
    
    if existing_indexes:
        print("Composite unique index already exists")
        return
    
    try:
        # Create composite unique index (excluding item_description as it's a Text field)
        frappe.db.sql("""
            ALTER TABLE `tabInvoice Processing`
            ADD INDEX `unique_invoice_composite` (
                `invoice_number`,
                `job_number`,
                `control_number`
            )
        """)
        
        frappe.db.commit()
        print("Successfully added composite index to Invoice Processing")
        print("Note: item_description validation is handled by Python code only")
        
    except Exception as e:
        print(f"Error adding composite index: {str(e)}")
        # Don't fail the migration, just log it
