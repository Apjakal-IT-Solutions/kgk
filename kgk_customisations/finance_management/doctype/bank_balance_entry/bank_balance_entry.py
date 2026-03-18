# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from kgk_customisations.finance_management.doctype.cash_balance.cash_balance import (
	COMPANY_MAP,
	REVERSE_COMPANY_MAP,
)


def _require_role(roles):
	if frappe.session.user == "Administrator":
		return
	user_roles = frappe.get_roles(frappe.session.user)
	if not any(r in user_roles for r in roles):
		frappe.throw(
			frappe._("You do not have permission to perform this action."),
			frappe.PermissionError,
		)


def _entry_key(row):
	"""Return the compound key string for a Bank Balance Entry row.

	Bank entries (account set): key = account value, e.g. 'ZAR@ABSA'.
	Cash entries (company + currency set): key = 'ShortName_Currency', e.g. 'Diamonds_USD'.
	"""
	if row.get("account"):
		return row["account"]
	company_name = row.get("company") or ""
	currency = row.get("currency") or ""
	if company_name and currency:
		short = REVERSE_COMPANY_MAP.get(company_name, company_name)
		return "{}_{}".format(short, currency)
	return company_name or currency or ""


def _entry_filters(date, username, account=None, company=None, currency=None):
	"""Build a filters dict that uniquely identifies an entry."""
	f = {"date": date, "username": username}
	if account:
		f["account"] = account
	if company:
		f["company"] = company
	if currency:
		f["currency"] = currency
	return f


class BankBalanceEntry(Document):

	def validate(self):
		# Require at least one identifying field (account or company).
		if not self.account and not self.company:
			frappe.throw(frappe._("Either Account (for bank entries) or Company (for cash entries) is required."))

		# Prevent duplicate (date, account/company/currency, username) on new documents.
		if self.is_new():
			filters = _entry_filters(
				self.date, self.username,
				account=self.account or None,
				company=self.company or None,
				currency=self.currency or None,
			)
			filters["name"] = ("!=", self.name)
			existing = frappe.db.get_value("Bank Balance Entry", filters, "name")
			if existing:
				identifier = self.account or "{} / {}".format(self.company, self.currency)
				frappe.throw(
					frappe._(
						"A Bank Balance Entry already exists for {0} / {1} / {2}."
					).format(self.date, identifier, self.username)
				)


# ---------------------------------------------------------------------------
# Whitelisted API functions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def set_balance(date, username, balance, account=None, company=None, currency=None):
	# Upsert a checker balance.
	# For bank entries: supply account (e.g. 'ZAR@ABSA').
	# For cash entries: supply company (Link) + currency.
	_require_role(["Cash Checker", "Cash Super User", "Administrator"])

	filters = _entry_filters(date, username, account=account, company=company, currency=currency)
	existing = frappe.db.get_value("Bank Balance Entry", filters, "name")

	if existing:
		frappe.db.set_value("Bank Balance Entry", existing, "balance", flt(balance))
	else:
		doc_fields = {
			"doctype": "Bank Balance Entry",
			"date": date,
			"username": username,
			"balance": flt(balance),
		}
		if account:
			doc_fields["account"] = account
		if company:
			doc_fields["company"] = company
		if currency:
			doc_fields["currency"] = currency
		frappe.get_doc(doc_fields).insert(ignore_permissions=True)

	frappe.db.commit()


@frappe.whitelist()
def get_balance(date, username, account=None, company=None, currency=None):
	# Get the balance for a specific entry.
	filters = _entry_filters(date, username, account=account, company=company, currency=currency)
	return frappe.db.get_value("Bank Balance Entry", filters, "balance")


@frappe.whitelist()
def get_totals(date):
	# Return total balance per compound key for a date (summed across all usernames).
	rows = frappe.db.sql(
		"""
		SELECT account, company, currency, SUM(balance) AS total
		FROM `tabBank Balance Entry`
		WHERE date = %s
		GROUP BY account, company, currency
		""",
		[date],
		as_dict=True,
	)
	return {_entry_key(r): flt(r.total) for r in rows}


@frappe.whitelist()
def migrate_compound_keys():
	"""One-off migration: split legacy compound company keys into the new fields.

	Bank entries (e.g. 'ZAR@ABSA') → account = 'ZAR@ABSA', company = '', currency = ''.
	Cash entries (e.g. 'Diamonds_USD') → company = 'KGK Diamonds' (Link), currency = 'USD', account = ''.

	Run once from bench console:
	  bench execute kgk_customisations.finance_management.doctype.bank_balance_entry.bank_balance_entry.migrate_compound_keys
	"""
	_require_role(["Cash Super User", "Administrator"])

	_KNOWN_ACCOUNTS = {"ZAR@ABSA", "USD@ABSA", "BWP@FNB", "BWP@ABSA"}

	rows = frappe.db.sql(
		"SELECT name, company FROM `tabBank Balance Entry`"
		" WHERE (account IS NULL OR account = '')"
		"   AND (company IS NOT NULL AND company != '')",
		as_dict=True,
	)

	migrated = 0
	for row in rows:
		old_val = (row.company or "").strip()
		if not old_val:
			continue

		if old_val in _KNOWN_ACCOUNTS:
			# Bank entry: move to account field
			frappe.db.set_value(
				"Bank Balance Entry", row.name,
				{"account": old_val, "company": "", "currency": ""},
				update_modified=False,
			)
			migrated += 1
		elif "_" in old_val:
			# Potential cash entry: split on last underscore → CompanyShort + Currency
			parts = old_val.rsplit("_", 1)
			if len(parts) == 2:
				short_name, currency_code = parts
				full_company = COMPANY_MAP.get(short_name, "")
				if full_company and currency_code:
					frappe.db.set_value(
						"Bank Balance Entry", row.name,
						{"company": full_company, "currency": currency_code, "account": ""},
						update_modified=False,
					)
					migrated += 1

	frappe.db.commit()
	return {"migrated": migrated, "total": len(rows)}


@frappe.whitelist()
def get_all_totals(date_from, date_to):
	# Return totals per (date, compound_key) for a date range (used by Bank Balance Report).
	rows = frappe.db.sql(
		"""
		SELECT date, account, company, currency, SUM(balance) AS total
		FROM `tabBank Balance Entry`
		WHERE date BETWEEN %s AND %s
		GROUP BY date, account, company, currency
		""",
		[date_from, date_to],
		as_dict=True,
	)
	result = {}
	for row in rows:
		result.setdefault(str(row.date), {})[_entry_key(row)] = flt(row.total)
	return result
