frappe.ui.form.on('Parcel', {
    refresh: function(frm) {
        if (frm.doc.import_file) {
            // Analyze file button
            frm.add_custom_button('Analyze File', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.inspect_excel_file",
                    args: {
                        file_url: frm.doc.import_file
                    },
                    callback: function(r) {
                        if (r.message.error) {
                            frappe.msgprint(`Analysis Error: ${r.message.error}`);
                        } else {
                            let info = r.message;
                            let msg = `<strong>File Analysis:</strong><br>
                                Total Rows: ${info.total_rows}<br>
                                Total Columns: ${info.total_columns}<br>
                                Stone Name Column: ${info.stone_name_column}<br>
                                Recognized Columns: ${info.recognized_columns.length}<br>
                                Unrecognized Columns: ${info.unrecognized_columns.length}<br>
                                Sample Stones: ${info.sample_stones.slice(0, 5).join(', ')}`;
                            
                            frappe.msgprint({
                                title: 'File Analysis',
                                message: msg,
                                indicator: 'blue'
                            });
                        }
                    }
                });
            });
            
            // Import stones (sync) button
            frm.add_custom_button('Import Stones (Quick)', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file",
                    args: {
                        parcel_name: frm.doc.name,
                        file_url: frm.doc.import_file
                    },
                    freeze: true,
                    freeze_message: "Importing stones...",
                    callback: function(r) {
                        if (r.message && r.message.status === "success") {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        }
                    }
                });
            });
            
            // Import stones (async) button
            frm.add_custom_button('Import Stones (Background)', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file_async",
                    args: {
                        parcel_name: frm.doc.name,
                        file_url: frm.doc.import_file
                    },
                    callback: function(r) {
                        if (r.message.status === "queued") {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'blue'
                            });
                        }
                    }
                });
            });
        }
        
        // Backfill missing barcodes button (always available)
        frm.add_custom_button('Fix Missing Barcodes', function() {
            frappe.confirm(
                'This will backfill missing main_barcodes from parent/sibling stones. Continue?',
                function() {
                    frappe.call({
                        method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.backfill_missing_main_barcodes",
                        args: {
                            parcel_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: "Fixing barcodes...",
                        callback: function(r) {
                            if (r.message && r.message.status === "success") {
                                frappe.show_alert({
                                    message: r.message.message,
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                }
            );
        });
    }
});