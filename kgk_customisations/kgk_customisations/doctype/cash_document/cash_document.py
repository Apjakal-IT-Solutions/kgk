# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

class CashDocument(Document):
	def autoname(self):
		"""Generate unique document number with format CD-YYYY-MM-#####"""
		self.name = make_autoname("CD-.YYYY.-.MM.-.#####.")
		self.document_number = self.name
	
	def before_insert(self):
		"""Set audit information when document is created"""
		self.created_by_user = frappe.session.user
		self.created_by_role = self.get_user_primary_role()
		self.last_modified_by = frappe.session.user
		self.last_modified_date = frappe.utils.now()
	
	def before_save(self):
		"""Update audit information on every save"""
		self.last_modified_by = frappe.session.user
		self.last_modified_date = frappe.utils.now()
		
		# Clean child tables to prevent framework issues - must be done early
		self.clean_child_tables()
		
		# Validate amount is positive
		if self.amount and self.amount <= 0:
			frappe.throw("Amount must be greater than zero")
		
		# Validate transaction date is not in future
		if self.transaction_date and frappe.utils.getdate(self.transaction_date) > frappe.utils.getdate():
			frappe.throw("Transaction date cannot be in the future")
	
	def before_insert(self):
		"""Set audit information when document is created"""
		self.created_by_user = frappe.session.user
		self.created_by_role = self.get_user_primary_role()
		self.last_modified_by = frappe.session.user
		self.last_modified_date = frappe.utils.now()
		
		# Clean child tables before insert
		self.clean_child_tables()
	
	def validate(self):
		"""Validate document data"""
		# Ensure party is selected if party_type is specified
		if self.party_type and not self.party:
			frappe.throw(f"Please select a {self.party_type}")
		
		# Validate contact number format if provided
		if self.contact_number:
			import re
			if not re.match(r'^[\d\-\+\s\(\)]+$', self.contact_number):
				frappe.throw("Invalid contact number format")
	
	def on_submit(self):
		"""Actions to perform when document is submitted"""
		self.status = "Processed"
		
		# Create accounting entries if applicable
		self.create_accounting_entries()
	
	def on_cancel(self):
		"""Actions to perform when document is cancelled"""
		self.status = "Cancelled"
		
		# Cancel related accounting entries
		self.cancel_accounting_entries()
	
	def get_user_primary_role(self):
		"""Get the primary cash management role of the current user"""
		user_roles = frappe.get_roles(frappe.session.user)
		cash_roles = ["Cash Super User", "Cash Accountant", "Cash Checker", "Cash Basic User"]
		
		for role in cash_roles:
			if role in user_roles:
				return role
		
		return "Cash Basic User"  # Default role
	
	def create_accounting_entries(self):
		"""Create corresponding Journal Entry for accounting"""
		# This will be implemented based on specific accounting requirements
		# For now, just log the action
		frappe.log_error(f"Accounting entry needed for Cash Document {self.name}", "Cash Document Accounting")
	
	def cancel_accounting_entries(self):
		"""Cancel related Journal Entries"""
		# This will be implemented based on specific accounting requirements
		# For now, just log the action
		frappe.log_error(f"Accounting entry cancellation needed for Cash Document {self.name}", "Cash Document Accounting")
	
	@frappe.whitelist()
	def add_flag(self, flag_type, comments=""):
		"""Add a flag to this document"""
		flag_doc = frappe.get_doc({
			"doctype": "Cash Document Flag",
			"parent": self.name,
			"parenttype": "Cash Document",
			"parentfield": "document_flags",
			"flag_type": flag_type,
			"flagged_by": frappe.session.user,
			"flag_date": frappe.utils.now(),
			"comments": comments
		})
		flag_doc.insert()
		
		# Update document status based on flag type
		if flag_type == "Approved":
			self.status = "Approved"
		elif flag_type == "Rejected":
			self.status = "Rejected"
		elif flag_type == "Review Required":
			self.status = "Pending Review"
		
		self.save()
		return flag_doc.name
	
	@frappe.whitelist()
	def get_document_summary(self):
		"""Get a summary of this document for dashboard display"""
		return {
			"document_number": self.document_number,
			"transaction_type": self.transaction_type,
			"amount": self.amount,
			"currency": self.currency,
			"transaction_date": self.transaction_date,
			"status": self.status,
			"party": self.party,
			"description": self.description[:100] + "..." if len(self.description or "") > 100 else self.description
		}
	
	def clean_child_tables(self):
		"""Clean up child table data to prevent framework issues"""
		# Simple approach - just ensure child tables exist and are lists
		if not hasattr(self, 'supporting_files'):
			self.supporting_files = []
		if not hasattr(self, 'document_flags'):
			self.document_flags = []
		
		# Ensure they are lists, not strings or other objects
		if not isinstance(self.supporting_files, list):
			self.supporting_files = []
		if not isinstance(self.document_flags, list):
			self.document_flags = []

