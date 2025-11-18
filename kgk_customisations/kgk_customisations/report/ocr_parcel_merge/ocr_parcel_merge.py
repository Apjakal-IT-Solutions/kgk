# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

"""
OCR Parcel Merge Report
======================

Script Report to merge OCR consolidated data with uploaded Parcel files.
Matches OCR lot_id fields with Parcel barcode fields and generates
comprehensive merge analysis with export capabilities.

Features:
- Match OCR data (lot_id_1, lot_id_2, sub_lot_id) with Parcel data (barcode)
- Multiple matching modes: Strict, Fuzzy, All Matches
- Export matched/unmatched records separately
- Complete merge report with confidence scoring
- Uses centralized utilities for consistent data processing

Dependencies:
- kgk_customisations.uti		filenam		filename = f"ocr_parcel_complete_analysis_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
		
		# Use centralized Excel utility
		workbook_result = create_styled_excel_workbook(sheets_data, "ocr_parcel_complete")
		if not workbook_result.get("success"):
			frappe.throw(f"Failed to create Excel workbook: {workbook_result.get('message', 'Unknown error')}")
			
		workbook = workbook_result["workbook"]ocr_parcel_matched_{frappe.utils.now_datetime().strftime('%Y		# Use centralized Excel utility
		excel_result = create_styled_excel_workbook(sheets_data, "ocr_parcel_matched")
		if not excel_result.get("success"):
			frappe.throw("Failed to create Excel workbook")
		
		workbook = excel_result.get("workbook")
		return create_download_response(workbook, filename)d_%H%M%S')}.xlsx"
		
		# Use centralized Excel utility
		workbook = create_styled_excel_workbook(sheets_data, "ocr_parcel_matched")_utils (OCR data retrieval)
- kgk_customisations.utils.file_utils (Parcel file processing) 
- kgk_customisations.utils.excel_utils (Export functionality)
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, today, formatdate
import pandas as pd
import re
from difflib import SequenceMatcher
from kgk_customisations.utils.ocr_utils import get_consolidated_ocr_data
from kgk_customisations.utils.file_utils import read_excel_file_safely, get_file_path_from_url
from kgk_customisations.utils.excel_utils import create_styled_excel_workbook, create_download_response


def execute(filters=None):
	"""
	Main function for the OCR Parcel Merge report.
	Shows all columns from OCR and attached file for matched records ONLY.
	
	Args:
		filters: Dict containing report filters including parcel_file
		
	Returns:
		Tuple (columns, data, message, chart) for report display
	"""
	try:
		# Handle case when no filters are provided (initial page load)
		if not filters:
			return get_basic_columns(), [create_info_row("Please select a parcel file and configure filters to run the analysis")]
		
		# Validate filters and parcel file
		validation_result = validate_filters(filters)
		if not validation_result["valid"]:
			return get_basic_columns(), [create_info_row(validation_result["message"])]
		
		# Get OCR data using centralized utility
		ocr_data = get_ocr_data(filters)
		if not ocr_data:
			return get_basic_columns(), [create_info_row("No OCR data found in the system")]
		
		# Get and validate Parcel data
		parcel_result = get_parcel_data(filters)
		if not parcel_result["success"]:
			return get_basic_columns(), [create_error_row(parcel_result["message"])]
		
		parcel_data = parcel_result["data"]
		parcel_columns = parcel_result.get("columns", [])
		barcode_field = parcel_result.get("barcode_field", "barcode")  # Get which field to use
		
		if not parcel_data:
			return get_basic_columns(), [create_info_row("No valid parcel data found in uploaded file")]
		
		# Perform matching between OCR and Parcel data
		merge_result = perform_merge_analysis(ocr_data, parcel_data, filters, barcode_field)
		all_records = merge_result.get("all_records", [])
		matched_pairs = merge_result.get("matched_pairs", [])
		unmatched_ocr = merge_result.get("unmatched_ocr", [])
		unmatched_parcels = merge_result.get("unmatched_parcels", [])
		
		# Calculate statistics - focus on UNIQUE BARCODE VALUES
		# Count how many distinct barcode values were matched
		matched_barcodes = set()
		
		for m in matched_pairs:
			if m.get("is_matched"):
				ocr_data = m.get("ocr_data")
				if ocr_data:
					barcode_value = str(ocr_data.get("lot_id_1", "")).strip().upper()
					if barcode_value and barcode_value != "NONE":
						matched_barcodes.add(barcode_value)
		
		unique_barcode_count = len(matched_barcodes)
		
		# Calculate DISTINCT barcode values and distribution
		barcode_distribution = {}
		distinct_barcodes = set()
		
		for match in matched_pairs:
			if match.get("is_matched"):
				ocr_data = match.get("ocr_data")
				parcel_data = match.get("parcel_data")
				
				if ocr_data and parcel_data:
					# Get the barcode value that matched
					barcode_value = str(ocr_data.get("lot_id_1", "")).strip().upper()
					if barcode_value and barcode_value != "NONE":
						distinct_barcodes.add(barcode_value)
						
						# Track distribution: count how many times each barcode appears
						if barcode_value not in barcode_distribution:
							barcode_distribution[barcode_value] = {
								"ocr_ids": set(),
								"parcel_ids": set(),
								"total_rows": 0
							}
						
						# Add unique record IDs using proper identifiers
						ocr_id = ocr_data.get("name") or f"{ocr_data.get('upload_name')}_{ocr_data.get('sequence')}"
						parcel_id = parcel_data.get("_row_index", f"unknown_{id(parcel_data)}")
						
						barcode_distribution[barcode_value]["ocr_ids"].add(ocr_id)
						barcode_distribution[barcode_value]["parcel_ids"].add(parcel_id)
						barcode_distribution[barcode_value]["total_rows"] += 1
		
		# Convert sets to counts
		barcode_analysis = []
		for barcode, data in barcode_distribution.items():
			ocr_count = len(data["ocr_ids"])
			parcel_count = len(data["parcel_ids"])
			total_rows = data["total_rows"]
			
			barcode_analysis.append({
				"barcode": barcode,
				"ocr_count": ocr_count,
				"parcel_count": parcel_count,
				"cartesian_product": ocr_count * parcel_count,
				"total_rows": total_rows
			})
		
		# Sort by most duplicates (highest Cartesian product)
		barcode_analysis.sort(key=lambda x: x["cartesian_product"], reverse=True)
		
		# Add percentage of total rows for each barcode
		total_matched_rows = len(matched_pairs)
		for item in barcode_analysis:
			item["percentage"] = round((item["total_rows"] / total_matched_rows * 100), 2) if total_matched_rows > 0 else 0
		
		# Calculate totals from barcode distribution table
		total_ocr_matched = sum(item["ocr_count"] for item in barcode_analysis)  # Sum of OCR counts (used for stats cards)
		total_parcel_matched = sum(item["parcel_count"] for item in barcode_analysis)  # Sum of Parcel counts (used for stats cards)
		
		# Calculate unique OCR and Parcel records that participate in matches (for chart display)
		all_matched_ocr_ids = set()
		all_matched_parcel_ids = set()
		for barcode, data in barcode_distribution.items():
			all_matched_ocr_ids.update(data["ocr_ids"])
			all_matched_parcel_ids.update(data["parcel_ids"])
		
		unique_ocr_matched = len(all_matched_ocr_ids)
		unique_parcel_matched = len(all_matched_parcel_ids)
		
		stats = {
			"total_ocr_records": len(ocr_data),
			"total_parcel_records": len(parcel_data),
			"matched_barcode_count": unique_barcode_count,  # Number of unique barcodes that matched
			"total_ocr_matched": total_ocr_matched,  # Sum of OCR counts from barcode table (for stats cards)
			"total_parcel_matched": total_parcel_matched,  # Sum of Parcel counts from barcode table (for stats cards)
			"unique_ocr_matched": unique_ocr_matched,  # Unique OCR records that participate in matches (for chart)
			"unique_parcel_matched": unique_parcel_matched,  # Unique Parcel records that participate in matches (for chart)
			"unmatched_ocr_records": len(unmatched_ocr),
			"unmatched_parcel_records": len(unmatched_parcels),
			"total_matched_rows": total_matched_rows,  # Total Cartesian product rows
			"distinct_barcodes": len(distinct_barcodes),  # Number of distinct barcode values (should equal matched_barcode_count)
			"barcode_analysis": barcode_analysis  # ALL barcodes with distribution (not just top 10)
		}
		
		if not matched_pairs:
			# Return with statistics even if no matches
			chart = generate_statistics_chart(stats)
			
			# DEBUG: Show sample values to help diagnose matching issues
			debug_rows = []
			
			# Header row
			debug_rows.append({
				"match_status": "DEBUG",
				"message": f"Total OCR Records: {len(ocr_data)}, Total Parcel Records: {len(parcel_data)}. Matching OCR lot_id_1 against Parcel '{barcode_field}'"
			})
			
			# Show sample OCR lot_id_1 values
			debug_rows.append({
				"match_status": "OCR SAMPLES",
				"message": "Sample lot_id_1 values from OCR:"
			})
			for i, ocr_record in enumerate(ocr_data[:5]):
				lot_id_1 = str(ocr_record.get("lot_id_1", ""))
				debug_rows.append({
					"match_status": f"OCR {i+1}",
					"message": f"lot_id_1 = '{lot_id_1}' (length: {len(lot_id_1)})"
				})
			
			# Show sample Parcel barcode values
			debug_rows.append({
				"match_status": "PARCEL SAMPLES",
				"message": f"Sample '{barcode_field}' values from Parcel:"
			})
			for i, parcel_record in enumerate(parcel_data[:5]):
				barcode_value = str(parcel_record.get(barcode_field, ""))
				debug_rows.append({
					"match_status": f"PARCEL {i+1}",
					"message": f"{barcode_field} = '{barcode_value}' (length: {len(barcode_value)})"
				})
			
			message = f"No matched records found. See debug information below."
			return get_basic_columns(), debug_rows, message, chart
		
		# Generate dynamic columns based on actual OCR and Parcel data
		columns = generate_dynamic_columns(ocr_data, parcel_columns)
		
		# Format ONLY MATCHED records for display (LEFT JOIN filtered to matches only)
		formatted_data = format_all_records(matched_pairs)
		
		# Safety check: ensure we have data
		if not formatted_data or len(formatted_data) == 0:
			error_msg = f"formatted_data is empty even though we have {len(matched_pairs)} matched_pairs!"
			frappe.log_error(error_msg, "OCR Merge Data Error")
			message = f"Error: No data could be formatted from {len(matched_pairs)} matched pairs"
			return get_basic_columns(), [{
				"match_status": "ERROR",
				"message": message
			}], message, generate_statistics_chart(stats)
		
		# Generate chart and message with statistics
		chart = generate_statistics_chart(stats)
		message = (
			f"Analysis Complete: {len(matched_pairs)} total rows displayed (Cartesian product). "
			f"Source: {len(ocr_data)} total OCR records, {len(parcel_data)} total Parcel records. "
			f"DEBUG: Chart matched_ocr={chart.get('matched_ocr', 'MISSING')}, stats.total_ocr_matched={stats.get('total_ocr_matched', 'MISSING')}"
		)
		
		return columns, formatted_data, message, chart
		
	except Exception as e:
		# Create a more detailed error message for debugging
		import traceback
		error_detail = traceback.format_exc()
		error_msg = f"Report error: {str(e)}"
		frappe.log_error(f"Error in OCR Parcel Merge report:\n{error_detail}", "OCR Merge Error")
		
		# Return basic error display
		basic_cols = get_basic_columns()
		error_row = {
			"match_status": "ERROR",
			"message": f"{error_msg[:200]}"
		}
		
		# Try to return with empty chart to prevent further errors
		try:
			empty_chart = {
				"matched_ocr": 0,
				"matched_parcel": 0,
				"unmatched_ocr": 0,
				"unmatched_parcel": 0,
				"total_matched_rows": 0,
				"distinct_barcodes": 0,
				"barcode_analysis": []
			}
			return basic_cols, [error_row], error_msg, empty_chart
		except:
			return basic_cols, [error_row]


def validate_filters(filters):
	"""
	Validate report filters and requirements.
	
	Args:
		filters: Dict containing filter values
		
	Returns:
		Dict with validation result
	"""
	if not filters:
		return {"valid": False, "message": "No filters provided"}
	
	if not filters.get("parcel_file"):
		return {"valid": False, "message": "Please upload a Parcel file to proceed with merge analysis"}
	
	return {"valid": True, "message": "Validation successful"}


def get_ocr_data(filters):
	"""
	Retrieve OCR data using centralized utility with filtering.
	
	Args:
		filters: Dict containing filter parameters
		
	Returns:
		List of OCR records or empty list
	"""
	try:
		# Prepare filters for OCR data retrieval - no date filtering
		ocr_filters = {}
		
		# Add lot ID filtering if specified
		if filters.get("lot_id_filter"):
			ocr_filters["lot_id_filter"] = filters.get("lot_id_filter")
		
		# Get consolidated OCR data with refined analysis - no date restrictions
		# Note: format="dict" returns {record_id: record_data, ...}
		ocr_data_dict = get_consolidated_ocr_data(
			filters=ocr_filters,
			format="dict",
			include_refined=True
		)
		
		# Convert dict to list of record values
		ocr_data = list(ocr_data_dict.values()) if isinstance(ocr_data_dict, dict) else ocr_data_dict
		
		# Apply additional filtering if needed
		if filters.get("lot_id_filter"):
			lot_filter = filters.get("lot_id_filter").upper()
			ocr_data = [
				record for record in ocr_data
				if (record.get("lot_id_1", "").upper().find(lot_filter) != -1 or
					record.get("lot_id_2", "").upper().find(lot_filter) != -1 or
					str(record.get("sub_lot_id", "")).find(lot_filter) != -1)
			]
		
		return ocr_data
		
	except Exception as e:
		frappe.log_error(f"Error in get_ocr_data: {str(e)}", "OCR Data Error")
		return []


def get_parcel_data(filters):
	"""
	Read and validate Parcel data from uploaded Excel file.
	
	Args:
		filters: Dict containing parcel_file attachment
		
	Returns:
		Dict with success status and parcel data
	"""
	try:
		parcel_file_url = filters.get("parcel_file")
		
		# Get file path from URL using centralized utility
		file_path = get_file_path_from_url(parcel_file_url)
		
		# Read Excel file using centralized utility
		excel_result = read_excel_file_safely(parcel_file_url)
		if not excel_result["success"]:
			return {"success": False, "message": f"Cannot read parcel file: {excel_result['error']}"}
		
		df = excel_result["dataframe"]
		
		# Validate required columns - check for either "barcode" or "main_barcode"
		normalized_columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
		
		has_barcode = "barcode" in normalized_columns
		has_main_barcode = "main_barcode" in normalized_columns
		
		if not has_barcode and not has_main_barcode:
			available_cols = ", ".join(df.columns.tolist())
			return {
				"success": False, 
				"message": f"Missing required column 'Barcode' or 'Main Barcode'. Available columns: {available_cols}"
			}
		
		# Normalize column names (case-insensitive, replace spaces with underscores)
		original_columns = df.columns.tolist()  # Keep original names for display
		df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]
		
		# Determine which barcode field to use for matching
		barcode_field = "main_barcode" if has_main_barcode else "barcode"
		
		# Convert to list of dicts for processing
		parcel_records = df.to_dict("records")
		
		# Clean barcode fields - remove .0 suffix from float conversion
		for record in parcel_records:
			if barcode_field in record:
				value = str(record[barcode_field])
				# Remove trailing .0 if present (from float conversion)
				if value.endswith('.0'):
					record[barcode_field] = value[:-2]
				else:
					record[barcode_field] = value
		
		# Filter by barcode pattern if specified
		if filters.get("barcode_filter"):
			barcode_filter = filters.get("barcode_filter").upper()
			parcel_records = [
				record for record in parcel_records
				if str(record.get(barcode_field, "")).upper().find(barcode_filter) != -1
			]
		
		return {
			"success": True, 
			"data": parcel_records,
			"total_records": len(parcel_records),
			"columns": original_columns,  # Return original column names for display
			"barcode_field": barcode_field  # Return which field is being used for matching
		}
		
	except Exception as e:
		frappe.log_error(f"Error processing parcel file: {str(e)}", "OCR Parcel Merge")
		return {"success": False, "message": f"Error processing parcel file: {str(e)}"}


def create_error_row(message):
	"""Create a row to display error messages."""
	return {
		"message": message,
		"status": "ERROR"
	}


def create_info_row(message):
	"""Create a row to display informational messages."""
	return {
		"match_status": "INFO",
		"message": message,
		"status": "INFO"
	}


def get_basic_columns():
	"""Return basic columns for error/info messages."""
	return [
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "message",
			"label": "Message",
			"fieldtype": "Data",
			"width": 500
		}
	]


def generate_dynamic_columns(ocr_data, parcel_columns):
	"""
	Generate dynamic columns based on actual OCR and Parcel data fields.
	OCR columns first (matching cumulative report exactly), then Parcel columns.
	"""
	columns = []
	
	# Add match info columns first
	columns.extend([
		{
			"fieldname": "match_status",
			"label": "Match Status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "match_confidence",
			"label": "Confidence",
			"fieldtype": "Percent",
			"width": 100
		}
	])
	
	# Get all OCR fields from sample data - match cumulative report exactly
	if ocr_data:
		# Handle both list and dict formats
		if isinstance(ocr_data, dict):
			# If it's a dict, get the first value
			sample_ocr = list(ocr_data.values())[0] if ocr_data else {}
		elif isinstance(ocr_data, list) and len(ocr_data) > 0:
			sample_ocr = ocr_data[0]
		else:
			sample_ocr = {}
		
		# OCR fields in exact order as cumulative report (from prepare_excel_data)
		ocr_fields = [
			("upload_name", "Upload Name", "Link", "OCR Data Upload", 140),
			("upload_date", "Upload Date", "Date", None, 100),
			("sequence", "Sequence", "Data", None, 150),
			("created_on", "Created On", "Date", None, 100),
			("batch_name", "Batch Name", "Data", None, 120),
			("text_data", "Text Data", "Text", None, 200),
			("lot_id_1", "Lot ID 1", "Data", None, 120),
			("lot_id_2", "Lot ID 2", "Data", None, 120),
			("sub_lot_id", "Sub Lot ID", "Data", None, 120),
			("result", "Result", "Data", None, 100),
			("color", "Color", "Data", None, 100),
			("blue_uv", "Blue UV", "Data", None, 120),
			("yellow_uv", "Yellow UV", "Data", None, 120),
			("brown", "Brown", "Data", None, 120),
			("type", "Type", "Data", None, 100),
			("fancy_yellow", "Fancy Yellow", "Data", None, 120),
			# Refined fields (processed from text_data)
			("refined_result", "Refined Result", "Data", None, 120),
			("refined_color", "Refined Color", "Data", None, 120),
			("refined_blue_uv", "Refined Blue UV", "Data", None, 130),
			("refined_brown", "Refined Brown", "Data", None, 120),
			("refined_yellow_uv", "Refined Yellow UV", "Data", None, 130),
			("refined_type", "Refined Type", "Data", None, 120),
			("refined_fancy_yellow", "Refined Fancy Yellow", "Data", None, 140)
		]
		
		# Add ALL OCR columns (they will be empty for unmatched records)
		for field_name, label, field_type, options, width in ocr_fields:
			column = {
				"fieldname": field_name,  # Use original field name without prefix
				"label": label,  # Use original label without "OCR" prefix
				"fieldtype": field_type,
				"width": width
			}
			if options:
				column["options"] = options
			columns.append(column)
	
	# Add parcel columns
	for col_name in parcel_columns:
		# Skip problematic column names that are None or invalid
		if not col_name or not isinstance(col_name, str) or len(str(col_name).strip()) == 0:
			continue
			
		# Clean column name for fieldname
		clean_field_name = str(col_name).lower().replace(' ', '_').replace('.', '_').replace('%', 'pct').replace('@', 'at')
		
		# Try to infer field type based on column name
		field_type = "Data"
		width = 120
		
		col_name_lower = str(col_name).lower()
		if any(keyword in col_name_lower for keyword in ["weight", "carat", "size", "wght", "cts"]):
			field_type = "Float"
		elif any(keyword in col_name_lower for keyword in ["amount", "value", "price", "cost", "amt", "list", "esp"]):
			field_type = "Currency"
		elif any(keyword in col_name_lower for keyword in ["date", "time"]):
			field_type = "Date"
			width = 100
		elif any(keyword in col_name_lower for keyword in ["name", "description", "comment", "article", "shape"]):
			width = 150
		elif col_name_lower.endswith(('_pct', '%')):
			field_type = "Percent"
			width = 80
		
		# Don't create columns for problematic field names that are too complex
		if len(clean_field_name) > 50:  # Skip overly long field names
			continue
			
		columns.append({
			"fieldname": clean_field_name,  # Use original field name without prefix
			"label": col_name,  # Use original column name as label
			"fieldtype": field_type,
			"width": width
		})
	
	return columns


def format_all_records(all_records):
	"""
	Format all records from LEFT JOIN for display.
	Shows all parcel records with OCR data where available.
	"""
	import math
	
	def clean_value(value):
		"""Clean problematic values that can't be serialized to JSON."""
		if value is None:
			return ""
		elif isinstance(value, float):
			if math.isnan(value) or math.isinf(value):
				return ""
			return value
		elif isinstance(value, str):
			# Handle string representations of NaN
			if value.upper() in ['NAN', 'NULL', 'NONE']:
				return ""
			return value
		return value
	
	formatted_data = []
	
	for record in all_records:
		parcel_data = record.get("parcel_data", {})
		ocr_data = record.get("ocr_data", {})
		is_matched = record.get("is_matched", False)
		
		# Start with match information
		row = {
			"match_status": f"MATCHED ({record.get('match_type', 'Unknown')})" if is_matched else "UNMATCHED",
			"match_confidence": record.get('confidence', 0)
		}
		
		# Add all OCR fields with original field names (empty if unmatched)
		if ocr_data:
			for field_name, field_value in ocr_data.items():
				row[field_name] = clean_value(field_value)
		
		# Add all parcel fields with cleaned field names
		for field_name, field_value in parcel_data.items():
			# Normalize field name to match column fieldname
			normalized_field = field_name.lower().replace(' ', '_').replace('.', '_')
			row[normalized_field] = clean_value(field_value)
		
		formatted_data.append(row)
	
	return formatted_data


