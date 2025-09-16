// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Document Report"] = {
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
			"fieldname": "transaction_type",
			"label": __("Transaction Type"),
			"fieldtype": "Select",
			"options": "\nPayment\nReceipt"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select", 
			"options": "\nDraft\nPending Review\nApproved\nRejected\nProcessed"
		},
		{
			"fieldname": "party_type",
			"label": __("Party Type"),
			"fieldtype": "Select",
			"options": "\nCustomer\nSupplier\nEmployee\nOther"
		},
		{
			"fieldname": "party",
			"label": __("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type"
		},
		{
			"fieldname": "currency",
			"label": __("Currency"),
			"fieldtype": "Link",
			"options": "Currency"
		},
		{
			"fieldname": "created_by",
			"label": __("Created By"),
			"fieldtype": "Link",
			"options": "User"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "status") {
			var status_colors = {
				"Draft": "#ff9500",
				"Pending Review": "#ff6b35", 
				"Approved": "#98d982",
				"Rejected": "#ff5858",
				"Processed": "#5e64ff"
			};
			
			if (status_colors[value]) {
				value = `<span style="color: ${status_colors[value]}; font-weight: bold;">${value}</span>`;
			}
		}
		
		if (column.fieldname == "transaction_type") {
			var type_colors = {
				"Payment": "#ff6b6b",
				"Receipt": "#51cf66"
			};
			
			if (type_colors[value]) {
				value = `<span style="color: ${type_colors[value]}; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	}
};