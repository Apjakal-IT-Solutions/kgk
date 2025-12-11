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
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
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
	},
	
	"onload": function(report) {
		// Add custom button to view detailed cuts
		report.page.add_inner_button(__("View Cuts Details"), function() {
			let filters = report.get_values();
			if (!filters.serial_number && !filters.lot_id) {
				frappe.msgprint(__("Please select Serial Number or Lot ID to view cut details"));
				return;
			}
			
			frappe.set_route("query-report", "Stone Cuts Detail", {
				serial_number: filters.serial_number,
				lot_id: filters.lot_id
			});
		});
	}
};
