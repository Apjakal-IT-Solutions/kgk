# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, add_months, get_first_day, get_last_day
from datetime import datetime
import calendar
import math
import math

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_summary(data)
	return columns, data, None, chart, summary

def get_columns():
	return [
		{
			"fieldname": "period",
			"fieldtype": "Data",
			"label": _("Period"),
			"width": 5000,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "round_target",
			"fieldtype": "Int",
			"label": _("Round Target"),
			"width": 250,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "fancy_target",
			"fieldtype": "Int",
			"label": _("Fancy Target"),
			"width": 250,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "target",
			"fieldtype": "Int",
			"label": _("Target Total"),
			"width": 250,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "round_ct",
			"fieldtype": "Int",
			"label": _("Round Ct"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "fancy_ct",
			"fieldtype": "Int",
			"label": _("Fancy Ct"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "actual",
			"fieldtype": "Int", 
			"label": _("Actual Total"),
			"width": 220,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "diff",
			"fieldtype": "Int",
			"label": _("Diff."),
			"width": 180,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "diff_percentage",
			"fieldtype": "Int",
			"label": _("Diff. %"),
			"width": 180,
			"filterable": 0,
			"align": "center"
		}
	]

def get_data(filters):
	if not filters:
		filters = {
			"from_date": "2025-07-01",
			"to_date": "2025-11-30",
			"view_type": "Monthly"
		}
		
	conditions = get_conditions(filters)
	view_type = filters.get("view_type", "Monthly")
	
	# Debug: Print the filters being used
	frappe.log_error(f"Planning Report Filters: {filters}", "Planning Report Debug")
	
	if view_type == "Reason-wise":
		return get_reason_wise_data(filters, conditions)
	else:
		return get_monthly_data(filters, conditions)

def get_monthly_data(filters, conditions):
	# Get data from Planning Main with all fields
	data = frappe.db.sql(f"""
		SELECT 
			pm.date,
			SUM(pm.round_target) as round_target,
			SUM(pm.fancy_target) as fancy_target,
			SUM(pm.target_total) as target,
			SUM(pm.round_actual) as round_ct,
			SUM(pm.fancy_actual) as fancy_ct,
			SUM(pm.actual_total) as actual,
			(
				SELECT pm2.fancy_reason 
				FROM `tabPlanning Main` pm2 
				WHERE pm2.date = pm.date 
					AND pm2.docstatus < 2 
					AND pm2.fancy_reason IS NOT NULL 
				LIMIT 1
			) as reason
		FROM 
			`tabPlanning Main` pm
		WHERE 
			pm.docstatus < 2
			{conditions}
		GROUP BY 
			pm.date
		ORDER BY 
			pm.date
	""", filters, as_dict=1)
	
	return build_tree_structure(data)

def get_reason_wise_data(filters, conditions):
	# Get data from Planning Main with all fields, grouped by reason but still showing individual dates
	data = frappe.db.sql(f"""
		SELECT 
			pm.date,
			COALESCE(pm.fancy_reason, 'NO REASON') as reason,
			SUM(pm.round_target) as round_target,
			SUM(pm.fancy_target) as fancy_target,
			SUM(pm.target_total) as target,
			SUM(pm.round_actual) as round_ct,
			SUM(pm.fancy_actual) as fancy_ct,
			SUM(pm.actual_total) as actual
		FROM 
			`tabPlanning Main` pm
		WHERE 
			pm.docstatus < 2
			{conditions}
		GROUP BY 
			pm.date, COALESCE(pm.fancy_reason, 'NO REASON')
		ORDER BY 
			COALESCE(pm.fancy_reason, 'NO REASON'), pm.date
	""", filters, as_dict=1)
	
	return build_reason_tree_structure(data)

def build_reason_tree_structure(data):
	# Process data for tree structure grouped by reason
	tree_data = []
	reason_groups = {}
	
	for row in data:
		# Calculate values with integer rounding
		round_target = math.ceil(flt(row.round_target))
		fancy_target = math.ceil(flt(row.fancy_target))
		target = math.ceil(flt(row.target))
		round_ct = math.ceil(flt(row.round_ct))
		fancy_ct = math.ceil(flt(row.fancy_ct))
		actual = math.ceil(flt(row.actual))
		diff = actual - target
		diff_percentage = math.ceil((diff / target * 100)) if target else 0
		
		reason_key = row.reason
		
		# Initialize reason group if not exists
		if reason_key not in reason_groups:
			reason_groups[reason_key] = {
				"period": reason_key,  # Display reason name in tree
				"round_target": 0,
				"fancy_target": 0,
				"target": 0,
				"round_ct": 0,
				"fancy_ct": 0,
				"actual": 0,
				"diff": 0,
				"diff_percentage": 0,
				"indent": 0,
				"is_group": 1
			}
		
		# Add to reason totals
		reason_groups[reason_key]["round_target"] += round_target
		reason_groups[reason_key]["fancy_target"] += fancy_target
		reason_groups[reason_key]["target"] += target
		reason_groups[reason_key]["round_ct"] += round_ct
		reason_groups[reason_key]["fancy_ct"] += fancy_ct
		reason_groups[reason_key]["actual"] += actual
		reason_groups[reason_key]["diff"] += diff
		
		# Add daily row
		tree_data.append({
			"period": formatdate(row.date, "dd-MMM-YYYY"),
			"date": row.date,  # Keep for sorting
			"round_target": round_target,
			"fancy_target": fancy_target,
			"target": target,
			"round_ct": round_ct,
			"fancy_ct": fancy_ct,
			"actual": actual,
			"diff": diff,
			"diff_percentage": diff_percentage,
			"indent": 1,
			"parent_key": reason_key
		})
	
	# Calculate reason percentages
	for reason_data in reason_groups.values():
		if reason_data["target"]:
			reason_data["diff_percentage"] = math.ceil((reason_data["diff"] / reason_data["target"]) * 100)
	
	# Build final tree structure
	result = []
	for reason_key in sorted(reason_groups.keys()):
		# Add reason header
		result.append(reason_groups[reason_key])
		
		# Add daily entries for this reason
		daily_rows = [row for row in tree_data if row.get("parent_key") == reason_key]
		daily_rows.sort(key=lambda x: x["date"])
		
		# Remove internal fields before adding to result
		for row in daily_rows:
			row.pop("parent_key", None)
			row.pop("date", None)  # Remove date field, keep only period for display
		
		result.extend(daily_rows)
	
	return result

def build_tree_structure(data):
	# Process data for tree structure with all fields
	tree_data = []
	monthly_groups = {}
	
	for row in data:
		# Calculate values with integer rounding
		round_target = math.ceil(flt(row.round_target))
		fancy_target = math.ceil(flt(row.fancy_target))
		target = math.ceil(flt(row.target))
		round_ct = math.ceil(flt(row.round_ct))
		fancy_ct = math.ceil(flt(row.fancy_ct))
		actual = math.ceil(flt(row.actual))
		diff = actual - target
		diff_percentage = math.ceil((diff / target * 100)) if target else 0
		
		# Format month key
		date_obj = getdate(row.date)
		month_key = date_obj.strftime("%b-%Y")  # e.g., "Nov-2025"
		month_name = date_obj.strftime("%B %Y")  # e.g., "November 2025"
		
		# Initialize monthly group if not exists
		if month_key not in monthly_groups:
			monthly_groups[month_key] = {
				"period": month_name,
				"round_target": 0,
				"fancy_target": 0,
				"target": 0,
				"round_ct": 0,
				"fancy_ct": 0,
				"actual": 0,
				"diff": 0,
				"diff_percentage": 0,
				"indent": 0,
				"is_group": 1
			}
		
		# Add to monthly totals
		monthly_groups[month_key]["round_target"] += round_target
		monthly_groups[month_key]["fancy_target"] += fancy_target
		monthly_groups[month_key]["target"] += target
		monthly_groups[month_key]["round_ct"] += round_ct
		monthly_groups[month_key]["fancy_ct"] += fancy_ct
		monthly_groups[month_key]["actual"] += actual
		monthly_groups[month_key]["diff"] += diff
		
		# Add daily row
		tree_data.append({
			"period": formatdate(row.date, "dd-MMM-YYYY"),
			"date": row.date,  # Keep for sorting
			"round_target": round_target,
			"fancy_target": fancy_target,
			"target": target,
			"round_ct": round_ct,
			"fancy_ct": fancy_ct,
			"actual": actual,
			"diff": diff,
			"diff_percentage": diff_percentage,
			"indent": 1,
			"parent_key": month_key
		})
	
	# Calculate monthly percentages
	for month_data in monthly_groups.values():
		if month_data["target"]:
			month_data["diff_percentage"] = math.ceil((month_data["diff"] / month_data["target"]) * 100)
	
	# Build final tree structure
	result = []
	
	# If no monthly groups created, return simple flat data
	if not monthly_groups:
		for row in tree_data:
			if row.get("period"):
				row.pop("parent_key", None)
				row.pop("date", None)  # Remove internal date field
				row["indent"] = 0
				result.append(row)
		return result
	
	# Normal tree structure
	for month_key in sorted(monthly_groups.keys()):
		# Add month header
		result.append(monthly_groups[month_key])
		
		# Add daily entries for this month
		daily_rows = [row for row in tree_data if row.get("parent_key") == month_key]
		daily_rows.sort(key=lambda x: x["date"])
		
		# Remove internal fields before adding to result
		for row in daily_rows:
			row.pop("parent_key", None)
			row.pop("date", None)  # Remove date field, keep only period for display
		
		result.extend(daily_rows)
	
	return result

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("pm.date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("pm.date <= %(to_date)s")
		
	if filters.get("reason"):
		conditions.append("pm.fancy_reason = %(reason)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data, filters):
	if not data:
		return None
		
	view_type = filters.get("view_type", "Monthly")
	
	# Get daily data only (not group headers) for both view types
	daily_data = [row for row in data if row.get("indent") == 1]
	
	if not daily_data:
		return None
	
	# Prepare chart data
	labels = []
	targets = []
	actuals = []
	
	for row in daily_data:
		if view_type == "Reason-wise":
			# For reason view, show period with reason context from parent
			label = row["period"][:10]  # Truncate date for chart readability
		else:
			# For monthly view, show period (date)
			label = row["period"][:10]  # Truncate for readability
		
		labels.append(label)
		targets.append(math.ceil(flt(row["target"])))
		actuals.append(math.ceil(flt(row["actual"])))
	
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": "Target",
					"chartType": "line",
					"values": targets,
					"color": "#36A2EB"
				},
				{
					"name": "Actual", 
					"chartType": "line",
					"values": actuals,
					"color": "#4BC0C0"
				}
			]
		},
		"type": "line",
		"height": 300,
		"colors": ["#36A2EB", "#4BC0C0"]
	}

