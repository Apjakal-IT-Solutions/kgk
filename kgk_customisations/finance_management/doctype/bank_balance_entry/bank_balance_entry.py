# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


def _require_role(roles):
	if frappe.session.user == "Administrator":
		return
	user_roles = frappe.get_roles(frappe.session.user)
	if not any(r in user_roles for r in roles):
		frappe.throw(
			frappe._("You do not have permission to perform this action."),
			frappe.PermissionError,
		)


class BankBalanceEntry(Document):

	def validate(self):
		# Prevent duplicate (date, company, username) on new documents.
		if self.is_new():
			existing = frappe.db.get_value(
				"Bank Balance Entry",
				{
					"date": self.date,
					"company": self.company,
					"username": self.username,
					"name": ("!=", self.name),
				},
				"name",
			)
			if existing:
				frappe.throw(
					frappe._(
						"A Bank Balance Entry already exists for {0} / {1} / {2}."
					).format(self.date, self.company, self.username)
				)


# ---------------------------------------------------------------------------
# Whitelisted API functions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def set_balance(date, company, username, balance):
	# Upsert a checker balance for (date, company, username).
	# company is a compound key e.g. 'ZAR@ABSA' or 'Diamonds_USD'.
	_require_role(["Cash Checker", "Cash Super User", "Administrator"])

	existing = frappe.db.get_value(
		"Bank Balance Entry",
		{"date": date, "company": company, "username": username},
		"name",
	)

	if existing:
		frappe.db.set_value("Bank Balance Entry", existing, "balance", flt(balance))
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Bank Balance Entry",
				"date": date,
				"company": company,
				"username": username,
				"balance": flt(balance),
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()


@frappe.whitelist()
def get_balance(date, company, username):
	# Get the balance for a specific (date, company, username).
	return frappe.db.get_value(
		"Bank Balance Entry",
		{"date": date, "company": company, "username": username},
		"balance",
	)


@frappe.whitelist()
def get_totals(date):
	# Return total balance per company for a date (summed across all usernames).
	rows = frappe.db.sql(
		"""
		SELECT company, SUM(balance) AS total
		FROM `tabBank Balance Entry`
		WHERE date = %s
		GROUP BY company
		""",
		[date],
		as_dict=True,
	)
	return {row.company: flt(row.total) for row in rows}


@frappe.whitelist()
def get_all_totals(date_from, date_to):
	# Return totals per (date, company) for a date range (used by Bank Balance Report).
	rows = frappe.db.sql(
		"""
		SELECT date, company, SUM(balance) AS total
		FROM `tabBank Balance Entry`
		WHERE date BETWEEN %s AND %s
		GROUP BY date, company
		""",
		[date_from, date_to],
		as_dict=True,
	)
	result = {}
	for row in rows:
		result.setdefault(str(row.date), {})[row.company] = flt(row.total)
	return result
