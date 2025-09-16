# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart_data = get_chart_data(data)
	summary = get_summary(data)
	
	return columns, data, None, chart_data, summary

def get_columns():
	return [
		{
			"fieldname": "document_number",
			"label": _("Document Number"),
			"fieldtype": "Link",
			"options": "Cash Document",
			"width": 140
		},
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "transaction_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "party_type",
			"label": _("Party Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "created_by_user",
			"label": _("Created By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		},
		{
			"fieldname": "created_by_role",
			"label": _("Role"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 200
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			name as document_number,
			transaction_date,
			transaction_type,
			party_type,
			party,
			amount,
			currency,
			status,
			created_by_user,
			created_by_role,
			LEFT(description, 100) as description
		FROM `tabCash Document`
		WHERE 1=1 {conditions}
		ORDER BY transaction_date DESC, creation DESC
	"""
	
	return frappe.db.sql(query, filters, as_dict=True)

def get_conditions(filters):
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND transaction_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND transaction_date <= %(to_date)s"
	
	if filters.get("transaction_type"):
		conditions += " AND transaction_type = %(transaction_type)s"
	
	if filters.get("status"):
		conditions += " AND status = %(status)s"
	
	if filters.get("party_type"):
		conditions += " AND party_type = %(party_type)s"
	
	if filters.get("party"):
		conditions += " AND party = %(party)s"
	
	if filters.get("currency"):
		conditions += " AND currency = %(currency)s"
	
	if filters.get("created_by"):
		conditions += " AND created_by_user = %(created_by)s"
	
	return conditions

def get_chart_data(data):
	# Group by transaction type for pie chart
	payment_amount = sum([flt(d.amount) for d in data if d.transaction_type == "Payment"])
	receipt_amount = sum([flt(d.amount) for d in data if d.transaction_type == "Receipt"])
	
	chart_data = {
		"data": {
			"labels": ["Payments", "Receipts"],
			"datasets": [{
				"name": "Amount",
				"values": [payment_amount, receipt_amount]
			}]
		},
		"type": "pie",
		"height": 300
	}
	
	return chart_data

def get_summary(data):
	if not data:
		return []
	
	total_payments = sum([flt(d.amount) for d in data if d.transaction_type == "Payment"])
	total_receipts = sum([flt(d.amount) for d in data if d.transaction_type == "Receipt"])
	net_flow = total_receipts - total_payments
	
	return [
		{
			"value": len(data),
			"indicator": "Blue",
			"label": _("Total Documents"),
			"datatype": "Int"
		},
		{
			"value": total_payments,
			"indicator": "Red",
			"label": _("Total Payments"),
			"datatype": "Currency"
		},
		{
			"value": total_receipts,
			"indicator": "Green", 
			"label": _("Total Receipts"),
			"datatype": "Currency"
		},
		{
			"value": net_flow,
			"indicator": "Orange" if net_flow < 0 else "Green",
			"label": _("Net Cash Flow"),
			"datatype": "Currency"
		}
	]