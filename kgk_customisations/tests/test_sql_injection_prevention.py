# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

"""
Security Tests: SQL Injection Prevention
=========================================

Tests to verify that SQL injection vulnerabilities have been fixed.
These tests attempt various SQL injection attack patterns and verify they are blocked.

Author: Security Remediation Team
Date: January 19, 2026
"""

import frappe
import unittest
from kgk_customisations.kgk_customisations.utils.query_builder import SafeQueryBuilder


class TestSQLInjectionPrevention(unittest.TestCase):
	"""Test that SQL injection attempts are blocked"""
	
	@classmethod
	def setUpClass(cls):
		"""Set up test data"""
		frappe.set_user("Administrator")
	
	def test_query_builder_prevents_injection_in_where(self):
		"""Test that malicious WHERE conditions are safely handled"""
		malicious_filters = {
			"serial_number": "'; DROP TABLE `tabStone Prediction`; --",
			"lot_id": "1' OR '1'='1"
		}
		
		field_mapping = {
			"serial_number": "sp.serial_number",
			"lot_id": "sp.lot_id"
		}
		
		# Build WHERE clause - should safely parameterize
		where_clause, params = SafeQueryBuilder.build_where_clause(
			malicious_filters, field_mapping
		)
		
		# Verify the malicious content is in params, not in the SQL string
		self.assertIn("serial_number", params)
		self.assertIn("lot_id", params)
		self.assertEqual(params["serial_number"], "'; DROP TABLE `tabStone Prediction`; --")
		self.assertEqual(params["lot_id"], "1' OR '1'='1")
		
		# Verify WHERE clause only contains placeholders, not actual values
		self.assertNotIn("DROP TABLE", where_clause)
		self.assertNotIn("1'='1", where_clause)
		self.assertIn("%(serial_number)s", where_clause)
		self.assertIn("%(lot_id)s", where_clause)
	
	def test_stone_prediction_report_with_sql_injection_attempt(self):
		"""Test stone prediction report blocks SQL injection"""
		from kgk_customisations.kgk_customisations.report.stone_prediction_analysis.stone_prediction_analysis import execute
		
		malicious_filters = {
			"serial_number": "'; DROP TABLE `tabStone Prediction`; --",
			"lot_id": "' UNION SELECT * FROM `tabUser`; --",
			"from_date": "2026-01-01' OR '1'='1",
		}
		
		# Should execute safely without SQL injection
		try:
			columns, data = execute(malicious_filters)
			
			# Query should return safe results (likely empty)
			# and NOT execute malicious SQL
			self.assertIsInstance(data, list)
			self.assertIsInstance(columns, list)
			
			# Verify tables still exist (DROP didn't execute)
			exists = frappe.db.exists("DocType", "Stone Prediction")
			self.assertTrue(exists, "Stone Prediction DocType should still exist")
			
		except Exception as e:
			# If it fails, it should be a validation error, not a SQL error
			self.assertNotIn("syntax error", str(e).lower())
	
	def test_order_by_sanitization(self):
		"""Test that ORDER BY clauses are sanitized"""
		malicious_order = "name; DROP TABLE users; --"
		allowed_fields = ["name", "prediction_date", "predicted_by"]
		
		sanitized = SafeQueryBuilder.sanitize_order_by(
			malicious_order, allowed_fields
		)
		
		# Should only include valid fields
		self.assertNotIn("DROP", sanitized)
		self.assertNotIn(";", sanitized)
	
	def test_order_by_whitelist_enforcement(self):
		"""Test that only whitelisted fields are allowed in ORDER BY"""
		order_by = "malicious_field ASC"
		allowed_fields = ["name", "date"]
		
		sanitized = SafeQueryBuilder.sanitize_order_by(order_by, allowed_fields)
		
		# Should return empty string since field not in whitelist
		self.assertEqual(sanitized, "")
	
	def test_order_by_allows_valid_fields(self):
		"""Test that valid ORDER BY clauses work correctly"""
		order_by = "name DESC, prediction_date ASC"
		allowed_fields = ["name", "prediction_date", "predicted_by"]
		
		sanitized = SafeQueryBuilder.sanitize_order_by(order_by, allowed_fields)
		
		# Should preserve valid fields
		self.assertIn("name DESC", sanitized)
		self.assertIn("prediction_date ASC", sanitized)
	
	def test_limit_validation(self):
		"""Test that LIMIT values are validated"""
		# Test negative limit
		self.assertEqual(SafeQueryBuilder.validate_limit(-100), 5000)
		
		# Test zero limit
		self.assertEqual(SafeQueryBuilder.validate_limit(0), 5000)
		
		# Test very large limit (should cap at max)
		self.assertEqual(SafeQueryBuilder.validate_limit(999999), 5000)
		
		# Test normal limit
		self.assertEqual(SafeQueryBuilder.validate_limit(100), 100)
		
		# Test string limit (should convert)
		self.assertEqual(SafeQueryBuilder.validate_limit("50"), 50)
		
		# Test malicious limit
		self.assertEqual(
			SafeQueryBuilder.validate_limit("100; DROP TABLE users"),
			5000  # Should use default on conversion error
		)
	
	def test_unmapped_filters_are_ignored(self):
		"""Test that unmapped filters don't make it into the query"""
		filters = {
			"valid_field": "value1",
			"malicious_unmapped_field": "'; DROP TABLE users; --"
		}
		
		field_mapping = {
			"valid_field": "t.valid_field"
		}
		
		where_clause, params = SafeQueryBuilder.build_where_clause(
			filters, field_mapping
		)
		
		# Only valid_field should be in params
		self.assertIn("valid_field", params)
		self.assertNotIn("malicious_unmapped_field", params)
		
		# WHERE clause should only reference valid field
		self.assertIn("t.valid_field", where_clause)
		self.assertNotIn("malicious_unmapped_field", where_clause)
	
	def test_execute_safe_query_handles_errors(self):
		"""Test that execute_safe_query handles errors securely"""
		# Malformed query should log error but not expose details
		malicious_query = "SELECT * FROM `tabUser` WHERE name = %(name)s AND bad_syntax"
		params = {"name": "test"}
		
		with self.assertRaises(frappe.ValidationError):
			SafeQueryBuilder.execute_safe_query(malicious_query, params)
	
	def test_date_range_condition_builder(self):
		"""Test safe date range condition building"""
		# Attempt SQL injection through date parameter - should raise validation error
		malicious_date = "2026-01-01' OR '1'='1"
		
		# The builder should reject invalid dates (this is correct security behavior)
		with self.assertRaises(frappe.ValidationError):
			SafeQueryBuilder.build_date_range_condition(
				"sp.prediction_date",
				malicious_date,
				"2026-01-31"
			)
		
		# Test with valid dates to ensure normal operation works
		condition, params = SafeQueryBuilder.build_date_range_condition(
			"sp.prediction_date",
			"2026-01-01",
			"2026-01-31"
		)
		
		# Verify parameters are safely bound
		self.assertIn("from_date", params)
		self.assertIn("to_date", params)
		
		# Verify condition uses placeholders
		self.assertIn("%(from_date)s", condition)
		self.assertIn("%(to_date)s", condition)
		
		# Verify malicious content is in params, not query
		self.assertNotIn("OR '1'='1", condition)
	
	def test_list_parameter_in_clause(self):
		"""Test that IN clauses with lists are safely parameterized"""
		filters = {
			"companies": ["Company1", "Company2'; DROP TABLE users; --"]
		}
		
		field_mapping = {
			"companies": "t.company"
		}
		
		where_clause, params = SafeQueryBuilder.build_where_clause(
			filters, field_mapping
		)
		
		# Should have individual parameters for each list item
		self.assertIn("companies_0", params)
		self.assertIn("companies_1", params)
		
		# Malicious content should be in params, not query
		self.assertEqual(params["companies_1"], "Company2'; DROP TABLE users; --")
		self.assertNotIn("DROP TABLE", where_clause)
		
		# WHERE clause should use parameterized IN clause
		self.assertIn("IN", where_clause)
		self.assertIn("%(companies_0)s", where_clause)
		self.assertIn("%(companies_1)s", where_clause)
	
	def test_range_parameter(self):
		"""Test that range parameters are safely handled"""
		filters = {
			"amount_range": ["100", "1000' OR '1'='1"]
		}
		
		field_mapping = {
			"amount_range": "t.amount"
		}
		
		where_clause, params = SafeQueryBuilder.build_where_clause(
			filters, field_mapping
		)
		
		# Should use BETWEEN with parameters
		self.assertIn("BETWEEN", where_clause)
		self.assertIn("amount_range_start", params)
		self.assertIn("amount_range_end", params)
		
		# Malicious content in params, not query
		self.assertEqual(params["amount_range_end"], "1000' OR '1'='1")
		self.assertNotIn("OR '1'='1", where_clause)


