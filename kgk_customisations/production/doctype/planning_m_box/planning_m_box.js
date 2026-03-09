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


// Event handler for additional processes table changes
frappe.ui.form.on("Planning M-Box Additional Process Item", {
	additional_process_table_add: function(frm) {
		apply_additional_process_highlighting(frm);
	},
	additional_process_table_remove: function(frm) {
		apply_additional_process_highlighting(frm);
	},
	factory_code: function(frm) {
		apply_additional_process_highlighting(frm);
	}
});

function apply_additional_process_highlighting(frm) {
	// Wait for the grid to be rendered
	setTimeout(() => {
		if (!frm.fields_dict.primary_process_table || !frm.fields_dict.primary_process_table.grid) return;
		
		let grid = frm.fields_dict.primary_process_table.grid;
		if (!grid.grid_rows) return;
		
		// Get all factory_codes that have additional processes
		let rows_with_additional = new Set();
		if (frm.doc.additional_process_table) {
			frm.doc.additional_process_table.forEach(process => {
				if (process.factory_code) {
					rows_with_additional.add(process.factory_code);
				}
			});
		}
		
		// Apply highlighting to each grid row
		grid.grid_rows.forEach(grid_row => {
			if (grid_row.doc && grid_row.doc.factory_code) {
				if (rows_with_additional.has(grid_row.doc.factory_code)) {
					// Add highlight - light blue background with left border
					grid_row.wrapper.css({
						'border': '3px solid #2490ef',
						'color': '#000'
					});
					grid_row.wrapper.addClass('has-additional-process');
				} else {
					// Remove highlight
					grid_row.wrapper.css({
						'background-color': '',
						'border': ''
					});
					grid_row.wrapper.removeClass('has-additional-process');
				}
			}
		});
	}, 100);
}
