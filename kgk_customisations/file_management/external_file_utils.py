# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

"""
Utility functions for accessing files from external SQLite databases and network shares.
These functions query external databases and convert UNC paths to Linux mount paths.
"""

import frappe
import sqlite3
import os
import mimetypes
import hashlib
from werkzeug.wrappers import Response


def get_external_db_path():
	"""Get the path to the external SQLite database from site config"""
	return frappe.get_site_config().get('external_sqlite_db_path', '/home/kgk/OnePc/file_search/file_index.db')


def convert_unc_to_mount(unc_path):
	"""
	Convert UNC path to Linux mount path.
	
	Args:
		unc_path (str): UNC path from Windows (e.g., \\nas-gradding\POLISH-VIDEO\file.mp4)
	
	Returns:
		str: Converted Linux mount path (e.g., /mnt/nas-gradding.local/POLISH-VIDEO/file.mp4)
		None: If path cannot be converted or file doesn't exist
	"""
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


def get_video_paths_from_db(lot_id, db_path=None):
	"""
	Query external SQLite database for video paths based on lot ID.
	
	Args:
		lot_id (str): The lot ID to search for
		db_path (str, optional): Path to SQLite database. Uses config default if not provided.
	
	Returns:
		dict: Dictionary with keys 'rough_video', 'polish_video', 'tension_video' containing mount paths
		      Returns empty dict if no results found or error occurs
	"""
	result = {
		'rough_video': None,
		'polish_video': None,
		'tension_video': None
	}
	
	try:
		if not db_path:
			db_path = get_external_db_path()
		
		if not os.path.exists(db_path):
			frappe.log_error(
				f"External database not found at {db_path}. Please check the path and permissions.",
				"External Database Not Found"
			)
			return result
		
		# Connect to the external SQLite database in immutable mode (read-only, no locking)
		conn = sqlite3.connect(f'file:{db_path}?immutable=1', uri=True)
		cursor = conn.cursor()
		
		# Query for files matching the lot_id
		query = """
			SELECT rough_path, polish_path, tension_path 
			FROM video_index 
			WHERE lot = ?
		"""
		
		cursor.execute(query, (lot_id,))
		results = cursor.fetchall()
		
		if results:
			# Get the first row (should only be one result per lot)
			rough_path, polish_path, tension_path = results[0]
			
			# Convert UNC paths to mounted Linux paths
			if rough_path:
				result['rough_video'] = convert_unc_to_mount(rough_path)
			
			if polish_path:
				result['polish_video'] = convert_unc_to_mount(polish_path)
			
			if tension_path:
				result['tension_video'] = convert_unc_to_mount(tension_path)
		
		conn.close()
		
	except Exception as e:
		frappe.log_error(
			f"Error querying video paths for lot {lot_id}: {str(e)}",
			"External Database Query Error"
		)
	
	return result


def get_packet_scan_paths_from_db(lot_id, db_path=None):
	"""
	Query external SQLite database for packet scan paths based on lot ID.
	
	Args:
		lot_id (str): The lot ID to search for
		db_path (str, optional): Path to SQLite database. Uses config default if not provided.
	
	Returns:
		list: List of converted mount paths for packet scans
		      Returns empty list if no results found or error occurs
	"""
	scan_paths = []
	
	try:
		if not db_path:
			db_path = get_external_db_path()
		
		if not os.path.exists(db_path):
			frappe.log_error(
				f"External database not found at {db_path}. Please check the path and permissions.",
				"External Database Not Found"
			)
			return scan_paths
		
		# Connect to the external SQLite database in immutable mode (read-only, no locking)
		conn = sqlite3.connect(f'file:{db_path}?immutable=1', uri=True)
		cursor = conn.cursor()
		
		# Query for all scan paths matching the lot_id
		query = """
			SELECT path 
			FROM scan_index 
			WHERE lot = ?
		"""
		
		cursor.execute(query, (lot_id,))
		results = cursor.fetchall()
		
		if results:
			for row in results:
				scan_path = row[0]
				
				if scan_path:
					# Convert UNC path to mounted Linux path
					converted_path = convert_unc_to_mount(scan_path)
					
					if converted_path:
						scan_paths.append(converted_path)
		
		conn.close()
		
	except Exception as e:
		frappe.log_error(
			f"Error querying packet scans for lot {lot_id}: {str(e)}",
			"External Database Query Error"
		)
	
	return scan_paths


