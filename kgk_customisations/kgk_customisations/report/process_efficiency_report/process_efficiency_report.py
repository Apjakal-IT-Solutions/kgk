# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
import math
from kgk_customisations.kgk_customisations.utils.query_builder import SafeQueryBuilder

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
			"width": 250,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "factory_process",
			"label": _("Process"),
			"fieldtype": "Link",
			"options": "Factory Process",
			"width": 200,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "target",
			"label": _("Target"),
			"fieldtype": "Int",
			"width": 150,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "actual",
			"label": _("Actual"),
			"fieldtype": "Int",
			"width": 150,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "diff",
			"label": _("Variance"),
			"fieldtype": "Int",
			"width": 150,
			"filterable": 0,
			"align": "center"
		},
		{
			"fieldname": "achievement",
			"label": _("Achievement %"),
			"fieldtype": "Int",
			"width": 150,
			"filterable": 0,
			"align": "center"
		}
	]

def get_data(filters):
	if not filters:
		filters = {
			"from_date": frappe.utils.get_first_day(frappe.utils.today()),
			"to_date": frappe.utils.get_last_day(frappe.utils.today()),
			"view_type": "Monthly"
		}
		
	conditions = get_conditions(filters)
	view_type = filters.get("view_type", "Monthly")
	
	if view_type == "Reason-wise":
		return get_reason_wise_data(filters, conditions)
	else:
		return get_monthly_data(filters, conditions)

def get_monthly_data(filters, conditions):
	"""Get data grouped by date and process"""
	query = """
		SELECT 
			fe.work_date as date,
			fei.factory_process,
			SUM(CAST(fei.target AS DECIMAL(10,2))) as target,
			SUM(fei.actual) as actual,
			(
				SELECT fei2.reason 
				FROM `tabFactory Entry Item` fei2 
				WHERE fei2.parent = fe.name 
					AND fei2.reason IS NOT NULL 
				LIMIT 1
			) as reason
		FROM 
			`tabFactory Entry` fe
		INNER JOIN 
			`tabFactory Entry Item` fei ON fe.name = fei.parent
		WHERE 
			fe.docstatus < 2
			AND fei.factory_process IS NOT NULL 
			AND fei.factory_process != ''
	"""
	
	params = {}
	if filters.get("from_date"):
		query += " AND fe.work_date >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		query += " AND fe.work_date <= %(to_date)s"
		params["to_date"] = filters.get("to_date")
	
	query += """
		GROUP BY 
			fe.work_date, fei.factory_process
		ORDER BY 
			fe.work_date, fei.factory_process
	"""
	
	data = frappe.db.sql(query, params, as_dict=1)
	
	return build_monthly_tree_structure(data)

def get_reason_wise_data(filters, conditions):
	"""Get data grouped by reason, date, and process"""
	query = """
		SELECT 
			fe.work_date as date,
			fei.factory_process,
			COALESCE(fei.reason, 'NO REASON') as reason,
			SUM(CAST(fei.target AS DECIMAL(10,2))) as target,
			SUM(fei.actual) as actual
		FROM 
			`tabFactory Entry` fe
		INNER JOIN 
			`tabFactory Entry Item` fei ON fe.name = fei.parent
		WHERE 
			fe.docstatus < 2
			AND fei.factory_process IS NOT NULL 
			AND fei.factory_process != ''
	"""
	
	params = {}
	if filters.get("from_date"):
		query += " AND fe.work_date >= %(from_date)s"
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		query += " AND fe.work_date <= %(to_date)s"
		params["to_date"] = filters.get("to_date")
	
	query += """
		GROUP BY 
			fe.work_date, fei.factory_process, COALESCE(fei.reason, 'NO REASON')
		ORDER BY 
			COALESCE(fei.reason, 'NO REASON'), fe.work_date, fei.factory_process
	"""
	
	data = frappe.db.sql(query, params, as_dict=1)
	
	return build_reason_tree_structure(data)

def build_monthly_tree_structure(data):
	"""Build tree structure grouped by month"""
	if not data:
		return []
	
	tree_data = []
	monthly_groups = {}
	
	for row in data:
		# Calculate values with integer rounding
		target = math.ceil(flt(row.target))
		actual = math.ceil(flt(row.actual))
		diff = actual - target
		achievement = math.ceil((actual / target * 100)) if target else 0
		
		# Format month key
		date_obj = getdate(row.date)
		month_key = date_obj.strftime("%b-%Y")
		month_name = date_obj.strftime("%B %Y")
		
		# Initialize monthly group if not exists
		if month_key not in monthly_groups:
			monthly_groups[month_key] = {
				"period": month_name,
				"factory_process": "",
				"target": 0,
				"actual": 0,
				"diff": 0,
				"achievement": 0,
				"indent": 0,
				"is_group": 1
			}
		
		# Add to monthly totals
		monthly_groups[month_key]["target"] += target
		monthly_groups[month_key]["actual"] += actual
		monthly_groups[month_key]["diff"] += diff
		
		# Add daily row
		tree_data.append({
			"period": formatdate(row.date, "dd-MMM-YYYY"),
			"factory_process": row.factory_process,
			"target": target,
			"actual": actual,
			"diff": diff,
			"achievement": achievement,
			"indent": 1,
			"parent_key": month_key
		})
	
	# Recalculate achievement for monthly totals
	for month_key, month_data in monthly_groups.items():
		if month_data["target"] > 0:
			month_data["achievement"] = math.ceil((month_data["actual"] / month_data["target"] * 100))
	
	# Build final tree with monthly groups first, then their children
	result = []
	for month_key in sorted(monthly_groups.keys()):
		result.append(monthly_groups[month_key])
		# Add children for this month
		for row in tree_data:
			if row.get("parent_key") == month_key:
				result.append(row)
	
	return result

