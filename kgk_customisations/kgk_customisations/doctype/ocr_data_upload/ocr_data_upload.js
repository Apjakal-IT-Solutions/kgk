// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("OCR Data Upload", {
	refresh(frm) {
		// Add custom buttons
		if (!frm.is_new()) {
			frm.add_custom_button(__('Download Cumulative Report'), function() {
				// Show progress dialog
				let progress_dialog = new frappe.ui.Dialog({
					title: __('Generating Report'),
					fields: [{
						fieldtype: 'HTML',
						fieldname: 'progress_html',
						options: `
							<div class="text-center">
								<h5>Processing OCR Data Report</h5>
								<div class="progress mb-3">
									<div class="progress-bar progress-bar-striped progress-bar-animated bg-info" 
										 style="width: 100%" role="progressbar">
										<span>Preparing data...</span>
									</div>
								</div>
								<p class="text-muted">
									<i class="fa fa-info-circle"></i> 
									Large datasets may take several minutes to process.
								</p>
							</div>
						`
					}],
					primary_action_label: __('Cancel'),
					primary_action: function() {
						progress_dialog.hide();
					}
				});
				
				progress_dialog.show();
				
				frappe.call({
					method: "kgk_customisations.kgk_customisations.doctype.ocr_data_upload.ocr_data_upload.download_cumulative_report",
					timeout: 300000, // 5 minutes timeout
					callback: function(r) {
						progress_dialog.hide();
						
						if (r.message && r.message.success) {
							if (r.message.is_background) {
								// Background job started
								frappe.show_alert({
									message: r.message.message,
									indicator: 'blue'
								}, 10);
								
								// Show background job notification
								frappe.msgprint({
									title: __('Report Generation Started'),
									indicator: 'blue',
									message: `
										<div class="text-center">
											<h5><i class="fa fa-cog fa-spin"></i> Background Processing</h5>
											<p>Your report with ${r.message.records_count} records is being generated in the background.</p>
											<p><strong>You will receive a notification when it's ready for download.</strong></p>
											<small class="text-muted">Estimated time: ${Math.ceil(r.message.records_count/1000)} - ${Math.ceil(r.message.records_count/500)} minutes</small>
										</div>
									`
								});
							} else {
								// Immediate download
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								}, 5);
								
								if (r.message.file_url) {
									window.open(r.message.file_url, '_blank');
								}
							}
						} else if (r.message && r.message.message) {
							frappe.show_alert({
								message: r.message.message,
								indicator: 'red'
							}, 7);
						}
					},
					error: function(r) {
						progress_dialog.hide();
						console.error("Error downloading report:", r);
						
						let error_msg = 'Error generating report. Please try again.';
						if (r.responseJSON && r.responseJSON.message) {
							error_msg += ' Details: ' + r.responseJSON.message;
						}
						
						frappe.show_alert({
							message: __(error_msg),
							indicator: 'red'
						}, 10);
					}
				});
			});
		}
		
		// Add help text for file upload
		if (frm.fields_dict.file_upload) {
			frm.set_df_property('file_upload', 'description', 
				'Upload Excel files with OCR data. Large files (>1000 rows) will show a progress indicator during processing.');
		}
	},

	file_upload(frm) {
		if (frm.doc.file_upload) {
			console.log("File uploaded, calling preview method");
			
			// Create progress dialog for file processing
			let upload_progress = new frappe.ui.Dialog({
				title: __('Processing Excel File'),
				fields: [{
					fieldtype: 'HTML',
					fieldname: 'upload_progress_html',
					options: `
						<div class="text-center">
							<h5><i class="fa fa-file-excel-o text-success"></i> Processing Excel Data</h5>
							<div class="progress mb-3">
								<div class="progress-bar progress-bar-striped progress-bar-animated bg-success" 
									 style="width: 100%" role="progressbar">
									<span>Reading and analyzing data...</span>
								</div>
							</div>
							<div id="upload-status">
								<p><i class="fa fa-search"></i> Parsing Excel columns and mapping fields...</p>
								<p><i class="fa fa-cogs"></i> Running OCR analysis and data extraction...</p>
								<p><i class="fa fa-save"></i> Saving processed data...</p>
							</div>
							<p class="text-muted">
								<small>This may take a moment for large files.</small>
							</p>
						</div>
					`
				}],
				primary_action_label: __('Cancel'),
				primary_action: function() {
					upload_progress.hide();
				}
			});
			
			upload_progress.show();
			
			// Wait a moment to avoid saving conflicts, then process
			setTimeout(function() {
				frm.call({
					method: "preview_excel_data",
					doc: frm.doc,
					timeout: 120000, // 2 minutes timeout
					callback: function(r) {
						upload_progress.hide();
						console.log("Preview callback:", r);
						
						if (r.message) {
							if (r.message.success) {
								// Success notification
								frappe.show_alert({
									message: r.message.message,
									indicator: 'green'
								}, 5);
								
								// Show success dialog with details
								frappe.msgprint({
									title: __('File Processed Successfully'),
									indicator: 'green',
									message: `
										<div class="text-center">
											<h5><i class="fa fa-check-circle text-success"></i> Processing Complete</h5>
											<p><strong>${r.message.rows_loaded || 0}</strong> records loaded and processed.</p>
											<p>Data is now available in the Items table below.</p>
										</div>
									`
								});
								
								frm.refresh_field('items');
								frm.set_value('total_records', r.message.rows_loaded || 0);
								
								// Save after setting values
								setTimeout(function() {
									if (!frm.is_dirty() || !frm.doc.__unsaved) {
										frm.save();
									}
								}, 500);
							} else {
								frappe.show_alert({
									message: r.message.message,
									indicator: 'red'
								}, 7);
								
								// Show detailed error
								frappe.msgprint({
									title: __('File Processing Error'),
									indicator: 'red',
									message: `
										<div>
											<h5><i class="fa fa-exclamation-triangle text-danger"></i> Processing Failed</h5>
											<p>${r.message.message}</p>
											<p><strong>Please check:</strong></p>
											<ul>
												<li>File format is .xlsx or .xls</li>
												<li>File is not corrupted</li>
												<li>File contains expected column headers</li>
											</ul>
										</div>
									`
								});
							}
						} else {
							console.error("No message in response:", r);
							upload_progress.hide();
							frappe.show_alert({
								message: "Error: No response from server",
								indicator: 'red'
							}, 7);
						}
					},
					error: function(r) {
						upload_progress.hide();
						console.error("Error in preview call:", r);
						
						let error_msg = "Error processing file: " + (r.message || "Unknown error");
						if (r.responseJSON && r.responseJSON.message) {
							error_msg = "Error processing file: " + r.responseJSON.message;
						}
						
						frappe.show_alert({
							message: error_msg,
							indicator: 'red'
						}, 10);
						
						// Show detailed error dialog
						frappe.msgprint({
							title: __('File Processing Error'),
							indicator: 'red',
							message: `
								<div>
									<h5><i class="fa fa-exclamation-triangle text-danger"></i> Processing Failed</h5>
									<p>${error_msg}</p>
									<p><strong>Possible causes:</strong></p>
									<ul>
										<li>File is too large (try splitting into smaller files)</li>
										<li>Server timeout (try again or contact support)</li>
										<li>Invalid file format or corrupted data</li>
									</ul>
								</div>
							`
						});
					}
				});
			}, 1000);
		}
	}
});