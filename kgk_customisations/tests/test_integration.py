# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Integration tests for workflow and business processes
Tests complete user journeys and system interactions
"""

import frappe
import unittest
from frappe.utils import today, add_days, flt, now
from kgk_customisations.tests.test_cash_document import create_test_cash_document, create_test_company
from kgk_customisations.tests.test_daily_cash_balance import create_test_balance


class TestWorkflowIntegration(unittest.TestCase):
    """Integration tests for workflow processes"""
    
    def setUp(self):
        """Set up test environment"""
        self.company = create_test_company()
        self.test_date = today()
        
        # Clean up
        frappe.db.delete("Cash Document Audit Trail", {"company": self.company})
        frappe.db.delete("Daily Cash Balance", {"company": self.company})
        frappe.db.delete("Cash Document", {"company": self.company})
        frappe.db.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        frappe.db.rollback()
    
    def test_end_to_end_receipt_workflow(self):
        """Test complete receipt workflow from creation to verification"""
        # Step 1: Create receipt
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=5000
        )
        doc.insert()
        
        # Verify invoice number assigned
        self.assertIsNotNone(doc.invoice_number)
        
        # Step 2: Submit document
        doc.submit()
        self.assertEqual(doc.docstatus, 1)
        
        # Step 3: Verify balance updated
        balance = frappe.get_doc("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": self.company
        })
        self.assertEqual(flt(balance.erp_balance), 5000)
        
        # Step 4: Manual verification
        balance.status = "Manually Verified"
        balance.verified_by = frappe.session.user
        balance.verification_time = now()
        balance.save()
        
        # Step 5: ERP verification
        balance.status = "ERP Verified"
        balance.save()
        
        # Step 6: Final verification
        balance.status = "Finally Verified"
        balance.save()
        
        # Verify audit trail exists
        audit_count = frappe.db.count("Cash Document Audit Trail", {
            "document_name": doc.name
        })
        self.assertGreater(audit_count, 0)
    
    def test_balance_reconciliation_workflow(self):
        """Test daily balance reconciliation process"""
        # Create multiple transactions
        transactions = [
            ("Receipt", 10000),
            ("Receipt", 5000),
            ("Payment", 3000),
            ("Payment", 2000),
            ("Invoice", 8000)
        ]
        
        for doc_type, amount in transactions:
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=self.test_date,
                main_document_type=doc_type,
                amount=amount
            )
            doc.insert()
            doc.submit()
        
        # Calculate expected balance
        expected_balance = 10000 + 5000 - 3000 - 2000
        
        # Get balance
        balance = frappe.get_doc("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": self.company
        })
        
        # Verify calculation
        self.assertEqual(flt(balance.erp_balance), expected_balance)
        
        # Set manual balance (with small variance)
        balance.manual_balance = expected_balance + 50
        balance.save()
        
        # Verify variance calculated
        self.assertEqual(flt(balance.variance_amount), 50)
    
    def test_document_cancellation_workflow(self):
        """Test document cancellation and balance adjustment"""
        # Create and submit document
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=3000
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
        
        # Verify balance updated
        balance.reload()
        self.assertEqual(flt(balance.erp_balance), initial_balance - 3000)
        
        # Verify audit trail
        audit = frappe.get_all("Cash Document Audit Trail", {
            "document_name": doc.name,
            "activity_type": "Document Cancellation"
        })
        self.assertTrue(len(audit) > 0)
    
    def test_multi_company_workflow(self):
        """Test workflow with multiple companies"""
        company2 = "_Test Company 2"
        
        # Create second company if needed
        if not frappe.db.exists("Company", company2):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": company2,
                "abbr": "_TC2",
                "default_currency": "BWP",
                "country": "Botswana"
            }).insert(ignore_permissions=True)
        
        # Create documents for both companies
        doc1 = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=5000
        )
        doc1.insert()
        doc1.submit()
        
        doc2 = create_test_cash_document(
            company=company2,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=7000
        )
        doc2.insert()
        doc2.submit()
        
        # Verify separate balances
        balance1 = frappe.get_value("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": self.company
        }, "erp_balance")
        
        balance2 = frappe.get_value("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": company2
        }, "erp_balance")
        
        self.assertEqual(flt(balance1), 5000)
        self.assertEqual(flt(balance2), 7000)
    
    def test_scheduled_tasks_workflow(self):
        """Test scheduled task execution"""
        # This would test the actual scheduled tasks
        # For now, we'll test the underlying functions
        
        from kgk_customisations.tasks import (
            update_all_daily_balances,
            check_unverified_balances
        )
        
        # Create test data
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        doc.submit()
        
        # Run scheduled task
        try:
            update_all_daily_balances()
            # If no exception, task executed successfully
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Scheduled task failed: {str(e)}")
    
    def test_report_generation_workflow(self):
        """Test report generation with data"""
        # Create test data
        for i in range(5):
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=add_days(self.test_date, -i),
                main_document_type="Receipt",
                amount=1000 * (i + 1)
            )
            doc.insert()
            doc.submit()
        
        # Test Daily Cash Summary report
        from kgk_customisations.kgk_customisations.report.daily_cash_summary.daily_cash_summary import execute
        
        filters = {
            "from_date": add_days(self.test_date, -7),
            "to_date": self.test_date,
            "company": self.company
        }
        
        columns, data, message, chart = execute(filters)
        
        # Verify report generated
        self.assertIsNotNone(columns)
        self.assertTrue(len(data) > 0)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error conditions"""
    
    def setUp(self):
        """Set up test environment"""
        self.company = create_test_company()
        self.test_date = today()
    
    def tearDown(self):
        """Clean up"""
        frappe.db.rollback()
    
    def test_negative_amount_validation(self):
        """Test that negative amounts are rejected"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=-1000
        )
        
        with self.assertRaises(Exception):
            doc.insert()
    
    def test_duplicate_invoice_number_prevention(self):
        """Test prevention of duplicate invoice numbers"""
        doc1 = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc1.insert()
        
        doc2 = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=2000
        )
        doc2.insert()
        
        # Verify different invoice numbers
        self.assertNotEqual(doc1.invoice_number, doc2.invoice_number)
    
    def test_future_date_handling(self):
        """Test handling of future dates"""
        future_date = add_days(today(), 30)
        
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=future_date,
            main_document_type="Receipt",
            amount=1000
        )
        
        # Should allow future dates
        doc.insert()
        self.assertEqual(doc.transaction_date, future_date)
    
    def test_large_amount_handling(self):
        """Test handling of very large amounts"""
        large_amount = 999999999.99
        
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=large_amount
        )
        doc.insert()
        doc.submit()
        
        # Verify amount preserved
        self.assertEqual(flt(doc.amount), flt(large_amount))


def run_integration_tests():
    """Run all integration tests"""
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWorkflowIntegration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEdgeCases))
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    run_integration_tests()
