# Copyright (c) 2025, KGK Customisations and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from kgk_customisations.kgk_customisations.utils.permission_manager import PermissionManager


class StoneProcessingStage(Document):
	def validate(self):
		"""Validate processing stage data"""
		if self.weight and self.weight <= 0:
			frappe.throw("Weight must be greater than 0")
		
		if self.esp_percent and (self.esp_percent < 0 or self.esp_percent > 100):
			frappe.throw("ESP % must be between 0 and 100")
	
	def before_insert(self):
		"""Set default values before inserting"""
		if not self.stage_date:
			self.stage_date = frappe.utils.today()
	
	def after_insert(self):
		"""Update parent stone after inserting processing stage"""
		if self.parent:
			self.update_parent_stone_status()
	
	def update_parent_stone_status(self):
		"""Update parent stone's current stage and latest values"""
		try:
			parent_stone = frappe.get_doc("Stone", self.parent)
			
			# Update current processing stage
			parent_stone.current_stage = self.processing_stage
			
			# Update latest weight and valuation
			if self.weight:
				parent_stone.current_weight = self.weight
			
			if self.esp_amount:
				parent_stone.current_value = self.esp_amount
			
			# Update quality specifications from latest stage
			if self.shape:
				parent_stone.shape = self.shape
			if self.color:
				parent_stone.color = self.color
			if self.clarity:
				parent_stone.clarity = self.clarity
			
			# Save with permission check - system operation (stage update)
			PermissionManager.save_with_permission_check(parent_stone, ignore_for_system=True)
			
		except Exception as e:
			frappe.log_error(f"Failed to update parent stone status: {str(e)}", "Stone Processing Stage Error")