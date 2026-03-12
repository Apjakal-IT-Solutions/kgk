// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Balance Report"] = {
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
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		// Color both cells (accountant, checker) in each bank group
		// based on the hidden tally_{i} column (1=green, 0=red)
		var fn = column.fieldname;
		var match = fn.match(/^bank_(\d+)_(accountant|checker)$/);
		if (match) {
			var idx = match[1];
			var tally = data["tally_" + idx];
			var color = tally ? "lightgreen" : "lightcoral";
			return "<span style='background:" + color + ";padding:2px 6px;display:block;text-align:right'>"
				+ value + "</span>";
		}
		return value;
	}
};
