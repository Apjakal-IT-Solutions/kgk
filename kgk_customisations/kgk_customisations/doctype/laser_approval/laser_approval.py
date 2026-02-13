# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today
import sqlite3
import os
import mimetypes


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
		try:
			# Define the path to your external SQLite database
			db_path = frappe.get_site_config().get('external_sqlite_db_path', '/home/kgk/OnePc/file_search/file_index.db')
			
			if not os.path.exists(db_path):
				error_msg = f"External database not found at {db_path}. Please check the path and permissions."
				frappe.log_error(error_msg, "Laser Approval File Attachment")
				frappe.msgprint(
					error_msg,
					title='Database Not Found',
					indicator='red'
				)
				return
			
			# Connect to the external SQLite database in immutable mode (read-only, no locking)
			conn = sqlite3.connect(f'file:{db_path}?immutable=1', uri=True)
			cursor = conn.cursor()
			
			# Query for files matching the org_lot_id (mapped to 'lot' column)
			query = """
				SELECT rough_path, polish_path, tension_path 
				FROM video_index 
				WHERE lot = ?
			"""
			
			cursor.execute(query, (self.org_lot_id,))
			results = cursor.fetchall()
			
			if results:
				# Get the first row (should only be one result per lot)
				rough_path, polish_path, tension_path = results[0]
				
				# Convert UNC paths to mounted Linux paths and store
				paths_found = 0
				
				if polish_path:
					self.polish_video = self.convert_unc_to_mount(polish_path)
					if self.polish_video:
						paths_found += 1
				
				if rough_path:
					self.rough_video = self.convert_unc_to_mount(rough_path)
					if self.rough_video:
						paths_found += 1
				
				if tension_path:
					self.tension_video = self.convert_unc_to_mount(tension_path)
					if self.tension_video:
						paths_found += 1
				
				if paths_found > 0:
					frappe.msgprint(
						f'Found {paths_found} video path(s) from external database',
						title='Video Paths Loaded',
						indicator='green'
					)
				else:
					frappe.msgprint(
						f'Video paths found but could not access mount points',
						title='Mount Point Issue',
						indicator='orange'
					)
			else:
				frappe.msgprint(
					f'No matching records found in database for Lot ID: {self.org_lot_id}',
					title='No Database Records',
					indicator='orange'
				)
			
			conn.close()
			
		except Exception as e:
			error_msg = f"Error attaching files from external database for {self.name}: {str(e)}"
			frappe.log_error(error_msg, "Laser Approval File Attachment Error")
			frappe.msgprint(
				f"Error accessing external database: {str(e)}",
				title='Database Error',
				indicator='red'
			)
	
	def convert_unc_to_mount(self, unc_path):
		"""Convert UNC path to Linux mount path"""
		if not unc_path:
			return None
			
		# Normalize path separators
		path = unc_path.replace('\\', '/')
		
		# Convert UNC paths to mount points
		# nas-gradding shares
		if path.startswith('//nas-gradding/POLISH-VIDEO'):
			path = path.replace('//nas-gradding', '/mnt/nas-gradding.local')
		elif path.startswith('//nas-gradding/ROUGH-VIDEO'):
			path = path.replace('//nas-gradding', '/mnt/nas-gradding.local')
		elif path.startswith('//nas-gradding/PARCEL-SCANS'):
			path = path.replace('//nas-gradding', '/mnt/nas-gradding.local')
		# nas-planning shares
		elif path.startswith('//nas-planning/ROUGH VIDEO'):
			path = path.replace('//nas-planning', '/mnt/nas-planning.local')
		elif path.startswith('//nas-planning/TENSION-STONE-VIDEO'):
			path = path.replace('//nas-planning', '/mnt/nas-planning.local')
		elif path.startswith('//nas-planning/stones'):
			path = path.replace('//nas-planning', '/mnt/nas-planning.local')
		elif path.startswith('//nas-planning'):
			path = path.replace('//nas-planning', '/mnt/nas-planning.local')
		
		# Verify file exists
		if os.path.exists(path):
			return path
		else:
			frappe.log_error(
				f"Mount: {path}\nOriginal: {unc_path}",
				"File Not Found"
			)
			return None
	
	def get_packet_scans(self):
		"""Query external SQLite database and populate packet scan paths based on org_lot_id"""
		try:
			# Define the path to your external SQLite database
			db_path = frappe.get_site_config().get('external_sqlite_db_path', '/home/kgk/OnePc/file_search/file_index.db')
			
			if not os.path.exists(db_path):
				error_msg = f"External database not found at {db_path}. Please check the path and permissions."
				frappe.log_error(error_msg, "Laser Approval Packet Scan")
				return
			
			# Connect to the external SQLite database in immutable mode (read-only, no locking)
			conn = sqlite3.connect(f'file:{db_path}?immutable=1', uri=True)
			cursor = conn.cursor()
			
			# Query for all scan paths matching the org_lot_id (mapped to 'lot' column)
			query = """
				SELECT path 
				FROM scan_index 
				WHERE lot = ?
			"""
			
			cursor.execute(query, (self.org_lot_id,))
			results = cursor.fetchall()
			
			if results:
				# Clear existing packet scans
				self.packet_scans = []
				
				scans_found = 0
				for row in results:
					scan_path = row[0]
					
					if scan_path:
						# Convert UNC path to mounted Linux path
						converted_path = self.convert_unc_to_mount(scan_path)
						
						if converted_path:
							# Add to child table
							self.append('packet_scans', {
								'image_path': converted_path
							})
							scans_found += 1
				
				if scans_found > 0:
					frappe.msgprint(
						f'Found {scans_found} packet scan(s) from external database',
						title='Packet Scans Loaded',
						indicator='green'
					)
				else:
					frappe.msgprint(
						f'Packet scan paths found but could not access mount points',
						title='Mount Point Issue',
						indicator='orange'
					)
			else:
				frappe.msgprint(
					f'No packet scans found in database for Lot ID: {self.org_lot_id}',
					title='No Scan Records',
					indicator='orange'
				)
			
			conn.close()
			
		except Exception as e:
			error_msg = f"Error fetching packet scans from external database for {self.name}: {str(e)}"
			frappe.log_error(error_msg, "Laser Approval Packet Scan Error")
			frappe.msgprint(
				f"Error accessing scan database: {str(e)}",
				title='Database Error',
				indicator='red'
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
	Serve video file from mounted network path
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
	
	# Check if file exists
	if not os.path.exists(file_path):
		frappe.throw(f"Video file not found at path: {file_path}")
	
	# Get file info
	file_name = os.path.basename(file_path)
	mime_type, _ = mimetypes.guess_type(file_name)
	
	# If MIME type not detected, use comprehensive mapping
	if not mime_type:
		ext = os.path.splitext(file_name)[1].lower()
		mime_type_map = {
			# Video formats
			'.mp4': 'video/mp4',
			'.avi': 'video/x-msvideo',
			'.mov': 'video/quicktime',
			'.wmv': 'video/x-ms-wmv',
			'.mkv': 'video/x-matroska',
			# PDF
			'.pdf': 'application/pdf',
			# Image formats (packet scans)
			'.jpg': 'image/jpeg',
			'.jpeg': 'image/jpeg',
			'.png': 'image/png',
			'.gif': 'image/gif',
			'.bmp': 'image/bmp',
			'.tiff': 'image/tiff',
			'.tif': 'image/tiff',
			# Advisor files
			'.adv': 'application/octet-stream',
			# Office documents
			'.doc': 'application/msword',
			'.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			'.xls': 'application/vnd.ms-excel',
			'.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
		}
		mime_type = mime_type_map.get(ext, 'application/octet-stream')
	
	# Read and serve the file
	with open(file_path, 'rb') as f:
		file_content = f.read()
	
	# Build a proper response using frappe's response object
	from werkzeug.wrappers import Response
	
	response = Response()
	response.data = file_content
	response.mimetype = mime_type
	response.headers['Content-Disposition'] = f'inline; filename="{file_name}"'
	response.headers['Accept-Ranges'] = 'bytes'
	response.headers['Cache-Control'] = 'public, max-age=3600'
	response.status_code = 200
	
	# Return the response object - Frappe should handle it
	frappe.local.response = response
	return response

@frappe.whitelist()
def serve_packet_scan_file(docname, row_id):
	"""
	Serve packet scan file from mounted network path
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
	
	# Check if file exists
	if not os.path.exists(file_path):
		# Check if it's a mount point issue
		mount_point = file_path.split('/')[1:4]  # Extract /mnt/nas-xxx.local
		mount_path = '/' + '/'.join(mount_point) if len(mount_point) >= 3 else None
		
		error_msg = f"File not found: {os.path.basename(file_path)}<br><br>"
		error_msg += f"<b>Path:</b> {file_path}<br><br>"
		
		if mount_path and not os.path.ismount(mount_path):
			error_msg += f"<b>Issue:</b> Network share is not mounted<br>"
			error_msg += f"Please contact system administrator to mount: {mount_path}"
		else:
			error_msg += f"<b>Issue:</b> File may have been moved or deleted from the network share"
		
		frappe.throw(error_msg, title="File Not Accessible")
	
	# Get file info
	file_name = os.path.basename(file_path)
	mime_type, _ = mimetypes.guess_type(file_name)
	
	# If MIME type not detected, use comprehensive mapping
	if not mime_type:
		ext = os.path.splitext(file_name)[1].lower()
		mime_type_map = {
			# PDF
			'.pdf': 'application/pdf',
			# Image formats (packet scans)
			'.jpg': 'image/jpeg',
			'.jpeg': 'image/jpeg',
			'.png': 'image/png',
			'.gif': 'image/gif',
			'.bmp': 'image/bmp',
			'.tiff': 'image/tiff',
			'.tif': 'image/tiff',
		}
		mime_type = mime_type_map.get(ext, 'application/octet-stream')
	
	# Read and serve the file
	with open(file_path, 'rb') as f:
		file_content = f.read()
	
	# Build a proper response using frappe's response object
	from werkzeug.wrappers import Response
	
	response = Response()
	response.data = file_content
	response.mimetype = mime_type
	response.headers['Content-Disposition'] = f'inline; filename="{file_name}"'
	response.headers['Accept-Ranges'] = 'bytes'
	response.headers['Cache-Control'] = 'public, max-age=3600'
	response.status_code = 200
	
	# Return the response object - Frappe should handle it
	frappe.local.response = response
	return response