def get_summary(data):
	if not data:
		return []
	
	# Calculate totals from appropriate data based on view
	data_to_sum = data
	if any(row.get("indent") == 1 for row in data):
		# Monthly view - use daily data only
		data_to_sum = [row for row in data if row.get("indent") == 1]
	
	total_round_target = math.ceil(sum(flt(row.get("round_target", 0)) for row in data_to_sum))
	total_fancy_target = math.ceil(sum(flt(row.get("fancy_target", 0)) for row in data_to_sum))
	total_target = math.ceil(sum(flt(row["target"]) for row in data_to_sum))
	total_round_ct = math.ceil(sum(flt(row.get("round_ct", 0)) for row in data_to_sum))
	total_fancy_ct = math.ceil(sum(flt(row.get("fancy_ct", 0)) for row in data_to_sum))
	total_actual = math.ceil(sum(flt(row["actual"]) for row in data_to_sum))
	total_diff = total_actual - total_target
	total_diff_percentage = math.ceil((total_diff / total_target * 100)) if total_target else 0
	
	return [
		{
			"value": total_round_target,
			"label": "Total Round Target",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_fancy_target,
			"label": "Total Fancy Target",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_target,
			"label": "Total Target",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_round_ct,
			"label": "Total Round Ct",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_fancy_ct,
			"label": "Total Fancy Ct",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_actual,
			"label": "Total Actual", 
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_diff,
			"label": "Total Difference",
			"datatype": "Int", 
			"currency": None,
			"indicator": "Green" if total_diff >= 0 else "Red"
		},
		{
			"value": total_diff_percentage,
			"label": "Overall Performance",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green" if total_diff_percentage >= 0 else "Red"
		}
	]
