// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Planning Entry Item', {
    employee_code: function(frm, cdt, cdn) {
        // Trigger when employee_code field changes
        let row = locals[cdt][cdn];
        if (row.employee_code && !row.employee) {
            // Search for Employee Target by factory_code
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee Target',
                    filters: {
                        factory_code: row.employee_code
                    },
                    fields: ['name', 'employee_name', 'factory_code', 'target']
                },
                callback: function(response) {
                    if (response.message && response.message.length > 0) {
                        let employee_target = response.message[0];
                        // Set the Employee Target name (this will auto-fetch employee_name and factory_code)
                        frappe.model.set_value(cdt, cdn, 'employee', employee_target.name);
                        frm.refresh_field('planning_entry_item_table');
                    } else {
                        frappe.msgprint(`No Employee Target found for factory code: ${row.employee_code}`);
                        // Clear the employee_code if no match found
                        frappe.model.set_value(cdt, cdn, 'employee_code', '');
                    }
                }
            });
        }
    },
    
    employee: function(frm, cdt, cdn) {
        // This will automatically trigger fetch_from fields
        // employee_name and employee_code will be auto-populated from Employee Target
        frm.refresh_field('planning_entry_item_table');
    }
});