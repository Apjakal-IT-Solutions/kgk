# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Time"),
			"fieldname": "time",
			"fieldtype": "Time",
			"width": 80
		},
		{
			"label": _("Type"),
			"fieldname": "type",
			"fieldtype": "Link",
			"options": "Laser Positoin Type",
			"width": 150
		},
		{
			"label": _("PCS"),
			"fieldname": "pcs",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("CTS"),
			"fieldname": "cts",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"label": _("Total PCS"),
			"fieldname": "pcs_total",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Total CTS"),
			"fieldname": "cts_total",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"label": _("Document"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Laser Stock Position",
			"width": 150
		}
	]


def get_data(filters):
	"""Fetch data from Laser Stock Position and child table"""
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT 
			lsp.date,
			lsp.time,
			lspi.type,
			lspi.pcs,
			lspi.cts,
			lsp.pcs_total,
			lsp.cts_total,
			lsp.name
		FROM `tabLaser Stock Position` lsp
		LEFT JOIN `tabLaser Stock Position Item` lspi 
			ON lspi.parent = lsp.name
		WHERE 1=1
			{conditions}
		ORDER BY lsp.date DESC, lsp.time DESC
	""".format(conditions=conditions), filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build WHERE clause conditions"""
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND lsp.date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND lsp.date <= %(to_date)s"
	
	if filters.get("type"):
		conditions += " AND lspi.type = %(type)s"
	
	# Only submitted documents
	conditions += " AND lsp.docstatus = 1"
	
	return conditions


def get_chart_data(data, filters):
	"""Generate chart data based on selected chart view"""
	if not data:
		return None
	
	chart_view = filters.get("chart_view", "Daily Total Trend")
	
	if chart_view == "Daily Total Trend":
		return get_daily_total_trend_chart(data)
	elif chart_view == "Type Distribution":
		return get_type_distribution_chart(data)
	elif chart_view == "Type Comparison by CTS":
		return get_type_comparison_chart(data)
	elif chart_view == "Daily Type Breakdown":
		return get_daily_type_breakdown_chart(data)
	elif chart_view == "Average CTS per Type":
		return get_average_cts_chart(data)
	elif chart_view == "Time-based Pattern":
		return get_time_pattern_chart(data)
	
	return None


def get_daily_total_trend_chart(data):
	"""Chart 1: Daily Total Trend - Line/Bar combo showing PCS and CTS over time"""
	# Group by date
	date_data = {}
	for row in data:
		date = str(row.get("date"))
		if date not in date_data:
			date_data[date] = {
				"pcs_total": row.get("pcs_total", 0),
				"cts_total": row.get("cts_total", 0)
			}
	
	# Sort dates
	sorted_dates = sorted(date_data.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": "Total PCS",
					"values": [date_data[d]["pcs_total"] for d in sorted_dates],
					"chartType": "bar"
				},
				{
					"name": "Total CTS",
					"values": [date_data[d]["cts_total"] for d in sorted_dates],
					"chartType": "line"
				}
			]
		},
		"type": "axis-mixed",
		"colors": ["#4CAF50", "#FF9800"]
	}


def get_type_distribution_chart(data):
	"""Chart 2: Type Distribution - Pie chart showing PCS breakdown by type"""
	# Group by type
	type_data = {}
	for row in data:
		type_name = row.get("type") or "Unknown"
		pcs = row.get("pcs", 0)
		if type_name in type_data:
			type_data[type_name] += pcs
		else:
			type_data[type_name] = pcs
	
	# Filter out zero values and sort
	type_data = {k: v for k, v in type_data.items() if v > 0}
	sorted_types = sorted(type_data.items(), key=lambda x: x[1], reverse=True)
	
	if not sorted_types:
		return None
	
	return {
		"data": {
			"labels": [t[0] for t in sorted_types],
			"datasets": [
				{
					"name": "PCS Distribution",
					"values": [t[1] for t in sorted_types]
				}
			]
		},
		"type": "pie",
		"colors": ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0", "#00BCD4"]
	}


