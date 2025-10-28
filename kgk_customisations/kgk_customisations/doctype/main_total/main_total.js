// set actual_total on form load and refresh
frappe.ui.form.on("Main Total", {
    refresh(frm) {
        // actual_total is equivalent to round_actual + fancy_actual
        let actual_total = (frm.doc.round_actual || 0) + (frm.doc.fancy_actual || 0);
        frm.set_value('actual_total', actual_total);

        // target_total is equivalent to target_round + fancy_round
        let target_total = (frm.doc.round_target || 0) + (frm.doc.fancy_target || 0);
        frm.set_value('target_total', target_total);
    }
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