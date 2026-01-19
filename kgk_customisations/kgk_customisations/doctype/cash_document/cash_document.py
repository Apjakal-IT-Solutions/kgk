# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from kgk_customisations.kgk_customisations.audit_trail import AuditTrail
from kgk_customisations.kgk_customisations.utils.input_validator import InputValidator

class CashDocument(Document):
	def autoname(self):
		"""Generate unique document number with format CD-{company_abbr}-YYYY-MM-#####"""
		if not self.company:
			frappe.throw("Company is required before saving")
		
		# Get company abbreviation
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		if not company_abbr:
			company_abbr = self.company[:3].upper()
		
		self.name = make_autoname(f"CD-{company_abbr}-.YYYY.-.MM.-.#####.")
		self.document_number = self.name
	
	def before_insert(self):
		"""Set audit information when document is created"""
		# Set audit fields
		self.created_by_user = frappe.session.user
		self.created_by_role = self.get_user_primary_role()
		self.last_modified_by = frappe.session.user
		self.last_modified_date = frappe.utils.now()
		
		# Auto-populate year from transaction_date
		if self.transaction_date:
			self.year = frappe.utils.getdate(self.transaction_date).year
		
		# Auto-generate invoice number if not provided and document type requires it
		if not self.invoice_number and self.main_document_type and self.company:
			# Import here to avoid circular dependency
			from kgk_customisations.kgk_customisations.doctype.invoice_number_series.invoice_number_series import InvoiceNumberSeries
			
			try:
				year = self.year or (frappe.utils.getdate(self.transaction_date).year if self.transaction_date else frappe.utils.getdate().year)
				self.invoice_number = InvoiceNumberSeries.generate_invoice_number(
					self.main_document_type,
					self.company,
					year
				)
			except Exception as e:
				frappe.log_error(f"Failed to auto-generate invoice number: {str(e)}", "Cash Document Invoice Generation")
				# Continue without invoice number - it can be added manually
		
		# Clean child tables before insert
		self.clean_child_tables()
	
	def before_save(self):
		"""Update audit information on every save"""
		# Update audit fields
		self.last_modified_by = frappe.session.user
		self.last_modified_date = frappe.utils.now()
		
		# Auto-populate year from transaction_date if changed
		if self.transaction_date:
			self.year = frappe.utils.getdate(self.transaction_date).year
		
		# Validate company is set
		if not self.company:
			frappe.throw("Company is required")
		
		# Clean child tables to prevent framework issues - must be done early
		self.clean_child_tables()
		
		# Auto-assign suffix letters to supporting files
		self.assign_file_suffixes()
		
		# Validate amount is positive
		if self.amount and self.amount <= 0:
			frappe.throw("Amount must be greater than zero")
		
		# Validate transaction date is not in future
		if self.transaction_date and frappe.utils.getdate(self.transaction_date) > frappe.utils.getdate():
			frappe.throw("Transaction date cannot be in the future")
	
	def validate(self):
		"""Validate document data"""
		# Validate company is set
		if not self.company:
			frappe.throw("Company is required")
		
		# Validate primary_document_file for non-Draft status
		if self.status != "Draft" and not self.primary_document_file:
			frappe.throw("Primary Document File is required for non-Draft documents")
		
		# Validate file attachments
		self.validate_file_attachments()
		
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
		old_status = self.status
		self.status = "Processed"
		
		# Log workflow change
		AuditTrail.log_workflow_change(self.name, self.doctype, old_status, "Processed")
		
		# Auto-update Daily Cash Balance if enabled
		if self.auto_update_balance and self.balance_entry:
			self.update_daily_cash_balance()
		
		# Create accounting entries if applicable
		self.create_accounting_entries()
	
	def on_cancel(self):
		"""Actions to perform when document is cancelled"""
		old_status = self.status
		self.status = "Cancelled"
		
		# Log workflow change
		AuditTrail.log_workflow_change(self.name, self.doctype, old_status, "Cancelled")
		
		# Reverse Daily Cash Balance update if enabled
		if self.auto_update_balance and self.balance_entry:
			self.reverse_daily_cash_balance()
		
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
	
	def assign_file_suffixes(self):
		"""Auto-assign suffix letters (A, B, C...) to supporting files based on upload order"""
		if not self.supporting_files:
			return
		
		# Get alphabet for suffix assignment
		import string
		alphabet = list(string.ascii_uppercase)
		
		# Track existing suffixes to avoid duplicates
		existing_suffixes = set()
		
		# First pass: collect existing suffixes that should be preserved
		for idx, file_row in enumerate(self.supporting_files):
			if file_row.file_suffix and file_row.file_suffix.strip():
				existing_suffixes.add(file_row.file_suffix.strip().upper())
		
		# Second pass: assign missing suffixes
		suffix_index = 0
		for idx, file_row in enumerate(self.supporting_files):
			if not file_row.file_suffix or not file_row.file_suffix.strip():
				# Find next available suffix
				while suffix_index < len(alphabet):
					candidate = alphabet[suffix_index]
					if candidate not in existing_suffixes:
						file_row.file_suffix = candidate
						existing_suffixes.add(candidate)
						suffix_index += 1
						break
					suffix_index += 1
				
				# If we run out of single letters, use double letters (AA, AB, AC...)
				if suffix_index >= len(alphabet) and not file_row.file_suffix:
					double_index = suffix_index - len(alphabet)
					first_letter = alphabet[double_index // len(alphabet)]
					second_letter = alphabet[double_index % len(alphabet)]
					candidate = f"{first_letter}{second_letter}"
					if candidate not in existing_suffixes:
						file_row.file_suffix = candidate
						existing_suffixes.add(candidate)
						suffix_index += 1
			
			# Auto-set upload metadata if not set
			if not file_row.uploaded_by:
				file_row.uploaded_by = frappe.session.user
			if not file_row.upload_date:
				file_row.upload_date = frappe.utils.now()
	
	def validate_file_attachments(self):
		"""Validate file types and sizes for all attachments"""
		# Maximum file size in MB (configurable)
		max_file_size_mb = frappe.db.get_single_value("Cash Management Settings", "max_file_size_mb") or 10
		max_file_size_bytes = max_file_size_mb * 1024 * 1024
		
		# Allowed file extensions
		allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.zip']
		
		# Validate primary document file
		if self.primary_document_file:
			self._validate_single_file(self.primary_document_file, "Primary Document", max_file_size_bytes, allowed_extensions)
		
		# Validate supporting files
		if self.supporting_files:
			for idx, file_row in enumerate(self.supporting_files, 1):
				if file_row.file_attachment:
					self._validate_single_file(
						file_row.file_attachment, 
						f"Supporting File {idx} ({file_row.file_suffix or 'N/A'})",
						max_file_size_bytes,
						allowed_extensions
					)
					
					# Auto-calculate file size if not set
					if file_row.file_attachment and not file_row.file_size:
						try:
							file_doc = frappe.get_doc("File", {"file_url": file_row.file_attachment})
							if file_doc and file_doc.file_size:
								# Convert bytes to human readable format
								file_row.file_size = self._format_file_size(file_doc.file_size)
						except Exception as e:
							frappe.log_error(f"Failed to get file size: {str(e)}", "File Size Calculation")
	
	def _validate_single_file(self, file_url, file_label, max_size_bytes, allowed_extensions):
		"""Validate a single file attachment"""
		import os
		
		if not file_url:
			return
		
		# Extract file extension
		file_name = file_url.split('/')[-1]
		file_ext = os.path.splitext(file_name)[1].lower()
		
		# Check if extension is allowed
		if file_ext not in allowed_extensions:
			frappe.throw(f"{file_label}: File type '{file_ext}' is not allowed. Allowed types: {', '.join(allowed_extensions)}")
		
		# Check file size
		try:
			file_doc = frappe.get_doc("File", {"file_url": file_url})
			if file_doc and file_doc.file_size:
				if file_doc.file_size > max_size_bytes:
					max_size_mb = max_size_bytes / (1024 * 1024)
					actual_size_mb = file_doc.file_size / (1024 * 1024)
					frappe.throw(f"{file_label}: File size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB)")
		except Exception as e:
			# If we can't validate size, log it but don't fail
			frappe.log_error(f"Failed to validate file size for {file_label}: {str(e)}", "File Validation")
	
	def _format_file_size(self, size_bytes):
		"""Convert bytes to human readable format"""
		for unit in ['B', 'KB', 'MB', 'GB']:
			if size_bytes < 1024.0:
				return f"{size_bytes:.2f} {unit}"
			size_bytes /= 1024.0
		return f"{size_bytes:.2f} TB"
	
	def update_daily_cash_balance(self):
		"""Update the linked Daily Cash Balance with this document's amount"""
		if not self.balance_entry:
			return
		
		try:
			balance_doc = frappe.get_doc("Daily Cash Balance", self.balance_entry)
			
			# Update balance based on transaction type
			if self.main_document_type in ["Receipt", "Invoice"]:
				# Receipts and Invoices increase the balance
				balance_doc.total_receipts = (balance_doc.total_receipts or 0) + self.amount
				balance_doc.closing_balance = (balance_doc.opening_balance or 0) + (balance_doc.total_receipts or 0) - (balance_doc.total_payments or 0)
			elif self.main_document_type in ["Payment", "Petty Cash"]:
				# Payments and Petty Cash decrease the balance
				balance_doc.total_payments = (balance_doc.total_payments or 0) + self.amount
				balance_doc.closing_balance = (balance_doc.opening_balance or 0) + (balance_doc.total_receipts or 0) - (balance_doc.total_payments or 0)
			
			# Recalculate variance
			if balance_doc.expected_balance:
				balance_doc.variance = (balance_doc.closing_balance or 0) - balance_doc.expected_balance
			
			# Save with permission check - system operation (automated balance calculation)
			PermissionManager.save_with_permission_check(balance_doc, ignore_for_system=True)
			frappe.db.commit()
			frappe.logger().info(f"Updated Daily Cash Balance {self.balance_entry} from Cash Document {self.name}")
			
			# Log balance update in audit trail
			AuditTrail.log_balance_update(self.name, self.balance_entry, "update", self.amount)
			
		except Exception as e:
			frappe.log_error(f"Failed to update Daily Cash Balance: {str(e)}", "Balance Update Error")
			# Don't throw error - log it and continue
	
	def reverse_daily_cash_balance(self):
		"""Reverse the balance update when document is cancelled"""
		if not self.balance_entry:
			return
		
		try:
			balance_doc = frappe.get_doc("Daily Cash Balance", self.balance_entry)
			
			# Reverse the balance update
			if self.main_document_type in ["Receipt", "Invoice"]:
				balance_doc.total_receipts = (balance_doc.total_receipts or 0) - self.amount
				balance_doc.closing_balance = (balance_doc.opening_balance or 0) + (balance_doc.total_receipts or 0) - (balance_doc.total_payments or 0)
			elif self.main_document_type in ["Payment", "Petty Cash"]:
				balance_doc.total_payments = (balance_doc.total_payments or 0) - self.amount
				balance_doc.closing_balance = (balance_doc.opening_balance or 0) + (balance_doc.total_receipts or 0) - (balance_doc.total_payments or 0)
			
			# Recalculate variance
			if balance_doc.expected_balance:
				balance_doc.variance = (balance_doc.closing_balance or 0) - balance_doc.expected_balance
			
			# Save with permission check - system operation (automated balance reversal)
			PermissionManager.save_with_permission_check(balance_doc, ignore_for_system=True)
			frappe.db.commit()
			frappe.logger().info(f"Reversed Daily Cash Balance {self.balance_entry} from Cash Document {self.name}")
			
			# Log balance reversal in audit trail
			AuditTrail.log_balance_update(self.name, self.balance_entry, "reverse", self.amount)
			
		except Exception as e:
			frappe.log_error(f"Failed to reverse Daily Cash Balance: {str(e)}", "Balance Reverse Error")
	
	@frappe.whitelist()
	def add_flag(self, flag_type, comments=""):
		"""Add a flag to this document"""
		# Validate inputs
		validator = InputValidator()
		validator.validate_choice(flag_type, "flag_type", ["Approved", "Rejected", "Review Required", "Information Request"])
		
		# Sanitize comments (max 500 characters)
		if comments:
			comments = validator.sanitize_string(comments, max_length=500)
		
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
	# Validate and parse input
	document_names = InputValidator.validate_json(document_names, "document_names")
	
	if not isinstance(document_names, list):
		frappe.throw(_("document_names must be a list"), frappe.ValidationError)
	
	if len(document_names) == 0:
		frappe.throw(_("No documents provided"), frappe.ValidationError)
	
	if len(document_names) > 100:
		frappe.throw(_("Cannot process more than 100 documents at once"), frappe.ValidationError)
	
	success_count = 0
	errors = []
	
	for name in document_names:
		try:
			# Validate document name
			name = InputValidator.validate_document_name('Cash Document', name)
			
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
	# Validate and parse input
	document_names = InputValidator.validate_json(document_names, "document_names")
	
	if not isinstance(document_names, list):
		frappe.throw(_("document_names must be a list"), frappe.ValidationError)
	
	if len(document_names) > 100:
		frappe.throw(_("Cannot process more than 100 documents at once"), frappe.ValidationError)
	
	# Sanitize comments
	comments = InputValidator.sanitize_string(comments, max_length=500)
	
	success_count = 0
	errors = []
	
	for name in document_names:
		try:
			# Validate document name
			name = InputValidator.validate_document_name('Cash Document', name)
			
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
	# Validate inputs
	validator = InputValidator()
	
	if isinstance(document_names, str):
		document_names = frappe.parse_json(document_names)
	
	# Validate document list
	if not isinstance(document_names, list):
		frappe.throw("document_names must be a list")
	
	if len(document_names) > 100:
		frappe.throw("Cannot flag more than 100 documents at once")
	
	# Validate flag type
	validator.validate_choice(flag_type, "flag_type", ["Approved", "Rejected", "Review Required", "Information Request"])
	
	# Sanitize comments
	if comments:
		comments = validator.sanitize_string(comments, max_length=500)
	
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