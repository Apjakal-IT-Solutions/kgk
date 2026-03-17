// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

function calculate_totals(frm) {
	let total_basic = 0;
	let total_accountant = 0;
	(frm.doc.balances_table || []).forEach(row => {
		total_basic += row.basic || 0;
		total_accountant += row.accountant || 0;
	});
	frm.set_value('basic', total_basic);
	frm.set_value('accountant', total_accountant);
}

frappe.ui.form.on('Cash Balance', {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.set_intro(
				`Balance Type: <b>${frm.doc.balance_type}</b> | Company/Account: <b>${frm.doc.company}</b>`,
				'blue'
			);
		}
	},
	balances_table_remove(frm) {
		calculate_totals(frm);
	},
});

frappe.ui.form.on('Cash Balance Item', {
	basic(frm) {
		calculate_totals(frm);
	},
	accountant(frm) {
		calculate_totals(frm);
	},
});
