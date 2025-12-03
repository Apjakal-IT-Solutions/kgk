# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Data integrity validation utilities
Validates database consistency, balance reconciliation, and workflow states
"""

import frappe
from frappe.utils import flt, getdate, today, add_days
from datetime import datetime


class DataIntegrityValidator:
    """Validate data integrity across the cash management system"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def validate_all(self):
        """Run all validation checks"""
        print("Starting comprehensive data integrity validation...")
        print("=" * 80)
        
        self.validate_invoice_uniqueness()
        self.validate_balance_calculations()
        self.validate_workflow_states()
        self.validate_foreign_keys()
        self.validate_amount_consistency()
        self.validate_date_logic()
        self.validate_audit_trail_completeness()
        
        self.generate_report()
    
    def validate_invoice_uniqueness(self):
        """Ensure all invoice numbers are unique"""
        print("\n1. Validating invoice number uniqueness...")
        
        duplicates = frappe.db.sql("""
            SELECT invoice_number, COUNT(*) as count
            FROM `tabCash Document`
            WHERE invoice_number IS NOT NULL
            GROUP BY invoice_number
            HAVING count > 1
        """, as_dict=1)
        
        if duplicates:
            for dup in duplicates:
                self.issues.append({
                    "severity": "CRITICAL",
                    "category": "Invoice Numbers",
                    "message": f"Duplicate invoice number: {dup.invoice_number} (count: {dup.count})"
                })
        else:
            print("  ✓ All invoice numbers are unique")
        
        self.stats["invoice_uniqueness"] = len(duplicates)
    
    def validate_balance_calculations(self):
        """Validate that ERP balances match actual document totals"""
        print("\n2. Validating balance calculations...")
        
        balances = frappe.db.sql("""
            SELECT name, balance_date, company, erp_balance
            FROM `tabDaily Cash Balance`
            WHERE docstatus = 1
        """, as_dict=1)
        
        mismatches = 0
        
        for balance in balances:
            # Calculate actual balance from documents
            actual_balance = self._calculate_actual_balance(
                balance.balance_date, 
                balance.company
            )
            
            stored_balance = flt(balance.erp_balance)
            
            # Allow small rounding differences (0.01)
            if abs(stored_balance - actual_balance) > 0.01:
                self.issues.append({
                    "severity": "HIGH",
                    "category": "Balance Mismatch",
                    "message": f"Balance mismatch on {balance.balance_date} for {balance.company}: "
                              f"Stored={stored_balance}, Actual={actual_balance}"
                })
                mismatches += 1
        
        if mismatches == 0:
            print(f"  ✓ All {len(balances)} balances match calculated values")
        else:
            print(f"  ✗ Found {mismatches} balance mismatches")
        
        self.stats["balance_mismatches"] = mismatches
    
    def _calculate_actual_balance(self, balance_date, company):
        """Calculate balance from actual documents"""
        result = frappe.db.sql("""
            SELECT 
                SUM(CASE WHEN main_document_type = 'Receipt' THEN amount ELSE 0 END) as receipts,
                SUM(CASE WHEN main_document_type = 'Payment' THEN amount ELSE 0 END) as payments
            FROM `tabCash Document`
            WHERE company = %s
            AND transaction_date = %s
            AND docstatus = 1
        """, (company, balance_date), as_dict=1)
        
        if result:
            receipts = flt(result[0].receipts)
            payments = flt(result[0].payments)
            return receipts - payments
        
        return 0.0
    
    def validate_workflow_states(self):
        """Validate workflow state consistency"""
        print("\n3. Validating workflow states...")
        
        # Check for invalid workflow states
        valid_states = [
            None, "Draft", "Pending Approval", "Approved", 
            "Rejected", "Revision Required", "Cancelled"
        ]
        
        invalid = frappe.db.sql("""
            SELECT name, workflow_state
            FROM `tabCash Document`
            WHERE workflow_state IS NOT NULL
            AND workflow_state NOT IN %s
        """, (valid_states,), as_dict=1)
        
        if invalid:
            for doc in invalid:
                self.issues.append({
                    "severity": "MEDIUM",
                    "category": "Workflow",
                    "message": f"Invalid workflow state '{doc.workflow_state}' in {doc.name}"
                })
        else:
            print("  ✓ All workflow states are valid")
        
        # Check for submitted documents without approval (if workflow enabled)
        unapproved_submitted = frappe.db.sql("""
            SELECT name, workflow_state, docstatus
            FROM `tabCash Document`
            WHERE docstatus = 1
            AND (workflow_state IS NULL OR workflow_state NOT IN ('Approved', 'Finally Verified'))
        """, as_dict=1)
        
        if unapproved_submitted:
            for doc in unapproved_submitted[:10]:  # Limit to first 10
                self.warnings.append({
                    "category": "Workflow",
                    "message": f"Document {doc.name} is submitted but not approved"
                })
        
        self.stats["workflow_issues"] = len(invalid)
    
    def validate_foreign_keys(self):
        """Validate foreign key relationships"""
        print("\n4. Validating foreign key relationships...")
        
        # Check if all companies exist
        orphaned_docs = frappe.db.sql("""
            SELECT cd.name, cd.company
            FROM `tabCash Document` cd
            LEFT JOIN `tabCompany` c ON cd.company = c.name
            WHERE c.name IS NULL
        """, as_dict=1)
        
        if orphaned_docs:
            for doc in orphaned_docs:
                self.issues.append({
                    "severity": "CRITICAL",
                    "category": "Foreign Keys",
                    "message": f"Document {doc.name} references non-existent company: {doc.company}"
                })
        else:
            print("  ✓ All company references are valid")
        
        # Check balance submissions
        orphaned_balances = frappe.db.sql("""
            SELECT dcb.name, dcb.company
            FROM `tabDaily Cash Balance` dcb
            LEFT JOIN `tabCompany` c ON dcb.company = c.name
            WHERE c.name IS NULL
        """, as_dict=1)
        
        if orphaned_balances:
            for bal in orphaned_balances:
                self.issues.append({
                    "severity": "CRITICAL",
                    "category": "Foreign Keys",
                    "message": f"Balance {bal.name} references non-existent company: {bal.company}"
                })
        else:
            print("  ✓ All balance company references are valid")
        
        self.stats["orphaned_records"] = len(orphaned_docs) + len(orphaned_balances)
    
    def validate_amount_consistency(self):
        """Validate amount fields are positive and consistent"""
        print("\n5. Validating amount consistency...")
        
        # Check for negative amounts
        negative_amounts = frappe.db.sql("""
            SELECT name, amount
            FROM `tabCash Document`
            WHERE amount < 0
        """, as_dict=1)
        
        if negative_amounts:
            for doc in negative_amounts:
                self.issues.append({
                    "severity": "HIGH",
                    "category": "Amount Validation",
                    "message": f"Negative amount in {doc.name}: {doc.amount}"
                })
        else:
            print("  ✓ All amounts are positive")
        
        # Check for zero amounts in submitted documents
        zero_amounts = frappe.db.sql("""
            SELECT name, amount
            FROM `tabCash Document`
            WHERE docstatus = 1
            AND (amount IS NULL OR amount = 0)
        """, as_dict=1)
        
        if zero_amounts:
            for doc in zero_amounts:
                self.warnings.append({
                    "category": "Amount Validation",
                    "message": f"Zero or null amount in submitted document {doc.name}"
                })
        
        self.stats["amount_issues"] = len(negative_amounts) + len(zero_amounts)
    
    def validate_date_logic(self):
        """Validate date-related logic"""
        print("\n6. Validating date logic...")
        
        # Check for future dates beyond reasonable range
        far_future = add_days(today(), 365)
        
        future_dates = frappe.db.sql("""
            SELECT name, transaction_date
            FROM `tabCash Document`
            WHERE transaction_date > %s
        """, (far_future,), as_dict=1)
        
        if future_dates:
            for doc in future_dates:
                self.warnings.append({
                    "category": "Date Validation",
                    "message": f"Document {doc.name} has far future date: {doc.transaction_date}"
                })
        
        # Check for very old dates (potential data entry errors)
        very_old = add_days(today(), -365 * 10)  # 10 years ago
        
        old_dates = frappe.db.sql("""
            SELECT name, transaction_date
            FROM `tabCash Document`
            WHERE transaction_date < %s
            AND docstatus = 0
        """, (very_old,), as_dict=1)
        
        if old_dates:
            for doc in old_dates:
                self.warnings.append({
                    "category": "Date Validation",
                    "message": f"Draft document {doc.name} has very old date: {doc.transaction_date}"
                })
        
        print(f"  ✓ Checked date logic ({len(future_dates)} future, {len(old_dates)} old)")
        
        self.stats["date_issues"] = len(future_dates) + len(old_dates)
    
    def validate_audit_trail_completeness(self):
        """Validate that audit trails exist for critical operations"""
        print("\n7. Validating audit trail completeness...")
        
        # Check submitted documents have creation audit
        docs_without_audit = frappe.db.sql("""
            SELECT cd.name
            FROM `tabCash Document` cd
            WHERE cd.docstatus = 1
            AND NOT EXISTS (
                SELECT 1 FROM `tabCash Document Audit Trail` cat
                WHERE cat.document_name = cd.name
                AND cat.activity_type = 'Document Creation'
            )
        """, as_dict=1)
        
        if docs_without_audit:
            for doc in docs_without_audit[:10]:  # Limit to first 10
                self.warnings.append({
                    "category": "Audit Trail",
                    "message": f"No creation audit trail for {doc.name}"
                })
        
        # Check verified balances have audit
        verified_without_audit = frappe.db.sql("""
            SELECT dcb.name, dcb.status
            FROM `tabDaily Cash Balance` dcb
            WHERE dcb.status IN ('Manually Verified', 'ERP Verified', 'Finally Verified')
            AND NOT EXISTS (
                SELECT 1 FROM `tabCash Document Audit Trail` cat
                WHERE cat.document_name = dcb.name
                AND cat.activity_type LIKE '%Verification%'
            )
        """, as_dict=1)
        
        if verified_without_audit:
            for bal in verified_without_audit[:10]:
                self.warnings.append({
                    "category": "Audit Trail",
                    "message": f"No verification audit trail for balance {bal.name}"
                })
        
        print(f"  ✓ Audit trail check complete ({len(docs_without_audit)} missing)")
        
        self.stats["missing_audit"] = len(docs_without_audit) + len(verified_without_audit)
    
    def generate_report(self):
        """Generate validation report"""
        print("\n" + "=" * 80)
        print("DATA INTEGRITY VALIDATION REPORT")
        print("=" * 80)
        
        # Summary statistics
        print("\nSUMMARY:")
        print(f"  Total Issues: {len(self.issues)}")
        print(f"  Total Warnings: {len(self.warnings)}")
        
        # Critical issues
        critical = [i for i in self.issues if i["severity"] == "CRITICAL"]
        high = [i for i in self.issues if i["severity"] == "HIGH"]
        medium = [i for i in self.issues if i["severity"] == "MEDIUM"]
        
        print(f"\nBY SEVERITY:")
        print(f"  Critical: {len(critical)}")
        print(f"  High: {len(high)}")
        print(f"  Medium: {len(medium)}")
        
        # Detailed issues
        if self.issues:
            print("\nISSUES FOUND:")
            for issue in self.issues[:20]:  # Show first 20
                print(f"  [{issue['severity']}] {issue['category']}: {issue['message']}")
            
            if len(self.issues) > 20:
                print(f"  ... and {len(self.issues) - 20} more issues")
        
        # Warnings
        if self.warnings:
            print("\nWARNINGS:")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"  [WARNING] {warning['category']}: {warning['message']}")
            
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more warnings")
        
        # Statistics
        print("\nSTATISTICS:")
        for key, value in self.stats.items():
            print(f"  {key}: {value}")
        
        print("\n" + "=" * 80)
        
        if len(self.issues) == 0:
            print("✓ NO CRITICAL ISSUES FOUND - Data integrity is good!")
        else:
            print("✗ ISSUES FOUND - Please review and fix the problems above")
        
        print("=" * 80)


