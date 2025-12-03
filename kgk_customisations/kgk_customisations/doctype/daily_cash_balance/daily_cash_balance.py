# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt
from kgk_customisations.kgk_customisations.audit_trail import AuditTrail

class DailyCashBalance(Document):
	def autoname(self):
		"""Generate unique name with format DCB-YYYY-MM-DD"""
		date_str = getdate(self.balance_date).strftime("%Y-%m-%d")
		self.name = f"DCB-{date_str}"
	
	def before_insert(self):
		"""Set audit information when document is created"""
		self.created_by_user = frappe.session.user
		self.last_updated_by = frappe.session.user
		self.last_updated_date = frappe.utils.now()
	
	def before_save(self):
		"""Calculate totals and variance before saving"""
		self.last_updated_by = frappe.session.user
		self.last_updated_date = frappe.utils.now()
		
		# Calculate manual totals
		self.calculate_manual_totals()
		
		# Get ERP balance from actual transactions
		self.calculate_erp_balance()
		
		# Calculate variance
		self.calculate_variance()
		
		# Determine reconciliation requirement
		self.check_reconciliation_required()
	
	def validate(self):
		"""Validate document data"""
		# Ensure balance date is not in future
		if self.balance_date and getdate(self.balance_date) > getdate():
			frappe.throw("Balance date cannot be in the future")
		
		# Check for duplicate entries for the same date
		existing = frappe.db.exists("Daily Cash Balance", {
			"balance_date": self.balance_date,
			"name": ["!=", self.name or ""]
		})
		if existing:
			frappe.throw(f"Daily Cash Balance already exists for {self.balance_date}")
	
	def calculate_manual_totals(self):
		"""Calculate total manual counts and balances"""
		self.total_manual_count = (
			flt(self.basic_user_count) + 
			flt(self.checker_count) + 
			flt(self.accountant_count) + 
			flt(self.super_user_count)
		)
		
		self.total_manual_balance = (
			flt(self.basic_user_balance) + 
			flt(self.checker_balance) + 
			flt(self.accountant_balance) + 
			flt(self.super_user_balance)
		)
	
	def calculate_erp_balance(self):
		"""Calculate ERP balance from actual Cash Document transactions"""
		# Get all submitted Cash Documents for this date
		cash_docs = frappe.db.sql("""
			SELECT 
				COUNT(*) as count,
				SUM(CASE WHEN transaction_type = 'Receipt' THEN amount ELSE -amount END) as net_amount
			FROM `tabCash Document`
			WHERE transaction_date = %s 
			AND docstatus = 1
			AND currency = %s
		""", (self.balance_date, self.currency), as_dict=True)
		
		if cash_docs:
			self.erp_transaction_count = cash_docs[0].count or 0
			self.erp_balance = cash_docs[0].net_amount or 0
		else:
			self.erp_transaction_count = 0
			self.erp_balance = 0
	
	def calculate_variance(self):
		"""Calculate variance between manual and ERP balances"""
		manual_balance = flt(self.total_manual_balance)
		erp_balance = flt(self.erp_balance)
		
		self.variance_amount = manual_balance - erp_balance
		self.variance_count = flt(self.total_manual_count) - flt(self.erp_transaction_count)
		
		# Calculate percentage variance
		if erp_balance != 0:
			self.variance_percentage = (self.variance_amount / erp_balance) * 100
		else:
			self.variance_percentage = 100 if manual_balance != 0 else 0
	
	def check_reconciliation_required(self):
		"""Determine if reconciliation is required"""
		# Set reconciliation required if variance exceeds threshold
		variance_threshold = frappe.db.get_single_value("Cash Management Settings", "variance_threshold") or 5
		
		if abs(flt(self.variance_percentage)) > variance_threshold:
			self.reconciliation_required = 1
			self.status = "Variance Identified"
			# Log variance alert
			AuditTrail.log_variance_alert(self.name, self.variance_amount, self.variance_percentage)
		elif self.variance_amount == 0 and self.variance_count == 0:
			self.status = "Reconciled"
		else:
			self.status = "Pending Review"
	
	@frappe.whitelist()
	def mark_reconciled(self, reconciliation_notes=""):
		"""Mark the balance as reconciled"""
		self.reconciled_by = frappe.session.user
		self.reconciliation_date = frappe.utils.now()
		self.status = "Reconciled"
		self.reconciliation_required = 0
		
		if reconciliation_notes:
			self.notes = (self.notes or "") + f"\n\nReconciliation Notes ({frappe.utils.now()}):\n{reconciliation_notes}"
		
		self.save()
		
		# Log reconciliation in audit trail
		AuditTrail.log_reconciliation(self.name, "manual", reconciliation_notes)
		
		return "Balance marked as reconciled successfully"
	
	@frappe.whitelist()
	def refresh_erp_data(self):
		"""Refresh ERP data from Cash Documents"""
		self.calculate_erp_balance()
		self.calculate_variance()
		self.check_reconciliation_required()
		self.save()
		return "ERP data refreshed successfully"
	
	@frappe.whitelist()
	def get_variance_details(self):
		"""Get detailed variance information"""
		return {
			"manual_count": self.total_manual_count,
			"manual_balance": self.total_manual_balance,
			"erp_count": self.erp_transaction_count,
			"erp_balance": self.erp_balance,
			"variance_count": self.variance_count,
			"variance_amount": self.variance_amount,
			"variance_percentage": self.variance_percentage,
			"reconciliation_required": self.reconciliation_required,
			"status": self.status,
			"debug": "Method called successfully"
		}
	
	@frappe.whitelist()
	def get_role_breakdown(self):
		"""Get breakdown by user roles"""
		return {
			"basic_user": {
				"count": self.basic_user_count,
				"balance": self.basic_user_balance
			},
			"checker": {
				"count": self.checker_count,
				"balance": self.checker_balance
			},
			"accountant": {
				"count": self.accountant_count,
				"balance": self.accountant_balance
			},
			"super_user": {
				"count": self.super_user_count,
				"balance": self.super_user_balance
			}
		}
	
	@frappe.whitelist()
	def get_related_documents(self):
		"""Get related Cash Documents for this date"""
		cash_docs = frappe.db.sql("""
			SELECT 
				name, document_number, transaction_type, amount, 
				party, description, status, created_by_user
			FROM `tabCash Document`
			WHERE transaction_date = %s 
			AND currency = %s
			ORDER BY creation DESC
		""", (self.balance_date, self.currency), as_dict=True)
		
		return cash_docs
	
	@frappe.whitelist()
	def calculate_document_totals(self, company=None):
		"""Calculate totals from Cash Documents for this date and optionally company
		
		Args:
			company: Optional company filter
			
		Returns:
			dict: Dictionary containing receipt totals, payment totals, net balance
		"""
		filters = {
			"transaction_date": self.balance_date,
			"docstatus": 1  # Only submitted documents
		}
		
		if company:
			filters["company"] = company
		
		# Get all submitted Cash Documents
		documents = frappe.get_all(
			"Cash Document",
			filters=filters,
			fields=["main_document_type", "amount", "currency"]
		)
		
		totals = {
			"total_receipts": 0,
			"total_payments": 0,
			"total_invoices": 0,
			"total_petty_cash": 0,
			"document_count": len(documents),
			"net_balance": 0
		}
		
		for doc in documents:
			amount = flt(doc.amount)
			
			if doc.main_document_type == "Receipt":
				totals["total_receipts"] += amount
			elif doc.main_document_type == "Payment":
				totals["total_payments"] += amount
			elif doc.main_document_type == "Invoice":
				totals["total_invoices"] += amount
			elif doc.main_document_type == "Petty Cash":
				totals["total_petty_cash"] += amount
		
		# Calculate net balance (receipts + invoices - payments - petty cash)
		totals["net_balance"] = (
			totals["total_receipts"] + 
			totals["total_invoices"] - 
			totals["total_payments"] - 
			totals["total_petty_cash"]
		)
		
		return totals
	
	@frappe.whitelist()
	def check_variance(self, submitted_balance=None):
		"""Check variance between submitted balance and calculated balance
		
		Args:
			submitted_balance: The balance submitted by users (default: use total_manual_balance)
			
		Returns:
			dict: Variance details including amount, percentage, and status
		"""
		if submitted_balance is None:
			submitted_balance = self.total_manual_balance or 0
		
		# Calculate document totals
		document_totals = self.calculate_document_totals()
		calculated_balance = document_totals["net_balance"]
		
		# Calculate variance
		variance_amount = flt(submitted_balance) - flt(calculated_balance)
		
		# Calculate percentage variance
		if calculated_balance != 0:
			variance_percentage = (variance_amount / calculated_balance) * 100
		else:
			variance_percentage = 100 if variance_amount != 0 else 0
		
		# Get threshold from settings
		variance_threshold = frappe.db.get_single_value(
			"Cash Management Settings", 
			"variance_threshold"
		) or 5
		
		# Determine status
		exceeds_threshold = abs(variance_percentage) > variance_threshold
		
		return {
			"submitted_balance": submitted_balance,
			"calculated_balance": calculated_balance,
			"variance_amount": variance_amount,
			"variance_percentage": variance_percentage,
			"variance_threshold": variance_threshold,
			"exceeds_threshold": exceeds_threshold,
			"status": "Variance Exceeds Threshold" if exceeds_threshold else "Within Threshold",
			"document_totals": document_totals
		}
	
	@frappe.whitelist()
	def get_variance_percentage(self, submitted_balance=None, calculated_balance=None):
		"""Calculate percentage variance between submitted and calculated balance
		
		Args:
			submitted_balance: User-submitted balance (default: total_manual_balance)
			calculated_balance: System-calculated balance (default: from calculate_document_totals)
			
		Returns:
			float: Variance percentage
		"""
		if submitted_balance is None:
			submitted_balance = self.total_manual_balance or 0
		
		if calculated_balance is None:
			document_totals = self.calculate_document_totals()
			calculated_balance = document_totals["net_balance"]
		
		variance_amount = flt(submitted_balance) - flt(calculated_balance)
		
		if calculated_balance != 0:
			variance_percentage = (variance_amount / calculated_balance) * 100
		else:
			variance_percentage = 100 if variance_amount != 0 else 0
		
		return variance_percentage
	
	@frappe.whitelist()
	def get_reconciliation_report(self):
		"""Generate comprehensive reconciliation report
		
		Returns:
			dict: Complete reconciliation data including balances, variances, and document breakdown
		"""
		# Get document totals
		document_totals = self.calculate_document_totals()
		
		# Get variance details
		variance_details = self.check_variance()
		
		# Get related documents
		documents = self.get_related_documents()
		
		# Get role breakdown
		role_breakdown = self.get_role_breakdown()
		
		return {
			"balance_date": self.balance_date,
			"company": self.company if hasattr(self, "company") else None,
			"opening_balance": self.opening_balance if hasattr(self, "opening_balance") else 0,
			"closing_balance": self.closing_balance if hasattr(self, "closing_balance") else 0,
			"document_totals": document_totals,
			"variance_details": variance_details,
			"role_breakdown": role_breakdown,
			"reconciliation_required": variance_details["exceeds_threshold"],
			"status": self.status,
			"verified": self.verified if hasattr(self, "verified") else 0,
			"verified_by": self.verified_by if hasattr(self, "verified_by") else None,
			"verified_at": self.verified_at if hasattr(self, "verified_at") else None,
			"total_documents": len(documents),
			"documents": documents
		}