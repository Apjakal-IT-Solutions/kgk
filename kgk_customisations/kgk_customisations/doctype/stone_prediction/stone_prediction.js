// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stone Prediction", {
	refresh(frm) {
		// Add button to view Stone Prediction Analysis report
		if (frm.doc.parcel_name && frm.doc.predicted_number_of_cuts) {
			frm.add_custom_button(__('View Prediction Analysis'), function() {
				frappe.set_route('query-report', 'Stone Prediction Analysis', {
					serial_number: frm.doc.parcel_name,
					lot_id: frm.doc.predicted_number_of_cuts
				});
			}, __('Reports'));
		}
		
		// Calculate totals on form load
		calculate_totals(frm);
	}
});

// auto set a field value with the user id of the current user
frappe.ui.form.on("Stone Prediction", "onload", function(frm) {
    if (!frm.doc.predicted_by) {
        frm.set_value("predicted_by", frappe.session.user);
    }
    // Calculate totals on load
    calculate_totals(frm);
});

// Calculate totals when child table changes
frappe.ui.form.on("Stone Cuts", {
    predicted_cuts_add: function(frm) {
        calculate_totals(frm);
    },
    predicted_cuts_remove: function(frm) {
        calculate_totals(frm);
    },
    amount: function(frm, cdt, cdn) {
        calculate_totals(frm);
    }
});

// Function to calculate totals
function calculate_totals(frm) {
    let total_amount = 0;
    let number_of_cuts = 0;
    
    if (frm.doc.predicted_cuts) {
        number_of_cuts = frm.doc.predicted_cuts.length;
        
        frm.doc.predicted_cuts.forEach(function(row) {
            if (row.amount) {
                total_amount += flt(row.amount);
            }
        });
    }
    
    frm.set_value('number_of_cuts', number_of_cuts);
    frm.set_value('estimated_value', total_amount);
}
