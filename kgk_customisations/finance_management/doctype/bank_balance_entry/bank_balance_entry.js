// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Balance Entry', {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.set_intro(
				`Date: <b>${frm.doc.date}</b> | Account: <b>${frm.doc.company}</b> | User: <b>${frm.doc.username}</b>`,
				'blue'
			);
		}
	},

	onload(frm) {
		// Auto-populate username with current user on new records
		if (frm.is_new() && !frm.doc.username) {
			frm.set_value('username', frappe.session.user);
		}
	},
});
