frappe.ui.form.on('File Search Dashboard', {
    refresh: function(frm) {
        // Add Search button
        frm.add_custom_button(__('Search Files'), function() {
            if (!frm.doc.lot_number) {
                frappe.msgprint(__('Please enter a Lot Number'));
                return;
            }
            
            frappe.call({
                method: 'kgk_customisations.file_management.Utils.file_operations.search_all_files',
                args: {
                    lot_number: frm.doc.lot_number,
                    use_cache: 0
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table('last_search_results');
                        
                        // Add polish video
                        if (r.message.polish_video) {
                            frm.add_child('last_search_results', {
                                file_type: 'Polish Video',
                                file_name: r.message.polish_video.file_name,
                                file_path: r.message.polish_video.file_path,
                                file_size: r.message.polish_video.file_size,
                                exists: 1
                            });
                        }
                        
                        // Add rough video
                        if (r.message.rough_video) {
                            frm.add_child('last_search_results', {
                                file_type: 'Rough Video',
                                file_name: r.message.rough_video.file_name,
                                file_path: r.message.rough_video.file_path,
                                file_size: r.message.rough_video.file_size,
                                exists: 1
                            });
                        }
                        
                        // Add advisor files
                        (r.message.advisor_files || []).forEach(function(file) {
                            frm.add_child('last_search_results', {
                                file_type: 'Advisor',
                                file_name: file.file_name,
                                file_path: file.file_path,
                                file_size: file.file_size,
                                exists: 1
                            });
                        });
                        
                        // Add scan files
                        (r.message.scan_files || []).forEach(function(file) {
                            frm.add_child('last_search_results', {
                                file_type: 'Scan',
                                file_name: file.file_name,
                                file_path: file.file_path,
                                file_size: file.file_size,
                                exists: 1
                            });
                        });
                        
                        frm.refresh_field('last_search_results');
                        frappe.show_alert({message: __('Search completed'), indicator: 'green'});
                    }
                }
            });
        }, __('Actions'));
        
        // Add Open All Files button
        frm.add_custom_button(__('Open All Files'), function() {
            if (!frm.doc.lot_number) {
                frappe.msgprint(__('Please enter a Lot Number'));
                return;
            }
            
            frappe.confirm(
                __('Open all files for lot {0}?', [frm.doc.lot_number]),
                function() {
                    frappe.call({
                        method: 'kgk_customisations.file_management.Utils.file_opener.open_lot_files',
                        args: {
                            lot_number: frm.doc.lot_number
                        },
                        callback: function(r) {
                            if (r.message) {
                                frappe.msgprint(__('Opened {0} files', [r.message.opened]));
                            }
                        }
                    });
                }
            );
        }, __('Actions'));
        
        // Load statistics
        frm.call('load_statistics');
    },
    
    load_statistics: function(frm) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'File Index',
                fields: ['file_type', 'count(*) as count'],
                group_by: 'file_type'
            },
            callback: function(r) {
                if (r.message) {
                    let total = 0;
                    r.message.forEach(function(row) {
                        total += row.count;
                        if (row.file_type === 'polish_video') {
                            frm.set_value('polish_count', row.count);
                        } else if (row.file_type === 'rough_video') {
                            frm.set_value('rough_count', row.count);
                        } else if (row.file_type === 'advisor') {
                            frm.set_value('advisor_count', row.count);
                        } else if (row.file_type === 'scan') {
                            frm.set_value('scan_count', row.count);
                        }
                    });
                    frm.set_value('total_files', total);
                }
            }
        });
    }
});