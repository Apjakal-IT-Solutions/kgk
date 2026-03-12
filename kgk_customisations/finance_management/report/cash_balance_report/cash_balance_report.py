# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

_CATEGORIES = ["Diamonds", "Jewellery", "Agro"]
_CURRENCIES = ["USD", "ZAR", "BWP"]
_COMBOS = [(cat, cur) for cat in _CATEGORIES for cur in _CURRENCIES]


def execute(filters=None):
	if not filters:
		filters = {}
	columns = _get_columns()
	data = _get_data(filters)
	return columns, data


def _get_columns():
	columns = [
		{
			"fieldname": "date",
			"label": "Date",
			"fieldtype": "Date",
			"width": 100,
		}
	]
	for i, (cat, cur) in enumerate(_COMBOS):
		label = "{} {}".format(cat, cur)
		columns += [
			{
				"fieldname": "group_{}_basic".format(i),
				"label": "{} Cebo".format(label),
				"fieldtype": "Currency",
				"width": 100,
			},
			{
				"fieldname": "group_{}_accountant".format(i),
				"label": "{} Lore".format(label),
				"fieldtype": "Currency",
				"width": 100,
			},
			{
				"fieldname": "group_{}_checker".format(i),
				"label": "{} Harsh".format(label),
				"fieldtype": "Currency",
				"width": 100,
			},
		]
	# Hidden tally columns used by JS formatter (1=match, 0=mismatch)
	for i in range(len(_COMBOS)):
		columns.append(
			{
				"fieldname": "tally_{}".format(i),
				"label": "Tally {}".format(i),
				"fieldtype": "Int",
				"hidden": 1,
			}
		)
	return columns


def _get_data(filters):
	date_from = filters.get("date_from")
	date_to = filters.get("date_to")
	if not date_from or not date_to:
		return []

	# Cash Checker (without Super User) sees only their own BankBasicEntry rows
	user_roles = frappe.get_roles(frappe.session.user)
	is_checker = (
		"Cash Checker" in user_roles
		and "Cash Super User" not in user_roles
		and frappe.session.user != "Administrator"
	)
	current_user = frappe.session.user

	# Collect all dates that have Cash data or cash-type BankBasicEntry rows
	cash_dates = frappe.db.sql(
		"SELECT DISTINCT date FROM `tabCash Balance`"
		" WHERE balance_type = 'Cash' AND date BETWEEN %s AND %s",
		[date_from, date_to],
	)
	bb_dates = frappe.db.sql(
		"SELECT DISTINCT date FROM `tabBank Balance Entry`"
		" WHERE company LIKE %s AND date BETWEEN %s AND %s",
		["%\\_%", date_from, date_to],
	)
	all_dates = sorted(
		set(row[0] for row in cash_dates) | set(row[0] for row in bb_dates)
	)

	data = []
	for date in all_dates:
		date_str = str(date)

		# Cash Balance rows for this date
		bal_rows = frappe.db.get_all(
			"Cash Balance",
			filters={"date": date_str, "balance_type": "Cash"},
			fields=["company", "basic", "accountant"],
		)
		bal_map = {r.company: r for r in bal_rows}

		# Checker values from Bank Balance Entry (company contains "_" for cash)
		if is_checker:
			bb_rows = frappe.db.get_all(
				"Bank Balance Entry",
				filters={"date": date_str, "username": current_user},
				fields=["company", "balance"],
			)
			checker_map = {r.company: flt(r.balance) for r in bb_rows}
		else:
			bb_rows = frappe.db.sql(
				"SELECT company, SUM(balance) AS total"
				" FROM `tabBank Balance Entry`"
				" WHERE date = %s AND company LIKE %s"
				" GROUP BY company",
				[date_str, "%\\_%"],
				as_dict=True,
			)
			checker_map = {r.company: flt(r.total) for r in bb_rows}

		row = {"date": date_str}
		nonzero = False

		for i, (cat, cur) in enumerate(_COMBOS):
			comp_key = "{}_{}".format(cat, cur)
			rec = bal_map.get(comp_key)
			basic = flt(rec.basic) if rec else 0.0
			accountant = flt(rec.accountant) if rec else 0.0
			checker = checker_map.get(comp_key, 0.0)
			tally = 1 if abs((basic + accountant) - checker) < 1e-6 else 0

			row["group_{}_basic".format(i)] = basic
			row["group_{}_accountant".format(i)] = accountant
			row["group_{}_checker".format(i)] = checker
			row["tally_{}".format(i)] = tally

			if abs(basic) > 1e-6 or abs(accountant) > 1e-6 or abs(checker) > 1e-6:
				nonzero = True

		if nonzero:
			data.append(row)

	return data
