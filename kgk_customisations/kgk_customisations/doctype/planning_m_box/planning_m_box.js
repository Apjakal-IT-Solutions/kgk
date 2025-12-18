// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Planning M-Box Item", {
	factory_code: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.factory_code) {
			// Search for Employee Target record by factory_code
			frappe.db.get_list("Employee Target", {
				filters: {
					factory_code: row.factory_code,
					active: 1
				},
				fields: ["name", "employee_name"]
			}).then(records => {
				if (records && records.length > 0) {
					// Employee Target found, populate employee_name
					let target_record = records[0];
					frappe.model.set_value(cdt, cdn, "employee_name", target_record.employee_name || "");
				} else {
					// No Employee Target found, clear employee_name
					frappe.model.set_value(cdt, cdn, "employee_name", "");
					frappe.msgprint(__("No active Employee Target found for factory code: {0}", [row.factory_code]));
				}
			});
		}
	}
});