# Bulk Operations for Cash Documents
@frappe.whitelist()
def bulk_finalize_documents(document_names):
	"""Bulk finalize multiple documents"""
	if isinstance(document_names, str):
		document_names = frappe.parse_json(document_names)
	
	success_count = 0
	errors = []
	
	for name in document_names:
		try:
			doc = frappe.get_doc('Cash Document', name)
			if doc.status not in ['Processed', 'Finalized']:
				doc.status = 'Processed'
				doc.last_modified_by = frappe.session.user
				doc.last_modified_date = frappe.utils.now()
				doc.save()
				success_count += 1
		except Exception as e:
			errors.append(f"{name}: {str(e)}")
	
	return {
		"success_count": success_count,
		"total": len(document_names),
		"errors": errors,
		"message": f"Successfully finalized {success_count} out of {len(document_names)} documents"
	}

@frappe.whitelist()
def bulk_approve_documents(document_names, comments=""):
	"""Bulk approve multiple documents"""
	if isinstance(document_names, str):
		document_names = frappe.parse_json(document_names)
	
	success_count = 0
	errors = []
	
	for name in document_names:
		try:
			doc = frappe.get_doc('Cash Document', name)
			if doc.status != 'Approved':
				# Add approval flag
				flag_doc = frappe.get_doc({
					"doctype": "Cash Document Flag",
					"parent": name,
					"parenttype": "Cash Document",
					"parentfield": "document_flags",
					"flag_type": "Approved",
					"flagged_by": frappe.session.user,
					"flag_date": frappe.utils.now(),
					"comments": comments or "Bulk approval"
				})
				flag_doc.insert()
				
				# Update document status
				doc.status = 'Approved'
				doc.last_modified_by = frappe.session.user
				doc.last_modified_date = frappe.utils.now()
				doc.save()
				success_count += 1
		except Exception as e:
			errors.append(f"{name}: {str(e)}")
	
	return {
		"success_count": success_count,
		"total": len(document_names),
		"errors": errors,
		"message": f"Successfully approved {success_count} out of {len(document_names)} documents"
	}

@frappe.whitelist()
def bulk_flag_documents(document_names, flag_type, comments=""):
	"""Bulk flag multiple documents"""
	if isinstance(document_names, str):
		document_names = frappe.parse_json(document_names)
	
	success_count = 0
	errors = []
	
	for name in document_names:
		try:
			doc = frappe.get_doc('Cash Document', name)
			
			# Add flag
			flag_doc = frappe.get_doc({
				"doctype": "Cash Document Flag",
				"parent": name,
				"parenttype": "Cash Document",
				"parentfield": "document_flags",
				"flag_type": flag_type,
				"flagged_by": frappe.session.user,
				"flag_date": frappe.utils.now(),
				"comments": comments or f"Bulk {flag_type.lower()}"
			})
			flag_doc.insert()
			
			# Update document status based on flag type
			if flag_type == "Approved":
				doc.status = "Approved"
			elif flag_type == "Rejected":
				doc.status = "Rejected"
			elif flag_type == "Review Required":
				doc.status = "Pending Review"
			
			doc.last_modified_by = frappe.session.user
			doc.last_modified_date = frappe.utils.now()
			doc.save()
			success_count += 1
		except Exception as e:
			errors.append(f"{name}: {str(e)}")
	
	return {
		"success_count": success_count,
		"total": len(document_names),
		"errors": errors,
		"message": f"Successfully flagged {success_count} out of {len(document_names)} documents as {flag_type}"
	}

@frappe.whitelist()
def check_missing_documents():
	"""Check for missing document numbers in sequence"""
	documents = frappe.get_all(
		'Cash Document',
		fields=['name', 'document_number'],
		filters={'document_number': ['like', 'CD-%']},
		order_by='document_number'
	)
	
	if not documents:
		return {"missing": [], "message": "No documents found"}
	
	# Extract numbers from format CD-YYYY-MM-#####
	numbers = []
	doc_map = {}
	
	for doc in documents:
		parts = doc.document_number.split('-')
		if len(parts) >= 4:
			try:
				num = int(parts[3])
				numbers.append(num)
				doc_map[num] = doc.document_number
			except (ValueError, IndexError):
				continue
	
	if not numbers:
		return {"missing": [], "message": "No valid document numbers found"}
	
	numbers.sort()
	missing = []
	
	# Check for gaps in sequence
	for i in range(numbers[0], numbers[-1] + 1):
		if i not in numbers:
			missing.append(f"CD-XXXX-XX-{i:05d}")
	
	return {
		"missing": missing,
		"total_documents": len(documents),
		"missing_count": len(missing),
		"first_number": numbers[0],
		"last_number": numbers[-1],
		"message": f"Found {len(missing)} missing document numbers out of {len(numbers)} total documents"
	}

@frappe.whitelist()
def get_pending_count():
	"""Get count of pending documents for dashboard"""
	pending_count = frappe.db.count('Cash Document', {'status': ['!=', 'Processed']})
	return pending_count

@frappe.whitelist()
def get_flagged_count():
	"""Get count of flagged documents"""
	flagged_count = frappe.db.sql("""
		SELECT COUNT(DISTINCT parent) 
		FROM `tabCash Document Flag` 
		WHERE flag_type != 'Approved'
	""")[0][0]
	return flagged_count

@frappe.whitelist()
def get_flagged_documents():
	"""Get list of flagged document names"""
	flagged_docs = frappe.db.sql("""
		SELECT DISTINCT parent 
		FROM `tabCash Document Flag` 
		WHERE flag_type != 'Approved'
	""", as_dict=True)
	return [doc.parent for doc in flagged_docs]