// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Laser Stock Position", {
	refresh(frm) {
		// Calculate PCS total on form refresh
		calculate_pcs_total(frm);
	},
	
	validate(frm) {
		// Ensure PCS total is calculated before saving
		calculate_pcs_total(frm);
	}
});

frappe.ui.form.on("Laser Stock Position Item", {
	pcs: function(frm) {
		// Recalculate PCS total when PCS value changes
		calculate_pcs_total(frm);
	},
	
	laser_stock_item_table_add: function(frm) {
		// Recalculate when new row is added
		calculate_pcs_total(frm);
	},
	
	laser_stock_item_table_remove: function(frm) {
		// Recalculate when row is removed
		calculate_pcs_total(frm);
	}
});

function calculate_pcs_total(frm) {
	let total_pcs = 0;
	
	// Loop through child table and sum up PCS values
	if (frm.doc.laser_stock_item_table) {
		frm.doc.laser_stock_item_table.forEach(function(row) {
			if (row.pcs && !isNaN(row.pcs)) {
				total_pcs += parseInt(row.pcs) || 0;
			}
		});
	}
	
	// Set the calculated total in the PCS Total field
	frm.set_value('pcs_total', total_pcs);
}
