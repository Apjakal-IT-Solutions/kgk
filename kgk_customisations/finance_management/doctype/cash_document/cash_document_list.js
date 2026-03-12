frappe.listview_settings["Cash Document"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Import JE Details"), function () {
			const d = new frappe.ui.Dialog({
				title: __("Import JE Details"),
				fields: [
					{
						label: __("Fantasy Export File (.xls / .xlsx)"),
						fieldname: "export_file",
						fieldtype: "Attach",
						reqd: 1,
						description: __("Upload the Fantasy Export spreadsheet. It will be deleted from the server after processing."),
					},
				],
				primary_action_label: __("Import"),
				primary_action(values) {
					if (!values.export_file) return;
					d.hide();
					frappe.show_alert({ message: __("Importing, please wait…"), indicator: "blue" });
					frappe.call({
						method: "kgk_customisations.finance_management.doctype.cash_document.cash_document.import_je_details",
						args: { file_url: values.export_file },
						callback(r) {
							if (r.exc) return;
							const { matched, not_found, xls_rows } = r.message;
							let msg = `<b>${matched}</b> document(s) updated from ${xls_rows} XLS entr${xls_rows === 1 ? "y" : "ies"}.`;
							if (not_found.length) {
								msg += `<br><br><b>${not_found.length}</b> JE ID(s) had no match in the file:<br>`
									+ not_found.map(n => `&nbsp;&bull; ${n}`).join("<br>");
							}
							frappe.msgprint({ title: __("Import Complete"), message: msg, indicator: "green" });
							listview.refresh();
						},
					});
				},
			});
			d.show();
		});
	},
};
