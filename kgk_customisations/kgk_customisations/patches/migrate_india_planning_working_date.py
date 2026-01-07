# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe

def execute():
	"""
	Migrate data from wroking_date to working_date field in India Planning doctype
	This patch is needed after fixing the typo in the field name
	"""
	frappe.logger().info("Starting India Planning field migration patch")
	
	# Check if the old column exists in the database
	if frappe.db.has_column("India Planning", "wroking_date"):
		# Copy data from old field to new field
		frappe.db.sql("""
			UPDATE `tabIndia Planning`
			SET working_date = wroking_date
			WHERE wroking_date IS NOT NULL
				AND (working_date IS NULL OR working_date = '')
		""")
		
		frappe.db.commit()
		frappe.logger().info("Successfully migrated wroking_date to working_date")
		
		# Note: The old column will be automatically removed by Frappe during migrate
		# when it syncs the doctype schema
	else:
		frappe.logger().info("Old wroking_date column not found - migration may have already been completed")
