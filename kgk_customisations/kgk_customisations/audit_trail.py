# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Audit Trail Utilities for Cash Management System
Logs all critical operations for compliance and tracking
"""

import frappe
from frappe.utils import now_datetime, get_datetime
import json


class AuditTrail:
	"""Centralized audit trail logging for cash management operations"""
	
	@staticmethod
	def log_balance_update(document_name, balance_name, operation, amount, user=None):
		"""
		Log balance update operations
		
		Args:
			document_name: Name of the Cash Document
			balance_name: Name of the Daily Cash Balance
			operation: "update" or "reverse"
			amount: Amount updated
			user: User performing the operation (default: current user)
		"""
		try:
			user = user or frappe.session.user
			
			log_entry = frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Daily Cash Balance",
				"reference_name": balance_name,
				"content": f"""
				<strong>Balance {operation.capitalize()}</strong><br>
				Document: {document_name}<br>
				Amount: {amount}<br>
				User: {user}<br>
				Timestamp: {now_datetime()}
				""",
				"comment_by": user
			})
			log_entry.insert(ignore_permissions=True)
			
			frappe.logger().info(f"Audit: Balance {operation} - {document_name} → {balance_name} by {user}")
			
		except Exception as e:
			frappe.log_error(f"Audit trail logging failed: {str(e)}", "Audit Trail Error")
	
	@staticmethod
	def log_verification(submission_name, verification_level, balance, user=None):
		"""
		Log verification operations in Cash Balance Submission
		
		Args:
			submission_name: Name of the Cash Balance Submission
			verification_level: "basic", "checker", or "accountant"
			balance: Submitted balance amount
			user: User performing verification
		"""
		try:
			user = user or frappe.session.user
			
			log_entry = frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Cash Balance Submission",
				"reference_name": submission_name,
				"content": f"""
				<strong>{verification_level.capitalize()} Verification</strong><br>
				Balance: {balance}<br>
				Verified By: {user}<br>
				Timestamp: {now_datetime()}
				""",
				"comment_by": user
			})
			log_entry.insert(ignore_permissions=True)
			
			frappe.logger().info(f"Audit: {verification_level} verification - {submission_name} by {user}")
			
		except Exception as e:
			frappe.log_error(f"Audit trail logging failed: {str(e)}", "Audit Trail Error")
	
	@staticmethod
	def log_workflow_change(document_name, doctype, old_status, new_status, user=None):
		"""
		Log workflow status changes
		
		Args:
			document_name: Name of the document
			doctype: DocType name
			old_status: Previous status
			new_status: New status
			user: User performing the change
		"""
		try:
			user = user or frappe.session.user
			
			log_entry = frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Workflow",
				"reference_doctype": doctype,
				"reference_name": document_name,
				"content": f"""
				<strong>Status Change</strong><br>
				From: {old_status}<br>
				To: {new_status}<br>
				Changed By: {user}<br>
				Timestamp: {now_datetime()}
				""",
				"comment_by": user
			})
			log_entry.insert(ignore_permissions=True)
			
			frappe.logger().info(f"Audit: Workflow change - {doctype} {document_name}: {old_status} → {new_status} by {user}")
			
		except Exception as e:
			frappe.log_error(f"Audit trail logging failed: {str(e)}", "Audit Trail Error")
	
	@staticmethod
	def log_reconciliation(balance_name, reconciliation_type, notes, user=None):
		"""
		Log reconciliation operations
		
		Args:
			balance_name: Name of the Daily Cash Balance
			reconciliation_type: "manual" or "automatic"
			notes: Reconciliation notes
			user: User performing reconciliation
		"""
		try:
			user = user or frappe.session.user
			
			log_entry = frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Daily Cash Balance",
				"reference_name": balance_name,
				"content": f"""
				<strong>{reconciliation_type.capitalize()} Reconciliation</strong><br>
				Notes: {notes}<br>
				Reconciled By: {user}<br>
				Timestamp: {now_datetime()}
				""",
				"comment_by": user
			})
			log_entry.insert(ignore_permissions=True)
			
			frappe.logger().info(f"Audit: {reconciliation_type} reconciliation - {balance_name} by {user}")
			
		except Exception as e:
			frappe.log_error(f"Audit trail logging failed: {str(e)}", "Audit Trail Error")
	
	@staticmethod
	def log_invoice_generation(document_name, invoice_number, document_type, user=None):
		"""
		Log invoice number generation
		
		Args:
			document_name: Name of the Cash Document
			invoice_number: Generated invoice number
			document_type: Document type
			user: User generating the invoice
		"""
		try:
			user = user or frappe.session.user
			
			log_entry = frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Cash Document",
				"reference_name": document_name,
				"content": f"""
				<strong>Invoice Number Generated</strong><br>
				Invoice Number: {invoice_number}<br>
				Document Type: {document_type}<br>
				Generated By: {user}<br>
				Timestamp: {now_datetime()}
				""",
				"comment_by": user
			})
			log_entry.insert(ignore_permissions=True)
			
			frappe.logger().info(f"Audit: Invoice generated - {invoice_number} for {document_name} by {user}")
			
		except Exception as e:
			frappe.log_error(f"Audit trail logging failed: {str(e)}", "Audit Trail Error")
	
	@staticmethod
	def log_variance_alert(balance_name, variance_amount, variance_percentage):
		"""
		Log variance alerts when threshold is exceeded
		
		Args:
			balance_name: Name of the Daily Cash Balance
			variance_amount: Variance amount
			variance_percentage: Variance percentage
		"""
		try:
			log_entry = frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Daily Cash Balance",
				"reference_name": balance_name,
				"content": f"""
				<strong>Variance Alert</strong><br>
				Variance Amount: {variance_amount}<br>
				Variance Percentage: {variance_percentage}%<br>
				Threshold Exceeded<br>
				Timestamp: {now_datetime()}
				""",
				"comment_by": "Administrator"
			})
			log_entry.insert(ignore_permissions=True)
			
			frappe.logger().warning(f"Audit: Variance alert - {balance_name}: {variance_amount} ({variance_percentage}%)")
			
		except Exception as e:
			frappe.log_error(f"Audit trail logging failed: {str(e)}", "Audit Trail Error")
	
	@staticmethod
	def get_audit_trail(doctype, document_name, limit=50):
		"""
		Retrieve audit trail for a document
		
		Args:
			doctype: DocType name
			document_name: Document name
			limit: Maximum number of entries to retrieve
			
		Returns:
			list: List of audit trail entries
		"""
		try:
			comments = frappe.get_all(
				"Comment",
				filters={
					"reference_doctype": doctype,
					"reference_name": document_name,
					"comment_type": ["in", ["Info", "Workflow"]]
				},
				fields=["content", "comment_by", "creation", "comment_type"],
				order_by="creation desc",
				limit=limit
			)
			
			return comments
			
		except Exception as e:
			frappe.log_error(f"Audit trail retrieval failed: {str(e)}", "Audit Trail Error")
			return []
	
	@staticmethod
	def export_audit_trail(doctype, document_name, format="json"):
		"""
		Export audit trail in specified format
		
		Args:
			doctype: DocType name
			document_name: Document name
			format: Export format ("json" or "html")
			
		Returns:
			str: Formatted audit trail
		"""
		try:
			trail = AuditTrail.get_audit_trail(doctype, document_name, limit=1000)
			
			if format == "json":
				return json.dumps(trail, indent=2, default=str)
			
			elif format == "html":
				html = f"<h3>Audit Trail: {doctype} - {document_name}</h3>"
				html += "<table border='1' cellpadding='5' cellspacing='0'>"
				html += "<tr><th>Timestamp</th><th>User</th><th>Type</th><th>Details</th></tr>"
				
				for entry in trail:
					html += f"""
					<tr>
						<td>{entry.creation}</td>
						<td>{entry.comment_by}</td>
						<td>{entry.comment_type}</td>
						<td>{entry.content}</td>
					</tr>
					"""
				
				html += "</table>"
				return html
			
			else:
				return str(trail)
				
		except Exception as e:
			frappe.log_error(f"Audit trail export failed: {str(e)}", "Audit Trail Error")
			return None
