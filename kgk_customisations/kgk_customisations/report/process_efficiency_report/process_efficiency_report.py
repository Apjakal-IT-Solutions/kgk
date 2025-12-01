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
			"fieldname": "factory_process",
			"label": _("Factory Process"),
			"fieldtype": "Link",
			"options": "Factory Process",
			"width": 200
		},
		{
			"fieldname": "total_employees_assigned",
			"label": _("Employees Assigned"),
			"fieldtype": "Int",
			"width": 180
		},
		{
			"fieldname": "total_target",
			"label": _("Target"),
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"fieldname": "total_actual",
			"label": _("Actual"),
			"fieldtype": "Float",
			"width": 120,
			"precision": 2
		},
		{
			"fieldname": "achievement",
			"label": _("Achievement %"),
			"fieldtype": "Percent",
			"width": 120,
			"precision": 0
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	query = """
		SELECT 
			fei.factory_process,
			COUNT(DISTINCT fei.employee) as total_employees_assigned,
			SUM(CAST(fei.target AS DECIMAL(10,2))) as total_target,
			SUM(fei.actual) as total_actual,
			CASE 
				WHEN SUM(CAST(fei.target AS DECIMAL(10,2))) > 0 
				THEN (SUM(fei.actual) * 100.0 / SUM(CAST(fei.target AS DECIMAL(10,2))))
				ELSE 0 
			END as achievement
		FROM `tabFactory Entry` fe
		JOIN `tabFactory Entry Item` fei ON fei.parent = fe.name
		WHERE fe.docstatus < 2 
			AND fei.factory_process IS NOT NULL 
			AND fei.factory_process != '' 
			{conditions}
		GROUP BY fei.factory_process
		ORDER BY achievement DESC
	""".format(conditions=conditions)
	
	return frappe.db.sql(query, filters, as_dict=1)

def get_conditions(filters):
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND fe.work_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND fe.work_date <= %(to_date)s"
	
	if filters.get("factory_process"):
		conditions += " AND fei.factory_process = %(factory_process)s"
	
	return conditions

def get_summary(data):
	if not data:
		return []
	
	total_employees = sum(d.get("total_employees_assigned", 0) for d in data)
	total_target = sum(d.get("total_target", 0) for d in data)
	total_actual = sum(d.get("total_actual", 0) for d in data)
	overall_achievement = (total_actual * 100.0 / total_target) if total_target > 0 else 0
	
	return [
		{
			"value": len(data),
			"label": _("Total Processes"),
			"datatype": "Int",
			"indicator": "Blue"
		},
		{
			"value": total_employees,
			"label": _("Total Employees"),
			"datatype": "Int",
			"indicator": "Gray"
		},
		{
			"value": total_target,
			"label": _("Total Target"),
			"datatype": "Float",
			"indicator": "Blue"
		},
		{
			"value": total_actual,
			"label": _("Total Actual"),
			"datatype": "Float",
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
	if not data or len(data) == 0:
		return None
	
	# Sort by achievement for better visualization
	processes_sorted = sorted(data, key=lambda x: x.get("achievement", 0), reverse=True)
	
	return {
		"data": {
			"labels": [d.get("factory_process") for d in processes_sorted],
			"datasets": [
				{
					"name": "Target",
					"values": [d.get("total_target", 0) for d in processes_sorted]
				},
				{
					"name": "Actual",
					"values": [d.get("total_actual", 0) for d in processes_sorted]
				}
			]
		},
		"type": "bar",
		"colors": ["#ffa00a", "#28a745"],
		"height": 300,
		"barOptions": {
			"stacked": 0
		},
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 1
		}
	}
