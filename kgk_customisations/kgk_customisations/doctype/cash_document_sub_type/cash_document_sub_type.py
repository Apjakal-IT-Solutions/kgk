# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CashDocumentSubType(Document):
	def validate(self):
		"""Validate Cash Document Sub Type"""
		# Ensure code is uppercase
		if self.code:
			self.code = self.code.upper()
		
		# Check for duplicate code
		if self.code:
			existing = frappe.db.exists(
				"Cash Document Sub Type",
				{
					"code": self.code,
					"name": ["!=", self.name]
				}
			)
			if existing:
				frappe.throw(f"Sub Type with code {self.code} already exists")
		
		# Check for duplicate sub_type_name within same main_document_type
		existing = frappe.db.exists(
			"Cash Document Sub Type",
			{
				"main_document_type": self.main_document_type,
				"sub_type_name": self.sub_type_name,
				"name": ["!=", self.name]
			}
		)
		if existing:
			frappe.throw(f"Sub Type '{self.sub_type_name}' already exists for {self.main_document_type}")