def format_matched_records_only(matched_pairs):
	"""
	DEPRECATED: Use format_all_records instead.
	Format only the matched pairs for display with all available data.
	"""
	import math
	
	def clean_value(value):
		"""Clean problematic values that can't be serialized to JSON."""
		if value is None:
			return ""
		elif isinstance(value, float):
			if math.isnan(value) or math.isinf(value):
				return ""
			return value
		elif isinstance(value, str):
			# Handle string representations of NaN
			if value.upper() in ['NAN', 'NULL', 'NONE']:
				return ""
			return value
		return value
	
	formatted_data = []
	
	for match in matched_pairs:
		ocr_data = match.get("ocr_data", {})
		parcel_data = match.get("parcel_data", {})
		
		# Start with match information
		row = {
			"match_status": f"MATCHED ({match.get('match_type', 'Unknown')})",
			"match_confidence": match.get('confidence', 0)
		}
		
		# Add all OCR fields with original field names (no prefix)
		for field_name, field_value in ocr_data.items():
			row[field_name] = clean_value(field_value)
		
		# Add all parcel fields with cleaned field names (no prefix)
		for field_name, field_value in parcel_data.items():
			# Normalize field name to match column fieldname
			normalized_field = field_name.lower().replace(' ', '_').replace('.', '_')
			row[normalized_field] = clean_value(field_value)
		
		formatted_data.append(row)
	
	return formatted_data


