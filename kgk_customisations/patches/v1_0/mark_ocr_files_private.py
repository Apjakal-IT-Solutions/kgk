import frappe

def execute():
	"""Mark all OCR Data Upload files as private for security"""
	
	# Get all OCR Data Upload documents
	ocr_uploads = frappe.get_all("OCR Data Upload", 
		fields=["name", "excel_file"], 
		filters={"excel_file": ["is", "set"]})
	
	frappe.logger().info(f"Found {len(ocr_uploads)} OCR uploads to check")
	
	updated_count = 0
	
	for upload in ocr_uploads:
		if upload.excel_file:
			try:
				# Find the file document
				file_doc = frappe.get_doc("File", {"file_url": upload.excel_file})
				
				if not file_doc.is_private:
					file_doc.is_private = 1
					file_doc.save()
					updated_count += 1
					frappe.logger().info(f"Marked file {upload.excel_file} as private")
					
			except frappe.DoesNotExistError:
				frappe.logger().warning(f"File document not found for {upload.excel_file}")
			except Exception as e:
				frappe.logger().error(f"Error updating file {upload.excel_file}: {str(e)}")
	
	frappe.logger().info(f"Updated {updated_count} files to private status")
	frappe.db.commit()