def build_reason_tree_structure(data):
	"""Build tree structure grouped by reason"""
	if not data:
		return []
	
	tree_data = []
	reason_groups = {}
	
	for row in data:
		# Calculate values with integer rounding
		target = math.ceil(flt(row.target))
		actual = math.ceil(flt(row.actual))
		diff = actual - target
		achievement = math.ceil((actual / target * 100)) if target else 0
		
		reason_key = row.reason
		
		# Initialize reason group if not exists
		if reason_key not in reason_groups:
			reason_groups[reason_key] = {
				"period": reason_key,
				"factory_process": "",
				"target": 0,
				"actual": 0,
				"diff": 0,
				"achievement": 0,
				"indent": 0,
				"is_group": 1
			}
		
		# Add to reason totals
		reason_groups[reason_key]["target"] += target
		reason_groups[reason_key]["actual"] += actual
		reason_groups[reason_key]["diff"] += diff
		
		# Add daily row
		tree_data.append({
			"period": formatdate(row.date, "dd-MMM-YYYY"),
			"factory_process": row.factory_process,
			"target": target,
			"actual": actual,
			"diff": diff,
			"achievement": achievement,
			"indent": 1,
			"parent_key": reason_key
		})
	
	# Recalculate achievement for reason totals
	for reason_key, reason_data in reason_groups.items():
		if reason_data["target"] > 0:
			reason_data["achievement"] = math.ceil((reason_data["actual"] / reason_data["target"] * 100))
	
	# Build final tree with reason groups first, then their children
	result = []
	for reason_key in sorted(reason_groups.keys()):
		result.append(reason_groups[reason_key])
		# Add children for this reason
		for row in tree_data:
			if row.get("parent_key") == reason_key:
				result.append(row)
	
	return result

def get_conditions(filters):
	conditions = ""
	
	if filters.get("from_date"):
		conditions += " AND fe.work_date >= %(from_date)s"
	
	if filters.get("to_date"):
		conditions += " AND fe.work_date <= %(to_date)s"
	
	if filters.get("factory_process"):
		conditions += " AND fei.factory_process = %(factory_process)s"
	
	if filters.get("reason"):
		conditions += " AND fei.reason = %(reason)s"
	
	return conditions

def get_summary(data):
	if not data:
		return []
	
	# Calculate totals from daily data only (indent == 1)
	daily_data = [row for row in data if row.get("indent") == 1]
	
	if not daily_data:
		return []
	
	total_target = math.ceil(sum(flt(d.get("target", 0)) for d in daily_data))
	total_actual = math.ceil(sum(flt(d.get("actual", 0)) for d in daily_data))
	total_diff = total_actual - total_target
	overall_achievement = math.ceil((total_actual / total_target * 100)) if total_target > 0 else 0
	
	return [
		{
			"value": len(daily_data),
			"label": "Total Records",
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
			"value": total_actual,
			"label": "Total Actual",
			"datatype": "Int",
			"currency": None,
			"indicator": "Blue"
		},
		{
			"value": total_diff,
			"label": "Total Variance",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green" if total_diff >= 0 else "Red"
		},
		{
			"value": overall_achievement,
			"label": "Overall Achievement",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green" if overall_achievement >= 100 else "Red"
		}
	]

def get_chart_data(data, filters):
	if not data:
		return None
	
	# Get daily data only
	daily_data = [row for row in data if row.get("indent") == 1]
	
	if not daily_data:
		return None
	
	# Group by process
	process_data = {}
	for row in daily_data:
		process = row.get("factory_process", "Unknown")
		if process not in process_data:
			process_data[process] = {"target": 0, "actual": 0}
		process_data[process]["target"] += flt(row.get("target", 0))
		process_data[process]["actual"] += flt(row.get("actual", 0))
	
	# Sort by actual for better visualization
	processes_sorted = sorted(process_data.items(), key=lambda x: x[1]["actual"], reverse=True)[:10]
	
	return {
		"data": {
			"labels": [p[0] for p in processes_sorted],
			"datasets": [
				{
					"name": "Target",
					"chartType": "bar",
					"values": [math.ceil(p[1]["target"]) for p in processes_sorted],
					"color": "#FF6B6B"
				},
				{
					"name": "Actual",
					"chartType": "bar",
					"values": [math.ceil(p[1]["actual"]) for p in processes_sorted],
					"color": "#4ECDC4"
				}
			]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#FF6B6B", "#4ECDC4"]
	}
