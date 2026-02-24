# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeTarget(Document):
	def before_save(self):
		"""Populate read-only fields from Employee link if empty"""
		if self.employee:
			# Fetch employee details if fields are empty
			if not self.employee_name:
				self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
			
			if not self.section:
				self.section = frappe.db.get_value("Employee", self.employee, "department")
