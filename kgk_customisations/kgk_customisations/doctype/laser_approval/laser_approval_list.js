// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.listview_settings['Laser Approval'] = {
    add_fields: ['checked_'],  // Ensure checked_ field is fetched
    
    get_indicator: function(doc) {
        // Check if document has been checked by an approver
        if (doc.checked_ == 1 || doc.checked_ === true) {
            return [__('Approved'), 'green', 'checked_,=,1'];
        } else {
            return [__('Pending'), 'orange', 'checked_,=,0'];
        }
    },
    
};
