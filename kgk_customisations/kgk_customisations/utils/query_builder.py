# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

"""
Safe SQL Query Builder Utilities
=================================

Prevents SQL injection by using parameterized queries exclusively.
All database queries should use this utility instead of string formatting.

Security: This module implements defense against SQL injection attacks by:
1. Using parameterized queries with %(param)s placeholders
2. Never concatenating user input into SQL strings
3. Validating and sanitizing filter values
4. Providing safe query building patterns

Author: Security Remediation Team
Date: January 19, 2026
"""

import frappe
from typing import Dict, List, Any, Optional, Tuple, Union
from frappe.utils import cstr, flt, cint, getdate
import re


class SafeQueryBuilder:
	"""
	Build SQL queries safely with parameter binding to prevent SQL injection.
	
	Example:
		>>> builder = SafeQueryBuilder()
		>>> where, params = builder.build_where_clause(
		...     filters={'from_date': '2026-01-01', 'company': 'Test Co'},
		...     field_mapping={'from_date': 'sp.prediction_date', 'company': 'sp.company'}
		... )
		>>> query = f"SELECT * FROM `tabStone Prediction` sp WHERE {where}"
		>>> results = builder.execute_safe_query(query, params)
	"""
	
	@staticmethod
	def build_where_clause(filters: Dict[str, Any], 
	                       field_mapping: Dict[str, str],
	                       allow_wildcards: bool = False) -> Tuple[str, Dict[str, Any]]:
		"""
		Build WHERE clause from filters safely using parameterized queries.
		
		Args:
			filters: Dictionary of filter field -> value
			field_mapping: Dictionary mapping filter keys to SQL field names
			allow_wildcards: Whether to allow LIKE queries with % wildcards
			
		Returns:
			Tuple of (where_clause_string, parameters_dict)
			
		Security:
			- All values are parameterized, never concatenated
			- Field names are whitelisted via field_mapping
			- No user input is directly embedded in SQL
		"""
		conditions = []
		params = {}
		
		for filter_key, filter_value in filters.items():
			if filter_key not in field_mapping:
				# Skip unmapped filters (not in whitelist)
				frappe.log_error(
					f"Attempted to use unmapped filter: {filter_key}",
					"Query Builder: Unmapped Filter"
				)
				continue
			
			if filter_value is None or filter_value == "":
				# Skip empty/null filters
				continue
			
			sql_field = field_mapping[filter_key]
			param_name = filter_key.replace('.', '_')  # Sanitize param name
			
			# Handle different filter types
			if isinstance(filter_value, (list, tuple)) and len(filter_value) > 0:
				if len(filter_value) == 2 and filter_key.endswith('_range'):
					# Range query (e.g., date_range: ['2026-01-01', '2026-01-31'])
					conditions.append(
						f"{sql_field} BETWEEN %({param_name}_start)s AND %({param_name}_end)s"
					)
					params[f"{param_name}_start"] = filter_value[0]
					params[f"{param_name}_end"] = filter_value[1]
				else:
					# IN clause (e.g., companies: ['Co1', 'Co2', 'Co3'])
					placeholders = ', '.join([
						f"%({param_name}_{i})s" for i in range(len(filter_value))
					])
					conditions.append(f"{sql_field} IN ({placeholders})")
					for i, val in enumerate(filter_value):
						params[f"{param_name}_{i}"] = val
			
			elif isinstance(filter_value, str) and allow_wildcards and '%' in filter_value:
				# LIKE query (only if explicitly allowed)
				conditions.append(f"{sql_field} LIKE %({param_name})s")
				params[param_name] = filter_value
			
			else:
				# Standard equality
				conditions.append(f"{sql_field} = %({param_name})s")
				params[param_name] = filter_value
		
		where_clause = " AND ".join(conditions) if conditions else "1=1"
		return where_clause, params
	
	@staticmethod
	def build_date_range_condition(field_name: str,
	                                from_date: Optional[str] = None,
	                                to_date: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
		"""
		Build date range condition safely.
		
		Args:
			field_name: SQL field name for the date column
			from_date: Start date (inclusive)
			to_date: End date (inclusive)
			
		Returns:
			Tuple of (condition_string, parameters_dict)
		"""
		conditions = []
		params = {}
		
		if from_date:
			conditions.append(f"{field_name} >= %(from_date)s")
			params['from_date'] = getdate(from_date)
		
		if to_date:
			conditions.append(f"{field_name} <= %(to_date)s")
			params['to_date'] = getdate(to_date)
		
		condition = " AND ".join(conditions) if conditions else "1=1"
		return condition, params
	
	@staticmethod
	def execute_safe_query(query_template: str, 
	                       params: Dict[str, Any],
	                       as_dict: bool = True,
	                       debug: bool = False) -> List:
		"""
		Execute parameterized query safely.
		
		Args:
			query_template: SQL with %(param_name)s placeholders
			params: Dictionary of parameters
			as_dict: Return results as dictionaries
			debug: Log query for debugging (sanitizes sensitive data)
			
		Returns:
			Query results
			
		Security:
			- All parameters are properly escaped by MariaDB
			- No string concatenation or formatting
			- Errors are logged without exposing query details to users
		"""
		try:
			if debug:
				# Log sanitized query for debugging (don't log actual values)
				sanitized_params = {k: f"<{type(v).__name__}>" for k, v in params.items()}
				frappe.logger().debug(
					f"Executing safe query with params: {sanitized_params}"
				)
			
			return frappe.db.sql(query_template, params, as_dict=as_dict)
		
		except frappe.db.ProgrammingError as e:
			# SQL syntax error
			frappe.log_error(
				f"SQL syntax error in safe query: {str(e)}\n"
				f"Query template: {query_template}",
				"Query Builder: SQL Syntax Error"
			)
			frappe.throw("Database query failed. Please contact administrator.")
		
		except frappe.db.DataError as e:
			# Data type mismatch or constraint violation
			frappe.log_error(
				f"Data error in safe query: {str(e)}",
				"Query Builder: Data Error"
			)
			frappe.throw("Invalid data in query. Please check your filters.")
		
		except Exception as e:
			# Unexpected error
			frappe.log_error(
				f"Unexpected error in safe query: {str(e)}\n"
				f"Query template: {query_template}",
				"Query Builder: Unexpected Error"
			)
			frappe.throw("Database query failed. Please contact administrator.")
	
	@staticmethod
	def sanitize_order_by(order_by: str, allowed_fields: List[str]) -> str:
		"""
		Sanitize ORDER BY clause to prevent SQL injection.
		
		Args:
			order_by: User-provided order by string
			allowed_fields: List of allowed field names
			
		Returns:
			Sanitized ORDER BY clause
			
		Security:
			- Only allows whitelisted field names
			- Only allows ASC/DESC keywords
			- Rejects any other SQL keywords or special characters
		"""
		if not order_by:
			return ""
		
		# Parse ORDER BY components
		parts = []
		for part in order_by.split(','):
			part = part.strip()
			
			# Split field and direction
			tokens = part.split()
			if len(tokens) == 0:
				continue
			
			field = tokens[0]
			direction = tokens[1].upper() if len(tokens) > 1 else 'ASC'
			
			# Validate field is in whitelist
			if field not in allowed_fields:
				frappe.log_error(
					f"Attempted to order by non-whitelisted field: {field}",
					"Query Builder: Invalid ORDER BY"
				)
				continue
			
			# Validate direction
			if direction not in ('ASC', 'DESC'):
				direction = 'ASC'
			
			parts.append(f"{field} {direction}")
		
		return ", ".join(parts) if parts else ""
	
	@staticmethod
	def validate_limit(limit: Any, max_limit: int = 5000) -> int:
		"""
		Validate and sanitize LIMIT value.
		
		Args:
			limit: User-provided limit
			max_limit: Maximum allowed limit
			
		Returns:
			Sanitized integer limit
		"""
		try:
			limit = cint(limit)
			if limit <= 0:
				return max_limit
			return min(limit, max_limit)
		except:
			return max_limit


class ReportQueryBuilder(SafeQueryBuilder):
	"""
	Specialized query builder for Frappe reports.
	Extends SafeQueryBuilder with report-specific patterns.
	"""
	
	@staticmethod
	def build_report_query(base_query: str,
	                       filters: Dict[str, Any],
	                       field_mapping: Dict[str, str],
	                       order_by: Optional[str] = None,
	                       allowed_order_fields: Optional[List[str]] = None,
	                       limit: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
		"""
		Build complete report query with WHERE, ORDER BY, and LIMIT.
		
		Args:
			base_query: Base SELECT query (without WHERE clause)
			filters: Filter dictionary from report
			field_mapping: Mapping of filter keys to SQL fields
			order_by: ORDER BY clause (will be sanitized)
			allowed_order_fields: Whitelisted fields for ordering
			limit: Result limit
			
		Returns:
			Tuple of (complete_query, parameters)
		"""
		builder = SafeQueryBuilder()
		
		# Build WHERE clause
		where_clause, params = builder.build_where_clause(filters, field_mapping)
		
		# Build complete query
		query = f"{base_query}\nWHERE {where_clause}"
		
		# Add ORDER BY if specified
		if order_by and allowed_order_fields:
			sanitized_order = builder.sanitize_order_by(order_by, allowed_order_fields)
			if sanitized_order:
				query += f"\nORDER BY {sanitized_order}"
		
		# Add LIMIT if specified
		if limit:
			validated_limit = builder.validate_limit(limit)
			query += f"\nLIMIT {validated_limit}"
		
		return query, params


# Convenience function for backward compatibility
def execute_safe_query(query: str, params: Dict[str, Any], as_dict: bool = True) -> List:
	"""
	Convenience wrapper for SafeQueryBuilder.execute_safe_query()
	
	Args:
		query: SQL query with %(param)s placeholders
		params: Dictionary of parameters
		as_dict: Return results as dictionaries
		
	Returns:
		Query results
	"""
	return SafeQueryBuilder.execute_safe_query(query, params, as_dict)
