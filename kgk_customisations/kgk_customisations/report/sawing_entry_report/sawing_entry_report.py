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
			"label": _("Work Date"),
			"fieldname": "work_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("LS From Sawing (A)"),
			"fieldname": "ls_from_sawing_a",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("LS From Factory (A)"),
			"fieldname": "factory_stones_a",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Results OK (A)"),
			"fieldname": "results_ok_a",
			"fieldtype": "Int",
			"width": 110
		},
		{
			"label": _("Results Not OK (A)"),
			"fieldname": "results_not_ok_a",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Total Sheet A"),
			"fieldname": "total_sheet_a",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Normal LS (B)"),
			"fieldname": "ls_from_factoy_b",
			"fieldtype": "Int",
			"width": 140
		},
		{
			"label": _("Results OK (B)"),
			"fieldname": "results_ok_b",
			"fieldtype": "Int",
			"width": 110
		},
		{
			"label": _("Results Not OK (B)"),
			"fieldname": "results_not_ok_b",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Total Sheet B"),
			"fieldname": "total_sheet_b",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Grand Total"),
			"fieldname": "grand_total",
			"fieldtype": "Int",
			"width": 100
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
			"options": "Sawing Entry",
			"width": 150
		}
	]


def get_data(filters):
	"""Fetch data from Sawing Entry"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT 
			work_date,
			ls_from_sawing_a,
			factory_stones_a,
			results_ok_a,
			results_not_ok_a,
			ls_from_factoy_b,
			results_ok_b,
			results_not_ok_b,
			docstatus,
			name
		FROM `tabSawing Entry`
		WHERE 1=1
			{conditions}
		ORDER BY work_date DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Calculate totals and add labels
	for row in data:
		# Calculate Sheet A total (all inputs and outputs)
		row["total_sheet_a"] = (
			row.get("results_ok_a", 0) + 
			row.get("results_not_ok_a", 0)
		)
		
		# Calculate Sheet B total
		row["total_sheet_b"] = (
			row.get("results_ok_b", 0) + 
			row.get("results_not_ok_b", 0)
		)
		
		# Calculate grand total
		row["grand_total"] = row["total_sheet_a"] + row["total_sheet_b"]
		
		# Add docstatus label
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
		conditions += " AND work_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND work_date <= %(to_date)s"
	
	# Only submitted documents
	conditions += " AND docstatus = 1"
	
	return conditions


def get_chart_data(data, filters):
	"""Generate chart data based on selected chart view"""
	if not data:
		return None
	
	chart_view = filters.get("chart_view", "Daily Production Trend")
	
	if chart_view == "Daily Production Trend":
		return get_daily_production_trend_chart(data)
	elif chart_view == "Sheet Comparison":
		return get_sheet_comparison_chart(data)
	elif chart_view == "Success Rate Analysis":
		return get_success_rate_chart(data)
	elif chart_view == "Input vs Output (Sheet A)":
		return get_sheet_a_efficiency_chart(data)
	elif chart_view == "Input vs Output (Sheet B)":
		return get_sheet_b_efficiency_chart(data)
	elif chart_view == "Weekly Quality Comparison":
		return get_weekly_quality_chart(data)
	
	return None


def get_daily_production_trend_chart(data):
	"""Chart 1: Daily Production Trend - Line chart showing total daily production"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("work_date"))
		total = row.get("grand_total", 0)
		
		if date in date_data:
			date_data[date] += total
		else:
			date_data[date] = total
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Total Production",
					"values": [date_data[d] for d in sorted_dates]
				}
			]
		},
		"type": "line",
		"colors": ["#2196F3"]
	}


def get_sheet_comparison_chart(data):
	"""Chart 2: Sheet Comparison - Bar chart comparing Sheet A vs Sheet B totals"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("work_date"))
		sheet_a = row.get("total_sheet_a", 0)
		sheet_b = row.get("total_sheet_b", 0)
		
		if date not in date_data:
			date_data[date] = {"sheet_a": 0, "sheet_b": 0}
		
		date_data[date]["sheet_a"] += sheet_a
		date_data[date]["sheet_b"] += sheet_b
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Sheet A Total",
					"values": [date_data[d]["sheet_a"] for d in sorted_dates]
				},
				{
					"name": "Sheet B Total",
					"values": [date_data[d]["sheet_b"] for d in sorted_dates]
				}
			]
		},
		"type": "bar",
		"colors": ["#4CAF50", "#FF9800"]
	}


def get_success_rate_chart(data):
	"""Chart 3: Success Rate Analysis - Stacked bar showing OK vs Not OK results"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("work_date"))
		ok_total = row.get("results_ok_a", 0) + row.get("results_ok_b", 0)
		not_ok_total = row.get("results_not_ok_a", 0) + row.get("results_not_ok_b", 0)
		
		if date not in date_data:
			date_data[date] = {"ok": 0, "not_ok": 0}
		
		date_data[date]["ok"] += ok_total
		date_data[date]["not_ok"] += not_ok_total
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Results OK",
					"values": [date_data[d]["ok"] for d in sorted_dates],
					"chartType": "bar"
				},
				{
					"name": "Results Not OK",
					"values": [date_data[d]["not_ok"] for d in sorted_dates],
					"chartType": "bar"
				}
			]
		},
		"type": "bar",
		"barOptions": {
			"stacked": 1
		},
		"colors": ["#4CAF50", "#F44336"]
	}


