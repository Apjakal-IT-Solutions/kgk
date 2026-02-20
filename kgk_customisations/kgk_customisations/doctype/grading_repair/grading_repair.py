# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GradingRepair(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from kgk_customisations.kgk_customisations.doctype.grading_report_percentage_item.grading_report_percentage_item import GradingReportPercentageItem
		from kgk_customisations.kgk_customisations.doctype.grading_report_pieces_item.grading_report_pieces_item import GradingReportPiecesItem

		amended_from: DF.Link | None
		date: DF.Date
		gia_rep: DF.Int
		grp_rep: DF.Int
		percent_values: DF.Table[GradingReportPercentageItem]
		piece_values: DF.Table[GradingReportPiecesItem]
		week: DF.Int
	# end: auto-generated types
	pass
