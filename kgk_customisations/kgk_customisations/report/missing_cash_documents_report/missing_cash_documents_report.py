# Copyright (c) 2024, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint

def execute(filters=None):
	"""Execute Missing Cash Documents Report"""
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data

def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "missing_number",
			"label": "Missing Document Number",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "sequence_position",
			"label": "Position in Sequence",
			"fieldtype": "Int",
			"width": 150
		},
		{
			"fieldname": "previous_doc",
			"label": "Previous Document",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "next_doc",
			"label": "Next Document",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "gap_size",
			"label": "Gap Size",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Data",
			"width": 120
		}
	]

def get_data(filters):
	"""Get missing documents data"""
	# Get all existing documents
	documents = frappe.get_all(
		'Cash Document',
		fields=['name', 'document_number', 'transaction_date', 'status'],
		filters={'document_number': ['like', 'CD-%']},
		order_by='document_number'
	)
	
	if not documents:
		return []
	
	# Parse document numbers and create mapping
	doc_numbers = []
	doc_map = {}
	
	for doc in documents:
		parts = doc.document_number.split('-')
		if len(parts) >= 4:
			try:
				# Extract year, month, and sequence number
				year = parts[1]
				month = parts[2]
				seq_num = int(parts[3])
				
				key = f"{year}-{month}"
				if key not in doc_map:
					doc_map[key] = {}
				
				doc_map[key][seq_num] = doc
				doc_numbers.append((key, seq_num))
			except (ValueError, IndexError):
				continue
	
	if not doc_numbers:
		return []
	
	# Find missing documents
	missing_data = []
	
	for key in doc_map:
		year_month = key
		numbers = sorted(doc_map[key].keys())
		
		if len(numbers) < 2:
			continue
		
		# Check for gaps in sequence
		for i in range(numbers[0], numbers[-1] + 1):
			if i not in doc_map[key]:
				# Found a missing number
				missing_doc_number = f"CD-{year_month}-{i:05d}"
				
				# Find previous and next documents
				prev_doc = None
				next_doc = None
				
				# Find previous
				for j in range(i - 1, numbers[0] - 1, -1):
					if j in doc_map[key]:
						prev_doc = doc_map[key][j]['document_number']
						break
				
				# Find next
				for j in range(i + 1, numbers[-1] + 1):
					if j in doc_map[key]:
						next_doc = doc_map[key][j]['document_number']
						break
				
				# Calculate gap size
				gap_start = i
				gap_end = i
				while gap_end + 1 <= numbers[-1] and (gap_end + 1) not in doc_map[key]:
					gap_end += 1
				gap_size = gap_end - gap_start + 1
				
				missing_data.append({
					"missing_number": missing_doc_number,
					"sequence_position": i,
					"previous_doc": prev_doc or "N/A",
					"next_doc": next_doc or "N/A",
					"gap_size": gap_size,
					"status": "Missing"
				})
	
	# Sort by missing document number
	missing_data.sort(key=lambda x: x['missing_number'])
	
	return missing_data