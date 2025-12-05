// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("File Search Config", {
	refresh(frm) {
		// Add button to trigger full indexing
		frm.add_custom_button(__('Reindex All Files'), function() {
			frappe.confirm(
				__('This will reindex all video, advisor, and scan files. This may take several minutes. Continue?'),
				function() {
					// On confirm
					frappe.call({
						method: 'kgk_customisations.file_management.Utils.indexer.start_full_indexing',
						callback: function(r) {
							if (r.message) {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								});
								
								// Set status to indicate indexing started
								frm.set_value('indexing_status', 'Indexing in progress...');
								frm.save();
								
								// Listen for progress updates
								frappe.realtime.on('indexing_progress', function(data) {
									if (data.progress === 100) {
										frappe.show_alert({
											message: __('Indexing complete!'),
											indicator: 'green'
										});
										frm.set_value('indexing_status', 'Complete');
										frm.reload_doc();
									} else if (data.progress === -1) {
										frappe.show_alert({
											message: __('Indexing failed: ') + data.status,
											indicator: 'red'
										});
										frm.set_value('indexing_status', 'Failed: ' + data.status);
										frm.save();
									} else {
										frm.set_value('indexing_status', data.status + ' (' + data.progress + '%)');
										frm.refresh_field('indexing_status');
									}
								});
							}
						}
					});
				}
			);
		}, __('Actions'));
		
		// Add button to index only advisor files
		frm.add_custom_button(__('Index Advisor Files'), function() {
			frappe.call({
				method: 'kgk_customisations.file_management.Utils.indexer.start_advisor_indexing',
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: r.message.message,
							indicator: 'green'
						});
					}
				}
			});
		}, __('Actions'));
		
		// Display file index summary
		if (!frm.is_new()) {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'File Index',
					fields: ['file_type', 'count(*) as count'],
					group_by: 'file_type'
				},
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						let summary_html = '<div class="form-message blue"><b>Indexed Files Summary:</b><br>';
						let total = 0;
						r.message.forEach(function(row) {
							summary_html += `${row.file_type}: ${row.count}<br>`;
							total += row.count;
						});
						summary_html += `<b>Total: ${total}</b></div>`;
						frm.dashboard.add_comment(summary_html, null, true);
					}
				}
			});
		}
	}
});

