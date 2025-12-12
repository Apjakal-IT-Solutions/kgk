# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PlanningEntryItem(Document):
	
	def validate(self):
		"""Auto-populate employee details when employee_code is entered"""
		if self.employee_code and not self.employee:
			self.populate_employee_target()
	
	def populate_employee_target(self):
		"""Find Employee Target by factory code and set as employee"""
		if self.employee_code:
			targets = frappe.get_all("Employee Target", 
				filters={"factory_code": self.employee_code, "active": 1}, 
				fields=["name", "employee_name", "factory_code", "target"]
			)
			if targets:
				target = targets[0]
				# Set employee to Employee Target name, this will auto-fetch other fields
				self.employee = target.name
			else:
				frappe.throw(f"No Employee Target found for factory code: {self.employee_code}")


@frappe.whitelist()
def get_employee_target_by_code(factory_code):
	"""Get Employee Target by factory code"""
	if not factory_code:
		return None
		
	targets = frappe.get_all("Employee Target", 
		filters={"factory_code": factory_code, "active": 1}, 
		fields=["name", "employee_name", "employee", "factory_code", "target"]
	)
	
	if targets:
		return targets[0]
	return None
		
