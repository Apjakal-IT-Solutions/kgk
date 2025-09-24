// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Parcel Import", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Parcel Import', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button('Process Import', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel_import.parcel_import.process_parcel_import",
                    args: { docname: frm.doc.name },
                    callback: function(r) {
                        frappe.msgprint(r.message);
                        frm.reload_doc();
                    }
                });
            });
        }
    }
});