def validate_mount_accessibility(mount_point):
	"""
	Check if a network mount point is accessible.
	
	Args:
		mount_point (str): Path to mount point (e.g., /mnt/nas-gradding.local/POLISH-VIDEO)
	
	Returns:
		tuple: (is_accessible: bool, error_message: str or None)
	"""
	if not mount_point:
		return False, "No mount point provided"
	
	# Check if mount point exists
	if not os.path.exists(mount_point):
		return False, f"Mount point does not exist: {mount_point}"
	
	# Check if it's actually mounted (for top-level mount directories)
	base_mount = '/'.join(mount_point.split('/')[:4])  # e.g., /mnt/nas-gradding.local
	
	if base_mount and not os.path.ismount(base_mount):
		return False, f"Network share is not mounted: {base_mount}"
	
	# Check if directory is readable
	if not os.access(mount_point, os.R_OK):
		return False, f"Mount point is not readable: {mount_point}"
	
	return True, None


def get_mime_type(file_path):
	"""
	Get MIME type for a file with comprehensive fallback mapping.
	
	Args:
		file_path (str): Path to the file
	
	Returns:
		str: MIME type string
	"""
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
			# Image formats
			'.jpg': 'image/jpeg',
			'.jpeg': 'image/jpeg',
			'.png': 'image/png',
			'.gif': 'image/gif',
			'.bmp': 'image/bmp',
			'.tiff': 'image/tiff',
			'.tif': 'image/tiff',
			'.svg': 'image/svg+xml',
			# Advisor files
			'.adv': 'application/octet-stream',
			# Office documents
			'.doc': 'application/msword',
			'.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			'.xls': 'application/vnd.ms-excel',
			'.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'.ppt': 'application/vnd.ms-powerpoint',
			'.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
			# Text formats
			'.txt': 'text/plain',
			'.csv': 'text/csv',
			'.json': 'application/json',
			'.xml': 'application/xml',
		}
		mime_type = mime_type_map.get(ext, 'application/octet-stream')
	
	return mime_type


def serve_file_from_path(file_path, inline=True):
	"""
	Serve a file from the network share with proper HTTP headers.
	
	Args:
		file_path (str): Full path to the file on the mounted network share
		inline (bool): If True, display inline (browser); if False, force download
	
	Returns:
		Response: Werkzeug Response object
	
	Raises:
		frappe.ValidationError: If file doesn't exist or mount is not accessible
	"""
	if not file_path:
		frappe.throw("No file path provided")
	
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
	mime_type = get_mime_type(file_path)
	
	# Read and serve the file
	with open(file_path, 'rb') as f:
		file_content = f.read()
	
	# Build response
	response = Response()
	response.data = file_content
	response.mimetype = mime_type
	
	disposition = 'inline' if inline else 'attachment'
	response.headers['Content-Disposition'] = f'{disposition}; filename="{file_name}"'
	response.headers['Accept-Ranges'] = 'bytes'
	response.headers['Cache-Control'] = 'public, max-age=3600'
	response.status_code = 200
	
	# Set frappe response
	frappe.local.response = response
	return response


def generate_pdf_thumbnail(pdf_path, size=320):
	"""
	Generate a thumbnail image from the first page of a PDF.
	Returns the path to the generated thumbnail PNG file.
	Uses pdf2image library (requires poppler-utils to be installed).
	
	Args:
		pdf_path (str): Path to the PDF file
		size (int): Target width for thumbnail (height auto-calculated)
	
	Returns:
		str: Path to generated thumbnail, or None if generation fails
	"""
	try:
		# Generate unique cache filename based on PDF path
		cache_dir = os.path.join(frappe.get_site_path(), 'private', 'thumbnails')
		os.makedirs(cache_dir, exist_ok=True)
		
		# Create hash of file path for unique filename
		file_hash = hashlib.md5(pdf_path.encode()).hexdigest()
		thumbnail_path = os.path.join(cache_dir, f"{file_hash}.png")
		
		# Return cached thumbnail if it exists and is newer than source
		if os.path.exists(thumbnail_path):
			if os.path.getmtime(thumbnail_path) >= os.path.getmtime(pdf_path):
				return thumbnail_path
		
		# Generate new thumbnail
		from pdf2image import convert_from_path
		
		# Convert only first page with size limit
		images = convert_from_path(
			pdf_path,
			first_page=1,
			last_page=1,
			size=(size, None),  # Width, height auto
			fmt='png'
		)
		
		if images:
			images[0].save(thumbnail_path, 'PNG')
			return thumbnail_path
		
		return None
		
	except ImportError:
		frappe.log_error(
			"pdf2image library not installed. Install with: pip install pdf2image\n"
			"Also requires poppler-utils: sudo apt-get install poppler-utils",
			"PDF Thumbnail Generation"
		)
		return None
	except Exception as e:
		frappe.log_error(f"Error generating PDF thumbnail: {str(e)}", "PDF Thumbnail Generation")
		return None


