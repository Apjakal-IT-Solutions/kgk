// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.listview_settings['OCR Data Upload'] = {
    onload: function(listview) {
        // Listen for background report completion
        frappe.realtime.on('report_ready', function(data) {
            frappe.show_alert({
                message: data.message,
                indicator: 'green'
            });
            
            // Offer to download the completed report
            frappe.confirm(
                __('Your OCR report is ready. Download now?'),
                function() {
                    window.open(data.file_url, '_blank');
                }
            );
        });
        
        frappe.realtime.on('report_error', function(data) {
            frappe.show_alert({
                message: data.message,
                indicator: 'red'
            });
        });
        
        // Add download report button to the list view
        listview.page.add_menu_item(__('Download Cumulative Report'), function() {
            frappe.confirm(
                __('Generate a complete OCR data report?<br><br><strong>Note:</strong><br>• Small datasets (&lt;5,000 records): Immediate download<br>• Large datasets (&gt;5,000 records): Background processing with notification'),
                function() {
                    // Show initial loading message
                    frappe.show_alert({
                        message: __('Checking dataset size and starting report generation...'),
                        indicator: 'blue'
                    });
                    
                    frappe.call({
                        method: 'kgk_customisations.kgk_customisations.doctype.ocr_data_upload.ocr_data_upload.download_cumulative_report',
                        timeout: 60000, // 1 minute timeout for initial request
                        callback: function(r) {
                            if (r.message && r.message.success) {
                                if (r.message.is_background) {
                                    // Background processing
                                    frappe.show_alert({
                                        message: r.message.message + ' You can continue working and will be notified when ready.',
                                        indicator: 'orange'
                                    });
                                    
                                    // Show a toast that stays visible
                                    frappe.show_alert({
                                        message: `Background job started for ${r.message.records_count} records. Check notifications for completion.`,
                                        indicator: 'blue'
                                    }, 10);
                                    
                                } else {
                                    // Immediate download
                                    frappe.show_alert({
                                        message: r.message.message + '. Download should start automatically.',
                                        indicator: 'green'
                                    });
                                    
                                    // File should download automatically via direct response
                                    if (r.message.file_url) {
                                        window.open(r.message.file_url, '_blank');
                                    }
                                }
                            } else {
                                frappe.show_alert({
                                    message: r.message ? r.message.message : 'Error generating report',
                                    indicator: 'red'
                                });
                            }
                        },
                        error: function(r) {
                            let error_msg = 'Error generating report';
                            if (r.responseJSON && r.responseJSON.message) {
                                error_msg += ': ' + r.responseJSON.message;
                            } else if (r.statusText === 'timeout') {
                                error_msg = 'Request timeout. Please try again.';
                            }
                            
                            frappe.show_alert({
                                message: __(error_msg),
                                indicator: 'red'
                            });
                        }
                    });
                }
            );
        });
    }
};
