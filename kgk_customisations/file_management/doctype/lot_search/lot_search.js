// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Lot Search", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.lot_number) {
			// Add search button
			frm.add_custom_button(__('Search Files'), function() {
				frappe.call({
					method: 'kgk_customisations.file_management.Utils.file_operations.search_all_files',
					args: {
						lot_number: frm.doc.lot_number,
						use_cache: 0  // Bypass cache for fresh results
					},
					callback: function(r) {
						if (r.message) {
							frm.set_value('search_results', r.message);
							frm.save();
							display_search_results(frm, r.message);
						}
					}
				});
			}, __('Actions'));
			
			// Add open files button
			frm.add_custom_button(__('Open All Files'), function() {
				frappe.confirm(
					__('This will open all indexed files for lot {0}. Continue?', [frm.doc.lot_number]),
					function() {
						frappe.call({
							method: 'kgk_customisations.file_management.Utils.file_opener.open_lot_files',
							args: {
								lot_number: frm.doc.lot_number
							},
							callback: function(r) {
								if (r.message) {
									frappe.show_alert({
										message: r.message.message,
										indicator: r.message.status === 'success' ? 'green' : 'red'
									});
								}
							}
						});
					}
				);
			}, __('Actions'));
			
			// Add validate files button
			frm.add_custom_button(__('Validate Files'), function() {
				frappe.call({
					method: 'kgk_customisations.file_management.Utils.file_operations.validate_indexed_files',
					args: {
						lot_number: frm.doc.lot_number
					},
					callback: function(r) {
						if (r.message) {
							frappe.msgprint({
								title: __('Validation Complete'),
								message: r.message.message,
								indicator: 'green'
							});
						}
					}
				});
			}, __('Actions'));
			
			// Display search results if available
			if (frm.doc.search_results) {
				try {
					let results = typeof frm.doc.search_results === 'string' 
						? JSON.parse(frm.doc.search_results) 
						: frm.doc.search_results;
					display_search_results(frm, results);
				} catch (e) {
					console.error('Error parsing search results:', e);
				}
			}
		}
	}
});

function display_search_results(frm, results) {
	let html = '<div class="search-results-display">';
	
	// Polish Video
	if (results.polish_video && results.polish_video.found) {
		html += `<div class="alert alert-success">
			<strong>Polish Video:</strong> ${results.polish_video.name}<br>
			<small>Path: ${results.polish_video.path}</small><br>
			<button class="btn btn-xs btn-primary" onclick="open_file_path('${results.polish_video.path}')">Open File</button>
		</div>`;
	} else {
		html += '<div class="alert alert-warning"><strong>Polish Video:</strong> Not found</div>';
	}
	
	// Rough Video
	if (results.rough_video && results.rough_video.found) {
		html += `<div class="alert alert-success">
			<strong>Rough Video:</strong> ${results.rough_video.name}<br>
			<small>Path: ${results.rough_video.path}</small><br>
			<button class="btn btn-xs btn-primary" onclick="open_file_path('${results.rough_video.path}')">Open File</button>
		</div>`;
	} else {
		html += '<div class="alert alert-warning"><strong>Rough Video:</strong> Not found</div>';
	}
	
	// Advisor Files
	if (results.advisor_files && results.advisor_files.length > 0) {
		html += '<div class="alert alert-info"><strong>Advisor Files:</strong><ul>';
		results.advisor_files.forEach(function(file) {
			html += `<li>${file.name} <button class="btn btn-xs btn-primary" onclick="open_file_path('${file.path}')">Open</button></li>`;
		});
		html += '</ul></div>';
	} else {
		html += '<div class="alert alert-warning"><strong>Advisor Files:</strong> Not found</div>';
	}
	
	// Scan Files
	if (results.scan_files && results.scan_files.length > 0) {
		html += '<div class="alert alert-info"><strong>Scan Files:</strong><ul>';
		results.scan_files.forEach(function(file) {
			html += `<li>${file.name} (${file.type}) <button class="btn btn-xs btn-primary" onclick="open_file_path('${file.path}')">Open</button></li>`;
		});
		html += '</ul></div>';
	} else {
		html += '<div class="alert alert-warning"><strong>Scan Files:</strong> Not found</div>';
	}
	
	html += '</div>';
	
	frm.dashboard.set_headline_alert(html);
}

function open_file_path(file_path) {
	frappe.call({
		method: 'kgk_customisations.file_management.Utils.file_opener.open_file_by_path',
		args: {
			file_path: file_path
		},
		callback: function(r) {
			if (r.message) {
				frappe.show_alert({
					message: r.message.message,
					indicator: r.message.status === 'success' ? 'green' : 'red'
				});
			}
		}
	});
}

