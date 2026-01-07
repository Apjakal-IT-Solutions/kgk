// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Laser Stock Position Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "type",
			"label": __("Type"),
			"fieldtype": "Link",
			"options": "Laser Positoin Type"
		},
		{
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Daily Total Trend",
				"Type Distribution",
				"Type Comparison by CTS",
				"Daily Type Breakdown",
				"Average CTS per Type",
				"Time-based Pattern"
			],
			"default": "Daily Total Trend"
		}
	]
};
