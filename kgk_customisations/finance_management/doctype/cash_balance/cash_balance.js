// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Balance', {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.set_intro(
				`Balance Type: <b>${frm.doc.balance_type}</b> | Company/Account: <b>${frm.doc.company}</b>`,
				'blue'
			);
		}
	},
});
