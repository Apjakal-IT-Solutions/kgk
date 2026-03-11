# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
import re
from frappe.model.document import Document
from frappe.utils import flt, today, getdate
from datetime import date


def get_base_lot_id(name):
	"""Strip the -b, -c, …, -z, -aa, -ab, … suffix to get the original lot ID."""
	return re.sub(r'-[a-z]+$', '', name)


def _next_suffix(existing_suffixes):
	"""Given a set of existing letter suffixes (e.g. {'b','c'}), return the next one."""
	# Generate a, b, c, …, z, aa, ab, …
	idx = 0
	while True:
		# Convert idx to base-26 letter string (0→a, 1→b, …, 25→z, 26→aa, …)
		n = idx
		suffix = ""
		while True:
			suffix = chr(ord('a') + (n % 26)) + suffix
			n = n // 26 - 1
			if n < 0:
				break
		# First doc has no suffix; second starts at 'b' (idx=1)
		if idx >= 1 and suffix not in existing_suffixes:
			return suffix
		idx += 1


class StoneBreakingReport(Document):
	def autoname(self):
		lot_id = self.org_lot_id
		if not lot_id:
			return  # let the format: expression handle it (will fail gracefully)

		if not frappe.db.exists("Stone Breaking Report", lot_id):
			self.name = lot_id
			return

		existing = frappe.get_all(
			"Stone Breaking Report",
			filters={"name": ["like", f"{lot_id}-%"]},
			pluck="name",
		)
		existing_suffixes = set()
		for n in existing:
			m = re.search(r'-([a-z]+)$', n)
			if m:
				existing_suffixes.add(m.group(1))

		self.name = f"{lot_id}-{_next_suffix(existing_suffixes)}"

	def before_print(self, print_settings=None):
		try:
			self.breaking_report_html = self._build_breaking_report_html()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "StoneBreakingReport.before_print")
			self.breaking_report_html = "<p style='color:red'>Breaking summary could not be computed.</p>"

	def _build_breaking_report_html(self):
		from datetime import date as date_cls

		summary = get_breaking_summary(department=self.department, current_doc_name=self.name)
		if not summary:
			summary = {
				"currentMonth": {"stoneFault": {}, "workerFault": {}},
				"currentYear": {"stoneFault": {}, "workerFault": {}},
				"workers": {},
				"counted_lots": {"year": [], "month": [], "worker_year": {}, "worker_month": {}},
			}

		counted_lots = summary.get("counted_lots", {})
		seen_lot_year = set(counted_lots.get("year", []))
		seen_lot_month = set(counted_lots.get("month", []))
		worker_seen_year = {k: set(v) for k, v in counted_lots.get("worker_year", {}).items()}
		worker_seen_month = {k: set(v) for k, v in counted_lots.get("worker_month", {}).items()}

		ba = flt(self.breaking_amount)
		opv = flt(self.org_plan_value)

		if ba and opv:
			doc_date = getdate(self.date) if self.date else getdate(today())
			today_date = getdate(today())
			current_month_start = date_cls(today_date.year, today_date.month, 1)
			fy_start_year = today_date.year if today_date.month >= 4 else today_date.year - 1
			fy_start_date = date_cls(fy_start_year, 4, 1)
			is_month = doc_date >= current_month_start
			is_fy = doc_date >= fy_start_date
			bucket = "stoneFault" if self.stone_fault else "workerFault"
			base_lot = get_base_lot_id(self.name)

			for period_key, condition, seen_set in [
				("currentMonth", is_month, seen_lot_month),
				("currentYear", is_fy, seen_lot_year),
			]:
				if condition:
					b = summary[period_key][bucket]
					b["breaking_amount"] = flt(b.get("breaking_amount", 0)) + ba
					if base_lot not in seen_set:
						seen_set.add(base_lot)
						b["org_plan_value"] = flt(b.get("org_plan_value", 0)) + opv

			for worker in self.article_workers or []:
				code = worker.employee_code
				if not code:
					continue
				if code not in summary["workers"]:
					summary["workers"][code] = {
						"employee_code": code,
						"worker_name": worker.worker_name or "",
						"month": {"breaking_amount": 0, "org_plan_value": 0, "breaking_percentage": 0},
						"ytd": {"breaking_amount": 0, "org_plan_value": 0, "breaking_percentage": 0},
					}
					worker_seen_year[code] = set()
					worker_seen_month[code] = set()
				if code not in worker_seen_year:
					worker_seen_year[code] = set()
				if code not in worker_seen_month:
					worker_seen_month[code] = set()

				w_ba = flt(worker.breaking_amount)
				if is_month:
					summary["workers"][code]["month"]["breaking_amount"] += w_ba
					if base_lot not in worker_seen_month[code]:
						worker_seen_month[code].add(base_lot)
						summary["workers"][code]["month"]["org_plan_value"] += opv
				if is_fy:
					summary["workers"][code]["ytd"]["breaking_amount"] += w_ba
					if base_lot not in worker_seen_year[code]:
						worker_seen_year[code].add(base_lot)
						summary["workers"][code]["ytd"]["org_plan_value"] += opv

			def calc_pct(b):
				opv_val = flt(b.get("org_plan_value", 0))
				b["breaking_percentage"] = (flt(b.get("breaking_amount", 0)) / opv_val * 100) if opv_val else 0

			for period in ["currentMonth", "currentYear"]:
				for fault in ["stoneFault", "workerFault"]:
					calc_pct(summary[period][fault])
			for w in summary["workers"].values():
				calc_pct(w["month"])
				calc_pct(w["ytd"])

		return self._render_summary_html(summary)

	def _render_summary_html(self, summary):
		def fmt(v):
			return f"{flt(v):.2f}"

		def fmt_pct(v):
			return f"{flt(v):.2f}%"

		dept = self.department or "Dept."
		cm = summary.get("currentMonth", {})
		cy = summary.get("currentYear", {})

		def summary_rows(label, period):
			stone = period.get("stoneFault", {})
			worker = period.get("workerFault", {})
			total_ba = flt(stone.get("breaking_amount", 0)) + flt(worker.get("breaking_amount", 0))
			total_opv = flt(stone.get("org_plan_value", 0)) + flt(worker.get("org_plan_value", 0))
			total_pct = (total_ba / total_opv * 100) if total_opv else 0
			return f"""
		<tr style="border-bottom: 1px solid #ebeff2;">
			<td style="padding: 10px; color: #444; vertical-align: top;">
				<div style="font-weight: bold; margin-bottom: 5px;">{label}</div>
				<div>Stone</div><div>Worker</div><div>Total</div>
			</td>
			<td style="padding: 10px; color: #444; vertical-align: top;">
				<div style="height: 22px;"></div>
				<div>{fmt(stone.get("breaking_amount", 0))}</div>
				<div>{fmt(worker.get("breaking_amount", 0))}</div>
				<div>{fmt(total_ba)}</div>
			</td>
			<td style="padding: 10px; color: #444; vertical-align: top;">
				<div style="height: 22px;"></div>
				<div>{fmt(stone.get("org_plan_value", 0))}</div>
				<div>{fmt(worker.get("org_plan_value", 0))}</div>
				<div>{fmt(total_opv)}</div>
			</td>
			<td style="padding: 10px; color: #444; vertical-align: top;">
				<div style="height: 22px;"></div>
				<div>{fmt_pct(stone.get("breaking_percentage", 0))}</div>
				<div>{fmt_pct(worker.get("breaking_percentage", 0))}</div>
				<div>{fmt_pct(total_pct)}</div>
			</td>
		</tr>"""

		workers = summary.get("workers", {})
		current_codes = [w.employee_code for w in (self.article_workers or []) if w.employee_code]

		def worker_section(period_key, label):
			rows = f"""<tr style="border-bottom: 1px solid #ebeff2;">
			<td colspan="4" style="padding: 10px; color: #444; font-weight: bold;">{label}</td>
		</tr>"""
			has_any = False
			for code in current_codes:
				w = workers.get(code)
				if not w:
					continue
				has_any = True
				period = w.get(period_key, {})
				name_label = f"{w.get('worker_name', '')} ({code})" if w.get("worker_name") else code
				rows += f"""<tr style="border-bottom: 1px solid #ebeff2;">
				<td style="padding: 10px 10px 10px 20px; color: #444;">{name_label}</td>
				<td style="padding: 10px; color: #444;">{fmt(period.get("breaking_amount", 0))}</td>
				<td style="padding: 10px; color: #444;">{fmt(period.get("org_plan_value", 0))}</td>
				<td style="padding: 10px; color: #444;">{fmt_pct(period.get("breaking_percentage", 0))}</td>
			</tr>"""
			if not has_any:
				rows += """<tr><td colspan="4" style="padding: 10px; text-align: center; color: #999;">No worker data available</td></tr>"""
			return rows

		return f"""<table style="width: 100%; border-collapse: collapse; margin: 10px 0; font-family: sans-serif;">
	<thead>
		<tr style="background-color: #f8f9fa; border-bottom: 2px solid #d1d8dd;">
			<th style="padding: 12px; text-align: left; color: #800000;">{dept}</th>
			<th style="padding: 12px; text-align: left; color: #800000;">Breaking amnt.</th>
			<th style="padding: 12px; text-align: left; color: #800000;">Org amnt.</th>
			<th style="padding: 12px; text-align: left; color: #800000;">Breaking %</th>
		</tr>
	</thead>
	<tbody>
		{summary_rows("Month", cm)}
		{summary_rows("Year To Date", cy)}
		<tr style="background-color: #f8f9fa; border-bottom: 2px solid #d1d8dd;">
			<th style="padding: 10px; color: #800000;">Employee</th>
			<th style="padding: 10px; color: #800000;">Breaking Amnt.</th>
			<th style="padding: 10px; color: #800000;">Org Amnt.</th>
			<th style="padding: 10px; color: #800000;">Breaking %</th>
		</tr>
		{worker_section("month", "Month")}
		{worker_section("ytd", "Year To Date")}
	</tbody>
</table>"""


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

	# Track which base lot IDs have already contributed org_plan_value
	seen_lot_year = set()
	seen_lot_month = set()

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
		base_lot = get_base_lot_id(rec.name)

		# Year bucket — only count org_plan_value once per lot
		lot_new_year = base_lot not in seen_lot_year
		if lot_new_year:
			seen_lot_year.add(base_lot)
		if is_stone:
			year_stone["breaking_amount"] += ba
			if lot_new_year:
				year_stone["org_plan_value"] += opv
		else:
			year_worker["breaking_amount"] += ba
			if lot_new_year:
				year_worker["org_plan_value"] += opv

		# Month bucket — only count org_plan_value once per lot
		if is_month:
			lot_new_month = base_lot not in seen_lot_month
			if lot_new_month:
				seen_lot_month.add(base_lot)
			if is_stone:
				month_stone["breaking_amount"] += ba
				if lot_new_month:
					month_stone["org_plan_value"] += opv
			else:
				month_worker["breaking_amount"] += ba
				if lot_new_month:
					month_worker["org_plan_value"] += opv

		record_names.append(rec.name)
		record_map[rec.name] = {
			"org_plan_value": opv,
			"date": rec_date,
			"is_month": is_month,
			"base_lot": base_lot,
		}

	# Fetch all worker child rows in one query
	worker_stats = {}
	# Per-worker tracking of which base lots have contributed org_plan_value
	worker_seen_lot_year = {}   # code -> set of base_lot
	worker_seen_lot_month = {}  # code -> set of base_lot
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
				worker_seen_lot_year[code] = set()
				worker_seen_lot_month[code] = set()
			parent_info = record_map.get(row.parent)
			if not parent_info:
				continue
			ba = flt(row.breaking_amount)
			opv = parent_info["org_plan_value"]
			base_lot = parent_info["base_lot"]

			# YTD — only count org_plan_value once per lot per worker
			worker_stats[code]["ytd"]["breaking_amount"] += ba
			if base_lot not in worker_seen_lot_year[code]:
				worker_seen_lot_year[code].add(base_lot)
				worker_stats[code]["ytd"]["org_plan_value"] += opv

			# Month
			if parent_info["is_month"]:
				worker_stats[code]["month"]["breaking_amount"] += ba
				if base_lot not in worker_seen_lot_month[code]:
					worker_seen_lot_month[code].add(base_lot)
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
		"counted_lots": {
			"year": list(seen_lot_year),
			"month": list(seen_lot_month),
			"worker_year": {code: list(lots) for code, lots in worker_seen_lot_year.items()},
			"worker_month": {code: list(lots) for code, lots in worker_seen_lot_month.items()},
		},
	}

	

