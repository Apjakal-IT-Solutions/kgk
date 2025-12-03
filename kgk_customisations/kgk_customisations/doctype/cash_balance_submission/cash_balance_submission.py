# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt
from kgk_customisations.kgk_customisations.audit_trail import AuditTrail


class CashBalanceSubmission(Document):
	def before_save(self):
		"""Calculate variance when balance is updated"""
		self.calculate_variance()
	
	def validate(self):
		"""Validate submission workflow"""
		self.validate_workflow_progression()
		self.calculate_calculated_balance()
	
	def calculate_calculated_balance(self):
		"""Calculate the balance from Cash Documents for this date and company"""
		if not self.submission_date or not self.company:
			return
		
		# Get all submitted Cash Documents for this date and company
		filters = {
			"transaction_date": self.submission_date,
			"company": self.company,
			"docstatus": 1  # Only submitted documents
		}
		
		documents = frappe.get_all(
			"Cash Document",
			filters=filters,
			fields=["main_document_type", "amount"]
		)
		
		total_receipts = 0
		total_payments = 0
		
		for doc in documents:
			if doc.main_document_type in ["Receipt", "Invoice"]:
				total_receipts += flt(doc.amount)
			elif doc.main_document_type in ["Payment", "Petty Cash"]:
				total_payments += flt(doc.amount)
		
		self.total_receipts = total_receipts
		self.total_payments = total_payments
		
		# Get opening balance from previous day's closing
		prev_date = frappe.utils.add_days(self.submission_date, -1)
		prev_submission = frappe.get_all(
			"Cash Balance Submission",
			filters={
				"submission_date": prev_date,
				"company": self.company,
				"balance_type": self.balance_type,
				"verification_status": "Accountant Verified"
			},
			fields=["accountant_balance"],
			limit=1
		)
		
		if prev_submission:
			self.opening_balance = prev_submission[0].accountant_balance
		else:
			self.opening_balance = 0
		
		# Calculate closing balance
		self.calculated_balance = self.opening_balance + total_receipts - total_payments
	
	def calculate_variance(self):
		"""Calculate variance between submitted and calculated balance"""
		# Determine which balance to compare against calculated balance
		reference_balance = None
		
		if self.accountant_balance:
			reference_balance = self.accountant_balance
		elif self.checker_balance:
			reference_balance = self.checker_balance
		elif self.basic_balance:
			reference_balance = self.basic_balance
		
		if reference_balance and self.calculated_balance:
			self.variance = reference_balance - self.calculated_balance
			
			# Calculate percentage variance
			if self.calculated_balance != 0:
				self.variance_percentage = (self.variance / self.calculated_balance) * 100
			else:
				self.variance_percentage = 0
	
	def validate_workflow_progression(self):
		"""Ensure workflow progresses logically: Basic → Checker → Accountant"""
		# Can't have checker balance without basic balance
		if self.checker_balance and not self.basic_balance:
			frappe.throw("Checker balance cannot be submitted without Basic User balance")
		
		# Can't have accountant balance without checker balance
		if self.accountant_balance and not self.checker_balance:
			frappe.throw("Accountant balance cannot be submitted without Checker balance")
	
	@frappe.whitelist()
	def submit_basic_balance(self, balance, comments=""):
		"""Submit basic user balance (first verification tier)"""
		if self.verification_status not in ["Draft", "Rejected"]:
			frappe.throw("Basic balance already submitted")
		
		self.basic_balance = balance
		self.basic_submitted_at = now_datetime()
		self.basic_submitted_by = frappe.session.user
		self.basic_comments = comments
		self.verification_status = "Basic Submitted"
		
		self.calculate_calculated_balance()
		self.calculate_variance()
		self.save()
		
		# Log verification in audit trail
		AuditTrail.log_verification(self.name, "basic", balance)
		
		frappe.msgprint(f"Basic balance of {balance} submitted successfully")
	
	@frappe.whitelist()
	def submit_checker_balance(self, balance, comments=""):
		"""Submit checker balance (second verification tier)"""
		if self.verification_status != "Basic Submitted":
			frappe.throw("Cannot submit checker balance - basic balance must be submitted first")
		
		self.checker_balance = balance
		self.checker_submitted_at = now_datetime()
		self.checker_submitted_by = frappe.session.user
		self.checker_comments = comments
		self.verification_status = "Checker Verified"
		
		self.calculate_variance()
		self.save()
		
		# Log verification in audit trail
		AuditTrail.log_verification(self.name, "checker", balance)
		
		# Check if variance exceeds threshold
		self._check_variance_threshold()
		
		frappe.msgprint(f"Checker balance of {balance} verified successfully")
	
	@frappe.whitelist()
	def submit_accountant_balance(self, balance, comments=""):
		"""Submit accountant balance (final verification tier)"""
		if self.verification_status != "Checker Verified":
			frappe.throw("Cannot submit accountant balance - checker verification must be completed first")
		
		self.accountant_balance = balance
		self.accountant_submitted_at = now_datetime()
		self.accountant_submitted_by = frappe.session.user
		self.accountant_comments = comments
		self.verification_status = "Accountant Verified"
		
		self.calculate_variance()
		self.save()
		
		# Log verification in audit trail
		AuditTrail.log_verification(self.name, "accountant", balance)
		
		# Check if variance exceeds threshold
		self._check_variance_threshold()
		
		# Update Daily Cash Balance with final verified amount
		self._update_daily_cash_balance()
		
		frappe.msgprint(f"Accountant balance of {balance} verified and finalized successfully")
	
	@frappe.whitelist()
	def reject_submission(self, comments=""):
		"""Reject the current submission and reset to draft"""
		self.verification_status = "Rejected"
		self.accountant_comments = comments
		self.save()
		
		frappe.msgprint("Submission rejected. Please review and resubmit.")
	
	def _check_variance_threshold(self):
		"""Check if variance exceeds threshold from settings"""
		settings = frappe.get_single("Cash Management Settings")
		
		if abs(self.variance_percentage) > settings.variance_threshold:
			frappe.msgprint(
				f"Warning: Variance of {self.variance_percentage:.2f}% exceeds threshold of {settings.variance_threshold}%",
				indicator="orange",
				alert=True
			)
			
			if settings.notify_on_variance:
				self._send_variance_notification()
	
	def _send_variance_notification(self):
		"""Send notification when variance exceeds threshold"""
		# Get users with Accounts Manager role
		managers = frappe.get_all(
			"Has Role",
			filters={"role": "Accounts Manager"},
			fields=["parent"],
			pluck="parent"
		)
		
		message = f"""
		<p>Cash Balance Submission variance alert:</p>
		<ul>
			<li>Date: {self.submission_date}</li>
			<li>Company: {self.company}</li>
			<li>Calculated Balance: {self.calculated_balance}</li>
			<li>Submitted Balance: {self.accountant_balance or self.checker_balance or self.basic_balance}</li>
			<li>Variance: {self.variance} ({self.variance_percentage:.2f}%)</li>
		</ul>
		"""
		
		for user in managers:
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"High Variance Alert - {self.name}",
				"email_content": message,
				"for_user": user,
				"type": "Alert",
				"document_type": self.doctype,
				"document_name": self.name
			}).insert(ignore_permissions=True)
	
	def _update_daily_cash_balance(self):
		"""Update Daily Cash Balance with final accountant-verified balance"""
		# Find or create Daily Cash Balance entry
		balance_name = frappe.db.exists(
			"Daily Cash Balance",
			{
				"balance_date": self.submission_date,
				"company": self.company
			}
		)
		
		if balance_name:
			balance_doc = frappe.get_doc("Daily Cash Balance", balance_name)
		else:
			balance_doc = frappe.get_doc({
				"doctype": "Daily Cash Balance",
				"balance_date": self.submission_date,
				"company": self.company
			})
		
		# Update with verified balances
		balance_doc.opening_balance = self.opening_balance
		balance_doc.total_receipts = self.total_receipts
		balance_doc.total_payments = self.total_payments
		balance_doc.closing_balance = self.accountant_balance
		balance_doc.expected_balance = self.calculated_balance
		balance_doc.variance = self.variance
		balance_doc.verified = 1
		balance_doc.verified_by = self.accountant_submitted_by
		balance_doc.verified_at = self.accountant_submitted_at
		
		balance_doc.save(ignore_permissions=True)
		frappe.db.commit()
