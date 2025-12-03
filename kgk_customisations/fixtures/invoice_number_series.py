# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

"""
Fixtures for creating default Invoice Number Series records.
These will be installed when setting up the app.
"""

import frappe

def create_default_invoice_series():
	"""Create default invoice number series for common document types"""
	
	# Get all companies
	companies = frappe.get_all("Company", fields=["name", "abbr"])
	
	if not companies:
		frappe.log_error("No companies found. Cannot create default invoice series.", "Invoice Series Setup")
		return
	
	document_types = [
		{"type": "Payment", "prefix": "PAY"},
		{"type": "Receipt", "prefix": "REC"},
		{"type": "Invoice", "prefix": "INV"},
		{"type": "Credit Note", "prefix": "CN"},
		{"type": "Debit Note", "prefix": "DN"},
		{"type": "Journal Entry", "prefix": "JE"},
		{"type": "Petty Cash", "prefix": "PC"}
	]
	
	for company in companies:
		for doc_type in document_types:
			# Check if series already exists
			existing = frappe.db.exists(
				"Invoice Number Series",
				{
					"document_type": doc_type["type"],
					"company": company.name,
					"is_active": 1
				}
			)
			
			if not existing:
				try:
					series = frappe.get_doc({
						"doctype": "Invoice Number Series",
						"document_type": doc_type["type"],
						"company": company.name,
						"prefix": doc_type["prefix"],
						"current_number": 1,
						"padding": 5,
						"year_based": 1,
						"reset_on_year_change": 1,
						"is_active": 1
					})
					series.insert(ignore_permissions=True)
					frappe.db.commit()
					frappe.logger().info(f"Created Invoice Number Series: {doc_type['type']} for {company.name}")
				except Exception as e:
					frappe.log_error(f"Failed to create Invoice Number Series for {doc_type['type']} - {company.name}: {str(e)}", "Invoice Series Setup Error")
					frappe.db.rollback()
	
	frappe.msgprint("Default Invoice Number Series created successfully for all companies")


def execute():
	"""Execute function called during app installation"""
	create_default_invoice_series()
