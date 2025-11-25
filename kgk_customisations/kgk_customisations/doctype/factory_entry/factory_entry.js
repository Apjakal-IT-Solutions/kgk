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
		// Apply highlighting to all existing rows on refresh
		if (frm.doc.factory_entry_item_table && frm.doc.factory_entry_item_table.length > 0) {
			refresh_all_row_highlighting(frm);
		}
	},
	
	section: function(frm) {
		// Clear child table when section changes
		// frm.clear_table("factory_entry_item_table");
		// frm.refresh_field("factory_entry_item_table");
	}
});

frappe.ui.form.on("Factory Entry Item", {
	// Add a custom button when the row is rendered
     additional_process_on_form_rendered: function(frm, cdt, cdn) {
        add_multiselect_button(frm, cdt, cdn);
    },
    
    // Alternative: trigger when form is loaded
    form_render: function(frm, cdt, cdn) {
        add_multiselect_button(frm, cdt, cdn);
    }, 
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
		// if actual is >= target, set reason to "" and disalbled
		let row = locals[cdt][cdn];
		if (row.actual >= row.target){
			frappe.model.set_value(cdt, cdn, "reason", "");
			frappe.model.set_value(cdt, cdn, "read_only", 1);
		} else {
			frappe.model.set_value(cdt, cdn, "read_only", 0);
		}	
	}
});

function add_multiselect_button(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let grid_row = frm.fields_dict.factory_entry_item_table.grid.grid_rows_by_docname[cdn];
    
    if (!grid_row) return;
    
    // Highlight row if has additional processes
    highlight_row_with_additional_process(grid_row, row, frm);
    
    // Remove existing button if any
    grid_row.wrapper.find('.btn-additional-process').remove();
    
    // Add button in the row actions area
    let actions_area = grid_row.wrapper.find('.grid-row-actions');
    
    if (actions_area.length > 0 && !actions_area.find('.btn-additional-process').length) {
        actions_area.prepend(`
            <button class="btn btn-xs btn-secondary btn-additional-process" 
                    style="margin-right: 5px;"
                    title="Manage Additional Processes">
                <i class="fa fa-cog"></i> Additional
            </button>
        `);
        
        actions_area.find('.btn-additional-process').on('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            open_additional_process_dialog(frm, cdt, cdn);
        });
    }
}

function highlight_row_with_additional_process(grid_row, row, frm) {
    // Check if this employee has any additional processes in the parent table
    let has_additional = false;
    if (frm.doc.additional_processes && row.idx) {
        has_additional = frm.doc.additional_processes.some(p => p.parent_row_idx === row.idx);
    }
    
    // Apply or remove highlighting
    if (has_additional) {
        // Add highlight - light blue background
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

function refresh_all_row_highlighting(frm) {
    // Iterate through all child table rows and apply highlighting
    if (!frm.fields_dict.factory_entry_item_table) return;
    
    let grid = frm.fields_dict.factory_entry_item_table.grid;
    if (!grid || !grid.grid_rows) return;
    
    grid.grid_rows.forEach(grid_row => {
        if (grid_row.doc) {
            highlight_row_with_additional_process(grid_row, grid_row.doc, frm);
        }
    });
}

function open_additional_process_dialog(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    if (!row.employee) {
        frappe.msgprint(__('Please select an employee first'));
        return;
    }
    
    // Get existing additional processes for this row
    let existing_processes = [];
    if (frm.doc.additional_processes) {
        existing_processes = frm.doc.additional_processes.filter(p => p.parent_row_idx === row.idx);
    }
    
    // Fetch available factory processes
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Factory Process',
            fields: ['name'],
            filters: {},
            limit_page_length: 0
        },
        callback: function(r) {
            if (r.message) {
                show_additional_process_dialog(frm, row, existing_processes, r.message);
            }
        }
    });
}

function show_additional_process_dialog(frm, row, existing_processes, available_processes) {
    // Prepare data for the table
    let process_data = existing_processes.map(p => ({
        factory_process: p.factory_process,
        process_reason: p.process_reason,
        stones: p.stones
    }));
    
    // Create dialog
    let d = new frappe.ui.Dialog({
        title: __('Additional Processes for {0}', [row.employee_name || row.employee]),
        fields: [
            {
                fieldname: 'info',
                fieldtype: 'HTML',
                options: `<div class="small text-muted mb-3">
                    <strong>Employee:</strong> ${row.employee_name || row.employee}<br>
                    <strong>Section:</strong> ${row.section || 'N/A'}
                </div>`
            },
            {
                fieldname: 'processes_table',
                fieldtype: 'Table',
                label: 'Additional Processes',
                cannot_add_rows: false,
                cannot_delete_rows: false,
                in_place_edit: true,
                data: process_data,
                fields: [
                    {
                        fieldname: 'factory_process',
                        fieldtype: 'Link',
                        label: 'Factory Process',
                        options: 'Factory Process',
                        in_list_view: 1,
                        reqd: 1,
                        columns: 3
                    },
                    {
                        fieldname: 'process_reason',
                        fieldtype: 'Link',
                        label: 'Reason',
                        options: 'Reason',
                        in_list_view: 1,
                        reqd: 1,
                        columns: 3
                    },
                    {
                        fieldname: 'stones',
                        fieldtype: 'Int',
                        label: 'Stones',
                        in_list_view: 1,
                        reqd: 1,
                        columns: 2
                    }
                ]
            }
        ],
        primary_action_label: __('Save'),
        primary_action: function(values) {
            save_additional_processes(frm, row, values.processes_table);
            d.hide();
        }
    });
    
    d.show();
}

function save_additional_processes(frm, row, process_data) {
    // Remove existing additional processes for this row
    if (!frm.doc.additional_processes) {
        frm.doc.additional_processes = [];
    }
    
    // Filter out old entries for this row
    frm.doc.additional_processes = frm.doc.additional_processes.filter(
        p => p.parent_row_idx !== row.idx
    );
    
    // Add new entries
    if (process_data && process_data.length > 0) {
        process_data.forEach(p => {
            if (p.factory_process) {  // Only add if process is selected
                let child = frappe.model.add_child(frm.doc, 'Factory Entry Additional Process', 'additional_processes');
                child.employee = row.employee;
                child.employee_name = row.employee_name;
                child.factory_process = p.factory_process;
                child.process_reason = p.process_reason;
                child.stones = p.stones || 0;
                child.parent_row_idx = row.idx;
            }
        });
    }
    
    // Refresh the field and highlighting
    frm.refresh_field('additional_processes');
    refresh_all_row_highlighting(frm);
    frm.dirty();
}