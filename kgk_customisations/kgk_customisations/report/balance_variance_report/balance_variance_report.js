// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Balance Variance Report"] = {
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
			"fieldname": "currency",
			"label": __("Currency"),
			"fieldtype": "Link",
			"options": "Currency"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select", 
			"options": "\nDraft\nPending Review\nVariance Identified\nReconciled"
		},
		{
			"fieldname": "reconciliation_required",
			"label": __("Reconciliation Required"),
			"fieldtype": "Select",
			"options": "\nYes\nNo"
		},
		{
			"fieldname": "variance_threshold",
			"label": __("Variance Threshold (%)"),
			"fieldtype": "Float",
			"description": "Show only records with variance percentage above this threshold"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "status") {
			var status_colors = {
				"Draft": "#ff9500",
				"Pending Review": "#ff6b35", 
				"Variance Identified": "#ff5858",
				"Reconciled": "#98d982"
			};
			
			if (status_colors[value]) {
				value = `<span style="color: ${status_colors[value]}; font-weight: bold;">${value}</span>`;
			}
		}
		
		if (column.fieldname == "variance_amount") {
			var variance = parseFloat(value) || 0;
			var color = variance == 0 ? "#98d982" : (variance > 0 ? "#ff9500" : "#ff5858");
			value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
		}
		
		if (column.fieldname == "variance_percentage") {
			var percentage = parseFloat(value) || 0;
			var abs_percentage = Math.abs(percentage);
			var color = "#98d982"; // Green for low variance
			
			if (abs_percentage > 10) {
				color = "#ff5858"; // Red for high variance
			} else if (abs_percentage > 5) {
				color = "#ff9500"; // Orange for medium variance
			}
			
			value = `<span style="color: ${color}; font-weight: bold;">${value}%</span>`;
		}
		
		if (column.fieldname == "reconciliation_required") {
			if (value == "1" || value == 1) {
				value = '<span style="color: #ff5858; font-weight: bold;">Yes</span>';
			} else {
				value = '<span style="color: #98d982;">No</span>';
			}
		}
		
		return value;
	}, 

	"onload": function(report) {
        // Force an adjustment after a short delay to ensure rendering is complete
        setTimeout(() => {
            if (report.datatable) {
                window.dispatchEvent(new Event('resize'));
            }
        }, 500);
    }
};
