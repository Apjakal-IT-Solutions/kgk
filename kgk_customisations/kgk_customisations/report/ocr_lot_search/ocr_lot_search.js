// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["OCR Lot Search"] = {
	"filters": [
		{
			"fieldname": "lot_id",
			"label": __("Lot ID"),
			"fieldtype": "Data",
			"width": "120",
			"reqd": 1
		},
		{
			"fieldname": "search_field",
			"label": __("Search In"),
			"fieldtype": "Select",
			"options": "All Fields\nLot ID 1\nLot ID 2\nSub Lot ID\nBatch Name",
			"default": "Lot ID 1",
			"width": "120"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "100"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "100"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight the refined columns with light green background
		let refined_columns = [
			"refined_result", "refined_color", "refined_blue_uv", 
			"refined_brown", "refined_yellow_uv", "refined_type", "refined_fancy_yellow"
		];
		
		if (refined_columns.includes(column.fieldname)) {
			if (value && value !== "") {
				value = `<span style="background-color: #d4edda; padding: 2px 4px; border-radius: 3px;">${value}</span>`;
			}
		}
		
		// Highlight matching lot IDs with yellow background
		if (column.fieldname === "lot_id_1" || column.fieldname === "lot_id_2" || column.fieldname === "sub_lot_id") {
			let search_term = frappe.query_report.get_filter_value('lot_id');
			if (value && search_term && value.toString().includes(search_term)) {
				value = `<span style="background-color: #fffacd; font-weight: bold; padding: 2px 4px; border-radius: 3px;">${value}</span>`;
			}
		}
		
		return value;
	}
};
