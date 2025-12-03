# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Bulk Import Utilities for Cash Documents
Supports CSV/Excel import with validation
"""

import frappe
from frappe.utils import getdate, flt, cstr
import pandas as pd
from datetime import datetime
import os


class CashDocumentBulkImport:
	"""Handle bulk import of Cash Documents from CSV/Excel"""
	
	def __init__(self):
		self.errors = []
		self.warnings = []
		self.success_count = 0
		self.failed_count = 0
	
	@staticmethod
	def get_import_template():
		"""
		Generate CSV import template
		
		Returns:
			str: CSV template content
		"""
		headers = [
			"Company",
			"Transaction Date (YYYY-MM-DD)",
			"Main Document Type",
			"Sub Document Type",
			"Amount",
			"Currency",
			"Description",
			"Party Type",
			"Party",
			"Contact Person",
			"Contact Number",
			"Primary Document File",
			"Invoice Number (optional)",
			"Status (optional)"
		]
		
		sample_data = [
			[
				"KGK",
				"2025-01-15",
				"Receipt",
				"Customer Payment",
				"5000.00",
				"BWP",
				"Payment received from customer",
				"Customer",
				"CUST-001",
				"John Doe",
				"73123456",
				"receipt_001.pdf",
				"INV-2025-001",
				"Draft"
			],
			[
				"KGK",
				"2025-01-15",
				"Payment",
				"Supplier Payment",
				"3000.00",
				"BWP",
				"Payment to supplier",
				"Supplier",
				"SUPP-001",
				"Jane Smith",
				"72987654",
				"payment_001.pdf",
				"",
				"Pending Review"
			]
		]
		
		# Create DataFrame
		df = pd.DataFrame(sample_data, columns=headers)
		return df.to_csv(index=False)
	
	def validate_row(self, row_data, row_num):
		"""
		Validate a single row of import data
		
		Args:
			row_data: Dictionary of row data
			row_num: Row number for error reporting
			
		Returns:
			tuple: (is_valid, errors)
		"""
		errors = []
		
		# Required fields
		required_fields = ["Company", "Transaction Date (YYYY-MM-DD)", "Main Document Type", "Amount"]
		
		for field in required_fields:
			if field not in row_data or not row_data[field]:
				errors.append(f"Row {row_num}: Missing required field '{field}'")
		
		# Validate company exists
		if row_data.get("Company") and not frappe.db.exists("Company", row_data["Company"]):
			errors.append(f"Row {row_num}: Company '{row_data['Company']}' does not exist")
		
		# Validate date format
		try:
			if row_data.get("Transaction Date (YYYY-MM-DD)"):
				getdate(row_data["Transaction Date (YYYY-MM-DD)"])
		except:
			errors.append(f"Row {row_num}: Invalid date format. Use YYYY-MM-DD")
		
		# Validate amount is numeric
		try:
			if row_data.get("Amount"):
				float(row_data["Amount"])
		except:
			errors.append(f"Row {row_num}: Amount must be a valid number")
		
		# Validate main document type
		valid_types = ["Receipt", "Payment", "Invoice", "Petty Cash"]
		if row_data.get("Main Document Type") and row_data["Main Document Type"] not in valid_types:
			errors.append(f"Row {row_num}: Invalid Main Document Type. Must be one of: {', '.join(valid_types)}")
		
		# Validate party type if provided
		if row_data.get("Party Type"):
			valid_party_types = ["Customer", "Supplier", "Employee"]
			if row_data["Party Type"] not in valid_party_types:
				errors.append(f"Row {row_num}: Invalid Party Type. Must be one of: {', '.join(valid_party_types)}")
		
		return len(errors) == 0, errors
	
	def import_from_dataframe(self, df, validate_only=False):
		"""
		Import cash documents from pandas DataFrame
		
		Args:
			df: pandas DataFrame with cash document data
			validate_only: If True, only validate without importing
			
		Returns:
			dict: Import results
		"""
		results = {
			"total": len(df),
			"success": 0,
			"failed": 0,
			"errors": [],
			"warnings": [],
			"imported_docs": []
		}
		
		for idx, row in df.iterrows():
			row_num = idx + 2  # Excel row number (1-indexed + header row)
			
			try:
				# Convert row to dict
				row_data = row.to_dict()
				
				# Validate row
				is_valid, errors = self.validate_row(row_data, row_num)
				
				if not is_valid:
					results["failed"] += 1
					results["errors"].extend(errors)
					continue
				
				if validate_only:
					results["success"] += 1
					continue
				
				# Create Cash Document
				doc = frappe.get_doc({
					"doctype": "Cash Document",
					"company": row_data["Company"],
					"transaction_date": getdate(row_data["Transaction Date (YYYY-MM-DD)"]),
					"main_document_type": row_data["Main Document Type"],
					"sub_document_type": row_data.get("Sub Document Type", ""),
					"amount": flt(row_data["Amount"]),
					"currency": row_data.get("Currency", "BWP"),
					"description": row_data.get("Description", ""),
					"party_type": row_data.get("Party Type", ""),
					"party": row_data.get("Party", ""),
					"contact_person": row_data.get("Contact Person", ""),
					"contact_number": row_data.get("Contact Number", ""),
					"primary_document_file": row_data.get("Primary Document File", ""),
					"invoice_number": row_data.get("Invoice Number (optional)", ""),
					"status": row_data.get("Status (optional)", "Draft")
				})
				
				doc.insert(ignore_permissions=True)
				results["success"] += 1
				results["imported_docs"].append(doc.name)
				
				# Commit every 100 records
				if results["success"] % 100 == 0:
					frappe.db.commit()
			
			except Exception as e:
				results["failed"] += 1
				results["errors"].append(f"Row {row_num}: {str(e)}")
		
		# Final commit
		if not validate_only:
			frappe.db.commit()
		
		return results
	
	def import_from_file(self, filepath, validate_only=False):
		"""
		Import from CSV or Excel file
		
		Args:
			filepath: Path to CSV or Excel file
			validate_only: If True, only validate
			
		Returns:
			dict: Import results
		"""
		file_ext = os.path.splitext(filepath)[1].lower()
		
		try:
			if file_ext == '.csv':
				df = pd.read_csv(filepath)
			elif file_ext in ['.xlsx', '.xls']:
				df = pd.read_excel(filepath)
			else:
				return {
					"total": 0,
					"success": 0,
					"failed": 0,
					"errors": ["Unsupported file format. Use CSV or Excel (.xlsx, .xls)"]
				}
			
			return self.import_from_dataframe(df, validate_only)
		
		except Exception as e:
			return {
				"total": 0,
				"success": 0,
				"failed": 0,
				"errors": [f"Failed to read file: {str(e)}"]
			}


@frappe.whitelist()
def download_import_template():
	"""Generate and download import template"""
	template = CashDocumentBulkImport.get_import_template()
	
	frappe.response['filename'] = 'cash_document_import_template.csv'
	frappe.response['filecontent'] = template
	frappe.response['type'] = 'csv'


@frappe.whitelist()
def validate_import_file(file_url):
	"""
	Validate import file without importing
	
	Args:
		file_url: URL of uploaded file
		
	Returns:
		dict: Validation results
	"""
	try:
		# Get file from frappe
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		filepath = file_doc.get_full_path()
		
		importer = CashDocumentBulkImport()
		results = importer.import_from_file(filepath, validate_only=True)
		
		return results
	
	except Exception as e:
		return {
			"total": 0,
			"success": 0,
			"failed": 0,
			"errors": [str(e)]
		}


@frappe.whitelist()
def import_cash_documents(file_url):
	"""
	Import cash documents from file
	
	Args:
		file_url: URL of uploaded file
		
	Returns:
		dict: Import results
	"""
	try:
		# Get file from frappe
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		filepath = file_doc.get_full_path()
		
		importer = CashDocumentBulkImport()
		results = importer.import_from_file(filepath, validate_only=False)
		
		return results
	
	except Exception as e:
		frappe.log_error(f"Bulk import failed: {str(e)}", "Cash Document Import Error")
		return {
			"total": 0,
			"success": 0,
			"failed": 0,
			"errors": [str(e)]
		}
