# file_management/utils/indexer.py
@frappe.whitelist()
def start_advisor_indexing():
    """Start background job to index advisor files"""
    frappe.enqueue(
        'your_app.file_management.utils.indexer.index_advisor_files',
        queue='long',
        timeout=3600,
        job_name=f'advisor_indexing_{frappe.utils.now()}'
    )
    return {"status": "started", "message": "Advisor file indexing started"}

def index_advisor_files():
    """Background job - replaces your DatabaseManager functionality"""
    try:
        # Clear existing advisor index
        frappe.db.delete("File Index", {"file_type": "advisor"})
        
        config = frappe.get_single("File Search Config")
        
        for directory_row in config.file_directories:
            if directory_row.file_type == "advisor" and directory_row.enabled:
                advisor_dir = Path(directory_row.directory_path)
                if not advisor_dir.exists():
                    continue
                
                for advisor_file in advisor_dir.rglob("*.adv"):
                    lot = extract_lot_number(advisor_file)
                    if lot:
                        frappe.get_doc({
                            "doctype": "File Index",
                            "lot_number": lot,
                            "file_type": "advisor",
                            "file_path": str(advisor_file),
                            "file_name": advisor_file.name,
                            "file_size": round(advisor_file.stat().st_size / (1024 * 1024), 2)
                        }).insert(ignore_permissions=True)
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Advisor indexing failed: {str(e)}")
        raise