"""
Rename existing Laser Approval records to match new naming rule (field:org_lot_id)
"""
import frappe
from frappe.model.rename_doc import rename_doc

def execute():
    """Rename all existing Laser Approval records based on org_lot_id field"""
    
    frappe.logger().info("Starting Laser Approval record renaming patch...")
    
    try:
        # Get all Laser Approval records
        laser_approvals = frappe.get_all(
            'Laser Approval',
            fields=['name', 'org_lot_id'],
            order_by='creation asc'
        )
        
        if not laser_approvals:
            print("No Laser Approval records found to rename")
            return
        
        renamed_count = 0
        skipped_count = 0
        error_count = 0
        
        for doc in laser_approvals:
            old_name = doc.name
            new_name = doc.org_lot_id
            
            # Skip if org_lot_id is empty or same as current name
            if not new_name or old_name == new_name:
                skipped_count += 1
                continue
            
            try:
                # Check if new name already exists
                if frappe.db.exists('Laser Approval', new_name):
                    print(f"Skipping {old_name}: {new_name} already exists")
                    skipped_count += 1
                    continue
                
                # Rename the document
                rename_doc(
                    'Laser Approval',
                    old_name,
                    new_name,
                    force=False,
                    merge=False,
                    ignore_permissions=True
                )
                
                renamed_count += 1
                print(f"Renamed: {old_name} → {new_name}")
                
            except Exception as e:
                error_count += 1
                frappe.log_error(
                    f"Error renaming {old_name} to {new_name}: {str(e)}",
                    "Laser Approval Rename Patch Error"
                )
                print(f"Error renaming {old_name}: {str(e)}")
        
        # Commit the changes
        frappe.db.commit()
        
        print(f"\n✓ Laser Approval rename patch completed:")
        print(f"  - Renamed: {renamed_count}")
        print(f"  - Skipped: {skipped_count}")
        print(f"  - Errors: {error_count}")
        print(f"  - Total: {len(laser_approvals)}")
        
        frappe.logger().info(
            f"Laser Approval rename patch completed. "
            f"Renamed: {renamed_count}, Skipped: {skipped_count}, Errors: {error_count}"
        )
        
    except Exception as e:
        frappe.log_error(f"Error in Laser Approval rename patch: {str(e)}", frappe.get_traceback())
        print(f"✗ Error in rename patch: {str(e)}")
        raise
