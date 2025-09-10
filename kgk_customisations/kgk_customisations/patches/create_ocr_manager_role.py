# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Create OCR Manager role if it doesn't exist"""
	if not frappe.db.exists("Role", "OCR Manager"):
		role = frappe.new_doc("Role")
		role.role_name = "OCR Manager"
		role.desk_access = 1
		role.save()
		frappe.db.commit()
		print("Created OCR Manager role")
