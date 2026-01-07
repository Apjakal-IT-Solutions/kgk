# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime


def execute(filters=None):
	"""
	Generate Polishing Repairs Report
	Fetches Polishing Repair records and organizes them by month and week
	with characteristics (C, P, S)
	"""
	
	if not filters:
		filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns():
	"""
	Define report columns for a single week:
	Month | C | P | S (each with Pcs and %)
	"""
	
	characteristics = [
		{"label": "C", "full_label": "Color", "fieldname": "c"},
		{"label": "P", "full_label": "Polish", "fieldname": "p"},
		{"label": "S", "full_label": "Symmetry", "fieldname": "s"}
	]
	
	columns = [
		{
			"label": _("Month"),
			"fieldname": "month",
			"fieldtype": "Data",
			"width": 100
		}
	]
	
	# Create columns for each characteristic with Pieces and Percentage
	for char in characteristics:
		# Pieces column
		columns.append({
			"label": _(f"{char['label']} (Pcs)"),
			"fieldname": f"{char['fieldname']}_pcs",
			"fieldtype": "Int",
			"width": 90
		})
		# Percentage column
		columns.append({
			"label": _(f"{char['label']} (%)"),
			"fieldname": f"{char['fieldname']}_pct",
			"fieldtype": "Percent",
			"width": 85
		})
	
	return columns


def get_data(filters):
	"""
	Fetch Polishing Repair records and organize by month for a specific week
	"""
	
	# Get the selected week (default to week 1)
	week_value = filters.get("week", "Week 1")
	# Extract the number from "Week 1", "Week 2", etc.
	selected_week = int(week_value.split()[-1]) if isinstance(week_value, str) and "Week" in week_value else int(week_value)
	
	# Fetch Polishing Repair records for the selected week
	polishing_repairs = frappe.get_all(
		"Polishing Repair",
		filters=get_filters(filters, selected_week),
		fields=["name", "date", "week", "section", "grd_rep", "gia_rep"],
		order_by="date"
	)
	
	if not polishing_repairs:
		return []
	
	# Organize data by month
	month_data = {}
	
	for repair in polishing_repairs:
		repair_date = repair.get("date")
		if not repair_date:
			continue
		
		# Extract month and year for grouping
		date_obj = repair_date if isinstance(repair_date, datetime) else datetime.strptime(str(repair_date), "%Y-%m-%d")
		month_key = date_obj.strftime("%B")  # e.g., "January", "February"
		
		if month_key not in month_data:
			month_data[month_key] = {
				"pieces": {},
				"percentages": {}
			}
		
		# Fetch piece_values and percent_values for this record
		piece_items = frappe.get_all(
			"Polishing Report Piece Item",
			filters={"parent": repair["name"], "parenttype": "Polishing Repair"},
			fields=["polishing_c", "polishing_p", "polishing_s"]
		)
		
		percent_items = frappe.get_all(
			"Polishing Report Percentage Item",
			filters={"parent": repair["name"], "parenttype": "Polishing Repair"},
			fields=["percent_c", "percent_p", "percent_s"]
		)
		
		# Store the data (aggregating if multiple records per month)
		if piece_items:
			month_data[month_key]["pieces"] = piece_items[0]
		if percent_items:
			month_data[month_key]["percentages"] = percent_items[0]
	
	# Format data for display
	formatted_data = []
	
	for month in sorted(month_data.keys(), key=lambda x: datetime.strptime(x, "%B").month):
		row = {"month": month}
		
		month_info = month_data[month]
		pieces = month_info.get("pieces", {})
		percentages = month_info.get("percentages", {})
		
		# C (Color)
		row["c_pcs"] = pieces.get("polishing_c", 0) if pieces else 0
		row["c_pct"] = percentages.get("percent_c", 0) if percentages else 0
		
		# P (Polish)
		row["p_pcs"] = pieces.get("polishing_p", 0) if pieces else 0
		row["p_pct"] = percentages.get("percent_p", 0) if percentages else 0
		
		# S (Symmetry)
		row["s_pcs"] = pieces.get("polishing_s", 0) if pieces else 0
		row["s_pct"] = percentages.get("percent_s", 0) if percentages else 0
		
		formatted_data.append(row)
	
	return formatted_data


def get_filters(filters, selected_week=1):
	"""
	Build filters for Polishing Repair query
	"""
	
	query_filters = {"week": selected_week}
	
	if filters.get("section"):
		query_filters["section"] = filters.get("section")
	
	return query_filters


def get_chart_data(data, filters=None):
	"""
	Generate chart based on user-selected view
	Supports multiple analytical perspectives
	"""
	
	if not data:
		return None
	
	# Get chart view from filters (default to Monthly Trend Line)
	chart_view = "Monthly Trend (Line)"
	if filters and filters.get("chart_view"):
		chart_view = filters.get("chart_view")
	
	# Define characteristics
	characteristics = [
		{"label": "C", "fieldname": "c_pct"},
		{"label": "P", "fieldname": "p_pct"},
		{"label": "S", "fieldname": "s_pct"}
	]
	
	# Route to appropriate chart builder
	if chart_view == "Monthly Trend (Line)":
		return get_monthly_trend_chart(data, characteristics, "line")
	elif chart_view == "Monthly Trend (Bar)":
		return get_monthly_trend_chart(data, characteristics, "bar")
	elif chart_view == "Characteristics Comparison":
		return get_characteristics_comparison_chart(data, characteristics)
	elif chart_view == "Week-by-Week Comparison":
		return get_week_comparison_chart(data, characteristics, filters)
	elif chart_view == "Top/Bottom Performers":
		return get_top_bottom_chart(data, characteristics)
	elif chart_view == "Percentage Distribution (Pie)":
		return get_distribution_chart(data, characteristics)
	
	return None


