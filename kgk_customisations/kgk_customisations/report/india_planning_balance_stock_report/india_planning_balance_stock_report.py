# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta


def execute(filters=None):
	"""
	Generate India Planning Balance Stock Report
	Shows daily stock balances with trend analysis
	"""
	
	if not filters:
		filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns():
	"""
	Define report columns for India Planning Balance Stock analysis
	"""
	return [
		{
			"fieldname": "workingdate",
			"label": _("Working Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "document_id",
			"label": _("Document ID"),
			"fieldtype": "Link",
			"options": "India Planning Balance Stock",
			"width": 150
		},
		{
			"fieldname": "pcs",
			"label": _("PCS"),
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
			"fieldname": "avg_cts_per_pcs",
			"label": _("Avg CTS/PCS"),
			"fieldtype": "Float",
			"width": 110,
			"precision": 3
		},
		{
			"fieldname": "change_pcs",
			"label": _("Change PCS"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "change_cts",
			"label": _("Change CTS"),
			"fieldtype": "Float",
			"width": 100,
			"precision": 2
		},
		{
			"fieldname": "overseas_stock_balance",
			"label": _("Overseas Stock"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "stock_level",
			"label": _("Stock Level"),
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""
	Fetch India Planning Balance Stock data with day-over-day changes
	"""
	conditions = get_conditions(filters)
	
	# First, get all records ordered by date
	query = """
		SELECT 
			ipbs.workingdate,
			ipbs.name as document_id,
			ipbs.pcs,
			ipbs.cts,
			CASE 
				WHEN ipbs.pcs > 0 THEN (ipbs.cts / ipbs.pcs)
				ELSE 0 
			END as avg_cts_per_pcs,
			ipbs.overseas_stock_balance,
			CASE 
				WHEN ipbs.pcs >= 1000 THEN 'High'
				WHEN ipbs.pcs >= 500 THEN 'Medium'
				ELSE 'Low'
			END as stock_level
		FROM `tabIndia Planning Balance Stock` ipbs
		WHERE ipbs.docstatus = 1
			{conditions}
		ORDER BY ipbs.workingdate DESC
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Calculate day-over-day changes
	for i in range(len(data)):
		if i < len(data) - 1:
			# Current vs previous (since we're ordered DESC, next item is previous date)
			prev_row = data[i + 1]
			data[i]["change_pcs"] = data[i].get("pcs", 0) - prev_row.get("pcs", 0)
			data[i]["change_cts"] = round((data[i].get("cts", 0) - prev_row.get("cts", 0)), 2)
		else:
			# First record (oldest) has no previous data
			data[i]["change_pcs"] = 0
			data[i]["change_cts"] = 0.0
	
	return data


def get_conditions(filters):
	"""
	Build SQL WHERE conditions from filters
	"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("ipbs.workingdate >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("ipbs.workingdate <= %(to_date)s")
	
	if filters.get("min_pcs"):
		conditions.append("ipbs.pcs >= %(min_pcs)s")
	
	if filters.get("max_pcs"):
		conditions.append("ipbs.pcs <= %(max_pcs)s")
	
	if filters.get("overseas_stock_balance"):
		conditions.append("ipbs.overseas_stock_balance LIKE %(overseas_stock_balance)s")
		filters["overseas_stock_balance"] = f"%{filters['overseas_stock_balance']}%"
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters=None):
	"""
	Generate chart based on user-selected view
	Supports multiple analytical perspectives
	"""
	
	if not data:
		return None
	
	# Get chart view from filters
	chart_view = "Stock Balance Trend"
	if filters and filters.get("chart_view"):
		chart_view = filters.get("chart_view")
	
	# Route to appropriate chart builder
	if chart_view == "Stock Balance Trend":
		return get_stock_balance_trend_chart(data)
	elif chart_view == "Daily Stock Changes":
		return get_daily_changes_chart(data)
	elif chart_view == "CTS per PCS Trend":
		return get_cts_per_pcs_trend_chart(data)
	elif chart_view == "Weekly Stock Summary":
		return get_weekly_summary_chart(data)
	elif chart_view == "Stock Distribution":
		return get_stock_distribution_chart(data)
	elif chart_view == "PCS vs CTS Correlation":
		return get_correlation_chart(data)
	
	return None


def get_stock_balance_trend_chart(data):
	"""
	Chart: Stock Balance Trend - Shows PCS and CTS levels over time
	Use Case: Track stock levels over time
	"""
	dates = [str(row.get("workingdate")) for row in data]
	pcs = [row.get("pcs") or 0 for row in data]
	cts = [row.get("cts") or 0 for row in data]
	
	# Reverse for chronological order
	dates.reverse()
	pcs.reverse()
	cts.reverse()
	
	chart = {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "PCS",
					"values": pcs
				},
				{
					"name": "CTS",
					"values": cts
				}
			]
		},
		"type": "line",
		"colors": ["#3498db", "#2ecc71"],
		"height": 350,
		"title": "Stock Balance Trend - PCS & CTS Over Time",
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


def get_daily_changes_chart(data):
	"""
	Chart: Daily Stock Changes - Shows day-over-day changes in PCS
	Use Case: Monitor daily inventory changes
	"""
	dates = [str(row.get("workingdate")) for row in data if row.get("change_pcs") != 0]
	changes = [row.get("change_pcs") or 0 for row in data if row.get("change_pcs") != 0]
	
	if not dates:
		return {
			"data": {
				"labels": ["No Changes"],
				"datasets": [{
					"name": "Change in PCS",
					"values": [0]
				}]
			},
			"type": "bar",
			"colors": ["#95a5a6"],
			"height": 350,
			"title": "Daily Stock Changes - No Data"
		}
	
	# Reverse for chronological order
	dates.reverse()
	changes.reverse()
	
	# Color code: positive (green), negative (red)
	colors = ["#2ecc71" if c > 0 else "#e74c3c" for c in changes]
	
	chart = {
		"data": {
			"labels": dates,
			"datasets": [{
				"name": "Change in PCS",
				"values": changes
			}]
		},
		"type": "bar",
		"colors": colors,
		"height": 350,
		"title": "Daily Stock Changes - Day-over-Day PCS",
		"barOptions": {
			"stacked": 0
		}
	}
	
	return chart


def get_cts_per_pcs_trend_chart(data):
	"""
	Chart: CTS per PCS Trend - Shows average stone weight trend
	Use Case: Track average stone size/quality
	"""
	dates = [str(row.get("workingdate")) for row in data]
	avg_cts = [round(row.get("avg_cts_per_pcs") or 0, 3) for row in data]
	
	# Reverse for chronological order
	dates.reverse()
	avg_cts.reverse()
	
	chart = {
		"data": {
			"labels": dates,
			"datasets": [
				{
					"name": "Avg CTS/PCS",
					"values": avg_cts
				}
			]
		},
		"type": "line",
		"colors": ["#9b59b6"],
		"height": 350,
		"title": "CTS per PCS Trend - Average Stone Weight",
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


def get_weekly_summary_chart(data):
	"""
	Chart: Weekly Stock Summary - Shows weekly averages
	Use Case: Weekly inventory patterns
	"""
	# Aggregate by week
	weekly_data = {}
	for row in data:
		date_obj = row.get("workingdate")
		if date_obj:
			# Get week number and year
			if isinstance(date_obj, str):
				date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
			week_key = f"W{date_obj.isocalendar()[1]}-{date_obj.year}"
			
			if week_key not in weekly_data:
				weekly_data[week_key] = {"pcs": [], "cts": []}
			weekly_data[week_key]["pcs"].append(row.get("pcs", 0))
			weekly_data[week_key]["cts"].append(row.get("cts", 0))
	
	# Calculate averages
	weeks = sorted(weekly_data.keys())
	avg_pcs = [sum(weekly_data[w]["pcs"]) / len(weekly_data[w]["pcs"]) if weekly_data[w]["pcs"] else 0 for w in weeks]
	avg_cts = [sum(weekly_data[w]["cts"]) / len(weekly_data[w]["cts"]) if weekly_data[w]["cts"] else 0 for w in weeks]
	
	chart = {
		"data": {
			"labels": weeks,
			"datasets": [
				{
					"name": "Avg PCS",
					"values": avg_pcs
				},
				{
					"name": "Avg CTS",
					"values": avg_cts
				}
			]
		},
		"type": "bar",
		"colors": ["#3498db", "#2ecc71"],
		"height": 350,
		"title": "Weekly Stock Summary - Average PCS & CTS",
		"barOptions": {
			"stacked": 0,
			"spaceRatio": 0.5
		}
	}
	
	return chart


def get_stock_distribution_chart(data):
	"""
	Chart: Stock Distribution - Shows stock level distribution
	Use Case: Understand stock concentration
	"""
	# Count stock levels
	stock_levels = {}
	for row in data:
		level = row.get("stock_level", "Unknown")
		if level not in stock_levels:
			stock_levels[level] = 0
		stock_levels[level] += 1
	
	labels = list(stock_levels.keys())
	values = list(stock_levels.values())
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": [{
				"name": "Count",
				"values": values
			}]
		},
		"type": "pie",
		"colors": ["#e74c3c", "#f39c12", "#2ecc71"],
		"height": 350,
		"title": "Stock Distribution - By Stock Level"
	}
	
	return chart


def get_correlation_chart(data):
	"""
	Chart: PCS vs CTS Correlation - Shows relationship between quantity and weight
	Use Case: Analyze relationship between quantity and weight
	"""
	pcs = [row.get("pcs") or 0 for row in data]
	cts = [row.get("cts") or 0 for row in data]
	
	chart = {
		"data": {
			"labels": pcs,
			"datasets": [
				{
					"name": "CTS",
					"values": cts
				}
			]
		},
		"type": "line",
		"colors": ["#1abc9c"],
		"height": 350,
		"title": "PCS vs CTS Correlation",
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
