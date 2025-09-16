# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe

def setup_cash_management_roles():
	"""Setup custom roles for cash management"""
	
	roles = [
		{
			"role_name": "Cash Basic User",
			"description": "Basic user who can create and view cash documents",
			"permissions": {
				"Cash Document": ["read", "write", "create", "print", "email", "export", "share"],
				"Daily Cash Balance": ["read", "print", "email", "export", "share"]
			}
		},
		{
			"role_name": "Cash Checker",
			"description": "User who can review and flag cash documents",
			"permissions": {
				"Cash Document": ["read", "write", "create", "print", "email", "export", "share"],
				"Daily Cash Balance": ["read", "write", "print", "email", "export", "share"]
			}
		},
		{
			"role_name": "Cash Accountant",
			"description": "Accountant who can approve and submit cash documents",
			"permissions": {
				"Cash Document": ["read", "write", "create", "submit", "print", "email", "export", "share"],
				"Daily Cash Balance": ["read", "write", "create", "print", "email", "export", "share"]
			}
		},
		{
			"role_name": "Cash Super User",
			"description": "Super user with full access to cash management",
			"permissions": {
				"Cash Document": ["read", "write", "create", "delete", "submit", "print", "email", "export", "share"],
				"Daily Cash Balance": ["read", "write", "create", "delete", "print", "email", "export", "share"]
			}
		}
	]
	
	for role_data in roles:
		# Create role if it doesn't exist
		if not frappe.db.exists("Role", role_data["role_name"]):
			role_doc = frappe.get_doc({
				"doctype": "Role",
				"role_name": role_data["role_name"],
				"description": role_data["description"],
				"is_custom": 0
			})
			role_doc.insert()
			print(f"Created role: {role_data['role_name']}")
		else:
			print(f"Role already exists: {role_data['role_name']}")

def setup_cash_management_permissions():
	"""Setup permissions for cash management DocTypes"""
	
	# Cash Document permissions are already defined in the JSON
	# Daily Cash Balance permissions are already defined in the JSON
	# This function can be used for any additional permission setup
	
	print("Cash management permissions are configured in DocType JSON files")

def create_cash_management_workspace():
	"""Create a workspace for cash management"""
	
	workspace_name = "Cash Management"
	
	if not frappe.db.exists("Workspace", workspace_name):
		workspace = frappe.get_doc({
			"doctype": "Workspace",
			"title": workspace_name,
			"icon": "money-coins-1",
			"indicator_color": "Green",
			"is_standard": 0,
			"module": "Kgk Customisations",
			"shortcuts": [
				{
					"type": "DocType",
					"label": "Cash Document",
					"doc_type": "Cash Document",
					"link_to": "Cash Document",
					"icon": "file-text"
				},
				{
					"type": "DocType",
					"label": "Daily Cash Balance",
					"doc_type": "Daily Cash Balance",
					"link_to": "Daily Cash Balance",
					"icon": "calculator"
				}
			],
			"charts": [
				{
					"chart_name": "Cash Flow Trend",
					"label": "Cash Flow Trend",
					"chart_type": "Line",
					"document_type": "Cash Document",
					"based_on": "transaction_date",
					"value_based_on": "amount",
					"time_interval": "Daily",
					"timespan": "Last Month"
				}
			]
		})
		workspace.insert()
		print(f"Created workspace: {workspace_name}")
	else:
		print(f"Workspace already exists: {workspace_name}")

def setup_cash_management_settings():
	"""Create cash management settings DocType"""
	
	settings_doctype = {
		"doctype": "DocType",
		"name": "Cash Management Settings",
		"module": "Kgk Customisations",
		"is_single": 1,
		"track_changes": 1,
		"fields": [
			{
				"fieldname": "variance_threshold",
				"fieldtype": "Percent",
				"label": "Variance Threshold (%)",
				"description": "Threshold percentage for marking reconciliation required",
				"default": 5,
				"reqd": 1
			},
			{
				"fieldname": "auto_reconcile",
				"fieldtype": "Check",
				"label": "Auto Reconcile Zero Variance",
				"description": "Automatically mark as reconciled when variance is zero",
				"default": 1
			},
			{
				"fieldname": "notification_settings",
				"fieldtype": "Section Break",
				"label": "Notification Settings"
			},
			{
				"fieldname": "notify_on_variance",
				"fieldtype": "Check",
				"label": "Notify on Variance",
				"description": "Send notifications when variance exceeds threshold",
				"default": 1
			}
		],
		"permissions": [
			{
				"role": "Cash Super User",
				"read": 1,
				"write": 1
			},
			{
				"role": "Cash Accountant",
				"read": 1,
				"write": 1
			}
		]
	}
	
	if not frappe.db.exists("DocType", "Cash Management Settings"):
		doc = frappe.get_doc(settings_doctype)
		doc.insert()
		print("Created Cash Management Settings DocType")
	else:
		print("Cash Management Settings DocType already exists")

def execute():
	"""Main function to setup all cash management components"""
	print("Setting up cash management roles and permissions...")
	
	setup_cash_management_roles()
	setup_cash_management_permissions()
	setup_cash_management_settings()
	
	print("Cash management setup completed successfully!")

if __name__ == "__main__":
	execute()