def get_sheet_a_efficiency_chart(data):
	"""Chart 4: Input vs Output (Sheet A) - Mixed chart showing efficiency"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("work_date"))
		input_a = row.get("ls_from_sawing_a", 0) + row.get("factory_stones_a", 0)
		output_a = row.get("results_ok_a", 0) + row.get("results_not_ok_a", 0)
		
		if date not in date_data:
			date_data[date] = {"input": 0, "output": 0}
		
		date_data[date]["input"] += input_a
		date_data[date]["output"] += output_a
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Input (Sheet A)",
					"values": [date_data[d]["input"] for d in sorted_dates],
					"chartType": "bar"
				},
				{
					"name": "Output (Sheet A)",
					"values": [date_data[d]["output"] for d in sorted_dates],
					"chartType": "line"
				}
			]
		},
		"type": "axis-mixed",
		"colors": ["#2196F3", "#4CAF50"]
	}


def get_sheet_b_efficiency_chart(data):
	"""Chart 5: Input vs Output (Sheet B) - Mixed chart showing efficiency"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("work_date"))
		input_b = row.get("ls_from_factoy_b", 0)
		output_b = row.get("results_ok_b", 0) + row.get("results_not_ok_b", 0)
		
		if date not in date_data:
			date_data[date] = {"input": 0, "output": 0}
		
		date_data[date]["input"] += input_b
		date_data[date]["output"] += output_b
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Input (Sheet B)",
					"values": [date_data[d]["input"] for d in sorted_dates],
					"chartType": "bar"
				},
				{
					"name": "Output (Sheet B)",
					"values": [date_data[d]["output"] for d in sorted_dates],
					"chartType": "line"
				}
			]
		},
		"type": "axis-mixed",
		"colors": ["#FF9800", "#9C27B0"]
	}


def get_weekly_quality_chart(data):
	"""Chart 6: Weekly Quality Comparison - Bar chart showing success rate % by week"""
	# Group by week
	week_data = {}
	
	for row in data:
		date = row.get("work_date")
		if date:
			# Get week number
			week_num = datetime.strptime(str(date), "%Y-%m-%d").isocalendar()[1]
			year = datetime.strptime(str(date), "%Y-%m-%d").year
			week_key = f"{year}-W{week_num:02d}"
			
			if week_key not in week_data:
				week_data[week_key] = {
					"a_ok": 0, "a_not_ok": 0,
					"b_ok": 0, "b_not_ok": 0
				}
			
			week_data[week_key]["a_ok"] += row.get("results_ok_a", 0)
			week_data[week_key]["a_not_ok"] += row.get("results_not_ok_a", 0)
			week_data[week_key]["b_ok"] += row.get("results_ok_b", 0)
			week_data[week_key]["b_not_ok"] += row.get("results_not_ok_b", 0)
	
	# Calculate success rates
	sorted_weeks = sorted(week_data.keys())
	sheet_a_rates = []
	sheet_b_rates = []
	
	for week in sorted_weeks:
		# Sheet A success rate
		a_total = week_data[week]["a_ok"] + week_data[week]["a_not_ok"]
		a_rate = (week_data[week]["a_ok"] / a_total * 100) if a_total > 0 else 0
		sheet_a_rates.append(round(a_rate, 1))
		
		# Sheet B success rate
		b_total = week_data[week]["b_ok"] + week_data[week]["b_not_ok"]
		b_rate = (week_data[week]["b_ok"] / b_total * 100) if b_total > 0 else 0
		sheet_b_rates.append(round(b_rate, 1))
	
	if not sorted_weeks:
		return None
	
	return {
		"data": {
			"labels": sorted_weeks,
			"datasets": [
				{
					"name": "Sheet A Success %",
					"values": sheet_a_rates
				},
				{
					"name": "Sheet B Success %",
					"values": sheet_b_rates
				}
			]
		},
		"type": "bar",
		"colors": ["#4CAF50", "#00BCD4"]
	}
