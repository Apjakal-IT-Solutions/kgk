// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Balance Report"] = {
	"filters": [
		{
			"fieldname": "date_from",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "date_to",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Select",
			"options": "\nDiamonds\nJewellery\nAgro",
			"reqd": 1
		},
		{
			"fieldname": "currency",
			"label": __("Currency"),
			"fieldtype": "Select",
			"options": "\nUSD\nZAR\nBWP",
			"reqd": 1
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		var fn = column.fieldname;
		if (["basic", "accountant", "checker"].indexOf(fn) !== -1) {
			var color = data.tally ? "lightgreen" : "lightcoral";
			return "<span style='background:" + color + ";padding:2px 6px;display:block;text-align:right'>"
				+ value + "</span>";
		}
		return value;
	}
};
