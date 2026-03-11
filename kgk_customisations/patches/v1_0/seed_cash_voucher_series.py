"""
Patch: seed_cash_voucher_series

Initialise the Cash Voucher Series Single DocType so that all five counter
fields exist in tabSingles with a starting value of 0.

This makes the first document created for each type receive the number 1.
"""

import frappe


def execute():
	# Counter fields introduced by the Cash Voucher Series Single DocType.
	counter_fields = [
		"cash_counter",
		"bank_counter",
		"cash_2_counter",
		"bank_2_counter",
		"je_counter",
	]

	for field in counter_fields:
		existing = frappe.db.get_single_value("Cash Voucher Series", field)
		if existing is None:
			# Seed a zero starting value. Use set_single_value() so Frappe manages
			# the tabSingles row correctly (INSERT or UPDATE as needed).
			frappe.db.set_single_value("Cash Voucher Series", field, 0)

	frappe.db.commit()
