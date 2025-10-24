// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Planning Entry", {
	refresh(frm) {
		// Any parent form logic can be added here if needed
	}
});

frappe.ui.form.on("Planning Entry Item", {
	employee: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.employee) {
			// Search for Employee Target record by employee
			frappe.db.get_list("Employee Target", {
				filters: {
					employee: row.employee
				},
				fields: ["name", "target", "employee_name"]
			}).then(records => {
				if (records && records.length > 0) {
					// Employee Target found, populate the target field
					let target_record = records[0];
					frappe.model.set_value(cdt, cdn, "target", target_record.target || 0);
					
					frappe.show_alert({
						message: `Target loaded: ${target_record.target || 0} for ${target_record.employee_name || row.employee}`,
						indicator: 'green'
					});
				} else {
					// No Employee Target found, offer to create one
					frappe.confirm(
						`No Employee Target record found for this employee. Would you like to create one?`,
						() => {
							// Create new Employee Target
							frappe.new_doc("Employee Target", {
								employee: row.employee
							});
						},
						() => {
							// User declined, clear the target field
							frappe.model.set_value(cdt, cdn, "target", 0);
						}
					);
				}
			}).catch(error => {
				console.error("Error fetching Employee Target:", error);
				frappe.show_alert({
					message: "Error loading employee target information",
					indicator: 'red'
				});
				frappe.model.set_value(cdt, cdn, "target", 0);
			});
		} else {
			// Employee cleared, reset target
			frappe.model.set_value(cdt, cdn, "target", 0);
		}
	}
});
