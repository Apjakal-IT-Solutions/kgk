# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Test suite for Cash Document functionality
Tests invoice generation, balance updates, workflow, and validations
"""

import frappe
import unittest
from frappe.utils import today, add_days, nowdate, flt
from kgk_customisations.kgk_customisations.doctype.cash_document.cash_document import (
    generate_invoice_number,
    update_daily_balance
)


class TestCashDocument(unittest.TestCase):
    """Test cases for Cash Document DocType"""
    
    def setUp(self):
        """Set up test data before each test"""
        self.company = create_test_company()
        self.test_date = today()
        
        # Clean up any existing test documents
        frappe.db.delete("Cash Document", {
            "company": self.company,
            "transaction_date": self.test_date
        })
        frappe.db.commit()
    
    def tearDown(self):
        """Clean up after each test"""
        frappe.db.rollback()
    
    def test_invoice_number_generation(self):
        """Test atomic invoice number generation"""
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
            main_document_type="Payment",
            amount=500
        )
        doc2.insert()
        
        # Verify invoice numbers are sequential
        self.assertIsNotNone(doc1.invoice_number)
        self.assertIsNotNone(doc2.invoice_number)
        
        # Extract numbers from format: COMPANY-YYYYMMDD-XXXX
        num1 = int(doc1.invoice_number.split('-')[-1])
        num2 = int(doc2.invoice_number.split('-')[-1])
        
        self.assertEqual(num2, num1 + 1, "Invoice numbers should be sequential")
    
    def test_invoice_number_uniqueness(self):
        """Test that invoice numbers are unique across documents"""
        docs = []
        for i in range(5):
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=self.test_date,
                main_document_type="Receipt",
                amount=100 * (i + 1)
            )
            doc.insert()
            docs.append(doc)
        
        invoice_numbers = [doc.invoice_number for doc in docs]
        unique_numbers = set(invoice_numbers)
        
        self.assertEqual(len(invoice_numbers), len(unique_numbers), 
                        "All invoice numbers should be unique")
    
    def test_company_name_auto_population(self):
        """Test automatic company name population from code"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        
        # Verify company name is populated
        self.assertIsNotNone(doc.company_name)
        self.assertTrue(len(doc.company_name) > 0)
    
    def test_year_auto_population(self):
        """Test automatic year field population from transaction date"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        
        expected_year = str(frappe.utils.getdate(self.test_date).year)
        self.assertEqual(doc.year, expected_year)
    
    def test_file_suffix_assignment(self):
        """Test automatic file suffix assignment"""
        # Create multiple documents
        for i in range(3):
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=self.test_date,
                main_document_type="Receipt",
                amount=100 * (i + 1)
            )
            doc.insert()
        
        # Verify file suffixes are assigned
        docs = frappe.get_all("Cash Document", 
            filters={
                "company": self.company,
                "transaction_date": self.test_date
            },
            fields=["name", "file_suffix"],
            order_by="creation asc"
        )
        
        for idx, doc_data in enumerate(docs):
            expected_suffix = f"{idx + 1:03d}"
            self.assertEqual(doc_data.file_suffix, expected_suffix,
                           f"File suffix should be {expected_suffix}")
    
    def test_balance_update_on_submit(self):
        """Test that daily balance is updated when document is submitted"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=5000
        )
        doc.insert()
        doc.submit()
        
        # Check if daily balance record exists
        balance = frappe.get_all("Daily Cash Balance",
            filters={
                "balance_date": self.test_date,
                "company": self.company
            },
            fields=["erp_balance", "status"]
        )
        
        self.assertTrue(len(balance) > 0, "Daily balance should be created")
        self.assertEqual(balance[0].status, "Calculated")
    
    def test_workflow_state_transitions(self):
        """Test workflow state transitions"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        
        # Initial state should be Draft or Pending Approval
        self.assertIn(doc.workflow_state, [None, "Draft", "Pending Approval"])
        
        # Simulate approval (if workflow is configured)
        if hasattr(doc, 'workflow_state'):
            doc.workflow_state = "Approved"
            doc.save()
            self.assertEqual(doc.workflow_state, "Approved")
    
    def test_amount_validation(self):
        """Test that amount must be positive"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=-1000  # Negative amount
        )
        
        with self.assertRaises(frappe.exceptions.ValidationError):
            doc.insert()
    
    def test_document_type_validation(self):
        """Test document type field validation"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        
        # Verify main_document_type is set correctly
        self.assertIn(doc.main_document_type, ["Receipt", "Payment", "Invoice"])
    
    def test_concurrent_invoice_generation(self):
        """Test invoice number generation under concurrent requests"""
        import threading
        
        results = []
        errors = []
        
        def create_doc():
            try:
                doc = create_test_cash_document(
                    company=self.company,
                    transaction_date=self.test_date,
                    main_document_type="Receipt",
                    amount=1000
                )
                doc.insert()
                frappe.db.commit()
                results.append(doc.invoice_number)
            except Exception as e:
                errors.append(str(e))
        
        # Create 10 documents concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_doc)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Verify all invoice numbers are unique
        self.assertEqual(len(results), len(set(results)), 
                        "All invoice numbers should be unique in concurrent scenario")
    
    def test_audit_trail_creation(self):
        """Test that audit trail is created for document operations"""
        doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        
        # Check for audit trail entry
        audit_entries = frappe.get_all("Cash Document Audit Trail",
            filters={
                "document_name": doc.name,
                "activity_type": "Document Creation"
            }
        )
        
        self.assertTrue(len(audit_entries) > 0, "Audit trail should be created")
    
    def test_balance_recalculation(self):
        """Test balance recalculation with multiple documents"""
        # Create multiple documents
        amounts = [1000, 500, 750]
        for amount in amounts:
            doc = create_test_cash_document(
                company=self.company,
                transaction_date=self.test_date,
                main_document_type="Receipt",
                amount=amount
            )
            doc.insert()
            doc.submit()
        
        # Get daily balance
        balance = frappe.get_value("Daily Cash Balance",
            {
                "balance_date": self.test_date,
                "company": self.company
            },
            "erp_balance"
        )
        
        expected_balance = sum(amounts)
        self.assertEqual(flt(balance), flt(expected_balance),
                        "Balance should equal sum of all receipts")


def create_test_company():
    """Create or get test company"""
    company_name = "_Test Company"
    
    if not frappe.db.exists("Company", company_name):
        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": company_name,
            "abbr": "_TC",
            "default_currency": "BWP",
            "country": "Botswana"
        })
        company.insert(ignore_permissions=True)
        frappe.db.commit()
    
    return company_name


def create_test_cash_document(**kwargs):
    """Helper function to create test Cash Document"""
    doc = frappe.get_doc({
        "doctype": "Cash Document",
        "company": kwargs.get("company", "_Test Company"),
        "transaction_date": kwargs.get("transaction_date", today()),
        "main_document_type": kwargs.get("main_document_type", "Receipt"),
        "document_type": kwargs.get("document_type", "General Receipt"),
        "amount": kwargs.get("amount", 1000),
        "currency": kwargs.get("currency", "BWP"),
        "description": kwargs.get("description", "Test transaction")
    })
    
    return doc


def run_tests():
    """Run all Cash Document tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCashDocument)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    run_tests()
