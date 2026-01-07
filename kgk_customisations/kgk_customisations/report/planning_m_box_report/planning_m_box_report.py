# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days
from datetime import datetime


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Working Date"),
			"fieldname": "working_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Employee Name"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Factory Code"),
			"fieldname": "factory_code",
			"fieldtype": "Link",
			"options": "Factory Code",
			"width": 120
		},
		{
			"label": _("X-Ray Done"),
			"fieldname": "x_ray_done",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Reason"),
			"fieldname": "reason",
			"fieldtype": "Link",
			"options": "Reason",
			"width": 150
		},
		{
			"label": _("Status"),
			"fieldname": "docstatus_label",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Document"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Planning M-Box",
			"width": 150
		}
	]


def get_data(filters):
	"""Fetch data from Planning M-Box and child table"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT 
			pmb.working_date,
			pmbi.employee_name,
			pmbi.factory_code,
			pmbi.x_ray_done,
			pmbi.reason,
			pmb.docstatus,
			pmb.name
		FROM `tabPlanning M-Box` pmb
		LEFT JOIN `tabPlanning M-Box Item` pmbi 
			ON pmbi.parent = pmb.name
		WHERE 1=1
			{conditions}
		ORDER BY pmb.working_date DESC, pmbi.employee_name
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Add docstatus label
	for row in data:
		if row.get("docstatus") == 0:
			row["docstatus_label"] = "Draft"
		elif row.get("docstatus") == 1:
			row["docstatus_label"] = "Submitted"
		elif row.get("docstatus") == 2:
			row["docstatus_label"] = "Cancelled"
		else:
			row["docstatus_label"] = "Unknown"
	
	return data


def get_conditions(filters):
	"""Build WHERE clause conditions"""
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND pmb.working_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND pmb.working_date <= %(to_date)s"
	
	if filters.get("employee_name"):
		conditions += " AND pmbi.employee_name = %(employee_name)s"
	
	if filters.get("factory_code"):
		conditions += " AND pmbi.factory_code = %(factory_code)s"
	
	# Handle docstatus filter
	docstatus_filter = filters.get("docstatus", "Submitted")
	if docstatus_filter == "Draft":
		conditions += " AND pmb.docstatus = 0"
	elif docstatus_filter == "Submitted":
		conditions += " AND pmb.docstatus = 1"
	elif docstatus_filter == "All":
		conditions += " AND pmb.docstatus < 2"  # Exclude cancelled
	
	return conditions


def get_chart_data(data, filters):
	"""Generate chart data based on selected chart view"""
	if not data:
		return None
	
	chart_view = filters.get("chart_view", "Daily X-Ray Trend")
	
	if chart_view == "Daily X-Ray Trend":
		return get_daily_trend_chart(data)
	elif chart_view == "Employee Performance Ranking":
		return get_employee_ranking_chart(data)
	elif chart_view == "Factory Code Comparison":
		return get_factory_comparison_chart(data)
	elif chart_view == "Reason Analysis":
		return get_reason_analysis_chart(data)
	elif chart_view == "Weekly Aggregate":
		return get_weekly_aggregate_chart(data)
	elif chart_view == "Employee Daily Activity":
		return get_employee_activity_chart(data)
	
	return None


def get_daily_trend_chart(data):
	"""Chart 1: Daily X-Ray Trend - Line chart showing daily production"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("working_date"))
		x_ray = row.get("x_ray_done", 0)
		
		if date in date_data:
			date_data[date] += x_ray
		else:
			date_data[date] = x_ray
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Total X-Ray Done",
					"values": [date_data[d] for d in sorted_dates]
				}
			]
		},
		"type": "line",
		"colors": ["#2196F3"]
	}


def get_employee_ranking_chart(data):
	"""Chart 2: Employee Performance Ranking - Bar chart showing top performers"""
	# Group by employee
	employee_data = {}
	for row in data:
		employee = row.get("employee_name") or "Unknown"
		x_ray = row.get("x_ray_done", 0)
		
		if employee in employee_data:
			employee_data[employee] += x_ray
		else:
			employee_data[employee] = x_ray
	
	# Sort and get top 10
	sorted_employees = sorted(employee_data.items(), key=lambda x: x[1], reverse=True)[:10]
	
	if not sorted_employees:
		return None
	
	return {
		"data": {
			"labels": [e[0] for e in sorted_employees],
			"datasets": [
				{
					"name": "Total X-Ray Done",
					"values": [e[1] for e in sorted_employees]
				}
			]
		},
		"type": "bar",
		"colors": ["#4CAF50"]
	}


