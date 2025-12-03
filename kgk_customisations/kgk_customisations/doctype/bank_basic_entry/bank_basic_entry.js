// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Basic Entry', {
	refresh: function(frm) {
		// Add verify button if not verified
		if (!frm.doc.verified && !frm.is_new()) {
			frm.add_custom_button(__('Verify Entry'), function() {
				frm.call({
					method: 'verify_entry',
					callback: function(r) {
						frm.reload_doc();
					}
				});
			});
		}
		
		// Add unverify button if verified (for authorized users)
		if (frm.doc.verified && frappe.user_roles.includes('System Manager')) {
			frm.add_custom_button(__('Unverify'), function() {
				frappe.confirm(
					'Are you sure you want to unverify this entry?',
					function() {
						frm.call({
							method: 'unverify_entry',
							callback: function(r) {
								frm.reload_doc();
							}
						});
					}
				);
			}, __('Actions'));
		}
		
		// Add indicator for verification status
		if (frm.doc.verified) {
			frm.dashboard.add_indicator(__('Verified'), 'green');
		} else {
			frm.dashboard.add_indicator(__('Not Verified'), 'orange');
		}
	},
	
	company: function(frm) {
		// Auto-populate company abbreviation in username if empty
		if (frm.doc.company && !frm.doc.username) {
			frappe.db.get_value('Company', frm.doc.company, 'abbr', function(r) {
				if (r && r.abbr) {
					frm.set_value('username', frappe.session.user_email.split('@')[0] + '_' + r.abbr);
				}
			});
		}
	}
});
