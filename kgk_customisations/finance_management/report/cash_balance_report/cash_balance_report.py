# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from kgk_customisations.finance_management.doctype.cash_balance.cash_balance import COMPANY_MAP, _load_aggregates

_COMPANIES  = ["Diamonds", "Jewellery", "Agro"]
_CURRENCIES = ["USD", "ZAR", "BWP"]

_CHECKER_MAP = {
	"Hitesh": "hitesh.khandelwal@kgkmail.com",
	"Dipak":  "dipak.botare@kgkmail.com",
}


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns(filters)
	data    = _get_data(filters)
	return columns, data


def _get_columns(filters=None):
	filters   = filters or {}
	company   = filters.get("company")  or ""
	currency  = filters.get("currency") or ""

	companies  = [company]  if company  and company  != "All" else _COMPANIES
	currencies = [currency] if currency and currency != "All" else _CURRENCIES

	cols = [{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 110}]

	for comp in companies:
		for curr in currencies:
			prefix    = "{}_{}".format(comp.lower(), curr.lower())
			group     = "{} / {}".format(comp, curr)
			tally_fld = "{}_tally".format(prefix)
			for fname, label in [
				("basic",      "Cebo"),
				("accountant", "Lore"),
				("checker",    "Harsh"),
				("hitesh",     "Hitesh"),
				("dipak",      "Dipak"),
			]:
				cols.append({
					"fieldname":   "{}_{}".format(prefix, fname),
					"label":       label,
					"fieldtype":   "Currency",
					"width":       120,
					"group":       group,
					"tally_field": tally_fld,
				})
			cols.append({
				"fieldname": tally_fld,
				"label":     "Match",
				"fieldtype": "Int",
				"hidden":    1,
			})

	return cols


def _get_data(filters):
	date_from = filters.get("date_from")
	date_to   = filters.get("date_to")
	company   = filters.get("company")  or ""
	currency  = filters.get("currency") or ""

	if not date_from or not date_to:
		return []

	companies  = [company]  if company  and company  != "All" else _COMPANIES
	currencies = [currency] if currency and currency != "All" else _CURRENCIES

	# Build permutation descriptors: (short_company, currency, prefix, full_company)
	perms = [
		(comp, curr,
		 "{}_{}".format(comp.lower(), curr.lower()),
		 COMPANY_MAP.get(comp, comp))
		for comp in companies for curr in currencies
	]

	user_roles = frappe.get_roles(frappe.session.user)
	is_restricted_checker = (
		"Cash Checker" in user_roles
		and "Cash Super User" not in user_roles
		and frappe.session.user != "Administrator"
	)
	current_user = frappe.session.user

	agg = _load_aggregates(date_from=date_from, date_to=date_to, balance_type="Cash")

	# Collect all relevant dates across all permutations
	all_dates = set()
	for comp, curr, prefix, full_co in perms:
		ck = "{}_{}".format(comp, curr)
		for (d, bt, key), vals in agg.items():
			if bt == "Cash" and key == ck and (
				abs(flt(vals.get("basic"))) > 1e-6 or abs(flt(vals.get("accountant"))) > 1e-6
			):
				all_dates.add(str(d))
		bb = frappe.db.sql(
			"SELECT DISTINCT date FROM `tabBank Balance Entry`"
			" WHERE company = %s AND currency = %s AND date BETWEEN %s AND %s",
			[full_co, curr, date_from, date_to],
		)
		all_dates.update(str(r[0]) for r in bb)

	data = []
	for date_str in sorted(all_dates):
		row      = {"date": date_str}
		has_data = False

		for comp, curr, prefix, full_co in perms:
			ck   = "{}_{}".format(comp, curr)
			vals = agg.get((date_str, "Cash", ck), {"basic": 0.0, "accountant": 0.0})
			basic = flt(vals.get("basic"))
			acct  = flt(vals.get("accountant"))

			if is_restricted_checker:
				res = frappe.db.sql(
					"SELECT SUM(balance) FROM `tabBank Balance Entry`"
					" WHERE date=%s AND company=%s AND currency=%s AND username=%s",
					[date_str, full_co, curr, current_user],
				)
			else:
				res = frappe.db.sql(
					"SELECT SUM(balance) FROM `tabBank Balance Entry`"
					" WHERE date=%s AND company=%s AND currency=%s",
					[date_str, full_co, curr],
				)
			checker = flt(res[0][0]) if res else 0.0

			def _bbe_user(email, fc=full_co, cu=curr):
				r = frappe.db.sql(
					"SELECT SUM(balance) FROM `tabBank Balance Entry`"
					" WHERE date=%s AND company=%s AND currency=%s AND username=%s",
					[date_str, fc, cu, email],
				)
				return flt(r[0][0]) if r else 0.0

			hitesh_val = _bbe_user(_CHECKER_MAP["Hitesh"])
			dipak_val  = _bbe_user(_CHECKER_MAP["Dipak"])
			tally      = 1 if abs((basic + acct) - checker) < 1e-6 else 0

			row["{}_basic".format(prefix)]      = basic
			row["{}_accountant".format(prefix)] = acct
			row["{}_checker".format(prefix)]    = checker
			row["{}_hitesh".format(prefix)]     = hitesh_val
			row["{}_dipak".format(prefix)]      = dipak_val
			row["{}_tally".format(prefix)]      = tally

			if abs(basic) > 1e-6 or abs(acct) > 1e-6 or abs(checker) > 1e-6 \
					or abs(hitesh_val) > 1e-6 or abs(dipak_val) > 1e-6:
				has_data = True

		if has_data:
			data.append(row)

	return data
