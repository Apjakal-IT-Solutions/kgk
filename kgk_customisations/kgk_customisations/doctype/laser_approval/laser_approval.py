# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LaserApproval(Document):
	def before_insert(self):
		"""Prepopulate document_users table with all employees from Laser Approval User Item"""
		if not self.document_users or len(self.document_users) == 0:
			self.populate_users()
	
	def populate_users(self):
		"""Fetch all users from Laser Approval User Item and add them to document_users"""
		# Get all users from Laser Approval User Item
		users = frappe.get_all(
			'Laser Approval User Item',
			fields=['name', 'full_name'],
			order_by='full_name asc'
		)
		
		if users:
			# Clear existing rows (if any)
			self.document_users = []
			
			# Add each user to the child table
			for user in users:
				self.append('document_users', {
					'employee_name': user.name,
					'status': 'No'  # Default status
				})
			
			frappe.msgprint(
				f'Added {len(users)} users to the document',
				title='Users Prepopulated',
				indicator='green'
			)

@frappe.whitelist()
def refresh_user_list(docname):
	"""Refresh the user list for an existing document"""
	doc = frappe.get_doc('Laser Approval', docname)
	doc.populate_users()
	doc.save()
	return {'message': f'User list refreshed with {len(doc.document_users)} users'}
