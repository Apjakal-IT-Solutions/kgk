// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Document Sub Type', {
	refresh: function(frm) {
		// Set filter to show only active sub types in lists
		if (!frm.is_new()) {
			frm.set_indicator_formatter('is_active', function(doc) {
				return (doc.is_active) ? 'green' : 'red';
			});
		}
	},
	
	main_document_type: function(frm) {
		// Clear code when main document type changes
		if (frm.doc.main_document_type) {
			frm.set_value('code', '');
		}
	}
});
