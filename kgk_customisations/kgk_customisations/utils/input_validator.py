# Copyright (c) 2026, KGK and contributors
# For license information, please see license.txt

"""
Input Validation Utilities
Provides comprehensive input validation and sanitization for API endpoints
"""

import frappe
from frappe import _
import re
import os
import json
from datetime import datetime
from frappe.utils import cstr, flt, cint, getdate


class InputValidator:
	"""Centralized input validation for API endpoints and user inputs"""
	
	# Dangerous patterns for XSS/injection
	DANGEROUS_PATTERNS = [
		r'<script[^>]*>.*?</script>',  # Script tags
		r'javascript:',  # JavaScript protocol
		r'on\w+\s*=',  # Event handlers (onclick, onload, etc.)
		r'<iframe[^>]*>',  # iframes
		r'<object[^>]*>',  # object tags
		r'<embed[^>]*>',  # embed tags
		r'eval\s*\(',  # eval calls
		r'expression\s*\(',  # CSS expressions
	]
	
	# SQL injection patterns
	SQL_INJECTION_PATTERNS = [
		r"(\bunion\b.*\bselect\b)",
		r"(\bor\b.*=.*)",
		r"(\band\b.*=.*)",
		r"(;.*drop\b)",
		r"(;.*delete\b)",
		r"(;.*update\b)",
		r"(;.*insert\b)",
		r"(--)",
		r"(/\*.*\*/)",
	]
	
	# Path traversal patterns
	PATH_TRAVERSAL_PATTERNS = [
		r'\.\.',  # Parent directory
		r'~/',  # Home directory
		r'/etc/',  # System directories
		r'/proc/',
		r'/sys/',
		r'\\\\',  # Windows UNC paths
	]
	
	@staticmethod
	def validate_required(value, field_name):
		"""
		Validate that a required field has a value
		
		Args:
			value: Value to validate
			field_name: Name of the field
			
		Returns:
			value: The validated value
			
		Raises:
			frappe.ValidationError: If value is missing
		"""
		if value is None or (isinstance(value, str) and not value.strip()):
			frappe.throw(_("{0} is required").format(field_name), frappe.ValidationError)
		return value
	
	@staticmethod
	def sanitize_string(value, max_length=None, allow_html=False):
		"""
		Sanitize string input
		
		Args:
			value: String to sanitize
			max_length: Maximum allowed length
			allow_html: Allow HTML tags (will still sanitize dangerous patterns)
			
		Returns:
			str: Sanitized string
		"""
		if not value:
			return ""
		
		value = cstr(value)
		
		# Check for XSS patterns
		if not allow_html:
			for pattern in InputValidator.DANGEROUS_PATTERNS:
				if re.search(pattern, value, re.IGNORECASE):
					frappe.throw(
						_("Invalid input detected. HTML/JavaScript not allowed."),
						frappe.ValidationError
					)
		
		# Remove null bytes
		value = value.replace('\x00', '')
		
		# Truncate if needed
		if max_length and len(value) > max_length:
			frappe.throw(
				_("Input exceeds maximum length of {0} characters").format(max_length),
				frappe.ValidationError
			)
		
		return value.strip()
	
	@staticmethod
	def validate_email(email):
		"""
		Validate email format
		
		Args:
			email: Email to validate
			
		Returns:
			str: Validated email
		"""
		if not email:
			return ""
		
		email = cstr(email).strip()
		
		# Basic email regex
		email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
		
		if not re.match(email_pattern, email):
			frappe.throw(_("Invalid email format: {0}").format(email), frappe.ValidationError)
		
		return email
	
	@staticmethod
	def validate_number(value, field_name, min_value=None, max_value=None, allow_negative=True):
		"""
		Validate numeric input
		
		Args:
			value: Value to validate
			field_name: Name of the field
			min_value: Minimum allowed value
			max_value: Maximum allowed value
			allow_negative: Allow negative numbers
			
		Returns:
			float: Validated number
		"""
		try:
			num = flt(value)
		except:
			frappe.throw(
				_("{0} must be a valid number").format(field_name),
				frappe.ValidationError
			)
		
		if not allow_negative and num < 0:
			frappe.throw(
				_("{0} cannot be negative").format(field_name),
				frappe.ValidationError
			)
		
		if min_value is not None and num < min_value:
			frappe.throw(
				_("{0} cannot be less than {1}").format(field_name, min_value),
				frappe.ValidationError
			)
		
		if max_value is not None and num > max_value:
			frappe.throw(
				_("{0} cannot be greater than {1}").format(field_name, max_value),
				frappe.ValidationError
			)
		
		return num
	
	@staticmethod
	def validate_integer(value, field_name, min_value=None, max_value=None):
		"""
		Validate integer input
		
		Args:
			value: Value to validate
			field_name: Name of the field
			min_value: Minimum allowed value
			max_value: Maximum allowed value
			
		Returns:
			int: Validated integer
		"""
		try:
			num = cint(value)
		except:
			frappe.throw(
				_("{0} must be a valid integer").format(field_name),
				frappe.ValidationError
			)
		
		if min_value is not None and num < min_value:
			frappe.throw(
				_("{0} cannot be less than {1}").format(field_name, min_value),
				frappe.ValidationError
			)
		
		if max_value is not None and num > max_value:
			frappe.throw(
				_("{0} cannot be greater than {1}").format(field_name, max_value),
				frappe.ValidationError
			)
		
		return num
	
	@staticmethod
	def validate_date(value, field_name, allow_future=True, allow_past=True):
		"""
		Validate date input
		
		Args:
			value: Date string to validate
			field_name: Name of the field
			allow_future: Allow future dates
			allow_past: Allow past dates
			
		Returns:
			date: Validated date object
		"""
		if not value:
			return None
		
		try:
			date = getdate(value)
		except:
			frappe.throw(
				_("{0} must be a valid date").format(field_name),
				frappe.ValidationError
			)
		
		today = getdate()
		
		if not allow_future and date > today:
			frappe.throw(
				_("{0} cannot be a future date").format(field_name),
				frappe.ValidationError
			)
		
		if not allow_past and date < today:
			frappe.throw(
				_("{0} cannot be a past date").format(field_name),
				frappe.ValidationError
			)
		
		return date
	
	@staticmethod
	def validate_file_path(file_path, allowed_extensions=None, max_size_mb=None):
		"""
		Validate file path for security
		
		Args:
			file_path: File path to validate
			allowed_extensions: List of allowed file extensions
			max_size_mb: Maximum file size in MB
			
		Returns:
			str: Validated file path
		"""
		if not file_path:
			frappe.throw(_("File path is required"), frappe.ValidationError)
		
		file_path = cstr(file_path)
		
		# Check for path traversal
		for pattern in InputValidator.PATH_TRAVERSAL_PATTERNS:
			if re.search(pattern, file_path, re.IGNORECASE):
				frappe.throw(
					_("Invalid file path. Path traversal detected."),
					frappe.SecurityException
				)
		
		# Check file extension
		if allowed_extensions:
			ext = os.path.splitext(file_path)[1].lower()
			if ext not in [e.lower() if e.startswith('.') else f'.{e.lower()}' for e in allowed_extensions]:
				frappe.throw(
					_("File type not allowed. Allowed types: {0}").format(", ".join(allowed_extensions)),
					frappe.ValidationError
				)
		
		# Check file size if path exists
		if max_size_mb and os.path.exists(file_path):
			size_mb = os.path.getsize(file_path) / (1024 * 1024)
			if size_mb > max_size_mb:
				frappe.throw(
					_("File size exceeds maximum allowed size of {0} MB").format(max_size_mb),
					frappe.ValidationError
				)
		
		return file_path
	
	@staticmethod
	def validate_doctype_name(doctype):
		"""
		Validate DocType name exists
		
		Args:
			doctype: DocType name to validate
			
		Returns:
			str: Validated DocType name
		"""
		if not doctype:
			frappe.throw(_("DocType is required"), frappe.ValidationError)
		
		doctype = cstr(doctype).strip()
		
		# Check if doctype exists
		if not frappe.db.exists("DocType", doctype):
			frappe.throw(
				_("DocType {0} does not exist").format(doctype),
				frappe.ValidationError
			)
		
		return doctype
	
	@staticmethod
	def validate_document_name(doctype, name):
		"""
		Validate that a document exists
		
		Args:
			doctype: DocType name
			name: Document name
			
		Returns:
			str: Validated document name
		"""
		doctype = InputValidator.validate_doctype_name(doctype)
		
		if not name:
			frappe.throw(_("Document name is required"), frappe.ValidationError)
		
		name = cstr(name).strip()
		
		if not frappe.db.exists(doctype, name):
			frappe.throw(
				_("{0} {1} does not exist").format(doctype, name),
				frappe.DoesNotExistError
			)
		
		return name
	
	@staticmethod
	def validate_json(value, field_name):
		"""
		Validate and parse JSON input
		
		Args:
			value: JSON string to validate
			field_name: Name of the field
			
		Returns:
			dict/list: Parsed JSON
		"""
		if not value:
			return {}
		
		if isinstance(value, (dict, list)):
			return value
		
		try:
			return json.loads(value)
		except json.JSONDecodeError as e:
			frappe.throw(
				_("{0} must be valid JSON: {1}").format(field_name, str(e)),
				frappe.ValidationError
			)
	
	@staticmethod
	def validate_choice(value, field_name, choices):
		"""
		Validate value is in allowed choices
		
		Args:
			value: Value to validate
			field_name: Name of the field
			choices: List of allowed choices
			
		Returns:
			value: Validated value
		"""
		if not value:
			return None
		
		value = cstr(value)
		
		if value not in choices:
			frappe.throw(
				_("{0} must be one of: {1}").format(field_name, ", ".join(choices)),
				frappe.ValidationError
			)
		
		return value
	
	@staticmethod
	def check_sql_injection(value, field_name):
		"""
		Check for SQL injection patterns
		
		Args:
			value: Value to check
			field_name: Name of the field
			
		Returns:
			str: Validated value
		"""
		if not value:
			return ""
		
		value = cstr(value)
		
		# Check for SQL injection patterns
		for pattern in InputValidator.SQL_INJECTION_PATTERNS:
			if re.search(pattern, value, re.IGNORECASE):
				frappe.log_error(
					f"SQL injection attempt detected in {field_name}: {value}",
					"Security Alert"
				)
				frappe.throw(
					_("Invalid input detected in {0}").format(field_name),
					frappe.SecurityException
				)
		
		return value
	
	@staticmethod
	def validate_filters(filters):
		"""
		Validate filter object for queries
		
		Args:
			filters: Filter dict/list to validate
			
		Returns:
			dict: Validated filters
		"""
		if not filters:
			return {}
		
		# Parse if JSON string
		if isinstance(filters, str):
			filters = InputValidator.validate_json(filters, "filters")
		
		# Convert list to dict if needed
		if isinstance(filters, list):
			filter_dict = {}
			for f in filters:
				if isinstance(f, (list, tuple)) and len(f) >= 2:
					filter_dict[f[0]] = f[-1]
			filters = filter_dict
		
		# Validate each filter value
		if isinstance(filters, dict):
			for key, value in filters.items():
				# Check field name for SQL injection
				InputValidator.check_sql_injection(str(key), "filter field")
				
				# Check value for SQL injection if string
				if isinstance(value, str):
					InputValidator.check_sql_injection(value, f"filter value for {key}")
		
		return filters
	
	@staticmethod
	def sanitize_filename(filename):
		"""
		Sanitize filename to prevent path traversal
		
		Args:
			filename: Filename to sanitize
			
		Returns:
			str: Sanitized filename
		"""
		if not filename:
			return ""
		
		filename = cstr(filename)
		
		# Remove path components
		filename = os.path.basename(filename)
		
		# Remove dangerous characters
		filename = re.sub(r'[^\w\s.-]', '', filename)
		
		# Remove leading/trailing dots and spaces
		filename = filename.strip('. ')
		
		if not filename:
			frappe.throw(_("Invalid filename"), frappe.ValidationError)
		
		return filename


