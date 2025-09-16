# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def get_notification_config():
    """Return notification configuration for cash management"""
    
    return {
        "for_doctype": {
            "Cash Document": {
                "status": "status",
                "conditions": [
                    {
                        "document_type": "Cash Document",
                        "subject": "New Cash Document: {document_number}",
                        "condition": "doc.status == 'Draft'",
                        "message": "A new cash document has been created and needs review.",
                        "recipients": ["role:Cash Checker", "role:Cash Accountant"],
                        "channel": "email"
                    },
                    {
                        "document_type": "Cash Document", 
                        "subject": "Cash Document Approved: {document_number}",
                        "condition": "doc.status == 'Approved'",
                        "message": "Cash document has been approved and is ready for processing.",
                        "recipients": ["role:Cash Accountant", "role:Cash Super User"],
                        "channel": "system"
                    },
                    {
                        "document_type": "Cash Document",
                        "subject": "Cash Document Rejected: {document_number}",
                        "condition": "doc.status == 'Rejected'",
                        "message": "Cash document has been rejected. Please review and make necessary changes.",
                        "recipients": ["eval:doc.created_by_user"],
                        "channel": "email"
                    }
                ]
            },
            "Daily Cash Balance": {
                "status": "status",
                "conditions": [
                    {
                        "document_type": "Daily Cash Balance",
                        "subject": "High Variance Detected: {balance_date}",
                        "condition": "abs(doc.variance_percentage or 0) > 10",
                        "message": "Daily cash balance shows high variance. Reconciliation required.",
                        "recipients": ["role:Cash Accountant", "role:Cash Super User"],
                        "channel": "system"
                    },
                    {
                        "document_type": "Daily Cash Balance",
                        "subject": "Reconciliation Required: {balance_date}",
                        "condition": "doc.reconciliation_required == 1",
                        "message": "Daily cash balance requires reconciliation due to variance.",
                        "recipients": ["role:Cash Accountant", "role:Cash Super User"],
                        "channel": "email"
                    }
                ]
            }
        }
    }

def send_daily_variance_alerts():
    """Send alerts for unreconciled balances - to be called by scheduled task"""
    
    # Get all unreconciled balances from last 7 days
    from frappe.utils import add_days, today
    
    unreconciled_balances = frappe.db.sql("""
        SELECT name, balance_date, variance_amount, variance_percentage
        FROM `tabDaily Cash Balance`
        WHERE reconciliation_required = 1
        AND balance_date >= %s
        AND balance_date <= %s
        ORDER BY balance_date DESC
    """, (add_days(today(), -7), today()), as_dict=True)
    
    if unreconciled_balances:
        # Create alert for accountants and super users
        recipients = frappe.get_users_for_role("Cash Accountant") + frappe.get_users_for_role("Cash Super User")
        
        message = f"""
        <h3>Daily Cash Balance Alert</h3>
        <p>The following cash balances require reconciliation:</p>
        <table border="1" cellpadding="5">
        <tr><th>Date</th><th>Variance Amount</th><th>Variance %</th></tr>
        """
        
        for balance in unreconciled_balances:
            message += f"""
            <tr>
            <td>{balance.balance_date}</td>
            <td>{frappe.format(balance.variance_amount, {'fieldtype': 'Currency'})}</td>
            <td>{balance.variance_percentage:.2f}%</td>
            </tr>
            """
        
        message += "</table><p>Please review and reconcile these balances.</p>"
        
        for user in set(recipients):
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": "Cash Balance Reconciliation Alert",
                "email_content": message,
                "for_user": user,
                "type": "Alert"
            }).insert(ignore_permissions=True)
        
        frappe.db.commit()
        
        return f"Sent alerts for {len(unreconciled_balances)} unreconciled balances to {len(set(recipients))} users"
    
    return "No unreconciled balances found"

def send_weekly_cash_summary():
    """Send weekly cash flow summary - to be called by scheduled task"""
    
    from frappe.utils import add_days, today
    
    # Get cash documents from last week
    week_start = add_days(today(), -7)
    
    cash_summary = frappe.db.sql("""
        SELECT 
            transaction_type,
            COUNT(*) as count,
            SUM(amount) as total_amount,
            currency
        FROM `tabCash Document`
        WHERE transaction_date >= %s
        AND transaction_date <= %s
        GROUP BY transaction_type, currency
        ORDER BY currency, transaction_type
    """, (week_start, today()), as_dict=True)
    
    if cash_summary:
        # Create summary message
        message = f"""
        <h3>Weekly Cash Flow Summary ({week_start} to {today()})</h3>
        <table border="1" cellpadding="5">
        <tr><th>Type</th><th>Count</th><th>Amount</th><th>Currency</th></tr>
        """
        
        for summary in cash_summary:
            message += f"""
            <tr>
            <td>{summary.transaction_type}</td>
            <td>{summary.count}</td>
            <td>{frappe.format(summary.total_amount, {'fieldtype': 'Currency'})}</td>
            <td>{summary.currency}</td>
            </tr>
            """
        
        message += "</table>"
        
        # Send to accountants and super users
        recipients = frappe.get_users_for_role("Cash Accountant") + frappe.get_users_for_role("Cash Super User")
        
        for user in set(recipients):
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": "Weekly Cash Flow Summary",
                "email_content": message,
                "for_user": user,
                "type": "Alert"
            }).insert(ignore_permissions=True)
        
        frappe.db.commit()
        
        return f"Sent weekly summary to {len(set(recipients))} users"
    
    return "No cash transactions found for the week"