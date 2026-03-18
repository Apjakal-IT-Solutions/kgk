# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from kgk_customisations.finance_management.doctype.cash_balance.cash_balance import COMPANY_MAP

_COMPANIES  = ["Diamonds", "Jewellery", "Agro"]
_CURRENCIES = ["USD", "ZAR", "BWP"]


def execute(filters=None):
	filters = filters or {}
	columns = _get_columns()
	data    = _get_data(filters)
	return columns, data


def _get_columns():
	return [
		{"fieldname": "date",       "label": "Date",       "fieldtype": "Date",     "width": 110},
		{"fieldname": "basic",      "label": "Cebo",       "fieldtype": "Currency", "width": 140},
		{"fieldname": "accountant", "label": "Lore",       "fieldtype": "Currency", "width": 140},
		{"fieldname": "checker",    "label": "Harsh",      "fieldtype": "Currency", "width": 140},
		{"fieldname": "tally",      "label": "Match",      "fieldtype": "Int",      "hidden": 1},
	]


def _get_data(filters):
	date_from = filters.get("date_from")
	date_to   = filters.get("date_to")
	company   = filters.get("company")
	currency  = filters.get("currency")

	if not date_from or not date_to or not company or not currency:
		return []

	comp_key     = "{}_{}".format(company, currency)
	full_company = COMPANY_MAP.get(company, company)

	# Restricted checkers see only their own Bank Balance Entry rows
	user_roles = frappe.get_roles(frappe.session.user)
	is_restricted_checker = (
		"Cash Checker" in user_roles
		and "Cash Super User" not in user_roles
		and frappe.session.user != "Administrator"
	)
	current_user = frappe.session.user

	# Collect dates that have any data for this company+currency
	cb_dates = frappe.db.sql(
		"SELECT DISTINCT date FROM `tabCash Balance`"
		" WHERE company = %s AND balance_type = 'Cash' AND date BETWEEN %s AND %s",
		[comp_key, date_from, date_to],
	)
	bb_dates = frappe.db.sql(
		"SELECT DISTINCT date FROM `tabBank Balance Entry`"
		" WHERE company = %s AND currency = %s AND date BETWEEN %s AND %s",
		[full_company, currency, date_from, date_to],
	)
	all_dates = sorted(set(r[0] for r in cb_dates) | set(r[0] for r in bb_dates))

	data = []
	for date in all_dates:
		date_str = str(date)

		rec = frappe.db.get_value(
			"Cash Balance",
			{"date": date_str, "company": comp_key, "balance_type": "Cash"},
			["basic", "accountant"],
			as_dict=True,
		)
		basic      = flt(rec.basic)      if rec else 0.0
		accountant = flt(rec.accountant) if rec else 0.0

		if is_restricted_checker:
			bb = frappe.db.get_value(
				"Bank Balance Entry",
				{"date": date_str, "company": full_company, "currency": currency, "username": current_user},
				"balance",
			)
			checker = flt(bb)
		else:
			agg = frappe.db.sql(
				"SELECT SUM(balance) FROM `tabBank Balance Entry`"
				" WHERE date = %s AND company = %s AND currency = %s",
				[date_str, full_company, currency],
			)
			checker = flt(agg[0][0]) if agg else 0.0

		tally = 1 if abs((basic + accountant) - checker) < 1e-6 else 0

		if abs(basic) > 1e-6 or abs(accountant) > 1e-6 or abs(checker) > 1e-6:
			data.append({
				"date":       date_str,
				"basic":      basic,
				"accountant": accountant,
				"checker":    checker,
				"tally":      tally,
			})

	return data
