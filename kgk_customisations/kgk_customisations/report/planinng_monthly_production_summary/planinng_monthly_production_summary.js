// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Planinng Monthly Production Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": "2025-07-01",
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"), 
			"fieldtype": "Date",
			"default": "2025-11-30",
			"reqd": 1
		},
		{
			"fieldname": "view_type",
			"label": __("View Type"),
			"fieldtype": "Select",
			"options": ["Monthly", "Reason-wise"],
			"default": "Monthly",
			"reqd": 1
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Section"
		},
		{
			"fieldname": "reason",
			"label": __("Reason"),
			"fieldtype": "Link",
			"options": "Reason"
		}
	],
	
	"onload": function(report) {
		// Enable tree view for both view types
		frappe.query_report.tree = true;
	},
	
	"get_datatable_options": function(options) {
		return Object.assign(options, {
			checkboxColumn: false,
			treeView: true,
			layout: 'fixed'
		});
	},
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color formatting for difference values
		if (column.fieldname === "diff" || column.fieldname === "diff_percentage") {
			if (flt(data[column.fieldname]) < 0) {
				value = `<span style="color: #d73527; font-weight: bold;">${value}</span>`;
			} else if (flt(data[column.fieldname]) > 0) {
				value = `<span style="color: #5cb85c; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Highlight reason column
		if (column.fieldname === "reason" && data.reason) {
			value = `<span style="font-weight: bold; color: #2196F3;">${value}</span>`;
		}
		
		// Row highlighting for group headers
		if (data.is_group) {
			value = `<span style="font-weight: bold; background-color: #f5f5f5;">${value}</span>`;
		}
		
		return value;
	}
};
