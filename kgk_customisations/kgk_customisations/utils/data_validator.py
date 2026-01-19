# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Data Validation and Cleanup Utilities
Ensures data quality before import/migration
"""

import frappe
from frappe.utils import getdate, flt, cstr
import re
from datetime import datetime


class DataValidator:
	"""Validate and clean cash management data"""
	
	@staticmethod
	def validate_company(company_name):
		"""
		Validate company exists in system
		
		Args:
			company_name: Company name
			
		Returns:
			tuple: (is_valid, message, cleaned_value)
		"""
		if not company_name:
			return False, "Company is required", None
		
		company_name = cstr(company_name).strip()
		
		if frappe.db.exists("Company", company_name):
			return True, "Valid", company_name
		
		# Try to find similar company
		similar = frappe.db.sql("""
			SELECT name FROM `tabCompany`
			WHERE name LIKE %s OR abbr LIKE %s
			LIMIT 1
		""", (f"%{company_name}%", f"%{company_name}%"))
		
		if similar:
			return False, f"Company not found. Did you mean '{similar[0][0]}'?", similar[0][0]
		
		return False, f"Company '{company_name}' does not exist", None
	
	@staticmethod
	def validate_date(date_value, field_name="Date"):
		"""
		Validate and parse date
		
		Args:
			date_value: Date string or object
			field_name: Field name for error messages
			
		Returns:
			tuple: (is_valid, message, cleaned_date)
		"""
		if not date_value:
			return False, f"{field_name} is required", None
		
		try:
			# Try to parse date
			parsed_date = getdate(date_value)
			
			# Check if date is not in future
			if parsed_date > getdate():
				return False, f"{field_name} cannot be in the future", parsed_date
			
			# Check if date is not too old (e.g., before 2000)
			if parsed_date.year < 2000:
				return False, f"{field_name} seems too old (before 2000)", parsed_date
			
			return True, "Valid", parsed_date
		
		except Exception as e:
			return False, f"Invalid {field_name} format. Use YYYY-MM-DD", None
	
	@staticmethod
	def validate_amount(amount_value):
		"""
		Validate amount is positive number
		
		Args:
			amount_value: Amount value
			
		Returns:
			tuple: (is_valid, message, cleaned_amount)
		"""
		if not amount_value and amount_value != 0:
			return False, "Amount is required", None
		
		try:
			amount = flt(amount_value)
			
			if amount <= 0:
				return False, "Amount must be greater than zero", amount
			
			if amount > 10000000:  # 10 million threshold
				return False, "Amount seems unusually large (> 10M). Please verify", amount
			
			return True, "Valid", amount
		
		except:
			return False, "Amount must be a valid number", None
	
	@staticmethod
	def validate_document_type(doc_type):
		"""
		Validate document type
		
		Args:
			doc_type: Document type
			
		Returns:
			tuple: (is_valid, message, cleaned_type)
		"""
		if not doc_type:
			return False, "Document type is required", None
		
		doc_type = cstr(doc_type).strip()
		
		valid_types = ["Receipt", "Payment", "Invoice", "Petty Cash"]
		
		# Exact match
		if doc_type in valid_types:
			return True, "Valid", doc_type
		
		# Case-insensitive match
		doc_type_lower = doc_type.lower()
		for vt in valid_types:
			if vt.lower() == doc_type_lower:
				return True, "Valid", vt
		
		# Partial match
		for vt in valid_types:
			if doc_type_lower in vt.lower() or vt.lower() in doc_type_lower:
				return False, f"Invalid document type. Did you mean '{vt}'?", vt
		
		return False, f"Invalid document type. Must be one of: {', '.join(valid_types)}", None
	
	@staticmethod
	def validate_phone_number(phone):
		"""
		Validate and clean phone number
		
		Args:
			phone: Phone number
			
		Returns:
			tuple: (is_valid, message, cleaned_phone)
		"""
		if not phone:
			return True, "Optional", None  # Phone is optional
		
		phone = cstr(phone).strip()
		
		# Remove common separators
		cleaned = re.sub(r'[\s\-\(\)]+', '', phone)
		
		# Check if contains only digits and +
		if not re.match(r'^[\d\+]+$', cleaned):
			return False, "Phone number contains invalid characters", cleaned
		
		# Check length (Botswana numbers typically 8 digits, with country code 11-12)
		if len(cleaned) < 8 or len(cleaned) > 15:
			return False, "Phone number length seems incorrect", cleaned
		
		return True, "Valid", cleaned
	
	@staticmethod
	def validate_party(party_type, party_name):
		"""
		Validate party exists in system
		
		Args:
			party_type: Customer, Supplier, Employee
			party_name: Party name/ID
			
		Returns:
			tuple: (is_valid, message, cleaned_party)
		"""
		if not party_type or not party_name:
			return True, "Optional", None  # Party is optional
		
		party_type = cstr(party_type).strip()
		party_name = cstr(party_name).strip()
		
		# Validate party type
		valid_party_types = ["Customer", "Supplier", "Employee"]
		if party_type not in valid_party_types:
			return False, f"Invalid party type. Must be one of: {', '.join(valid_party_types)}", None
		
		# Check if party exists
		if frappe.db.exists(party_type, party_name):
			return True, "Valid", party_name
		
		# Try to find similar party - using safe parameterized query
		# Party type is validated against whitelist above, safe to use in table name
		similar = frappe.db.sql(
			f"""SELECT name FROM `tab{party_type}` WHERE name LIKE %(pattern)s LIMIT 1""",
			{"pattern": f"%{party_name}%"},
			as_dict=False
		)
		
		if similar:
			return False, f"{party_type} not found. Did you mean '{similar[0][0]}'?", similar[0][0]
		
		return False, f"{party_type} '{party_name}' does not exist", None
	
	@staticmethod
	def clean_text(text, max_length=None):
		"""
		Clean and sanitize text field
		
		Args:
			text: Text to clean
			max_length: Maximum length
			
		Returns:
			str: Cleaned text
		"""
		if not text:
			return ""
		
		text = cstr(text).strip()
		
		# Remove excessive whitespace
		text = re.sub(r'\s+', ' ', text)
		
		# Truncate if needed
		if max_length and len(text) > max_length:
			text = text[:max_length]
		
		return text
	
	@staticmethod
	def validate_record(record_dict):
		"""
		Validate entire record
		
		Args:
			record_dict: Dictionary with record data
			
		Returns:
			dict: Validation results with errors and warnings
		"""
		results = {
			"is_valid": True,
			"errors": [],
			"warnings": [],
			"cleaned_data": {}
		}
		
		# Validate company
		is_valid, msg, cleaned = DataValidator.validate_company(record_dict.get("company"))
		if not is_valid:
			results["is_valid"] = False
			results["errors"].append(msg)
		else:
			results["cleaned_data"]["company"] = cleaned
		
		# Validate transaction date
		is_valid, msg, cleaned = DataValidator.validate_date(
			record_dict.get("transaction_date"),
			"Transaction Date"
		)
		if not is_valid:
			results["is_valid"] = False
			results["errors"].append(msg)
		else:
			results["cleaned_data"]["transaction_date"] = cleaned
		
		# Validate amount
		is_valid, msg, cleaned = DataValidator.validate_amount(record_dict.get("amount"))
		if not is_valid:
			results["is_valid"] = False
			results["errors"].append(msg)
		else:
			results["cleaned_data"]["amount"] = cleaned
			if cleaned > 100000:
				results["warnings"].append(f"Large amount: {cleaned}")
		
		# Validate document type
		is_valid, msg, cleaned = DataValidator.validate_document_type(
			record_dict.get("main_document_type")
		)
		if not is_valid:
			results["is_valid"] = False
			results["errors"].append(msg)
		else:
			results["cleaned_data"]["main_document_type"] = cleaned
		
		# Validate phone number
		is_valid, msg, cleaned = DataValidator.validate_phone_number(
			record_dict.get("contact_number")
		)
		if not is_valid:
			results["warnings"].append(msg)
		else:
			results["cleaned_data"]["contact_number"] = cleaned
		
		# Validate party
		is_valid, msg, cleaned = DataValidator.validate_party(
			record_dict.get("party_type"),
			record_dict.get("party")
		)
		if not is_valid:
			results["warnings"].append(msg)
		else:
			results["cleaned_data"]["party"] = cleaned
		
		# Clean text fields
		for field in ["description", "sub_document_type"]:
			if record_dict.get(field):
				results["cleaned_data"][field] = DataValidator.clean_text(
					record_dict[field],
					max_length=500
				)
		
		return results


@frappe.whitelist()
def validate_import_data(data):
	"""
	API endpoint to validate import data
	
	Args:
		data: List of dictionaries or single dictionary
		
	Returns:
		dict: Validation summary
	"""
	if isinstance(data, str):
		import json
		data = json.loads(data)
	
	if not isinstance(data, list):
		data = [data]
	
	summary = {
		"total": len(data),
		"valid": 0,
		"invalid": 0,
		"warnings": 0,
		"details": []
	}
	
	for idx, record in enumerate(data, 1):
		result = DataValidator.validate_record(record)
		
		if result["is_valid"]:
			summary["valid"] += 1
		else:
			summary["invalid"] += 1
		
		if result["warnings"]:
			summary["warnings"] += len(result["warnings"])
		
		summary["details"].append({
			"row": idx,
			"is_valid": result["is_valid"],
			"errors": result["errors"],
			"warnings": result["warnings"]
		})
	
	return summary
