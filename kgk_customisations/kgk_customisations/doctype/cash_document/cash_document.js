// Copyright (c) 2024, KGK and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Document', {
	refresh: function(frm) {
		// Set up custom buttons based on document status and user role
		setup_custom_buttons(frm);
		
		// Set up file upload area for supporting documents
		setup_file_upload_area(frm);
		
		// Add custom styling
		add_custom_styling(frm);
		
		// Setup party field filter
		setup_party_filter(frm);
		
		// Override save to check for prevent flag
		frm.save = function(save_action, callback) {
			if (frm._prevent_autosave && !save_action) {
				// Prevent auto-save but allow explicit saves
				frappe.show_alert({
					message: __('Auto-save prevented. Please use Save button when ready.'),
					indicator: 'orange'
				}, 3);
				return;
			}
			return frm.__proto__.save.call(frm, save_action, callback);
		};
	},
	
	party_type: function(frm) {
		// Clear party field when party type changes
		frm.set_value('party', '');
		
		// Clear contact number when party type changes
		frm.set_value('contact_number', '');
		
		// Setup party field filter based on selected type
		setup_party_filter(frm);
	},
	
	party: function(frm) {
		// Auto-populate contact number when party is selected
		if (frm.doc.party && frm.doc.party_type) {
			populate_contact_details(frm);
		} else {
			// Clear contact number if no party selected
			frm.set_value('contact_number', '');
		}
	},
	
	transaction_type: function(frm) {
		// Update form layout based on transaction type
		update_transaction_type_layout(frm);
	},
	
	main_document_type: function(frm) {
		// Clear sub_document_type when main_document_type changes
		frm.set_value('sub_document_type', '');
		
		// Set up filter for sub_document_type based on selected main_document_type
		if (frm.doc.main_document_type) {
			frm.set_query('sub_document_type', function() {
				return {
					filters: {
						'main_document_type': frm.doc.main_document_type,
						'is_active': 1
					}
				};
			});
		}
		
		// Update layout based on document type
		update_document_type_layout(frm);
	},
	
	company: function(frm) {
		// Refresh display when company changes
		if (frm.doc.company) {
			frm.refresh_field('company');
		}
	},
	
	amount: function(frm) {
		// Format amount display and validate
		if (frm.doc.amount) {
			if (frm.doc.amount <= 0) {
				frappe.msgprint({
					title: 'Invalid Amount',
					message: 'Amount must be greater than zero',
					indicator: 'red'
				});
				frm.set_value('amount', 0);
			}
		}
	},
	
	transaction_date: function(frm) {
		// Validate transaction date
		if (frm.doc.transaction_date) {
			let today = frappe.datetime.get_today();
			if (frm.doc.transaction_date > today) {
				frappe.msgprint({
					title: 'Future Date',
					message: 'Transaction date cannot be in the future',
					indicator: 'orange'
				});
				frm.set_value('transaction_date', today);
			}
		}
	}
});

frappe.ui.form.on('Cash Document Supporting File', {
	file_attachment: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.file_attachment && !row.file_name) {
			// Auto-set file name from attachment
			let filename = row.file_attachment.split('/').pop();
			frappe.model.set_value(cdt, cdn, 'file_name', filename);
		}
		
		// Prevent auto-save when uploading files in child table
		// This allows users to complete all fields before saving
		frm._prevent_autosave = true;
		setTimeout(() => {
			frm._prevent_autosave = false;
		}, 1000); // Reset after 1 second to allow manual saves
	},
	
	before_save: function(frm, cdt, cdn) {
		// Validate required fields before saving
		let row = locals[cdt][cdn];
		if (!row.file_name) {
			frappe.throw(__('File Name is required'));
		}
		if (!row.file_attachment) {
			frappe.throw(__('File Attachment is required'));
		}
	}
});

function setup_custom_buttons(frm) {
	// Remove existing custom buttons
	frm.custom_buttons && Object.keys(frm.custom_buttons).forEach(key => {
		frm.remove_custom_button(key);
	});
	
	if (frm.doc.docstatus === 1) {
		// Document is submitted
		if (frm.doc.status === 'Approved') {
			frm.add_custom_button(__('Mark as Processed'), function() {
				mark_as_processed(frm);
			}, __('Actions')).addClass('btn-success');
		}
		
		frm.add_custom_button(__('View Related Balance'), function() {
			view_related_balance(frm);
		}, __('View')).addClass('btn-info');
		
	} else if (frm.doc.docstatus === 0) {
		// Draft document
		if (frappe.user.has_role(['Cash Checker', 'Cash Accountant', 'Cash Super User'])) {
			frm.add_custom_button(__('Add Flag'), function() {
				add_flag_dialog(frm);
			}, __('Review')).addClass('btn-warning');
		}
		
		if (frappe.user.has_role(['Cash Accountant', 'Cash Super User'])) {
			frm.add_custom_button(__('Quick Approve'), function() {
				quick_approve(frm);
			}, __('Actions')).addClass('btn-success');
		}
	}
	
	// Always available buttons
	frm.add_custom_button(__('Print Receipt'), function() {
		print_receipt(frm);
	}, __('Print'));
	
	if (frm.doc.supporting_files && frm.doc.supporting_files.length > 0) {
		frm.add_custom_button(__('Download All Files'), function() {
			download_all_files(frm);
		}, __('Files'));
	}
}

