# file_management/utils/indexer.py
import frappe
from pathlib import Path
import re
from typing import Optional

def extract_lot_number(path) -> Optional[str]:
    """Extract 8-digit lot number from path (accepts string or Path object)"""
    if isinstance(path, str):
        path = Path(path)
    
    for text in (path.parent.name, path.name):
        m = re.search(r"(\d{8})", text)
        if m:
            return m.group(1)
    return None

@frappe.whitelist()
def start_advisor_indexing():
    """Start background job to index advisor files"""
    frappe.enqueue(
        'kgk_customisations.file_management.Utils.indexer.index_advisor_files',
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


def index_polish_videos():
    """Index polish video files from configured directories"""
    try:
        # Clear existing polish video index
        frappe.db.delete("File Index", {"file_type": "polish_video"})
        
        config = frappe.get_single("File Search Config")
        count = 0
        
        for directory_row in config.file_directories:
            if directory_row.file_type == "Polish Video" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    frappe.logger().warning(f"Polish video directory does not exist: {base}")
                    continue
                
                # Recursively find all .mp4 files
                for video_file in base.rglob("*.mp4"):
                    parent_folder = video_file.parent.name
                    
                    # Skip sparkle (-F) and fluorescence (-S) folders
                    if parent_folder.endswith("-F") or parent_folder.endswith("-S"):
                        continue
                    
                    # Skip rough videos (will index separately)
                    if parent_folder.endswith("-R"):
                        continue
                    
                    lot = extract_lot_number(video_file)
                    if lot:
                        frappe.get_doc({
                            "doctype": "File Index",
                            "lot_number": lot,
                            "file_type": "polish_video",
                            "file_path": str(video_file),
                            "file_name": video_file.name,
                            "file_size": round(video_file.stat().st_size / (1024 * 1024), 2),
                            "indexed_on": frappe.utils.now()
                        }).insert(ignore_permissions=True)
                        count += 1
                        
                        # Commit every 100 records to avoid memory issues
                        if count % 100 == 0:
                            frappe.db.commit()
        
        frappe.db.commit()
        frappe.logger().info(f"Indexed {count} polish video files")
        
    except Exception as e:
        frappe.log_error(f"Polish video indexing failed: {str(e)}", "File Indexing Error")
        raise


def index_rough_videos():
    """Index rough video files from configured directories"""
    try:
        # Clear existing rough video index
        frappe.db.delete("File Index", {"file_type": "rough_video"})
        
        config = frappe.get_single("File Search Config")
        count = 0
        
        for directory_row in config.file_directories:
            if directory_row.file_type == "Rough Video" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    frappe.logger().warning(f"Rough video directory does not exist: {base}")
                    continue
                
                # Recursively find all .mp4 files
                for video_file in base.rglob("*.mp4"):
                    parent_folder = video_file.parent.name
                    
                    # Skip sparkle (-F) and fluorescence (-S) folders
                    if parent_folder.endswith("-F") or parent_folder.endswith("-S"):
                        continue
                    
                    # Only index rough videos (ending with -R)
                    if not parent_folder.endswith("-R"):
                        continue
                    
                    lot = extract_lot_number(video_file)
                    if lot:
                        frappe.get_doc({
                            "doctype": "File Index",
                            "lot_number": lot,
                            "file_type": "rough_video",
                            "file_path": str(video_file),
                            "file_name": video_file.name,
                            "file_size": round(video_file.stat().st_size / (1024 * 1024), 2),
                            "indexed_on": frappe.utils.now()
                        }).insert(ignore_permissions=True)
                        count += 1
                        
                        # Commit every 100 records
                        if count % 100 == 0:
                            frappe.db.commit()
        
        frappe.db.commit()
        frappe.logger().info(f"Indexed {count} rough video files")
        
    except Exception as e:
        frappe.log_error(f"Rough video indexing failed: {str(e)}", "File Indexing Error")
        raise


def index_scan_files():
    """Index scan files (PDF, PNG, JPG, JPEG, TIF) from configured directories"""
    try:
        # Clear existing scan index
        frappe.db.delete("File Index", {"file_type": "scan"})
        
        config = frappe.get_single("File Search Config")
        extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tif"}
        count = 0
        
        for directory_row in config.file_directories:
            if directory_row.file_type == "Scan" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    frappe.logger().warning(f"Scan directory does not exist: {base}")
                    continue
                
                # Recursively find all scan files
                for scan_file in base.rglob("*"):
                    if scan_file.is_file() and scan_file.suffix.lower() in extensions:
                        lot = extract_lot_number(scan_file)
                        if lot:
                            frappe.get_doc({
                                "doctype": "File Index",
                                "lot_number": lot,
                                "file_type": "scan",
                                "file_path": str(scan_file),
                                "file_name": scan_file.name,
                                "file_size": round(scan_file.stat().st_size / (1024 * 1024), 2),
                                "indexed_on": frappe.utils.now()
                            }).insert(ignore_permissions=True)
                            count += 1
                            
                            # Commit every 100 records
                            if count % 100 == 0:
                                frappe.db.commit()
        
        frappe.db.commit()
        frappe.logger().info(f"Indexed {count} scan files")
        
    except Exception as e:
        frappe.log_error(f"Scan file indexing failed: {str(e)}", "File Indexing Error")
        raise


@frappe.whitelist()
def start_full_indexing():
    """Trigger background job to index ALL file types"""
    frappe.enqueue(
        'kgk_customisations.file_management.Utils.indexer.index_all_files',
        queue='long',
        timeout=7200,  # 2 hours
        job_name=f'full_indexing_{frappe.utils.now()}'
    )
    return {"status": "started", "message": "Full file indexing started in background"}


def index_all_files():
    """Index all file types in sequence with progress updates"""
    try:
        frappe.publish_realtime('indexing_progress', {
            'status': 'Starting full indexing...',
            'progress': 0
        })
        
        # Index polish videos
        frappe.logger().info("Starting polish video indexing...")
        index_polish_videos()
        frappe.publish_realtime('indexing_progress', {
            'status': 'Polish videos indexed',
            'progress': 25
        })
        
        # Index rough videos
        frappe.logger().info("Starting rough video indexing...")
        index_rough_videos()
        frappe.publish_realtime('indexing_progress', {
            'status': 'Rough videos indexed',
            'progress': 50
        })
        
        # Index advisor files
        frappe.logger().info("Starting advisor file indexing...")
        index_advisor_files()
        frappe.publish_realtime('indexing_progress', {
            'status': 'Advisor files indexed',
            'progress': 75
        })
        
        # Index scan files
        frappe.logger().info("Starting scan file indexing...")
        index_scan_files()
        frappe.publish_realtime('indexing_progress', {
            'status': 'Indexing complete!',
            'progress': 100
        })
        
        # Update last indexed timestamp
        frappe.db.set_value("File Search Config", "File Search Config", 
                          "last_indexed_on", frappe.utils.now())
        frappe.db.commit()
        
        # Get final counts
        counts = frappe.db.sql("""
            SELECT file_type, COUNT(*) as count
            FROM `tabFile Index`
            GROUP BY file_type
        """, as_dict=True)
        
        summary = {file_type: 0 for file_type in ["polish_video", "rough_video", "advisor", "scan"]}
        for row in counts:
            summary[row.file_type] = row.count
        
        frappe.logger().info(f"Full indexing complete: {summary}")
        
        return {
            "status": "success",
            "message": "All files indexed successfully",
            "summary": summary
        }
        
    except Exception as e:
        frappe.log_error(f"Full indexing failed: {str(e)}", "File Indexing Error")
        frappe.publish_realtime('indexing_progress', {
            'status': f'Indexing failed: {str(e)}',
            'progress': -1
        })
        raise
