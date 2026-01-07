// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Grading Repairs Report"] = {
	"filters": [
		{
			"fieldname": "week",
			"label": __("Week"),
			"fieldtype": "Select",
			"options": ["Week 1", "Week 2", "Week 3", "Week 4"],
			"default": "Week 1",
			"reqd": 1
		},
		{
			"fieldname": "chart_view",
			"label": __("Chart View"),
			"fieldtype": "Select",
			"options": [
				"Monthly Trend (Line)",
				"Monthly Trend (Bar)",
				"Characteristics Comparison",
				"Week-by-Week Comparison",
				"Top/Bottom Performers",
				"Percentage Distribution (Pie)"
			],
			"default": "Monthly Trend (Line)"
		}
	]
};
