# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime, getdate
import time

class InvoiceNumberSeries(Document):
	def validate(self):
		"""Validate Invoice Number Series"""
		# Ensure padding is reasonable
		if self.padding < 1 or self.padding > 10:
			frappe.throw("Padding must be between 1 and 10")
		
		# Ensure current_number is positive
		if self.current_number < 1:
			frappe.throw("Current Number must be at least 1")
		
		# Check for duplicate series for same document_type and company
		existing = frappe.db.exists(
			"Invoice Number Series",
			{
				"document_type": self.document_type,
				"company": self.company,
				"is_active": 1,
				"name": ["!=", self.name]
			}
		)
		if existing:
			frappe.throw(f"Active Invoice Number Series already exists for {self.document_type} in company {self.company}")
	
	@frappe.whitelist()
	def get_next_number(self, year=None):
		"""
		Get the next invoice number in the series with atomic increment.
		Uses database-level locking to prevent duplicate numbers.
		
		Args:
			year: Optional year for year-based numbering
		
		Returns:
			str: The next invoice number (e.g., 'INV-2024-00001')
		"""
		# Retry logic to handle concurrent requests
		max_retries = 5
		retry_count = 0
		
		while retry_count < max_retries:
			try:
				# Start a database transaction with FOR UPDATE lock
				frappe.db.sql("""
					SELECT current_number 
					FROM `tabInvoice Number Series` 
					WHERE name = %s 
					FOR UPDATE
				""", (self.name,))
				
				# Check if year-based and reset is needed
				if self.year_based and self.reset_on_year_change and year:
					last_year = None
					if self.last_generated_on:
						last_year = get_datetime(self.last_generated_on).year
					
					if last_year and last_year != year:
						# Reset counter for new year
						self.current_number = 1
				
				# Get the next number
				next_num = self.current_number
				
				# Generate the formatted invoice number
				if self.year_based and year:
					invoice_number = f"{self.prefix}-{year}-{str(next_num).zfill(self.padding)}"
				else:
					invoice_number = f"{self.prefix}-{str(next_num).zfill(self.padding)}"
				
				# Increment for next time (atomic operation)
				frappe.db.sql("""
					UPDATE `tabInvoice Number Series` 
					SET current_number = current_number + 1,
						last_generated = %s,
						last_generated_on = %s,
						modified = %s,
						modified_by = %s
					WHERE name = %s
				""", (invoice_number, now(), now(), frappe.session.user, self.name))
				
				# Commit the transaction
				frappe.db.commit()
				
				# Reload to get updated values
				self.reload()
				
				return invoice_number
				
			except Exception as e:
				frappe.db.rollback()
				retry_count += 1
				if retry_count >= max_retries:
					frappe.log_error(f"Failed to generate invoice number after {max_retries} retries: {str(e)}", "Invoice Number Generation Error")
					frappe.throw(f"Unable to generate invoice number. Please try again. Error: {str(e)}")
				
				# Wait before retrying (exponential backoff)
				time.sleep(0.1 * (2 ** retry_count))
		
		frappe.throw("Failed to generate invoice number after multiple retries")
	
	@staticmethod
	def generate_invoice_number(document_type, company, year=None):
		"""
		Static method to generate invoice number for a given document type and company.
		
		Args:
			document_type: Type of document (Payment, Receipt, Invoice, etc.)
			company: Company name
			year: Optional year for year-based numbering
		
		Returns:
			str: Generated invoice number
		"""
		# Find active series for this document type and company
		series = frappe.get_all(
			"Invoice Number Series",
			filters={
				"document_type": document_type,
				"company": company,
				"is_active": 1
			},
			limit=1
		)
		
		if not series:
			# Try to create default series if it doesn't exist
			default_prefix = get_default_prefix(document_type)
			series_doc = frappe.get_doc({
				"doctype": "Invoice Number Series",
				"document_type": document_type,
				"company": company,
				"prefix": default_prefix,
				"current_number": 1,
				"padding": 5,
				"year_based": 1,
				"reset_on_year_change": 1,
				"is_active": 1
			})
			series_doc.insert(ignore_permissions=True)
			frappe.db.commit()
			series_name = series_doc.name
		else:
			series_name = series[0].name
		
		# Get the series document and generate next number
		series_doc = frappe.get_doc("Invoice Number Series", series_name)
		return series_doc.get_next_number(year)


def get_default_prefix(document_type):
	"""Get default prefix for a document type"""
	prefix_map = {
		"Payment": "PAY",
		"Receipt": "REC",
		"Invoice": "INV",
		"Credit Note": "CN",
		"Debit Note": "DN",
		"Journal Entry": "JE",
		"Petty Cash": "PC"
	}
	return prefix_map.get(document_type, "DOC")
