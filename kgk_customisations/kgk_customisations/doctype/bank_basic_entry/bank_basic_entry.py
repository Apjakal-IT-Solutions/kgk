# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt, now_datetime


class BankBasicEntry(Document):
	def before_insert(self):
		"""Set audit information when document is created"""
		self.entered_by = frappe.session.user
	
	def validate(self):
		"""Validate document data"""
		# Ensure entry date is not in future
		if self.entry_date and getdate(self.entry_date) > getdate():
			frappe.throw("Entry date cannot be in the future")
		
		# Validate balance is positive
		if flt(self.balance) < 0:
			frappe.throw("Balance cannot be negative")
	
	@frappe.whitelist()
	def verify_entry(self):
		"""Verify the bank entry"""
		if self.verified:
			frappe.throw("Entry is already verified")
		
		self.verified = 1
		self.verified_by = frappe.session.user
		self.verified_at = now_datetime()
		self.save()
		
		frappe.msgprint("Bank entry verified successfully")
	
	@frappe.whitelist()
	def unverify_entry(self):
		"""Unverify the bank entry (requires permissions)"""
		if not self.verified:
			frappe.throw("Entry is not verified")
		
		self.verified = 0
		self.verified_by = None
		self.verified_at = None
		self.save()
		
		frappe.msgprint("Bank entry unverified")
	
	@staticmethod
	def get_totals_by_date(entry_date, company=None):
		"""Get total bank balances for a specific date
		
		Args:
			entry_date: Date to get totals for
			company: Optional company filter
			
		Returns:
			dict: Dictionary with company totals
		"""
		filters = {
			"entry_date": entry_date,
			"verified": 1  # Only include verified entries
		}
		
		if company:
			filters["company"] = company
		
		# Get all verified entries for the date
		entries = frappe.get_all(
			"Bank Basic Entry",
			filters=filters,
			fields=["company", "balance"]
		)
		
		# Sum by company
		totals = {}
		for entry in entries:
			company_name = entry.company
			if company_name not in totals:
				totals[company_name] = 0
			totals[company_name] += flt(entry.balance)
		
		return totals
	
	@staticmethod
	def get_balance_by_user(entry_date, company, username):
		"""Get bank balance for specific date, company, and username
		
		Args:
			entry_date: Date to query
			company: Company name
			username: Username/identifier
			
		Returns:
			float: Balance amount or None if not found
		"""
		entry = frappe.get_all(
			"Bank Basic Entry",
			filters={
				"entry_date": entry_date,
				"company": company,
				"username": username
			},
			fields=["balance"],
			limit=1
		)
		
		return entry[0].balance if entry else None
	
	@staticmethod
	def set_bank_balance(entry_date, company, username, balance):
		"""Create or update bank basic balance entry
		
		Args:
			entry_date: Entry date
			company: Company name
			username: Username/identifier
			balance: Balance amount
			
		Returns:
			str: Name of created/updated document
		"""
		# Check if entry exists
		existing = frappe.get_all(
			"Bank Basic Entry",
			filters={
				"entry_date": entry_date,
				"company": company,
				"username": username
			},
			limit=1
		)
		
		if existing:
			# Update existing entry
			doc = frappe.get_doc("Bank Basic Entry", existing[0].name)
			doc.balance = balance
			# Save with permission check - system operation
			PermissionManager.save_with_permission_check(doc, ignore_for_system=True)
			return doc.name
		else:
			# Create new entry
			doc = frappe.get_doc({
				"doctype": "Bank Basic Entry",
				"entry_date": entry_date,
				"company": company,
				"username": username,
				"balance": balance
			})
			# Insert with permission check - system operation
			PermissionManager.insert_with_permission_check(doc, ignore_for_system=True)
			return doc.name
	
	@staticmethod
	def integrate_with_daily_balance(entry_date):
		"""Integrate bank entries with Daily Cash Balance
		
		Args:
			entry_date: Date to integrate for
			
		Returns:
			dict: Integration results
		"""
		# Get bank totals for the date
		totals = BankBasicEntry.get_totals_by_date(entry_date)
		
		results = {
			"date": entry_date,
			"totals": totals,
			"updated_balances": []
		}
		
		# Update or create Daily Cash Balance entries for each company
		for company, total in totals.items():
			# Find or create Daily Cash Balance
			balance_name = frappe.db.exists(
				"Daily Cash Balance",
				{
					"balance_date": entry_date,
					"company": company
				}
			)
			
			if balance_name:
				balance_doc = frappe.get_doc("Daily Cash Balance", balance_name)
			else:
				balance_doc = frappe.get_doc({
					"doctype": "Daily Cash Balance",
					"balance_date": entry_date,
					"company": company
				})
			
			# Update bank-related fields if they exist
			if hasattr(balance_doc, "bank_balance"):
				balance_doc.bank_balance = total
			
			# Save with permission check - system operation (bank integration)
			PermissionManager.save_with_permission_check(balance_doc, ignore_for_system=True)
			results["updated_balances"].append({
				"company": company,
				"balance": balance_name or balance_doc.name,
				"bank_total": total
			})
		
		frappe.db.commit()
		return results
