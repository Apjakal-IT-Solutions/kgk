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
			"fieldname": "balance_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "name",
			"label": _("Balance ID"),
			"fieldtype": "Link",
			"options": "Daily Cash Balance",
			"width": 140
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80
		},
		{
			"fieldname": "total_manual_count",
			"label": _("Manual Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "total_manual_balance",
			"label": _("Manual Balance"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "erp_transaction_count",
			"label": _("ERP Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "erp_balance",
			"label": _("ERP Balance"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "variance_count",
			"label": _("Count Variance"),
			"fieldtype": "Int",
			"width": 110
		},
		{
			"fieldname": "variance_amount",
			"label": _("Amount Variance"),
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
			"width": 120
		},
		{
			"fieldname": "reconciliation_required",
			"label": _("Recon Required"),
			"fieldtype": "Check",
			"width": 120
		},
		{
			"fieldname": "reconciled_by",
			"label": _("Reconciled By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT 
			name,
			balance_date,
			currency,
			total_manual_count,
			total_manual_balance,
			erp_transaction_count,
			erp_balance,
			variance_count,
			variance_amount,
			variance_percentage,
			status,
			reconciliation_required,
			reconciled_by
		FROM `tabDaily Cash Balance`
		WHERE 1=1 {conditions}
		ORDER BY balance_date DESC
	"""
	
	return frappe.db.sql(query, filters, as_dict=True)

def get_conditions(filters):
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND balance_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND balance_date <= %(to_date)s"
	
	if filters.get("currency"):
		conditions += " AND currency = %(currency)s"
	
	if filters.get("status"):
		conditions += " AND status = %(status)s"
	
	if filters.get("reconciliation_required"):
		conditions += " AND reconciliation_required = %(reconciliation_required)s"
	
	if filters.get("variance_threshold"):
		threshold = flt(filters.get("variance_threshold"))
		conditions += f" AND ABS(variance_percentage) >= {threshold}"
	
	return conditions

def get_chart_data(data):
	# Create a line chart showing variance trends over time
	dates = []
	variance_amounts = []
	variance_percentages = []
	
	for d in reversed(data[-30:]):  # Last 30 days
		dates.append(str(d.balance_date))
		variance_amounts.append(flt(d.variance_amount))
		variance_percentages.append(flt(d.variance_percentage))
	
	chart_data = {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "Variance Amount",
					"values": variance_amounts,
					"chartType": "line"
				},
				{
					"name": "Variance %",
					"values": variance_percentages,
					"chartType": "line"
				}
			]
		},
		"type": "line",
		"height": 300,
		"lineOptions": {
			"regionFill": 1
		}
	}
	
	return chart_data

def get_summary(data):
	if not data:
		return []
	
	total_variances = len([d for d in data if flt(d.variance_amount) != 0])
	reconciliation_pending = len([d for d in data if d.reconciliation_required])
	avg_variance = sum([abs(flt(d.variance_amount)) for d in data]) / len(data) if data else 0
	max_variance = max([abs(flt(d.variance_amount)) for d in data]) if data else 0
	
	return [
		{
			"value": len(data),
			"indicator": "Blue",
			"label": _("Total Balance Records"),
			"datatype": "Int"
		},
		{
			"value": total_variances,
			"indicator": "Orange",
			"label": _("Records with Variance"),
			"datatype": "Int"
		},
		{
			"value": reconciliation_pending,
			"indicator": "Red",
			"label": _("Pending Reconciliation"),
			"datatype": "Int"
		},
		{
			"value": avg_variance,
			"indicator": "Yellow",
			"label": _("Average Variance"),
			"datatype": "Currency"
		},
		{
			"value": max_variance,
			"indicator": "Red",
			"label": _("Maximum Variance"),
			"datatype": "Currency"
		}
	]