function setup_file_upload_area(frm) {
	// Add a custom file upload area if not already present
	if (!frm.fields_dict.supporting_files.grid.wrapper.find('.custom-file-upload').length) {
		let upload_html = `
			<div class="custom-file-upload" style="margin: 10px 0; padding: 15px; border: 2px dashed #d1d8dd; text-align: center; border-radius: 5px;">
				<i class="fa fa-cloud-upload" style="font-size: 24px; color: #8d99a6; margin-bottom: 10px;"></i>
				<p style="margin: 0; color: #8d99a6;">Drag and drop files here or click to upload supporting documents</p>
				<button class="btn btn-sm btn-primary" style="margin-top: 10px;">Browse Files</button>
			</div>
		`;
		
		frm.fields_dict.supporting_files.grid.wrapper.prepend(upload_html);
		
		// Add click handler for file upload
		frm.fields_dict.supporting_files.grid.wrapper.find('.custom-file-upload').click(function() {
			let dialog = new frappe.ui.Dialog({
				title: 'Upload Supporting Document',
				fields: [
					{
						fieldtype: 'Attach',
						fieldname: 'file_attachment',
						label: 'File',
						reqd: 1
					},
					{
						fieldtype: 'Data',
						fieldname: 'file_name',
						label: 'File Name',
						reqd: 1
					},
					{
						fieldtype: 'Select',
						fieldname: 'file_type',
						label: 'File Type',
						options: 'Invoice\nReceipt\nContract\nAgreement\nPhoto\nDocument\nOther'
					},
					{
						fieldtype: 'Small Text',
						fieldname: 'file_description',
						label: 'Description'
					}
				],
				primary_action: function(values) {
					let child = frm.add_child('supporting_files');
					Object.keys(values).forEach(key => {
						child[key] = values[key];
					});
					frm.refresh_field('supporting_files');
					dialog.hide();
				},
				primary_action_label: 'Add File'
			});
			dialog.show();
		});
	}
}

function add_custom_styling(frm) {
	// Add status indicator styling
	if (frm.doc.status) {
		let status_colors = {
			'Draft': '#ff9500',
			'Pending Review': '#ff6b35',
			'Approved': '#98d982',
			'Rejected': '#ff5858',
			'Processed': '#5e64ff'
		};
		
		let status_field = frm.fields_dict.status;
		if (status_field && status_field.$wrapper) {
			status_field.$wrapper.find('select').css({
				'background-color': status_colors[frm.doc.status] || '#f5f5f5',
				'color': 'white',
				'font-weight': 'bold'
			});
		}
	}
	
	// Add transaction type styling
	if (frm.doc.transaction_type) {
		let type_colors = {
			'Payment': '#ff6b6b',
			'Receipt': '#51cf66'
		};
		
		let type_field = frm.fields_dict.transaction_type;
		if (type_field && type_field.$wrapper) {
			type_field.$wrapper.find('select').css({
				'border-left': `4px solid ${type_colors[frm.doc.transaction_type] || '#ddd'}`
			});
		}
	}
}

function setup_party_filter(frm) {
	// Dynamic Link field automatically handles filtering based on party_type
	// No additional filtering needed
	if (frm.doc.party_type) {
		frm.refresh_field('party');
	}
}

function update_transaction_type_layout(frm) {
	// Add visual indicators based on transaction type
	if (frm.doc.transaction_type === 'Payment') {
		frm.dashboard.add_indicator(__('Payment Transaction'), 'red');
	} else if (frm.doc.transaction_type === 'Receipt') {
		frm.dashboard.add_indicator(__('Receipt Transaction'), 'green');
	}
}

function add_flag_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: 'Add Flag to Document',
		fields: [
			{
				fieldtype: 'Select',
				fieldname: 'flag_type',
				label: 'Flag Type',
				options: 'Review Required\nApproved\nRejected\nQuery\nHold\nPriority\nRevision Needed',
				reqd: 1
			},
			{
				fieldtype: 'Long Text',
				fieldname: 'comments',
				label: 'Comments',
				reqd: 1
			}
		],
		primary_action: function(values) {
			frm.call({
				method: 'add_flag',
				args: {
					flag_type: values.flag_type,
					comments: values.comments
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: 'Flag Added',
							message: 'Flag has been added successfully',
							indicator: 'green'
						});
						frm.reload_doc();
					}
				}
			});
			dialog.hide();
		},
		primary_action_label: 'Add Flag'
	});
	dialog.show();
}

