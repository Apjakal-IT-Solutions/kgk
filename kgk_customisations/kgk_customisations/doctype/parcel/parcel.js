// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Parcel", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Parcel', {
    refresh: function(frm) {
        if (frm.doc.import_file) {
            frm.add_custom_button('Import Stones', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file_async",
                    args: {
                        parcel_name: frm.doc.parcel_name,
                        file_url: frm.doc.import_file
                    },
                    callback: function(r) {
                        if (r.message.status === "queued") {
                            frappe.show_alert("Import queued. Check Background Jobs for progress.");                            
                        }
                    }
                });
            });
        }
    }
});


