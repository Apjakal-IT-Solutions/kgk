import frappe
from kgk_customisations.file_management.external_file_utils import (
	get_video_paths_from_db,
	get_packet_scan_paths_from_db,
	serve_file_from_path
)


@frappe.whitelist()
def search_lot(lot_id):
	"""
	Search for videos and packet scans for a given lot_id
	Returns: dict with video_paths and packet_scan_paths
	"""
	if not lot_id:
		frappe.throw("Please provide a Lot ID")
	
	# Get video paths
	video_paths = get_video_paths_from_db(lot_id)
	
	# Get packet scan paths
	packet_scan_paths = get_packet_scan_paths_from_db(lot_id)
	
	return {
		'lot_id': lot_id,
		'videos': video_paths,
		'packet_scans': packet_scan_paths,
		'has_results': bool(video_paths or packet_scan_paths)
	}


@frappe.whitelist()
def serve_file(file_path):
	"""
	Serve a file from the given path
	"""
	if not file_path:
		frappe.throw("No file path provided")
	
	return serve_file_from_path(file_path, inline=True)
