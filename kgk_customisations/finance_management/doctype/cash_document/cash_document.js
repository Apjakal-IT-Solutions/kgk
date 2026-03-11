// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// Sub-type options per main_type
const SUB_TYPE_OPTIONS = {
"Cash":   "\nPayment\nReceipt",
"Bank":   "\nCredit Card\nEFT",
"Cash-2": "",
"Bank-2": "",
"JE":     "\nJE",
};

const FLAG_TYPES = [
"Review Required", "Approved", "Rejected",
"Query", "Hold", "Priority", "Revision Needed",
];

frappe.ui.form.on("Cash Document", {

// Form lifecycle

refresh(frm) {
frm.trigger("update_sub_type_options");
frm.trigger("refresh_action_buttons");
},

// Field handlers

main_type(frm) {
frm.set_value("sub_type", "");
frm.trigger("update_sub_type_options");
},

// Helpers

update_sub_type_options(frm) {
const opts = SUB_TYPE_OPTIONS[frm.doc.main_type] ?? "";
frm.set_df_property("sub_type", "options", opts);
frm.set_df_property("sub_type", "hidden", opts === "");
frm.refresh_field("sub_type");
},

refresh_action_buttons(frm) {
if (frm.is_new()) return;

// View File — opens the attached primary document in a new tab
if (frm.doc.main_file) {
frm.add_custom_button(__("View File"), function () {
window.open(frm.doc.main_file, "_blank");
});
}

const roles = new Set(frappe.user_roles);
const isSuperUser  = roles.has("Cash Super User") || roles.has("Administrator");
const isAccountant = roles.has("Cash Accountant") || isSuperUser;
const isChecker    = roles.has("Cash Checker")    || isSuperUser;

// Finalise (status -> final) — draft only
if (isAccountant && frm.doc.docstatus === 0 && frm.doc.status !== "final") {
frm.add_custom_button(__("Finalise"), function () {
frappe.confirm(
__("Mark this document as <b>final</b>?"),
() => {
frappe.call({
method: "kgk_customisations.finance_management.doctype.cash_document.cash_document.finalise",
args: { doc_name: frm.doc.name },
callback(r) {
if (!r.exc) frm.reload_doc();
},
});
}
);
}, __("Actions"));
}

		// Finalise 2 (final_status2 -> final2) — draft only
		if (isChecker && frm.doc.docstatus === 0 && frm.doc.final_status2 !== "final2") {
frm.add_custom_button(__("Finalise 2"), function () {
frappe.confirm(
__("Mark Status 2 as <b>final2</b>?"),
() => {
frappe.call({
method: "kgk_customisations.finance_management.doctype.cash_document.cash_document.finalise2",
args: { doc_name: frm.doc.name },
callback(r) {
if (!r.exc) frm.reload_doc();
},
});
}
);
}, __("Actions"));
}

// Add Flag
frm.add_custom_button(__("Add Flag"), function () {
const d = new frappe.ui.Dialog({
title: __("Add Review Flag"),
fields: [
{
label: __("Flag Type"),
fieldname: "flag_type",
fieldtype: "Select",
options: FLAG_TYPES.join("\n"),
reqd: 1,
},
{
label: __("Comment"),
fieldname: "comment",
fieldtype: "Small Text",
reqd: 1,
},
],
primary_action_label: __("Add"),
primary_action(values) {
frappe.call({
method: "kgk_customisations.finance_management.doctype.cash_document.cash_document.add_flag",
args: {
doc_name:  frm.doc.name,
flag_type: values.flag_type,
comment:   values.comment,
},
callback(r) {
if (!r.exc) { d.hide(); frm.reload_doc(); }
},
});
},
});
d.show();
}, __("Actions"));

// Clear Flags (Super User only)
if (isSuperUser && (frm.doc.document_flags || []).length > 0) {
frm.add_custom_button(__("Clear Flags"), function () {
frappe.confirm(
__("Remove <b>all</b> review flags from this document?"),
() => {
frappe.call({
method: "kgk_customisations.finance_management.doctype.cash_document.cash_document.clear_flags",
args: { doc_name: frm.doc.name },
callback(r) {
if (!r.exc) frm.reload_doc();
},
});
}
);
}, __("Actions"));
}
},
});
