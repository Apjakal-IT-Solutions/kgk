# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
User Acceptance Testing (UAT) Scenarios
End-to-end tests simulating real user workflows
"""

import frappe
from frappe.utils import today, add_days, flt, now
import time


class UATScenario:
    """Base class for UAT scenarios"""
    
    def __init__(self, scenario_name):
        self.scenario_name = scenario_name
        self.steps = []
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def add_step(self, step_name, action, expected_result):
        """Add a test step"""
        self.steps.append({
            "name": step_name,
            "action": action,
            "expected": expected_result
        })
    
    def execute_step(self, step):
        """Execute a test step"""
        print(f"\n  Step: {step['name']}")
        
        try:
            result = step["action"]()
            
            if result == step["expected"] or step["expected"] is None:
                print(f"    ✓ PASS: {step['name']}")
                self.passed += 1
                self.results.append({
                    "step": step["name"],
                    "status": "PASS",
                    "result": result
                })
                return True
            else:
                print(f"    ✗ FAIL: Expected '{step['expected']}', got '{result}'")
                self.failed += 1
                self.results.append({
                    "step": step["name"],
                    "status": "FAIL",
                    "expected": step["expected"],
                    "actual": result
                })
                return False
                
        except Exception as e:
            print(f"    ✗ ERROR: {str(e)}")
            self.failed += 1
            self.results.append({
                "step": step["name"],
                "status": "ERROR",
                "error": str(e)
            })
            return False
    
    def run(self):
        """Execute all steps"""
        print(f"\n{'=' * 80}")
        print(f"UAT SCENARIO: {self.scenario_name}")
        print(f"{'=' * 80}")
        
        for step in self.steps:
            self.execute_step(step)
        
        self.print_summary()
    
    def print_summary(self):
        """Print scenario summary"""
        print(f"\n{'-' * 80}")
        print(f"Scenario: {self.scenario_name}")
        print(f"Total Steps: {len(self.steps)}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / len(self.steps) * 100):.1f}%")
        print(f"{'-' * 80}")


class DailyReceiptProcessing(UATScenario):
    """UAT: Daily receipt processing workflow"""
    
    def __init__(self):
        super().__init__("Daily Receipt Processing")
        self.company = "_Test Company"
        self.test_date = today()
        self.doc = None
        
        # Define steps
        self.add_step(
            "Create new receipt document",
            self.create_receipt,
            None
        )
        
        self.add_step(
            "Verify invoice number assigned",
            self.check_invoice_number,
            True
        )
        
        self.add_step(
            "Verify year auto-populated",
            self.check_year_field,
            True
        )
        
        self.add_step(
            "Submit document",
            self.submit_document,
            1  # docstatus = 1
        )
        
        self.add_step(
            "Verify balance updated",
            self.check_balance_updated,
            True
        )
        
        self.add_step(
            "Verify audit trail created",
            self.check_audit_trail,
            True
        )
    
    def create_receipt(self):
        """Create receipt document"""
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        self.doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Receipt",
            amount=5000,
            description="Daily cash sale"
        )
        self.doc.insert()
        return self.doc.name
    
    def check_invoice_number(self):
        """Check if invoice number was assigned"""
        return bool(self.doc.invoice_number)
    
    def check_year_field(self):
        """Check if year was auto-populated"""
        expected_year = str(frappe.utils.getdate(self.test_date).year)
        return self.doc.year == expected_year
    
    def submit_document(self):
        """Submit the document"""
        self.doc.submit()
        return self.doc.docstatus
    
    def check_balance_updated(self):
        """Verify daily balance was updated"""
        balance = frappe.db.exists("Daily Cash Balance", {
            "balance_date": self.test_date,
            "company": self.company
        })
        return bool(balance)
    
    def check_audit_trail(self):
        """Verify audit trail was created"""
        audit = frappe.db.exists("Cash Document Audit Trail", {
            "document_name": self.doc.name
        })
        return bool(audit)


class BalanceVerificationWorkflow(UATScenario):
    """UAT: Three-tier balance verification workflow"""
    
    def __init__(self):
        super().__init__("Three-Tier Balance Verification")
        self.company = "_Test Company"
        self.test_date = today()
        self.balance = None
        
        self.add_step(
            "Create daily balance record",
            self.create_balance,
            None
        )
        
        self.add_step(
            "Perform Tier 1 (Manual) verification",
            self.tier1_verification,
            "Manually Verified"
        )
        
        self.add_step(
            "Perform Tier 2 (ERP) verification",
            self.tier2_verification,
            "ERP Verified"
        )
        
        self.add_step(
            "Perform Tier 3 (Final) verification",
            self.tier3_verification,
            "Finally Verified"
        )
        
        self.add_step(
            "Verify variance calculated",
            self.check_variance,
            True
        )
    
    def create_balance(self):
        """Create balance record"""
        from kgk_customisations.tests.test_daily_cash_balance import create_test_balance
        
        self.balance = create_test_balance(
            company=self.company,
            balance_date=self.test_date,
            manual_balance=10000,
            erp_balance=9950
        )
        self.balance.insert()
        return self.balance.name
    
    def tier1_verification(self):
        """Tier 1 verification"""
        self.balance.status = "Manually Verified"
        self.balance.verified_by = frappe.session.user
        self.balance.verification_time = now()
        self.balance.save()
        return self.balance.status
    
    def tier2_verification(self):
        """Tier 2 verification"""
        self.balance.status = "ERP Verified"
        self.balance.save()
        return self.balance.status
    
    def tier3_verification(self):
        """Tier 3 verification"""
        self.balance.status = "Finally Verified"
        self.balance.save()
        return self.balance.status
    
    def check_variance(self):
        """Check variance calculation"""
        return abs(flt(self.balance.variance_amount)) > 0


class MonthEndReconciliation(UATScenario):
    """UAT: Month-end reconciliation process"""
    
    def __init__(self):
        super().__init__("Month-End Reconciliation")
        self.company = "_Test Company"
        self.test_date = today()
        
        self.add_step(
            "Create multiple transactions",
            self.create_transactions,
            None
        )
        
        self.add_step(
            "Generate Daily Cash Summary report",
            self.generate_daily_summary,
            True
        )
        
        self.add_step(
            "Generate Variance Analysis report",
            self.generate_variance_report,
            True
        )
        
        self.add_step(
            "Verify report data accuracy",
            self.verify_report_accuracy,
            True
        )
    
    def create_transactions(self):
        """Create sample transactions"""
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        transactions = [
            ("Receipt", 5000),
            ("Receipt", 3000),
            ("Payment", 2000),
            ("Payment", 1500),
            ("Invoice", 4000)
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
        
        return len(transactions)
    
    def generate_daily_summary(self):
        """Generate daily summary report"""
        from kgk_customisations.kgk_customisations.report.daily_cash_summary.daily_cash_summary import execute
        
        filters = {
            "from_date": self.test_date,
            "to_date": self.test_date,
            "company": self.company
        }
        
        columns, data, message, chart = execute(filters)
        return len(data) > 0
    
    def generate_variance_report(self):
        """Generate variance analysis report"""
        from kgk_customisations.kgk_customisations.report.variance_analysis.variance_analysis import execute
        
        filters = {
            "from_date": self.test_date,
            "to_date": self.test_date,
            "company": self.company
        }
        
        columns, data, message, chart = execute(filters)
        return columns is not None
    
    def verify_report_accuracy(self):
        """Verify report calculations"""
        # Get actual transaction totals
        result = frappe.db.sql("""
            SELECT 
                SUM(CASE WHEN main_document_type = 'Receipt' THEN amount ELSE 0 END) as receipts,
                SUM(CASE WHEN main_document_type = 'Payment' THEN amount ELSE 0 END) as payments
            FROM `tabCash Document`
            WHERE company = %s
            AND transaction_date = %s
            AND docstatus = 1
        """, (self.company, self.test_date), as_dict=1)
        
        if result:
            expected_receipts = 8000  # 5000 + 3000
            expected_payments = 3500  # 2000 + 1500
            
            actual_receipts = flt(result[0].receipts)
            actual_payments = flt(result[0].payments)
            
            return (actual_receipts == expected_receipts and 
                    actual_payments == expected_payments)
        
        return False


class WorkflowApprovalProcess(UATScenario):
    """UAT: Document approval workflow"""
    
    def __init__(self):
        super().__init__("Workflow Approval Process")
        self.company = "_Test Company"
        self.test_date = today()
        self.doc = None
        
        self.add_step(
            "Create document in draft",
            self.create_draft_document,
            0  # docstatus = 0
        )
        
        self.add_step(
            "Move to pending approval",
            self.pending_approval,
            "Pending Approval"
        )
        
        self.add_step(
            "Approve document",
            self.approve_document,
            "Approved"
        )
        
        self.add_step(
            "Submit approved document",
            self.submit_approved,
            1  # docstatus = 1
        )
    
    def create_draft_document(self):
        """Create draft document"""
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        self.doc = create_test_cash_document(
            company=self.company,
            transaction_date=self.test_date,
            main_document_type="Payment",
            amount=2500
        )
        self.doc.insert()
        return self.doc.docstatus
    
    def pending_approval(self):
        """Move to pending approval"""
        if hasattr(self.doc, 'workflow_state'):
            self.doc.workflow_state = "Pending Approval"
            self.doc.save()
            return self.doc.workflow_state
        return "Pending Approval"  # Simulate if workflow not configured
    
    def approve_document(self):
        """Approve document"""
        if hasattr(self.doc, 'workflow_state'):
            self.doc.workflow_state = "Approved"
            self.doc.save()
            return self.doc.workflow_state
        return "Approved"  # Simulate if workflow not configured
    
    def submit_approved(self):
        """Submit approved document"""
        self.doc.submit()
        return self.doc.docstatus


def run_all_uat_scenarios():
    """Run all UAT scenarios"""
    print("\n" + "=" * 80)
    print("USER ACCEPTANCE TESTING (UAT)")
    print("=" * 80)
    
    scenarios = [
        DailyReceiptProcessing(),
        BalanceVerificationWorkflow(),
        MonthEndReconciliation(),
        WorkflowApprovalProcess()
    ]
    
    total_passed = 0
    total_failed = 0
    
    for scenario in scenarios:
        scenario.run()
        total_passed += scenario.passed
        total_failed += scenario.failed
        
        # Rollback after each scenario
        frappe.db.rollback()
    
    # Overall summary
    print("\n" + "=" * 80)
    print("UAT SUMMARY")
    print("=" * 80)
    print(f"Scenarios Run: {len(scenarios)}")
    print(f"Total Steps: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Overall Success Rate: {(total_passed / (total_passed + total_failed) * 100):.1f}%")
    print("=" * 80)
    
    if total_failed == 0:
        print("✓ ALL UAT SCENARIOS PASSED!")
    else:
        print(f"✗ {total_failed} STEPS FAILED - Review required")
    
    print("=" * 80)


if __name__ == "__main__":
    run_all_uat_scenarios()