def get_monthly_trend_chart(data, characteristics, chart_type="line"):
	"""
	Chart: Monthly Trend - Shows how each characteristic performs over months
	Use Case: Identify improving or declining trends over time
	"""
	months = [row.get("month") for row in data]
	
	datasets = []
	for char in characteristics:
		values = [row.get(char["fieldname"], 0) for row in data]
		datasets.append({
			"name": char["label"],
			"values": values
		})
	
	chart = {
		"data": {
			"labels": months,
			"datasets": datasets
		},
		"type": chart_type,
		"colors": ["#3498db", "#2ecc71", "#f39c12"],
		"height": 350,
		"title": f"Monthly Trend - Percentage Performance by Characteristic ({chart_type.capitalize()})"
	}
	
	if chart_type == "line":
		chart["axisOptions"] = {
			"xAxisMode": "tick",
			"xIsSeries": 1
		}
		chart["lineOptions"] = {
			"regionFill": 1,
			"dotSize": 4
		}
	else:  # bar
		chart["axisOptions"] = {
			"xAxisMode": "tick",
			"xIsSeries": 1
		}
		chart["barOptions"] = {
			"stacked": 0,
			"spaceRatio": 0.5
		}
	
	return chart


def get_characteristics_comparison_chart(data, characteristics):
	"""
	Chart: Characteristics Comparison - Compares average performance across all characteristics
	Use Case: Identify which characteristics consistently perform better or worse
	"""
	# Calculate average for each characteristic across all months
	averages = []
	for char in characteristics:
		values = [row.get(char["fieldname"], 0) for row in data]
		avg = sum(values) / len(values) if values else 0
		averages.append(round(avg, 2))
	
	chart = {
		"data": {
			"labels": [char["label"] for char in characteristics],
			"datasets": [{
				"name": "Average %",
				"values": averages
			}]
		},
		"type": "bar",
		"colors": ["#2ecc71"],
		"height": 350,
		"title": "Characteristics Comparison - Average Performance Across All Months",
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart


def get_week_comparison_chart(data, characteristics, filters):
	"""
	Chart: Week-by-Week Comparison - Shows selected week's performance across months
	Use Case: Analyze consistency of a specific week across different months
	"""
	months = [row.get("month") for row in data]
	selected_week = filters.get("week", "Week 1") if filters else "Week 1"
	
	# For this chart, we'll show all characteristics for the selected week
	datasets = []
	for char in characteristics:
		values = [row.get(char["fieldname"], 0) for row in data]
		datasets.append({
			"name": char["label"],
			"values": values
		})
	
	chart = {
		"data": {
			"labels": months,
			"datasets": datasets
		},
		"type": "line",
		"colors": ["#3498db", "#2ecc71", "#f39c12"],
		"height": 350,
		"title": f"{selected_week} Performance Across Months - All Characteristics",
		"axisOptions": {
			"xAxisMode": "tick",
			"xIsSeries": 1
		},
		"lineOptions": {
			"regionFill": 0,
			"dotSize": 5
		}
	}
	
	return chart


def get_top_bottom_chart(data, characteristics):
	"""
	Chart: Top/Bottom Performers - Shows best and worst performing characteristics
	Use Case: Quickly identify which characteristics need attention
	"""
	# Calculate average for each characteristic
	char_averages = []
	for char in characteristics:
		values = [row.get(char["fieldname"], 0) for row in data]
		avg = sum(values) / len(values) if values else 0
		char_averages.append({
			"label": char["label"],
			"average": round(avg, 2)
		})
	
	# Sort by average
	char_averages.sort(key=lambda x: x["average"], reverse=True)
	
	# For 3 characteristics, just show all of them sorted
	labels = [p["label"] for p in char_averages]
	values = [p["average"] for p in char_averages]
	
	# Color code: best (green), middle (orange), worst (red)
	colors_list = ["#2ecc71", "#f39c12", "#e74c3c"]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{
				"name": "Average %",
				"values": values
			}]
		},
		"type": "bar",
		"colors": colors_list,
		"height": 350,
		"title": "Performance Ranking - Best to Worst Average Percentage",
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart


def get_distribution_chart(data, characteristics):
	"""
	Chart: Percentage Distribution - Shows overall distribution of percentages
	Use Case: See relative contribution/weight of each characteristic
	"""
	# Calculate total for each characteristic across all months
	totals = []
	for char in characteristics:
		values = [row.get(char["fieldname"], 0) for row in data]
		total = sum(values)
		totals.append(round(total, 2))
	
	chart = {
		"data": {
			"labels": [char["label"] for char in characteristics],
			"datasets": [{
				"name": "Total %",
				"values": totals
			}]
		},
		"type": "pie",
		"colors": ["#3498db", "#2ecc71", "#f39c12"],
		"height": 350,
		"title": "Percentage Distribution - Total Across All Months"
	}
	
	return chart

