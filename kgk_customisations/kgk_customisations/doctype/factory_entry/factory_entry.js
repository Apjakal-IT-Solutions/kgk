// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Factory Entry", {
	refresh(frm) {
		// get employees from employee targets based on selected section
		if (frm.doc.section) {
			frappe.db.get_list("Employee Target", {
				filters: {
					section: frm.doc.section
				},
				fields: ["employee"]
			}).then(records => {
				if (records && records.length > 0) {
					// Populate child table with employees
					records.forEach(record => {
						let child = frm.add_child("factory_entry_item_table");
						child.employee = record.employee;
					});
					frm.refresh_field("factory_entry_item_table");
				}
			});
		}
	},
	
	section: function(frm) {
		// Clear child table when section changes
		frm.clear_table("factory_entry_item_table");
		frm.refresh_field("factory_entry_item_table");
	}
});

frappe.ui.form.on("Factory Entry Item", {
	employee: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.employee) {
			// Search for Employee Target record by employee
			frappe.db.get_list("Employee Target", {
				filters: {
					employee: row.employee
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
	}
});


