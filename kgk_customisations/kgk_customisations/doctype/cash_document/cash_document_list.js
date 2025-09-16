// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.listview_settings['Cash Document'] = {
	add_fields: ["transaction_type", "status", "amount", "currency", "transaction_date", "party", "created_by_user"],
	
	get_indicator: function(doc) {
		if (doc.status === "Processed") {
			return [__("Processed"), "green", "status,=,Processed"];
		} else if (doc.status === "Approved") {
			return [__("Approved"), "blue", "status,=,Approved"];
		} else if (doc.status === "Pending Review") {
			return [__("Pending Review"), "orange", "status,=,Pending Review"];
		} else if (doc.status === "Rejected") {
			return [__("Rejected"), "red", "status,=,Rejected"];
		} else {
			return [__("Draft"), "gray", "status,=,Draft"];
		}
	},
	
	filters: [
		['status', '!=', 'Cancelled']
	],
	
	onload: function(listview) {
		// Add quick filter buttons
		listview.page.add_action_item(__('Pending Documents'), function() {
			listview.filter_area.clear();
			listview.filter_area.add([
				['Cash Document', 'status', '!=', 'Processed']
			]);
			listview.refresh();
		});
		
		listview.page.add_action_item(__('Today\'s Documents'), function() {
			listview.filter_area.clear();
			listview.filter_area.add([
				['Cash Document', 'transaction_date', '=', frappe.datetime.get_today()]
			]);
			listview.refresh();
		});
		
		listview.page.add_action_item(__('This Week'), function() {
			let week_start = frappe.datetime.add_days(frappe.datetime.get_today(), -7);
			listview.filter_area.clear();
			listview.filter_area.add([
				['Cash Document', 'transaction_date', 'between', [week_start, frappe.datetime.get_today()]]
			]);
			listview.refresh();
		});
		
		listview.page.add_action_item(__('Flagged Documents'), function() {
			// Get flagged documents
			frappe.call({
				method: 'kgk_customisations.kgk_customisations.doctype.cash_document.cash_document.get_flagged_documents',
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						listview.filter_area.clear();
						listview.filter_area.add([
							['Cash Document', 'name', 'in', r.message]
						]);
						listview.refresh();
					} else {
						frappe.msgprint(__('No flagged documents found'));
					}
				}
			});
		});
		
		// Add bulk operations button
		if (frappe.user.has_role(['Cash Accountant', 'Cash Super User', 'Administrator'])) {
			listview.page.add_action_item(__('Bulk Operations'), function() {
				show_bulk_operations_dialog(listview);
			});
		}
		
		// Add missing documents report button
		listview.page.add_action_item(__('Missing Documents'), function() {
			frappe.set_route('query-report', 'Missing Cash Documents Report');
		});
		
		// Add real-time counters
		add_realtime_counters(listview);
	},
	
	formatters: {
		amount: function(value) {
			return frappe.format(value, {fieldtype: 'Currency'});
		},
		transaction_date: function(value) {
			return frappe.format(value, {fieldtype: 'Date'});
		}
	},
	
	// Custom column width
	column_render: {
		"document_number": function(doc, col, value, column) {
			return `<a href="/app/cash-document/${doc.name}" style="font-weight: bold;">${value}</a>`;
		}
	}
};

