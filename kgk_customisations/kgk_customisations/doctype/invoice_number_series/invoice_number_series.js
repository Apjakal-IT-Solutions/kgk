// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Number Series', {
	refresh: function(frm) {
		// Add button to preview next number
		if (!frm.is_new()) {
			frm.add_custom_button(__('Preview Next Number'), function() {
				preview_next_number(frm);
			});
			
			// Add button to reset series
			if (frappe.user.has_role(['Cash Super User', 'Administrator'])) {
				frm.add_custom_button(__('Reset Series'), function() {
					reset_series(frm);
				}, __('Actions'));
			}
		}
		
		// Set indicator based on active status
		if (frm.doc.is_active) {
			frm.set_indicator_formatter('is_active', function(doc) {
				return (doc.is_active) ? 'green' : 'red';
			});
		}
	},
	
	document_type: function(frm) {
		// Auto-suggest prefix when document type is selected
		if (frm.doc.document_type && !frm.doc.prefix) {
			let prefix_map = {
				'Payment': 'PAY',
				'Receipt': 'REC',
				'Invoice': 'INV',
				'Credit Note': 'CN',
				'Debit Note': 'DN',
				'Journal Entry': 'JE',
				'Petty Cash': 'PC'
			};
			let suggested_prefix = prefix_map[frm.doc.document_type] || 'DOC';
			frm.set_value('prefix', suggested_prefix);
		}
	},
	
	year_based: function(frm) {
		// Show/hide reset_on_year_change based on year_based
		frm.toggle_display('reset_on_year_change', frm.doc.year_based);
		if (!frm.doc.year_based) {
			frm.set_value('reset_on_year_change', 0);
		}
	}
});

function preview_next_number(frm) {
	// Preview what the next generated number will be
	let year = new Date().getFullYear();
	let next_num = frm.doc.current_number;
	let padded_num = String(next_num).padStart(frm.doc.padding, '0');
	
	let preview;
	if (frm.doc.year_based) {
		preview = `${frm.doc.prefix}-${year}-${padded_num}`;
	} else {
		preview = `${frm.doc.prefix}-${padded_num}`;
	}
	
	frappe.msgprint({
		title: __('Next Invoice Number Preview'),
		message: `The next generated invoice number will be: <strong>${preview}</strong>`,
		indicator: 'blue'
	});
}

function reset_series(frm) {
	// Reset the series counter to 1
	frappe.confirm(
		'Are you sure you want to reset this series to 1? This action cannot be undone.',
		function() {
			frm.set_value('current_number', 1);
			frm.save();
			frappe.show_alert({
				message: __('Series has been reset to 1'),
				indicator: 'green'
			}, 5);
		}
	);
}
