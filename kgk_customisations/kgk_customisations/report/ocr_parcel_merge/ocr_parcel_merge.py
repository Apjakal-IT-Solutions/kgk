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
		Tuple (columns, data) for report display
	"""
	try:
		# Validate filters and parcel file
		validation_result = validate_filters(filters)
		if not validation_result["valid"]:
			return get_basic_columns(), [create_error_row(validation_result["message"])]
		
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
		if not parcel_data:
			return get_basic_columns(), [create_info_row("No valid parcel data found in uploaded file")]
		
		# Perform matching between OCR and Parcel data
		merge_result = perform_merge_analysis(ocr_data, parcel_data, filters)
		matched_pairs = merge_result.get("matched_pairs", [])
		
		if not matched_pairs:
			return get_basic_columns(), [create_info_row("No matched records found. Please check your data and try different matching settings.")]
		
		# Generate dynamic columns based on actual OCR and Parcel data
		columns = generate_dynamic_columns(ocr_data, parcel_columns)
		
		# Format only matched data for display
		formatted_data = format_matched_records_only(matched_pairs)
		
		# Log successful execution for debugging
		frappe.log_error(
			f"OCR Parcel Merge Report Success: {len(matched_pairs)} matches found from {len(ocr_data)} OCR and {len(parcel_data)} parcel records",
			"OCR Parcel Merge Success"
		)
		
		return columns, formatted_data
		
	except Exception as e:
		frappe.log_error(f"Error in OCR Parcel Merge report: {str(e)}\n{frappe.get_traceback()}", "OCR Parcel Merge Report Error")
		error_msg = f"Error generating report: {str(e)}"
		return get_basic_columns(), [create_error_row(error_msg)]


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
		ocr_data = get_consolidated_ocr_data(
			filters=ocr_filters,
			format="dict",
			include_refined=True
		)
		
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
		
		# Validate required columns
		required_columns = ["barcode"]  # Primary matching field
		missing_columns = [col for col in required_columns if col.lower() not in [c.lower() for c in df.columns]]
		
		if missing_columns:
			available_cols = ", ".join(df.columns.tolist())
			return {
				"success": False, 
				"message": f"Missing required columns: {missing_columns}. Available columns: {available_cols}"
			}
		
		# Normalize column names (case-insensitive) but keep originals for display
		original_columns = df.columns.tolist()  # Keep original names for display
		df.columns = [col.lower().strip() for col in df.columns]
		
		# Convert to list of dicts for processing
		parcel_records = df.to_dict("records")
		
		# Filter by barcode pattern if specified
		if filters.get("barcode_filter"):
			barcode_filter = filters.get("barcode_filter").upper()
			parcel_records = [
				record for record in parcel_records
				if record.get("barcode", "").upper().find(barcode_filter) != -1
			]
		
		return {
			"success": True, 
			"data": parcel_records,
			"total_records": len(parcel_records),
			"columns": original_columns  # Return original column names for display
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
		sample_ocr = ocr_data[0]
		
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
		
		# Add OCR columns that exist in the data - use original field names
		for field_name, label, field_type, options, width in ocr_fields:
			# Only add columns for fields that actually exist in our data
			if field_name in sample_ocr:
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
		# Clean column name for fieldname
		clean_field_name = col_name.lower().replace(' ', '_').replace('.', '_').replace('%', 'pct').replace('@', 'at')
		
		# Try to infer field type based on column name
		field_type = "Data"
		width = 120
		
		if any(keyword in col_name.lower() for keyword in ["weight", "carat", "size", "wght", "cts"]):
			field_type = "Float"
		elif any(keyword in col_name.lower() for keyword in ["amount", "value", "price", "cost", "amt", "list", "esp"]):
			field_type = "Currency"
		elif any(keyword in col_name.lower() for keyword in ["date", "time"]):
			field_type = "Date"
			width = 100
		elif any(keyword in col_name.lower() for keyword in ["name", "description", "comment", "article", "shape"]):
			width = 150
		elif col_name.lower().endswith(('_pct', '%')):
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


def format_matched_records_only(matched_pairs):
	"""
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


