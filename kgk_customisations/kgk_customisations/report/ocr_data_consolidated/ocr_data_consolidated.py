# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	"""Main function for the report"""
	try:
		columns = get_columns()
		data = get_data(filters)
		return columns, data
	except Exception as e:
		frappe.log_error(f"Error in OCR Data Consolidated report: {str(e)}", "Report Error")
		frappe.throw(f"Error generating report: {str(e)}")


def get_columns():
	"""Return the columns for the report"""
	return [
		{
			"label": _("Upload Date"),
			"fieldname": "upload_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Upload ID"),
			"fieldname": "upload_id",
			"fieldtype": "Link",
			"options": "OCR Data Upload",
			"width": 150
		},
		{
			"label": _("Status"),
			"fieldname": "processing_status",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Lot ID"),
			"fieldname": "lot_id_1",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Sub Lot"),
			"fieldname": "sub_lot_id",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Result (Original)"),
			"fieldname": "result_original",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Result (Processed)"),
			"fieldname": "result_processed",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Color (Original)"),
			"fieldname": "color_original",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Color (Processed)"),
			"fieldname": "color_processed",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Blue UV (Original)"),
			"fieldname": "blue_uv_original",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Blue UV (Processed)"),
			"fieldname": "blue_uv_processed",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Brown (Original)"),
			"fieldname": "brown_original",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Brown (Processed)"),
			"fieldname": "brown_processed",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Yellow UV (Original)"),
			"fieldname": "yellow_uv_original",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Yellow UV (Processed)"),
			"fieldname": "yellow_uv_processed",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Type (Original)"),
			"fieldname": "type_original",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Type (Processed)"),
			"fieldname": "type_processed",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Fancy Yellow (Original)"),
			"fieldname": "fancy_yellow_original",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Fancy Yellow (Processed)"),
			"fieldname": "fancy_yellow_processed",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Text Data"),
			"fieldname": "text_data",
			"fieldtype": "Long Text",
			"width": 200
		}
	]


def get_data(filters):
	"""Get the cumulative data for the report - all OCR data up to the specified date or latest upload"""
	conditions = get_conditions(filters)
	
	# If upload_id is specified, show cumulative data up to that upload date
	upload_date_condition = ""
	if filters and filters.get("upload_id"):
		upload_doc = frappe.get_doc("OCR Data Upload", filters.get("upload_id"))
		upload_date_condition = f"AND upload.upload_date <= '{upload_doc.upload_date}'"
	
	query = f"""
		SELECT 
			upload.upload_date,
			upload.name as upload_id,
			upload.status as upload_status,
			item.lot_id_1,
			item.sub_lot_id,
			item.result_original,
			item.result_processed,
			item.color_original,
			item.color_processed,
			item.blue_uv_original,
			item.blue_uv_processed,
			item.brown_original,
			item.brown_processed,
			item.yellow_uv_original,
			item.yellow_uv_processed,
			item.type_original,
			item.type_processed,
			item.fancy_yellow_original,
			item.fancy_yellow_processed,
			item.text_data,
			CASE 
				WHEN item.result_processed IS NOT NULL AND item.result_processed != '' 
				THEN 'Processed' 
				ELSE 'Original' 
			END as processing_status
		FROM 
			`tabOCR Data Upload` upload
		INNER JOIN 
			`tabOCR Data Item` item ON item.parent = upload.name
		WHERE 
			upload.docstatus < 2
			AND upload.status IN ('Uploaded', 'Processed')
			{upload_date_condition}
			{conditions}
		ORDER BY 
			upload.upload_date DESC, item.lot_id_1, item.sub_lot_id
	"""
	
	data = frappe.db.sql(query, as_dict=True)
	
	# Add summary statistics
	if data:
		total_records = len(data)
		processed_records = len([d for d in data if d.get('processing_status') == 'Processed'])
		
		# Add a summary row at the top
		summary_row = {
			'upload_date': 'SUMMARY',
			'upload_id': f'Total Records: {total_records}',
			'lot_id_1': f'Processed: {processed_records}',
			'sub_lot_id': f'Success Rate: {round((processed_records/total_records)*100, 1)}%' if total_records > 0 else '0%',
			'result_original': '',
			'result_processed': f'Coverage: {round((processed_records/total_records)*100, 1)}%' if total_records > 0 else '0%',
			'processing_status': 'SUMMARY'
		}
		data.insert(0, summary_row)
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions for the query"""
	conditions = ""
	
	# Handle case where filters is None
	if not filters:
		filters = {}
	
	if filters.get("from_date"):
		conditions += f" AND upload.upload_date >= '{filters.get('from_date')}'"
	
	if filters.get("to_date"):
		conditions += f" AND upload.upload_date <= '{filters.get('to_date')}'"
	
	if filters.get("upload_id"):
		conditions += f" AND upload.name = '{filters.get('upload_id')}'"
	
	if filters.get("status"):
		conditions += f" AND upload.status = '{filters.get('status')}'"
	
	return conditions
