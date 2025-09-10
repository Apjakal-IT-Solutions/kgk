frappe.query_reports["OCR Data Consolidated"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"width": "80px"
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"width": "80px"
		},
		{
			"fieldname": "upload_id",
			"label": __("Up to Upload ID"),
			"fieldtype": "Link",
			"options": "OCR Data Upload",
			"width": "150px",
			"description": "Show cumulative data up to this upload"
		},
		{
			"fieldname": "lot_id",
			"label": __("Lot ID"),
			"fieldtype": "Data",
			"width": "100px"
		},
		{
			"fieldname": "status",
			"label": __("Upload Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nUploaded\nProcessed\nError",
			"width": "100px"
		},
		{
			"fieldname": "result_processed",
			"label": __("Result (Processed)"),
			"fieldtype": "Data",
			"width": "100px"
		},
		{
			"fieldname": "color_processed",
			"label": __("Color (Processed)"),
			"fieldtype": "Data",
			"width": "100px"
		}
	],
	
	"onload": function(report) {
		// Handle route options for filtering
		if (frappe.route_options) {
			Object.keys(frappe.route_options).forEach(key => {
				if (report.get_filter(key)) {
					report.set_filter_value(key, frappe.route_options[key]);
				}
			});
			// Clear route options after use
			frappe.route_options = null;
			// Refresh the report with new filters
			report.refresh();
		}
		
		// Also handle URL parameters directly
		const urlParams = new URLSearchParams(window.location.search);
		if (urlParams.get('upload_id')) {
			setTimeout(() => {
				if (report.get_filter('upload_id')) {
					report.set_filter_value('upload_id', urlParams.get('upload_id'));
					report.refresh();
				}
			}, 500);
		}
	},
	
	"formatter": function (value, row, column, data, default_formatter) {
		// Highlight summary row
		if (data && data.processing_status === 'SUMMARY') {
			return `<div style="background-color: #f8f9fa; font-weight: bold; padding: 5px;">${value || ''}</div>`;
		}
		
		// Highlight differences between original and processed values
		if (column.fieldname.includes("_processed")) {
			const originalField = column.fieldname.replace("_processed", "_original");
			const originalValue = data[originalField];
			
			if (originalValue !== value && value) {
				return `<span style="background-color: #d4edda; padding: 2px 4px; border-radius: 3px;">${value}</span>`;
			}
		}
		
		// Highlight processed status
		if (column.fieldname === 'processing_status') {
			if (value === 'Processed') {
				return `<span class="indicator green">${value}</span>`;
			} else if (value === 'Original') {
				return `<span class="indicator orange">${value}</span>`;
			} else if (value === 'SUMMARY') {
				return `<span class="indicator blue">${value}</span>`;
			}
		}
		
		return default_formatter(value, row, column, data);
	}
};
