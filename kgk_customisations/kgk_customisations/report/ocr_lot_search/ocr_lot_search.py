# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	"""
	OCR Lot Search Report
	Searches for lot IDs across all OCR Data Upload records
	"""
	data = get_data(filters)
	columns = get_columns(data)
	chart = None
	summary = get_report_summary(data)
	
	return columns, data, None, chart, summary


def get_columns(data):
	"""Define report columns - only show columns with non-empty values"""
	
	# Define all possible columns
	all_columns = [
		{
			"label": _("Text Data"),
			"fieldname": "text_data",
			"fieldtype": "Text",
			"width": 200
		},
		{
			"label": _("Lot ID 1"),
			"fieldname": "lot_id_1",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Sub Lot ID"),
			"fieldname": "sub_lot_id",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Result"),
			"fieldname": "result",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Color"),
			"fieldname": "color",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Blue UV"),
			"fieldname": "blue_uv",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Yellow UV"),
			"fieldname": "yellow_uv",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Brown"),
			"fieldname": "brown",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Type"),
			"fieldname": "type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Fancy Yellow"),
			"fieldname": "fancy_yellow",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Result"),
			"fieldname": "refined_result",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Color"),
			"fieldname": "refined_color",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Blue UV"),
			"fieldname": "refined_blue_uv",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Brown"),
			"fieldname": "refined_brown",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Yellow UV"),
			"fieldname": "refined_yellow_uv",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Type"),
			"fieldname": "refined_type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Fancy Yellow"),
			"fieldname": "refined_fancy_yellow",
			"fieldtype": "Data",
			"width": 150
		}
	]
	
	# If no data, return all columns
	if not data:
		return all_columns
	
	# Check which columns have at least one non-empty value
	columns_with_data = []
	for col in all_columns:
		fieldname = col["fieldname"]
		has_data = False
		
		for row in data:
			value = row.get(fieldname)
			# Check if value is not None, not empty string, and not just whitespace
			if value and str(value).strip():
				has_data = True
				break
		
		# Include column if it has data
		if has_data:
			columns_with_data.append(col)
	
	# Return columns with data, or all columns if none have data
	return columns_with_data if columns_with_data else all_columns


def get_data(filters):
	"""Fetch OCR data based on lot ID search - matches cumulative report format"""
	
	if not filters.get("lot_id"):
		frappe.msgprint(_("Please enter a Lot ID to search"))
		return []
	
	conditions = get_conditions(filters)
	
	# Query to search across all OCR data items with refined fields
	query = """
		SELECT 
			odu.name as upload_document,
			odu.upload_date,
			odi.sequence,
			odi.created_on,
			odi.batch_name,
			odi.text_data,
			odi.lot_id_1,
			odi.lot_id_2,
			odi.sub_lot_id,
			odi.result,
			odi.color,
			odi.blue_uv,
			odi.yellow_uv,
			odi.brown,
			odi.type,
			odi.fancy_yellow
		FROM 
			`tabOCR Data Item` odi
		INNER JOIN 
			`tabOCR Data Upload` odu ON odu.name = odi.parent
		WHERE
			{conditions}
		ORDER BY 
			odu.upload_date DESC, odi.sequence
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Add refined fields by extracting from text_data (same as cumulative report)
	from kgk_customisations.utils.ocr_utils import extract_ocr_fields_from_text
	
	for row in data:
		# Truncate text_data for display (same as cumulative report)
		if row.get("text_data"):
			row["text_data"] = (row["text_data"] or "")[:1000]
		
		# Extract refined fields if text_data exists
		if row.get("text_data") and row.get("text_data").strip():
			try:
				refined_data = extract_ocr_fields_from_text(row["text_data"])
				row["refined_result"] = refined_data.get("Result", "")
				row["refined_color"] = refined_data.get("Color", "")
				row["refined_blue_uv"] = refined_data.get("Blue UV", "")
				row["refined_brown"] = refined_data.get("Brown", "")
				row["refined_yellow_uv"] = refined_data.get("Yellow UV", "")
				row["refined_type"] = refined_data.get("Type", "")
				row["refined_fancy_yellow"] = refined_data.get("Fancy Yellow", "")
			except Exception as e:
				# Add empty refined fields on error
				row["refined_result"] = ""
				row["refined_color"] = ""
				row["refined_blue_uv"] = ""
				row["refined_brown"] = ""
				row["refined_yellow_uv"] = ""
				row["refined_type"] = ""
				row["refined_fancy_yellow"] = ""
				frappe.log_error(f"OCR refinement error: {str(e)}")
		else:
			# Add empty refined fields if no text data
			row["refined_result"] = ""
			row["refined_color"] = ""
			row["refined_blue_uv"] = ""
			row["refined_brown"] = ""
			row["refined_yellow_uv"] = ""
			row["refined_type"] = ""
			row["refined_fancy_yellow"] = ""
		
		# Abbreviate "NOT MEASURED" to "N/M" in all fields (after refined field extraction)
		for field in ["brown", "refined_brown", "blue_uv", "refined_blue_uv", "yellow_uv", "refined_yellow_uv", "type", "refined_type"]:
			if row.get(field):
				# Normalize whitespace and check for "NOT MEASURED" variations
				# Handle cases like "NOT MEASURED", "NOT MEASURED -", "NOT  MEASURED", etc.
				value_normalized = " ".join(str(row.get(field)).upper().split())
				if value_normalized.startswith("NOT MEASURED"):
					row[field] = "N/M"
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions based on filters"""
	conditions = ["1=1"]
	
	lot_id = filters.get("lot_id")
	search_field = filters.get("search_field", "Lot ID 1")
	
	# Build lot ID search conditions based on selected field
	if lot_id:
		lot_id_pattern = f"%{lot_id}%"
		
		if search_field == "All Fields":
			conditions.append("""(
				odi.lot_id_1 LIKE %(lot_id_pattern)s 
				OR odi.lot_id_2 LIKE %(lot_id_pattern)s 
				OR odi.sub_lot_id LIKE %(lot_id_pattern)s 
				OR odi.batch_name LIKE %(lot_id_pattern)s
			)""")
			filters["lot_id_pattern"] = lot_id_pattern
		elif search_field == "Lot ID 1":
			conditions.append("odi.lot_id_1 LIKE %(lot_id_pattern)s")
			filters["lot_id_pattern"] = lot_id_pattern
		elif search_field == "Lot ID 2":
			conditions.append("odi.lot_id_2 LIKE %(lot_id_pattern)s")
			filters["lot_id_pattern"] = lot_id_pattern
		elif search_field == "Sub Lot ID":
			conditions.append("odi.sub_lot_id LIKE %(lot_id_pattern)s")
			filters["lot_id_pattern"] = lot_id_pattern
		elif search_field == "Batch Name":
			conditions.append("odi.batch_name LIKE %(lot_id_pattern)s")
			filters["lot_id_pattern"] = lot_id_pattern
	
	# Date range filters
	if filters.get("from_date"):
		conditions.append("odu.upload_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("odu.upload_date <= %(to_date)s")
	
	return " AND ".join(conditions)


def get_report_summary(data):
	"""Calculate summary statistics"""
	if not data:
		return []
	
	total_records = len(data)
	unique_uploads = len(set(row.get("upload_document") for row in data if row.get("upload_document")))
	unique_lot_id_1 = len(set(row.get("lot_id_1") for row in data if row.get("lot_id_1")))
	unique_lot_id_2 = len(set(row.get("lot_id_2") for row in data if row.get("lot_id_2")))
	
	summary = [
		{
			"value": total_records,
			"indicator": "Blue",
			"label": _("Total Records Found"),
			"datatype": "Int"
		},
		{
			"value": unique_uploads,
			"indicator": "Green",
			"label": _("Upload Documents"),
			"datatype": "Int"
		},
		{
			"value": unique_lot_id_1,
			"indicator": "Orange",
			"label": _("Unique Lot ID 1"),
			"datatype": "Int"
		},
		{
			"value": unique_lot_id_2,
			"indicator": "Purple",
			"label": _("Unique Lot ID 2"),
			"datatype": "Int"
		}
	]
	
	return summary
