# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe

def execute():
	"""
	Set all existing Employee Target records as active
	New 'active' checkbox defaults to 1, but existing records need to be updated
	"""
	frappe.logger().info("Setting all Employee Target records as active")
	
	# Update all Employee Target records to active = 1
	frappe.db.sql("""
		UPDATE `tabEmployee Target`
		SET active = 1
		WHERE active IS NULL OR active = 0
	""")
	
	frappe.db.commit()
	
	count = frappe.db.count("Employee Target", {"active": 1})
	frappe.logger().info(f"Employee Target active flag patch completed. {count} records now active.")
	print(f"✓ Set {count} Employee Target records as active")
