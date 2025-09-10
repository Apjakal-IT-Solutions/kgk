# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import os
import re


# Extraction logic (adapted from readings_optimisation.py)
def extract_fields(text: str):
	"""
	Tokenise OCR output into field segments, extract with regex,
	apply inference and override rules for Blue UV, Brown, Type,
	handle mis-ordered COLOR/RESULT, enforce strict validation on
	Result and Color, and support Fancy Yellow override.
	"""
	
	t = re.sub(r"[\r\n]+", " ", text or "").upper()
	t = re.sub(r"\bYELL\s*UU\b", "YELL UV", t)
	t = t.replace("=", "-").replace("||", "")
	t = re.sub(r"\bLICHT\b", "LIGHT", t)

	t = re.sub(r"\bLUE\s*UV\b", "BLUE UV", t)
	t = re.sub(r"\bWU\b", "UV", t)
	t = re.sub(r"\bROWN\b", "BROWN", t)

	fancy_override = "CHECK FANCY" in t

	m0 = re.search(r"\b(RESULT|COLOR|BLUE\s*UV)\b", t)
	if m0:
		t = t[m0.start() :]

	fields = [
		"RESULT",
		"COLOR",
		"BLUE\\s*UV",
		"BROWN",
		"YELL?OW\\s*UV",
		"TYPE",
		"FANCY\\s*YELLOW",
	]
	parts = re.split(r"\b(" + "|".join(fields) + r")\b", t, flags=re.IGNORECASE)
	raw = {}
	for i in range(1, len(parts) - 1, 2):
		key = parts[i].strip().upper().replace(" ", "_")
		val = parts[i + 1].strip()
		raw.setdefault(key, val)

	patterns = {
		"RESULT": re.compile(r"([!?]{1,4}|[A-Z0-9+\-]{1,2})"),
		"COLOR": re.compile(r"([A-Z]{1,2}[+\-]?|\d+)"),
		"BLUE_UV": re.compile(r"([A-Z]+)\s*\.?([0-9]{1,3})"),
		"BROWN": re.compile(r"([A-Z? ]+)"),
		"YELLOW_UV": re.compile(r"([A-Z! ]+)"),
		"TYPE": re.compile(r"([A-Z][A-Z ]+)"),
		"FANCY_YELLOW": re.compile(r"([A-Z ]+)"),
	}
	clean = {}
	for fld, pat in patterns.items():
		seg = raw.get(fld, "")
		if fld in ("RESULT", "COLOR"):
			seg = seg.replace(" ", "")
		m = pat.search(seg)
		val = m.group(0).strip() if m else ""
		if fld in ("RESULT", "COLOR"):
			val = val.replace("=", "-")
			dm = re.fullmatch(r"(\d)([+\-]?)", val)
			if dm and dm.group(1) in {"6", "1"}:
				val = {"6": "G", "1": "I"}[dm.group(1)] + dm.group(2)
			if fld == "RESULT" and val.isdigit():
				val = "".join("!" if int(d) < 5 else "?" for d in val)
		if fld == "BLUE_UV" and m:
			val = f"{m.group(1)} {m.group(2)}"
		clean[fld] = val

	col_blob = raw.get("COLOR", "")
	if "RESULT" in col_blob.upper():
		blob = col_blob.replace(" ", "")
		toks = re.findall(r"([A-Z0-9!?+\-]+)", blob)
		if len(toks) >= 2:
			first, second = toks[0], toks[1]
			if first in ("!", "1!"):
				first = "!!"
			elif first.isdigit():
				first = "".join("!" if int(d) < 5 else "?" for d in first)
			clean["RESULT"], clean["COLOR"] = first, second
	elif not clean["COLOR"]:
		resseg = raw.get("RESULT", "").replace(" ", "")
		toks = re.findall(r"([A-Z0-9!?+\-]+)", resseg)
		if len(toks) >= 2:
			first, second = toks[0], toks[1]
			if first in ("!", "1!"):
				first = "!!"
			elif first.isdigit():
				first = "".join("!" if int(d) < 5 else "?" for d in first)
			clean["RESULT"], clean["COLOR"] = first, second

	if clean.get("COLOR") == "1":
		clean["COLOR"] = "I"

	buv = raw.get("BLUE_UV", "")
	m_lbl = re.search(r"\b(FAINT|LIGHT|MEDIUM|STRONG|NONE)\b", buv)
	m_dig = re.search(r"\b(\d{1,4})\b", buv)
	if m_lbl:
		lbl = m_lbl.group(1)
		if lbl == "NONE":
			clean["BLUE_UV"] = "NONE 000"
		elif m_dig:
			code = m_dig.group(1)[:3]
			clean["BLUE_UV"] = f"{lbl} {code}"
		else:
			clean["BLUE_UV"] = lbl
	elif m_dig:
		clean["BLUE_UV"] = m_dig.group(1)[:3]

	if not clean["RESULT"] and "STRONG" in buv:
		clean["RESULT"] = "??"
	if not clean["RESULT"] and raw.get("YELL?OW_UV", ""):
		clean["RESULT"] = "!!"

	br = raw.get("BROWN", "").upper()
	if "TLB?" in br:
		clean["BROWN"] = "TLB?"
	elif re.search(r"\bLB\b", br):
		clean["BROWN"] = "LB!"
	elif "NOT" in br and "MEASURED" in br:
		clean["BROWN"] = "NOT MEASURED"
	elif "NONE" in br:
		clean["BROWN"] = "NONE"
	else:
		clean["BROWN"] = ""

	mT = re.search(r"TYPE\s*2[AB]\s+(MIXED|WHITE|BLUE OR GRAY|GRAY|BROWN)", t)
	clean["TYPE"] = mT.group(1) if mT else ""

	if clean.get("RESULT") in ("!", "1!"):
		clean["RESULT"] = "!!"
	allowed_res = {
		"D",
		"DE",
		"E",
		"E-",
		"E+",
		"F",
		"F-",
		"F+",
		"G",
		"G-",
		"G+",
		"H",
		"H-",
		"H+",
		"I",
		"I-",
		"I+",
		"J",
		"J-",
		"J+",
		"K",
		"K-",
		"K+",
		"?",
		"??",
		"???",
	}
	if (
		not re.fullmatch(r"[!?]{1,4}", clean.get("RESULT", ""))
		and clean.get("RESULT", "") not in allowed_res
	):
		clean["RESULT"] = ""

	c = clean.get("COLOR", "")
	allowed_col = {
		"D",
		"DE",
		"E",
		"E+",
		"E-",
		"F",
		"F+",
		"F-",
		"G",
		"G+",
		"G-",
		"H",
		"H+",
		"H-",
		"I",
		"I+",
		"I-",
		"J",
		"J+",
		"J-",
		"K",
		"K+",
		"K-",
	}
	if re.fullmatch(r"[A-Z]{1,3}[+\-]?", c):
		if c not in allowed_col:
			clean["COLOR"] = ""
	elif not re.fullmatch(r"\d{3}", c):
		clean["COLOR"] = ""

	scale = [chr(x) for x in range(ord("D"), ord("Z") + 1)]
	r0, c0 = clean.get("RESULT", "")[:1], clean.get("COLOR", "")[:1]
	if r0 in scale and c0 in scale and scale.index(c0) < scale.index(r0):
		clean["COLOR"] = clean["RESULT"]

	if not clean["RESULT"]:
		parts = raw.get("RESULT", "").strip().split()
		norm = []
		skip = False
		for i, p in enumerate(parts):
			if skip:
				skip = False
				continue
			if (
				re.fullmatch(r"[A-Z]", p)
				and i + 1 < len(parts)
				and parts[i + 1] in ("+", "-")
			):
				norm.append(p + parts[i + 1])
				skip = True
			elif re.fullmatch(r"[A-Z][+\-]?", p):
				norm.append(p)
			elif re.fullmatch(r"[!?]{1,4}", p):
				norm.append(p)
		if norm:
			clean["RESULT"] = norm[0]

	if not clean["COLOR"]:
		rseg = raw.get("RESULT", "")
		toks = re.findall(r"([A-Z][+\-]?|[!?]{1,4})", rseg.replace(" ", ""))
		if len(toks) >= 2:
			letter_toks = [tok for tok in toks if re.fullmatch(r"[A-Z][+\-]?", tok)]
			if letter_toks:
				clean["COLOR"] = letter_toks[-1]

	if not clean["COLOR"]:
		rc = raw.get("COLOR", "").upper()
		m = re.findall(r"[DEFGHIJK]", rc)
		if m:
			clean["COLOR"] = m[0]
		elif "1" in rc:
			clean["COLOR"] = "I"

	if not clean["COLOR"]:
		rc = raw.get("COLOR", "").upper().strip()
		for bad, good in {"FS": "F", "CH": "H", "1": "I"}.items():
			if rc == bad:
				clean["COLOR"] = good
				break

	if fancy_override:
		clean["FANCY_YELLOW"] = "CHECK FANCY"

	return {
		"Result": clean.get("RESULT", ""),
		"Color": clean.get("COLOR", ""),
		"Blue UV": clean.get("BLUE_UV", ""),
		"Brown": clean.get("BROWN", ""),
		"Yellow UV": clean.get("YELLOW_UV", ""),
		"Type": clean.get("TYPE", ""),
		"Fancy Yellow": clean.get("FANCY_YELLOW", ""),
	}


