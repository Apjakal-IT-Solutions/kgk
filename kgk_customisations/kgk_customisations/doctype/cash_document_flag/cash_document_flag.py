# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate
from kgk_customisations.kgk_customisations.utils.permission_manager import PermissionManager

class CashDocumentFlag(Document):
	def before_insert(self):
		"""Set flag information when flag is created"""
		# Set default values only if not already set
		if not self.flagged_by:
			self.flagged_by = frappe.session.user
		if not self.flag_date:
			self.flag_date = frappe.utils.now()
		if not self.flagged_by_role:
			self.flagged_by_role = self.get_user_primary_role()
		
		# Set resolution required based on flag type
		if self.flag_type in ["Query", "Hold", "Revision Needed"]:
			self.resolution_required = 1
	
	def validate(self):
		"""Validate flag data"""
		# Ensure comments are provided for certain flag types
		if self.flag_type in ["Rejected", "Query", "Hold", "Revision Needed"] and not self.comments:
			frappe.throw(f"Comments are required for {self.flag_type} flags")
		
		# Validate resolution data if resolution is marked as completed
		if self.resolution_date and not self.resolved_by:
			frappe.throw("Resolved By is required when Resolution Date is set")
	
	def get_user_primary_role(self):
		"""Get the primary cash management role of the current user"""
		user_roles = frappe.get_roles(frappe.session.user)
		cash_roles = ["Cash Super User", "Cash Accountant", "Cash Checker", "Cash Basic User"]
		
		for role in cash_roles:
			if role in user_roles:
				return role
		
		return "Cash Basic User"  # Default role
	
	@frappe.whitelist()
	def resolve_flag(self, resolution_comments=""):
		"""Mark the flag as resolved"""
		if not self.resolution_required:
			frappe.throw("This flag does not require resolution")
		
		if self.resolution_date:
			frappe.throw("This flag has already been resolved")
		
		self.resolved_by = frappe.session.user
		self.resolution_date = frappe.utils.now()
		self.resolution_comments = resolution_comments
		self.save()
		
		# Send notification to document creator
		self.send_resolution_notification()
		
		return "Flag resolved successfully"
	
	def send_resolution_notification(self):
		"""Send notification when flag is resolved"""
		# Get the parent cash document
		if hasattr(self, 'parent') and self.parent:
			cash_doc = frappe.get_doc("Cash Document", self.parent)
			
			# Create notification
			notification = frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"Flag Resolved: {self.flag_type}",
				"email_content": f"""
				A flag on Cash Document {cash_doc.document_number} has been resolved.
				
				Flag Type: {self.flag_type}
				Resolved By: {self.resolved_by}
				Resolution Date: {self.resolution_date}
				Resolution Comments: {self.resolution_comments or 'No comments'}
				
				Original Comments: {self.comments or 'No comments'}
				""",
				"for_user": cash_doc.created_by_user,
				"type": "Alert",
				"document_type": "Cash Document",
				"document_name": cash_doc.name
			})
			# System notification - allowed to bypass permissions
			PermissionManager.insert_with_permission_check(notification, ignore_for_system=True)
	
	@frappe.whitelist()
	def get_flag_summary(self):
		"""Get a summary of this flag"""
		return {
			"flag_type": self.flag_type,
			"flagged_by": self.flagged_by,
			"flagged_by_role": self.flagged_by_role,
			"flag_date": self.flag_date,
			"comments": self.comments,
			"resolution_required": self.resolution_required,
			"is_resolved": bool(self.resolution_date),
			"resolved_by": self.resolved_by,
			"resolution_date": self.resolution_date,
			"resolution_comments": self.resolution_comments
		}
	
	def get_flag_priority(self):
		"""Get numeric priority for flag sorting"""
		priority_map = {
			"Priority": 1,
			"Rejected": 2,
			"Hold": 3,
			"Query": 4,
			"Revision Needed": 5,
			"Review Required": 6,
			"Approved": 7
		}
		return priority_map.get(self.flag_type, 8)