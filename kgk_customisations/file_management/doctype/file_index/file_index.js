frappe.listview_settings['File Index'] = {
    onload: function(listview) {
        listview.page.add_inner_button(__('Open Selected Files'), function() {
            let selected = listview.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__('Please select files to open'));
                return;
            }
            
            selected.forEach(function(item) {
                frappe.call({
                    method: 'kgk_customisations.file_management.Utils.file_opener.open_file_by_path',
                    args: {
                        file_path: item.file_path
                    }
                });
            });
            
            frappe.show_alert({
                message: __('Opening {0} files', [selected.length]),
                indicator: 'green'
            });
        });
        
        listview.page.add_inner_button(__('Validate Existence'), function() {
            frappe.call({
                method: 'kgk_customisations.file_management.Utils.file_operations.validate_indexed_files',
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message.message);
                        listview.refresh();
                    }
                }
            });
        });
    },
    
    get_indicator: function(doc) {
        // Color code by file type
        if (doc.file_type === 'polish_video') {
            return [__('Polish Video'), 'blue', 'file_type,=,polish_video'];
        } else if (doc.file_type === 'rough_video') {
            return [__('Rough Video'), 'orange', 'file_type,=,rough_video'];
        } else if (doc.file_type === 'advisor') {
            return [__('Advisor'), 'green', 'file_type,=,advisor'];
        } else if (doc.file_type === 'scan') {
            return [__('Scan'), 'purple', 'file_type,=,scan'];
        }
    }
};