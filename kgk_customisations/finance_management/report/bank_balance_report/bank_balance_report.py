# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from kgk_customisations.finance_management.doctype.cash_balance.cash_balance import _load_aggregates

_BANKS = ["ZAR@ABSA", "USD@ABSA", "BWP@FNB", "BWP@ABSA"]
_ACCOUNT_NUMBERS = {
	"ZAR@ABSA": "1008748",
	"USD@ABSA": "1004556",
	"BWP@FNB": "62415220110",
	"BWP@ABSA": "1023469",
}


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
	for i, bank in enumerate(_BANKS):
		acc_no = _ACCOUNT_NUMBERS[bank]
		label = "{} ({})".format(bank, acc_no)
		columns += [
			{
				"fieldname": "bank_{}_accountant".format(i),
				"label": "{} Lore".format(label),
				"fieldtype": "Currency",
				"width": 150,
			},
			{
				"fieldname": "bank_{}_checker".format(i),
				"label": "{} Harsh".format(label),
				"fieldtype": "Currency",
				"width": 150,
			},
		]
	# Hidden tally columns used by JS formatter (1=match, 0=mismatch)
	for i in range(len(_BANKS)):
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

	# Collect all relevant dates from both tables
	agg = _load_aggregates(date_from=date_from, date_to=date_to, balance_type="Bank")
	cb_dates = [(d,) for (d, bt, key), vals in agg.items() if bt == "Bank"]
	bb_dates = frappe.db.sql(
		"SELECT DISTINCT date FROM `tabBank Balance Entry`"
		" WHERE date BETWEEN %s AND %s",
		[date_from, date_to],
	)
	all_dates = sorted(
		set(row[0] for row in cb_dates) | set(row[0] for row in bb_dates)
	)

	data = []
	for date in all_dates:
		date_str = str(date)

		# Accountant values: Cash Balance child-table aggregates (legacy fallback included)
		acct_map = {
			company_key: flt(vals.get("accountant"))
			for (d, bt, company_key), vals in agg.items()
			if str(d) == date_str and bt == "Bank"
		}

		# Checker values from Bank Balance Entry
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
				" WHERE date = %s"
				" GROUP BY company",
				[date_str],
				as_dict=True,
			)
			checker_map = {r.company: flt(r.total) for r in bb_rows}

		row = {"date": date_str}
		nonzero = False

		for i, bank in enumerate(_BANKS):
			accountant = acct_map.get(bank, 0.0)
			checker = checker_map.get(bank, 0.0)
			tally = 1 if abs(accountant - checker) < 1e-6 else 0

			row["bank_{}_accountant".format(i)] = accountant
			row["bank_{}_checker".format(i)] = checker
			row["tally_{}".format(i)] = tally

			if abs(accountant) > 1e-6 or abs(checker) > 1e-6:
				nonzero = True

		if nonzero:
			data.append(row)

	return data
