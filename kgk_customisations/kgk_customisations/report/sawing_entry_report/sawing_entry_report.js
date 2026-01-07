// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Sawing Entry Report"] = {
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
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Daily Production Trend",
				"Sheet Comparison",
				"Success Rate Analysis",
				"Input vs Output (Sheet A)",
				"Input vs Output (Sheet B)",
				"Weekly Quality Comparison"
			],
			"default": "Daily Production Trend"
		}
	]
};