def validate_api_input(**validators):
	"""
	Decorator for validating API inputs
	
	Usage:
		@frappe.whitelist()
		@validate_api_input(
			name=("required", "string"),
			amount=("required", "number", {"min_value": 0}),
			date=("required", "date")
		)
		def my_api_method(name, amount, date):
			...
	"""
	def decorator(func):
		def wrapper(*args, **kwargs):
			validated_kwargs = {}
			
			for param, rules in validators.items():
				value = kwargs.get(param)
				
				if not isinstance(rules, (list, tuple)):
					rules = [rules]
				
				# Check required
				if "required" in rules:
					InputValidator.validate_required(value, param)
				
				# Validate by type
				if "string" in rules:
					validated_kwargs[param] = InputValidator.sanitize_string(value)
				elif "number" in rules:
					validated_kwargs[param] = InputValidator.validate_number(value, param)
				elif "integer" in rules:
					validated_kwargs[param] = InputValidator.validate_integer(value, param)
				elif "date" in rules:
					validated_kwargs[param] = InputValidator.validate_date(value, param)
				elif "email" in rules:
					validated_kwargs[param] = InputValidator.validate_email(value)
				elif "json" in rules:
					validated_kwargs[param] = InputValidator.validate_json(value, param)
				else:
					validated_kwargs[param] = value
			
			# Update kwargs with validated values
			kwargs.update(validated_kwargs)
			
			return func(*args, **kwargs)
		
		return wrapper
	return decorator
