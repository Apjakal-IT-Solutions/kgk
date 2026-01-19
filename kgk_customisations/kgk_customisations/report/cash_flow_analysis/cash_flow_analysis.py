# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, add_days, add_months, add_to_date, get_first_day, get_last_day
from datetime import datetime, timedelta
import calendar
from kgk_customisations.kgk_customisations.utils.query_builder import SafeQueryBuilder


def execute(filters=None):
	"""
	Cash Flow Analysis Report - Period comparison, trends, and forecasting
	"""
	if not filters:
		filters = {}
	
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	
	return columns, data, None, chart


def get_columns(filters):
	"""Define report columns based on periodicity"""
	comparison = filters.get("comparison_period")
	show_forecast = filters.get("show_forecast")
	
	columns = [
		{
			"fieldname": "period",
			"label": _("Period"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "total_receipts",
			"label": _("Total Receipts"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "total_payments",
			"label": _("Total Payments"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "total_invoices",
			"label": _("Total Invoices"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "net_cash_flow",
			"label": _("Net Cash Flow"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "closing_balance",
			"label": _("Closing Balance"),
			"fieldtype": "Currency",
			"width": 130
		}
	]
	
	if comparison:
		columns.extend([
			{
				"fieldname": "previous_net_flow",
				"label": _("Previous Net Flow"),
				"fieldtype": "Currency",
				"width": 130
			},
			{
				"fieldname": "growth_amount",
				"label": _("Growth Amount"),
				"fieldtype": "Currency",
				"width": 120
			},
			{
				"fieldname": "growth_percentage",
				"label": _("Growth %"),
				"fieldtype": "Percent",
				"width": 100
			}
		])
	
	if show_forecast:
		columns.append({
			"fieldname": "forecast_amount",
			"label": _("Forecast Net Flow"),
			"fieldtype": "Currency",
			"width": 130
		})
	
	return columns


def get_data(filters):
	"""Fetch cash flow data grouped by period"""
	periodicity = filters.get("periodicity", "Monthly")
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	
	# Get period boundaries
	periods = get_periods(from_date, to_date, periodicity)
	
	data = []
	previous_balance = 0
	
	for period_start, period_end, period_label in periods:
		period_data = get_period_data(period_start, period_end, filters)
		period_data["period"] = period_label
		
		# Calculate net cash flow
		receipts = flt(period_data.get("total_receipts", 0))
		payments = flt(period_data.get("total_payments", 0))
		period_data["net_cash_flow"] = receipts - payments
		period_data["closing_balance"] = previous_balance + period_data["net_cash_flow"]
		
		previous_balance = period_data["closing_balance"]
		
		data.append(period_data)
	
	# Add comparison data
	if filters.get("comparison_period"):
		data = add_comparison_data(data, filters)
	
	# Add forecast
	if filters.get("show_forecast"):
		data = add_forecast_data(data, filters)
	
	return data


def get_periods(from_date, to_date, periodicity):
	"""Generate period boundaries based on periodicity"""
	periods = []
	current = from_date
	
	while current <= to_date:
		if periodicity == "Daily":
			period_start = current
			period_end = current
			period_label = current.strftime("%Y-%m-%d")
			current = add_days(current, 1)
		
		elif periodicity == "Weekly":
			period_start = current
			period_end = add_days(current, 6)
			period_label = f"Week {current.strftime('%Y-W%U')}"
			current = add_days(current, 7)
		
		elif periodicity == "Monthly":
			period_start = get_first_day(current)
			period_end = get_last_day(current)
			period_label = current.strftime("%B %Y")
			current = add_months(current, 1)
		
		elif periodicity == "Quarterly":
			quarter = (current.month - 1) // 3 + 1
			period_start = get_first_day(current.replace(month=(quarter - 1) * 3 + 1))
			period_end = get_last_day(current.replace(month=quarter * 3))
			period_label = f"Q{quarter} {current.year}"
			current = add_months(period_start, 3)
		
		elif periodicity == "Yearly":
			period_start = current.replace(month=1, day=1)
			period_end = current.replace(month=12, day=31)
			period_label = str(current.year)
			current = current.replace(year=current.year + 1)
		
		if period_end > to_date:
			period_end = to_date
		
		periods.append((period_start, period_end, period_label))
		
		if period_end >= to_date:
			break
	
	return periods


def get_period_data(period_start, period_end, filters):
	"""Get aggregated data for a specific period"""
	query = """
		SELECT
			SUM(CASE WHEN cd.main_document_type = 'Receipt' THEN cd.amount ELSE 0 END) as total_receipts,
			SUM(CASE WHEN cd.main_document_type = 'Payment' THEN cd.amount ELSE 0 END) as total_payments,
			SUM(CASE WHEN cd.main_document_type = 'Invoice' THEN cd.amount ELSE 0 END) as total_invoices
		FROM `tabCash Document` cd
		WHERE cd.docstatus = 1
		AND cd.transaction_date >= %(period_start)s
		AND cd.transaction_date <= %(period_end)s
	"""
	
	params = {
		"period_start": period_start,
		"period_end": period_end
	}
	
	if filters.get("company"):
		query += " AND cd.company = %(company)s"
		params["company"] = filters.get("company")
	
	result = frappe.db.sql(query, params, as_dict=1)
	
	if result:
		return result[0]
	else:
		return {
			"total_receipts": 0,
			"total_payments": 0,
			"total_invoices": 0
		}


def add_comparison_data(data, filters):
	"""Add comparison with previous period or same period last year"""
	comparison_type = filters.get("comparison_period")
	
	if not comparison_type or comparison_type == "None":
		return data
	
	for i, row in enumerate(data):
		if comparison_type == "Previous Period":
			if i > 0:
				previous = data[i - 1]
				row["previous_net_flow"] = previous.get("net_cash_flow", 0)
		
		elif comparison_type == "Same Period Last Year":
			# Find same period from last year (simplified - assumes yearly pattern)
			if i >= 12:  # Assuming monthly data
				previous = data[i - 12]
				row["previous_net_flow"] = previous.get("net_cash_flow", 0)
		
		# Calculate growth
		if row.get("previous_net_flow"):
			current = flt(row.get("net_cash_flow", 0))
			previous = flt(row.get("previous_net_flow", 0))
			
			row["growth_amount"] = current - previous
			
			if previous != 0:
				row["growth_percentage"] = (current - previous) / abs(previous) * 100
			else:
				row["growth_percentage"] = 0
	
	return data


def add_forecast_data(data, filters):
	"""Add simple linear forecast based on recent trends"""
	forecast_months = filters.get("forecast_months", 3)
	
	if len(data) < 3:
		return data
	
	# Calculate average growth from last 3 periods
	recent_data = data[-3:]
	growth_rates = []
	
	for i in range(1, len(recent_data)):
		current = flt(recent_data[i].get("net_cash_flow", 0))
		previous = flt(recent_data[i - 1].get("net_cash_flow", 0))
		
		if previous != 0:
			growth_rate = (current - previous) / abs(previous)
			growth_rates.append(growth_rate)
	
	avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
	last_value = flt(data[-1].get("net_cash_flow", 0))
	
	# Add forecast to existing rows (mark last few as forecast)
	for row in data:
		row["forecast_amount"] = None
	
	# Add simple forecast indication to last row
	if data:
		forecast_value = last_value * (1 + avg_growth)
		data[-1]["forecast_amount"] = forecast_value
	
	return data


def get_chart_data(data, filters):
	"""Generate line chart for cash flow trends"""
	if not data:
		return None
	
	labels = [row.get("period") for row in data]
	receipts = [flt(row.get("total_receipts", 0)) for row in data]
	payments = [flt(row.get("total_payments", 0)) for row in data]
	net_flow = [flt(row.get("net_cash_flow", 0)) for row in data]
	
	datasets = [
		{
			"name": "Receipts",
			"values": receipts,
			"chartType": "line"
		},
		{
			"name": "Payments",
			"values": payments,
			"chartType": "line"
		},
		{
			"name": "Net Cash Flow",
			"values": net_flow,
			"chartType": "bar"
		}
	]
	
	chart = {
		"data": {
			"labels": labels,
			"datasets": datasets
		},
		"type": "axis-mixed",
		"colors": ["#28a745", "#dc3545", "#007bff"],
		"axisOptions": {
			"xIsSeries": 1
		}
	}
	
	return chart


@frappe.whitelist()
def generate_statement(filters):
	"""Generate formatted cash flow statement"""
	filters = frappe.parse_json(filters)
	columns, data, _, _ = execute(filters)
	
	statement = "CASH FLOW STATEMENT\n"
	statement += "=" * 80 + "\n"
	statement += f"Period: {filters.get('from_date')} to {filters.get('to_date')}\n"
	if filters.get('company'):
		statement += f"Company: {filters.get('company')}\n"
	statement += "=" * 80 + "\n\n"
	
	for row in data:
		statement += f"Period: {row.get('period')}\n"
		statement += f"  Receipts:        {row.get('total_receipts', 0):15,.2f}\n"
		statement += f"  Payments:        {row.get('total_payments', 0):15,.2f}\n"
		statement += f"  Invoices:        {row.get('total_invoices', 0):15,.2f}\n"
		statement += f"  " + "-" * 40 + "\n"
		statement += f"  Net Cash Flow:   {row.get('net_cash_flow', 0):15,.2f}\n"
		statement += f"  Closing Balance: {row.get('closing_balance', 0):15,.2f}\n"
		statement += "\n"
	
	return statement
