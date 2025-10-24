frappe.ui.form.on('Parcel', {
    refresh: function(frm) {
        if (frm.doc.import_file) {
            // Main Import button (only custom button)
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
            
            // File Analysis menu item
            frm.page.add_menu_item('Analyze File', function() {
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
            
            // Pre-import validation menu item
            frm.page.add_menu_item('Validate File Before Import', function() {
                frappe.call({
                    method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.validate_excel_before_import",
                    args: {
                        file_url: frm.doc.import_file
                    },
                    freeze: true,
                    freeze_message: "Validating Excel file...",
                    callback: function(r) {
                        if (r.message.error) {
                            frappe.msgprint(`Validation Error: ${r.message.error}`);
                        } else {
                            let report = r.message;
                            let status = report.stones_without_barcode === 0 ? 'green' : 'orange';
                            let msg = `<strong>File Validation Report:</strong><br>
                                Total Rows: ${report.total_rows}<br>
                                Stones with Barcode: ${report.stones_with_barcode}<br>
                                Stones without Barcode: ${report.stones_without_barcode}<br>
                                Barcode Format Issues: ${report.barcode_format_issues.length}<br>
                                Barcode Column Found: ${report.column_analysis.barcode_column_found ? 'Yes' : 'No'}<br>
                                Main Barcode Column Found: ${report.column_analysis.main_barcode_column_found ? 'Yes' : 'No'}`;
                            
                            if (report.missing_barcode_stones.length > 0 && report.missing_barcode_stones.length <= 10) {
                                msg += `<br><br><strong>Stones without Barcode:</strong><br>${report.missing_barcode_stones.join(', ')}`;
                            } else if (report.missing_barcode_stones.length > 10) {
                                msg += `<br><br><strong>First 10 Stones without Barcode:</strong><br>${report.missing_barcode_stones.slice(0, 10).join(', ')}...`;
                            }
                            
                            frappe.msgprint({
                                title: 'Validation Report',
                                message: msg,
                                indicator: status
                            });
                        }
                    }
                });
            });
        }
        
        // Barcode recovery menu item
        frm.page.add_menu_item('Recover Missing Barcodes', function() {
            if (!frm.doc.import_file) {
                frappe.msgprint('Please attach the original Excel file first to enable barcode recovery.');
                return;
            }
            
            frappe.confirm(
                'This will attempt to recover missing barcodes by re-reading the original Excel file. Continue?',
                function() {
                    frappe.call({
                        method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.recover_missing_barcodes",
                        args: {
                            parcel_name: frm.doc.name,
                            file_url: frm.doc.import_file
                        },
                        freeze: true,
                        freeze_message: "Recovering missing barcodes...",
                        callback: function(r) {
                            if (r.message && r.message.status === "success") {
                                let msg = `<strong>Barcode Recovery Complete:</strong><br>
                                    ${r.message.message}<br><br>
                                    <strong>Details:</strong><br>
                                    Total Missing: ${r.message.total_missing}<br>
                                    Recovered: ${r.message.recovered}<br>
                                    Not Found in Excel: ${r.message.not_found}<br>
                                    Errors: ${r.message.errors}`;
                                
                                frappe.msgprint({
                                    title: 'Recovery Results',
                                    message: msg,
                                    indicator: r.message.recovered > 0 ? 'green' : 'orange'
                                });
                                
                                if (r.message.recovered > 0) {
                                    frm.reload_doc();
                                }
                            }
                        }
                    });
                }
            );
        });
        
        // Fix barcodes & child tables menu item
        frm.page.add_menu_item('Fix Barcodes & Child Tables', function() {
            frappe.confirm(
                'This will backfill missing barcodes AND populate child stone tables. Continue?',
                function() {
                    frappe.call({
                        method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.backfill_missing_main_barcodes",
                        args: {
                            parcel_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: "Fixing barcodes and populating child tables...",
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
        
        // Rebuild child tables menu item
        frm.page.add_menu_item('Rebuild Child Tables', function() {
            frappe.call({
                method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.populate_child_stones_async",
                args: {
                    parcel_name: frm.doc.name
                },
                freeze: true,
                freeze_message: "Rebuilding child stone tables...",
                callback: function(r) {
                    if (r.message && r.message.status === "success") {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });
                    }
                }
            });
        });
        
        // Clear stones data menu item (for testing/re-import)
        frm.page.add_menu_item('Clear All Stones Data', function() {
            frappe.confirm(
                `<strong>WARNING: This will permanently delete ALL stones data for this parcel!</strong><br><br>
                This action cannot be undone. Are you sure you want to proceed?<br><br>
                This is typically used for testing or before re-importing data.`,
                function() {
                    frappe.call({
                        method: "kgk_customisations.kgk_customisations.doctype.parcel.parcel.clear_stones_data",
                        args: {
                            parcel_name: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: "Clearing stones data...",
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
                },
                'Yes, Delete All Stones'
            );
        });
    }
});