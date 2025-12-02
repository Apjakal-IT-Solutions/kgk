// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["FM Process Performance Report"] = {
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
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Section"
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
		},
		{
			"fieldname": "day_type",
			"label": __("Day Type"),
			"fieldtype": "Select",
			"options": "All\nNormal\nWeekend",
			"default": "All"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight group headers (month or reason)
		if (data && data.is_group) {
			value = `<strong style="color: #2c3e50;">${value}</strong>`;
		}
		
		// Color formatting for section columns (show positive values in green)
		if (column.fieldname !== "period" && column.fieldname !== "total_days" && 
		    !data.is_group && flt(data[column.fieldname]) > 0) {
			value = `<span style="color: #5cb85c;">${value}</span>`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Enable tree view
		frappe.query_report.tree = true;
	},
	
	"get_datatable_options": function(options) {
		return Object.assign(options, {
			checkboxColumn: false,
			layout: 'fluid',
			treeView: true
		});
	}
};

frappe.query_reports["F.M Process Performance Report"] = {
	"filters": [

	]
};
