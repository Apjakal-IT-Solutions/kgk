// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("OCR Data Upload", {
	refresh(frm) {
		// Add custom buttons
		if (!frm.is_new()) {
			frm.add_custom_button(__('Download Cumulative Report'), function() {
				frappe.call({
					method: "kgk_customisations.kgk_customisations.doctype.ocr_data_upload.ocr_data_upload.download_cumulative_report",
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __('Report generated successfully'),
								indicator: 'green'
							}, 5);
							if (r.message.file_url) {
								window.open(r.message.file_url, '_blank');
							}
						} else if (r.message && r.message.message) {
							frappe.show_alert({
								message: r.message.message,
								indicator: 'red'
							}, 7);
						}
					},
					error: function(r) {
						console.error("Error downloading report:", r);
						frappe.show_alert({
							message: __('Error generating report. Please try again.'),
							indicator: 'red'
						}, 7);
					}
				});
			});
		}
	},

	file_upload(frm) {
		if (frm.doc.file_upload) {
			console.log("File uploaded, calling preview method");
			// Wait a moment to avoid saving conflicts
			setTimeout(function() {
				frm.call({
					method: "preview_excel_data",
					doc: frm.doc,
					callback: function(r) {
						console.log("Preview callback:", r);
						if (r.message) {
							if (r.message.success) {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								}, 5);
								frm.refresh_field('items');
								frm.set_value('total_records', r.message.rows_loaded || 0);
								// Save after setting values, with a small delay to avoid conflicts
								setTimeout(function() {
									if (!frm.is_dirty() || !frm.doc.__unsaved) {
										frm.save();
									} else {
										console.log("Form already saved or saving");
									}
								}, 500);
							} else {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'red'
								}, 7);
							}
						} else {
							console.error("No message in response:", r);
							frappe.show_alert({
								message: "Error: No response from server",
								indicator: 'red'
							}, 7);
						}
					},
					error: function(r) {
						console.error("Error in preview call:", r);
						frappe.show_alert({
							message: "Error calling preview method: " + (r.message || "Unknown error"),
							indicator: 'red'
						}, 7);
					}
				});
			}, 1000); // Wait 1 second to let any automatic save complete
		}
	}
});