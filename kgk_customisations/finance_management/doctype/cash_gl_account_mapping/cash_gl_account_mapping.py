# Copyright (c) 2026, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CashGLAccountMapping(Document):
	def validate(self):
		"""Prevent duplicate (third_party_name, cash_company) pairs."""
		existing = frappe.db.get_value(
			"Cash GL Account Mapping",
			{
				"third_party_name": self.third_party_name,
				"cash_company": self.cash_company,
				"name": ("!=", self.name),
			},
			"name",
		)
		if existing:
			frappe.throw(
				frappe._(
					"A mapping for '{0}' (Company: {1}) already exists: {2}"
				).format(self.third_party_name, self.cash_company, existing)
			)
