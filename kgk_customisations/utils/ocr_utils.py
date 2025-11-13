# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

"""
OCR Data Processing Utilities
============================

Centralized functions for OCR data processing, extraction, and reporting.
Used by OCR Data Upload DocType and OCR-Parcel Merge Report.
"""

import frappe
import pandas as pd
from frappe.utils import now_datetime, today, formatdate
import re


def extract_ocr_fields_from_text(text: str):
	"""
	Tokenise OCR output into field segments, extract with regex,
	apply inference and override rules for Blue UV, Brown, Type,
	handle mis-ordered COLOR/RESULT, enforce strict validation on
	Result and Color, and support Fancy Yellow override.
	
	Extracted from ocr_data_upload.py for reusability.
	Used by: OCR Data Upload preview, OCR-Parcel merge report
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


@frappe.whitelist()
def get_consolidated_ocr_data(from_date=None, to_date=None, filters=None, format="dict", include_refined=True):
	"""
	Centralized OCR data retrieval function.
	
	Args:
		from_date: Filter records from this date (ISO format)
		to_date: Filter records to this date (ISO format)
		filters: Additional filters dict
		format: "dict" | "dataframe" | "excel_ready"
		include_refined: Whether to include refined/extracted fields
		
	Returns:
		List of records or DataFrame based on format
		
	Used by:
		- OCR Data Upload cumulative report
		- OCR-Parcel merge report
		- Future OCR data consumers
	"""
	try:
		# Build base query for OCR data
		upload_filters = {"docstatus": ("!=", 2)}
		
		# Add date filtering if specified
		if from_date:
			upload_filters["creation"] = (">=", from_date)
		if to_date:
			upload_filters["creation"] = ("<=", to_date)
		
		# Add custom filters if provided
		if filters and isinstance(filters, dict):
			upload_filters.update(filters)
		
		# Get matching OCR Data Upload records
		uploads = frappe.get_all("OCR Data Upload", 
			filters=upload_filters,
			fields=["name", "creation"],
			order_by="creation desc"
		)
		
		if not uploads:
			return [] if format == "dict" else pd.DataFrame()
		
		# Get all OCR Data Items for these uploads
		upload_names = [upload.name for upload in uploads]
		
		# Base fields from OCR Data Item
		item_fields = [
			"name", "parent", "sequence", "created_on", "batch_name", "text_data",
			"lot_id_1", "lot_id_2", "sub_lot_id", "result", "color", 
			"blue_uv", "yellow_uv", "brown", "type", "fancy_yellow"
		]
		
		# Get OCR items
		ocr_items = []
		for upload in uploads:
			upload_date = formatdate(upload.creation) if upload.creation else ""
			
			items = frappe.db.sql("""
				SELECT sequence, created_on, batch_name, text_data, lot_id_1, lot_id_2, 
					   sub_lot_id, result, color, blue_uv, yellow_uv, brown, type, fancy_yellow
				FROM `tabOCR Data Item` 
				WHERE parent = %s
				ORDER BY sequence
			""", upload.name, as_dict=True)
			
			for item in items:
				# Build consolidated record
				record = {
					"upload_name": upload.name,
					"upload_date": upload_date,
					"sequence": item.sequence or "",
					"created_on": formatdate(item.created_on) if item.created_on else "",
					"batch_name": item.batch_name or "",
					"text_data": item.text_data or "",
					"lot_id_1": item.lot_id_1 or "",
					"lot_id_2": item.lot_id_2 or "",
					"sub_lot_id": item.sub_lot_id or "",
					"result": item.result or "",
					"color": item.color or "",
					"blue_uv": item.blue_uv or "",
					"yellow_uv": item.yellow_uv or "",
					"brown": item.brown or "",
					"type": item.type or "",
					"fancy_yellow": item.fancy_yellow or ""
				}
				
				# Add refined fields if requested and text data exists
				if include_refined and item.text_data and item.text_data.strip():
					try:
						refined_data = extract_ocr_fields_from_text(item.text_data)
						record.update({
							"refined_result": refined_data.get("Result", ""),
							"refined_color": refined_data.get("Color", ""),
							"refined_blue_uv": refined_data.get("Blue UV", ""),
							"refined_brown": refined_data.get("Brown", ""),
							"refined_yellow_uv": refined_data.get("Yellow UV", ""),
							"refined_type": refined_data.get("Type", ""),
							"refined_fancy_yellow": refined_data.get("Fancy Yellow", "")
						})
					except Exception as e:
						# If refinement fails, add empty refined fields
						record.update({
							"refined_result": "",
							"refined_color": "",
							"refined_blue_uv": "",
							"refined_brown": "",
							"refined_yellow_uv": "",
							"refined_type": "",
							"refined_fancy_yellow": ""
						})
						frappe.log_error(f"OCR refinement error for {upload.name}: {str(e)}")
				elif include_refined:
					# Add empty refined fields if no text data
					record.update({
						"refined_result": "",
						"refined_color": "",
						"refined_blue_uv": "",
						"refined_brown": "",
						"refined_yellow_uv": "",
						"refined_type": "",
						"refined_fancy_yellow": ""
					})
				
				ocr_items.append(record)
		
		# Return data in requested format
		if format == "dataframe":
			return pd.DataFrame(ocr_items)
		elif format == "excel_ready":
			return prepare_excel_data(ocr_items, include_refined)
		else:
			return ocr_items
			
	except Exception as e:
		frappe.log_error(f"Error in get_consolidated_ocr_data: {str(e)}")
		if format == "dataframe":
			return pd.DataFrame()
		return []


def prepare_excel_data(ocr_items, include_refined=True):
	"""
	Prepare OCR data for Excel export with proper formatting.
	
	Args:
		ocr_items: List of OCR records
		include_refined: Include refined analysis columns
		
	Returns:
		Dict with headers, data, and formatting info
	"""
	try:
		# Define headers
		base_headers = [
			"Upload Date", "Sequence", "Created On", "Batch Name", "Text Data",
			"Lot ID 1", "Lot ID 2", "Sub Lot ID", "Result", "Color", 
			"Blue UV", "Yellow UV", "Brown", "Type", "Fancy Yellow"
		]
		
		refined_headers = [
			"Refined Result", "Refined Color", "Refined Blue UV", "Refined Brown",
			"Refined Yellow UV", "Refined Type", "Refined Fancy Yellow"
		]
		
		headers = base_headers + (refined_headers if include_refined else [])
		
		# Prepare data rows
		data_rows = []
		for item in ocr_items:
			row = [
				item.get("upload_date", ""),
				item.get("sequence", ""),
				item.get("created_on", ""),
				item.get("batch_name", ""),
				(item.get("text_data", "") or "")[:1000],  # Truncate for Excel
				item.get("lot_id_1", ""),
				item.get("lot_id_2", ""),
				item.get("sub_lot_id", ""),
				item.get("result", ""),
				item.get("color", ""),
				item.get("blue_uv", ""),
				item.get("yellow_uv", ""),
				item.get("brown", ""),
				item.get("type", ""),
				item.get("fancy_yellow", "")
			]
			
			if include_refined:
				row.extend([
					item.get("refined_result", ""),
					item.get("refined_color", ""),
					item.get("refined_blue_uv", ""),
					item.get("refined_brown", ""),
					item.get("refined_yellow_uv", ""),
					item.get("refined_type", ""),
					item.get("refined_fancy_yellow", "")
				])
			
			data_rows.append(row)
		
		return {
			"headers": headers,
			"data": data_rows,
			"refined_column_start": len(base_headers) if include_refined else None,
			"total_records": len(data_rows)
		}
		
	except Exception as e:
		frappe.log_error(f"Error in prepare_excel_data: {str(e)}")
		return {
			"headers": [],
			"data": [],
			"refined_column_start": None,
			"total_records": 0
		}