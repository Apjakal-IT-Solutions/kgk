// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Stone Prediction", {
// 	refresh(frm) {

// 	},
// });

// auto set a field value with the user id of the current user
frappe.ui.form.on("Stone Prediction", "onload", function(frm) {
    if (!frm.doc.predicted_by) {
        frm.set_value("predicted_by", frappe.session.user);
        }
    });

// validate number of child table entries against a field value before saving
frappe.ui.form.on("Stone Prediction", "validate", function(frm) {
    let expected_count = frm.doc.predicted_number_of_cuts || 0;
    let actual_count = frm.doc.predicted_cuts.length
    if (expected_count !== actual_count) {
        frappe.msgprint(`The number of predicted cuts (${actual_count}) does not match the expected number (${expected_count}). Please adjust accordingly.`);
        frappe.validated = false; // Prevent form from being saved
    }
});
