// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.listview_settings['OCR Data Upload'] = {
    onload: function(listview) {
        // Add download report button to the list view using correct method
        listview.page.add_menu_item(__('Download Cumulative Report'), function() {
            frappe.show_alert({
                message: __('Generating cumulative report...'),
                indicator: 'blue'
            });
            
            frappe.call({
                method: 'kgk_customisations.kgk_customisations.doctype.ocr_data_upload.ocr_data_upload.download_cumulative_report',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        });
                        
                        // If file_url is provided, open it for download
                        if (r.message.file_url) {
                            window.open(r.message.file_url, '_blank');
                        }
                    } else {
                        frappe.show_alert({
                            message: r.message ? r.message.message : 'Error generating report',
                            indicator: 'red'
                        });
                    }
                },
                error: function() {
                    frappe.show_alert({
                        message: __('Error generating report'),
                        indicator: 'red'
                    });
                }
            });
        });
    }
};
