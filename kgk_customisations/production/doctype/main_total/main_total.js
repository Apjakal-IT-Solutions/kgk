// set actual_total on form load and refresh
frappe.ui.form.on("Main Total", {
    refresh(frm) {
        // actual_total is equivalent to round_actual + fancy_actual
        let actual_total = (frm.doc.round_actual || 0) + (frm.doc.fancy_actual || 0);
        frm.set_value('actual_total', actual_total);

        // target_total is equivalent to target_round + fancy_round
        let target_total = (frm.doc.round_target || 0) + (frm.doc.fancy_target || 0);
        frm.set_value('target_total', target_total);
    }, 

    onload(frm) {
        // get all values from "Factory Main Section Type Target" and populate child table
        frappe.db.get_list("Factory Main Section Type Target", {
            fields: ["target", "type", "section"]
        }).then(records => {
            if (records && records.length > 0) {
                // Populate child table with fetched records
                records.forEach(record => {
                    let child = frm.add_child("factory_main_item_table");
                    child.target = record.target;
                    child.type = record.type;
                    child.section = record.section;
                });
                // sort child table by section and type
                frm.doc.factory_main_item_table.sort((a, b) => {
                    if (a.section === b.section) {
                        return a.type.localeCompare(b.type);
                    }
                    return a.section.localeCompare(b.section);
                });
                frm.refresh_field("factory_main_item_table");
            }
        });
    },
});

// set actual_total on change of actual_round or fancy_round
frappe.ui.form.on("Main Total", {
    round_actual(frm) {
        let actual_total = (frm.doc.round_actual || 0) + (frm.doc.fancy_actual || 0);
        frm.set_value('actual_total', actual_total);
    },
    fancy_actual(frm) {
        let actual_total = (frm.doc.round_actual || 0) + (frm.doc.fancy_actual || 0);
        frm.set_value('actual_total', actual_total);

        let target_total = (frm.doc.round_target || 0) + (frm.doc.fancy_target || 0);
        frm.set_value('target_total', target_total);
    },
    round_target(frm) {
        let target_total = (frm.doc.round_target || 0) + (frm.doc.fancy_target || 0);
        frm.set_value('target_total', target_total);
    }
});

// //  On selection of section values, search for all "Factory Main Section Type Target" with matching section and populate the child table rows
// frappe.ui.form.on("Factory Main Item", {
//     section(frm) {
//         if (frm.doc.section) {
//             // Fetch Factory Main Section Type Target records based on selected section
//             frappe.db.get_list("Factory Main Section Type Target", {
//                 filters: {
//                     section: frm.doc.section
//                 },
//                 fields: ["name", "target", "factory_process", "employee_name"]
//             }).then(records => {
//                 if (records && records.length > 0) {
//                     // Populate child table with fetched records
//                     records.forEach(record => {
//                         let child = frm.add_child("main_main_item_table");
//                         child.target = record.target;
//                         child.factory_process = record.factory_process;
//                         child.employee_name = record.employee_name;
//                     });
//                     frm.refresh_field("main_main_item_table");
//                 }
//             });
//         }
//     }
// });