@frappe.whitelist()
def serve_pdf_thumbnail(file_path):
	"""
	Generate and serve a thumbnail for a PDF file.
	Returns PNG image of first page.
	"""
	if not file_path:
		frappe.throw("No file path provided")
	
	# Check if file exists
	if not os.path.exists(file_path):
		frappe.throw(f"File not found: {file_path}")
	
	# Check if it's a PDF
	if not file_path.lower().endswith('.pdf'):
		frappe.throw("File is not a PDF")
	
	# Generate thumbnail
	thumbnail_path = generate_pdf_thumbnail(file_path)
	
	if not thumbnail_path or not os.path.exists(thumbnail_path):
		frappe.throw("Failed to generate PDF thumbnail")
	
	# Serve the thumbnail image
	return serve_file_from_path(thumbnail_path, inline=True)


def generate_video_thumbnail(video_path, size=320):
	"""
	Generate a thumbnail image from the first frame of a video.
	Returns the path to the generated thumbnail PNG file.
	Uses ffmpeg (requires ffmpeg to be installed).
	
	Args:
		video_path (str): Path to the video file
		size (int): Target width for thumbnail (height auto-calculated)
	
	Returns:
		str: Path to generated thumbnail, or None if generation fails
	"""
	try:
		import subprocess
		
		# Generate unique cache filename based on video path
		cache_dir = os.path.join(frappe.get_site_path(), 'private', 'thumbnails')
		os.makedirs(cache_dir, exist_ok=True)
		
		# Create hash of file path for unique filename
		file_hash = hashlib.md5(video_path.encode()).hexdigest()
		thumbnail_path = os.path.join(cache_dir, f"{file_hash}_video.png")
		
		# Return cached thumbnail if it exists and is newer than source
		if os.path.exists(thumbnail_path):
			if os.path.getmtime(thumbnail_path) >= os.path.getmtime(video_path):
				return thumbnail_path
		
		# Generate new thumbnail using ffmpeg
		# Extract frame at 1 second, scale to target width
		cmd = [
			'ffmpeg',
			'-ss', '1',  # Seek to 1 second
			'-i', video_path,
			'-vframes', '1',  # Extract 1 frame
			'-vf', f'scale={size}:-1',  # Scale width, auto height
			'-y',  # Overwrite output
			thumbnail_path
		]
		
		result = subprocess.run(
			cmd,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			timeout=10
		)
		
		if result.returncode == 0 and os.path.exists(thumbnail_path):
			return thumbnail_path
		
		return None
		
	except FileNotFoundError:
		frappe.log_error(
			"ffmpeg not installed. Install with: sudo apt-get install ffmpeg",
			"Video Thumbnail Generation"
		)
		return None
	except Exception as e:
		frappe.log_error(f"Error generating video thumbnail: {str(e)}", "Video Thumbnail Generation")
		return None


@frappe.whitelist()
def serve_video_thumbnail(file_path):
	"""
	Generate and serve a thumbnail for a video file.
	Returns PNG image of first frame.
	"""
	if not file_path:
		frappe.throw("No file path provided")
	
	# Check if file exists
	if not os.path.exists(file_path):
		frappe.throw(f"File not found: {file_path}")
	
	# Check if it's a video
	video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
	if not any(file_path.lower().endswith(ext) for ext in video_extensions):
		frappe.throw("File is not a supported video format")
	
	# Generate thumbnail
	thumbnail_path = generate_video_thumbnail(file_path)
	
	if not thumbnail_path or not os.path.exists(thumbnail_path):
		frappe.throw("Failed to generate video thumbnail")
	
	# Serve the thumbnail image
	return serve_file_from_path(thumbnail_path, inline=True)