def get_type_comparison_chart(data):
	"""Chart 3: Type Comparison by CTS - Bar chart showing total carats per type"""
	# Group by type
	type_data = {}
	for row in data:
		type_name = row.get("type") or "Unknown"
		cts = row.get("cts", 0)
		if type_name in type_data:
			type_data[type_name] += cts
		else:
			type_data[type_name] = cts
	
	# Filter and sort
	type_data = {k: v for k, v in type_data.items() if v > 0}
	sorted_types = sorted(type_data.items(), key=lambda x: x[1], reverse=True)
	
	if not sorted_types:
		return None
	
	return {
		"data": {
			"labels": [t[0] for t in sorted_types],
			"datasets": [
				{
					"name": "Total CTS",
					"values": [round(t[1], 2) for t in sorted_types]
				}
			]
		},
		"type": "bar",
		"colors": ["#4CAF50"]
	}


def get_daily_type_breakdown_chart(data):
	"""Chart 4: Daily Type Breakdown - Stacked bar showing composition over time"""
	# Get all unique types
	all_types = set()
	date_type_data = {}
	
	for row in data:
		date = str(row.get("date"))
		type_name = row.get("type") or "Unknown"
		pcs = row.get("pcs", 0)
		
		all_types.add(type_name)
		
		if date not in date_type_data:
			date_type_data[date] = {}
		
		if type_name in date_type_data[date]:
			date_type_data[date][type_name] += pcs
		else:
			date_type_data[date][type_name] = pcs
	
	# Sort dates
	sorted_dates = sorted(date_type_data.keys())
	sorted_types = sorted(all_types)
	
	# Create datasets for each type
	datasets = []
	colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0", "#00BCD4", "#FFEB3B", "#795548"]
	
	for idx, type_name in enumerate(sorted_types):
		values = [date_type_data[d].get(type_name, 0) for d in sorted_dates]
		datasets.append({
			"name": type_name,
			"values": values,
			"chartType": "bar"
		})
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": datasets
		},
		"type": "bar",
		"barOptions": {
			"stacked": 1
		},
		"colors": colors[:len(sorted_types)]
	}


def get_average_cts_chart(data):
	"""Chart 5: Average CTS per Type - Bar chart showing average weight characteristics"""
	# Calculate average CTS per type
	type_data = {}
	type_count = {}
	
	for row in data:
		type_name = row.get("type") or "Unknown"
		cts = row.get("cts", 0)
		
		if cts > 0:  # Only count non-zero values
			if type_name in type_data:
				type_data[type_name] += cts
				type_count[type_name] += 1
			else:
				type_data[type_name] = cts
				type_count[type_name] = 1
	
	# Calculate averages
	averages = {}
	for type_name in type_data:
		if type_count[type_name] > 0:
			averages[type_name] = type_data[type_name] / type_count[type_name]
	
	# Sort by average
	sorted_types = sorted(averages.items(), key=lambda x: x[1], reverse=True)
	
	if not sorted_types:
		return None
	
	return {
		"data": {
			"labels": [t[0] for t in sorted_types],
			"datasets": [
				{
					"name": "Average CTS",
					"values": [round(t[1], 2) for t in sorted_types]
				}
			]
		},
		"type": "bar",
		"colors": ["#FF9800"]
	}


def get_time_pattern_chart(data):
	"""Chart 6: Time-based Pattern - Shows stock recording patterns by hour"""
	# Extract hour from time and group
	hour_data = {}
	
	for row in data:
		time_str = str(row.get("time", ""))
		if time_str:
			# Extract hour from time (format: HH:MM:SS)
			hour = time_str.split(":")[0] if ":" in time_str else "Unknown"
			
			if hour not in hour_data:
				hour_data[hour] = {"count": 0, "total_pcs": 0, "total_cts": 0}
			
			hour_data[hour]["count"] += 1
			hour_data[hour]["total_pcs"] += row.get("pcs", 0)
			hour_data[hour]["total_cts"] += row.get("cts", 0)
	
	# Sort by hour
	sorted_hours = sorted(hour_data.keys())
	
	if not sorted_hours:
		return None
	
	return {
		"data": {
			"labels": [f"{h}:00" for h in sorted_hours],
			"datasets": [
				{
					"name": "Record Count",
					"values": [hour_data[h]["count"] for h in sorted_hours],
					"chartType": "bar"
				},
				{
					"name": "Total PCS",
					"values": [hour_data[h]["total_pcs"] for h in sorted_hours],
					"chartType": "line"
				}
			]
		},
		"type": "axis-mixed",
		"colors": ["#9C27B0", "#4CAF50"]
	}
