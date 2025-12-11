# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FileSearchDashboard(Document):
	def validate(self):
		# Ensure search_type has a valid value
		valid_types = ['All', 'Polish Video', 'Rough Video', 'Advisor', 'Scan']
		if self.search_type and self.search_type not in valid_types:
			# Fix case sensitivity - capitalize first letter of each word
			self.search_type = self.search_type.title()
			# If still not valid, set to default
			if self.search_type not in valid_types:
				self.search_type = 'All'
		elif not self.search_type:
			self.search_type = 'All'
