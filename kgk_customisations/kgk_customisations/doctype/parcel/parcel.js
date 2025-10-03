// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Parcel", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Parcel', {
    refresh: function(frm) {
        if (frm.doc.import_file) {
            // Inspect Excel columns
            // frm.add_custom_button('Inspect Excel Columns', function() {
            //     frappe.call({
            //         method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.inspect_excel_file",
            //         args: {
            //             file_url: frm.doc.import_file
            //         },
            //         callback: function(r) {
            //             if (r.message && !r.message.error) {
            //                 console.log("Excel Column Analysis:", r.message);
                            
            //                 // Safe array handling with fallback to empty arrays
            //                 const e_cols = (r.message.e_columns || []).join(', ') || 'None found';
            //                 const l_cols = (r.message.l_columns || []).join(', ') || 'None found';
            //                 const ig_cols = (r.message.ig_columns || []).join(', ') || 'None found';
            //                 const esp_cols = (r.message.esp_columns || []).join(', ') || 'None found';
            //                 const all_cols = (r.message.column_names || []).join(', ') || 'None found';
                            
            //                 let msg = `<h4>Excel File Analysis</h4>
            //                           <p><strong>Total Rows:</strong> ${r.message.total_rows || 0}</p>
            //                           <p><strong>Total Columns:</strong> ${r.message.total_columns || 0}</p>
            //                           <p><strong>Name Column:</strong> ${r.message.name_column || 'Not detected'}</p>
            //                           <hr>
            //                           <p><strong>E Columns (${(r.message.e_columns || []).length}):</strong> ${e_cols}</p>
            //                           <p><strong>L Columns (${(r.message.l_columns || []).length}):</strong> ${l_cols}</p>
            //                           <p><strong>IG Columns (${(r.message.ig_columns || []).length}):</strong> ${ig_cols}</p>
            //                           <p><strong>ESP Columns (${(r.message.esp_columns || []).length}):</strong> ${esp_cols}</p>
            //                           <hr>
            //                           <p><strong>All Columns:</strong></p>
            //                           <div style="max-height: 200px; overflow-y: scroll; font-size: 11px;">
            //                           ${all_cols}
            //                           </div>`;
            //                 frappe.msgprint(msg, 'Column Analysis');
            //             } else if (r.message && r.message.error) {
            //                 frappe.msgprint(`Error: ${r.message.error}`, 'Column Analysis Error');
            //             } else {
            //                 frappe.msgprint('Unexpected response format', 'Error');
            //             }
            //         }
            //     });
            // });
            
                       
            // Synchronous import with progress bar (for testing/small files)
            // frm.add_custom_button('Import Stones (small file)', function() {
            //     frappe.call({
            //         method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file",
            //         args: {
            //             parcel_name: frm.doc.parcel_name,
            //             file_url: frm.doc.import_file
            //         },
            //         freeze: true,
            //         freeze_message: "Importing stones...",
            //         callback: function(r) {
            //             if (r.message) {
            //                 frappe.show_alert({
            //                     message: r.message,
            //                     indicator: 'green'
            //                 });
            //                 frm.reload_doc();
            //             }
            //         }
            //     });
            // });
            
            // Asynchronous import (for large files)
            frm.add_custom_button('Import Stones', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file_async",
                    args: {
                        parcel_name: frm.doc.parcel_name,
                        file_url: frm.doc.import_file
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === "queued") {
                            frappe.show_alert("Import queued. Check Background Jobs for progress.");                            
                        }
                    }
                });
            });
        }
    }
});


