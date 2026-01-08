#!/usr/bin/env python3
"""
Console script to bulk update Employee Target records with current Employee data.
Run this once to sync all existing records.

Usage:
    bench --site <sitename> console
    >>> exec(open("update_employee_targets_bulk.py").read())
"""

import frappe

def update_all_employee_targets():
	"""Update all Employee Target records with current Employee data."""
	
	frappe.init(site='kgkerp.local')  # Change site name if needed
	frappe.connect()
	
	# Get all Employee Target records
	targets = frappe.get_all(
		"Employee Target",
		filters={"employee": ["is", "set"]},
		fields=["name", "employee", "employee_name", "section"]
	)
	
	print(f"\nFound {len(targets)} Employee Target records to check...")
	
	updated_count = 0
	error_count = 0
	
	for target in targets:
		try:
			# Get the linked Employee
			employee = frappe.get_doc("Employee", target.employee)
			
			# Check if update needed
			needs_update = False
			changes = []
			
			if target.employee_name != employee.employee_name:
				needs_update = True
				changes.append(f"name: '{target.employee_name}' → '{employee.employee_name}'")
			
			if target.section != employee.department:
				needs_update = True
				changes.append(f"section: '{target.section}' → '{employee.department}'")
			
			if needs_update:
				# Update the Employee Target
				et = frappe.get_doc("Employee Target", target.name)
				et.employee_name = employee.employee_name
				et.section = employee.department
				et.db_update()
				
				updated_count += 1
				print(f"✓ Updated {target.name}: {', '.join(changes)}")
			
		except Exception as e:
			error_count += 1
			print(f"✗ Error updating {target.name}: {str(e)}")
	
	# Commit all changes
	frappe.db.commit()
	
	print(f"\n{'='*60}")
	print(f"Update Complete!")
	print(f"  Updated: {updated_count} records")
	print(f"  Errors:  {error_count} records")
	print(f"  Checked: {len(targets)} records")
	print(f"{'='*60}\n")

if __name__ == "__main__":
	update_all_employee_targets()
