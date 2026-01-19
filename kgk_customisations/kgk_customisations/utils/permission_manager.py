# Copyright (c) 2026, KGK and contributors
# For license information, please see license.txt

"""
Permission Management Utilities
Provides secure permission checking for sensitive operations
"""

import frappe
from frappe import _
from frappe.permissions import has_permission


class PermissionManager:
	"""Centralized permission management for cash management system"""
	
	# System operations that legitimately need to bypass permissions
	SYSTEM_DOCTYPES = [
		"Comment",  # Audit trail logging
		"Notification Log",  # System notifications
		"Version",  # Document versioning
		"Activity Log"  # Activity tracking
	]
	
	@staticmethod
	def can_create_system_log(doctype):
		"""
		Check if creating a system log entry is allowed
		System logs (audit trail, notifications) can bypass permissions
		if they're for legitimate system operations
		
		Args:
			doctype: DocType name
			
		Returns:
			bool: True if system log creation is allowed
		"""
		return doctype in PermissionManager.SYSTEM_DOCTYPES
	
	@staticmethod
	def can_update_balance(balance_doc, user=None):
		"""
		Check if user can update a Daily Cash Balance
		
		Args:
			balance_doc: Daily Cash Balance document
			user: User to check (default: current user)
			
		Returns:
			bool: True if user has permission
		"""
		user = user or frappe.session.user
		
		# Administrator always allowed
		if user == "Administrator":
			return True
		
		# Check if user has write permission on Daily Cash Balance
		if has_permission("Daily Cash Balance", "write", user=user, doc=balance_doc):
			return True
		
		# Check if user has Cash Manager role
		if "Cash Manager" in frappe.get_roles(user):
			return True
		
		return False
	
	@staticmethod
	def can_create_document(doctype, user=None):
		"""
		Check if user can create a document
		
		Args:
			doctype: DocType name
			user: User to check (default: current user)
			
		Returns:
			bool: True if user has create permission
		"""
		user = user or frappe.session.user
		
		# Administrator always allowed
		if user == "Administrator":
			return True
		
		# Check if user has create permission
		if has_permission(doctype, "create", user=user):
			return True
		
		return False
	
	@staticmethod
	def validate_company_access(company, user=None):
		"""
		Validate if user has access to a specific company
		
		Args:
			company: Company name
			user: User to check (default: current user)
			
		Returns:
			bool: True if user has access to company
		"""
		user = user or frappe.session.user
		
		# Administrator always has access
		if user == "Administrator":
			return True
		
		# Get user's permitted companies
		user_companies = frappe.get_all(
			"User Permission",
			filters={
				"user": user,
				"allow": "Company",
				"for_value": company
			},
			pluck="name"
		)
		
		# If no specific company restrictions, user has access to all
		if not user_companies:
			all_user_permissions = frappe.get_all(
				"User Permission",
				filters={
					"user": user,
					"allow": "Company"
				},
				pluck="name"
			)
			# If user has ANY company restrictions, they don't have access to this one
			if all_user_permissions:
				return False
			return True
		
		return True
	
	@staticmethod
	def enforce_permission(doctype, ptype, doc=None, throw=True):
		"""
		Enforce permission check - raises exception if permission denied
		
		Args:
			doctype: DocType name
			ptype: Permission type (read, write, create, delete, submit, cancel, etc.)
			doc: Document object (optional)
			throw: Raise exception if permission denied (default: True)
			
		Returns:
			bool: True if permission granted
			
		Raises:
			frappe.PermissionError: If permission denied and throw=True
		"""
		user = frappe.session.user
		
		# Administrator bypass
		if user == "Administrator":
			return True
		
		# Check permission
		has_perm = has_permission(doctype, ptype, doc=doc, user=user)
		
		if not has_perm and throw:
			frappe.throw(
				_("You do not have permission to {0} {1}").format(ptype, doctype),
				frappe.PermissionError
			)
		
		return has_perm
	
	@staticmethod
	def is_system_operation():
		"""
		Check if current operation is a system-level operation
		System operations include: scheduled tasks, migrations, fixtures
		
		Returns:
			bool: True if system operation
		"""
		# Check if running from scheduler
		if frappe.flags.in_scheduler:
			return True
		
		# Check if running migration
		if frappe.flags.in_migrate:
			return True
		
		# Check if running fixture/setup
		if frappe.flags.in_install or frappe.flags.in_setup_wizard:
			return True
		
		# Check if running test
		if frappe.flags.in_test:
			return True
		
		return False
	
	@staticmethod
	def insert_with_permission_check(doc, ignore_for_system=False):
		"""
		Insert document with proper permission checking
		
		Args:
			doc: Document object to insert
			ignore_for_system: Allow ignore_permissions for system doctypes
			
		Returns:
			Document: Inserted document
		"""
		# System operations or system doctypes can bypass
		if ignore_for_system and (
			PermissionManager.is_system_operation() or 
			PermissionManager.can_create_system_log(doc.doctype)
		):
			return doc.insert(ignore_permissions=True)
		
		# Regular permission check
		PermissionManager.enforce_permission(doc.doctype, "create")
		return doc.insert()
	
	@staticmethod
	def save_with_permission_check(doc, ignore_for_system=False):
		"""
		Save document with proper permission checking
		
		Args:
			doc: Document object to save
			ignore_for_system: Allow ignore_permissions for system operations
			
		Returns:
			Document: Saved document
		"""
		# System operations can bypass
		if ignore_for_system and PermissionManager.is_system_operation():
			return doc.save(ignore_permissions=True)
		
		# Regular permission check
		PermissionManager.enforce_permission(doc.doctype, "write", doc=doc)
		return doc.save()


def has_role(user, role):
	"""
	Check if user has a specific role
	
	Args:
		user: User name
		role: Role name
		
	Returns:
		bool: True if user has role
	"""
	return role in frappe.get_roles(user)


def get_user_companies(user=None):
	"""
	Get list of companies user has access to
	
	Args:
		user: User name (default: current user)
		
	Returns:
		list: List of company names
	"""
	user = user or frappe.session.user
	
	if user == "Administrator":
		return frappe.get_all("Company", pluck="name")
	
	# Get user's company permissions
	permitted_companies = frappe.get_all(
		"User Permission",
		filters={
			"user": user,
			"allow": "Company"
		},
		pluck="for_value"
	)
	
	# If no restrictions, return all companies
	if not permitted_companies:
		return frappe.get_all("Company", pluck="name")
	
	return permitted_companies
