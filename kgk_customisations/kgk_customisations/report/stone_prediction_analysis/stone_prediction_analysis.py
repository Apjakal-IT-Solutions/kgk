# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Stone Prediction Analysis Report
================================

Security: Updated January 2026 to prevent SQL injection vulnerabilities.
All queries now use parameterized approach via SafeQueryBuilder.
"""

import frappe
from frappe import _
from kgk_customisations.kgk_customisations.utils.query_builder import SafeQueryBuilder


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_report_summary(data, filters)
	
	# Prepare report summary for Excel export
	message = None
	report_summary = get_summary_data_for_excel(data, filters) if data else None
	
	return columns, data, message, chart, summary, report_summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Prediction ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Stone Prediction",
			"width": 150
		},
		{
			"label": _("Prediction Date"),
			"fieldname": "prediction_date",
			"fieldtype": "Date",
			"width": 110
		},
		{
			"label": _("Predicted By"),
			"fieldname": "predicted_by",
			"fieldtype": "Link",
			"options": "User",
			"width": 150
		},
		{
			"label": _("Lot ID"),
			"fieldname": "lot_id",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Serial Number"),
			"fieldname": "serial_number",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Original Weight"),
			"fieldname": "original_weight",
			"fieldtype": "Float",
			"width": 110,
			"precision": 2
		},
		{
			"label": _("Number of Cuts"),
			"fieldname": "number_of_cuts",
			"fieldtype": "Int",
			"width": 110
		},
		{
			"label": _("Total Pol CTS"),
			"fieldname": "total_pol_cts",
			"fieldtype": "Float",
			"width": 110,
			"precision": 2
		},
		{
			"label": _("Estimated Value"),
			"fieldname": "estimated_value",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"label": _("Docstatus"),
			"fieldname": "docstatus",
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""
	Fetch Stone Prediction data with aggregations.
	
	Security: Uses parameterized queries to prevent SQL injection.
	All user inputs are properly escaped via parameter binding.
	"""
	if not filters:
		filters = {}
	
	# Build WHERE clause safely using SafeQueryBuilder
	where_conditions = []
	params = {}
	
	if filters.get("serial_number"):
		where_conditions.append("sp.serial_number = %(serial_number)s")
		params["serial_number"] = filters.get("serial_number")
	
	if filters.get("lot_id"):
		where_conditions.append("sp.lot_id = %(lot_id)s")
		params["lot_id"] = filters.get("lot_id")
	
	if filters.get("from_date"):
		where_conditions.append("sp.prediction_date >= %(from_date)s")
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		where_conditions.append("sp.prediction_date <= %(to_date)s")
		params["to_date"] = filters.get("to_date")
	
	if filters.get("predicted_by"):
		where_conditions.append("sp.predicted_by = %(predicted_by)s")
		params["predicted_by"] = filters.get("predicted_by")
	
	# Handle docstatus filter safely
	if filters.get("docstatus") is not None and filters.get("docstatus") != "":
		docstatus_map = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
		if filters.get("docstatus") in docstatus_map:
			where_conditions.append("sp.docstatus = %(docstatus_value)s")
			params["docstatus_value"] = docstatus_map[filters.get("docstatus")]
	
	# Build final WHERE clause
	where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
	
	# SECURITY: Query uses parameterized approach - no string formatting with user input
	query = f"""
		SELECT 
			sp.name,
			sp.prediction_date,
			sp.predicted_by,
			sp.lot_id,
			sp.serial_number,
			sp.original_weight,
			sp.number_of_cuts,
			sp.estimated_value,
			sp.docstatus,
			COALESCE(SUM(sc.pol_cts), 0) as total_pol_cts
		FROM 
			`tabStone Prediction` sp
		LEFT JOIN 
			`tabStone Cuts` sc ON sc.parent = sp.name
		WHERE
			{where_clause}
		GROUP BY 
			sp.name
		ORDER BY 
			sp.prediction_date DESC, sp.name
	"""
	
	# Execute query safely with parameter binding
	predictions = SafeQueryBuilder.execute_safe_query(query, params, as_dict=True)
	
	# Add status labels
	for pred in predictions:
		if pred.docstatus == 0:
			pred.docstatus = "Draft"
		elif pred.docstatus == 1:
			pred.docstatus = "Submitted"
		elif pred.docstatus == 2:
			pred.docstatus = "Cancelled"
	
	return predictions


