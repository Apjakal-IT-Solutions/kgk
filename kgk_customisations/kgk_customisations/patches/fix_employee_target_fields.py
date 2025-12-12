# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe

def execute():
	"""
	Fix Employee Target records with missing employee_name and section fields
	These fields were marked as virtual and didn't persist - now we populate them
	"""
	frappe.logger().info("Starting Employee Target field population patch")
	
	# Get all Employee Target records
	employee_targets = frappe.get_all(
		"Employee Target",
		fields=["name", "employee", "employee_name", "section"]
	)
	
	updated_count = 0
	
	for target in employee_targets:
		needs_update = False
		update_dict = {}
		
		if target.employee:
			# Check if employee_name is missing
			if not target.employee_name:
				employee_name = frappe.db.get_value("Employee", target.employee, "employee_name")
				if employee_name:
					update_dict["employee_name"] = employee_name
					needs_update = True
			
			# Check if section is missing
			if not target.section:
				department = frappe.db.get_value("Employee", target.employee, "department")
				if department:
					update_dict["section"] = department
					needs_update = True
		
		# Update the record if needed
		if needs_update:
			frappe.db.set_value("Employee Target", target.name, update_dict)
			updated_count += 1
			frappe.logger().info(f"Updated Employee Target: {target.name}")
	
	frappe.db.commit()
	
	frappe.logger().info(f"Employee Target patch completed. Updated {updated_count} records.")
	print(f"✓ Updated {updated_count} Employee Target records with missing employee_name/section fields")
