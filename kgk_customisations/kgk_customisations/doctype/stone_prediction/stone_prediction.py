# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StonePrediction(Document):
	def validate(self):
		"""Calculate estimated_value and number_of_cuts from predicted_cuts child table"""
		self.calculate_totals()
	
	def calculate_totals(self):
		"""Calculate totals from child table"""
		# Count number of rows in child table
		self.number_of_cuts = len(self.predicted_cuts) if self.predicted_cuts else 0
		
		# Sum of amount column from child table
		self.estimated_value = sum(
			row.amount for row in self.predicted_cuts if row.amount
		) if self.predicted_cuts else 0
