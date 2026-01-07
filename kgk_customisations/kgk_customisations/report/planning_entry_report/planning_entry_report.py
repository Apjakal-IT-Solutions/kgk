# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	"""
	Generate Planning Entry Report
	Shows employee performance: target vs actual with variance analysis
	"""
	
	if not filters:
		filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns():
	"""
	Define report columns for Planning Entry analysis
	"""
	return [
		{
			"fieldname": "working_date",
			"label": _("Working Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "employee_code",
			"label": _("Emp Code"),
			"fieldtype": "Data",
			"width": 90
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "target",
			"label": _("Target"),
			"fieldtype": "Float",
			"width": 90,
			"precision": 2
		},
		{
			"fieldname": "actual",
			"label": _("Actual"),
			"fieldtype": "Float",
			"width": 90,
			"precision": 2
		},
		{
			"fieldname": "variance",
			"label": _("Variance"),
			"fieldtype": "Float",
			"width": 90,
			"precision": 2
		},
		{
			"fieldname": "variance_percent",
			"label": _("Var %"),
			"fieldtype": "Percent",
			"width": 90,
			"precision": 1
		},
		{
			"fieldname": "achievement_percent",
			"label": _("Achievement %"),
			"fieldtype": "Percent",
			"width": 120,
			"precision": 1
		},
		{
			"fieldname": "reason",
			"label": _("Reason"),
			"fieldtype": "Link",
			"options": "Reason",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""
	Fetch Planning Entry data with calculations
	"""
	conditions = get_conditions(filters)
	
	query = """
		SELECT 
			pe.working_date,
			pei.employee_code,
			et.employee_name,
			pei.target,
			pei.actual,
			(pei.actual - pei.target) as variance,
			CASE 
				WHEN pei.target > 0 THEN ((pei.actual - pei.target) * 100.0 / pei.target)
				ELSE 0 
			END as variance_percent,
			CASE 
				WHEN pei.target > 0 THEN (pei.actual * 100.0 / pei.target)
				ELSE 0 
			END as achievement_percent,
			pei.reason,
			CASE 
				WHEN pei.actual > pei.target THEN 'Above Target'
				WHEN pei.actual < pei.target THEN 'Below Target'
				ELSE 'On Target'
			END as status,
			pe.name as planning_entry_id
		FROM `tabPlanning Entry` pe
		JOIN `tabPlanning Entry Item` pei ON pei.parent = pe.name
		LEFT JOIN `tabEmployee Target` et ON et.name = pei.employee
		WHERE pe.docstatus = 1
			{conditions}
		ORDER BY pe.working_date DESC, et.employee_name
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""
	Build SQL WHERE conditions from filters
	"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("pe.working_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("pe.working_date <= %(to_date)s")
	
	if filters.get("employee"):
		conditions.append("pei.employee = %(employee)s")
	
	if filters.get("employee_code"):
		conditions.append("pei.employee_code = %(employee_code)s")
	
	if filters.get("reason"):
		conditions.append("pei.reason = %(reason)s")
	
	# Variance filter
	variance_filter = filters.get("variance_filter", "All")
	if variance_filter == "Above Target":
		conditions.append("pei.actual > pei.target")
	elif variance_filter == "Below Target":
		conditions.append("pei.actual < pei.target")
	elif variance_filter == "On Target":
		conditions.append("pei.actual = pei.target")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters=None):
	"""
	Generate chart based on user-selected view
	Supports multiple analytical perspectives
	"""
	
	if not data:
		return None
	
	# Get chart view from filters
	chart_view = "Daily Performance Trend"
	if filters and filters.get("chart_view"):
		chart_view = filters.get("chart_view")
	
	# Route to appropriate chart builder
	if chart_view == "Daily Performance Trend":
		return get_daily_trend_chart(data)
	elif chart_view == "Achievement % Over Time":
		return get_achievement_trend_chart(data)
	elif chart_view == "Top/Bottom Performers":
		return get_top_bottom_performers_chart(data)
	elif chart_view == "Variance Distribution":
		return get_variance_distribution_chart(data)
	elif chart_view == "Reason Breakdown":
		return get_reason_breakdown_chart(data)
	elif chart_view == "Employee Comparison":
		return get_employee_comparison_chart(data)
	
	return None


def get_daily_trend_chart(data):
	"""
	Chart: Daily Performance Trend - Shows total actual vs total target per day
	Use Case: Track overall daily performance trends
	"""
	# Aggregate by date
	date_data = {}
	for row in data:
		date = str(row.get("working_date"))
		if date not in date_data:
			date_data[date] = {"target": 0, "actual": 0}
		date_data[date]["target"] += row.get("target", 0)
		date_data[date]["actual"] += row.get("actual", 0)
	
	# Sort by date
	sorted_dates = sorted(date_data.keys())
	
	targets = [date_data[d]["target"] for d in sorted_dates]
	actuals = [date_data[d]["actual"] for d in sorted_dates]
	
	chart = {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Target",
					"values": targets
				},
				{
					"name": "Actual",
					"values": actuals
				}
			]
		},
		"type": "line",
		"colors": ["#f39c12", "#2ecc71"],
		"height": 350,
		"title": "Daily Performance Trend - Target vs Actual",
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 1
		},
		"lineOptions": {
			"regionFill": 1,
			"dotSize": 4
		}
	}
	
	return chart


def get_achievement_trend_chart(data):
	"""
	Chart: Achievement % Over Time - Shows daily achievement percentage
	Use Case: Identify improving or declining trends
	"""
	# Aggregate by date
	date_data = {}
	for row in data:
		date = str(row.get("working_date"))
		if date not in date_data:
			date_data[date] = {"target": 0, "actual": 0}
		date_data[date]["target"] += row.get("target", 0)
		date_data[date]["actual"] += row.get("actual", 0)
	
	# Sort by date and calculate achievement %
	sorted_dates = sorted(date_data.keys())
	achievements = []
	for d in sorted_dates:
		target = date_data[d]["target"]
		actual = date_data[d]["actual"]
		achievement = (actual * 100.0 / target) if target > 0 else 0
		achievements.append(round(achievement, 2))
	
	chart = {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Achievement %",
					"values": achievements
				}
			]
		},
		"type": "line",
		"colors": ["#3498db"],
		"height": 350,
		"title": "Achievement % Over Time - Daily Trend",
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 1
		},
		"lineOptions": {
			"regionFill": 1,
			"dotSize": 5
		}
	}
	
	return chart


def get_top_bottom_performers_chart(data):
	"""
	Chart: Top/Bottom Performers - Shows best and worst performing employees
	Use Case: Quickly identify which employees need attention
	"""
	# Aggregate by employee
	employee_data = {}
	for row in data:
		emp_name = row.get("employee_name") or row.get("employee_code") or "Unknown"
		if emp_name not in employee_data:
			employee_data[emp_name] = {"target": 0, "actual": 0}
		employee_data[emp_name]["target"] += row.get("target", 0)
		employee_data[emp_name]["actual"] += row.get("actual", 0)
	
	# Calculate achievement % for each employee
	employee_achievements = []
	for emp, values in employee_data.items():
		target = values["target"]
		actual = values["actual"]
		achievement = (actual * 100.0 / target) if target > 0 else 0
		employee_achievements.append({
			"name": emp,
			"achievement": round(achievement, 2)
		})
	
	# Sort by achievement
	employee_achievements.sort(key=lambda x: x["achievement"], reverse=True)
	
	# Get top 5 and bottom 5 (or all if less than 10)
	if len(employee_achievements) > 10:
		top_performers = employee_achievements[:5]
		bottom_performers = employee_achievements[-5:]
		performers = top_performers + bottom_performers
	else:
		performers = employee_achievements
	
	labels = [p["name"] for p in performers]
	values = [p["achievement"] for p in performers]
	
	# Color code based on achievement
	colors = []
	for v in values:
		if v >= 100:
			colors.append("#2ecc71")  # Green
		elif v >= 90:
			colors.append("#f39c12")  # Orange
		else:
			colors.append("#e74c3c")  # Red
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{
				"name": "Achievement %",
				"values": values
			}]
		},
		"type": "bar",
		"colors": colors,
		"height": 350,
		"title": "Top & Bottom Performers - Achievement %",
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart


def get_variance_distribution_chart(data):
	"""
	Chart: Variance Distribution - Shows variance for each employee
	Use Case: See who's over/under performing
	"""
	# Aggregate by employee
	employee_data = {}
	for row in data:
		emp_name = row.get("employee_name") or row.get("employee_code") or "Unknown"
		if emp_name not in employee_data:
			employee_data[emp_name] = {"target": 0, "actual": 0}
		employee_data[emp_name]["target"] += row.get("target", 0)
		employee_data[emp_name]["actual"] += row.get("actual", 0)
	
	# Calculate variance for each employee
	employee_variances = []
	for emp, values in employee_data.items():
		variance = values["actual"] - values["target"]
		employee_variances.append({
			"name": emp,
			"variance": round(variance, 2)
		})
	
	# Sort by variance (highest to lowest)
	employee_variances.sort(key=lambda x: x["variance"], reverse=True)
	
	# Limit to top 15 for readability
	if len(employee_variances) > 15:
		employee_variances = employee_variances[:15]
	
	labels = [p["name"] for p in employee_variances]
	values = [p["variance"] for p in employee_variances]
	
	# Color code: positive variance (green), negative variance (red)
	colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in values]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{
				"name": "Variance",
				"values": values
			}]
		},
		"type": "bar",
		"colors": colors,
		"height": 350,
		"title": "Variance Distribution - Top 15 Employees (Actual - Target)",
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart


def get_reason_breakdown_chart(data):
	"""
	Chart: Reason Breakdown - Shows distribution of reasons for missing targets
	Use Case: Identify most common blockers
	"""
	# Count reasons (only for rows with reasons)
	reason_counts = {}
	total_with_reasons = 0
	
	for row in data:
		reason = row.get("reason")
		if reason:
			total_with_reasons += 1
			if reason not in reason_counts:
				reason_counts[reason] = 0
			reason_counts[reason] += 1
	
	if not reason_counts:
		# No reasons recorded
		return {
			"data": {
				"labels": ["No Reasons Recorded"],
				"datasets": [{
					"name": "Count",
					"values": [1]
				}]
			},
			"type": "pie",
			"colors": ["#95a5a6"],
			"height": 350,
			"title": "Reason Breakdown - No Data Available"
		}
	
	# Sort by count
	sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
	
	labels = [r[0] for r in sorted_reasons]
	values = [r[1] for r in sorted_reasons]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{
				"name": "Count",
				"values": values
			}]
		},
		"type": "pie",
		"colors": ["#e74c3c", "#f39c12", "#f1c40f", "#3498db", "#9b59b6", "#1abc9c", "#95a5a6"],
		"height": 350,
		"title": f"Reason Breakdown - Total Entries with Reasons: {total_with_reasons}"
	}
	
	return chart


def get_employee_comparison_chart(data):
	"""
	Chart: Employee Comparison - Compares average performance across employees
	Use Case: Overall employee performance comparison
	"""
	# Aggregate by employee
	employee_data = {}
	for row in data:
		emp_name = row.get("employee_name") or row.get("employee_code") or "Unknown"
		if emp_name not in employee_data:
			employee_data[emp_name] = {"target": 0, "actual": 0, "count": 0}
		employee_data[emp_name]["target"] += row.get("target", 0)
		employee_data[emp_name]["actual"] += row.get("actual", 0)
		employee_data[emp_name]["count"] += 1
	
	# Calculate averages
	employee_averages = []
	for emp, values in employee_data.items():
		avg_target = values["target"] / values["count"] if values["count"] > 0 else 0
		avg_actual = values["actual"] / values["count"] if values["count"] > 0 else 0
		employee_averages.append({
			"name": emp,
			"avg_target": round(avg_target, 2),
			"avg_actual": round(avg_actual, 2)
		})
	
	# Sort by average actual (descending)
	employee_averages.sort(key=lambda x: x["avg_actual"], reverse=True)
	
	# Limit to top 15 for readability
	if len(employee_averages) > 15:
		employee_averages = employee_averages[:15]
	
	labels = [p["name"] for p in employee_averages]
	targets = [p["avg_target"] for p in employee_averages]
	actuals = [p["avg_actual"] for p in employee_averages]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Avg Target",
					"values": targets
				},
				{
					"name": "Avg Actual",
					"values": actuals
				}
			]
		},
		"type": "bar",
		"colors": ["#f39c12", "#2ecc71"],
		"height": 350,
		"title": "Employee Comparison - Average Target vs Actual (Top 15)",
		"barOptions": {
			"stacked": 0,
			"spaceRatio": 0.5
		}
	}
	
	return chart
