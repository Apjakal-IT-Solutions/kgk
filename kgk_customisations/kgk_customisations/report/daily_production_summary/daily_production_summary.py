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
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "section",
			"label": _("Section"),
			"fieldtype": "Link",
			"options": "Section",
			"width": 120
		},
		{
			"fieldname": "type",
			"label": _("Type"),
			"fieldtype": "Data",
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
			"fieldname": "variance",
			"label": _("Variance"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "achievement",
			"label": _("Achievement %"),
			"fieldtype": "Percent",
			"width": 100
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
			fm.work_date,
			fmi.section,
			fmi.type,
			fmi.target,
			fmi.actual,
			(fmi.actual - fmi.target) as variance,
			CASE 
				WHEN fmi.target > 0 THEN (fmi.actual * 100.0 / fmi.target)
				ELSE 0 
			END as achievement,
			fmi.reason
		FROM `tabFactory Main` fm
		JOIN `tabFactory Main Item` fmi ON fmi.parent = fm.name
		WHERE fm.docstatus = 1 {conditions}
		ORDER BY fm.work_date DESC, fmi.section, fmi.type
	""".format(conditions=conditions)
	
	return frappe.db.sql(query, filters, as_dict=1)

def get_conditions(filters):
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND fm.work_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND fm.work_date <= %(to_date)s"
	
	if filters.get("section"):
		conditions += " AND fmi.section = %(section)s"
	
	if filters.get("type"):
		conditions += " AND fmi.type = %(type)s"
	
	return conditions

def get_summary(data):
	if not data:
		return []
	
	total_target = sum(d.get("target", 0) for d in data)
	total_actual = sum(d.get("actual", 0) for d in data)
	overall_achievement = (total_actual * 100.0 / total_target) if total_target > 0 else 0
	
	return [
		{
			"value": total_target,
			"label": _("Total Target"),
			"datatype": "Int",
			"indicator": "Blue"
		},
		{
			"value": total_actual,
			"label": _("Total Actual"),
			"datatype": "Int",
			"indicator": "Green" if total_actual >= total_target else "Orange"
		},
		{
			"value": overall_achievement,
			"label": _("Overall Achievement"),
			"datatype": "Percent",
			"indicator": "Green" if overall_achievement >= 100 else "Red"
		}
	]

def get_chart_data(data):
	if not data:
		return None
	
	# Group by date for trend chart
	date_data = {}
	for row in data:
		date = str(row.get("work_date"))
		if date not in date_data:
			date_data[date] = {"target": 0, "actual": 0}
		date_data[date]["target"] += row.get("target", 0)
		date_data[date]["actual"] += row.get("actual", 0)
	
	dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "Target",
					"values": [date_data[d]["target"] for d in dates]
				},
				{
					"name": "Actual",
					"values": [date_data[d]["actual"] for d in dates]
				}
			]
		},
		"type": "line",
		"colors": ["#ffa00a", "#28a745"]
	}