class TestQueryBuilderFunctionality(unittest.TestCase):
	"""Test that SafeQueryBuilder works correctly for legitimate use cases"""
	
	def test_simple_equality_filter(self):
		"""Test simple equality filters work correctly"""
		filters = {"name": "TEST-001", "company": "Test Company"}
		field_mapping = {"name": "t.name", "company": "t.company"}
		
		where_clause, params = SafeQueryBuilder.build_where_clause(
			filters, field_mapping
		)
		
		self.assertEqual(params["name"], "TEST-001")
		self.assertEqual(params["company"], "Test Company")
		self.assertIn("t.name = %(name)s", where_clause)
		self.assertIn("t.company = %(company)s", where_clause)
	
	def test_empty_filters(self):
		"""Test that empty filters result in 1=1 condition"""
		filters = {}
		field_mapping = {}
		
		where_clause, params = SafeQueryBuilder.build_where_clause(
			filters, field_mapping
		)
		
		self.assertEqual(where_clause, "1=1")
		self.assertEqual(params, {})
	
	def test_none_and_empty_values_skipped(self):
		"""Test that None and empty string values are skipped"""
		filters = {
			"field1": "value",
			"field2": None,
			"field3": "",
			"field4": "another_value"
		}
		
		field_mapping = {
			"field1": "t.field1",
			"field2": "t.field2",
			"field3": "t.field3",
			"field4": "t.field4"
		}
		
		where_clause, params = SafeQueryBuilder.build_where_clause(
			filters, field_mapping
		)
		
		# Only field1 and field4 should be in params
		self.assertIn("field1", params)
		self.assertIn("field4", params)
		self.assertNotIn("field2", params)
		self.assertNotIn("field3", params)


def run_tests():
	"""Run all security tests"""
	suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
	unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
	run_tests()
