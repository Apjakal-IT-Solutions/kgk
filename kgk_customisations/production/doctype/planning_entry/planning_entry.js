// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Planning Entry Item", {	
	employee: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.employee) {
			// Search for Employee Target record by employee
			frappe.db.get_list("Employee Target", {
				filters: {
					employee: row.employee,
					active: 1
				},
				fields: ["name", "target", "factory_process", "employee_name"]
			}).then(records => {
				if (records && records.length > 0) {
					// Employee Target found, populate the fields
					let target_record = records[0];
					frappe.model.set_value(cdt, cdn, "target", target_record.target || "");
					frappe.model.set_value(cdt, cdn, "factory_process", target_record.factory_process || "");
					frappe.model.set_value(cdt, cdn, "employee_name", target_record.employee_name || "");
				} else {
					// No Employee Target found, offer to create one
					frappe.confirm(
						`No Employee Target record found for this employee. Would you like to create one?`,
						() => {
							// Create new Employee Target
							frappe.new_doc("Employee Target", {
								employee: row.employee
							});
						}
					);
				}
			});
		}
	},
	employee_code: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.employee_code) {
			// Search for Employee Target record by employee code
			frappe.db.get_list("Employee Target", {
				filters: {
					factory_code: row.employee_code,
					active: 1
				},
				fields: ["name", "target", "factory_process", "employee"]
			}).then(records => {
				if (records && records.length > 0) {
					// Employee Target found, populate the fields
					let target_record = records[0];
					frappe.model.set_value(cdt, cdn, "target", target_record.target || "");
					frappe.model.set_value(cdt, cdn, "factory_process", target_record.factory_process || "");
					frappe.model.set_value(cdt, cdn, "employee", target_record.employee || "");
				} else {
					// No Employee Target found, offer to create one
					frappe.confirm(
						`No Employee Target record found for this employee code. Would you like to create one?`,
						() => {
							// Create new Employee Target
							frappe.new_doc("Employee Target", {
								employee_code: row.employee_code
							});
						}
					);
				}
			});
		}
	}
});