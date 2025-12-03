// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Balance Submission', {
	refresh: function(frm) {
		// Add custom buttons based on verification status
		if (frm.doc.verification_status === "Draft" || frm.doc.verification_status === "Rejected") {
			frm.add_custom_button(__('Submit Basic Balance'), function() {
				submit_balance(frm, 'basic');
			});
		}
		
		if (frm.doc.verification_status === "Basic Submitted") {
			frm.add_custom_button(__('Verify as Checker'), function() {
				submit_balance(frm, 'checker');
			});
			frm.add_custom_button(__('Reject'), function() {
				reject_submission(frm);
			}, __('Actions'));
		}
		
		if (frm.doc.verification_status === "Checker Verified") {
			frm.add_custom_button(__('Verify as Accountant'), function() {
				submit_balance(frm, 'accountant');
			});
			frm.add_custom_button(__('Reject'), function() {
				reject_submission(frm);
			}, __('Actions'));
		}
		
		// Add indicator for variance
		if (frm.doc.variance_percentage) {
			let color = Math.abs(frm.doc.variance_percentage) > 5 ? 'red' : 'orange';
			frm.dashboard.add_indicator(__('Variance: {0}%', [frm.doc.variance_percentage.toFixed(2)]), color);
		}
		
		// Set field properties based on status
		update_field_permissions(frm);
	},
	
	submission_date: function(frm) {
		// Recalculate when date changes
		frm.call('calculate_calculated_balance');
	},
	
	company: function(frm) {
		// Recalculate when company changes
		frm.call('calculate_calculated_balance');
	}
});

function submit_balance(frm, type) {
	let title = type.charAt(0).toUpperCase() + type.slice(1);
	
	frappe.prompt([
		{
			fieldname: 'balance',
			fieldtype: 'Currency',
			label: __(`${title} Balance`),
			reqd: 1
		},
		{
			fieldname: 'comments',
			fieldtype: 'Small Text',
			label: __('Comments')
		}
	], function(values) {
		frm.call({
			method: `submit_${type}_balance`,
			args: {
				balance: values.balance,
				comments: values.comments
			},
			callback: function(r) {
				frm.reload_doc();
			}
		});
	}, __(`Submit ${title} Balance`));
}

function reject_submission(frm) {
	frappe.prompt([
		{
			fieldname: 'comments',
			fieldtype: 'Small Text',
			label: __('Rejection Reason'),
			reqd: 1
		}
	], function(values) {
		frm.call({
			method: 'reject_submission',
			args: {
				comments: values.comments
			},
			callback: function(r) {
				frm.reload_doc();
			}
		});
	}, __('Reject Submission'));
}

function update_field_permissions(frm) {
	// Make fields read-only based on verification status
	let status = frm.doc.verification_status;
	
	// Basic fields are editable only in Draft/Rejected
	frm.set_df_property('basic_balance', 'read_only', !['Draft', 'Rejected'].includes(status));
	frm.set_df_property('basic_comments', 'read_only', !['Draft', 'Rejected'].includes(status));
	
	// Checker fields are editable only in Basic Submitted
	frm.set_df_property('checker_balance', 'read_only', status !== 'Basic Submitted');
	frm.set_df_property('checker_comments', 'read_only', status !== 'Basic Submitted');
	
	// Accountant fields are editable only in Checker Verified
	frm.set_df_property('accountant_balance', 'read_only', status !== 'Checker Verified');
	frm.set_df_property('accountant_comments', 'read_only', status !== 'Checker Verified');
}