class OCRDataUpload(Document):
	@frappe.whitelist()
	def preview_excel_data(self):
		"""Load Excel data into child table for preview"""
		try:
			print(f"Preview method called - file_upload: {self.file_upload}")
			
			if not self.file_upload:
				error_msg = "Please upload an Excel file first"
				frappe.msgprint(error_msg, indicator="red")
				return {"success": False, "message": error_msg}

			# Mark file as private for security
			try:
				file_doc = frappe.get_doc("File", {"file_url": self.file_upload})
				if not file_doc.is_private:
					file_doc.is_private = 1
					file_doc.save(ignore_permissions=True)
					frappe.db.commit()
			except Exception as e:
				error_msg = f"Error accessing file: {str(e)}"
				print(f"File access error: {error_msg}")
				frappe.msgprint(error_msg, indicator="red")
				return {"success": False, "message": error_msg}

			# Get file path
			if file_doc.file_url.startswith('/private/'):
				file_path = frappe.get_site_path("private", "files", file_doc.file_name)
			else:
				file_path = frappe.get_site_path("public", "files", file_doc.file_name)

			print(f"File path: {file_path}")

			# Map expected Excel columns to DocType fields (define this first)
			# These should match the actual Excel file column headers
			excel_to_field_mapping = {
				# Common field variations - update these based on your actual Excel headers
				"Sequence": "sequence",
				"Created On": "created_on",				
				"Batch Name": "batch_name",
				"Text Data": "text_data",
				
				# Lot ID variations
				"Lot ID 1": "lot_id_1",
				"Lot ID 2": "lot_id_2",
				"Sub Lot ID": "sub_lot_id",
				
				# Result/analysis fields
				"Result": "result",
				"Color": "color",
				"Blue UV": "blue_uv",
				"Brown": "brown",
				"Yellow UV": "yellow_uv",
				"Type": "type",
				"Fancy Yellow": "fancy_yellow",
			}

			# Read Excel file
			import os
			if not os.path.exists(file_path):
				error_msg = f"File not found at expected location: {file_path}"
				print(f"File not found error: {error_msg}")
				frappe.msgprint(error_msg, indicator="red")
				return {"success": False, "message": error_msg}

			try:
				import pandas as pd
				df = pd.read_excel(file_path)
				print(f"Excel file loaded successfully. Rows: {len(df)}, Columns: {list(df.columns)}")
				
				# Log first few rows to understand data structure
				if len(df) > 0:
					print(f"Sample data from first row:")
					for col in df.columns:
						sample_value = df.iloc[0][col] if not pd.isna(df.iloc[0][col]) else "N/A"
						print(f"  '{col}': {sample_value}")
				
				# Check which Excel columns will be mapped to which fields
				print(f"\nColumn mapping analysis:")
				found_mappings = []
				missing_columns = []
				
				for excel_col, field_name in excel_to_field_mapping.items():
					if excel_col in df.columns:
						found_mappings.append(f"  FOUND: '{excel_col}' -> {field_name}")
						print(f"  FOUND: '{excel_col}' -> {field_name}")
					else:
						missing_columns.append(excel_col)
				
				print(f"\nUnmapped columns in Excel file:")
				for col in df.columns:
					if col not in excel_to_field_mapping:
						print(f"  UNMAPPED: '{col}'")
				
				if missing_columns:
					print(f"\nMissing expected columns: {missing_columns}")
						
			except Exception as e:
				error_msg = f"Error reading Excel file: {str(e)}"
				print(f"Excel read error: {error_msg}")
				frappe.msgprint(error_msg, indicator="red")
				return {"success": False, "message": error_msg}

			# Clear existing items
			self.set('items', [])

			# Add items to child table
			rows_processed = 0
			for index, row in df.iterrows():
				try:
					child = self.append('items', {})
					populated_fields = []
					
					# First, map direct Excel columns to fields
					for excel_col, field_name in excel_to_field_mapping.items():
						if excel_col in df.columns:
							value = row[excel_col]
							if pd.notna(value):
								# Handle date fields specially
								if field_name == 'created_on':
									try:
										# Try to parse different date formats
										if isinstance(value, str):
											# Try DD/MM/YYYY format first
											from datetime import datetime
											try:
												date_obj = datetime.strptime(value, '%d/%m/%Y').date()
											except ValueError:
												try:
													# Try MM/DD/YYYY format
													date_obj = datetime.strptime(value, '%m/%d/%Y').date()
												except ValueError:
													try:
														# Try YYYY-MM-DD format
														date_obj = datetime.strptime(value, '%Y-%m-%d').date()
													except ValueError:
														# Default to today if parsing fails
														date_obj = datetime.today().date()
											setattr(child, field_name, date_obj)
											populated_fields.append(f"{field_name}={date_obj}")
										elif hasattr(value, 'date'):
											# It's already a datetime object
											setattr(child, field_name, value.date())
											populated_fields.append(f"{field_name}={value.date()}")
										else:
											# Default to today
											from datetime import date
											setattr(child, field_name, date.today())
											populated_fields.append(f"{field_name}={date.today()}")
									except Exception as e:
										print(f"Error parsing date {value}: {str(e)}")
										from datetime import date
										setattr(child, field_name, date.today())
										populated_fields.append(f"{field_name}={date.today()}(default)")
								else:
									# Convert to string and truncate if needed
									str_value = str(value)
									if field_name == 'text_data':
										# OCR output can be very long, limit to 8000 chars
										str_value = str_value[:8000]
									elif field_name == 'image_data':
										# Image data can be very long, limit to 10000 chars
										str_value = str_value[:10000]
									else:
										# Other fields, limit to reasonable length
										str_value = str_value[:200]
									setattr(child, field_name, str_value)
									populated_fields.append(f"{field_name}={str_value[:50]}...")
							else:
								# Value is NaN/empty
								populated_fields.append(f"{field_name}=EMPTY")
						else:
							# Excel column not found
							populated_fields.append(f"{excel_col}->NOT_FOUND")
					
					# Now, if we have OCR output text, extract refined values using our extraction logic
					if hasattr(child, 'text_data') and child.text_data:
						try:
							extracted_fields = extract_fields(child.text_data)
							
							# Apply fallback logic from original Excel values (like in reference code)
							# Only update fields if they're not already populated from Excel, with fallbacks
							
							# Result field
							if not getattr(child, 'result', None) and extracted_fields.get('Result'):
								child.result = extracted_fields['Result']
								populated_fields.append(f"result(extracted)={extracted_fields['Result']}")
							
							# Color field with fallback logic
							if not getattr(child, 'color', None):
								if extracted_fields.get('Color'):
									child.color = extracted_fields['Color']
									populated_fields.append(f"color(extracted)={extracted_fields['Color']}")
								else:
									# Fallback: check if original Excel had valid color
									original_color = str(getattr(child, 'color', '') or '').strip().upper()
									if re.fullmatch(r"[DEFGHIJK][+\-]?|\d{3}", original_color):
										child.color = original_color
										populated_fields.append(f"color(fallback)={original_color}")
							
							# Blue UV field
							if not getattr(child, 'blue_uv', None) and extracted_fields.get('Blue UV'):
								child.blue_uv = extracted_fields['Blue UV']
								populated_fields.append(f"blue_uv(extracted)={extracted_fields['Blue UV']}")
							
							# Brown field with specific fallback logic
							if not getattr(child, 'brown', None):
								if extracted_fields.get('Brown'):
									child.brown = extracted_fields['Brown']
									populated_fields.append(f"brown(extracted)={extracted_fields['Brown']}")
								else:
									# Check if original Excel had "NOT MEASURED"
									original_brown = str(getattr(child, 'brown', '') or '').strip().upper()
									if original_brown == "NOT MEASURED":
										child.brown = "NOT MEASURED"
										populated_fields.append(f"brown(fallback)=NOT MEASURED")
							
							# Yellow UV field with special logic
							if not getattr(child, 'yellow_uv', None):
								if extracted_fields.get('Yellow UV'):
									child.yellow_uv = extracted_fields['Yellow UV']
									populated_fields.append(f"yellow_uv(extracted)={extracted_fields['Yellow UV']}")
								elif "YELL UV" in child.text_data.upper():
									child.yellow_uv = "YELL UV"
									populated_fields.append(f"yellow_uv(detected)=YELL UV")
							
							# Type field with fallback
							if not getattr(child, 'type', None):
								if extracted_fields.get('Type'):
									child.type = extracted_fields['Type']
									populated_fields.append(f"type(extracted)={extracted_fields['Type']}")
								else:
									# Check if original Excel had valid type
									original_type = str(getattr(child, 'type', '') or '').strip().upper()
									if original_type in {"MIXED", "WHITE", "BLUE OR GRAY", "GRAY", "BROWN"}:
										child.type = original_type
										populated_fields.append(f"type(fallback)={original_type}")
							
							# Fancy Yellow field
							if not getattr(child, 'fancy_yellow', None) and extracted_fields.get('Fancy Yellow'):
								child.fancy_yellow = extracted_fields['Fancy Yellow']
								populated_fields.append(f"fancy_yellow(extracted)={extracted_fields['Fancy Yellow']}")
									
						except Exception as e:
							print(f"Error extracting from OCR text for row {index}: {str(e)}")
							import traceback
							traceback.print_exc()
					else:
						# No OCR data available
						populated_fields.append("no_ocr_data")
					
					# Set created_on to today if not set
					if not getattr(child, 'created_on', None):
						from datetime import date
						child.created_on = date.today()
						populated_fields.append(f"created_on(default)={date.today()}")
					
					# Log what was populated for first few rows
					if index < 5:
						print(f"Row {index} populated fields: {', '.join(populated_fields)}")
					
					rows_processed += 1
				except Exception as e:
					print(f"Error processing row {index}: {str(e)}")
					import traceback
					traceback.print_exc()
					continue

			# Save the document
			try:
				self.save()
				frappe.db.commit()
			except Exception as e:
				error_msg = f"Error saving document: {str(e)}"
				print(f"Save error: {error_msg}")
				frappe.msgprint(error_msg, indicator="red")
				return {"success": False, "message": error_msg}

			msg = f"Successfully loaded {rows_processed} rows from Excel file."
			frappe.msgprint(msg, indicator="green")
			print(f"Success: {msg}")

			return {
				"success": True,
				"message": msg,
				"rows_loaded": rows_processed
			}

		except Exception as e:
			error_msg = f"Unexpected error in preview_excel_data: {str(e)}"
			frappe.msgprint(error_msg, indicator="red")
			print(f"Unexpected error: {error_msg}")
			import traceback
			traceback.print_exc()
			return {"success": False, "message": error_msg}


