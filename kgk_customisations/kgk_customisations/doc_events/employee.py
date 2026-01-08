# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe

def update_employee_targets(doc, method=None):
	"""
	Update all Employee Target records when an Employee is saved.
	This ensures that fetch_from fields (employee_name, section/department) 
	are synchronized when the source Employee record changes.
	"""
	
	# Find all Employee Target records linked to this employee
	targets = frappe.get_all(
		"Employee Target",
		filters={"employee": doc.name},
		fields=["name"]
	)
	
	if not targets:
		return
	
	# Update each Employee Target record to trigger fetch_from
	for target in targets:
		try:
			et = frappe.get_doc("Employee Target", target.name)
			
			# Update employee_name if changed
			if hasattr(doc, 'employee_name') and et.employee_name != doc.employee_name:
				et.employee_name = doc.employee_name
			
			# Update section (from department) if changed
			if hasattr(doc, 'department') and et.section != doc.department:
				et.section = doc.department
			
			# Save without triggering validations to avoid recursion
			et.db_update()
			
		except Exception as e:
			frappe.log_error(
				f"Failed to update Employee Target {target.name}: {str(e)}",
				"Employee Target Update Error"
			)
	
	# Commit the changes
	frappe.db.commit()
	
	frappe.msgprint(
		f"Updated {len(targets)} Employee Target record(s) linked to {doc.employee_name}",
		indicator="green",
		alert=True
	)
