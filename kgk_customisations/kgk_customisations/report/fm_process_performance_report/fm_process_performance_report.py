# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate
from datetime import datetime
import calendar
import math

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_summary(data)
	return columns, data, None, chart, summary

def get_columns(filters=None):
	"""Dynamically build columns with sections as column headers"""
	columns = [
		{
			"fieldname": "period",
			"fieldtype": "Data",
			"label": _("Period"),
			"width": 200,
			"filterable": 0,
			"align": "center"
		}
	]
	
	# Get all unique sections from Factory Main Item
	sections = frappe.db.sql("""
		SELECT DISTINCT fmi.section 
		FROM `tabFactory Main Item` fmi
		INNER JOIN `tabFactory Main` fm ON fm.name = fmi.parent
		WHERE fmi.section IS NOT NULL 
			AND fmi.section != ''
			AND fm.docstatus < 2
		ORDER BY fmi.section
	""", as_dict=1)
	
	# Add a column for each section
	for section in sections:
		section_name = section.section
		columns.append({
			"fieldname": frappe.scrub(section_name),
			"fieldtype": "Int",
			"label": _(section_name),
			"width": 150,
			"filterable": 0,
			"align": "center"
		})
	
	# Add total_days column at the end
	columns.append({
		"fieldname": "total_days",
		"fieldtype": "Int",
		"label": _("Total Days"),
		"width": 120,
		"filterable": 0,
		"align": "center"
	})
	
	return columns

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
	"""Get data grouped by date and section"""
	data = frappe.db.sql(f"""
		SELECT 
			fm.work_date as date,
			fmi.section,
			SUM(fmi.actual) as actual,
			(
				SELECT fmi2.reason 
				FROM `tabFactory Main Item` fmi2 
				WHERE fmi2.parent = fm.name 
					AND fmi2.reason IS NOT NULL 
				LIMIT 1
			) as reason
		FROM 
			`tabFactory Main` fm
		INNER JOIN 
			`tabFactory Main Item` fmi ON fm.name = fmi.parent
		WHERE 
			fm.docstatus < 2
			AND fmi.section IS NOT NULL 
			AND fmi.section != ''
			{conditions}
		GROUP BY 
			fm.work_date, fmi.section
		ORDER BY 
			fm.work_date, fmi.section
	""", filters, as_dict=1)
	
	return build_monthly_tree_structure(data)

def get_reason_wise_data(filters, conditions):
	"""Get data grouped by date, section, and reason"""
	data = frappe.db.sql(f"""
		SELECT 
			fm.work_date as date,
			fmi.section,
			COALESCE(fmi.reason, 'NO REASON') as reason,
			SUM(fmi.actual) as actual
		FROM 
			`tabFactory Main` fm
		INNER JOIN 
			`tabFactory Main Item` fmi ON fm.name = fmi.parent
		WHERE 
			fm.docstatus < 2
			AND fmi.section IS NOT NULL 
			AND fmi.section != ''
			{conditions}
		GROUP BY 
			fm.work_date, fmi.section, COALESCE(fmi.reason, 'NO REASON')
		ORDER BY 
			COALESCE(fmi.reason, 'NO REASON'), fm.work_date, fmi.section
	""", filters, as_dict=1)
	
	return build_reason_tree_structure(data)

