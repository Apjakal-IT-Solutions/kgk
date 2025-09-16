// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.ui.form.on('Daily Cash Balance', {
	refresh: function(frm) {
		// Set up custom buttons and indicators
		setup_balance_buttons(frm);
		
		// Add variance indicators
		setup_variance_indicators(frm);
		
		// Setup auto-calculation triggers
		setup_calculation_triggers(frm);
		
		// Add custom styling for variance fields
		add_variance_styling(frm);
	},
	
	balance_date: function(frm) {
		if (frm.doc.balance_date && !frm.doc.__islocal) {
			// Only auto-refresh ERP data when date changes on saved documents
			refresh_erp_data(frm);
		}
	},
	
	before_save: function(frm) {
		// Calculate totals before saving
		calculate_manual_totals(frm);
	}
});

// Trigger calculation when any manual count/balance field changes
[
	'basic_user_count', 'basic_user_balance',
	'checker_count', 'checker_balance', 
	'accountant_count', 'accountant_balance',
	'super_user_count', 'super_user_balance'
].forEach(fieldname => {
	frappe.ui.form.on('Daily Cash Balance', {
		[fieldname]: function(frm) {
			calculate_manual_totals(frm);
		}
	});
});

function setup_balance_buttons(frm) {
	// Clear existing custom buttons
	frm.custom_buttons && Object.keys(frm.custom_buttons).forEach(key => {
		frm.remove_custom_button(key);
	});
	
	if (frm.doc.docstatus === 0) {
		// Draft document
		frm.add_custom_button(__('Refresh ERP Data'), function() {
			refresh_erp_data(frm);
		}, __('Data')).addClass('btn-info');
		
		if (frm.doc.reconciliation_required && frappe.user.has_role(['Cash Accountant', 'Cash Super User'])) {
			frm.add_custom_button(__('Mark as Reconciled'), function() {
				mark_reconciled_dialog(frm);
			}, __('Actions')).addClass('btn-success');
		}
	}
	
	// Always available buttons
	frm.add_custom_button(__('View Related Documents'), function() {
		view_related_documents(frm);
	}, __('View')).addClass('btn-default');
	
	frm.add_custom_button(__('Variance Details'), function() {
		show_variance_details(frm);
	}, __('Analysis')).addClass('btn-warning');
}

function setup_variance_indicators(frm) {
	if (frm.doc.variance_amount || frm.doc.variance_percentage) {
		let indicator_color = 'green';
		let indicator_text = 'Balanced';
		
		if (Math.abs(frm.doc.variance_amount) > 0) {
			indicator_color = frm.doc.variance_amount > 0 ? 'orange' : 'red';
			indicator_text = `Variance: ${format_currency(frm.doc.variance_amount)}`;
		}
		
		frm.dashboard.add_indicator(__(indicator_text), indicator_color);
		
		if (frm.doc.reconciliation_required) {
			frm.dashboard.add_indicator(__('Reconciliation Required'), 'red');
		}
	}
}

function setup_calculation_triggers(frm) {
	// Set up real-time calculation display
	frm.fields_dict.total_manual_balance.$wrapper.addClass('text-success font-weight-bold');
	frm.fields_dict.variance_amount.$wrapper.addClass('text-warning font-weight-bold');
}

function add_variance_styling(frm) {
	// Add conditional styling to variance fields
	if (frm.doc.variance_amount) {
		let variance_field = frm.fields_dict.variance_amount;
		if (variance_field && variance_field.$wrapper) {
			let color = frm.doc.variance_amount > 0 ? '#ff9f43' : '#ee5a52';
			if (frm.doc.variance_amount === 0) color = '#26de81';
			
			variance_field.$wrapper.find('input').css({
				'background-color': color + '20',
				'border-color': color,
				'color': color,
				'font-weight': 'bold'
			});
		}
	}
}

function calculate_manual_totals(frm) {
	let total_count = 
		(frm.doc.basic_user_count || 0) +
		(frm.doc.checker_count || 0) +
		(frm.doc.accountant_count || 0) +
		(frm.doc.super_user_count || 0);
	
	let total_balance = 
		(frm.doc.basic_user_balance || 0) +
		(frm.doc.checker_balance || 0) +
		(frm.doc.accountant_balance || 0) +
		(frm.doc.super_user_balance || 0);
	
	frm.set_value('total_manual_count', total_count);
	frm.set_value('total_manual_balance', total_balance);
	
	// Calculate variance if ERP data is available
	if (frm.doc.erp_balance !== undefined) {
		let variance_amount = total_balance - (frm.doc.erp_balance || 0);
		let variance_count = total_count - (frm.doc.erp_transaction_count || 0);
		
		frm.set_value('variance_amount', variance_amount);
		frm.set_value('variance_count', variance_count);
		
		// Calculate percentage variance
		if (frm.doc.erp_balance && frm.doc.erp_balance !== 0) {
			let variance_percentage = (variance_amount / frm.doc.erp_balance) * 100;
			frm.set_value('variance_percentage', variance_percentage);
		}
	}
}

