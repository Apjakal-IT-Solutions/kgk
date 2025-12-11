// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Stone Prediction Analysis"] = {
	"filters": [
		{
			"fieldname": "serial_number",
			"label": __("Serial Number"),
			"fieldtype": "Data",
			"width": "120"
		},
		{
			"fieldname": "lot_id",
			"label": __("Lot ID"),
			"fieldtype": "Data",
			"width": "120"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname": "predicted_by",
			"label": __("Predicted By"),
			"fieldtype": "Link",
			"options": "User"
		},
		{
			"fieldname": "docstatus",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nSubmitted\nCancelled",
			"default": ""
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight status colors
		if (column.fieldname == "docstatus") {
			if (value == "Draft") {
				value = `<span style="color: orange;">${value}</span>`;
			} else if (value == "Submitted") {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (value == "Cancelled") {
				value = `<span style="color: red;">${value}</span>`;
			}
		}
		
		return value;
	}
};
