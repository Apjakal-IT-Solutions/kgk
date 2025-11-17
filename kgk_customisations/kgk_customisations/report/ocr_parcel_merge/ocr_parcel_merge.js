// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["OCR Parcel Merge"] = {
	"filters": [
		{
			"fieldname": "parcel_file",
			"label": __("Parcel File"),
			"fieldtype": "Attach",
			"width": "200px",
			"reqd": 1,
			"description": "Upload Excel file containing Parcel data with barcode column for matching"
		},
		{
			"fieldname": "matching_mode",
			"label": __("Matching Mode"),
			"fieldtype": "Select",
			"options": "\nStrict\nFuzzy",
			"default": "Strict",
			"width": "120px",
			"description": "Strict: Exact matches only, Fuzzy: Similar matches (80%+ similarity)"
		},
		{
			"fieldname": "lot_id_filter",
			"label": __("Lot ID Filter"),
			"fieldtype": "Data",
			"width": "120px",
			"description": "Filter by specific Lot ID pattern (optional)"
		},
		{
			"fieldname": "barcode_filter",
			"label": __("Barcode Filter"),
			"fieldtype": "Data",
			"width": "120px",
			"description": "Filter by specific barcode pattern (optional)"
		}
	],
	
	"onload": function(report) {
		// Handle route options for filtering
		if (frappe.route_options) {
			Object.keys(frappe.route_options).forEach(key => {
				if (report.get_filter(key)) {
					report.set_filter_value(key, frappe.route_options[key]);
				}
			});
			frappe.route_options = null;
			report.refresh();
		}
		
		// Simple message about the report focus
		report.page.add_inner_message(__("This report shows all columns from OCR and Parcel data for MATCHED records only."));
	},
	
	"formatter": function (value, row, column, data, default_formatter) {
		// Highlight match status
		if (column.fieldname === 'match_status') {
			if (value && value.includes('MATCHED')) {
				return `<span class="indicator green">${value}</span>`;
			}
		}
		
		// Highlight match confidence
		if (column.fieldname === 'match_confidence') {
			const confidence = parseFloat(value);
			if (confidence >= 0.9) {
				return `<span style="background-color: #d4edda; padding: 2px 6px; border-radius: 3px; color: #155724;">${(confidence * 100).toFixed(1)}%</span>`;
			} else if (confidence >= 0.8) {
				return `<span style="background-color: #fff3cd; padding: 2px 6px; border-radius: 3px; color: #856404;">${(confidence * 100).toFixed(1)}%</span>`;
			} else if (confidence >= 0.5) {
				return `<span style="background-color: #f8d7da; padding: 2px 6px; border-radius: 3px; color: #721c24;">${(confidence * 100).toFixed(1)}%</span>`;
			}
		}
		
		// Highlight refined columns (AI-processed fields) - matches cumulative report style
		if (column.fieldname && column.fieldname.startsWith('refined_') && value) {
			return `<span style="background-color: #e3f2fd; padding: 2px 4px; border-radius: 3px; border-left: 3px solid #2196f3; font-weight: 500;">${value}</span>`;
		}
		
		// Highlight OCR Upload Name as clickable links
		if (column.fieldname === 'upload_name' && value) {
			return `<a href="#Form/OCR Data Upload/${value}" target="_blank">${value}</a>`;
		}
		
		// Show matching lot IDs and barcodes in a special color
		if ((column.fieldname.includes('lot_id') || column.fieldname === 'barcode' || column.fieldname === 'main_barcode') && value) {
			return `<span style="background-color: #f3e5f5; padding: 1px 3px; border-radius: 2px; font-weight: 500;">${value}</span>`;
		}
		
		return default_formatter(value, row, column, data);
	}
};
