# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import pandas as pd
from frappe.utils.file_manager import get_file_path
from kgk_customisations.kgk_customisations.utils.input_validator import InputValidator


class ParcelImport(Document):
	pass

@frappe.whitelist()
def process_parcel_import(docname):
	# Validate inputs
	validator = InputValidator()
	validator.validate_document_name(docname, "Parcel Import")
	
	doc = frappe.get_doc("Parcel Import", docname)

	if not doc.upload_file:
		frappe.throw("Please attach an Excel file first.")

	try:
		# Validate file path for security
		file_url = get_file_path(doc.upload_file)
		validator.validate_file_path(file_url, allowed_extensions=['.xlsx', '.xls'])
		df = pd.read_excel(file_url, sheet_name="Report Data", skiprows=5)
		df = df.dropna(axis=1, how="all").dropna(how="all").reset_index(drop=True)

		created = 0
		for idx, row in df.iterrows():
			parcel = frappe.get_doc({
				"doctype": "Parcel",
				"parcel_name": str(row.get("Barcode", f"ROW-{idx}")),
				"barcode": row.get("Barcode"),
				"batch_reference": "BDC2-3/2-24",
				"status": "ROUGH",
				"planner": row.get("Planner"),
				"grader": row.get("Grader"),
				"remarks": row.get("Remarks"),
				# Initialize as empty lists - use consistent naming
				"rough_details": [],
				"polished_details": []
			})

			# Append to rough_details (make sure field name matches)
			parcel.append("rough_details", {
				"qty": row.get("Qty"),
				"carat_org": row.get("Org"),
				"carat_exp": row.get("Exp"),
				"shape": row.get("Shp"),
				"color": row.get("Col"),
				"clarity": row.get("Clr"),
				"quality": row.get("Quality"),
				"rapaport_price": row.get("Rap"),
				"back_percent": row.get("Back"),
				"amount": row.get("Amt")
			})

			# Append to polished_details (make sure field name matches)
			parcel.append("polished_details", {
				"carat_org": row.get("Org.1"),
				"carat_exp": row.get("Exp.1"),
				"shape": row.get("Shp.1"),
				"color": row.get("Col.1"),
				"clarity": row.get("Clr.1"),
				"quality": row.get("Quality.1"),
				"rapaport_price": row.get("Rap.1"),
				"back_percent": row.get("Back.1"),
				"amount": row.get("Amt.1"),
				"remark": row.get("Remark")
			})

			parcel.insert(ignore_permissions=True)
			created += 1

		frappe.db.commit()
		doc.status = "Completed"
		doc.log = f"Imported {created} parcels."
		doc.save()
		return f"{created} Parcels imported successfully."
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Parcel Import Error")
		frappe.throw(f"Error processing import: {str(e)}")

# Temporary debug function - add this to your parcel_import.py

@frappe.whitelist()
def debug_parcel_fields():
    """Debug function to find actual field names in Parcel DocType"""
    try:
        # Get Parcel DocType meta
        parcel_meta = frappe.get_meta("Parcel")
        
        # Get all fields
        all_fields = []
        table_fields = []
        
        for field in parcel_meta.fields:
            all_fields.append({
                "fieldname": field.fieldname,
                "fieldtype": field.fieldtype,
                "label": field.label,
                "options": getattr(field, 'options', None)
            })
            
            if field.fieldtype == "Table":
                table_fields.append({
                    "fieldname": field.fieldname,
                    "label": field.label,
                    "options": field.options
                })
        
        return {
            "all_fields": all_fields,
            "table_fields": table_fields,
            "total_fields": len(all_fields)
        }
        
    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist() 
def process_parcel_import_debug(docname):
    """Debug version of process_parcel_import to find field issues"""
    doc = frappe.get_doc("Parcel Import", docname)

    if not doc.upload_file:
        frappe.throw("Please attach an Excel file first.")

    try:
        file_url = get_file_path(doc.upload_file)
        df = pd.read_excel(file_url, sheet_name="Report Data", skiprows=5)
        df = df.dropna(axis=1, how="all").dropna(how="all").reset_index(drop=True)

        # Debug: Check what fields are available in Parcel DocType
        parcel_meta = frappe.get_meta("Parcel")
        available_fields = [f.fieldname for f in parcel_meta.fields]
        table_fields = [f.fieldname for f in parcel_meta.fields if f.fieldtype == "Table"]
        
        frappe.msgprint(f"Available fields in Parcel: {available_fields}")
        frappe.msgprint(f"Table fields in Parcel: {table_fields}")
        
        # Try creating a simple parcel first
        test_row = df.iloc[0]
        
        parcel_data = {
            "doctype": "Parcel",
            "parcel_name": str(test_row.get("Barcode", "TEST-1")),
            "barcode": test_row.get("Barcode"),
            "batch_reference": "BDC2-3/2-24",
            "status": "ROUGH",
            "planner": test_row.get("Planner"),
            "grader": test_row.get("Grader"),
            "remarks": test_row.get("Remarks")
        }
        
        parcel = frappe.get_doc(parcel_data)
        
        # Try to find the correct table field names
        for table_field in table_fields:
            try:
                frappe.msgprint(f"Testing field: {table_field}")
                parcel.append(table_field, {"test": "test"})
                frappe.msgprint(f"Field {table_field} works!")
            except Exception as e:
                frappe.msgprint(f"Field {table_field} failed: {str(e)}")
        
        return {
            "available_fields": available_fields,
            "table_fields": table_fields,
            "test_data": parcel_data
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Debug Import Error")
        return {"error": str(e), "traceback": frappe.get_traceback()}