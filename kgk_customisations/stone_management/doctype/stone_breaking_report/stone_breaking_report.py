# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today, getdate
from datetime import date


class StoneBreakingReport(Document):
	pass


@frappe.whitelist()
def get_breaking_summary(department, current_doc_name=None):
	"""
	Return department-level and per-worker aggregated breaking summary.
	Only considers submitted documents (docstatus=1).
	Uses the document 'date' field (not creation) for period filtering.
	Returns all data in a single call (no N+1).
	"""
	if not department:
		return {}

	today_date = getdate(today())
	current_month_start = date(today_date.year, today_date.month, 1)

	# Financial year starts in April
	fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
	fy_start_date = date(fy_start_year, 4, 1)

	# Fetch all submitted reports in this department within current FY
	filters = {
		"docstatus": 1,
		"department": department,
		"date": [">=", str(fy_start_date)],
	}
	if current_doc_name:
		filters["name"] = ["!=", current_doc_name]

	records = frappe.get_all(
		"Stone Breaking Report",
		filters=filters,
		fields=["name", "breaking_amount", "org_plan_value", "stone_fault", "worker_fault", "date"],
	)

	# Department-level summaries
	month_stone = {"breaking_amount": 0, "org_plan_value": 0}
	month_worker = {"breaking_amount": 0, "org_plan_value": 0}
	year_stone = {"breaking_amount": 0, "org_plan_value": 0}
	year_worker = {"breaking_amount": 0, "org_plan_value": 0}

	record_names = []
	record_map = {}

	for rec in records:
		rec_date = getdate(rec.date) if rec.date else None
		if not rec_date:
			continue

		ba = flt(rec.breaking_amount)
		opv = flt(rec.org_plan_value)
		is_stone = rec.stone_fault
		is_month = rec_date >= current_month_start

		# Year bucket (all records are already filtered >= fy_start_date)
		if is_stone:
			year_stone["breaking_amount"] += ba
			year_stone["org_plan_value"] += opv
		else:
			year_worker["breaking_amount"] += ba
			year_worker["org_plan_value"] += opv

		# Month bucket
		if is_month:
			if is_stone:
				month_stone["breaking_amount"] += ba
				month_stone["org_plan_value"] += opv
			else:
				month_worker["breaking_amount"] += ba
				month_worker["org_plan_value"] += opv

		record_names.append(rec.name)
		record_map[rec.name] = {
			"org_plan_value": opv,
			"date": rec_date,
			"is_month": is_month,
		}

	# Fetch all worker child rows in one query
	worker_stats = {}
	if record_names:
		worker_rows = frappe.get_all(
			"Stone Breaking Worker",
			filters={"parent": ["in", record_names], "parenttype": "Stone Breaking Report"},
			fields=["parent", "employee_code", "worker_name", "breaking_amount"],
		)
		for row in worker_rows:
			code = row.employee_code
			if not code:
				continue
			if code not in worker_stats:
				worker_stats[code] = {
					"employee_code": code,
					"worker_name": row.worker_name or "",
					"month": {"breaking_amount": 0, "org_plan_value": 0},
					"ytd": {"breaking_amount": 0, "org_plan_value": 0},
				}
			parent_info = record_map.get(row.parent)
			if not parent_info:
				continue
			ba = flt(row.breaking_amount)
			opv = parent_info["org_plan_value"]

			# YTD (all records are within FY)
			worker_stats[code]["ytd"]["breaking_amount"] += ba
			worker_stats[code]["ytd"]["org_plan_value"] += opv

			# Month
			if parent_info["is_month"]:
				worker_stats[code]["month"]["breaking_amount"] += ba
				worker_stats[code]["month"]["org_plan_value"] += opv

	# Calculate percentages
	def calc_pct(bucket):
		if bucket["org_plan_value"] > 0:
			bucket["breaking_percentage"] = (bucket["breaking_amount"] / bucket["org_plan_value"]) * 100
		else:
			bucket["breaking_percentage"] = 0

	calc_pct(month_stone)
	calc_pct(month_worker)
	calc_pct(year_stone)
	calc_pct(year_worker)
	for ws in worker_stats.values():
		calc_pct(ws["month"])
		calc_pct(ws["ytd"])

	return {
		"currentMonth": {
			"stoneFault": month_stone,
			"workerFault": month_worker,
		},
		"currentYear": {
			"stoneFault": year_stone,
			"workerFault": year_worker,
		},
		"workers": worker_stats,
	}

	

