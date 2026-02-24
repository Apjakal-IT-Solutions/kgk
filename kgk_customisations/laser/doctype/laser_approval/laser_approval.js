// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Laser Approval", {
	onload_post_render(frm) {
		// Prepopulate document_users table on new document creation ONLY
		if (frm.is_new() && (!frm.doc.document_users || frm.doc.document_users.length === 0)) {
			prepopulate_users(frm);

            // Generate a unique alphanumeric serial number for the new document
            const uniqueSerialNumber = 'LA-' + Math.random().toString(36).substr(2, 9).toUpperCase();
            frm.set_value('serial_number', uniqueSerialNumber);
			frm.set_df_property('remarks', 'reqd', true);		
		}
	},
	
	refresh(frm) {
		// Add button to manually repopulate users if needed
		if (!frm.is_new()) {
			frm.add_custom_button(__('Refresh User List'), function() {
				frappe.confirm(
					'This will replace the current user list with all users from Laser Approval User Item. Continue?',
					function() {
						prepopulate_users(frm, true);
					}
				);
			}, __('Actions'));
		}
		
		// Highlight sections and fields
		setTimeout(() => {
			// Highlight Document Approval Section - Light yellow background
			$('[data-fieldname="document_approval_section"]').closest('.form-section').css({
				'background-color': 'rgba(245, 242, 221, 0.3)',
				'padding': '15px',
				'border-radius': '5px',
				'margin': '10px 0',
				'border': '4px solid #f8e7b3'
			});
            $('[data-fieldname="results_section"]').closest('.form-section').css({
				'background-color': 'rgba(245, 242, 221, 0.3)',
				'padding': '15px',
				'border-radius': '5px',
				'margin': '10px 0',
				'border': '4px solid #f8e7b3'
			});
			
			// For editable fields
			frm.fields_dict['org_plan_value'].$wrapper.find('.control-input').css({
				'background-color': '#9edbf7',
				'border': '1px solid #2196f3',
				'border-radius': '1px'
			});
            frm.fields_dict['org_lot_id'].$wrapper.find('.control-input').css({
				'background-color': '#9edbf7',
				'border': '2px solid #000',
				'border-radius': '2px'
			});
			
			frm.fields_dict['revised_value'].$wrapper.find('.control-input').css({
				'background-color': '#fff',
				'border': '1px solid #2196f3',
				'border-radius': '1px',
				'color': '#2196f3 !important'
			});
						
			frm.fields_dict['safe_sawing_amount'].$wrapper.find('.control-input').css({
				'background-color': '#9edbf7',
				'border': '2px solid #2196f3',
				'border-radius': '2px'
			});			
			
            frm.fields_dict['safe_sawing_percent'].$wrapper.find('.control-input, .control-value').css({
                'background-color': '#9edbf7',
                'border': '2px solid rgba(33, 150, 243, 0.3)',
                'border-radius': '2px',
                'font-weight': 'bold',
                'color': '#000'
            });

			// Purple section - readonly fields
			frm.fields_dict['revised_value_no_ls'].$wrapper.find('.control-input').css({
				'background-color': '#f3e5f5',
				'border': '1px solid #9c27b0',
				'border-radius': '1px'
			});
			
			frm.fields_dict['nols_amount'].$wrapper.find('.control-input').css({
				'background-color': '#f3e5f5',
				'border': '2px solid #9c27b0',
				'border-radius': '2px'
			});
            
            frm.fields_dict['nols_percent'].$wrapper.find('.control-input, .control-value').css({
                'background-color': '#f3e5f5',
                'border': '2px solid #9c27b0',
                'border-radius': '2px',
                'font-weight': 'bold',
                'color': '#000'
            });
			
			frm.fields_dict['tension_type'].$wrapper.find('.control-input').css({
				'background-color': '#f3e5f5',
				'border': '2px solid #96360a',
				'border-radius': '4px'
			});
		}, 500);
	},

    org_plan_value: function(frm) {
        if(frm.doc.org_plan_value && frm.doc.revised_value){
            frm.set_value("safe_sawing_amount", (frm.doc.org_plan_value - frm.doc.revised_value));
        }
    },
    
    micron_safe: function(frm) {
        if(frm.doc.micron_safe && (frm.doc.micron_safe < 20 || frm.doc.micron_safe > 1000)){
            frappe.msgprint(__('Micron Safe value must be between 20 and 1000'));
            frm.set_value('micron_safe', null);
        }
    }, 

    safe_sawing_amount: function(frm) {
        if(frm.doc.safe_sawing_amount && frm.doc.org_plan_value && frm.doc.org_plan_value > 0){
            frm.set_value("safe_sawing_percent", (frm.doc.safe_sawing_amount / frm.doc.org_plan_value) * 100);
            frm.set_value("revised_value", (frm.doc.org_plan_value - frm.doc.safe_sawing_amount))
        }
        else{
            frm.set_value("safe_sawing_percent", 0);
            frm.set_value("revised_value", 0);
        }
    }, 
    tension_type: function(frm) {
        if(frm.doc.tension_type != "T4" && frm.doc.tension_type != "T5"){
            frm.set_df_property('remarks', 'reqd', true);
        }
        else{
            frm.set_df_property('remarks', 'reqd', false);
        }   
    }, 

    nols_amount: function(frm) {
        if(frm.doc.org_plan_value && frm.doc.org_plan_value && frm.doc.org_plan_value > 0){
            frm.set_value("nols_percent", (frm.doc.nols_amount / frm.doc.org_plan_value) * 100);
            frm.set_value("revised_value_no_ls", (frm.doc.org_plan_value - frm.doc.nols_amount));

            frm.fields_dict['nols_percent'].$wrapper.find('.control-input').css({
				'background-color': '#f3e5f5',
				'border': '2px solid #9c27b0',
				'border-radius': '4px'
			});
        }
        else{
            frm.set_value("nols_percent", 0);
            frm.set_value("revised_value_no_ls", 0);
        }
    }, 

    approval_remark: function(frm){
        if(frm.doc.approval_remark){
            frm.set_value("checked_", true);
            frm.set_value("approval_date", frappe.datetime.nowdate());
        }
        else{            
            frm.set_value("checked_", false);
        }
    },
	
	// Button click handlers for opening video files
	open_rough_video: function(frm) {
		if (frm.doc.rough_video) {
			open_video_file(frm.doc.name, 'rough', 'Rough Video');
		} else {
			frappe.msgprint(__('No rough video path available'));
		}
	},
	
	open_polish_video: function(frm) {
		if (frm.doc.polish_video) {
			open_video_file(frm.doc.name, 'polish', 'Polish Video');
		} else {
			frappe.msgprint(__('No polish video path available'));
		}
	},
	
	open_tension_video: function(frm) {
		if (frm.doc.tension_video) {
			open_video_file(frm.doc.name, 'tension', 'Tension Video');
		} else {
			frappe.msgprint(__('No tension video path available'));
		}
	}
});

