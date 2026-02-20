# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GradingReportPiecesItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		clarity_piece: DF.Int
		colory_piece: DF.Int
		cut_piece: DF.Int
		fluency_piece: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		polish_piece: DF.Int
		symmetry_piece: DF.Int
	# end: auto-generated types
	pass