def perform_merge_analysis(ocr_data, parcel_data, filters):
	"""
	Core matching logic between OCR and Parcel data.
	
	Args:
		ocr_data: List of OCR records
		parcel_data: List of Parcel records
		filters: Dict with matching mode and other options
		
	Returns:
		Dict with matched and unmatched records
	"""
	try:
		matching_mode = filters.get("matching_mode", "Strict")
		show_unmatched = filters.get("show_unmatched", 1)
		
		# Initialize results
		matched_pairs = []
		unmatched_ocr = []
		unmatched_parcels = list(parcel_data)  # Start with all parcels as unmatched
		
		# Create barcode lookup for efficiency
		parcel_lookup = {}
		for idx, parcel in enumerate(parcel_data):
			barcode = str(parcel.get("barcode", "")).strip().upper()
			main_barcode = str(parcel.get("main_barcode", "")).strip().upper()
			
			if barcode:
				parcel_lookup[barcode] = {"index": idx, "data": parcel}
			if main_barcode and main_barcode != barcode:
				parcel_lookup[main_barcode] = {"index": idx, "data": parcel}
		
		# Process each OCR record
		for ocr_record in ocr_data:
			matches_found = find_matches_for_ocr(ocr_record, parcel_lookup, matching_mode)
			
			if matches_found:
				# Process all matches based on mode
				if matching_mode == "All Matches":
					# Include all matches
					for match in matches_found:
						matched_pairs.append(match)
						# Remove from unmatched parcels
						if match["parcel_data"] in unmatched_parcels:
							unmatched_parcels.remove(match["parcel_data"])
				else:
					# Take the best match only
					best_match = max(matches_found, key=lambda x: x["confidence"])
					matched_pairs.append(best_match)
					# Remove from unmatched parcels
					if best_match["parcel_data"] in unmatched_parcels:
						unmatched_parcels.remove(best_match["parcel_data"])
			else:
				# No matches found
				unmatched_ocr.append(ocr_record)
		
		return {
			"matched_pairs": matched_pairs,
			"unmatched_ocr": unmatched_ocr if show_unmatched else [],
			"unmatched_parcels": unmatched_parcels if show_unmatched else [],
			"summary": {
				"total_ocr_records": len(ocr_data),
				"total_parcel_records": len(parcel_data),
				"matched_pairs": len(matched_pairs),
				"unmatched_ocr": len(unmatched_ocr),
				"unmatched_parcels": len(unmatched_parcels)
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Error in merge analysis: {str(e)}", "OCR Parcel Merge")
		return {
			"matched_pairs": [],
			"unmatched_ocr": [],
			"unmatched_parcels": [],
			"summary": {"error": str(e)}
		}


def find_matches_for_ocr(ocr_record, parcel_lookup, matching_mode):
	"""
	Find matching parcels for a single OCR record.
	
	Args:
		ocr_record: Single OCR record dict
		parcel_lookup: Dict of parcel data indexed by barcode
		matching_mode: Strict, Fuzzy, or All Matches
		
	Returns:
		List of match dictionaries
	"""
	matches = []
	
	# Extract OCR lot IDs for matching
	lot_ids = [
		str(ocr_record.get("lot_id_1", "")).strip().upper(),
		str(ocr_record.get("lot_id_2", "")).strip().upper(),
		str(ocr_record.get("sub_lot_id", "")).strip().upper()
	]
	
	# Remove empty lot IDs
	lot_ids = [lot_id for lot_id in lot_ids if lot_id and lot_id != "NONE"]
	
	# Try exact matches first
	for lot_id in lot_ids:
		if lot_id in parcel_lookup:
			matches.append({
				"ocr_data": ocr_record,
				"parcel_data": parcel_lookup[lot_id]["data"],
				"matching_field": _get_lot_id_field_name(ocr_record, lot_id),
				"matched_value": lot_id,
				"confidence": 1.0,
				"match_type": "Exact"
			})
	
	# If no exact matches and fuzzy matching is enabled
	if not matches and matching_mode in ["Fuzzy", "All Matches"]:
		for lot_id in lot_ids:
			for barcode, parcel_info in parcel_lookup.items():
				similarity = calculate_string_similarity(lot_id, barcode)
				if similarity >= 0.8:  # 80% similarity threshold
					matches.append({
						"ocr_data": ocr_record,
						"parcel_data": parcel_info["data"],
						"matching_field": _get_lot_id_field_name(ocr_record, lot_id),
						"matched_value": f"{lot_id} ≈ {barcode}",
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
def export_matched_records(filters):
	"""Export only matched records to Excel."""
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
