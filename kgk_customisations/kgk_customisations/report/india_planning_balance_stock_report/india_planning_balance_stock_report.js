// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["India Planning Balance Stock Report"] = {
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
			"fieldname": "min_pcs",
			"label": __("Min PCS"),
			"fieldtype": "Int"
		},
		{
			"fieldname": "max_pcs",
			"label": __("Max PCS"),
			"fieldtype": "Int"
		},
		{
			"fieldname": "overseas_stock_balance",
			"label": __("Overseas Stock Balance"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Stock Balance Trend",
				"Daily Stock Changes",
				"CTS per PCS Trend",
				"Weekly Stock Summary",
				"Stock Distribution",
				"PCS vs CTS Correlation"
			],
			"default": "Stock Balance Trend"
		}
	]
};