def get_factory_comparison_chart(data):
	"""Chart 3: Factory Code Comparison - Bar chart showing productivity by factory"""
	# Group by factory
	factory_data = {}
	for row in data:
		factory = row.get("factory_code") or "Unknown"
		x_ray = row.get("x_ray_done", 0)
		
		if factory in factory_data:
			factory_data[factory] += x_ray
		else:
			factory_data[factory] = x_ray
	
	# Sort by total
	sorted_factories = sorted(factory_data.items(), key=lambda x: x[1], reverse=True)
	
	if not sorted_factories:
		return None
	
	return {
		"data": {
			"labels": [f[0] for f in sorted_factories],
			"datasets": [
				{
					"name": "Total X-Ray Done",
					"values": [f[1] for f in sorted_factories]
				}
			]
		},
		"type": "bar",
		"colors": ["#FF9800"]
	}


def get_reason_analysis_chart(data):
	"""Chart 4: Reason Analysis - Pie chart showing distribution of reasons"""
	# Group by reason
	reason_data = {}
	for row in data:
		reason = row.get("reason") or "No Reason"
		
		if reason in reason_data:
			reason_data[reason] += 1
		else:
			reason_data[reason] = 1
	
	# Sort by count
	sorted_reasons = sorted(reason_data.items(), key=lambda x: x[1], reverse=True)
	
	if not sorted_reasons:
		return None
	
	return {
		"data": {
			"labels": [r[0] for r in sorted_reasons],
			"datasets": [
				{
					"name": "Reason Count",
					"values": [r[1] for r in sorted_reasons]
				}
			]
		},
		"type": "pie",
		"colors": ["#F44336", "#9C27B0", "#00BCD4", "#FFEB3B", "#795548", "#607D8B"]
	}


def get_weekly_aggregate_chart(data):
	"""Chart 5: Weekly Aggregate - Bar chart showing weekly totals"""
	# Group by week
	week_data = {}
	
	for row in data:
		date = row.get("working_date")
		if date:
			# Get week number
			week_num = datetime.strptime(str(date), "%Y-%m-%d").isocalendar()[1]
			year = datetime.strptime(str(date), "%Y-%m-%d").year
			week_key = f"{year}-W{week_num:02d}"
			
			x_ray = row.get("x_ray_done", 0)
			
			if week_key in week_data:
				week_data[week_key] += x_ray
			else:
				week_data[week_key] = x_ray
	
	# Sort by week
	sorted_weeks = sorted(week_data.keys())
	
	if not sorted_weeks:
		return None
	
	return {
		"data": {
			"labels": sorted_weeks,
			"datasets": [
				{
					"name": "Weekly X-Ray Done",
					"values": [week_data[w] for w in sorted_weeks]
				}
			]
		},
		"type": "bar",
		"colors": ["#9C27B0"]
	}


def get_employee_activity_chart(data):
	"""Chart 6: Employee Daily Activity - Shows individual employee patterns"""
	# Group by employee and calculate stats
	employee_stats = {}
	
	for row in data:
		employee = row.get("employee_name") or "Unknown"
		x_ray = row.get("x_ray_done", 0)
		
		if employee not in employee_stats:
			employee_stats[employee] = {"total": 0, "count": 0, "days": set()}
		
		employee_stats[employee]["total"] += x_ray
		employee_stats[employee]["count"] += 1
		employee_stats[employee]["days"].add(str(row.get("working_date")))
	
	# Calculate averages and get top 10
	employee_averages = []
	for employee, stats in employee_stats.items():
		if stats["count"] > 0:
			avg = stats["total"] / len(stats["days"])
			employee_averages.append((employee, avg, stats["total"], len(stats["days"])))
	
	# Sort by total and get top 10
	sorted_employees = sorted(employee_averages, key=lambda x: x[2], reverse=True)[:10]
	
	if not sorted_employees:
		return None
	
	return {
		"data": {
			"labels": [e[0] for e in sorted_employees],
			"datasets": [
				{
					"name": "Daily Average",
					"values": [round(e[1], 1) for e in sorted_employees],
					"chartType": "bar"
				},
				{
					"name": "Total Production",
					"values": [e[2] for e in sorted_employees],
					"chartType": "line"
				}
			]
		},
		"type": "axis-mixed",
		"colors": ["#00BCD4", "#FF5722"]
	}
