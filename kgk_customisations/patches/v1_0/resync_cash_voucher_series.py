"""
Patch: resync_cash_voucher_series_from_db

After legacy data has been migrated into tabCash Document (records imported with
their original unique_number as the Frappe document name), this patch reads the
MAX numeric suffix for each document type and writes it into the Cash Voucher Series
counters.

This guarantees that the next counter value is strictly greater than every
existing record, mirroring the logic in the Django InvoiceNumberGenerator:

    max_number = MAX(numeric_part of existing unique_numbers for this type)
    next_number = max_number + 1
    inv.last_number = next_number   ← we store max_number; autoname() does +1

It is safe to run this patch multiple times (idempotent): it only ever increases
the counters, never decreases them.
"""

import re
import frappe
from frappe.utils import cint


# Maps main_type → (Cash Voucher Series field, regex to extract the numeric suffix)
TYPE_CONFIG = {
	"Cash":   ("cash_counter",   re.compile(r"^25-(\d+)$")),
	"Bank":   ("bank_counter",   re.compile(r"^B(\d+)$")),
	"Cash-2": ("cash_2_counter", re.compile(r"^C2-25-(\d+)$")),
	"Bank-2": ("bank_2_counter", re.compile(r"^B2-(\d+)$")),
	"JE":     ("je_counter",     re.compile(r"^JE(\d+)$")),
}


def execute():
	resync_counters()


def resync_counters():
	"""
	Scan all Cash Document names and set each counter in Cash Voucher Series to
	MAX(numeric suffix for that type).

	Returns a dict of {main_type: new_counter_value} for logging/debugging.
	"""
	# Fetch all document names in one query
	names = frappe.db.sql(
		"SELECT name FROM `tabCash Document`",
		as_list=True,
	)
	names = [row[0] for row in names]

	max_by_type = {main_type: 0 for main_type in TYPE_CONFIG}

	for name in names:
		for main_type, (field, pattern) in TYPE_CONFIG.items():
			m = pattern.match(name)
			if m:
				num = cint(m.group(1))
				if num > max_by_type[main_type]:
					max_by_type[main_type] = num
				break  # a name can only match one type

	updated = {}
	for main_type, (field, _) in TYPE_CONFIG.items():
		new_val = max_by_type[main_type]
		# Only ever advance the counter, never go backwards
		row = frappe.db.sql(
			"SELECT value FROM `tabSingles` WHERE doctype='Cash Voucher Series' AND field=%s",
			[field],
		)
		current = cint(row[0][0]) if row else 0
		if new_val > current:
			frappe.db.sql(
				"UPDATE `tabSingles` SET value=%s WHERE doctype='Cash Voucher Series' AND field=%s",
				[str(new_val), field],
			)
			updated[main_type] = new_val
			frappe.logger().info(
				f"Cash Voucher Series: {field} advanced from {current} to {new_val}"
			)
		else:
			updated[main_type] = current

	frappe.db.commit()
	return updated
