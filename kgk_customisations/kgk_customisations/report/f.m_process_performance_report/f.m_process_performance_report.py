# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
import math

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_summary(data)
	return columns, data, None, chart, summary

def get_columns():
	return [
		{
			"fieldname": "factory_process",
			"fieldtype": "Link",
			"label": _("Factory Process"),
			"options": "Factory Process",
			"width": 300,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "target",
			"fieldtype": "Int",
			"label": _("Target"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "actual",
			"fieldtype": "Int",
			"label": _("Actual"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "diff",
			"fieldtype": "Int",
			"label": _("Diff"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "diff_percentage",
			"fieldtype": "Int",
			"label": _("Diff %"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		}
	]

def get_data(filters):
	if not filters:
		return []
		
	conditions = get_conditions(filters)
	
	# Get data from Factory Main and Factory Main Item
	data = frappe.db.sql(f"""
		SELECT 
			fmi.type as factory_process,
			SUM(CAST(fmi.target AS DECIMAL(10,2))) as target,
			SUM(fmi.actual) as actual
		FROM 
			`tabFactory Main` fm
		INNER JOIN 
			`tabFactory Main Item` fmi ON fm.name = fmi.parent
		WHERE 
			fm.docstatus < 2
			AND fmi.type IS NOT NULL 
			AND fmi.type != ''
			{conditions}
		GROUP BY 
			fmi.type
		ORDER BY 
			fmi.type
	""", filters, as_dict=1)
	
	# Calculate differences and percentages
	for row in data:
		target = math.ceil(flt(row.target))
		actual = math.ceil(flt(row.actual))
		row.target = target
		row.actual = actual
		row.diff = actual - target
		row.diff_percentage = math.ceil((row.diff / target * 100)) if target else 0
	
	return data

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("fm.work_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("fm.work_date <= %(to_date)s")
		
	if filters.get("department"):
		conditions.append("fm.section = %(department)s")
		
	if filters.get("factory_process"):
		conditions.append("fmi.type = %(factory_process)s")
		
	if filters.get("day_type") and filters.get("day_type") != "All":
		if filters.get("day_type") == "Normal":
			conditions.append("DAYOFWEEK(fm.work_date) NOT IN (1, 7)")  # Not Sunday or Saturday
		elif filters.get("day_type") == "Weekend":
			conditions.append("DAYOFWEEK(fm.work_date) IN (1, 7)")  # Sunday or Saturday
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data, filters):
	if not data:
		return None
	
	processes = []
	targets = []
	actuals = []
	
	for row in data:
		processes.append(row.factory_process or "Unknown")
		targets.append(math.ceil(flt(row.target)))
		actuals.append(math.ceil(flt(row.actual)))
	
	return {
		"data": {
			"labels": processes,
			"datasets": [
				{
					"name": "Target",
					"chartType": "bar",
					"values": targets,
					"color": "#FF6B6B"
				},
				{
					"name": "Actual",
					"chartType": "bar", 
					"values": actuals,
					"color": "#4ECDC4"
				}
			]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#FF6B6B", "#4ECDC4"]
	}

def get_summary(data):
	if not data:
		return []
	
	total_target = math.ceil(sum(flt(row["target"]) for row in data))
	total_actual = math.ceil(sum(flt(row["actual"]) for row in data))
	total_diff = total_actual - total_target
	total_diff_percentage = math.ceil((total_diff / total_target * 100)) if total_target else 0
	
	# Count processes with positive and negative variance
	positive_processes = len([row for row in data if flt(row["diff"]) > 0])
	negative_processes = len([row for row in data if flt(row["diff"]) < 0])
	
	return [
		{
			"value": len(data),
			"label": "Total Processes",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_target,
			"label": "Total Target",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_actual,
			"label": "Total Actual",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_diff,
			"label": "Overall Difference",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green" if total_diff >= 0 else "Red"
		},
		{
			"value": total_diff_percentage,
			"label": "Overall Performance",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green" if total_diff_percentage >= 0 else "Red"
		},
		{
			"value": positive_processes,
			"label": "Above Target",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green"
		},
		{
			"value": negative_processes,
			"label": "Below Target",
			"datatype": "Int",
			"currency": None,
			"indicator": "Red"
		}
	]
