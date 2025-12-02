// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["F.M Process Performance Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date", 
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"reqd": 1
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Section"
		},
		{
			"fieldname": "factory_process",
			"label": __("Factory Process"),
			"fieldtype": "Link",
			"options": "Factory Process"
		},
		{
			"fieldname": "day_type",
			"label": __("Day Type"),
			"fieldtype": "Select",
			"options": "All\nNormal\nWeekend",
			"default": "All"
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color formatting for difference values
		if (column.fieldname === "diff" || column.fieldname === "diff_percentage") {
			if (flt(data[column.fieldname]) < 0) {
				value = `<span style="color: #d73527; font-weight: bold;">${value}</span>`;
			} else if (flt(data[column.fieldname]) > 0) {
				value = `<span style="color: #5cb85c; font-weight: bold;">${value}</span>`;
			}
		}
		
		// Highlight factory process names
		if (column.fieldname === "factory_process") {
			value = `<strong>${value}</strong>`;
		}
		
		return value;
	},
	"onload": function(report) {
		// Add custom CSS for better visualization
		if (!$('#process-performance-styles').length) {
			$('<style id="process-performance-styles">')
				.text(`
					.dt-row .dt-cell[data-col-index="1"],
					.dt-row .dt-cell[data-col-index="2"],
					.dt-row .dt-cell[data-col-index="3"] {
						text-align: right;
					}
					.negative-diff {
						background-color: #ffe6e6 !important;
					}
					.positive-diff {
						background-color: #e6ffe6 !important;
					}
				`)
				.appendTo('head');
		}
		
		// Auto-refresh functionality for real-time updates
		setInterval(function() {
			if (report.page.current_route && report.page.current_route[0] === 'query-report' 
				&& report.page.current_route[1] === 'F.M Process Performance Report') {
				report.refresh();
			}
		}, 300000); // 5 minutes
	},
	"get_datatable_options": function(options) {
		return Object.assign(options, {
			checkboxColumn: false,
			layout: 'fluid',
			rowHeight: 30,
			headerHeight: 35,
			cellHeight: 30,
			getRowClass: function(row) {
				if (row && row[3] < 0) { // diff column
					return 'negative-diff';
				} else if (row && row[3] > 0) {
					return 'positive-diff';
				}
				return '';
			}
		});
	}
};

frappe.query_reports["F.M Process Performance Report"] = {
	"filters": [

	]
};