def build_monthly_tree_structure(data):
	"""Build tree structure with sections as columns, grouped by month"""
	if not data:
		return []
	
	# Get all unique sections
	sections = frappe.db.sql("""
		SELECT DISTINCT section 
		FROM `tabFactory Main Item`
		WHERE section IS NOT NULL AND section != ''
		ORDER BY section
	""", as_dict=1)
	section_list = [s.section for s in sections]
	
	# Group data by month and date
	month_groups = {}
	date_groups = {}
	
	for row in data:
		date_obj = getdate(row.date)
		month_key = date_obj.strftime("%Y-%m")
		month_name = date_obj.strftime("%B %Y")
		date_key = row.date.strftime("%Y-%m-%d")
		
		# Initialize month group
		if month_key not in month_groups:
			month_groups[month_key] = {
				"period": month_name,
				"indent": 0,
				"is_group": 1,
				"dates": set(),  # Track unique dates for this month
				"section_days": {}  # Track days per section
			}
			for section in section_list:
				month_groups[month_key][frappe.scrub(section)] = 0
				month_groups[month_key]["section_days"][section] = set()
		
		# Initialize date group
		if date_key not in date_groups:
			date_groups[date_key] = {
				"period": formatdate(row.date, "dd-MMM-YYYY"),
				"indent": 1,
				"parent_key": month_key,
				"date": row.date,
				"section_days": set()
			}
			for section in section_list:
				date_groups[date_key][frappe.scrub(section)] = 0
		
		# Add actual value to the section column
		section_field = frappe.scrub(row.section)
		actual = math.ceil(flt(row.actual))
		
		date_groups[date_key][section_field] += actual
		month_groups[month_key][section_field] += actual
		
		# Track dates and sections for total_days calculation
		month_groups[month_key]["dates"].add(date_key)
		month_groups[month_key]["section_days"][row.section].add(date_key)
		date_groups[date_key]["section_days"].add(row.section)
	
	# Build final result
	result = []
	for month_key in sorted(month_groups.keys()):
		month_row = month_groups[month_key]
		
		# Calculate total days for month (sum of unique days across all sections)
		total_section_days = sum(len(days) for days in month_row["section_days"].values())
		month_row["total_days"] = total_section_days
		
		# Clean up tracking fields
		month_row.pop("dates", None)
		month_row.pop("section_days", None)
		
		result.append(month_row)
		
		# Add daily rows for this month
		daily_rows = []
		for dk in sorted(date_groups.keys()):
			if date_groups[dk].get("parent_key") == month_key:
				row = date_groups[dk]
				# Total days for a single date = number of sections that had data
				row["total_days"] = len(row.get("section_days", set()))
				row.pop("parent_key", None)
				row.pop("date", None)
				row.pop("section_days", None)
				daily_rows.append(row)
		
		result.extend(daily_rows)
	
	return result

def build_reason_tree_structure(data):
	"""Build tree structure with sections as columns, grouped by reason"""
	if not data:
		return []
	
	# Get all unique sections
	sections = frappe.db.sql("""
		SELECT DISTINCT section 
		FROM `tabFactory Main Item`
		WHERE section IS NOT NULL AND section != ''
		ORDER BY section
	""", as_dict=1)
	section_list = [s.section for s in sections]
	
	# Group data by reason and date
	reason_groups = {}
	date_groups = {}
	
	for row in data:
		reason = row.reason or "NO REASON"
		date_key = row.date.strftime("%Y-%m-%d")
		unique_key = f"{reason}_{date_key}"
		
		# Initialize reason group
		if reason not in reason_groups:
			reason_groups[reason] = {
				"period": reason,
				"indent": 0,
				"is_group": 1,
				"section_days": {}
			}
			for section in section_list:
				reason_groups[reason][frappe.scrub(section)] = 0
				reason_groups[reason]["section_days"][section] = set()
		
		# Initialize date group
		if unique_key not in date_groups:
			date_groups[unique_key] = {
				"period": formatdate(row.date, "dd-MMM-YYYY"),
				"indent": 1,
				"parent_key": reason,
				"date": row.date,
				"section_days": set()
			}
			for section in section_list:
				date_groups[unique_key][frappe.scrub(section)] = 0
		
		# Add actual value to the section column
		section_field = frappe.scrub(row.section)
		actual = math.ceil(flt(row.actual))
		
		date_groups[unique_key][section_field] += actual
		reason_groups[reason][section_field] += actual
		
		# Track sections for total_days calculation
		reason_groups[reason]["section_days"][row.section].add(date_key)
		date_groups[unique_key]["section_days"].add(row.section)
	
	# Build final result
	result = []
	for reason in sorted(reason_groups.keys()):
		reason_row = reason_groups[reason]
		
		# Calculate total days for reason
		total_section_days = sum(len(days) for days in reason_row["section_days"].values())
		reason_row["total_days"] = total_section_days
		reason_row.pop("section_days", None)
		
		result.append(reason_row)
		
		# Add daily rows for this reason
		daily_rows = []
		for dk in sorted(date_groups.keys()):
			if date_groups[dk].get("parent_key") == reason:
				row = date_groups[dk]
				row["total_days"] = len(row.get("section_days", set()))
				row.pop("parent_key", None)
				row.pop("date", None)
				row.pop("section_days", None)
				daily_rows.append(row)
		
		result.extend(daily_rows)
	
	return result

