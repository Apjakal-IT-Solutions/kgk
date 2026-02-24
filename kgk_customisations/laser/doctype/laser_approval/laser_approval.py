# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today
from kgk_customisations.file_management.external_file_utils import (
	get_video_paths_from_db,
	get_packet_scan_paths_from_db,
	serve_file_from_path
)


class LaserApproval(Document):
	def validate(self):
		"""Runs on every save - populate video paths from external database"""
		if self.org_lot_id:
			self.get_video_indexes()
			self.get_packet_scans()
	
	def before_insert(self):
		"""Prepopulate document_users table with all employees from Laser Approval User Item"""
		if not self.document_users or len(self.document_users) == 0:
			self.populate_users()
	
	def before_submit(self):
		"""Set approval_date to today when document is submitted"""		
		self.approval_date = today()
		"""Final check for video paths before submission"""
		self.get_video_indexes()
		self.get_packet_scans()
	
	def populate_users(self):
		"""Fetch all users from Laser Approval User Item and add them to document_users"""
		# Get all users from Laser Approval User Item
		users = frappe.get_all(
			'Laser Approval User Item',
			fields=['name', 'full_name'],
			order_by='full_name asc'
		)
		
		if users:
			# Only clear if document is new (not saved yet)
			if self.is_new():
				self.document_users = []
			else:
				# For existing documents, don't clear - just log a warning
				frappe.log_error(
					f"populate_users called on existing document {self.name}",
					"Laser Approval Warning"
				)
				return
			
			# Add each user to the child table
			for user in users:
				self.append('document_users', {
					'employee_name': user.name,
					'status': 'No'  # Default status
				})
			
			if self.is_new():
				frappe.msgprint(
					f'Added {len(users)} users to the document',
					title='Users Prepopulated',
				indicator='green'
			)
	
	def get_video_indexes(self):
		"""Query external SQLite database and populate video path fields based on org_lot_id"""
		if not self.org_lot_id:
			return
		
		# Get video paths from external database
		video_paths = get_video_paths_from_db(self.org_lot_id)
		
		# Count how many paths were found
		paths_found = 0
		
		if video_paths.get('rough_video'):
			self.rough_video = video_paths['rough_video']
			paths_found += 1
		
		if video_paths.get('polish_video'):
			self.polish_video = video_paths['polish_video']
			paths_found += 1
		
		if video_paths.get('tension_video'):
			self.tension_video = video_paths['tension_video']
			paths_found += 1
		
		# Show appropriate message to user
		if paths_found > 0:
			frappe.msgprint(
				f'Found {paths_found} video path(s) from external database',
				title='Video Paths Loaded',
				indicator='green'
			)
		elif any(video_paths.values()):
			# Paths were found in DB but couldn't be mounted
			frappe.msgprint(
				f'An error occured and has been logged for review by system Administrator.',
				title='Server Error',
				indicator='orange'
			)
		else:
			frappe.msgprint(
				f'No matching records found in database for Lot ID: {self.org_lot_id}',
				title='No Database Records',
				indicator='orange'
			)
	
	def get_packet_scans(self):
		"""Query external SQLite database and populate packet scan paths based on org_lot_id"""
		if not self.org_lot_id:
			return
		
		# Get packet scan paths from external database
		scan_paths = get_packet_scan_paths_from_db(self.org_lot_id)
		
		if scan_paths:
			# Clear existing packet scans
			self.packet_scans = []
			
			# Add each scan to the child table
			for scan_path in scan_paths:
				self.append('packet_scans', {
					'image_path': scan_path
				})
			
			frappe.msgprint(
				f'Found {len(scan_paths)} packet scan(s) from external database',
				title='Packet Scans Loaded',
				indicator='green'
			)
		else:
			frappe.msgprint(
				f'No packet scans found in database for Lot ID: {self.org_lot_id}',
				title='No Scan Records',
				indicator='orange'
			)

@frappe.whitelist()
def refresh_user_list(docname):
	"""Refresh the user list for an existing document"""
	doc = frappe.get_doc('Laser Approval', docname)
	
	# Get all users from Laser Approval User Item
	users = frappe.get_all(
		'Laser Approval User Item',
		fields=['name', 'full_name'],
		order_by='full_name asc'
	)
	
	if users:
		# Clear and repopulate for existing documents
		doc.document_users = []
		
		for user in users:
			doc.append('document_users', {
				'employee_name': user.name,
				'status': 'No'
			})
		
		doc.save()
		return {'message': f'User list refreshed with {len(doc.document_users)} users'}
	
	return {'message': 'No users found'}

@frappe.whitelist()
def serve_video_file(docname, video_type):
	"""
	Serve video file from mounted network path.
	video_type: 'rough', 'polish', or 'tension'
	"""	
	# Get the document
	doc = frappe.get_doc('Laser Approval', docname)
	
	# Get the appropriate file path based on video_type
	file_path = None
	if video_type == 'rough':
		file_path = doc.rough_video
	elif video_type == 'polish':
		file_path = doc.polish_video
	elif video_type == 'tension':
		file_path = doc.tension_video
	
	if not file_path:
		frappe.throw(f"No {video_type} video path found for this document")
	
	# Use the global file serving function
	return serve_file_from_path(file_path, inline=True)


@frappe.whitelist()
def serve_packet_scan_file(docname, row_id):
	"""
	Serve packet scan file from mounted network path.
	row_id: The name (id) of the Packet Scan Item child row
	"""
	# Get the parent document
	doc = frappe.get_doc('Laser Approval', docname)
	
	# Find the specific packet scan item
	file_path = None
	for item in doc.packet_scans:
		if item.name == row_id:
			file_path = item.image_path
			break
	
	if not file_path:
		frappe.throw(f"No packet scan found with ID: {row_id}")
	
	# Use the global file serving function
	return serve_file_from_path(file_path, inline=True)