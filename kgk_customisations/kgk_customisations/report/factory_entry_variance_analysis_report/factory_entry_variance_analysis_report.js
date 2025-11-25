// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Factory Entry Variance Analysis Report"] = {
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
			"fieldname": "negative_variance_only",
			"label": __("Show Only Negative Variance"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "variance_threshold",
			"label": __("Variance Threshold %"),
			"fieldtype": "Float",
			"description": __("Show only records where variance % exceeds this threshold")
		}
	]
};
