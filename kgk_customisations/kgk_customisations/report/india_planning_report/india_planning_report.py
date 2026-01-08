# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime


def execute(filters=None):
	"""
	Generate India Planning Report
	Shows target vs stones/cts with variance analysis
	"""
	
	if not filters:
		filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns():
	"""
	Define report columns for India Planning analysis
	"""
	return [
		{
			"fieldname": "working_date",
			"label": _("Working Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "document_id",
			"label": _("Document ID"),
			"fieldtype": "Link",
			"options": "India Planning",
			"width": 150
		},
		{
			"fieldname": "target",
			"label": _("Target"),
			"fieldtype": "Int",
			"width": 90
		},
		{
			"fieldname": "stones",
			"label": _("Stones"),
			"fieldtype": "Int",
			"width": 90
		},
		{
			"fieldname": "cts",
			"label": _("CTS"),
			"fieldtype": "Float",
			"width": 90,
			"precision": 2
		},
		{
			"fieldname": "variance_stones",
			"label": _("Variance"),
			"fieldtype": "Int",
			"width": 100
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
			"fieldname": "avg_cts_per_stone",
			"label": _("Avg CTS/Stone"),
			"fieldtype": "Float",
			"width": 110,
			"precision": 3
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
	Fetch India Planning data with calculations
	"""
	conditions = get_conditions(filters)
	
	query = """
		SELECT 
			ip.working_date,
			ip.name as document_id,
			ip.target,
			ip.stones,
			ip.cts,
			(ip.stones - COALESCE(ip.target, 0)) as variance_stones,
			CASE 
				WHEN ip.target > 0 THEN ((ip.stones - ip.target) * 100.0 / ip.target)
				ELSE 0 
			END as variance_percent,
			CASE 
				WHEN ip.target > 0 THEN (ip.stones * 100.0 / ip.target)
				ELSE 0 
			END as achievement_percent,
			CASE 
				WHEN ip.stones > 0 THEN (ip.cts / ip.stones)
				ELSE 0 
			END as avg_cts_per_stone,
			CASE 
				WHEN ip.target IS NULL THEN 'No Target'
				WHEN ip.stones > ip.target THEN 'Above Target'
				WHEN ip.stones < ip.target THEN 'Below Target'
				ELSE 'On Target'
			END as status
		FROM `tabIndia Planning` ip
		WHERE ip.docstatus = 1
			{conditions}
		ORDER BY ip.working_date DESC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""
	Build SQL WHERE conditions from filters
	"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("ip.working_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("ip.working_date <= %(to_date)s")
	
	# Target filter
	has_target = filters.get("has_target", "All")
	if has_target == "Only with Target":
		conditions.append("ip.target IS NOT NULL AND ip.target > 0")
	elif has_target == "Only without Target":
		conditions.append("(ip.target IS NULL OR ip.target = 0)")
	
	# Variance filter
	variance_filter = filters.get("variance_filter", "All")
	if variance_filter == "Above Target":
		conditions.append("ip.target IS NOT NULL AND ip.stones > ip.target")
	elif variance_filter == "Below Target":
		conditions.append("ip.target IS NOT NULL AND ip.stones < ip.target")
	elif variance_filter == "On Target":
		conditions.append("ip.target IS NOT NULL AND ip.stones = ip.target")
	elif variance_filter == "No Target":
		conditions.append("(ip.target IS NULL OR ip.target = 0)")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters=None):
	"""
	Generate chart based on user-selected view
	Supports multiple analytical perspectives
	"""
	
	if not data:
		return None
	
	# Get chart view from filters
	chart_view = "Daily Trend"
	if filters and filters.get("chart_view"):
		chart_view = filters.get("chart_view")
	
	# Route to appropriate chart builder
	if chart_view == "Daily Trend":
		return get_daily_trend_chart(data)
	elif chart_view == "Achievement % Over Time":
		return get_achievement_trend_chart(data)
	elif chart_view == "Stones vs CTS Correlation":
		return get_correlation_chart(data)
	elif chart_view == "Monthly Aggregates":
		return get_monthly_aggregates_chart(data)
	elif chart_view == "Variance Distribution":
		return get_variance_distribution_chart(data)
	elif chart_view == "Avg CTS per Stone Trend":
		return get_avg_cts_trend_chart(data)
	
	return None


def get_daily_trend_chart(data):
	"""
	Chart: Daily Trend - Shows target vs stones per day
	Use Case: Track daily performance trends
	"""
	dates = [str(row.get("working_date")) for row in data]
	targets = [row.get("target") or 0 for row in data]
	stones = [row.get("stones") or 0 for row in data]
	
	# Reverse to show chronological order
	dates.reverse()
	targets.reverse()
	stones.reverse()
	
	chart = {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "Target",
					"values": targets
				},
				{
					"name": "Stones",
					"values": stones
				}
			]
		},
		"type": "line",
		"colors": ["#f39c12", "#2ecc71"],
		"height": 350,
		"title": "Daily Trend - Target vs Stones",
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
	Use Case: Identify improving or declining patterns
	"""
	# Filter only records with targets
	data_with_targets = [row for row in data if row.get("target") and row.get("target") > 0]
	
	if not data_with_targets:
		return {
			"data": {
				"labels": ["No Data"],
				"datasets": [{
					"name": "Achievement %",
					"values": [0]
				}]
			},
			"type": "line",
			"colors": ["#95a5a6"],
			"height": 350,
			"title": "Achievement % Over Time - No Data with Targets"
		}
	
	dates = [str(row.get("working_date")) for row in data_with_targets]
	achievements = [row.get("achievement_percent") or 0 for row in data_with_targets]
	
	# Reverse for chronological order
	dates.reverse()
	achievements.reverse()
	
	chart = {
		"data": {
			"labels": dates,
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


def get_correlation_chart(data):
	"""
	Chart: Stones vs CTS Correlation - Shows relationship between quantity and weight
	Use Case: Understand weight distribution patterns
	"""
	stones = [row.get("stones") or 0 for row in data]
	cts = [row.get("cts") or 0 for row in data]
	
	chart = {
		"data": {
			"labels": stones,
			"datasets": [
				{
					"name": "CTS",
					"values": cts
				}
			]
		},
		"type": "line",
		"colors": ["#9b59b6"],
		"height": 350,
		"title": "Stones vs CTS Correlation",
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 0
		},
		"lineOptions": {
			"regionFill": 0,
			"dotSize": 6
		}
	}
	
	return chart


def get_monthly_aggregates_chart(data):
	"""
	Chart: Monthly Aggregates - Shows monthly totals
	Use Case: Month-over-month comparison
	"""
	# Aggregate by month
	monthly_data = {}
	for row in data:
		date_obj = row.get("working_date")
		if date_obj:
			month_key = date_obj.strftime("%b-%Y") if isinstance(date_obj, datetime) else str(date_obj)[:7]
			if month_key not in monthly_data:
				monthly_data[month_key] = {"target": 0, "stones": 0, "cts": 0}
			monthly_data[month_key]["target"] += row.get("target") or 0
			monthly_data[month_key]["stones"] += row.get("stones") or 0
			monthly_data[month_key]["cts"] += row.get("cts") or 0
	
	# Sort by month
	sorted_months = sorted(monthly_data.keys())
	
	targets = [monthly_data[m]["target"] for m in sorted_months]
	stones = [monthly_data[m]["stones"] for m in sorted_months]
	cts = [monthly_data[m]["cts"] for m in sorted_months]
	
	chart = {
		"data": {
			"labels": sorted_months,
			"datasets": [
				{
					"name": "Target",
					"values": targets
				},
				{
					"name": "Stones",
					"values": stones
				},
				{
					"name": "CTS",
					"values": cts
				}
			]
		},
		"type": "bar",
		"colors": ["#f39c12", "#2ecc71", "#3498db"],
		"height": 350,
		"title": "Monthly Aggregates - Target, Stones, CTS",
		"barOptions": {
			"stacked": 0,
			"spaceRatio": 0.5
		}
	}
	
	return chart


def get_variance_distribution_chart(data):
	"""
	Chart: Variance Distribution - Shows variance for each date
	Use Case: Identify over/under performance
	"""
	# Filter only records with targets
	data_with_targets = [row for row in data if row.get("target") and row.get("target") > 0]
	
	if not data_with_targets:
		return {
			"data": {
				"labels": ["No Data"],
				"datasets": [{
					"name": "Variance",
					"values": [0]
				}]
			},
			"type": "bar",
			"colors": ["#95a5a6"],
			"height": 350,
			"title": "Variance Distribution - No Data with Targets"
		}
	
	# Limit to last 30 days for readability
	if len(data_with_targets) > 30:
		data_with_targets = data_with_targets[:30]
	
	dates = [str(row.get("working_date")) for row in data_with_targets]
	variances = [row.get("variance_stones") or 0 for row in data_with_targets]
	
	# Reverse for chronological order
	dates.reverse()
	variances.reverse()
	
	# Color code: positive variance (green), negative variance (red)
	colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in variances]
	
	chart = {
		"data": {
			"labels": dates,
			"datasets": [{
				"name": "Variance (Stones - Target)",
				"values": variances
			}]
		},
		"type": "bar",
		"colors": colors,
		"height": 350,
		"title": "Variance Distribution - Last 30 Days",
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart


def get_avg_cts_trend_chart(data):
	"""
	Chart: Average CTS per Stone Trend - Shows stone size/quality trends
	Use Case: Track average stone weight over time
	"""
	dates = [str(row.get("working_date")) for row in data]
	avg_cts = [round(row.get("avg_cts_per_stone") or 0, 3) for row in data]
	
	# Reverse for chronological order
	dates.reverse()
	avg_cts.reverse()
	
	chart = {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "Avg CTS/Stone",
					"values": avg_cts
				}
			]
		},
		"type": "line",
		"colors": ["#1abc9c"],
		"height": 350,
		"title": "Average CTS per Stone Trend",
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