def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("fm.work_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("fm.work_date <= %(to_date)s")
		
	if filters.get("department"):
		conditions.append("fmi.section = %(department)s")
		
	if filters.get("factory_process"):
		conditions.append("fmi.type = %(factory_process)s")
	
	if filters.get("reason"):
		conditions.append("fmi.reason = %(reason)s")
		
	if filters.get("day_type") and filters.get("day_type") != "All":
		if filters.get("day_type") == "Normal":
			conditions.append("DAYOFWEEK(fm.work_date) NOT IN (1, 7)")  # Not Sunday or Saturday
		elif filters.get("day_type") == "Weekend":
			conditions.append("DAYOFWEEK(fm.work_date) IN (1, 7)")  # Sunday or Saturday
	
	return " AND " + " AND ".join(conditions) if conditions else ""

def get_chart_data(data, filters):
	if not data:
		return None
	
	# Get only daily data (indent == 1) for the chart
	daily_data = [row for row in data if row.get("indent") == 1]
	
	if not daily_data:
		return None
	
	# Get all section columns (exclude period, total_days, indent, is_group)
	sections = frappe.db.sql("""
		SELECT DISTINCT section 
		FROM `tabFactory Main Item`
		WHERE section IS NOT NULL AND section != ''
		ORDER BY section
	""", as_dict=1)
	
	section_names = [s.section for s in sections]
	section_totals = []
	
	for section in section_names:
		section_field = frappe.scrub(section)
		total = sum(math.ceil(flt(row.get(section_field, 0))) for row in daily_data)
		section_totals.append(total)
	
	return {
		"data": {
			"labels": section_names,
			"datasets": [
				{
					"name": "Actual Production",
					"chartType": "bar",
					"values": section_totals,
					"color": "#4ECDC4"
				}
			]
		},
		"type": "bar",
		"height": 300,
		"colors": ["#4ECDC4"]
	}

def get_summary(data):
	if not data:
		return []
	
	# Calculate totals from daily data only (indent == 1)
	daily_data = [row for row in data if row.get("indent") == 1]
	
	if not daily_data:
		return []
	
	# Get all sections
	sections = frappe.db.sql("""
		SELECT DISTINCT section 
		FROM `tabFactory Main Item`
		WHERE section IS NOT NULL AND section != ''
		ORDER BY section
	""", as_dict=1)
	
	# Calculate total actual across all sections
	total_actual = 0
	for section in sections:
		section_field = frappe.scrub(section.section)
		total_actual += sum(math.ceil(flt(row.get(section_field, 0))) for row in daily_data)
	
	# Calculate grand total days (sum of all total_days from daily rows)
	grand_total_days = sum(row.get("total_days", 0) for row in daily_data)
	
	return [
		{
			"value": len(daily_data),
			"label": "Total Records",
			"datatype": "Int",
			"currency": None
		},
		{
			"value": total_actual,
			"label": "Total Actual Production",
			"datatype": "Int",
			"currency": None,
			"indicator": "Blue"
		},
		{
			"value": grand_total_days,
			"label": "Grand Total Days Worked",
			"datatype": "Int",
			"currency": None,
			"indicator": "Green"
		}
	]
