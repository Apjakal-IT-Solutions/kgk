// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Planning M-Box Report"] = {
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
			"fieldname": "employee_name",
			"label": __("Employee Name"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "factory_code",
			"label": __("Factory Code"),
			"fieldtype": "Link",
			"options": "Factory Code"
		},
		{
			"fieldname": "docstatus",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": [
				"All",
				"Draft",
				"Submitted"
			],
			"default": "Submitted"
		},
		{
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Daily X-Ray Trend",
				"Employee Performance Ranking",
				"Factory Code Comparison",
				"Reason Analysis",
				"Weekly Aggregate",
				"Employee Daily Activity"
			],
			"default": "Daily X-Ray Trend"
		}
	]
};