def get_chart_data(data, filters):
	"""Generate chart for visual representation"""
	if not data:
		return None
	
	# Group by prediction date for timeline chart
	labels = []
	values = []
	
	for row in data:
		if row.get("prediction_date"):
			labels.append(str(row.get("prediction_date")))
			values.append(row.get("estimated_value") or 0)
	
	return {
		"data": {
			"labels": labels[:10],  # Last 10 predictions
			"datasets": [
				{
					"name": "Estimated Value",
					"values": values[:10]
				}
			]
		},
		"type": "bar",
		"colors": ["#29CD42"],
		"barOptions": {
			"stacked": 0
		}
	}


def get_report_summary(data, filters):
	"""Calculate summary statistics"""
	if not data:
		return []
	
	total_predictions = len(data)
	total_estimated_value = sum(row.get("estimated_value") or 0 for row in data)
	avg_estimated_value = total_estimated_value / total_predictions if total_predictions else 0
	total_cuts = sum(row.get("number_of_cuts") or 0 for row in data)
	avg_cuts_per_prediction = total_cuts / total_predictions if total_predictions else 0
	total_pol_cts = sum(row.get("total_pol_cts") or 0 for row in data)
	
	summary = [
		{
			"value": total_predictions,
			"indicator": "Blue",
			"label": _("Total Predictions"),
			"datatype": "Int"
		},
		{
			"value": total_estimated_value,
			"indicator": "Green",
			"label": _("Total Estimated Value"),
			"datatype": "Currency"
		},
		{
			"value": avg_estimated_value,
			"indicator": "Orange",
			"label": _("Avg Estimated Value"),
			"datatype": "Currency"
		},
		{
			"value": total_cuts,
			"indicator": "Purple",
			"label": _("Total Cuts"),
			"datatype": "Int"
		},
		{
			"value": avg_cuts_per_prediction,
			"indicator": "Red",
			"label": _("Avg Cuts/Prediction"),
			"datatype": "Float",
			"precision": 1
		},
		{
			"value": total_pol_cts,
			"indicator": "Cyan",
			"label": _("Total Pol CTS"),
			"datatype": "Float",
			"precision": 2
		}
	]
	
	return summary


def get_summary_data_for_excel(data, filters):
	"""Prepare summary data for separate Excel sheet"""
	if not data:
		return None
	
	total_predictions = len(data)
	total_estimated_value = sum(row.get("estimated_value") or 0 for row in data)
	avg_estimated_value = total_estimated_value / total_predictions if total_predictions else 0
	total_cuts = sum(row.get("number_of_cuts") or 0 for row in data)
	avg_cuts_per_prediction = total_cuts / total_predictions if total_predictions else 0
	total_pol_cts = sum(row.get("total_pol_cts") or 0 for row in data)
	
	summary_data = {
		"data": [
			{
				"metric": _("Total Predictions"),
				"value": total_predictions
			},
			{
				"metric": _("Total Estimated Value"),
				"value": total_estimated_value
			},
			{
				"metric": _("Average Estimated Value"),
				"value": round(avg_estimated_value, 2)
			},
			{
				"metric": _("Total Number of Cuts"),
				"value": total_cuts
			},
			{
				"metric": _("Average Cuts per Prediction"),
				"value": round(avg_cuts_per_prediction, 1)
			},
			{
				"metric": _("Total Polished Carats"),
				"value": round(total_pol_cts, 2)
			}
		],
		"columns": [
			{
				"label": _("Metric"),
				"fieldname": "metric",
				"fieldtype": "Data",
				"width": 250
			},
			{
				"label": _("Value"),
				"fieldname": "value",
				"fieldtype": "Data",
				"width": 150
			}
		]
	}
	
	return summary_data
