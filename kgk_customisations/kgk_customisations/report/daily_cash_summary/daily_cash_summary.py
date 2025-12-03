# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt


def execute(filters=None):
	"""
	Daily Cash Summary Report
	Shows receipts, payments, and balances by company and date
	"""
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns(filters):
	"""Define report columns"""
	group_by = filters.get("group_by", "Date")
	
	columns = []
	
	if group_by == "Date":
		columns.append({
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		})
	
	if group_by in ["Company", "Date"]:
		columns.append({
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		})
	
	if group_by == "Document Type":
		columns.append({
			"fieldname": "main_document_type",
			"label": _("Document Type"),
			"fieldtype": "Data",
			"width": 120
		})
	
	columns.extend([
		{
			"fieldname": "opening_balance",
			"label": _("Opening Balance"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "total_receipts",
			"label": _("Total Receipts"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "receipt_count",
			"label": _("Receipt Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_payments",
			"label": _("Total Payments"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "payment_count",
			"label": _("Payment Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_invoices",
			"label": _("Total Invoices"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "invoice_count",
			"label": _("Invoice Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "closing_balance",
			"label": _("Closing Balance"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "variance",
			"label": _("Variance"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "variance_percentage",
			"label": _("Variance %"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		}
	])
	
	return columns


def get_data(filters):
	"""Fetch report data"""
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	currency = filters.get("currency", "BWP")
	group_by = filters.get("group_by", "Date")
	
	# Build base query
	conditions = ["cd.transaction_date BETWEEN %(from_date)s AND %(to_date)s"]
	conditions.append("cd.docstatus = 1")  # Only submitted documents
	conditions.append("cd.currency = %(currency)s")
	
	if company:
		conditions.append("cd.company = %(company)s")
	
	where_clause = " AND ".join(conditions)
	
	if group_by == "Date":
		group_clause = "cd.transaction_date, cd.company"
		select_clause = "cd.transaction_date, cd.company"
	elif group_by == "Company":
		group_clause = "cd.company"
		select_clause = "cd.company, NULL as transaction_date"
	else:  # Document Type
		group_clause = "cd.main_document_type"
		select_clause = "cd.main_document_type, NULL as transaction_date, NULL as company"
	
	# Get cash document summaries
	query = f"""
		SELECT 
			{select_clause},
			SUM(CASE WHEN cd.main_document_type = 'Receipt' THEN cd.amount ELSE 0 END) as total_receipts,
			SUM(CASE WHEN cd.main_document_type = 'Receipt' THEN 1 ELSE 0 END) as receipt_count,
			SUM(CASE WHEN cd.main_document_type = 'Payment' THEN cd.amount ELSE 0 END) as total_payments,
			SUM(CASE WHEN cd.main_document_type = 'Payment' THEN 1 ELSE 0 END) as payment_count,
			SUM(CASE WHEN cd.main_document_type = 'Invoice' THEN cd.amount ELSE 0 END) as total_invoices,
			SUM(CASE WHEN cd.main_document_type = 'Invoice' THEN 1 ELSE 0 END) as invoice_count,
			SUM(CASE WHEN cd.main_document_type = 'Petty Cash' THEN cd.amount ELSE 0 END) as total_petty_cash
		FROM `tabCash Document` cd
		WHERE {where_clause}
		GROUP BY {group_clause}
		ORDER BY {select_clause}
	"""
	
	cash_data = frappe.db.sql(query, {
		"from_date": from_date,
		"to_date": to_date,
		"company": company,
		"currency": currency
	}, as_dict=1)
	
	# Enhance with balance data
	data = []
	for row in cash_data:
		# Calculate closing balance
		opening_balance = get_opening_balance(row, from_date, filters)
		closing_balance = opening_balance + flt(row.total_receipts) + flt(row.total_invoices) - flt(row.total_payments) - flt(row.total_petty_cash)
		
		# Get variance from Daily Cash Balance if exists
		variance = 0
		variance_percentage = 0
		status = "Calculated"
		
		if group_by == "Date" and row.get("transaction_date") and row.get("company"):
			balance_doc = frappe.db.get_value(
				"Daily Cash Balance",
				{
					"balance_date": row.transaction_date,
					"company": row.company
				},
				["variance_amount", "variance_percentage", "status"],
				as_dict=1
			)
			
			if balance_doc:
				variance = flt(balance_doc.variance_amount)
				variance_percentage = flt(balance_doc.variance_percentage)
				status = balance_doc.status
		
		data.append({
			"transaction_date": row.get("transaction_date"),
			"company": row.get("company"),
			"main_document_type": row.get("main_document_type"),
			"opening_balance": opening_balance,
			"total_receipts": flt(row.total_receipts),
			"receipt_count": row.receipt_count,
			"total_payments": flt(row.total_payments),
			"payment_count": row.payment_count,
			"total_invoices": flt(row.total_invoices),
			"invoice_count": row.invoice_count,
			"closing_balance": closing_balance,
			"variance": variance,
			"variance_percentage": variance_percentage,
			"status": status
		})
	
	return data


def get_opening_balance(row, from_date, filters):
	"""Calculate opening balance for the period"""
	# For simplicity, return 0 for now
	# In production, this should fetch previous day's closing balance
	return 0


def get_chart_data(data, filters):
	"""Generate chart data"""
	if not data:
		return None
	
	group_by = filters.get("group_by", "Date")
	
	if group_by == "Date":
		labels = [row.get("transaction_date").strftime("%Y-%m-%d") if row.get("transaction_date") else "" for row in data]
	elif group_by == "Company":
		labels = [row.get("company") for row in data]
	else:
		labels = [row.get("main_document_type") for row in data]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Receipts",
					"values": [row.get("total_receipts", 0) for row in data]
				},
				{
					"name": "Payments",
					"values": [row.get("total_payments", 0) for row in data]
				},
				{
					"name": "Invoices",
					"values": [row.get("total_invoices", 0) for row in data]
				}
			]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#28a745", "#dc3545", "#007bff"]
	}
	
	return chart