@frappe.whitelist()
def download_cumulative_report():
	"""Generate and download cumulative report with refined columns"""
	try:
		import pandas as pd
		from openpyxl import Workbook
		from openpyxl.styles import PatternFill
		from openpyxl.utils.dataframe import dataframe_to_rows
		import io
		
		# Get all OCR Data Upload documents with data
		uploads = frappe.get_all(
			"OCR Data Upload",
			filters={"docstatus": ["!=", 2]},
			fields=["name", "file_upload", "creation", "owner"]
		)
		
		if not uploads:
			frappe.msgprint("No OCR data uploads found", indicator="orange")
			return
			
		all_data = []
		
		for upload in uploads:
			# Get items for each upload
			items = frappe.get_all(
				"OCR Data Item",
				filters={"parent": upload.name},
				fields=["*"]
			)
			
			for item in items:
				# Create base row with all available data (including new fields)
				row = {
					"Upload Date": frappe.utils.formatdate(upload.creation) if upload.creation else "",
					"Created On": frappe.utils.formatdate(item.created_on) if item.created_on else "",
					"Sequence": item.sequence or "",
					"Scan Data": item.scan_data or "",
					"Image Data": item.image_data or "",
					"Batch Name": item.batch_name or "",
					"Text Data": item.text_data or "",
					"Lot ID 1": item.lot_id_1 or "",
					"Lot ID 2": item.lot_id_2 or "",
					"Sub Lot ID": item.sub_lot_id or "",
					"Result": item.result or "",
					"Color": item.color or "",
					"Blue UV": item.blue_uv or "",
					"Yellow UV": item.yellow_uv or "",
					"Brown": item.brown or "",
					"Type": item.type or "",
					"Fancy Yellow": item.fancy_yellow or ""
				}
				
				# Apply advanced extraction logic if OCR output exists
				if item.text_data and item.text_data.strip():
					try:
						refined_data = extract_fields(item.text_data)
						# Add refined columns with "Refined" prefix
						for key, value in refined_data.items():
							refined_key = f"Refined {key}"
							row[refined_key] = value
					except Exception as e:
						print(f"Error processing OCR for item {item.name}: {str(e)}")
						# Add empty refined columns if extraction fails
						for key in ["Result", "Color", "Blue UV", "Brown", "Yellow UV", "Type", "Fancy Yellow"]:
							row[f"Refined {key}"] = ""
				else:
					# Add empty refined columns if no OCR output
					for key in ["Result", "Color", "Blue UV", "Brown", "Yellow UV", "Type", "Fancy Yellow"]:
						row[f"Refined {key}"] = ""
				
				all_data.append(row)
		
		if not all_data:
			frappe.msgprint("No data found in uploads", indicator="orange")
			return
			
		# Create DataFrame with proper column order
		if all_data:
			df = pd.DataFrame(all_data)
			
			# Define proper column order for better readability (including new fields)
			base_columns = [
				"Upload Date", "Sequence", "Created On", "Scan Data", "Image Data", "Batch Name", "Text Data",
				"Lot ID 1", "Lot ID 2", "Sub Lot ID", 
				"Result", "Color", "Blue UV", "Yellow UV", "Brown", "Type", "Fancy Yellow"
			]
			
			refined_columns = [
				"Refined Result", "Refined Color", "Refined Blue UV", "Refined Brown", 
				"Refined Yellow UV", "Refined Type", "Refined Fancy Yellow"
			]
			
			# Reorder columns
			available_base = [col for col in base_columns if col in df.columns]
			available_refined = [col for col in refined_columns if col in df.columns]
			other_columns = [col for col in df.columns if col not in base_columns + refined_columns]
			
			final_column_order = available_base + available_refined + other_columns
			df = df[final_column_order]
		else:
			df = pd.DataFrame()
		
		# Create Excel workbook with better formatting
		wb = Workbook()
		ws = wb.active
		ws.title = "Cumulative OCR Report"
		
		if not df.empty:
			# Add data to worksheet
			for r in dataframe_to_rows(df, index=False, header=True):
				ws.append(r)
			
			# Auto-adjust column widths
			from openpyxl.utils import get_column_letter
			for col_idx, column in enumerate(df.columns, 1):
				column_letter = get_column_letter(col_idx)
				max_length = max(
					len(str(column)),  # Header length
					max([len(str(value)) for value in df[column].fillna("")]) if not df[column].empty else 0
				)
				adjusted_width = min(max_length + 2, 50)  # Max width of 50
				ws.column_dimensions[column_letter].width = adjusted_width
			
			# Style the header row
			from openpyxl.styles import Font, PatternFill, Alignment
			header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
			header_font = Font(bold=True)
			
			for cell in ws[1]:
				cell.fill = header_fill
				cell.font = header_font
				cell.alignment = Alignment(horizontal="center", vertical="center")
			
			# Style the refined columns with yellow background
			yellow_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
			
			# Find refined columns and apply styling
			for col_idx, cell in enumerate(ws[1], 1):
				if cell.value and str(cell.value).startswith("Refined"):
					column_letter = get_column_letter(col_idx)
					# Apply yellow background to entire column (data rows only, not header)
					for row in range(2, ws.max_row + 1):
						ws[f"{column_letter}{row}"].fill = yellow_fill
			
			# Add borders to all cells
			from openpyxl.styles import Border, Side
			thin_border = Border(
				left=Side(style='thin'),
				right=Side(style='thin'),
				top=Side(style='thin'),
				bottom=Side(style='thin')
			)
			
			for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
				for cell in row:
					cell.border = thin_border
		else:
			# Add message if no data
			ws['A1'] = "No data available"
			ws['A1'].font = Font(bold=True)
		
		# Save to bytes
		excel_buffer = io.BytesIO()
		wb.save(excel_buffer)
		excel_buffer.seek(0)
		
		# Create file using Frappe's file handling
		from frappe.utils import now
		filename = f"cumulative_ocr_report_{frappe.utils.today().replace('-', '_')}.xlsx"
		
		try:
			# Use frappe.save_file for proper Excel handling
			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_name": filename,
				"is_private": 1,
				"folder": "Home",
				"content": excel_buffer.getvalue()
			})
			file_doc.insert()
			frappe.db.commit()
			
			msg = f"Report generated successfully with {len(all_data)} records"
			frappe.msgprint(msg, indicator="green")
			
			return {
				"success": True,
				"message": msg,
				"file_url": file_doc.file_url,
				"records_count": len(all_data)
			}
			
		except Exception as file_error:
			# If file creation fails, use direct response download
			print(f"File creation error: {str(file_error)}")
			
			# Set response headers for direct Excel download
			frappe.local.response.filename = filename
			frappe.local.response.filecontent = excel_buffer.getvalue()
			frappe.local.response.type = "download"
			frappe.local.response.headers = {
				"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				"Content-Disposition": f"attachment; filename={filename}"
			}
			
			return {
				"success": True,
				"message": f"Report generated with {len(all_data)} records - downloading directly",
				"download_triggered": True
			}
		
	except Exception as e:
		error_msg = f"Error generating report: {str(e)}"
		print(f"Download report error: {error_msg}")
		frappe.msgprint(error_msg, indicator="red")
		import traceback
		traceback.print_exc()
		return {
			"success": False, 
			"message": error_msg,
			"error_details": str(e)
		}
