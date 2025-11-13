# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

"""
File Processing Utilities
=========================

Centralized functions for file upload, reading, validation, and processing.
Used by Parcel import and OCR-Parcel merge report.
"""

import frappe
import pandas as pd
import os
from frappe.utils.file_manager import get_file_path


def read_excel_file_safely(file_url, expected_columns=None, sheet_name=None):
	"""
	Safely read Excel/CSV file with validation and error handling.
	
	Args:
		file_url: File URL from Frappe File DocType
		expected_columns: List of required column names
		sheet_name: Specific sheet name for Excel files (default None = first sheet)
		
	Returns:
		Dict with success status, DataFrame, and error info
		
	Used by:
		- Parcel Stone import
		- OCR-Parcel merge report
		- Future file processing features
	"""
	try:
		# Get and validate file path
		file_path = get_file_path_from_url(file_url)
		
		if not os.path.exists(file_path):
			return {
				"success": False,
				"error": f"File not found: {file_path}",
				"dataframe": None
			}
		
		# Determine file type and read accordingly
		file_extension = os.path.splitext(file_path)[1].lower()
		
		if file_extension in ['.xlsx', '.xls']:
			# Excel file
			if sheet_name:
				df = pd.read_excel(file_path, sheet_name=sheet_name, engine="pyxlsb" if file_extension == '.xlsx' else None)
			else:
				df = pd.read_excel(file_path, engine="pyxlsb" if file_extension == '.xlsx' else None)
		elif file_extension == '.csv':
			# CSV file
			df = pd.read_csv(file_path)
		else:
			return {
				"success": False,
				"error": f"Unsupported file type: {file_extension}. Please use Excel (.xlsx/.xls) or CSV files.",
				"dataframe": None
			}
		
		# Check if file is empty
		if df.empty:
			return {
				"success": False,
				"error": "No data found in the file",
				"dataframe": None
			}
		
		# Clean column names
		df.columns = [str(c).strip() for c in df.columns]
		
		# Validate expected columns if provided
		validation_result = None
		if expected_columns:
			validation_result = validate_file_structure(df, expected_columns)
			if not validation_result["valid"]:
				return {
					"success": False,
					"error": f"File validation failed: {validation_result['message']}",
					"dataframe": None,
					"validation": validation_result
				}
		
		return {
			"success": True,
			"error": None,
			"dataframe": df,
			"file_info": {
				"path": file_path,
				"extension": file_extension,
				"rows": len(df),
				"columns": len(df.columns),
				"column_names": list(df.columns)
			},
			"validation": validation_result
		}
		
	except Exception as e:
		return {
			"success": False,
			"error": f"Error reading file: {str(e)}",
			"dataframe": None
		}


def validate_file_structure(df, required_columns=None, optional_columns=None):
	"""
	Validate DataFrame structure against expected column requirements.
	
	Args:
		df: Pandas DataFrame
		required_columns: List of mandatory columns
		optional_columns: List of optional columns
		
	Returns:
		Dict with validation results and recommendations
	"""
	try:
		validation_result = {
			"valid": True,
			"message": "",
			"missing_required": [],
			"found_columns": list(df.columns),
			"suggestions": []
		}
		
		if required_columns:
			# Check for required columns
			missing_required = []
			for req_col in required_columns:
				# Case-insensitive and flexible matching
				found = False
				for df_col in df.columns:
					if req_col.lower() in df_col.lower() or df_col.lower() in req_col.lower():
						found = True
						break
				
				if not found:
					missing_required.append(req_col)
			
			validation_result["missing_required"] = missing_required
			
			if missing_required:
				validation_result["valid"] = False
				validation_result["message"] = f"Missing required columns: {', '.join(missing_required)}"
				
				# Suggest similar columns
				for missing_col in missing_required:
					similar_cols = []
					for df_col in df.columns:
						# Simple similarity check
						if any(word.lower() in df_col.lower() for word in missing_col.lower().split()):
							similar_cols.append(df_col)
					
					if similar_cols:
						validation_result["suggestions"].append({
							"missing": missing_col,
							"suggestions": similar_cols[:3]  # Top 3 suggestions
						})
		
		return validation_result
		
	except Exception as e:
		return {
			"valid": False,
			"message": f"Validation error: {str(e)}",
			"missing_required": [],
			"found_columns": [],
			"suggestions": []
		}


def extract_column_data_safely(df, column_mapping, row_index=None):
	"""
	Extract data from DataFrame using column mapping with error handling.
	
	Args:
		df: Pandas DataFrame
		column_mapping: Dict mapping expected names to actual column names
		row_index: Specific row to extract (None for all rows)
		
	Returns:
		Extracted data with error tracking
	"""
	try:
		if row_index is not None:
			# Extract single row
			if row_index >= len(df):
				return {
					"success": False,
					"error": f"Row index {row_index} out of range (max: {len(df)-1})",
					"data": None
				}
			
			row = df.iloc[row_index]
			extracted_data = {}
			missing_columns = []
			
			for expected_name, actual_column in column_mapping.items():
				if actual_column in df.columns:
					value = row[actual_column]
					# Handle NaN values
					if pd.isna(value):
						extracted_data[expected_name] = None
					else:
						extracted_data[expected_name] = str(value).strip()
				else:
					missing_columns.append(actual_column)
					extracted_data[expected_name] = None
			
			return {
				"success": True,
				"error": None,
				"data": extracted_data,
				"missing_columns": missing_columns
			}
		else:
			# Extract all rows
			extracted_rows = []
			missing_columns = set()
			
			for idx, row in df.iterrows():
				extracted_data = {}
				
				for expected_name, actual_column in column_mapping.items():
					if actual_column in df.columns:
						value = row[actual_column]
						if pd.isna(value):
							extracted_data[expected_name] = None
						else:
							extracted_data[expected_name] = str(value).strip()
					else:
						missing_columns.add(actual_column)
						extracted_data[expected_name] = None
				
				extracted_rows.append(extracted_data)
			
			return {
				"success": True,
				"error": None,
				"data": extracted_rows,
				"missing_columns": list(missing_columns)
			}
			
	except Exception as e:
		return {
			"success": False,
			"error": f"Data extraction error: {str(e)}",
			"data": None
		}


def get_file_path_from_url(file_url):
	"""
	Convert Frappe file URL to actual file system path.
	
	Args:
		file_url: File URL from File DocType
		
	Returns:
		Absolute file path or raises error
	"""
	try:
		# Handle different URL formats
		if not file_url:
			raise ValueError("File URL is required")
		
		# Remove leading slash if present
		clean_url = file_url.strip("/")
		
		# Get the full site path
		file_path = frappe.get_site_path(clean_url)
		
		return file_path
		
	except Exception as e:
		frappe.throw(f"Error resolving file path from URL '{file_url}': {str(e)}")