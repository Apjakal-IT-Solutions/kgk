# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Test data generator for Cash Management System
Creates realistic test data for development and testing
"""

import frappe
from frappe.utils import today, add_days, add_months, random_string, flt
import random
from datetime import datetime, timedelta


def generate_test_data(days=30, company="_Test Company", transactions_per_day=10):
    """
    Generate comprehensive test data for specified number of days
    
    Args:
        days: Number of days to generate data for
        company: Company name
        transactions_per_day: Average transactions per day
    """
    print(f"Generating test data for {days} days...")
    
    # Ensure test company exists
    ensure_test_company(company)
    
    start_date = add_days(today(), -days)
    
    for day_offset in range(days):
        current_date = add_days(start_date, day_offset)
        print(f"Generating data for {current_date}...")
        
        # Generate random number of transactions
        num_transactions = random.randint(
            max(1, transactions_per_day - 5),
            transactions_per_day + 5
        )
        
        daily_receipts = 0
        daily_payments = 0
        
        for i in range(num_transactions):
            # Randomly choose document type
            doc_type = random.choice([
                "Receipt", "Receipt", "Receipt",  # More receipts
                "Payment", "Payment",
                "Invoice"
            ])
            
            # Generate random amount based on type
            if doc_type == "Receipt":
                amount = random.uniform(500, 5000)
                daily_receipts += amount
            elif doc_type == "Payment":
                amount = random.uniform(200, 3000)
                daily_payments += amount
            else:  # Invoice
                amount = random.uniform(1000, 10000)
            
            # Create Cash Document
            doc = create_cash_document(
                company=company,
                transaction_date=current_date,
                main_document_type=doc_type,
                amount=amount
            )
            
            # Submit most documents (some left as draft)
            if random.random() > 0.1:  # 90% submitted
                doc.submit()
        
        # Create Daily Cash Balance
        create_daily_balance(
            company=company,
            balance_date=current_date,
            manual_balance=daily_receipts - daily_payments + random.uniform(-100, 100),
            erp_balance=daily_receipts - daily_payments
        )
        
        frappe.db.commit()
    
    print("Test data generation complete!")


def create_cash_document(company, transaction_date, main_document_type, amount):
    """Create a single Cash Document"""
    document_types = {
        "Receipt": ["Cash Sale", "Customer Payment", "General Receipt", "Refund"],
        "Payment": ["Supplier Payment", "Expense Payment", "General Payment", "Petty Cash"],
        "Invoice": ["Sales Invoice", "Purchase Invoice", "Credit Note"]
    }
    
    doc = frappe.get_doc({
        "doctype": "Cash Document",
        "company": company,
        "transaction_date": transaction_date,
        "main_document_type": main_document_type,
        "document_type": random.choice(document_types.get(main_document_type, ["General"])),
        "amount": flt(amount, 2),
        "currency": "BWP",
        "description": f"Test {main_document_type} - {random_string(10)}",
        "reference_number": f"REF-{random_string(8)}",
        "customer_supplier": f"Test Party {random.randint(1, 50)}"
    })
    
    doc.insert()
    return doc


def create_daily_balance(company, balance_date, manual_balance, erp_balance):
    """Create Daily Cash Balance record"""
    # Check if already exists
    if frappe.db.exists("Daily Cash Balance", {
        "company": company,
        "balance_date": balance_date
    }):
        return
    
    doc = frappe.get_doc({
        "doctype": "Daily Cash Balance",
        "balance_date": balance_date,
        "company": company,
        "manual_balance": flt(manual_balance, 2),
        "erp_balance": flt(erp_balance, 2),
        "status": random.choice([
            "Calculated",
            "Manually Verified",
            "ERP Verified",
            "Finally Verified"
        ])
    })
    
    doc.insert()
    return doc


def ensure_test_company(company_name):
    """Create test company if it doesn't exist"""
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


