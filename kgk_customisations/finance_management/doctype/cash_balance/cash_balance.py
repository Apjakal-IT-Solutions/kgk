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


def _parse_company_key(balance_type, company_key):
	"""Split legacy parent company key into child row company/currency.

	Cash key format: Company_Currency  (e.g. Diamonds_USD)
	Bank key format: Currency@Bank     (e.g. ZAR@ABSA)
	"""
	key = (company_key or "").strip()
	if not key:
		return "", ""

	if balance_type == "Cash" and "_" in key:
		company, currency = key.rsplit("_", 1)
		return company.strip(), currency.strip()

	if balance_type == "Bank" and "@" in key:
		currency, bank = key.split("@", 1)
		return bank.strip(), currency.strip()

	return key, ""


def _build_company_key(balance_type, company, currency, bank=None):
	company = (company or "").strip()
	currency = (currency or "").strip()
	bank = (bank or "").strip()

	if balance_type == "Cash" and currency:
		# Reverse-map full company name to short alias to preserve compound key format.
		short = REVERSE_COMPANY_MAP.get(company, company)
		if short:
			return "{}_{}".format(short, currency)

	if balance_type == "Bank":
		# bank field takes priority; fall back to company for legacy rows not yet migrated.
		bank_name = bank or company
		if "@" in bank_name:
			return bank_name
		if bank_name and currency:
			return "{}@{}".format(currency, bank_name)

	return company or bank


