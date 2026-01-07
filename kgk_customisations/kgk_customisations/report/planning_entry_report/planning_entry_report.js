// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Planning Entry Report"] = {
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
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee Target"
		},
		{
			"fieldname": "employee_code",
			"label": __("Employee Code"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "reason",
			"label": __("Reason"),
			"fieldtype": "Link",
			"options": "Reason"
		},
		{
			"fieldname": "variance_filter",
			"label": __("Variance Filter"),
			"fieldtype": "Select",
			"options": ["All", "Above Target", "Below Target", "On Target"],
			"default": "All"
		},
		{
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Daily Performance Trend",
				"Achievement % Over Time",
				"Top/Bottom Performers",
				"Variance Distribution",
				"Reason Breakdown",
				"Employee Comparison"
			],
			"default": "Daily Performance Trend"
		}
	]
};
