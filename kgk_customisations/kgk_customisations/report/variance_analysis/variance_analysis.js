// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Variance Analysis"] = {
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
			"fieldname": "variance_threshold",
			"label": __("Variance Threshold (%)"),
			"fieldtype": "Float",
			"default": 5.0,
			"description": "Show only variances above this percentage"
		},
		{
			"fieldname": "variance_type",
			"label": __("Variance Type"),
			"fieldtype": "Select",
			"options": "\nAll\nPositive Only\nNegative Only\nAbove Threshold",
			"default": "All"
		},
		{
			"fieldname": "status",
			"label": __("Balance Status"),
			"fieldtype": "Select",
			"options": "\nAll\nCalculated\nManually Verified\nERP Verified\nFinally Verified",
			"default": "All"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "variance_amount" && data && data.variance_amount) {
			if (data.variance_amount < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data.variance_amount > 0) {
				value = "<span style='color:orange'>" + value + "</span>";
			}
		}
		
		if (column.fieldname == "variance_percentage" && data && data.variance_percentage) {
			if (Math.abs(data.variance_percentage) > 5) {
				value = "<span style='color:red; font-weight:bold'>" + value + "</span>";
			} else if (Math.abs(data.variance_percentage) > 2) {
				value = "<span style='color:orange'>" + value + "</span>";
			}
		}
		
		if (column.fieldname == "status" && data && data.status) {
			const status_colors = {
				"Calculated": "gray",
				"Manually Verified": "blue",
				"ERP Verified": "green",
				"Finally Verified": "darkgreen"
			};
			const color = status_colors[data.status] || "black";
			value = "<span style='color:" + color + "'>" + value + "</span>";
		}
		
		return value;
	},
	
	"onload": function(report) {
		report.page.add_inner_button(__("Show Trend Chart"), function() {
			frappe.query_report.chart_data = frappe.query_report.get_chart_data();
			frappe.query_report.render_chart();
		});
		
		report.page.add_inner_button(__("Export for Audit"), function() {
			frappe.query_report.export_report('Excel');
		});
		
		report.page.add_inner_button(__("Drill Down Details"), function() {
			const data = frappe.query_report.data;
			if (!data || data.length === 0) {
				frappe.msgprint(__("No data to drill down"));
				return;
			}
			
			// Get selected row or first row with variance
			let selected_row = null;
			const selected = frappe.query_report.get_selected_rows();
			if (selected && selected.length > 0) {
				selected_row = selected[0];
			} else {
				selected_row = data.find(row => Math.abs(row.variance_percentage || 0) > 0);
			}
			
			if (selected_row && selected_row.balance_date) {
				frappe.set_route("List", "Cash Document", {
					"transaction_date": selected_row.balance_date,
					"company": selected_row.company || ""
				});
			}
		});
	}
};
