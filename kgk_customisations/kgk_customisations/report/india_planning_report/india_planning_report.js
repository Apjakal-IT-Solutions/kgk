// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["India Planning Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
			"fieldname": "has_target",
			"label": __("Target Filter"),
			"fieldtype": "Select",
			"options": ["All", "Only with Target", "Only without Target"],
			"default": "All"
		},
		{
			"fieldname": "variance_filter",
			"label": __("Variance Filter"),
			"fieldtype": "Select",
			"options": ["All", "Above Target", "Below Target", "On Target", "No Target"],
			"default": "All"
		},
		{
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Daily Trend",
				"Achievement % Over Time",
				"Stones vs CTS Correlation",
				"Monthly Aggregates",
				"Variance Distribution",
				"Avg CTS per Stone Trend"
			],
			"default": "Daily Trend"
		}
	]
};
