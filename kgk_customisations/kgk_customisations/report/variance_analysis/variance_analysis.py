# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, add_days


def execute(filters=None):
	"""
	Variance Analysis Report - Compare manual vs ERP balances with drill-down capability
	"""
	if not filters:
		filters = {}
	
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns(filters):
	"""Define report columns"""
	columns = [
		{
			"fieldname": "balance_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150
		},
		{
			"fieldname": "manual_balance",
			"label": _("Manual Balance"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "erp_balance",
			"label": _("ERP Balance"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "variance_amount",
			"label": _("Variance Amount"),
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
			"width": 130
		},
		{
			"fieldname": "verified_by",
			"label": _("Verified By"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "verification_time",
			"label": _("Verification Time"),
			"fieldtype": "Datetime",
			"width": 140
		},
		{
			"fieldname": "documents_count",
			"label": _("Document Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		}
	]
	
	return columns


def get_data(filters):
	"""Fetch variance analysis data"""
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			dcb.balance_date,
			dcb.company,
			dcb.manual_balance,
			dcb.erp_balance,
			dcb.variance_amount,
			dcb.variance_percentage,
			dcb.status,
			dcb.verified_by,
			dcb.verification_time,
			dcb.remarks,
			(SELECT COUNT(*) 
			 FROM `tabCash Document` cd 
			 WHERE cd.transaction_date = dcb.balance_date 
			 AND cd.docstatus = 1
			 {' AND cd.company = dcb.company' if filters.get('company') else ''}
			) as documents_count
		FROM `tabDaily Cash Balance` dcb
		WHERE dcb.docstatus = 1
		{conditions}
		ORDER BY dcb.balance_date DESC, dcb.company
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Apply variance type filtering
	variance_type = filters.get("variance_type", "All")
	variance_threshold = flt(filters.get("variance_threshold", 0))
	
	filtered_data = []
	for row in data:
		variance_pct = flt(row.get("variance_percentage", 0))
		
		if variance_type == "Positive Only" and variance_pct <= 0:
			continue
		elif variance_type == "Negative Only" and variance_pct >= 0:
			continue
		elif variance_type == "Above Threshold" and abs(variance_pct) < variance_threshold:
			continue
		
		filtered_data.append(row)
	
	return filtered_data


def get_conditions(filters):
	"""Build SQL WHERE conditions"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("dcb.balance_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("dcb.balance_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("dcb.company = %(company)s")
	
	if filters.get("status") and filters.get("status") != "All":
		conditions.append("dcb.status = %(status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate trend chart for variance analysis"""
	if not data:
		return None
	
	# Prepare data for line chart showing variance trend
	labels = []
	variance_amounts = []
	variance_percentages = []
	
	for row in data:
		label = f"{row.get('balance_date')} - {row.get('company', 'N/A')}"
		labels.append(label)
		variance_amounts.append(flt(row.get("variance_amount", 0)))
		variance_percentages.append(flt(row.get("variance_percentage", 0)))
	
	# Reverse to show chronological order
	labels.reverse()
	variance_amounts.reverse()
	variance_percentages.reverse()
	
	chart = {
		"data": {
			"labels": labels[:30],  # Limit to last 30 entries for readability
			"datasets": [
				{
					"name": "Variance Amount",
					"values": variance_amounts[:30],
					"chartType": "line"
				},
				{
					"name": "Variance %",
					"values": variance_percentages[:30],
					"chartType": "line"
				}
			]
		},
		"type": "line",
		"colors": ["#ff6384", "#36a2eb"],
		"axisOptions": {
			"xIsSeries": 1
		},
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart
