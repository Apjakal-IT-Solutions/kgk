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
		// Apply highlighting to rows that have additional processes
		apply_additional_process_highlighting(frm);
	},
	
	section: function(frm) {
		// Clear child table when section changes
		// frm.clear_table("factory_entry_item_table");
		// frm.refresh_field("factory_entry_item_table");
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
	},
	employee_code: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.employee_code) {
			// Search for Employee Target record by employee code
			frappe.db.get_list("Employee Target", {
				filters: {
					factory_code: row.employee_code
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
	},
	actual: function(frm, cdt, cdn){
		// if actual is >= target, set reason to "" and disabled
		let row = locals[cdt][cdn];
		if (row.actual >= row.target){
			frappe.model.set_value(cdt, cdn, "reason", "");
			frappe.model.set_value(cdt, cdn, "read_only", 1);
		} else {
			frappe.model.set_value(cdt, cdn, "read_only", 0);
		}	
	}
});

// Event handler for additional processes table changes
frappe.ui.form.on("Factory Entry Additional Process", {
	additional_process_item_table_add: function(frm) {
		apply_additional_process_highlighting(frm);
	},
	additional_process_item_table_remove: function(frm) {
		apply_additional_process_highlighting(frm);
	},
	parent_row_idx: function(frm) {
		apply_additional_process_highlighting(frm);
	}
});

function apply_additional_process_highlighting(frm) {
	// Wait for the grid to be rendered
	setTimeout(() => {
		if (!frm.fields_dict.factory_entry_item_table || !frm.fields_dict.factory_entry_item_table.grid) return;
		
		let grid = frm.fields_dict.factory_entry_item_table.grid;
		if (!grid.grid_rows) return;
		
		// Get all parent_row_idx values that have additional processes
		let rows_with_additional = new Set();
		if (frm.doc.additional_process_item_table) {
			frm.doc.additional_process_item_table.forEach(process => {
				if (process.parent_row_idx) {
					rows_with_additional.add(process.parent_row_idx);
				}
			});
		}
		
		// Apply highlighting to each grid row
		grid.grid_rows.forEach(grid_row => {
			if (grid_row.doc && grid_row.doc.idx) {
				if (rows_with_additional.has(grid_row.doc.idx)) {
					// Add highlight - light blue background with left border
					grid_row.wrapper.css({
						'background-color': '#e7f3ff',
						'border-left': '3px solid #2490ef'
					});
					grid_row.wrapper.addClass('has-additional-process');
				} else {
					// Remove highlight
					grid_row.wrapper.css({
						'background-color': '',
						'border-left': ''
					});
					grid_row.wrapper.removeClass('has-additional-process');
				}
			}
		});
	}, 100);
}

