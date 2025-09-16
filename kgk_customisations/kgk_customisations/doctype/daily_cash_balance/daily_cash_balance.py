# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt

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