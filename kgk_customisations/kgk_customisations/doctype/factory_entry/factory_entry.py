# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document


class FactoryEntry(Document):
	
	def before_save(self):
		for item in self.factory_entry_item_table:
			if item.additional_process:
				try:
					process_ids = json.loads(item.additional_process)
					if process_ids:
						# Fetch process names
						process_names = []
						for process_id in process_ids:
							process_doc = frappe.get_doc('Factory Process', process_id)
							process_names.append(process_doc.process_name)
						
						# Store readable version back (optional)
						# Or create a separate display field
						item.additional_process_display = ', '.join(process_names)
				except Exception as e:
					frappe.log_error(f"Error parsing additional_process: {str(e)}")
