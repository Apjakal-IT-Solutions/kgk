# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GradingReportPercentageItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		clarity_percentage: DF.Percent
		color_percentage: DF.Percent
		cut_percentage: DF.Percent
		fluency_percentage: DF.Percent
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		polish_percentage: DF.Percent
		symmetry_percentage: DF.Percent
	# end: auto-generated types
	pass