function refresh_erp_data(frm) {
	if (!frm.doc.balance_date) {
		frappe.msgprint({
			title: 'Missing Date',
			message: 'Please select a balance date first',
			indicator: 'red'
		});
		return;
	}
	
	// Check if document is saved before calling server method
	if (!frm.doc.name || frm.doc.__islocal) {
		frappe.msgprint({
			title: 'Document Not Saved',
			message: 'Please save the document before refreshing ERP data',
			indicator: 'orange'
		});
		return;
	}
	
	frappe.call({
		method: 'refresh_erp_data',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				frappe.msgprint({
					title: 'Data Refreshed',
					message: r.message,
					indicator: 'green'
				});
				frm.reload_doc();
			}
		}
	});
}

function mark_reconciled_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: 'Mark as Reconciled',
		fields: [
			{
				fieldtype: 'Long Text',
				fieldname: 'reconciliation_notes',
				label: 'Reconciliation Notes',
				description: 'Provide details about how the variance was resolved'
			}
		],
		primary_action: function(values) {
			frappe.call({
				method: 'mark_reconciled',
				doc: frm.doc,
				args: {
					reconciliation_notes: values.reconciliation_notes
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: 'Reconciled',
							message: r.message,
							indicator: 'green'
						});
						frm.reload_doc();
					}
				}
			});
			dialog.hide();
		},
		primary_action_label: 'Mark as Reconciled'
	});
	dialog.show();
}

function view_related_documents(frm) {
	if (!frm.doc.balance_date) {
		frappe.msgprint({
			title: 'Missing Date',
			message: 'Balance date is required',
			indicator: 'red'
		});
		return;
	}
	
	frappe.set_route('List', 'Cash Document', {
		'transaction_date': frm.doc.balance_date
	});
}

function show_variance_details(frm) {
	// Check if document is saved before calling server method
	if (!frm.doc.name || frm.doc.__islocal) {
		frappe.msgprint({
			title: 'Document Not Saved',
			message: 'Please save the document before viewing variance details',
			indicator: 'orange'
		});
		return;
	}
	
	frappe.call({
		method: 'get_variance_details',
		doc: frm.doc,
		callback: function(r) {
			if (r.message) {
				let data = r.message;
				let html = `
					<div class="row">
						<div class="col-md-6">
							<h5>Manual Data</h5>
							<table class="table table-bordered">
								<tr><td>Count</td><td>${data.manual_count || 0}</td></tr>
								<tr><td>Balance</td><td>${format_currency(data.manual_balance || 0)}</td></tr>
							</table>
						</div>
						<div class="col-md-6">
							<h5>ERP Data</h5>
							<table class="table table-bordered">
								<tr><td>Count</td><td>${data.erp_count || 0}</td></tr>
								<tr><td>Balance</td><td>${format_currency(data.erp_balance || 0)}</td></tr>
							</table>
						</div>
					</div>
					<div class="row">
						<div class="col-md-12">
							<h5>Variance Analysis</h5>
							<table class="table table-bordered">
								<tr><td>Count Variance</td><td style="color: ${data.variance_count > 0 ? '#ff9f43' : '#ee5a52'}">${data.variance_count || 0}</td></tr>
								<tr><td>Amount Variance</td><td style="color: ${data.variance_amount > 0 ? '#ff9f43' : '#ee5a52'}">${format_currency(data.variance_amount || 0)}</td></tr>
								<tr><td>Percentage Variance</td><td style="color: ${Math.abs(data.variance_percentage) > 5 ? '#ee5a52' : '#26de81'}">${(data.variance_percentage || 0).toFixed(2)}%</td></tr>
							</table>
						</div>
					</div>
				`;
				
				let dialog = new frappe.ui.Dialog({
					title: 'Variance Analysis Details',
					size: 'large',
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'variance_html',
							options: html
						}
					]
				});
				dialog.show();
			}
		}
	});
}

function format_currency(amount) {
	return frappe.format(amount, {fieldtype: 'Currency'});
}