# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	
	return columns, data, None, chart

def get_columns():
	return [
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "employee",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee Target",
			"width": 140
		},
		{
			"fieldname": "section",
			"label": _("Section"),
			"fieldtype": "Link",
			"options": "Section",
			"width": 120
		},
		{
			"fieldname": "total_days_worked",
			"label": _("Total Days Worked"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "total_target",
			"label": _("Total Target"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "total_actual",
			"label": _("Total Actual"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "average_daily_output",
			"label": _("Average Daily Output"),
			"fieldtype": "Float",
			"width": 140,
			"precision": 2
		},
		{
			"fieldname": "achievement",
			"label": _("Achievement %"),
			"fieldtype": "Percent",
			"width": 110
		},
		{
			"fieldname": "trend",
			"label": _("Trend"),
			"fieldtype": "Data",
			"width": 80
		}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	
	# Main query to get employee performance aggregates
	query = """
		SELECT 
			fei.employee,
			et.employee_name,
			fe.section,
			COUNT(DISTINCT fe.work_date) as total_days_worked,
			SUM(CAST(fei.target AS DECIMAL(10,2))) as total_target,
			SUM(fei.actual) as total_actual,
			AVG(fei.actual) as average_daily_output,
			CASE 
				WHEN SUM(CAST(fei.target AS DECIMAL(10,2))) > 0 
				THEN (SUM(fei.actual) * 100.0 / SUM(CAST(fei.target AS DECIMAL(10,2))))
				ELSE 0 
			END as achievement
		FROM `tabFactory Entry` fe
		JOIN `tabFactory Entry Item` fei ON fei.parent = fe.name
		LEFT JOIN `tabEmployee Target` et ON et.name = fei.employee
		WHERE fe.docstatus < 2 {conditions}
		GROUP BY fei.employee, et.employee_name, fe.section
		ORDER BY achievement DESC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Calculate trend for each employee
	for row in data:
		row['trend'] = calculate_trend(row['employee'], filters)
	
	# Apply min_achievement filter if specified
	if filters.get("min_achievement"):
		data = [d for d in data if d.get("achievement", 0) >= filters.get("min_achievement")]
	
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

def calculate_trend(employee, filters):
	"""Calculate if employee performance is improving, declining, or stable"""
	if not filters.get("from_date") or not filters.get("to_date"):
		return ""
	
	# Split the date range into two halves
	from datetime import datetime, timedelta
	
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	
	if isinstance(from_date, str):
		from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
	if isinstance(to_date, str):
		to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
	
	total_days = (to_date - from_date).days
	if total_days < 2:
		return "→"
	
	mid_date = from_date + timedelta(days=total_days // 2)
	
	# Get first half performance
	first_half = frappe.db.sql("""
		SELECT 
			CASE 
				WHEN SUM(CAST(fei.target AS DECIMAL(10,2))) > 0 
				THEN (SUM(fei.actual) * 100.0 / SUM(CAST(fei.target AS DECIMAL(10,2))))
				ELSE 0 
			END as achievement
		FROM `tabFactory Entry` fe
		JOIN `tabFactory Entry Item` fei ON fei.parent = fe.name
		WHERE fe.docstatus < 2 
			AND fei.employee = %(employee)s
			AND fe.work_date >= %(from_date)s
			AND fe.work_date < %(mid_date)s
	""", {"employee": employee, "from_date": from_date, "mid_date": mid_date}, as_dict=1)
	
	# Get second half performance
	second_half = frappe.db.sql("""
		SELECT 
			CASE 
				WHEN SUM(CAST(fei.target AS DECIMAL(10,2))) > 0 
				THEN (SUM(fei.actual) * 100.0 / SUM(CAST(fei.target AS DECIMAL(10,2))))
				ELSE 0 
			END as achievement
		FROM `tabFactory Entry` fe
		JOIN `tabFactory Entry Item` fei ON fei.parent = fe.name
		WHERE fe.docstatus < 2 
			AND fei.employee = %(employee)s
			AND fe.work_date >= %(mid_date)s
			AND fe.work_date <= %(to_date)s
	""", {"employee": employee, "mid_date": mid_date, "to_date": to_date}, as_dict=1)
	
	if not first_half or not second_half:
		return "→"
	
	first_achievement = first_half[0].get("achievement", 0) or 0
	second_achievement = second_half[0].get("achievement", 0) or 0
	
	# Calculate trend with threshold of 5% difference
	diff = second_achievement - first_achievement
	if diff > 5:
		return "↑"
	elif diff < -5:
		return "↓"
	else:
		return "→"

def get_chart_data(data):
	if not data or len(data) == 0:
		return None
	
	# Show all employees in the filtered data (not just top 10)
	employees_sorted = sorted(data, key=lambda x: x.get("achievement", 0), reverse=True)
	
	return {
		"data": {
			"labels": [d.get("employee_name") or d.get("employee") for d in employees_sorted],
			"datasets": [
				{
					"name": "Achievement %",
					"values": [d.get("achievement", 0) for d in employees_sorted]
				}
			]
		},
		"type": "bar",
		"colors": ["#28a745"],
		"height": 300,
		"barOptions": {
			"stacked": 0
		},
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 1
		},
		"lineOptions": {
			"regionFill": 1
		}
	}
