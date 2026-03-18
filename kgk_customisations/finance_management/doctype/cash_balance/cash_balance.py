# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

COMPANY_MAP = {
	"Diamonds": "KGK Diamonds",
	"Jewellery": "KGK Jewelry",
	"Agro": "KGK Agro",
	"Healthcare": "KGK Healthcare",
}
REVERSE_COMPANY_MAP = {v: k for k, v in COMPANY_MAP.items()}


def _require_role(roles):
	if frappe.session.user == "Administrator":
		return
	user_roles = frappe.get_roles(frappe.session.user)
	if not any(r in user_roles for r in roles):
		frappe.throw(
			frappe._("You do not have permission to perform this action."),
			frappe.PermissionError,
		)


class CashBalance(Document):

	def validate(self):
		# Prevent duplicate (date, balance_type, company) on new documents.
		if self.is_new():
			existing = frappe.db.get_value(
				"Cash Balance",
				{
					"date": self.date,
					"balance_type": self.balance_type,
					"company": self.company,
					"name": ("!=", self.name),
				},
				"name",
			)
			if existing:
				frappe.throw(
					frappe._(
						"A Cash Balance record already exists for {0} / {1} / {2}."
					).format(self.date, self.balance_type, self.company)
				)


# ---------------------------------------------------------------------------
# Whitelisted API functions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def set_balance(date, balance_type, company, role_field, value):
	# Upsert a balance value for the given (date, balance_type, company) triplet.
	# role_field: 'basic' (Cash Basic User) or 'accountant' (Cash Accountant)
	if role_field not in ("basic", "accountant"):
		frappe.throw(frappe._("Invalid role_field."))

	if role_field == "basic":
		_require_role(["Cash Basic User", "Cash Super User", "Administrator"])
	else:
		_require_role(["Cash Accountant", "Cash Super User", "Administrator"])

	existing = frappe.db.get_value(
		"Cash Balance",
		{"date": date, "balance_type": balance_type, "company": company},
		"name",
	)

	if existing:
		frappe.db.set_value("Cash Balance", existing, role_field, flt(value))
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Cash Balance",
				"date": date,
				"balance_type": balance_type,
				"company": company,
				role_field: flt(value),
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()


@frappe.whitelist()
def get_balances(date):
	# Return all Cash Balance rows for a date, structured as:
	# { "Cash": { "basic": {company: val}, "accountant": {company: val} },
	#   "Bank": { "basic": {company: val}, "accountant": {company: val} } }
	rows = frappe.db.get_all(
		"Cash Balance",
		filters={"date": date},
		fields=["balance_type", "company", "basic", "accountant"],
	)

	result = {
		"Cash": {"basic": {}, "accountant": {}},
		"Bank": {"basic": {}, "accountant": {}},
	}
	for row in rows:
		bt = row.balance_type
		if bt not in result:
			result[bt] = {"basic": {}, "accountant": {}}
		result[bt]["basic"][row.company] = flt(row.basic)
		result[bt]["accountant"][row.company] = flt(row.accountant)

	return result


@frappe.whitelist()
def get_cash_balance_report(date_from, date_to):
	# Return Cash balance rows for a date range (used by Script Report).
	rows = frappe.db.get_all(
		"Cash Balance",
		filters={
			"balance_type": "Cash",
			"date": ["between", [date_from, date_to]],
		},
		fields=["date", "company", "basic", "accountant"],
		order_by="date asc",
	)
	report = []
	for row in rows:
		basic_val = flt(row.basic)
		accountant_val = flt(row.accountant)
		net_diff = accountant_val - basic_val
		report.append(
			{
				"date": str(row.date),
				"company": row.company,
				"basic": basic_val,
				"accountant": accountant_val,
				"tally": "Tally" if abs(net_diff) < 1e-6 else "Not Tally",
				"net_difference": net_diff,
			}
		)
	return report


@frappe.whitelist()
def get_bank_balance_report(date_from, date_to):
	# Return Bank balance rows for a date range.
	# Accountant values: Cash Balance (balance_type=Bank).
	# Basic (checker) values: Bank Balance Entry summed per company/date.
	acct_rows = frappe.db.get_all(
		"Cash Balance",
		filters={
			"balance_type": "Bank",
			"date": ["between", [date_from, date_to]],
		},
		fields=["date", "company", "accountant"],
	)
	accountant_data = {
		(str(row.date), row.company): flt(row.accountant) for row in acct_rows
	}

	basic_rows = frappe.db.sql(
		"""
		SELECT date, account AS company, SUM(balance) AS total
		FROM `tabBank Balance Entry`
		WHERE date BETWEEN %s AND %s
		  AND account IS NOT NULL AND account != ''
		GROUP BY date, account
		""",
		[date_from, date_to],
		as_dict=True,
	)
	basic_data = {(str(row.date), row.company): flt(row.total) for row in basic_rows}

	all_keys = set(accountant_data.keys()) | set(basic_data.keys())
	report = []
	for key in sorted(all_keys):
		date_str, company = key
		basic_val = basic_data.get(key, 0)
		accountant_val = accountant_data.get(key, 0)
		net_diff = accountant_val - basic_val
		report.append(
			{
				"date": date_str,
				"company": company,
				"basic": basic_val,
				"accountant": accountant_val,
				"tally": "Tally" if abs(net_diff) < 1e-6 else "Not Tally",
				"net_difference": net_diff,
			}
		)
	return report
