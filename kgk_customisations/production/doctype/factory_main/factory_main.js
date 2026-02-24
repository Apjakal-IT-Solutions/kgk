// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Factory Main", {
    refresh(frm) {
        // Pre-fill table on form refresh
        prefill_section_type_target_table(frm);
    },
    
    onload(frm) {
        // Pre-fill table when form loads for the first time
        if (frm.is_new()) {
            prefill_section_type_target_table(frm);
        }
    }
});

function prefill_section_type_target_table(frm) {
    // Check if table is already populated to avoid duplicates
    if (frm.doc.factory_main_item_table && frm.doc.factory_main_item_table.length > 0) {
        return;
    }
    
    // Fetch all records from Factory Main Section Type Target doctype
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Factory Main Section Type Target",
            fields: ["name", "section", "type", "target"],
            limit_page_length: 0, // Get all records
            order_by: "section, type" // Optional: order by section and type
        },
        callback: function(response) {
            if (response.message && response.message.length > 0) {
                // Clear existing rows first
                frm.clear_table("factory_main_item_table");
                
                // Add each record as a new row in the table
                response.message.forEach(function(record) {
                    let row = frm.add_child("factory_main_item_table");
                    row.section = record.section;
                    row.type = record.type;
                    row.target = record.target;
                });
                
                // Refresh the table to show the new rows
                frm.refresh_field("factory_main_item_table");
                
                // Show success message
                frappe.show_alert({
                    message: __("Table pre-filled with {0} records", [response.message.length]),
                    indicator: 'green'
                });
            } else {
                frappe.show_alert({
                    message: __("No records found in Factory Main Section Type Target"),
                    indicator: 'orange'
                });
            }
        },
        error: function(error) {
            frappe.msgprint({
                title: __("Error"),
                message: __("Failed to fetch Factory Main Section Type Target records"),
                indicator: 'red'
            });
            console.error("Error fetching records:", error);
        }
    });
}

// Optional: Add a button to manually refresh the table
frappe.ui.form.on("Factory Main", {
    refresh(frm) {
        // Add custom button to refresh table data
        frm.add_custom_button(__("Refresh Table"), function() {
            // Clear existing data and refill
            frm.clear_table("factory_main_item_table");
            frm.refresh_field("factory_main_item_table");

            // Pre-fill again
            prefill_section_type_target_table(frm);
        }, __("Actions"));
        
        // Auto-fill on refresh if table is empty
        if (!frm.doc.section_type_target || frm.doc.section_type_target.length === 0) {
            prefill_section_type_target_table(frm);
        }
    }
});