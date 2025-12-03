// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Process Efficiency Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
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
			"fieldname": "factory_process",
			"label": __("Factory Process"),
			"fieldtype": "Link",
			"options": "Factory Process"
		},
		{
			"fieldname": "reason",
			"label": __("Reason"),
			"fieldtype": "Link",
			"options": "Reason"
		}
	],
	
	"onload": function(report) {
		// Enable tree view
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
		
		// Highlight group headers (month or reason)
		if (data && data.is_group) {
			value = `<strong style="color: #2c3e50;">${value}</strong>`;
		}
		
		// Color formatting for variance
		if (column.fieldname === "diff") {
			if (flt(data[column.fieldname]) < 0) {
				value = `<span style="color: #ee5a52; font-weight: bold;">${value}</span>`;
			} else if (flt(data[column.fieldname]) > 0) {
				value = `<span style="color: #98d982; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Color formatting for achievement
		if (column.fieldname === "achievement") {
			let achievement = flt(data[column.fieldname]);
			if (achievement >= 100) {
				value = `<span style="color: #98d982; font-weight: bold;">${value}</span>`;
			} else if (achievement >= 80) {
				value = `<span style="color: #ffa00a; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: #ee5a52; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	}
};
