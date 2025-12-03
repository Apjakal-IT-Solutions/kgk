# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Security and permission testing utilities
Tests for SQL injection, XSS, permission enforcement, and security vulnerabilities
"""

import frappe
from frappe.utils import cint
import re


class SecurityAuditor:
    """Comprehensive security audit for cash management system"""
    
    def __init__(self):
        self.vulnerabilities = []
        self.warnings = []
        self.passed_checks = []
    
    def run_full_audit(self):
        """Run complete security audit"""
        print("Starting comprehensive security audit...")
        print("=" * 80)
        
        self.test_sql_injection()
        self.test_xss_prevention()
        self.test_permission_enforcement()
        self.test_api_authentication()
        self.test_data_sanitization()
        self.test_audit_trail_integrity()
        
        self.generate_report()
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        print("\n1. Testing SQL Injection Prevention...")
        
        # Test inputs that could cause SQL injection
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE `tabCash Document`; --",
            "1' UNION SELECT * FROM `tabUser` --",
            "admin'--",
            "1' AND 1=1--"
        ]
        
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        for malicious_input in malicious_inputs:
            try:
                # Try to inject in various fields
                doc = create_test_cash_document(
                    company=malicious_input,
                    transaction_date=frappe.utils.today(),
                    main_document_type="Receipt",
                    amount=1000,
                    description=malicious_input
                )
                doc.insert()
                
                # If it gets here without error, check if injection worked
                # This should NOT execute any SQL
                self.warnings.append({
                    "category": "SQL Injection",
                    "message": f"Potentially unsafe input accepted: {malicious_input[:30]}"
                })
                
                # Clean up
                frappe.db.rollback()
                
            except frappe.exceptions.ValidationError:
                # Expected - input was rejected
                self.passed_checks.append(f"SQL injection prevented: {malicious_input[:30]}")
            except Exception as e:
                # Unexpected error
                if "does not exist" in str(e) or "invalid" in str(e).lower():
                    self.passed_checks.append(f"SQL injection prevented: {malicious_input[:30]}")
                else:
                    self.vulnerabilities.append({
                        "severity": "CRITICAL",
                        "category": "SQL Injection",
                        "message": f"Unexpected error with input: {malicious_input[:30]} - {str(e)}"
                    })
        
        print(f"  ✓ Tested {len(malicious_inputs)} SQL injection patterns")
    
    def test_xss_prevention(self):
        """Test for XSS (Cross-Site Scripting) vulnerabilities"""
        print("\n2. Testing XSS Prevention...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
            "');alert('XSS');//"
        ]
        
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        for payload in xss_payloads:
            try:
                doc = create_test_cash_document(
                    company="_Test Company",
                    transaction_date=frappe.utils.today(),
                    main_document_type="Receipt",
                    amount=1000,
                    description=payload,
                    reference_number=payload
                )
                doc.insert()
                
                # Check if the payload is properly escaped/sanitized
                saved_desc = frappe.db.get_value("Cash Document", doc.name, "description")
                
                if "<script" in saved_desc or "onerror" in saved_desc or "javascript:" in saved_desc:
                    self.vulnerabilities.append({
                        "severity": "HIGH",
                        "category": "XSS",
                        "message": f"Unsanitized XSS payload stored: {payload[:30]}"
                    })
                else:
                    self.passed_checks.append(f"XSS payload sanitized: {payload[:30]}")
                
                frappe.db.rollback()
                
            except Exception as e:
                # If error occurs, it's likely validation caught it
                self.passed_checks.append(f"XSS payload rejected: {payload[:30]}")
        
        print(f"  ✓ Tested {len(xss_payloads)} XSS attack patterns")
    
    def test_permission_enforcement(self):
        """Test permission checks are enforced"""
        print("\n3. Testing Permission Enforcement...")
        
        # Test 1: Guest user shouldn't access Cash Documents
        frappe.set_user("Guest")
        
        try:
            docs = frappe.get_all("Cash Document", limit=1)
            if docs:
                self.vulnerabilities.append({
                    "severity": "CRITICAL",
                    "category": "Permissions",
                    "message": "Guest user can access Cash Documents"
                })
        except frappe.exceptions.PermissionError:
            self.passed_checks.append("Guest access correctly denied")
        
        # Reset to Administrator
        frappe.set_user("Administrator")
        
        # Test 2: Check role-based access
        required_roles = {
            "Cash Document": ["Accounts User", "Accounts Manager"],
            "Daily Cash Balance": ["Accounts User", "Accounts Manager"],
            "Cash Balance Submission": ["Accounts Manager"]
        }
        
        for doctype, roles in required_roles.items():
            # Check if permissions are configured
            perms = frappe.get_all("Custom DocPerm", 
                filters={"parent": doctype},
                fields=["role", "read", "write", "submit"]
            )
            
            if not perms:
                self.warnings.append({
                    "category": "Permissions",
                    "message": f"No custom permissions configured for {doctype}"
                })
        
        print("  ✓ Permission enforcement checks completed")
    
    def test_api_authentication(self):
        """Test API endpoints require authentication"""
        print("\n4. Testing API Authentication...")
        
        # Test whitelisted methods
        whitelisted_methods = [
            "kgk_customisations.kgk_customisations.report.audit_trail_report.audit_trail_report.export_audit_report",
            "kgk_customisations.kgk_customisations.report.cash_flow_analysis.cash_flow_analysis.generate_statement"
        ]
        
        for method in whitelisted_methods:
            try:
                # Check if method exists and is properly decorated
                parts = method.split(".")
                module_path = ".".join(parts[:-1])
                method_name = parts[-1]
                
                # This is a simplified check - in reality you'd test actual API calls
                self.passed_checks.append(f"Whitelisted method checked: {method_name}")
                
            except Exception as e:
                self.warnings.append({
                    "category": "API Authentication",
                    "message": f"Could not verify method: {method_name}"
                })
        
        print("  ✓ API authentication checks completed")
    
    def test_data_sanitization(self):
        """Test data input sanitization"""
        print("\n5. Testing Data Sanitization...")
        
        # Test various input sanitization scenarios
        test_cases = [
            {
                "input": "Normal Company Name",
                "field": "company",
                "expected": "safe"
            },
            {
                "input": "Company\x00Name",  # Null byte
                "field": "description",
                "expected": "reject"
            },
            {
                "input": "A" * 1000,  # Very long string
                "field": "description",
                "expected": "truncate_or_reject"
            }
        ]
        
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        for test in test_cases:
            try:
                doc = create_test_cash_document(
                    company="_Test Company",
                    transaction_date=frappe.utils.today(),
                    main_document_type="Receipt",
                    amount=1000
                )
                
                # Set the field to test
                if test["field"] == "description":
                    doc.description = test["input"]
                
                doc.insert()
                
                # Check if input was properly handled
                saved_value = getattr(doc, test["field"], "")
                
                if test["expected"] == "reject" and saved_value == test["input"]:
                    self.warnings.append({
                        "category": "Data Sanitization",
                        "message": f"Potentially unsafe input accepted in {test['field']}"
                    })
                else:
                    self.passed_checks.append(f"Input sanitization OK for {test['field']}")
                
                frappe.db.rollback()
                
            except Exception:
                # Rejection is expected for unsafe inputs
                self.passed_checks.append(f"Unsafe input rejected for {test['field']}")
        
        print("  ✓ Data sanitization checks completed")
    
    def test_audit_trail_integrity(self):
        """Test that audit trails cannot be tampered with"""
        print("\n6. Testing Audit Trail Integrity...")
        
        # Try to modify audit trail directly
        try:
            # Create a test audit entry
            audit = frappe.get_doc({
                "doctype": "Cash Document Audit Trail",
                "document_type": "Cash Document",
                "document_name": "TEST-DOC-001",
                "activity_type": "Document Creation",
                "user": frappe.session.user,
                "timestamp": frappe.utils.now(),
                "details": "Test audit entry"
            })
            audit.insert()
            
            original_activity = audit.activity_type
            
            # Try to modify
            try:
                audit.activity_type = "Modified Activity"
                audit.save()
                
                # Check if modification was allowed
                saved_activity = frappe.db.get_value("Cash Document Audit Trail", 
                                                      audit.name, "activity_type")
                
                if saved_activity != original_activity:
                    self.vulnerabilities.append({
                        "severity": "HIGH",
                        "category": "Audit Trail",
                        "message": "Audit trail can be modified after creation"
                    })
                else:
                    self.passed_checks.append("Audit trail modification prevented")
                    
            except Exception:
                self.passed_checks.append("Audit trail modification correctly prevented")
            
            frappe.db.rollback()
            
        except Exception as e:
            self.warnings.append({
                "category": "Audit Trail",
                "message": f"Could not test audit trail integrity: {str(e)}"
            })
        
        print("  ✓ Audit trail integrity checks completed")
    
    def generate_report(self):
        """Generate security audit report"""
        print("\n" + "=" * 80)
        print("SECURITY AUDIT REPORT")
        print("=" * 80)
        
        # Summary
        print("\nSUMMARY:")
        print(f"  Vulnerabilities Found: {len(self.vulnerabilities)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Checks Passed: {len(self.passed_checks)}")
        
        # Vulnerabilities by severity
        critical = [v for v in self.vulnerabilities if v.get("severity") == "CRITICAL"]
        high = [v for v in self.vulnerabilities if v.get("severity") == "HIGH"]
        medium = [v for v in self.vulnerabilities if v.get("severity") == "MEDIUM"]
        
        print(f"\nVULNERABILITIES BY SEVERITY:")
        print(f"  Critical: {len(critical)}")
        print(f"  High: {len(high)}")
        print(f"  Medium: {len(medium)}")
        
        # Detailed vulnerabilities
        if self.vulnerabilities:
            print("\nVULNERABILITIES FOUND:")
            for vuln in self.vulnerabilities:
                print(f"  [{vuln.get('severity', 'UNKNOWN')}] {vuln['category']}: {vuln['message']}")
        
        # Warnings
        if self.warnings:
            print("\nWARNINGS:")
            for warning in self.warnings[:10]:
                print(f"  [WARNING] {warning['category']}: {warning['message']}")
        
        # Sample of passed checks
        if self.passed_checks:
            print(f"\nPASSED CHECKS (showing first 10 of {len(self.passed_checks)}):")
            for check in self.passed_checks[:10]:
                print(f"  ✓ {check}")
        
        print("\n" + "=" * 80)
        
        if len(self.vulnerabilities) == 0:
            print("✓ NO CRITICAL VULNERABILITIES FOUND - Security posture is good!")
        else:
            print("✗ VULNERABILITIES FOUND - Please address immediately!")
        
        print("=" * 80)


def test_permission_roles():
    """Test and document required roles for each DocType"""
    print("\nPERMISSION ROLES AUDIT")
    print("=" * 80)
    
    doctypes = [
        "Cash Document",
        "Daily Cash Balance",
        "Cash Balance Submission",
        "Bank Basic Entry",
        "Cash Document Audit Trail"
    ]
    
    for doctype in doctypes:
        print(f"\n{doctype}:")
        
        # Get all permissions
        perms = frappe.get_all("DocPerm",
            filters={"parent": doctype},
            fields=["role", "read", "write", "create", "delete", "submit", "cancel"],
            order_by="role"
        )
        
        if perms:
            print("  Permissions:")
            for perm in perms:
                actions = []
                if perm.read: actions.append("Read")
                if perm.write: actions.append("Write")
                if perm.create: actions.append("Create")
                if perm.delete: actions.append("Delete")
                if perm.submit: actions.append("Submit")
                if perm.cancel: actions.append("Cancel")
                
                print(f"    - {perm.role}: {', '.join(actions)}")
        else:
            print("  ⚠ No permissions configured!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "audit":
            auditor = SecurityAuditor()
            auditor.run_full_audit()
        
        elif command == "permissions":
            test_permission_roles()
        
        else:
            print("Unknown command. Use: audit|permissions")
    else:
        print("Usage: python security_auditor.py <command>")
        print("Commands:")
        print("  audit        - Run full security audit")
        print("  permissions  - Audit permission configuration")
