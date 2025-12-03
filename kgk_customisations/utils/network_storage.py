# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

"""
Network Storage Utility - Provides integration with network file shares
Similar to Django's NetworkPath class for accessing \\192.168.1.114\Fantasy\e-dox
"""

import frappe
import os
import subprocess
from pathlib import Path
import tempfile

class NetworkPath:
	"""
	Utility class to manage network file storage operations.
	Provides methods to connect, read, write, and manage files on network shares.
	"""
	
	def __init__(self, network_path=None, username=None, password=None):
		"""
		Initialize NetworkPath with connection details.
		
		Args:
			network_path: UNC path like \\\\192.168.1.114\\Fantasy\\e-dox
			username: Network username (optional)
			password: Network password (optional)
		"""
		# Get from Cash Management Settings if not provided
		if not network_path:
			network_path = frappe.db.get_single_value("Cash Management Settings", "network_file_path")
		
		self.network_path = network_path or "\\\\192.168.1.114\\Fantasy\\e-dox"
		self.username = username
		self.password = password
		self.is_mounted = False
		self.mount_point = None
	
	def connect(self):
		"""
		Connect/mount the network share.
		On Linux, this may require CIFS/SMB mounting.
		"""
		try:
			# For Linux systems, mount the network share
			if os.name != 'nt':  # Not Windows
				# Create a temporary mount point
				self.mount_point = tempfile.mkdtemp(prefix="network_share_")
				
				# Convert Windows UNC path to Linux format
				# \\192.168.1.114\Fantasy\e-dox -> //192.168.1.114/Fantasy/e-dox
				linux_path = self.network_path.replace('\\\\', '//').replace('\\', '/')
				
				# Mount command
				mount_cmd = [
					'sudo', 'mount', '-t', 'cifs',
					linux_path,
					self.mount_point
				]
				
				if self.username:
					mount_cmd.extend(['-o', f'username={self.username}'])
				if self.password:
					mount_cmd.extend(['-o', f'password={self.password}'])
				
				# Execute mount
				result = subprocess.run(mount_cmd, capture_output=True, text=True)
				
				if result.returncode == 0:
					self.is_mounted = True
					frappe.logger().info(f"Network share mounted at {self.mount_point}")
				else:
					frappe.log_error(f"Failed to mount network share: {result.stderr}", "Network Storage Error")
					return False
			else:
				# On Windows, UNC paths work directly
				self.mount_point = self.network_path
				self.is_mounted = os.path.exists(self.mount_point)
			
			return self.is_mounted
			
		except Exception as e:
			frappe.log_error(f"Network path connection error: {str(e)}", "Network Storage Error")
			return False
	
	def disconnect(self):
		"""Disconnect/unmount the network share"""
		try:
			if self.is_mounted and self.mount_point and os.name != 'nt':
				subprocess.run(['sudo', 'umount', self.mount_point], capture_output=True)
				os.rmdir(self.mount_point)
				self.is_mounted = False
				frappe.logger().info("Network share unmounted")
		except Exception as e:
			frappe.log_error(f"Error disconnecting network share: {str(e)}", "Network Storage Error")
	
	def get_file_path(self, year, document_number, suffix=""):
		"""
		Get the full file path for a document.
		
		Args:
			year: Document year
			document_number: Document number
			suffix: File suffix (A, B, C, etc.)
		
		Returns:
			Full path to the file
		"""
		if not self.mount_point:
			if not self.connect():
				return None
		
		# Build path: {mount_point}/{year}/{document_number}{suffix}.pdf
		file_name = f"{document_number}{suffix}.pdf"
		year_folder = os.path.join(self.mount_point, str(year))
		full_path = os.path.join(year_folder, file_name)
		
		return full_path
	
	def file_exists(self, year, document_number, suffix=""):
		"""Check if a file exists on the network share"""
		file_path = self.get_file_path(year, document_number, suffix)
		if not file_path:
			return False
		return os.path.exists(file_path)
	
	def save_file(self, year, document_number, file_content, suffix=""):
		"""
		Save a file to the network share.
		
		Args:
			year: Document year
			document_number: Document number
			file_content: File content (bytes)
			suffix: File suffix (A, B, C, etc.)
		
		Returns:
			True if successful, False otherwise
		"""
		try:
			file_path = self.get_file_path(year, document_number, suffix)
			if not file_path:
				return False
			
			# Ensure year folder exists
			year_folder = os.path.dirname(file_path)
			os.makedirs(year_folder, exist_ok=True)
			
			# Write file
			with open(file_path, 'wb') as f:
				f.write(file_content)
			
			frappe.logger().info(f"File saved to network storage: {file_path}")
			return True
			
		except Exception as e:
			frappe.log_error(f"Error saving file to network storage: {str(e)}", "Network Storage Error")
			return False
	
	def read_file(self, year, document_number, suffix=""):
		"""
		Read a file from the network share.
		
		Args:
			year: Document year
			document_number: Document number
			suffix: File suffix (A, B, C, etc.)
		
		Returns:
			File content (bytes) or None if error
		"""
		try:
			file_path = self.get_file_path(year, document_number, suffix)
			if not file_path or not os.path.exists(file_path):
				return None
			
			with open(file_path, 'rb') as f:
				return f.read()
				
		except Exception as e:
			frappe.log_error(f"Error reading file from network storage: {str(e)}", "Network Storage Error")
			return None
	
	def delete_file(self, year, document_number, suffix=""):
		"""Delete a file from the network share"""
		try:
			file_path = self.get_file_path(year, document_number, suffix)
			if file_path and os.path.exists(file_path):
				os.remove(file_path)
				frappe.logger().info(f"File deleted from network storage: {file_path}")
				return True
			return False
		except Exception as e:
			frappe.log_error(f"Error deleting file from network storage: {str(e)}", "Network Storage Error")
			return False
	
	def list_files(self, year):
		"""List all files for a given year"""
		try:
			if not self.mount_point:
				if not self.connect():
					return []
			
			year_folder = os.path.join(self.mount_point, str(year))
			if not os.path.exists(year_folder):
				return []
			
			return os.listdir(year_folder)
			
		except Exception as e:
			frappe.log_error(f"Error listing files from network storage: {str(e)}", "Network Storage Error")
			return []
	
	def __enter__(self):
		"""Context manager enter"""
		self.connect()
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""Context manager exit"""
		self.disconnect()


# Convenience functions
def get_network_storage():
	"""Get a NetworkPath instance with settings from Cash Management Settings"""
	return NetworkPath()

def save_to_network(year, document_number, file_content, suffix=""):
	"""Save a file to network storage"""
	with NetworkPath() as ns:
		return ns.save_file(year, document_number, file_content, suffix)

def read_from_network(year, document_number, suffix=""):
	"""Read a file from network storage"""
	with NetworkPath() as ns:
		return ns.read_file(year, document_number, suffix)

def check_network_file_exists(year, document_number, suffix=""):
	"""Check if a file exists on network storage"""
	with NetworkPath() as ns:
		return ns.file_exists(year, document_number, suffix)