def _get_child_rows(parent_names):
	if not parent_names:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT parent, company, bank, currency, basic, accountant
		FROM `tabCash Balance Item`
		WHERE parenttype = 'Cash Balance' AND parent IN %(parents)s
		ORDER BY idx ASC
		""",
		{"parents": tuple(parent_names)},
		as_dict=True,
	)

	grouped = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	return grouped


def _load_aggregates(date_from=None, date_to=None, date=None, balance_type=None):
	"""Return aggregated values keyed by (date_str, balance_type, company_key)."""
	filters = {}
	if date:
		filters["date"] = date
	elif date_from and date_to:
		filters["date"] = ["between", [date_from, date_to]]

	if balance_type:
		filters["balance_type"] = balance_type

	parents = frappe.db.get_all(
		"Cash Balance",
		filters=filters,
		fields=["name", "date", "balance_type", "company", "basic", "accountant"],
		order_by="date asc",
	)

	parent_names = [p.name for p in parents]
	children_by_parent = _get_child_rows(parent_names)

	agg = {}
	for p in parents:
		date_str = str(p.date)
		children = children_by_parent.get(p.name, [])

		if children:
			for child in children:
				company_key = _build_company_key(p.balance_type, child.company, child.currency, child.bank)
				if not company_key:
					continue
				key = (date_str, p.balance_type, company_key)
				if key not in agg:
					agg[key] = {"basic": 0.0, "accountant": 0.0}
				agg[key]["basic"] += flt(child.basic)
				agg[key]["accountant"] += flt(child.accountant)
		else:
			# Legacy fallback: parent-level amounts when child rows are absent.
			company_key = (p.company or "").strip()
			if not company_key:
				continue
			key = (date_str, p.balance_type, company_key)
			if key not in agg:
				agg[key] = {"basic": 0.0, "accountant": 0.0}
			agg[key]["basic"] += flt(p.basic)
			agg[key]["accountant"] += flt(p.accountant)

	return agg


def _get_amount_rows(doc):
	"""Support both historical and current child-table fieldnames."""
	return doc.get("balances_table") or doc.get("table_dwal") or []


def _collect_company_keys_from_doc(doc):
	keys = []
	for row in _get_amount_rows(doc):
		key = _build_company_key(doc.balance_type, row.company, row.currency, getattr(row, "bank", None))
		if key:
			keys.append(key)

	# Legacy fallback when child rows are absent.
	if not keys and (doc.company or "").strip():
		keys.append((doc.company or "").strip())

	return keys


def _find_target_doc_name(date, balance_type, company_key):
	# 1) Legacy exact parent-key match (backward compatibility).
	legacy = frappe.db.get_value(
		"Cash Balance",
		{"date": date, "balance_type": balance_type, "company": company_key},
		"name",
	)
	if legacy:
		return legacy

	# 2) Child-table match (new source of truth).
	child_entity, child_currency = _parse_company_key(balance_type, company_key)
	if child_entity:
		if balance_type == "Bank":
			match = frappe.db.sql(
				"""
				SELECT p.name
				FROM `tabCash Balance` p
				INNER JOIN `tabCash Balance Item` i ON i.parent = p.name
				WHERE p.date = %(date)s
				  AND p.balance_type = %(balance_type)s
				  AND COALESCE(i.bank, '') = %(bank)s
				  AND COALESCE(i.currency, '') = %(currency)s
				LIMIT 1
				""",
				{
					"date": date,
					"balance_type": balance_type,
					"bank": child_entity,
					"currency": child_currency or "",
				},
			)
		else:
			full_company = COMPANY_MAP.get(child_entity, child_entity)
			match = frappe.db.sql(
				"""
				SELECT p.name
				FROM `tabCash Balance` p
				INNER JOIN `tabCash Balance Item` i ON i.parent = p.name
				WHERE p.date = %(date)s
				  AND p.balance_type = %(balance_type)s
				  AND i.company = %(company)s
				  AND COALESCE(i.currency, '') = %(currency)s
				LIMIT 1
				""",
				{
					"date": date,
					"balance_type": balance_type,
					"company": full_company,
					"currency": child_currency or "",
				},
			)
		if match:
			return match[0][0]

	# 3) Reuse a consolidated doc for date/type when present (new pattern).
	candidate = frappe.db.get_value(
		"Cash Balance",
		{"date": date, "balance_type": balance_type},
		"name",
	)
	return candidate


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
		# Active company/account keys are driven by child rows.
		# Parent company is retained as legacy metadata.
		current_keys = _collect_company_keys_from_doc(self)

		seen = set()
		for key in current_keys:
			if key in seen:
				frappe.throw(
					frappe._("Duplicate company/account key in Amnt rows: {0}").format(key)
				)
			seen.add(key)

		if not current_keys:
			return

		other_docs = frappe.db.get_all(
			"Cash Balance",
			filters={
				"date": self.date,
				"balance_type": self.balance_type,
				"name": ("!=", self.name),
			},
			fields=["name", "company"],
		)

		if not other_docs:
			return

		other_names = [d.name for d in other_docs]
		existing_keys = set()

		if other_names:
			rows = frappe.db.sql(
				"""
				SELECT p.balance_type, i.company, i.bank, i.currency
				FROM `tabCash Balance` p
				INNER JOIN `tabCash Balance Item` i ON i.parent = p.name
				WHERE p.name IN %(names)s
				""",
				{"names": tuple(other_names)},
				as_dict=True,
			)
			for row in rows:
				key = _build_company_key(row.balance_type, row.company, row.currency, row.get("bank"))
				if key:
					existing_keys.add(key)

		# Include legacy parent keys from docs with no child rows.
		for d in other_docs:
			if (d.company or "").strip():
				existing_keys.add((d.company or "").strip())

		for key in current_keys:
			if key in existing_keys:
				frappe.throw(
					frappe._(
						"A Cash Balance record already exists for {0} / {1} / {2}."
					).format(self.date, self.balance_type, key)
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

	existing = _find_target_doc_name(date, balance_type, company)
	child_entity, child_currency = _parse_company_key(balance_type, company)

	if balance_type == "Cash":
		stored_company = COMPANY_MAP.get(child_entity, child_entity)
		legacy_parent_company = stored_company if frappe.db.exists("Company", stored_company) else ""
	else:
		stored_company = ""
		legacy_parent_company = ""

	if existing:
		doc = frappe.get_doc("Cash Balance", existing)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Cash Balance",
				"date": date,
				"balance_type": balance_type,
				"company": legacy_parent_company,
			}
		)

	company_key = _build_company_key(balance_type, child_entity, child_currency)

	match = None
	for row in _get_amount_rows(doc):
		row_key = _build_company_key(balance_type, row.company, row.currency, getattr(row, "bank", None))
		if row_key == company_key:
			match = row
			break

	if not match:
		if balance_type == "Bank":
			row_fields = {"bank": child_entity, "company": "", "currency": child_currency}
		else:
			row_fields = {"company": stored_company, "bank": "", "currency": child_currency}
		match = doc.append("balances_table", row_fields)

	setattr(match, role_field, flt(value))

	# Keep legacy parent fields mirrored for backward compatibility.
	# Child table remains the source of truth for read paths.
	setattr(doc, role_field, flt(value))

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	frappe.db.commit()


@frappe.whitelist()
def get_balances(date):
	# Return all Cash Balance rows for a date, structured as:
	# { "Cash": { "basic": {company: val}, "accountant": {company: val} },
	#   "Bank": { "basic": {company: val}, "accountant": {company: val} } }
	agg = _load_aggregates(date=date)

	result = {
		"Cash": {"basic": {}, "accountant": {}},
		"Bank": {"basic": {}, "accountant": {}},
	}
	for (row_date, bt, company_key), vals in agg.items():
		if str(row_date) != str(date):
			continue
		if bt not in result:
			result[bt] = {"basic": {}, "accountant": {}}
		result[bt]["basic"][company_key] = flt(vals.get("basic"))
		result[bt]["accountant"][company_key] = flt(vals.get("accountant"))

	return result


@frappe.whitelist()
def get_cash_balance_report(date_from, date_to):
	# Return Cash balance rows for a date range (used by Script Report).
	agg = _load_aggregates(date_from=date_from, date_to=date_to, balance_type="Cash")
	report = []
	for (date_str, bt, company_key), vals in sorted(agg.items()):
		if bt != "Cash":
			continue
		basic_val = flt(vals.get("basic"))
		accountant_val = flt(vals.get("accountant"))
		net_diff = accountant_val - basic_val
		report.append(
			{
				"date": str(date_str),
				"company": company_key,
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
	agg = _load_aggregates(date_from=date_from, date_to=date_to, balance_type="Bank")
	accountant_data = {}
	for (date_str, bt, company_key), vals in agg.items():
		if bt != "Bank":
			continue
		accountant_data[(str(date_str), company_key)] = flt(vals.get("accountant"))

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
