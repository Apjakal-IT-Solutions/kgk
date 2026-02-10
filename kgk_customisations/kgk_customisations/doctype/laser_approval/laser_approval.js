// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Laser Approval", {
	onload_post_render(frm) {
		// Prepopulate document_users table on new document creation
		if (frm.is_new() && (!frm.doc.document_users || frm.doc.document_users.length === 0)) {
			prepopulate_users(frm);

            // Generate a unique alphanumeric serial number for the new document
            const uniqueSerialNumber = 'LA-' + Math.random().toString(36).substr(2, 9).toUpperCase();
            frm.set_value('serial_number', uniqueSerialNumber);
		}
	},
	
	refresh(frm) {
		// Add button to manually repopulate users if needed
		if (!frm.is_new()) {
			frm.add_custom_button(__('Refresh User List'), function() {
				frappe.confirm(
					'This will replace the current user list with all users from Laser Approval User Item. Continue?',
					function() {
						prepopulate_users(frm, true);
					}
				);
			}, __('Actions'));
		}
	},

    org_plan_value: function(frm) {
        if(frm.doc.org_plan_value && frm.doc.revised_value){
            frm.set_value("safe_sawing_amount", (frm.doc.org_plan_value - frm.doc.revised_value));
        }
    },

    revised_value: function(frm) {
        if(frm.doc.org_plan_value && frm.doc.revised_value){
            frm.set_value("safe_sawing_amount", (frm.doc.org_plan_value - frm.doc.revised_value));
        }
    }, 

    micron_safe: function(frm) {
        if(frm.doc.micron_safe && (frm.doc.micron_safe < 20 || frm.doc.micron_safe > 1000)){
            frappe.msgprint(__('Micron Safe value must be between 20 and 1000'));
            frm.set_value('micron_safe', null);
        }
    }, 

    safe_sawing_amount: function(frm) {
        if(frm.doc.safe_sawing_amount && frm.doc.org_plan_value && frm.doc.org_plan_value > 0){
            frm.set_value("safe_sawing_percent", (frm.doc.safe_sawing_amount / frm.doc.org_plan_value) * 100);
        }
    }
});

function prepopulate_users(frm, clear_existing = false) {
	// Fetch all users from Laser Approval User Item
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Laser Approval User Item',
			fields: ['name', 'full_name'],
			order_by: 'full_name asc',
			limit_page_length: 0  // Get all records
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				if (clear_existing) {
					// Clear existing rows
					frm.clear_table('document_users');
				}
				
				// Add each user to the child table
				r.message.forEach(function(user) {
					let row = frm.add_child('document_users');
					row.employee_name = user.name;
					row.status = 'No';  // Default status
				});
				
				frm.refresh_field('document_users');
				frappe.show_alert({
					message: __('Added {0} users to the list', [r.message.length]),
					indicator: 'green'
				}, 5);
			} else {
				frappe.msgprint(__('No users found in Laser Approval User Item'));
			}
		}
	});
}
