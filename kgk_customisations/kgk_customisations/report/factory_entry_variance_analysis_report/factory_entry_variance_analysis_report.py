# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data)
	
	return columns, data, None, chart, summary

def get_columns():
	return [
		{
			"fieldname": "work_date",
			"label": _("Work Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee"),
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "factory_process",
			"label": _("Process"),
			"fieldtype": "Link",
			"options": "Factory Process",
			"width": 150
		},
		{
			"fieldname": "target",
			"label": _("Target"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "actual",
			"label": _("Actual"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "deviation",
			"label": _("Dev."),
			"fieldtype": "Float",
			"width": 150,
			"precision": 2
		},
		{
			"fieldname": "deviation_percentage",
			"label": _("Deviation %"),
			"fieldtype": "Percent",
			"width": 100,
			"precision": 0
		},
		{
			"fieldname": "variance",
			"label": _("Absolute Variance"),
			"fieldtype": "Float",
			"width": 130,
			"precision": 2
		},
		{
			"fieldname": "variance_percentage",
			"label": _("Variance %"),
			"fieldtype": "Percent",
			"width": 100,
			"precision": 0
		},
		{
			"fieldname": "reason",
			"label": _("Reason"),
			"fieldtype": "Link",
			"options": "Reason",
			"width": 120
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	query = """
		SELECT 
			fe.work_date,
			fei.employee,
			et.employee_name,
			fei.factory_process,
			CAST(fei.target AS DECIMAL(10,2)) as target,
			fei.actual,
			(fei.actual - CAST(fei.target AS DECIMAL(10,2))) as deviation,
			CASE 
				WHEN CAST(fei.target AS DECIMAL(10,2)) > 0 
				THEN ((fei.actual - CAST(fei.target AS DECIMAL(10,2))) * 100.0 / CAST(fei.target AS DECIMAL(10,2)))
				ELSE 0 
			END as deviation_percentage,
			ABS(fei.actual - CAST(fei.target AS DECIMAL(10,2))) as variance,
			CASE 
				WHEN CAST(fei.target AS DECIMAL(10,2)) > 0 
				THEN (ABS(fei.actual - CAST(fei.target AS DECIMAL(10,2))) * 100.0 / CAST(fei.target AS DECIMAL(10,2)))
				ELSE 0 
			END as variance_percentage,
			fei.reason
		FROM `tabFactory Entry` fe
		JOIN `tabFactory Entry Item` fei ON fei.parent = fe.name
		LEFT JOIN `tabEmployee Target` et ON et.name = fei.employee AND et.active = 1
		WHERE fe.docstatus < 2 {conditions}
		ORDER BY fe.work_date DESC, deviation ASC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Apply post-query filters
	if filters.get("negative_variance_only"):
		data = [d for d in data if d.get("deviation", 0) < 0]
	
	if filters.get("variance_threshold"):
		threshold = filters.get("variance_threshold")
		data = [d for d in data if abs(d.get("variance_percentage", 0)) > threshold]
	
	return data

def get_conditions(filters):
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND fe.work_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND fe.work_date <= %(to_date)s"
	
	if filters.get("section"):
		conditions += " AND fe.section = %(section)s"
	
	return conditions

def get_summary(data):
	if not data:
		return []
	
	negative_deviations = [d for d in data if d.get("deviation", 0) < 0]
	positive_deviations = [d for d in data if d.get("deviation", 0) > 0]
	
	total_deviation = sum(d.get("deviation", 0) for d in data)
	avg_variance = sum(d.get("variance", 0) for d in data) / len(data) if data else 0
	avg_variance_pct = sum(d.get("variance_percentage", 0) for d in data) / len(data) if data else 0
	
	return [
		{
			"value": len(data),
			"label": _("Records"),
			"datatype": "Int",
			"indicator": "Blue"
		},
		{
			"value": len(negative_deviations),
			"label": _("Underperform"),
			"datatype": "Int",
			"indicator": "Red"
		},
		{
			"value": len(positive_deviations),
			"label": _("Overperform"),
			"datatype": "Int",
			"indicator": "Green"
		},
		{
			"value": total_deviation,
			"label": _("Net Dev."),
			"datatype": "Float",
			"indicator": "Green" if total_deviation >= 0 else "Red"
		},
		{
			"value": avg_variance,
			"label": _("Avg. Abs. Var."),
			"datatype": "Float",
			"indicator": "Orange"
		},
		{
			"value": avg_variance_pct,
			"label": _("Avg. Var. %"),
			"datatype": "Percent",
			"indicator": "Orange"
		}
	]

def get_chart_data(data):
	if not data or len(data) == 0:
		return None
	
	# Group by date for variance trend
	date_deviation = {}
	for row in data:
		date = str(row.get("work_date"))
		if date not in date_deviation:
			date_deviation[date] = {"positive": 0, "negative": 0}
		
		deviation = row.get("deviation", 0)
		if deviation >= 0:
			date_deviation[date]["positive"] += deviation
		else:
			date_deviation[date]["negative"] += abs(deviation)
	
	dates = sorted(date_deviation.keys())
	
	return {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "+ Dev.",
					"values": [date_deviation[d]["positive"] for d in dates]
				},
				{
					"name": "- Dev.",
					"values": [date_deviation[d]["negative"] for d in dates]
				}
			]
		},
		"type": "line",
		"colors": ["#28a745", "#dc3545"],
		"height": 300,
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 1
		},
		"lineOptions": {
			"regionFill": 1
		}
	}