def generate_statistics_chart(stats):
	"""
	Generate chart data for matching statistics visualization.
	Enhanced overlay approach: Shows unique counts with total row count context.
	
	Args:
		stats: Dict containing match statistics
		
	Returns:
		Dict with chart configuration for Frappe charts
	"""
	try:
		# DEBUG: Log what we're receiving
		frappe.log_error(f"Chart stats: unique_ocr_matched={stats.get('unique_ocr_matched')}, total_ocr_matched={stats.get('total_ocr_matched')}", "Chart Debug")
		
		# Return chart data in format expected by JavaScript
		# Use unique record counts for the chart (not the sum from barcode table)
		return {
			"matched_ocr": stats.get("unique_ocr_matched", 0),  # Unique OCR records (not sum)
			"matched_parcel": stats.get("unique_parcel_matched", 0),  # Unique Parcel records (not sum)
			"unmatched_ocr": stats.get("unmatched_ocr_records", 0),
			"unmatched_parcel": stats.get("unmatched_parcel_records", 0),
			"total_matched_rows": stats.get("total_matched_rows", 0),  # Cartesian product total
			"distinct_barcodes": stats.get("distinct_barcodes", 0),  # Distinct barcode values
			"barcode_analysis": stats.get("barcode_analysis", [])  # All barcodes with distribution
		}
		
	except Exception as e:
		frappe.log_error(f"Error generating chart: {str(e)}")
		return {}


