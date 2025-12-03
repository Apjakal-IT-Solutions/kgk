// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Cash Summary"] = {
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
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company"
		},
		{
			"fieldname": "currency",
			"label": __("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"default": "BWP"
		},
		{
			"fieldname": "group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": "Date\nCompany\nDocument Type",
			"default": "Date"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Highlight negative variance
		if (column.fieldname === "variance" && data && data.variance < 0) {
			value = "<span style='color: red'>" + value + "</span>";
		}
		
		// Highlight high variance percentage
		if (column.fieldname === "variance_percentage" && data && Math.abs(data.variance_percentage) > 5) {
			value = "<span style='color: orange; font-weight: bold'>" + value + "</span>";
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add chart
		report.page.add_inner_button(__("Show Chart"), function() {
			report.refresh();
		});
	}
};
