# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Test suite for Daily Cash Balance functionality
Tests balance calculations, verification workflow, and reconciliation
"""

import frappe
import unittest
from frappe.utils import today, add_days, flt
from kgk_customisations.kgk_customisations.doctype.daily_cash_balance.daily_cash_balance import (
    calculate_erp_balance,
    perform_manual_verification,
    perform_erp_verification
)


class TestDailyCashBalance(unittest.TestCase):
    """Test cases for Daily Cash Balance DocType"""
    
    def setUp(self):
        """Set up test data"""
        self.company = "_Test Company"
        self.test_date = today()
        
        # Clean up existing test data
        frappe.db.delete("Daily Cash Balance", {
            "company": self.company,
            "balance_date": self.test_date
        })
        frappe.db.delete("Cash Document", {
            "company": self.company,
            "transaction_date": self.test_date
        })
        frappe.db.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        frappe.db.rollback()
    
    def test_erp_balance_calculation(self):
        """Test automatic ERP balance calculation"""
        # Create test transactions
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        receipts = [1000, 1500, 2000]
        payments = [500, 750]
        
        for amount in receipts:
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=self.test_date,
                main_document_type="Receipt",
                amount=amount
            )
            doc.insert()
            doc.submit()
        
        for amount in payments:
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=self.test_date,
                main_document_type="Payment",
                amount=amount
            )
            doc.insert()
            doc.submit()
        
        # Get balance
        balance = frappe.get_doc("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": self.company
        })
        
        expected_balance = sum(receipts) - sum(payments)
        self.assertEqual(flt(balance.erp_balance), flt(expected_balance),
                        "ERP balance should match calculated value")
    
    def test_variance_calculation(self):
        """Test variance calculation between manual and ERP balance"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=9500
        )
        balance.insert()
        
        # Variance should be calculated automatically
        self.assertEqual(flt(balance.variance_amount), -500)
        self.assertAlmostEqual(flt(balance.variance_percentage), -5.0, places=1)
    
    def test_manual_verification(self):
        """Test manual verification process"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=10000
        )
        balance.insert()
        
        # Perform manual verification
        balance.status = "Manually Verified"
        balance.verified_by = frappe.session.user
        balance.verification_time = frappe.utils.now()
        balance.save()
        
        self.assertEqual(balance.status, "Manually Verified")
        self.assertIsNotNone(balance.verified_by)
    
    def test_erp_verification(self):
        """Test ERP verification process"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=10000
        )
        balance.insert()
        balance.status = "Manually Verified"
        balance.save()
        
        # Perform ERP verification
        balance.status = "ERP Verified"
        balance.save()
        
        self.assertEqual(balance.status, "ERP Verified")
    
    def test_three_tier_verification_workflow(self):
        """Test complete three-tier verification workflow"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=10000
        )
        balance.insert()
        
        # Tier 1: Manual Verification
        self.assertEqual(balance.status, "Calculated")
        
        balance.status = "Manually Verified"
        balance.save()
        self.assertEqual(balance.status, "Manually Verified")
        
        # Tier 2: ERP Verification
        balance.status = "ERP Verified"
        balance.save()
        self.assertEqual(balance.status, "ERP Verified")
        
        # Tier 3: Final Verification
        balance.status = "Finally Verified"
        balance.save()
        self.assertEqual(balance.status, "Finally Verified")
    
    def test_high_variance_detection(self):
        """Test detection of high variance scenarios"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=8000  # 20% variance
        )
        balance.insert()
        
        variance_pct = flt(balance.variance_percentage)
        self.assertTrue(abs(variance_pct) > 10, "Should detect high variance")
    
    def test_reconciliation_with_opening_balance(self):
        """Test balance reconciliation including opening balance"""
        # Create balance for previous day
        prev_date = add_days(self.test_date, -1)
        prev_balance = create_test_balance(
            company=self.company,
            balance_date=prev_date,
            manual_balance=5000,
            erp_balance=5000
        )
        prev_balance.insert()
        
        # Create current day balance
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=7000,
            erp_balance=7000
        )
        balance.opening_balance = 5000
        balance.insert()
        
        self.assertEqual(flt(balance.opening_balance), 5000)
    
    def test_balance_submission_integration(self):
        """Test integration with Cash Balance Submission"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=10000
        )
        balance.insert()
        
        # Create submission record
        submission = frappe.get_doc({
            "doctype": "Cash Balance Submission",
            "submission_date": self.test_date,
            "company": self.company,
            "submitted_balance": 10000,
            "status": "Tier 1 Verified"
        })
        submission.insert()
        
        # Verify link
        self.assertEqual(submission.submitted_balance, balance.manual_balance)
    
    def test_audit_trail_for_verifications(self):
        """Test audit trail creation for verification activities"""
        balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=10000
        )
        balance.insert()
        
        # Perform verification
        balance.status = "Manually Verified"
        balance.save()
        
        # Check audit trail
        audit_entries = frappe.get_all("Cash Document Audit Trail",
            filters={
                "document_type": "Daily Cash Balance",
                "document_name": balance.name,
                "activity_type": "Manual Verification"
            }
        )
        
        self.assertTrue(len(audit_entries) > 0, "Audit trail should be created")
    
    def test_balance_update_on_document_cancel(self):
        """Test that balance is updated when document is cancelled"""
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        # Create and submit document
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        doc.submit()
        
        # Get initial balance
        balance = frappe.get_doc("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": self.company
        })
        initial_balance = flt(balance.erp_balance)
        
        # Cancel document
        doc.cancel()
        
        # Reload balance
        balance.reload()
        
        # Balance should be reduced
        self.assertEqual(flt(balance.erp_balance), initial_balance - 1000)


def create_test_balance(**kwargs):
    """Helper function to create test Daily Cash Balance"""
    doc = frappe.get_doc({
        "doctype": "Daily Cash Balance",
        "balance_date": kwargs.get("balance_date", today()),
        "company": kwargs.get("company", "_Test Company"),
        "manual_balance": kwargs.get("manual_balance", 0),
        "erp_balance": kwargs.get("erp_balance", 0),
        "opening_balance": kwargs.get("opening_balance", 0),
        "status": kwargs.get("status", "Calculated")
    })
    
    return doc


def run_tests():
    """Run all Daily Cash Balance tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDailyCashBalance)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    run_tests()
