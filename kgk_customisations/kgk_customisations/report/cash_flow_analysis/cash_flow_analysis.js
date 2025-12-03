// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Flow Analysis"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -6),
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
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": "Daily\nWeekly\nMonthly\nQuarterly\nYearly",
			"default": "Monthly",
			"reqd": 1
		},
		{
			"fieldname": "comparison_period",
			"label": __("Compare With"),
			"fieldtype": "Select",
			"options": "\nPrevious Period\nSame Period Last Year\nBoth"
		},
		{
			"fieldname": "show_forecast",
			"label": __("Show Forecast"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "forecast_months",
			"label": __("Forecast Months"),
			"fieldtype": "Int",
			"default": 3,
			"depends_on": "eval:doc.show_forecast==1"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "net_cash_flow" && data && data.net_cash_flow) {
			if (data.net_cash_flow < 0) {
				value = "<span style='color:red; font-weight:bold'>" + value + "</span>";
			} else if (data.net_cash_flow > 0) {
				value = "<span style='color:green; font-weight:bold'>" + value + "</span>";
			}
		}
		
		if (column.fieldname == "growth_percentage" && data) {
			const growth = data.growth_percentage || 0;
			if (growth > 10) {
				value = "<span style='color:green'>↑ " + value + "</span>";
			} else if (growth < -10) {
				value = "<span style='color:red'>↓ " + value + "</span>";
			} else {
				value = "<span style='color:gray'>→ " + value + "</span>";
			}
		}
		
		if (column.fieldname == "forecast_amount" && data && data.forecast_amount) {
			value = "<span style='color:blue; font-style:italic'>" + value + "</span>";
		}
		
		return value;
	},
	
	"onload": function(report) {
		report.page.add_inner_button(__("Show Trend Chart"), function() {
			frappe.query_report.chart_data = frappe.query_report.get_chart_data();
			frappe.query_report.render_chart();
		});
		
		report.page.add_inner_button(__("Export for Analysis"), function() {
			frappe.query_report.export_report('Excel');
		});
		
		report.page.add_inner_button(__("Period Comparison"), function() {
			show_period_comparison();
		});
		
		report.page.add_inner_button(__("Cash Flow Statement"), function() {
			const filters = frappe.query_report.get_filter_values();
			generate_cash_flow_statement(filters);
		});
		
		function show_period_comparison() {
			const data = frappe.query_report.data;
			if (!data || data.length < 2) {
				frappe.msgprint(__("Insufficient data for comparison"));
				return;
			}
			
			// Compare last two periods
			const current = data[data.length - 1];
			const previous = data[data.length - 2];
			
			const comparison = {
				"Period": current.period,
				"Current Receipts": current.total_receipts,
				"Previous Receipts": previous.total_receipts,
				"Receipt Change %": ((current.total_receipts - previous.total_receipts) / previous.total_receipts * 100).toFixed(2),
				"Current Payments": current.total_payments,
				"Previous Payments": previous.total_payments,
				"Payment Change %": ((current.total_payments - previous.total_payments) / previous.total_payments * 100).toFixed(2),
				"Current Net Flow": current.net_cash_flow,
				"Previous Net Flow": previous.net_cash_flow,
				"Net Flow Change %": ((current.net_cash_flow - previous.net_cash_flow) / previous.net_cash_flow * 100).toFixed(2)
			};
			
			let html = '<table class="table table-bordered"><tbody>';
			Object.keys(comparison).forEach(key => {
				html += `<tr><th>${key}</th><td>${comparison[key]}</td></tr>`;
			});
			html += '</tbody></table>';
			
			frappe.msgprint({
				title: __("Period Comparison"),
				message: html,
				wide: true
			});
		}
		
		function generate_cash_flow_statement(filters) {
			frappe.call({
				method: "kgk_customisations.kgk_customisations.report.cash_flow_analysis.cash_flow_analysis.generate_statement",
				args: {
					filters: filters
				},
				callback: function(r) {
					if (r.message) {
						const statement = r.message;
						let html = '<div style="font-family: monospace; white-space: pre-wrap;">';
						html += statement;
						html += '</div>';
						
						frappe.msgprint({
							title: __("Cash Flow Statement"),
							message: html,
							wide: true
						});
					}
				}
			});
		}
	}
};
