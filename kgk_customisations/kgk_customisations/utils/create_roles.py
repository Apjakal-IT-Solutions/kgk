# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe

def create_cash_roles():
    """Create cash management roles if they don't exist"""
    
    roles = [
        {
            "role_name": "Cash Basic User",
            "description": "Basic user who can create and view cash documents"
        },
        {
            "role_name": "Cash Checker", 
            "description": "User who can review and flag cash documents"
        },
        {
            "role_name": "Cash Accountant",
            "description": "Accountant who can approve and submit cash documents"
        },
        {
            "role_name": "Cash Super User",
            "description": "Super user with full access to cash management"
        }
    ]
    
    created_roles = []
    
    for role_data in roles:
        role_name = role_data["role_name"]
        
        if not frappe.db.exists("Role", role_name):
            try:
                role_doc = frappe.get_doc({
                    "doctype": "Role",
                    "role_name": role_name,
                    "description": role_data["description"],
                    "is_custom": 1
                })
                role_doc.insert(ignore_permissions=True)
                created_roles.append(role_name)
                frappe.logger().info(f"Created role: {role_name}")
            except Exception as e:
                frappe.logger().error(f"Error creating role {role_name}: {str(e)}")
        else:
            frappe.logger().info(f"Role already exists: {role_name}")
    
    if created_roles:
        frappe.db.commit()
        print(f"Created {len(created_roles)} new roles: {', '.join(created_roles)}")
    else:
        print("All roles already exist")
    
    return created_roles

if __name__ == "__main__":
    create_cash_roles()