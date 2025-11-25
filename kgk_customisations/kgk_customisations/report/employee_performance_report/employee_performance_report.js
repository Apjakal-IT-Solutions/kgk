// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Performance Report"] = {
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
			"fieldname": "section",
			"label": __("Section"),
			"fieldtype": "Link",
			"options": "Section"
		},
		{
			"fieldname": "min_achievement",
			"label": __("Min Achievement %"),
			"fieldtype": "Float",
			"description": __("Show only employees with achievement above this percentage")
		}
	]
};
