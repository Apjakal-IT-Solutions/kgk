# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FileSearchConfig(Document):
	pass


def get_dashboard_data():
	"""Return dashboard data for File Search Config"""
	return {
		"fieldname": "file_type",
		"non_standard_fieldnames": {},
		"transactions": [
			{
				"label": "Indexed Files",
				"items": ["File Index"]
			},
			{
				"label": "Searches",
				"items": ["Lot Search"]
			}
		]
	}


@frappe.whitelist()
def get_index_summary():
	"""
	Get summary statistics for File Search Config dashboard.
	Returns indexed file counts by type and storage usage.
	"""
	# Get file counts by type
	file_counts = frappe.db.sql("""
		SELECT 
			file_type,
			COUNT(*) as count,
			SUM(file_size) as total_size_mb
		FROM `tabFile Index`
		GROUP BY file_type
	""", as_dict=True)
	
	# Get total counts
	total_files = sum(row['count'] for row in file_counts)
	total_size_mb = sum(row['total_size_mb'] or 0 for row in file_counts)
	total_size_gb = total_size_mb / 1024
	
	# Get lot search count
	search_count = frappe.db.count("Lot Search")
	
	# Get last indexed timestamp
	config = frappe.get_single("File Search Config")
	last_indexed = config.last_indexed_on if config else None
	
	return {
		"file_counts": file_counts,
		"total_files": total_files,
		"total_size_mb": round(total_size_mb, 2),
		"total_size_gb": round(total_size_gb, 2),
		"search_count": search_count,
		"last_indexed": last_indexed
	}