def perform_merge_analysis(ocr_data, parcel_data, filters, barcode_field="barcode"):
	"""
	Core matching logic between OCR and Parcel data.
	LEFT JOIN: Parcel (left) with OCR (right) where lot_id_1 = parcel barcode
	
	Args:
		ocr_data: List of OCR records
		parcel_data: List of Parcel records
		filters: Dict with matching mode and other options
		barcode_field: Which barcode field to use for matching (barcode or main_barcode)
		
	Returns:
		Dict with matched and unmatched records
	"""
	try:
		matching_mode = filters.get("matching_mode", "Strict")
		
		# Create OCR lookup indexed by lot_id_1 for LEFT JOIN
		# Key: lot_id_1 (uppercase), Value: OCR record
		ocr_lookup = {}
		for ocr_record in ocr_data:
			lot_id_1 = str(ocr_record.get("lot_id_1", "")).strip().upper()
			if lot_id_1 and lot_id_1 != "NONE":
				# Store OCR record by its lot_id_1
				if lot_id_1 not in ocr_lookup:
					ocr_lookup[lot_id_1] = []
				ocr_lookup[lot_id_1].append(ocr_record)
		
		# DEBUG: Log sample OCR lot_id_1 values
		sample_ocr_keys = list(ocr_lookup.keys())[:10]
		print(f"\n=== OCR MATCHING DEBUG ===")
		print(f"OCR Lookup created with {len(ocr_lookup)} unique lot_id_1 values.")
		print(f"Sample OCR lot_id_1 values (normalized): {sample_ocr_keys}")
		print(f"Matching against parcel field: '{barcode_field}'")
		
		frappe.log_error(
			f"OCR Lookup created with {len(ocr_lookup)} unique lot_id_1 values.\n"
			f"Sample OCR lot_id_1 values: {sample_ocr_keys}\n"
			f"Matching against parcel field: '{barcode_field}'",
			"OCR Merge Debug - OCR Data"
		)
		
		# LEFT JOIN: Process ALL parcel records (left table)
		all_records = []
		matched_count = 0
		unmatched_count = 0
		
		# DEBUG: Collect sample parcel barcode values
		sample_parcel_barcodes = []
		
		for parcel_idx, parcel_record in enumerate(parcel_data):
			# Add row index to parcel record for unique identification
			parcel_record["_row_index"] = parcel_idx
			
			# Use the specified barcode field (barcode or main_barcode)
			parcel_barcode = str(parcel_record.get(barcode_field, "")).strip().upper()
			
			# Collect first 10 samples for debugging
			if len(sample_parcel_barcodes) < 10 and parcel_barcode:
				sample_parcel_barcodes.append(parcel_barcode)
			
			# Look for matching OCR record(s)
			if parcel_barcode and parcel_barcode in ocr_lookup:
				# MATCHED: Parcel has corresponding OCR data
				# Create Cartesian product: Each parcel × Each matching OCR
				matching_ocr_records = ocr_lookup[parcel_barcode]
				
				for ocr_record in matching_ocr_records:
					all_records.append({
						"parcel_data": parcel_record,
						"ocr_data": ocr_record,
						"matching_field": "lot_id_1",
						"matched_value": parcel_barcode,
						"confidence": 1.0,
						"match_type": "Exact",
						"is_matched": True
					})
					matched_count += 1
			else:
				# UNMATCHED: Parcel with no corresponding OCR data
				all_records.append({
					"parcel_data": parcel_record,
					"ocr_data": {},  # Empty OCR data
					"matching_field": None,
					"matched_value": None,
					"confidence": 0,
					"match_type": "Unmatched",
					"is_matched": False
				})
				unmatched_count += 1
		
		# DEBUG: Log parcel samples and matching results
		print(f"Parcel Data processed: {len(parcel_data)} total records.")
		print(f"Sample Parcel '{barcode_field}' values (normalized): {sample_parcel_barcodes}")
		print(f"Matched: {matched_count}, Unmatched: {unmatched_count}")
		print(f"=== END DEBUG ===\n")
		
		frappe.log_error(
			f"Parcel Data processed: {len(parcel_data)} total records.\n"
			f"Sample Parcel main_barcode values: {sample_parcel_barcodes}\n"
			f"Matched: {matched_count}, Unmatched: {unmatched_count}",
			"OCR Merge Debug - Parcel Data & Results"
		)
		
		# Separate matched and unmatched for statistics
		matched_pairs = [r for r in all_records if r["is_matched"]]
		unmatched_parcels = [r for r in all_records if not r["is_matched"]]
		
		# Count unmatched OCR records (OCR records not found in any parcel)
		matched_lot_ids = set()
		for record in matched_pairs:
			if record.get("matched_value"):
				matched_lot_ids.add(record["matched_value"])
		
		unmatched_ocr = []
		for lot_id_1, ocr_records in ocr_lookup.items():
			if lot_id_1 not in matched_lot_ids:
				unmatched_ocr.extend(ocr_records)
		
		return {
			"all_records": all_records,  # All parcel records with/without OCR
			"matched_pairs": matched_pairs,
			"unmatched_ocr": unmatched_ocr,
			"unmatched_parcels": [r["parcel_data"] for r in unmatched_parcels],
			"summary": {
				"total_ocr_records": len(ocr_data),
				"total_parcel_records": len(parcel_data),
				"matched_pairs": matched_count,
				"unmatched_ocr": len(unmatched_ocr),
				"unmatched_parcels": unmatched_count
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Error in merge analysis: {str(e)}", "OCR Parcel Merge")
		return {
			"all_records": [],
			"matched_pairs": [],
			"unmatched_ocr": [],
			"unmatched_parcels": [],
			"summary": {"error": str(e)}
		}


def find_matches_for_ocr(ocr_record, parcel_lookup, matching_mode):
	"""
	Find matching parcels for a single OCR record.
	Matches ONLY lot_id_1 from OCR against main_barcode from Parcel.
	
	Args:
		ocr_record: Single OCR record dict
		parcel_lookup: Dict of parcel data indexed by main_barcode
		matching_mode: Strict, Fuzzy, or All Matches
		
	Returns:
		List of match dictionaries
	"""
	matches = []
	
	# Extract ONLY lot_id_1 for matching against main_barcode
	lot_id_1 = str(ocr_record.get("lot_id_1", "")).strip().upper()
	
	# Skip if lot_id_1 is empty
	if not lot_id_1 or lot_id_1 == "NONE":
		return matches
	
	# Try exact match first
	if lot_id_1 in parcel_lookup:
		matches.append({
			"ocr_data": ocr_record,
			"parcel_data": parcel_lookup[lot_id_1]["data"],
			"matching_field": "lot_id_1",
			"matched_value": lot_id_1,
			"confidence": 1.0,
			"match_type": "Exact"
		})
	
	# If no exact match and fuzzy matching is enabled
	if not matches and matching_mode in ["Fuzzy", "All Matches"]:
		for main_barcode, parcel_info in parcel_lookup.items():
			similarity = calculate_string_similarity(lot_id_1, main_barcode)
			if similarity >= 0.8:  # 80% similarity threshold
				matches.append({
					"ocr_data": ocr_record,
					"parcel_data": parcel_info["data"],
					"matching_field": "lot_id_1",
					"matched_value": f"{lot_id_1} ≈ {main_barcode}",
					"confidence": similarity,
					"match_type": "Fuzzy"
				})
	
	# Sort by confidence descending
	matches.sort(key=lambda x: x["confidence"], reverse=True)
	
	return matches


def calculate_string_similarity(str1, str2):
	"""Calculate similarity ratio between two strings."""
	if not str1 or not str2:
		return 0.0
	return SequenceMatcher(None, str1.upper(), str2.upper()).ratio()


def _get_lot_id_field_name(ocr_record, lot_id):
	"""Get the field name that contains the matching lot ID."""
	if str(ocr_record.get("lot_id_1", "")).strip().upper() == lot_id:
		return "lot_id_1"
	elif str(ocr_record.get("lot_id_2", "")).strip().upper() == lot_id:
		return "lot_id_2"
	elif str(ocr_record.get("sub_lot_id", "")).strip().upper() == lot_id:
		return "sub_lot_id"
	return "unknown"



@frappe.whitelist()
def get_statistics(filters):
	"""
	Get matching statistics for chart display.
	
	Args:
		filters: Dict containing report filters
		
	Returns:
		Dict with statistics for display
	"""
	try:
		# Parse filters if they come as string
		if isinstance(filters, str):
			import json
			filters = json.loads(filters)
		
		# Get OCR and parcel data
		ocr_data = get_ocr_data(filters)
		parcel_result = get_parcel_data(filters)
		
		if not parcel_result.get("success"):
			return {"error": "Could not load parcel data"}
		
		parcel_data = parcel_result["data"]
		
		# Perform matching analysis
		merge_result = perform_merge_analysis(ocr_data, parcel_data, filters)
		matched_pairs = merge_result.get("matched_pairs", [])
		unmatched_ocr = merge_result.get("unmatched_ocr", [])
		unmatched_parcels = merge_result.get("unmatched_parcels", [])
		
		# Calculate statistics - focus on UNIQUE BARCODE VALUES
		# Count how many distinct barcode values were matched
		matched_barcodes = set()
		barcode_field = filters.get("barcode_field", "barcode")  # Get which field was used for matching
		
		for m in matched_pairs:
			if m.get("is_matched"):
				ocr_data_item = m.get("ocr_data")
				if ocr_data_item:
					barcode_value = str(ocr_data_item.get("lot_id_1", "")).strip().upper()
					if barcode_value and barcode_value != "NONE":
						matched_barcodes.add(barcode_value)
		
		unique_barcode_count = len(matched_barcodes)
		
		# Calculate DISTINCT barcode values and distribution (same as execute())
		barcode_distribution = {}
		distinct_barcodes = set()
		
		for match in matched_pairs:
			if match.get("is_matched"):
				ocr_data_rec = match.get("ocr_data")
				parcel_data_rec = match.get("parcel_data")
				
				if ocr_data_rec and parcel_data_rec:
					barcode_value = str(ocr_data_rec.get("lot_id_1", "")).strip().upper()
					if barcode_value and barcode_value != "NONE":
						distinct_barcodes.add(barcode_value)
						
						if barcode_value not in barcode_distribution:
							barcode_distribution[barcode_value] = {
								"ocr_ids": set(),
								"parcel_ids": set(),
								"total_rows": 0
							}
						
						# Add unique record IDs using proper identifiers
						ocr_id = ocr_data_rec.get("name") or f"{ocr_data_rec.get('upload_name')}_{ocr_data_rec.get('sequence')}"
						parcel_id = parcel_data_rec.get("_row_index", f"unknown_{id(parcel_data_rec)}")
						
						barcode_distribution[barcode_value]["ocr_ids"].add(ocr_id)
						barcode_distribution[barcode_value]["parcel_ids"].add(parcel_id)
						barcode_distribution[barcode_value]["total_rows"] += 1
		
		# Convert sets to counts
		barcode_analysis = []
		for barcode, data in barcode_distribution.items():
			ocr_count = len(data["ocr_ids"])
			parcel_count = len(data["parcel_ids"])
			total_rows = data["total_rows"]
			
			barcode_analysis.append({
				"barcode": barcode,
				"ocr_count": ocr_count,
				"parcel_count": parcel_count,
				"cartesian_product": ocr_count * parcel_count,
				"total_rows": total_rows
			})
		
		barcode_analysis.sort(key=lambda x: x["cartesian_product"], reverse=True)
		
		# Add percentage of total rows for each barcode
		total_matched_rows = len(matched_pairs)
		for item in barcode_analysis:
			item["percentage"] = round((item["total_rows"] / total_matched_rows * 100), 2) if total_matched_rows > 0 else 0
		
		# Calculate totals from barcode distribution table
		total_ocr_matched = sum(item["ocr_count"] for item in barcode_analysis)  # Sum of OCR counts (used for stats cards)
		total_parcel_matched = sum(item["parcel_count"] for item in barcode_analysis)  # Sum of Parcel counts (used for stats cards)
		
		# Calculate unique OCR and Parcel records that participate in matches (for chart display)
		all_matched_ocr_ids = set()
		all_matched_parcel_ids = set()
		for barcode, data in barcode_distribution.items():
			all_matched_ocr_ids.update(data["ocr_ids"])
			all_matched_parcel_ids.update(data["parcel_ids"])
		
		unique_ocr_matched = len(all_matched_ocr_ids)
		unique_parcel_matched = len(all_matched_parcel_ids)
		
		# Calculate statistics
		stats = {
			"total_ocr_records": len(ocr_data),
			"matched_barcode_count": unique_barcode_count,  # Number of unique barcodes that matched
			"total_ocr_matched": total_ocr_matched,  # Sum of OCR counts from barcode table (for stats cards)
			"total_parcel_matched": total_parcel_matched,  # Sum of Parcel counts from barcode table (for stats cards)
			"unique_ocr_matched": unique_ocr_matched,  # Unique OCR records that participate in matches (for chart)
			"unique_parcel_matched": unique_parcel_matched,  # Unique Parcel records that participate in matches (for chart)
			"unmatched_ocr_records": len(unmatched_ocr),
			"total_parcel_records": len(parcel_data),
			"unmatched_parcel_records": len(unmatched_parcels),
			"chart_data": {
				"matched_ocr": unique_ocr_matched,  # Use calculated unique OCR count
				"unmatched_ocr": len(unmatched_ocr),
				"matched_parcel": unique_parcel_matched,  # Use calculated unique Parcel count
				"unmatched_parcel": len(unmatched_parcels),
				"total_matched_rows": total_matched_rows,  # Total Cartesian product rows
				"distinct_barcodes": len(distinct_barcodes),  # Distinct barcode values (should equal matched_barcode_count)
				"barcode_analysis": barcode_analysis  # ALL barcodes with distribution
			}
		}
		
		return stats
		
	except Exception as e:
		frappe.log_error(f"Error getting statistics: {str(e)}")
		return {"error": f"Statistics error: {str(e)}"}


@frappe.whitelist()
def export_matched_records(filters):
	"""
	Export only matched records to Excel.
	
	IMPORTANT: This exports ALL matched pairs including Cartesian product.
	Example: If 5 parcel records have main_barcode='21348036' and 
	2 OCR records have lot_id_1='21348036', this will export 10 rows (5×2).
	Each unique match combination is exported as a separate row.
	"""
	try:
		# Parse filters if they come as string (from web requests)
		if isinstance(filters, str):
			import json
			filters = json.loads(filters)
		
		# Get the merge analysis data
		validation = validate_filters(filters)
		if not validation["valid"]:
			return {
				"success": False,
				"message": f"Filter validation failed: {validation['message']}",
				"count": 0
			}
		
		# Get data
		ocr_data = get_ocr_data(filters)
		if not ocr_data:
			return {
				"success": False,
				"message": "No OCR data found for the specified date range. Please check if OCR documents exist for this period.",
				"count": 0
			}
			
		parcel_result = get_parcel_data(filters)
		if not parcel_result.get("success"):
			return {
				"success": False,
				"message": f"Parcel data error: {parcel_result.get('message', 'Unknown error')}",
				"count": 0
			}
		
		parcel_data = parcel_result["data"]
		
		# Perform matching
		merge_results = perform_merge_analysis(ocr_data, parcel_data, filters)
		matched_pairs = merge_results.get("matched_pairs", [])
		
		if not matched_pairs:
			return {
				"success": False,
				"message": "No matched records found. Please check your data and filters.",
				"count": 0
			}
		
		# Prepare data for Excel export
		headers = [
			"OCR ID", "OCR Lot ID 1", "OCR Lot ID 2", "OCR Sub Lot ID", 
			"OCR Stone Name", "OCR Weight", "OCR Amount",
			"Parcel Barcode", "Parcel Main Barcode", "Parcel Stone Name", 
			"Parcel Weight", "Parcel Value",
			"Match Type", "Confidence", "Matching Field", "Matched Value"
		]
		
		data_rows = []
		for match in matched_pairs:
			ocr_data_record = match.get("ocr_data", {})
			parcel_data_record = match.get("parcel_data", {})
			
			row = [
				ocr_data_record.get("name", ""),
				ocr_data_record.get("lot_id_1", ""),
				ocr_data_record.get("lot_id_2", ""),
				str(ocr_data_record.get("sub_lot_id", "")),
				ocr_data_record.get("stone_name", ""),
				ocr_data_record.get("weight", 0),
				ocr_data_record.get("amount", 0),
				parcel_data_record.get("barcode", ""),
				parcel_data_record.get("main_barcode", ""),
				parcel_data_record.get("stone_name", ""),
				parcel_data_record.get("weight", 0),
				parcel_data_record.get("value", 0),
				match.get("match_type", "Unknown"),
				f"{match.get('confidence', 0):.2%}",
				match.get("matching_field", ""),
				match.get("matched_value", "")
			]
			data_rows.append(row)
		
		# Create Excel workbook
		sheets_data = {
			"Matched Records": {
				"headers": headers,
				"data": data_rows,
				"special_formatting": {
					"title": f"OCR-Parcel Matched Records - {len(matched_pairs)} matches",
					"highlight_matches": True
				}
			}
		}
		
		filename = f"ocr_parcel_matched_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
		
		# Use centralized Excel utility
		workbook_result = create_styled_excel_workbook(sheets_data, "ocr_parcel_matched")
		if not workbook_result.get("success"):
			return {
				"success": False,
				"message": f"Failed to create Excel workbook: {workbook_result.get('message', 'Unknown error')}",
				"count": 0
			}
			
		workbook = workbook_result["workbook"]
		return create_download_response(workbook, filename)
		
	except Exception as e:
		frappe.log_error(f"Error exporting matched records: {str(e)}", "OCR Parcel Merge")
		return {
			"success": False,
			"message": f"Export error: {str(e)}",
			"count": 0
		}


@frappe.whitelist()
def export_unmatched_ocr(filters):
	"""Export unmatched OCR records to Excel."""
	try:
		# Parse filters if they come as string (from web requests)
		if isinstance(filters, str):
			import json
			filters = json.loads(filters)
		
		# Simple validation - just check for parcel file
		if not filters.get("parcel_file"):
			return {
				"success": False,
				"message": "Please upload a Parcel file to proceed with merge analysis",
				"count": 0
			}
		
		# Get data - start simple, no date filtering
		ocr_data = get_ocr_data({})  # Get all OCR data first
		
		if not ocr_data:
			return {
				"success": False,
				"message": "No OCR data found in the system. Please check if OCR documents exist.",
				"count": 0
			}
			
		parcel_result = get_parcel_data(filters)
		if not parcel_result.get("success"):
			return {
				"success": False,
				"message": f"Parcel data error: {parcel_result.get('message', 'Unknown error')}",
				"count": 0
			}
		
		parcel_data = parcel_result["data"]
		
		# Perform matching
		merge_results = perform_merge_analysis(ocr_data, parcel_data, filters)
		unmatched_ocr = merge_results.get("unmatched_ocr", [])
		
		if not unmatched_ocr:
			return {
				"success": False,
				"message": "No unmatched OCR records found. All OCR records have been matched.",
				"count": 0
			}
		
		# Prepare data for Excel export
		headers = [
			"OCR ID", "OCR Lot ID 1", "OCR Lot ID 2", "OCR Sub Lot ID", 
			"OCR Stone Name", "OCR Weight", "OCR Amount", "Reason"
		]
		
		data_rows = []
		for ocr_record in unmatched_ocr:
			row = [
				ocr_record.get("name", ""),
				ocr_record.get("lot_id_1", ""),
				ocr_record.get("lot_id_2", ""),
				str(ocr_record.get("sub_lot_id", "")),
				ocr_record.get("stone_name", ""),
				ocr_record.get("weight", 0),
				ocr_record.get("amount", 0),
				"No matching parcel found"
			]
			data_rows.append(row)
		
		# Create Excel workbook
		sheets_data = {
			"Unmatched OCR Records": {
				"headers": headers,
				"data": data_rows,
				"special_formatting": {
					"title": f"Unmatched OCR Records - {len(unmatched_ocr)} records",
					"highlight_unmatched": True
				}
			}
		}
		
		filename = f"ocr_unmatched_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
		
		# Use centralized Excel utility
		excel_result = create_styled_excel_workbook(sheets_data, "ocr_unmatched")
		if not excel_result.get("success"):
			return {
				"success": False,
				"message": "Failed to create Excel workbook",
				"count": 0
			}
		
		workbook = excel_result.get("workbook")
		return create_download_response(workbook, filename)
		
	except Exception as e:
		frappe.log_error(f"Error exporting unmatched OCR: {str(e)}", "OCR Export Error")
		return {
			"success": False,
			"message": f"Export error: {str(e)}",
			"count": 0
		}


@frappe.whitelist()
def export_unmatched_parcels(filters):
	"""Export unmatched Parcel records to Excel."""
	try:
		# Parse filters if they come as string (from web requests)
		if isinstance(filters, str):
			import json
			filters = json.loads(filters)
		
		# Get the merge analysis data
		validation = validate_filters(filters)
		if not validation["valid"]:
			return {
				"success": False,
				"message": f"Filter validation failed: {validation['message']}",
				"count": 0
			}
		
		# Get data
		ocr_data = get_ocr_data(filters)
		if not ocr_data:
			return {
				"success": False,
				"message": "No OCR data found for the specified date range. Please check if OCR documents exist for this period.",
				"count": 0
			}
			
		parcel_result = get_parcel_data(filters)
		if not parcel_result.get("success"):
			return {
				"success": False,
				"message": f"Parcel data error: {parcel_result.get('message', 'Unknown error')}",
				"count": 0
			}
		
		parcel_data = parcel_result["data"]
		
		# Perform matching
		merge_results = perform_merge_analysis(ocr_data, parcel_data, filters)
		unmatched_parcels = merge_results.get("unmatched_parcels", [])
		
		if not unmatched_parcels:
			return {
				"success": False,
				"message": "No unmatched Parcel records found. All parcels have been matched.",
				"count": 0
			}
		
		# Prepare data for Excel export
		headers = [
			"Parcel Barcode", "Parcel Main Barcode", "Parcel Stone Name", 
			"Parcel Weight", "Parcel Value", "Reason"
		]
		
		data_rows = []
		for parcel_record in unmatched_parcels:
			row = [
				parcel_record.get("barcode", ""),
				parcel_record.get("main_barcode", ""),
				parcel_record.get("stone_name", ""),
				parcel_record.get("weight", 0),
				parcel_record.get("value", 0),
				"No matching OCR record found"
			]
			data_rows.append(row)
		
		# Create Excel workbook
		sheets_data = {
			"Unmatched Parcel Records": {
				"headers": headers,
				"data": data_rows,
				"special_formatting": {
					"title": f"Unmatched Parcel Records - {len(unmatched_parcels)} records",
					"highlight_unmatched": True
				}
			}
		}
		
		filename = f"parcel_unmatched_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
		
		# Use centralized Excel utility
		excel_result = create_styled_excel_workbook(sheets_data, "parcel_unmatched")
		if not excel_result.get("success"):
			return {
				"success": False,
				"message": "Failed to create Excel workbook",
				"count": 0
			}
		
		workbook = excel_result.get("workbook")
		return create_download_response(workbook, filename)
		
	except Exception as e:
		frappe.log_error(f"Error exporting unmatched Parcel records: {str(e)}", "OCR Parcel Merge")
		return {
			"success": False,
			"message": f"Export error: {str(e)}",
			"count": 0
		}


@frappe.whitelist()
def export_complete_report(filters):
	"""Export complete analysis with all data to Excel."""
	try:
		# Parse filters if they come as string (from web requests)
		if isinstance(filters, str):
			import json
			filters = json.loads(filters)
		
		# Get the merge analysis data
		validation = validate_filters(filters)
		if not validation["valid"]:
			return {
				"success": False,
				"message": f"Filter validation failed: {validation['message']}",
				"count": 0
			}
		
		# Get data
		ocr_data = get_ocr_data(filters)
		if not ocr_data:
			return {
				"success": False,
				"message": "No OCR data found for the specified date range. Please check if OCR documents exist for this period.",
				"count": 0
			}
			
		parcel_result = get_parcel_data(filters)
		if not parcel_result.get("success"):
			return {
				"success": False,
				"message": f"Parcel data error: {parcel_result.get('message', 'Unknown error')}",
				"count": 0
			}
		
		parcel_data = parcel_result["data"]
		
		# Perform matching
		merge_results = perform_merge_analysis(ocr_data, parcel_data, filters)
		
		# Prepare sheets data
		sheets_data = {}
		
		# Summary sheet
		summary = merge_results.get("summary", {})
		summary_headers = ["Metric", "Count"]
		summary_data = [
			["Total OCR Records", summary.get("total_ocr_records", 0)],
			["Total Parcel Records", summary.get("total_parcel_records", 0)],
			["Matched Pairs", summary.get("matched_pairs", 0)],
			["Unmatched OCR", summary.get("unmatched_ocr", 0)],
			["Unmatched Parcels", summary.get("unmatched_parcels", 0)],
			["Match Rate", f"{(summary.get('matched_pairs', 0) / max(summary.get('total_ocr_records', 1), 1) * 100):.1f}%"]
		]
		
		sheets_data["Summary"] = {
			"headers": summary_headers,
			"data": summary_data,
			"special_formatting": {
				"title": "OCR-Parcel Merge Analysis Summary",
				"highlight_summary": True
			}
		}
		
		# Add matched records if any
		matched_pairs = merge_results.get("matched_pairs", [])
		if matched_pairs:
			matched_headers = [
				"OCR ID", "OCR Lot ID 1", "OCR Lot ID 2", "OCR Sub Lot ID", 
				"OCR Stone Name", "OCR Weight", "OCR Amount",
				"Parcel Barcode", "Parcel Main Barcode", "Parcel Stone Name", 
				"Parcel Weight", "Parcel Value",
				"Match Type", "Confidence", "Matching Field", "Matched Value"
			]
			
			matched_data = []
			for match in matched_pairs:
				ocr_data_record = match.get("ocr_data", {})
				parcel_data_record = match.get("parcel_data", {})
				
				row = [
					ocr_data_record.get("name", ""),
					ocr_data_record.get("lot_id_1", ""),
					ocr_data_record.get("lot_id_2", ""),
					str(ocr_data_record.get("sub_lot_id", "")),
					ocr_data_record.get("stone_name", ""),
					ocr_data_record.get("weight", 0),
					ocr_data_record.get("amount", 0),
					parcel_data_record.get("barcode", ""),
					parcel_data_record.get("main_barcode", ""),
					parcel_data_record.get("stone_name", ""),
					parcel_data_record.get("weight", 0),
					parcel_data_record.get("value", 0),
					match.get("match_type", "Unknown"),
					f"{match.get('confidence', 0):.2%}",
					match.get("matching_field", ""),
					match.get("matched_value", "")
				]
				matched_data.append(row)
			
			sheets_data["Matched Records"] = {
				"headers": matched_headers,
				"data": matched_data,
				"special_formatting": {
					"title": f"Matched Records - {len(matched_pairs)} matches"
				}
			}
		
		# Add unmatched OCR if any
		unmatched_ocr = merge_results.get("unmatched_ocr", [])
		if unmatched_ocr:
			ocr_headers = [
				"OCR ID", "OCR Lot ID 1", "OCR Lot ID 2", "OCR Sub Lot ID", 
				"OCR Stone Name", "OCR Weight", "OCR Amount", "Reason"
			]
			
			ocr_data_rows = []
			for ocr_record in unmatched_ocr:
				row = [
					ocr_record.get("name", ""),
					ocr_record.get("lot_id_1", ""),
					ocr_record.get("lot_id_2", ""),
					str(ocr_record.get("sub_lot_id", "")),
					ocr_record.get("stone_name", ""),
					ocr_record.get("weight", 0),
					ocr_record.get("amount", 0),
					"No matching parcel found"
				]
				ocr_data_rows.append(row)
			
			sheets_data["Unmatched OCR"] = {
				"headers": ocr_headers,
				"data": ocr_data_rows,
				"special_formatting": {
					"title": f"Unmatched OCR Records - {len(unmatched_ocr)} records"
				}
			}
		
		# Add unmatched Parcels if any
		unmatched_parcels = merge_results.get("unmatched_parcels", [])
		if unmatched_parcels:
			parcel_headers = [
				"Parcel Barcode", "Parcel Main Barcode", "Parcel Stone Name", 
				"Parcel Weight", "Parcel Value", "Reason"
			]
			
			parcel_data_rows = []
			for parcel_record in unmatched_parcels:
				row = [
					parcel_record.get("barcode", ""),
					parcel_record.get("main_barcode", ""),
					parcel_record.get("stone_name", ""),
					parcel_record.get("weight", 0),
					parcel_record.get("value", 0),
					"No matching OCR record found"
				]
				parcel_data_rows.append(row)
			
			sheets_data["Unmatched Parcels"] = {
				"headers": parcel_headers,
				"data": parcel_data_rows,
				"special_formatting": {
					"title": f"Unmatched Parcel Records - {len(unmatched_parcels)} records"
				}
			}
		
		filename = f"ocr_parcel_complete_analysis_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
		
		# Use centralized Excel utility
		excel_result = create_styled_excel_workbook(sheets_data, "ocr_parcel_complete")
		if not excel_result.get("success"):
			return {
				"success": False,
				"message": "Failed to create Excel workbook",
				"count": 0
			}
		
		workbook = excel_result.get("workbook")
		return create_download_response(workbook, filename)
		
	except Exception as e:
		frappe.log_error(f"Error exporting complete analysis: {str(e)}", "OCR Parcel Merge")
		return {
			"success": False,
			"message": f"Export error: {str(e)}",
			"count": 0
		}