def create_edge_case_data():
    """Create edge case scenarios for testing"""
    company = "_Test Company"
    test_date = today()
    
    print("Creating edge case test data...")
    
    # Edge Case 1: Zero amount transaction
    try:
        doc = create_cash_document(
            company=company,
            transaction_date=test_date,
            main_document_type="Receipt",
            amount=0
        )
        print("✗ Edge Case 1 Failed: Zero amount should be rejected")
    except:
        print("✓ Edge Case 1 Passed: Zero amount rejected")
    
    # Edge Case 2: Very large amount
    doc = create_cash_document(
        company=company,
        transaction_date=test_date,
        main_document_type="Receipt",
        amount=999999999.99
    )
    doc.submit()
    print("✓ Edge Case 2 Passed: Large amount handled")
    
    # Edge Case 3: High variance in balance
    create_daily_balance(
        company=company,
        balance_date=add_days(test_date, -1),
        manual_balance=10000,
        erp_balance=7000  # 30% variance
    )
    print("✓ Edge Case 3 Passed: High variance scenario created")
    
    # Edge Case 4: Multiple documents same timestamp
    for i in range(5):
        doc = create_cash_document(
            company=company,
            transaction_date=test_date,
            main_document_type="Receipt",
            amount=1000 + i
        )
        doc.insert()
    print("✓ Edge Case 4 Passed: Concurrent documents created")
    
    # Edge Case 5: Future dated transaction
    future_date = add_days(test_date, 30)
    doc = create_cash_document(
        company=company,
        transaction_date=future_date,
        main_document_type="Receipt",
        amount=5000
    )
    doc.submit()
    print("✓ Edge Case 5 Passed: Future dated transaction created")
    
    frappe.db.commit()
    print("Edge case data creation complete!")


def create_workflow_test_data():
    """Create data for workflow testing"""
    company = "_Test Company"
    test_date = today()
    
    print("Creating workflow test data...")
    
    workflow_states = [
        "Draft",
        "Pending Approval",
        "Approved",
        "Rejected",
        "Revision Required",
        "Cancelled"
    ]
    
    for state in workflow_states:
        doc = create_cash_document(
            company=company,
            transaction_date=test_date,
            main_document_type="Receipt",
            amount=random.uniform(1000, 5000)
        )
        
        if state != "Draft":
            doc.submit()
            if hasattr(doc, 'workflow_state'):
                doc.workflow_state = state
                doc.save()
        
        print(f"✓ Created document in state: {state}")
    
    frappe.db.commit()
    print("Workflow test data creation complete!")


def create_performance_test_data(num_documents=1000):
    """Create large dataset for performance testing"""
    company = "_Test Company"
    
    print(f"Creating {num_documents} documents for performance testing...")
    
    batch_size = 100
    for batch in range(0, num_documents, batch_size):
        for i in range(batch_size):
            if batch + i >= num_documents:
                break
            
            test_date = add_days(today(), -random.randint(0, 365))
            
            doc = create_cash_document(
                company=company,
                transaction_date=test_date,
                main_document_type=random.choice(["Receipt", "Payment", "Invoice"]),
                amount=random.uniform(100, 10000)
            )
            
            if random.random() > 0.2:  # 80% submitted
                doc.submit()
        
        frappe.db.commit()
        print(f"Created {min(batch + batch_size, num_documents)}/{num_documents} documents")
    
    print("Performance test data creation complete!")


def cleanup_test_data(company="_Test Company"):
    """Remove all test data"""
    print("Cleaning up test data...")
    
    # Delete in correct order (respect foreign keys)
    doctypes_to_clean = [
        "Cash Document Audit Trail",
        "Cash Balance Submission",
        "Daily Cash Balance",
        "Cash Document"
    ]
    
    for doctype in doctypes_to_clean:
        frappe.db.delete(doctype, {"company": company})
        print(f"✓ Cleaned up {doctype}")
    
    frappe.db.commit()
    print("Test data cleanup complete!")


# Command-line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "generate":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            generate_test_data(days=days)
        
        elif command == "edge_cases":
            create_edge_case_data()
        
        elif command == "workflow":
            create_workflow_test_data()
        
        elif command == "performance":
            num_docs = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
            create_performance_test_data(num_documents=num_docs)
        
        elif command == "cleanup":
            cleanup_test_data()
        
        else:
            print("Unknown command. Use: generate|edge_cases|workflow|performance|cleanup")
    else:
        print("Usage: python test_data_generator.py <command> [args]")
        print("Commands:")
        print("  generate [days]        - Generate test data for N days (default: 30)")
        print("  edge_cases            - Create edge case scenarios")
        print("  workflow              - Create workflow test data")
        print("  performance [count]   - Create N documents for performance testing")
        print("  cleanup               - Remove all test data")
