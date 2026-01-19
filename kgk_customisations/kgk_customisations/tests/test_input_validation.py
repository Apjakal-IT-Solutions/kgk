"""
Input Validation Security Tests
================================

Comprehensive test suite for input validation and sanitization to prevent:
- XSS (Cross-Site Scripting) attacks
- SQL injection attempts
- Path traversal attacks
- Command injection
- Data corruption from invalid inputs

Tests the InputValidator utility and its integration with whitelisted API methods.
"""

import unittest
import frappe
from frappe.test_runner import make_test_records
from kgk_customisations.kgk_customisations.utils.input_validator import InputValidator


class TestInputValidator(unittest.TestCase):
	"""Test InputValidator utility methods"""
	
	@classmethod
	def setUpClass(cls):
		"""Set up test fixtures"""
		cls.validator = InputValidator()
	
	def test_xss_detection_script_tag(self):
		"""Test XSS detection for script tags"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.sanitize_string("<script>alert('XSS')</script>")
	
	def test_xss_detection_javascript_protocol(self):
		"""Test XSS detection for javascript: protocol"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.sanitize_string("javascript:alert('XSS')")
	
	def test_xss_detection_event_handler(self):
		"""Test XSS detection for event handlers"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.sanitize_string("<img src=x onerror=alert('XSS')>")
	
	def test_sql_injection_detection_union(self):
		"""Test SQL injection detection for UNION SELECT"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.check_sql_injection("' UNION SELECT * FROM users--")
	
	def test_sql_injection_detection_or_injection(self):
		"""Test SQL injection detection for OR 1=1"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.check_sql_injection("' OR '1'='1")
	
	def test_sql_injection_detection_drop_table(self):
		"""Test SQL injection detection for DROP TABLE"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.check_sql_injection("'; DROP TABLE users--")
	
	def test_path_traversal_detection_dotdot(self):
		"""Test path traversal detection for ../"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_file_path("../../etc/passwd")
	
	def test_path_traversal_detection_tilde(self):
		"""Test path traversal detection for ~/"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_file_path("~/../../etc/passwd")
	
	def test_path_traversal_detection_absolute(self):
		"""Test path traversal detection for /etc/"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_file_path("/etc/passwd")
	
	def test_valid_string_sanitization(self):
		"""Test sanitization of valid strings"""
		result = self.validator.sanitize_string("Hello, World! 123", max_length=50)
		self.assertEqual(result, "Hello, World! 123")
	
	def test_string_length_truncation(self):
		"""Test string truncation to max_length"""
		long_string = "A" * 1000
		result = self.validator.sanitize_string(long_string, max_length=100)
		self.assertEqual(len(result), 100)
	
	def test_email_validation_valid(self):
		"""Test email validation with valid email"""
		result = self.validator.validate_email("test@example.com")
		self.assertEqual(result, "test@example.com")
	
	def test_email_validation_invalid(self):
		"""Test email validation with invalid email"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_email("not-an-email")
	
	def test_number_validation_valid(self):
		"""Test number validation with valid number"""
		result = self.validator.validate_number("123.45", min_value=0, max_value=1000)
		self.assertEqual(result, 123.45)
	
	def test_number_validation_out_of_range(self):
		"""Test number validation with out-of-range value"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_number("1500", min_value=0, max_value=1000)
	
	def test_integer_validation_valid(self):
		"""Test integer validation with valid integer"""
		result = self.validator.validate_integer("42", min_value=0, max_value=100)
		self.assertEqual(result, 42)
	
	def test_integer_validation_not_integer(self):
		"""Test integer validation with float"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_integer("42.5", min_value=0, max_value=100)
	
	def test_date_validation_valid(self):
		"""Test date validation with valid date"""
		result = self.validator.validate_date("2025-01-15")
		self.assertEqual(str(result), "2025-01-15")
	
	def test_date_validation_invalid(self):
		"""Test date validation with invalid date"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_date("not-a-date")
	
	def test_doctype_name_validation_valid(self):
		"""Test DocType name validation with valid name"""
		result = self.validator.validate_doctype_name("User")
		self.assertEqual(result, "User")
	
	def test_doctype_name_validation_invalid(self):
		"""Test DocType name validation with invalid characters"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_doctype_name("User'; DROP TABLE--")
	
	def test_document_name_validation_exists(self):
		"""Test document name validation for existing document"""
		# Administrator always exists
		result = self.validator.validate_document_name("Administrator", "User")
		self.assertEqual(result, "Administrator")
	
	def test_document_name_validation_not_exists(self):
		"""Test document name validation for non-existent document"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_document_name("NonExistentUser12345", "User")
	
	def test_json_validation_valid(self):
		"""Test JSON validation with valid JSON"""
		json_data = {"key": "value", "number": 42}
		result = self.validator.validate_json(json_data)
		self.assertEqual(result, json_data)
	
	def test_json_validation_required_keys(self):
		"""Test JSON validation with required keys"""
		json_data = {"name": "test", "value": 123}
		result = self.validator.validate_json(json_data, required_keys=["name", "value"])
		self.assertEqual(result, json_data)
	
	def test_json_validation_missing_keys(self):
		"""Test JSON validation with missing required keys"""
		json_data = {"name": "test"}
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_json(json_data, required_keys=["name", "value"])
	
	def test_choice_validation_valid(self):
		"""Test choice validation with valid choice"""
		result = self.validator.validate_choice("option1", ["option1", "option2", "option3"], "field")
		self.assertEqual(result, "option1")
	
	def test_choice_validation_invalid(self):
		"""Test choice validation with invalid choice"""
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_choice("invalid", ["option1", "option2", "option3"], "field")
	
	def test_filters_validation_valid(self):
		"""Test filters validation with valid filters"""
		filters = {
			"status": "Active",
			"creation": [">=", "2025-01-01"]
		}
		result = self.validator.validate_filters(filters)
		self.assertEqual(result, filters)
	
	def test_filters_validation_sql_injection(self):
		"""Test filters validation with SQL injection attempt"""
		filters = {
			"name": "' OR '1'='1"
		}
		with self.assertRaises(frappe.ValidationError):
			self.validator.validate_filters(filters)
	
	def test_filename_sanitization_valid(self):
		"""Test filename sanitization with valid filename"""
		result = self.validator.sanitize_filename("report_2025-01-15.xlsx")
		self.assertEqual(result, "report_2025-01-15.xlsx")
	
	def test_filename_sanitization_path_traversal(self):
		"""Test filename sanitization removes path traversal"""
		result = self.validator.sanitize_filename("../../etc/passwd")
		self.assertEqual(result, "passwd")
	
	def test_filename_sanitization_special_chars(self):
		"""Test filename sanitization removes special characters"""
		result = self.validator.sanitize_filename("file<>:\"|?*.txt")
		self.assertEqual(result, "file.txt")


class TestWhitelistedMethodsValidation(unittest.TestCase):
	"""Test input validation in whitelisted API methods"""
	
	@classmethod
	def setUpClass(cls):
		"""Set up test data"""
		frappe.set_user("Administrator")
	
	def test_bulk_finalize_documents_validates_list(self):
		"""Test bulk_finalize_documents validates document_names is a list"""
		from kgk_customisations.kgk_customisations.doctype.cash_document.cash_document import bulk_finalize_documents
		
		# Should fail with non-list input
		with self.assertRaises(frappe.exceptions.ValidationError):
			bulk_finalize_documents("not-a-list")
	
	def test_bulk_finalize_documents_enforces_limit(self):
		"""Test bulk_finalize_documents enforces 100 document limit"""
		from kgk_customisations.kgk_customisations.doctype.cash_document.cash_document import bulk_finalize_documents
		
		# Create list of 101 documents (exceeds limit)
		doc_list = [f"CD-2025-01-{i:05d}" for i in range(101)]
		
		with self.assertRaises(frappe.exceptions.ValidationError):
			bulk_finalize_documents(doc_list)
	
	def test_bulk_approve_documents_sanitizes_comments(self):
		"""Test bulk_approve_documents sanitizes comments"""
		from kgk_customisations.kgk_customisations.doctype.cash_document.cash_document import bulk_approve_documents
		
		# Should fail with XSS attempt in comments
		with self.assertRaises(frappe.exceptions.ValidationError):
			bulk_approve_documents([], comments="<script>alert('XSS')</script>")
	
	def test_bulk_flag_documents_validates_flag_type(self):
		"""Test bulk_flag_documents validates flag_type"""
		from kgk_customisations.kgk_customisations.doctype.cash_document.cash_document import bulk_flag_documents
		
		# Should fail with invalid flag type
		with self.assertRaises(frappe.exceptions.ValidationError):
			bulk_flag_documents([], flag_type="InvalidType")
	
	def test_process_parcel_import_validates_docname(self):
		"""Test process_parcel_import validates document name"""
		from kgk_customisations.kgk_customisations.doctype.parcel_import.parcel_import import process_parcel_import
		
		# Should fail with SQL injection attempt
		with self.assertRaises(frappe.exceptions.ValidationError):
			process_parcel_import("'; DROP TABLE `tabParcel Import`--")
	
	def test_export_matched_records_validates_filters(self):
		"""Test export_matched_records validates filters JSON"""
		from kgk_customisations.kgk_customisations.report.ocr_parcel_merge.ocr_parcel_merge import export_matched_records
		
		# Should fail with missing required key
		result = export_matched_records({})
		self.assertFalse(result.get("success"))
		self.assertIn("parcel_file", result.get("message", "").lower())
	
	def test_get_statistics_validates_filters(self):
		"""Test get_statistics validates filters JSON"""
		from kgk_customisations.kgk_customisations.report.ocr_parcel_merge.ocr_parcel_merge import get_statistics
		
		# Should fail with missing required key
		with self.assertRaises(frappe.exceptions.ValidationError):
			get_statistics({})


def run_tests():
	"""Run all input validation tests"""
	unittest.main()


if __name__ == "__main__":
	run_tests()
