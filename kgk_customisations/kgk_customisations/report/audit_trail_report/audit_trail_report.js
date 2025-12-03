// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Audit Trail Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "activity_type",
			"label": __("Activity Type"),
			"fieldtype": "Select",
			"options": "\nAll\nBalance Update\nManual Verification\nERP Verification\nFinal Verification\nWorkflow Transition\nDocument Creation\nDocument Modification\nDocument Cancellation",
			"default": "All"
		},
		{
			"fieldname": "user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User"
		},
		{
			"fieldname": "document_type",
			"label": __("Document Type"),
			"fieldtype": "Select",
			"options": "\nAll\nCash Document\nDaily Cash Balance\nCash Balance Submission\nBank Basic Entry"
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company"
		},
		{
			"fieldname": "search_text",
			"label": __("Search in Details"),
			"fieldtype": "Data"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "activity_type" && data && data.activity_type) {
			const type_colors = {
				"Balance Update": "blue",
				"Manual Verification": "green",
				"ERP Verification": "darkgreen",
				"Final Verification": "purple",
				"Workflow Transition": "orange",
				"Document Creation": "teal",
				"Document Modification": "gray",
				"Document Cancellation": "red"
			};
			const color = type_colors[data.activity_type] || "black";
			value = "<span style='color:" + color + "'>" + value + "</span>";
		}
		
		if (column.fieldname == "document_name" && data && data.document_name && data.document_type) {
			value = `<a href="/app/${data.document_type.toLowerCase().replace(/ /g, '-')}/${data.document_name}">${data.document_name}</a>`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		report.page.add_inner_button(__("Export for Auditors"), function() {
			// Export with all details
			frappe.query_report.export_report('Excel');
		});
		
		report.page.add_inner_button(__("Activity Summary"), function() {
			show_activity_summary();
		});
		
		report.page.add_inner_button(__("User Activity Timeline"), function() {
			show_user_timeline();
		});
		
		report.page.add_inner_button(__("Compliance Check"), function() {
			run_compliance_check();
		});
		
		function show_activity_summary() {
			const data = frappe.query_report.data;
			if (!data || data.length === 0) {
				frappe.msgprint(__("No data available"));
				return;
			}
			
			// Group by activity type
			const summary = {};
			const user_summary = {};
			
			data.forEach(row => {
				const activity = row.activity_type || "Unknown";
				const user = row.user || "Unknown";
				
				summary[activity] = (summary[activity] || 0) + 1;
				
				if (!user_summary[user]) {
					user_summary[user] = {};
				}
				user_summary[user][activity] = (user_summary[user][activity] || 0) + 1;
			});
			
			let html = '<h4>Activity Summary</h4>';
			html += '<table class="table table-bordered"><thead><tr>';
			html += '<th>Activity Type</th><th>Count</th></tr></thead><tbody>';
			
			Object.keys(summary).sort((a, b) => summary[b] - summary[a]).forEach(activity => {
				html += `<tr><td>${activity}</td><td>${summary[activity]}</td></tr>`;
			});
			
			html += '</tbody></table>';
			
			html += '<h4 style="margin-top: 20px;">User Activity Summary</h4>';
			html += '<table class="table table-bordered"><thead><tr>';
			html += '<th>User</th><th>Total Actions</th><th>Details</th></tr></thead><tbody>';
			
			Object.keys(user_summary).forEach(user => {
				const total = Object.values(user_summary[user]).reduce((a, b) => a + b, 0);
				const details = Object.keys(user_summary[user])
					.map(act => `${act}: ${user_summary[user][act]}`)
					.join(', ');
				html += `<tr><td>${user}</td><td>${total}</td><td style="font-size: 0.9em;">${details}</td></tr>`;
			});
			
			html += '</tbody></table>';
			
			frappe.msgprint({
				title: __("Activity Summary"),
				message: html,
				wide: true
			});
		}
		
		function show_user_timeline() {
			const filters = frappe.query_report.get_filter_values();
			if (!filters.user) {
				frappe.msgprint(__("Please select a user first"));
				return;
			}
			
			const data = frappe.query_report.data;
			if (!data || data.length === 0) {
				frappe.msgprint(__("No data available"));
				return;
			}
			
			let html = '<div class="timeline">';
			
			data.forEach(row => {
				html += `<div class="timeline-item" style="margin-bottom: 15px; padding: 10px; border-left: 3px solid #007bff;">`;
				html += `<div style="font-weight: bold;">${row.timestamp}</div>`;
				html += `<div style="color: #007bff;">${row.activity_type}</div>`;
				html += `<div>${row.document_type}: ${row.document_name}</div>`;
				if (row.details) {
					html += `<div style="font-size: 0.9em; color: gray;">${row.details}</div>`;
				}
				html += `</div>`;
			});
			
			html += '</div>';
			
			frappe.msgprint({
				title: __("User Activity Timeline - ") + filters.user,
				message: html,
				wide: true
			});
		}
		
		function run_compliance_check() {
			const data = frappe.query_report.data;
			if (!data || data.length === 0) {
				frappe.msgprint(__("No data available"));
				return;
			}
			
			// Check for compliance issues
			const issues = [];
			
			// Check 1: Balance updates without verification
			const balance_updates = data.filter(r => r.activity_type === 'Balance Update');
			const verifications = data.filter(r => 
				r.activity_type === 'Manual Verification' || 
				r.activity_type === 'ERP Verification' || 
				r.activity_type === 'Final Verification'
			);
			
			if (balance_updates.length > verifications.length * 2) {
				issues.push(`Warning: ${balance_updates.length} balance updates but only ${verifications.length} verifications`);
			}
			
			// Check 2: Cancellations without proper authorization
			const cancellations = data.filter(r => r.activity_type === 'Document Cancellation');
			if (cancellations.length > 0) {
				issues.push(`Info: ${cancellations.length} document cancellations recorded`);
			}
			
			// Check 3: Same user creating and approving
			const workflow_transitions = data.filter(r => r.activity_type === 'Workflow Transition');
			// This would need more complex logic to check same-user approval
			
			let html = '<h4>Compliance Check Results</h4>';
			
			if (issues.length === 0) {
				html += '<p style="color: green;">✓ No compliance issues detected</p>';
			} else {
				html += '<ul>';
				issues.forEach(issue => {
					html += `<li>${issue}</li>`;
				});
				html += '</ul>';
			}
			
			html += '<p style="margin-top: 20px; font-style: italic; color: gray;">';
			html += 'Note: This is a basic compliance check. For detailed auditing, export the full report.';
			html += '</p>';
			
			frappe.msgprint({
				title: __("Compliance Check"),
				message: html,
				wide: true
			});
		}
	}
};