function show_bulk_operations_dialog(listview) {
	let selected = listview.get_checked_items(true);
	
	if (selected.length === 0) {
		frappe.msgprint(__('Please select documents first'));
		return;
	}
	
	let dialog = new frappe.ui.Dialog({
		title: __('Bulk Operations'),
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'selected_info',
				options: `<p><strong>${selected.length} documents selected</strong></p>`
			},
			{
				fieldtype: 'Select',
				fieldname: 'operation',
				label: __('Operation'),
				options: [
					'',
					'Finalize Documents',
					'Approve Documents', 
					'Flag as Review Required',
					'Flag as Rejected'
				],
				reqd: 1
			},
			{
				fieldtype: 'Long Text',
				fieldname: 'comments',
				label: __('Comments'),
				description: __('Optional comments for the operation')
			}
		],
		primary_action: function(values) {
			if (!values.operation) {
				frappe.msgprint(__('Please select an operation'));
				return;
			}
			
			let method_map = {
				'Finalize Documents': 'bulk_finalize_documents',
				'Approve Documents': 'bulk_approve_documents',
				'Flag as Review Required': 'bulk_flag_documents',
				'Flag as Rejected': 'bulk_flag_documents'
			};
			
			let args = {
				document_names: selected
			};
			
			if (values.operation.startsWith('Flag')) {
				args.flag_type = values.operation.replace('Flag as ', '');
				args.comments = values.comments;
			} else if (values.operation === 'Approve Documents') {
				args.comments = values.comments;
			}
			
			frappe.call({
				method: `kgk_customisations.kgk_customisations.doctype.cash_document.cash_document.${method_map[values.operation]}`,
				args: args,
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __('Bulk Operation Complete'),
							message: r.message.message,
							indicator: r.message.errors.length > 0 ? 'orange' : 'green'
						});
						
						if (r.message.errors.length > 0) {
							frappe.msgprint({
								title: __('Errors'),
								message: r.message.errors.join('<br>'),
								indicator: 'red'
							});
						}
						
						listview.refresh();
					}
				},
				freeze: true,
				freeze_message: __('Processing documents...')
			});
			
			dialog.hide();
		},
		primary_action_label: __('Execute')
	});
	
	dialog.show();
}

function add_realtime_counters(listview) {
	// Add counters to the page
	let counters_html = `
		<div class="cash-counters" style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
			<div class="row">
				<div class="col-md-3">
					<div class="counter-box">
						<span class="counter-label">Pending:</span>
						<span class="counter-value pending-counter">-</span>
					</div>
				</div>
				<div class="col-md-3">
					<div class="counter-box">
						<span class="counter-label">Today:</span>
						<span class="counter-value today-counter">-</span>
					</div>
				</div>
				<div class="col-md-3">
					<div class="counter-box">
						<span class="counter-label">Flagged:</span>
						<span class="counter-value flagged-counter">-</span>
					</div>
				</div>
				<div class="col-md-3">
					<div class="counter-box">
						<span class="counter-label">Total:</span>
						<span class="counter-value total-counter">-</span>
					</div>
				</div>
			</div>
		</div>
	`;
	
	// Add CSS for counters
	if (!document.getElementById('cash-counter-styles')) {
		let style = document.createElement('style');
		style.id = 'cash-counter-styles';
		style.innerHTML = `
			.cash-counters .counter-box {
				text-align: center;
				padding: 5px;
			}
			.cash-counters .counter-label {
				display: block;
				font-size: 12px;
				color: #666;
			}
			.cash-counters .counter-value {
				display: block;
				font-size: 18px;
				font-weight: bold;
				color: #333;
			}
		`;
		document.head.appendChild(style);
	}
	
	// Insert counters after the page title
	$(counters_html).insertAfter(listview.page.page_title);
	
	// Update counters
	update_counters();
	
	// Update counters every 30 seconds
	setInterval(update_counters, 30000);
}

function update_counters() {
	// Get pending count
	frappe.call({
		method: 'kgk_customisations.kgk_customisations.doctype.cash_document.cash_document.get_pending_count',
		callback: function(r) {
			$('.pending-counter').text(r.message || 0);
		}
	});
	
	// Get today's count
	frappe.call({
		method: 'frappe.client.get_count',
		args: {
			doctype: 'Cash Document',
			filters: {
				'transaction_date': frappe.datetime.get_today()
			}
		},
		callback: function(r) {
			$('.today-counter').text(r.message || 0);
		}
	});
	
	// Get flagged count
	frappe.call({
		method: 'kgk_customisations.kgk_customisations.doctype.cash_document.cash_document.get_flagged_count',
		callback: function(r) {
			$('.flagged-counter').text(r.message || 0);
		}
	});
	
	// Get total count
	frappe.call({
		method: 'frappe.client.get_count',
		args: {
			doctype: 'Cash Document'
		},
		callback: function(r) {
			$('.total-counter').text(r.message || 0);
		}
	});
}

// Keyboard shortcuts
$(document).on('keydown', function(e) {
	if (cur_page && cur_page.page_name === 'List/Cash Document') {
		if (e.ctrlKey) {
			switch(e.keyCode) {
				case 70: // Ctrl+F - Focus search
					e.preventDefault();
					$('.search-input-area input').focus();
					break;
				case 78: // Ctrl+N - New Document
					e.preventDefault();
					frappe.new_doc('Cash Document');
					break;
			}
		}
	}
});