def fix_balance_mismatches():
    """Automatically fix balance calculation mismatches"""
    print("Fixing balance mismatches...")
    
    balances = frappe.db.sql("""
        SELECT name, balance_date, company
        FROM `tabDaily Cash Balance`
        WHERE docstatus = 1
    """, as_dict=1)
    
    fixed_count = 0
    
    for balance in balances:
        # Recalculate balance
        result = frappe.db.sql("""
            SELECT 
                SUM(CASE WHEN main_document_type = 'Receipt' THEN amount ELSE 0 END) as receipts,
                SUM(CASE WHEN main_document_type = 'Payment' THEN amount ELSE 0 END) as payments
            FROM `tabCash Document`
            WHERE company = %s
            AND transaction_date = %s
            AND docstatus = 1
        """, (balance.company, balance.balance_date), as_dict=1)
        
        if result:
            actual_balance = flt(result[0].receipts) - flt(result[0].payments)
            
            # Update if different
            current_balance = frappe.db.get_value("Daily Cash Balance", balance.name, "erp_balance")
            
            if abs(flt(current_balance) - actual_balance) > 0.01:
                frappe.db.set_value("Daily Cash Balance", balance.name, "erp_balance", actual_balance)
                fixed_count += 1
                print(f"  ✓ Fixed balance for {balance.balance_date} - {balance.company}")
    
    frappe.db.commit()
    print(f"\nFixed {fixed_count} balance mismatches")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "validate":
            validator = DataIntegrityValidator()
            validator.validate_all()
        
        elif command == "fix_balances":
            fix_balance_mismatches()
        
        else:
            print("Unknown command. Use: validate|fix_balances")
    else:
        print("Usage: python data_integrity_validator.py <command>")
        print("Commands:")
        print("  validate      - Run all validation checks")
        print("  fix_balances  - Automatically fix balance mismatches")