function quick_approve(frm) {
	frappe.confirm(
		'Are you sure you want to approve this cash document?',
		function() {
			frm.call({
				method: 'add_flag',
				args: {
					flag_type: 'Approved',
					comments: 'Quick approval by ' + frappe.user.full_name()
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: 'Document Approved',
							message: 'Document has been approved successfully',
							indicator: 'green'
						});
						frm.reload_doc();
					}
				}
			});
		}
	);
}

function mark_as_processed(frm) {
	frappe.confirm(
		'Mark this document as processed?',
		function() {
			frm.set_value('status', 'Processed');
			frm.save();
		}
	);
}

function view_related_balance(frm) {
	frappe.set_route('List', 'Daily Cash Balance', {
		'balance_date': frm.doc.transaction_date
	});
}

function print_receipt(frm) {
	frappe.utils.print(
		frm.doctype,
		frm.docname,
		'Cash Document Receipt',
		frm.doc.language
	);
}

function download_all_files(frm) {
	if (frm.doc.supporting_files && frm.doc.supporting_files.length > 0) {
		frm.doc.supporting_files.forEach(file => {
			if (file.file_attachment) {
				window.open(file.file_attachment, '_blank');
			}
		});
	}
}

function populate_contact_details(frm) {
	// Auto-populate contact number from selected party
	if (!frm.doc.party || !frm.doc.party_type) {
		return;
	}
	
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: frm.doc.party_type,
			name: frm.doc.party
		},
		callback: function(r) {
			if (r.message) {
				let party_doc = r.message;
				
				// For Customer
				if (frm.doc.party_type === 'Customer') {
					// Try to get primary contact person
					if (party_doc.customer_primary_contact) {
						frappe.call({
							method: 'frappe.client.get',
							args: {
								doctype: 'Contact',
								name: party_doc.customer_primary_contact
							},
							callback: function(contact_r) {
								if (contact_r.message) {
									let contact = contact_r.message;
									// Get phone number from contact
									if (contact.phone_nos && contact.phone_nos.length > 0) {
										frm.set_value('contact_number', contact.phone_nos[0].phone);
									} else if (contact.mobile_no) {
										frm.set_value('contact_number', contact.mobile_no);
									}
								}
							}
						});
					} else {
						// Try to find any contact linked to this customer
						frappe.call({
							method: 'frappe.client.get_list',
							args: {
								doctype: 'Contact',
								filters: [
									['Dynamic Link', 'link_doctype', '=', 'Customer'],
									['Dynamic Link', 'link_name', '=', frm.doc.party]
								],
								fields: ['name', 'mobile_no', 'phone']
							},
							callback: function(contacts_r) {
								if (contacts_r.message && contacts_r.message.length > 0) {
									let contact = contacts_r.message[0];
									frm.set_value('contact_number', contact.mobile_no || contact.phone || '');
								}
							}
						});
					}
				}
				
				// For Supplier
				else if (frm.doc.party_type === 'Supplier') {
					// Try to find contact linked to this supplier
					frappe.call({
						method: 'frappe.client.get_list',
						args: {
							doctype: 'Contact',
							filters: [
								['Dynamic Link', 'link_doctype', '=', 'Supplier'],
								['Dynamic Link', 'link_name', '=', frm.doc.party]
							],
							fields: ['name', 'mobile_no', 'phone']
						},
						callback: function(contacts_r) {
							if (contacts_r.message && contacts_r.message.length > 0) {
								let contact = contacts_r.message[0];
								frm.set_value('contact_number', contact.mobile_no || contact.phone || '');
							}
						}
					});
				}
				
				// For Employee
				else if (frm.doc.party_type === 'Employee') {
					frm.set_value('contact_number', party_doc.cell_number || party_doc.personal_mobile || '');
				}
			}
		}
	});
}
function update_document_type_layout(frm) {
// Update form layout based on main_document_type selection
if (!frm.doc.main_document_type) {
return;
}

// Show/hide fields based on document type
let show_party = ['Payment', 'Receipt', 'Invoice'].includes(frm.doc.main_document_type);
frm.toggle_display('section_break_6', show_party);

// Set field labels based on document type
if (frm.doc.main_document_type === 'Invoice') {
frm.set_df_property('amount', 'label', 'Invoice Amount');
frm.set_df_property('description', 'label', 'Invoice Description');
} else if (frm.doc.main_document_type === 'Payment') {
frm.set_df_property('amount', 'label', 'Payment Amount');
frm.set_df_property('description', 'label', 'Payment Description');
} else if (frm.doc.main_document_type === 'Receipt') {
frm.set_df_property('amount', 'label', 'Receipt Amount');
frm.set_df_property('description', 'label', 'Receipt Description');
} else {
frm.set_df_property('amount', 'label', 'Amount');
frm.set_df_property('description', 'label', 'Description');
}

frm.refresh_fields();
}