// Child table event handler for Packet Scan Item
frappe.ui.form.on("Packet Scan Item", {
	open_file: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.image_path && row.name) {
			open_packet_scan_file(frm.doc.name, row.name);
		} else {
			frappe.msgprint(__('No file path available for this scan'));
		}
	}
});

function prepopulate_users(frm, clear_existing = false) {
	// Fetch all users from Laser Approval User Item
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Laser Approval User Item',
			fields: ['name', 'full_name'],
			order_by: 'full_name asc',
			limit_page_length: 0  // Get all records
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				if (clear_existing) {
					// Clear existing rows
					frm.clear_table('document_users');
				}
				
				// Add each user to the child table
				r.message.forEach(function(user) {
					let row = frm.add_child('document_users');
					row.employee_name = user.name;
					row.status = 'No';  // Default status
				});
				
				frm.refresh_field('document_users');
				frappe.show_alert({
					message: __('Added {0} users to the list', [r.message.length]),
					indicator: 'green'
				}, 5);
			} else {
				frappe.msgprint(__('No users found in Laser Approval User Item'));
			}
		}
	});
}

function open_video_file(docname, video_type, file_type) {
	// Build URL to server-side method that will serve the file
	let url = `/api/method/kgk_customisations.kgk_customisations.doctype.laser_approval.laser_approval.serve_video_file?docname=${encodeURIComponent(docname)}&video_type=${video_type}`;
	
	// Open in new tab - video will play in browser
	window.open(url, '_blank');

	frappe.show_alert({
		message: __('Opening {0}...', [file_type]),
		indicator: 'blue'
	}, 2);
}

function open_packet_scan_file(docname, row_id) {
	// Build URL to server-side method that will serve the packet scan file
	let url = `/api/method/kgk_customisations.kgk_customisations.doctype.laser_approval.laser_approval.serve_packet_scan_file?docname=${encodeURIComponent(docname)}&row_id=${encodeURIComponent(row_id)}`;
	
	// Open in new tab - file will display in browser (PDF, image, etc.)
	window.open(url, '_blank');

	frappe.show_alert({
		message: __('Opening packet scan file...'),
		indicator: 'blue'
	}, 2);
}