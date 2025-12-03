// Copyright (c) 2025, KGK and contributors
// For license information, please see license.txt

frappe.query_reports["Document Status Dashboard"] = {
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
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company"
		},
		{
			"fieldname": "workflow_state",
			"label": __("Workflow State"),
			"fieldtype": "Select",
			"options": "\nAll\nDraft\nPending Approval\nApproved\nRejected\nRevision Required\nCancelled"
		},
		{
			"fieldname": "assigned_to",
			"label": __("Assigned To"),
			"fieldtype": "Link",
			"options": "User"
		},
		{
			"fieldname": "view_type",
			"label": __("View Type"),
			"fieldtype": "Select",
			"options": "Summary\nDetailed",
			"default": "Summary"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "workflow_state" && data && data.workflow_state) {
			const state_colors = {
				"Draft": "gray",
				"Pending Approval": "orange",
				"Approved": "green",
				"Rejected": "red",
				"Revision Required": "blue",
				"Cancelled": "darkred"
			};
			const color = state_colors[data.workflow_state] || "black";
			value = "<span style='color:" + color + "; font-weight:bold'>" + value + "</span>";
		}
		
		if (column.fieldname == "aging_days" && data && data.aging_days) {
			if (data.aging_days > 7) {
				value = "<span style='color:red; font-weight:bold'>" + value + "</span>";
			} else if (data.aging_days > 3) {
				value = "<span style='color:orange'>" + value + "</span>";
			}
		}
		
		if (column.fieldname == "document_count" && data && data.document_count) {
			if (data.document_count > 100) {
				value = "<span style='font-weight:bold'>" + value + "</span>";
			}
		}
		
		return value;
	},
	
	"onload": function(report) {
		report.page.add_inner_button(__("Show Status Distribution"), function() {
			const chart_data = frappe.query_report.chart_data;
			if (chart_data) {
				frappe.query_report.render_chart();
			}
		});
		
		report.page.add_inner_button(__("Show Aging Chart"), function() {
			show_aging_chart();
		});
		
		report.page.add_inner_button(__("View Pending Approvals"), function() {
			frappe.set_route("List", "Cash Document", {
				"workflow_state": "Pending Approval"
			});
		});
		
		report.page.add_inner_button(__("User Activity Report"), function() {
			show_user_activity_dialog();
		});
		
		function show_aging_chart() {
			const data = frappe.query_report.data;
			if (!data || data.length === 0) {
				frappe.msgprint(__("No data available"));
				return;
			}
			
			// Group data by aging buckets
			const buckets = {
				"0-1 days": 0,
				"2-3 days": 0,
				"4-7 days": 0,
				"8-14 days": 0,
				"15+ days": 0
			};
			
			data.forEach(row => {
				const aging = row.aging_days || 0;
				if (aging <= 1) buckets["0-1 days"]++;
				else if (aging <= 3) buckets["2-3 days"]++;
				else if (aging <= 7) buckets["4-7 days"]++;
				else if (aging <= 14) buckets["8-14 days"]++;
				else buckets["15+ days"]++;
			});
			
			const aging_chart = {
				data: {
					labels: Object.keys(buckets),
					datasets: [{
						name: "Document Count",
						values: Object.values(buckets)
					}]
				},
				type: "bar",
				colors: ["#ff9999"]
			};
			
			frappe.query_report.chart_data = aging_chart;
			frappe.query_report.render_chart();
		}
		
		function show_user_activity_dialog() {
			const data = frappe.query_report.data;
			if (!data || data.length === 0) {
				frappe.msgprint(__("No data available"));
				return;
			}
			
			// Aggregate by user
			const user_stats = {};
			data.forEach(row => {
				const user = row.assigned_to || row.modified_by || "Unassigned";
				if (!user_stats[user]) {
					user_stats[user] = {
						total: 0,
						pending: 0,
						approved: 0,
						rejected: 0
					};
				}
				user_stats[user].total++;
				
				if (row.workflow_state === "Pending Approval") {
					user_stats[user].pending++;
				} else if (row.workflow_state === "Approved") {
					user_stats[user].approved++;
				} else if (row.workflow_state === "Rejected") {
					user_stats[user].rejected++;
				}
			});
			
			// Create HTML table
			let html = '<table class="table table-bordered"><thead><tr>';
			html += '<th>User</th><th>Total</th><th>Pending</th><th>Approved</th><th>Rejected</th>';
			html += '</tr></thead><tbody>';
			
			Object.keys(user_stats).forEach(user => {
				const stats = user_stats[user];
				html += `<tr><td>${user}</td><td>${stats.total}</td><td>${stats.pending}</td>`;
				html += `<td>${stats.approved}</td><td>${stats.rejected}</td></tr>`;
			});
			
			html += '</tbody></table>';
			
			frappe.msgprint({
				title: __("User Activity Summary"),
				message: html,
				wide: true
			});
		}
	}
};
