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
							const { matched, not_found, not_found_total, xls_jeid_rows, xls_invoice_rows } = r.message;
							const totalXls = (xls_jeid_rows || 0) + (xls_invoice_rows || 0);
							let msg = `<b>${matched}</b> document(s) updated`
								+ ` (${xls_jeid_rows} matched by JEID, ${xls_invoice_rows} by Invoice #`
								+ ` from ${totalXls} XLS data row${totalXls === 1 ? "" : "s"}).`;
							if (not_found.length) {
								const extra = not_found_total > not_found.length
									? ` <i>(showing ${not_found.length} of ${not_found_total} — full list in Error Log)</i>` : "";
								msg += `<br><br><b>${not_found_total}</b> document(s) had no match in the file:${extra}<br>`
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
