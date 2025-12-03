# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, date_diff, nowdate


def execute(filters=None):
	"""
	Document Status Dashboard - Workflow state distribution and aging analysis
	"""
	if not filters:
		filters = {}
	
	view_type = filters.get("view_type", "Summary")
	
	if view_type == "Summary":
		columns = get_summary_columns()
		data = get_summary_data(filters)
	else:
		columns = get_detailed_columns()
		data = get_detailed_data(filters)
	
	chart = get_chart_data(filters)
	
	return columns, data, None, chart


def get_summary_columns():
	"""Columns for summary view"""
	return [
		{
			"fieldname": "workflow_state",
			"label": _("Workflow State"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "document_count",
			"label": _("Document Count"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "avg_aging_days",
			"label": _("Avg Aging (Days)"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "oldest_document",
			"label": _("Oldest Document"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "newest_document",
			"label": _("Newest Document"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "percentage",
			"label": _("% of Total"),
			"fieldtype": "Percent",
			"width": 100
		}
	]


def get_detailed_columns():
	"""Columns for detailed view"""
	return [
		{
			"fieldname": "document_name",
			"label": _("Document"),
			"fieldtype": "Link",
			"options": "Cash Document",
			"width": 150
		},
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 130
		},
		{
			"fieldname": "main_document_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "workflow_state",
			"label": _("Workflow State"),
			"fieldtype": "Data",
			"width": 130
		},
		{
			"fieldname": "assigned_to",
			"label": _("Assigned To"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "aging_days",
			"label": _("Aging (Days)"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "modified_by",
			"label": _("Modified By"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "modified",
			"label": _("Modified On"),
			"fieldtype": "Datetime",
			"width": 140
		}
	]


def get_summary_data(filters):
	"""Get workflow state summary"""
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			COALESCE(cd.workflow_state, 'Draft') as workflow_state,
			COUNT(*) as document_count,
			SUM(cd.amount) as total_amount,
			AVG(DATEDIFF(CURDATE(), cd.transaction_date)) as avg_aging_days,
			MIN(cd.transaction_date) as oldest_document,
			MAX(cd.transaction_date) as newest_document
		FROM `tabCash Document` cd
		WHERE cd.docstatus IN (0, 1)
		{conditions}
		GROUP BY cd.workflow_state
		ORDER BY document_count DESC
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Calculate percentages
	total_count = sum(row.get("document_count", 0) for row in data)
	for row in data:
		if total_count > 0:
			row["percentage"] = (flt(row.get("document_count", 0)) / total_count) * 100
		else:
			row["percentage"] = 0
	
	return data


def get_detailed_data(filters):
	"""Get detailed document list"""
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			cd.name as document_name,
			cd.transaction_date,
			cd.company,
			cd.main_document_type,
			cd.amount,
			COALESCE(cd.workflow_state, 'Draft') as workflow_state,
			cd.modified_by,
			cd.modified,
			DATEDIFF(CURDATE(), cd.transaction_date) as aging_days,
			(SELECT owner FROM `tabToDo` 
			 WHERE reference_type = 'Cash Document' 
			 AND reference_name = cd.name 
			 AND status = 'Open'
			 LIMIT 1) as assigned_to
		FROM `tabCash Document` cd
		WHERE cd.docstatus IN (0, 1)
		{conditions}
		ORDER BY cd.transaction_date DESC, cd.modified DESC
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build SQL WHERE conditions"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("cd.transaction_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("cd.transaction_date <= %(to_date)s")
	
	if filters.get("company"):
		conditions.append("cd.company = %(company)s")
	
	if filters.get("workflow_state") and filters.get("workflow_state") != "All":
		if filters.get("workflow_state") == "Draft":
			conditions.append("(cd.workflow_state IS NULL OR cd.workflow_state = 'Draft')")
		else:
			conditions.append("cd.workflow_state = %(workflow_state)s")
	
	if filters.get("assigned_to"):
		conditions.append("""
			cd.name IN (
				SELECT reference_name FROM `tabToDo` 
				WHERE reference_type = 'Cash Document' 
				AND owner = %(assigned_to)s
				AND status = 'Open'
			)
		""")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(filters):
	"""Generate pie chart for workflow state distribution"""
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			COALESCE(cd.workflow_state, 'Draft') as workflow_state,
			COUNT(*) as count
		FROM `tabCash Document` cd
		WHERE cd.docstatus IN (0, 1)
		{conditions}
		GROUP BY cd.workflow_state
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	if not data:
		return None
	
	labels = [row.get("workflow_state") for row in data]
	values = [row.get("count") for row in data]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Documents",
					"values": values
				}
			]
		},
		"type": "donut",
		"colors": ["#808080", "#ffa500", "#28a745", "#dc3545", "#007bff", "#6c757d"]
	}
	
	return chart
