# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os

class CashDocumentSupportingFile(Document):
	def before_insert(self):
		"""Set upload information when file is added"""
		self.uploaded_by = frappe.session.user
		self.upload_date = frappe.utils.now()
		
		# Set file size if attachment is provided
		if self.file_attachment:
			self.set_file_size()
	
	def before_save(self):
		"""Update file information before saving"""
		if self.file_attachment and not self.file_size:
			self.set_file_size()
	
	def validate(self):
		"""Validate file attachment and details"""
		# Only validate if both required fields are present (to avoid issues with partial saves)
		if self.file_attachment and self.file_name:
			# Set default file name from attachment if not provided
			if not self.file_name:
				self.file_name = os.path.basename(self.file_attachment)
			
			# Validate file size limits (max 10MB)
			file_size = self.get_file_size_bytes()
			if file_size > 10 * 1024 * 1024:  # 10MB in bytes
				frappe.throw("File size cannot exceed 10MB")
		elif not self.file_attachment and not self.file_name:
			# Both missing - likely initial row creation, don't validate yet
			pass
		else:
			# One missing - validate only if we're not in a child table add scenario
			if frappe.flags.in_test or (self.file_attachment and not self.file_name):
				if self.file_attachment:
					self.file_name = os.path.basename(self.file_attachment)
			elif not frappe.flags.ignore_validate:
				if not self.file_attachment:
					frappe.throw("File attachment is required")
				if not self.file_name:
					frappe.throw("File name is required")
	
	def set_file_size(self):
		"""Set human-readable file size"""
		if self.file_attachment:
			size_bytes = self.get_file_size_bytes()
			self.file_size = self.format_file_size(size_bytes)
	
	def get_file_size_bytes(self):
		"""Get file size in bytes"""
		if not self.file_attachment:
			return 0
		
		try:
			file_doc = frappe.get_doc("File", {"file_url": self.file_attachment})
			if file_doc and hasattr(file_doc, 'file_size'):
				return file_doc.file_size or 0
		except:
			pass
		
		return 0
	
	def format_file_size(self, size_bytes):
		"""Format file size in human readable format"""
		if size_bytes == 0:
			return "0 B"
		
		size_names = ["B", "KB", "MB", "GB"]
		import math
		i = int(math.floor(math.log(size_bytes, 1024)))
		p = math.pow(1024, i)
		s = round(size_bytes / p, 2)
		return f"{s} {size_names[i]}"
	
	@frappe.whitelist()
	def get_file_preview_url(self):
		"""Get URL for file preview if supported"""
		if not self.file_attachment:
			return None
		
		# Get file extension
		file_ext = os.path.splitext(self.file_attachment)[1].lower()
		
		# Define previewable file types
		previewable_types = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.txt', '.doc', '.docx']
		
		if file_ext in previewable_types:
			return self.file_attachment
		
		return None
	
	@frappe.whitelist()
	def download_file(self):
		"""Download the attached file"""
		if not self.file_attachment:
			frappe.throw("No file attached")
		
		# Log file download
		frappe.log_error(
			f"File downloaded: {self.file_name} by {frappe.session.user}",
			"Cash Document File Download"
		)
		
		return self.file_attachment