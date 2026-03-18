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

COMPANY_MAP = {
				"Diamonds": "KGK Diamonds",
				"Jewellery": "KGK Jewelry",
				"Agro": "KGK Agro",
				"Healthcare": "KGK Healthcare",
}


def execute(filters=None):
	if not filters:
		filters = {}
	date_from = filters.get("date_from")
	date_to   = filters.get("date_to")
	if date_from and date_to:
		banks = _discover_banks(date_from, date_to)
	else:
		banks = list(_BANKS)
	columns = _get_columns(banks)
	data    = _get_data(filters, banks)
	return columns, data


def _discover_banks(date_from, date_to):
	"""Return an ordered list of unique bank keys present in the date range.

	Keys from Cash Balance (balance_type=Bank) and Bank Balance Entry.account
	are merged. Known banks (_BANKS) appear first in declared order; additional
	keys are appended alphabetically.
	"""
	cb_rows = frappe.db.sql(
		"SELECT DISTINCT company FROM `tabCash Balance`"
		" WHERE balance_type = 'Bank' AND date BETWEEN %s AND %s",
		[date_from, date_to],
	)
	cb_keys = {str(row[0]) for row in cb_rows if row[0]}

	bb_rows = frappe.db.sql(
		"SELECT DISTINCT account FROM `tabBank Balance Entry`"
		" WHERE account IS NOT NULL AND account != ''"
		" AND date BETWEEN %s AND %s",
		[date_from, date_to],
	)
	bb_keys = {str(row[0]) for row in bb_rows if row[0]}

	all_keys = cb_keys | bb_keys
	ordered = [b for b in _BANKS if b in all_keys]
	extras  = sorted(all_keys - set(_BANKS))
	return ordered + extras


def _get_columns(banks):
	columns = [
		{
			"fieldname": "date",
			"label": "Date",
			"fieldtype": "Date",
			"width": 100,
		}
	]
	for i, bank in enumerate(banks):
		acc_no = _ACCOUNT_NUMBERS.get(bank)
		label = "{} ({})".format(bank, acc_no) if acc_no else bank
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
	for i in range(len(banks)):
		columns.append(
			{
				"fieldname": "tally_{}".format(i),
				"label": "Tally {}".format(i),
				"fieldtype": "Int",
				"hidden": 1,
			}
		)
	return columns


def _get_data(filters, banks):
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
		" WHERE account IS NOT NULL AND account != ''"
		" AND date BETWEEN %s AND %s",
		[date_from, date_to],
	)
	all_dates = sorted(
		set(str(row[0]) for row in cb_dates) | set(str(row[0]) for row in bb_dates)
	)

	data = []
	for date in all_dates:
		date_str = str(date)

		# Accountant values: Cash Balance (balance_type=Bank), company = bank key
		acct_rows = frappe.db.get_all(
			"Cash Balance",
			filters={"date": date_str, "balance_type": "Bank"},
			fields=["company", "accountant"],
		)
		acct_map = {r.company: flt(r.accountant) for r in acct_rows}

		# Checker values from Bank Balance Entry (account field)
		if is_checker:
			bb_rows = frappe.db.get_all(
				"Bank Balance Entry",
				filters={"date": date_str, "username": current_user},
				fields=["account", "balance"],
			)
			checker_map = {r.account: flt(r.balance) for r in bb_rows if r.account}
		else:
			bb_rows = frappe.db.sql(
				"SELECT account, SUM(balance) AS total"
				" FROM `tabBank Balance Entry`"
				" WHERE date = %s AND account IS NOT NULL AND account != ''"
				" GROUP BY account",
				[date_str],
				as_dict=True,
			)
			checker_map = {r.account: flt(r.total) for r in bb_rows}

		row = {"date": date_str}
		nonzero = False

		for i, bank in enumerate(banks):
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
