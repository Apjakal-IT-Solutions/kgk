# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe

def execute():
	"""
	Update Laser Stock Position doctype to be submittable and submit all existing records.
	This patch:
	1. Ensures the doctype has docstatus column
	2. Updates all existing records to submitted status (docstatus = 1)
	"""
	
	frappe.logger().info("Starting Laser Stock Position submission patch...")
	
	try:
		# Try to check if docstatus column exists
		try:
			has_docstatus = frappe.db.has_column("tabLaser Stock Position", "docstatus")
		except Exception:
			# Table doesn't exist yet, will be created during migration
			frappe.logger().info("Laser Stock Position table does not exist yet, skipping patch")
			print("✓ Laser Stock Position table does not exist yet, will be created during migration")
			return
		
		if not has_docstatus:
			frappe.logger().info("Adding docstatus column to Laser Stock Position")
			frappe.db.sql("""
				ALTER TABLE `tabLaser Stock Position`
				ADD COLUMN docstatus INT(1) NOT NULL DEFAULT 0
			""")
			frappe.db.commit()
		
		# Get count of existing records
		existing_count = frappe.db.count("Laser Stock Position")
		frappe.logger().info(f"Found {existing_count} existing Laser Stock Position records")
		
		if existing_count > 0:
			# Update all existing records to submitted status
			frappe.db.sql("""
				UPDATE `tabLaser Stock Position`
				SET docstatus = 1
				WHERE docstatus = 0
			""")
			
			updated_count = frappe.db.sql("""
				SELECT COUNT(*) FROM `tabLaser Stock Position`
				WHERE docstatus = 1
			""")[0][0]
			
			frappe.db.commit()
			frappe.logger().info(f"Updated {updated_count} Laser Stock Position records to submitted status")
			print(f"✓ Successfully updated {updated_count} Laser Stock Position records to submitted status")
		else:
			frappe.logger().info("No existing records to update")
			print("✓ No existing records to update")
		
		frappe.logger().info("Laser Stock Position submission patch completed successfully")
		
	except Exception as e:
		frappe.logger().error(f"Error in Laser Stock Position submission patch: {str(e)}")
		print(f"✗ Error: {str(e)}")
		raise
