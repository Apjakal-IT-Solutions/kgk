# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, cint

# Counter field names in the Cash Voucher Series Single DocType
_COUNTER_MAP = {
	"Cash":   "cash_counter",
	"Bank":   "bank_counter",
	"Cash-2": "cash_2_counter",
	"Bank-2": "bank_2_counter",
	"JE":     "je_counter",
}

# Name format strings (one positional placeholder for the counter)
_FORMAT_MAP = {
	"Cash":   "25-{}",
	"Bank":   "B{}",
	"Cash-2": "C2-25-{}",
	"Bank-2": "B2-{}",
	"JE":     "JE{}",
}

# Allowed sub_type values per main_type (empty string means no sub_type is OK)
_VALID_SUB_TYPES = {
	"Cash":   {"Payment", "Receipt"},
	"Bank":   {"Credit Card", "EFT"},
	"Cash-2": {""},
	"Bank-2": {""},
	"JE":     {"JE"},
}

class CashDocument(Document):

	def autoname(self):
		"""Assign a name derived from an atomic per-type counter."""
		main_type = self.main_type
		if main_type not in _COUNTER_MAP:
			frappe.throw(frappe._("Select a Document Type before saving."))

		field = _COUNTER_MAP[main_type]

		# Atomic increment using UPDATE.  tabSingles has no UNIQUE constraint, so
		# INSERT ... ON DUPLICATE KEY UPDATE creates duplicate rows and cannot be used.
		# The counter row is guaranteed to exist (seeded at install time by the patch).
		# InnoDB row-level locking on the UPDATE makes this safe under concurrent access.
		frappe.db.sql(
			"""
			UPDATE `tabSingles`
			SET value = CAST(COALESCE(CAST(value AS UNSIGNED), 0) + 1 AS CHAR)
			WHERE doctype = 'Cash Voucher Series' AND field = %(field)s
			""",
			{"field": field},
		)

		# Read back via raw SQL to bypass Frappe's Single-doctype in-memory cache.
		# InnoDB read-your-own-writes guarantee means we see the updated value
		# within the same transaction.
		result = frappe.db.sql(
			"SELECT value FROM `tabSingles` WHERE doctype='Cash Voucher Series' AND field=%s",
			[field],
		)
		next_num = cint(result[0][0]) if result else 1
		self.name = _FORMAT_MAP[main_type].format(next_num)

	def before_insert(self):
		if not self.system_date:
			self.system_date = now_datetime()
		if self.date:
			self.year = getdate(self.date).year
		if not self.created_by:
			self.created_by = frappe.session.user
		# file_name is always <unique_number>.pdf — never entered manually
		if self.name:
			self.file_name = self.name + ".pdf"

	def validate(self):
		if self.main_type:
			valid = _VALID_SUB_TYPES.get(self.main_type, set())
			sub = self.sub_type or ""

			if self.main_type in ("Cash", "Bank") and not sub:
				frappe.throw(
					frappe._("Sub Type is required for {0} documents.").format(self.main_type)
				)
			elif sub and sub not in valid:
				frappe.throw(
					frappe._("Sub Type '{0}' is not valid for {1} documents.").format(
						sub, self.main_type
					)
				)

		if self.date:
			self.year = getdate(self.date).year


# Whitelisted server functions

@frappe.whitelist()
def finalise(doc_name):
	"""Set status to final. Restricted to Cash Accountant / Cash Super User."""
	_require_role(["Cash Accountant", "Cash Super User", "Administrator"])
	doc = frappe.get_doc("Cash Document", doc_name)
	if doc.docstatus != 0:
		frappe.throw(frappe._("Finalise is only allowed on draft (pre-submit) documents."))
	if doc.status == "final":
		frappe.throw(frappe._("Document is already finalised."))
	frappe.db.set_value("Cash Document", doc_name, "status", "final")
	return "final"


@frappe.whitelist()
def finalise2(doc_name):
	"""Set final_status2 to final2. Restricted to Cash Checker / Cash Super User."""
	_require_role(["Cash Checker", "Cash Super User", "Administrator"])
	doc = frappe.get_doc("Cash Document", doc_name)
	if doc.docstatus != 0:
		frappe.throw(frappe._("Finalise 2 is only allowed on draft (pre-submit) documents."))
	if doc.final_status2 == "final2":
		frappe.throw(frappe._("Document is already finalised (Status 2)."))
	frappe.db.set_value("Cash Document", doc_name, "final_status2", "final2")
	return "final2"


@frappe.whitelist()
def add_flag(doc_name, flag_type, comment):
	"""Append a review flag row to document_flags."""
	comment = (comment or "").strip()
	if not comment:
		frappe.throw(frappe._("Flag comment cannot be empty."))

	valid_types = {
		"Review Required", "Approved", "Rejected",
		"Query", "Hold", "Priority", "Revision Needed",
	}
	if flag_type not in valid_types:
		frappe.throw(frappe._("Invalid flag type: {0}").format(flag_type))

	doc = frappe.get_doc("Cash Document", doc_name)
	doc.append("document_flags", {
		"flag_type":      flag_type,
		"flag_date":      now_datetime(),
		"flagged_by":     frappe.session.user,
		"flagged_by_role": _primary_cash_role(),
		"comments":       comment,
	})
	doc.save(ignore_permissions=True)
	return len(doc.document_flags)


@frappe.whitelist()
def clear_flags(doc_name):
	"""Remove all review flags. Restricted to Cash Super User."""
	_require_role(["Cash Super User", "Administrator"])
	frappe.db.delete("Cash Document Flag", {"parent": doc_name})
	return 0


@frappe.whitelist()
def resync_counters():
	"""
	Resync Cash Voucher Series counters to MAX(numeric suffix) across all
	existing Cash Document records.  Call this after any bulk import of
	legacy data to prevent numbering collisions.

	Restricted to Cash Super User / Administrator.
	"""
	_require_role(["Cash Super User", "Administrator"])
	from kgk_customisations.patches.v1_0.resync_cash_voucher_series import (
		resync_counters as _resync,
	)
	return _resync()


# Internal helpers

def _require_role(roles):
	user_roles = set(frappe.get_roles(frappe.session.user))
	if not user_roles.intersection(roles):
		frappe.throw(
			frappe._("You do not have permission to perform this action."),
			frappe.PermissionError,
		)


def _primary_cash_role():
	"""Return the highest Cash role the current user holds, for audit logging."""
	priority = ["Cash Super User", "Cash Accountant", "Cash Checker", "Cash Basic User"]
	user_roles = set(frappe.get_roles(frappe.session.user))
	for role in priority:
		if role in user_roles:
			return role
	return "User"
