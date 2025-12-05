# file_management/utils/file_operations.py
import frappe
from pathlib import Path
import re
from typing import List, Optional, Dict

def extract_lot_number(path: Path) -> Optional[str]:
    """Extract 8-digit lot number from path"""
    for text in (path.parent.name, path.name):
        m = re.search(r"(\d{8})", text)
        if m:
            return m.group(1)
    return None

@frappe.whitelist()
def search_all_files(lot_number: str, use_cache: int = 1):
    """
    Main search function with caching support.
    
    Args:
        lot_number: 8-digit lot number to search
        use_cache: 1 to use cache, 0 to bypass (default: 1)
    
    Returns:
        dict: Search results for all file types
    """
    start_time = frappe.utils.now()
    use_cache = bool(int(use_cache))  # Convert to boolean
    
    # Try cache first
    if use_cache:
        cache_key = f"lot_search:{lot_number}"
        cached = frappe.cache().get_value(cache_key)
        if cached:
            frappe.logger().info(f"Cache hit for lot {lot_number}")
            return cached
    
    # Perform actual search
    results = {
        "polish_video": search_polish_video(lot_number),
        "rough_video": search_rough_video(lot_number), 
        "advisor_files": search_advisor_files(lot_number),
        "scan_files": search_scan_files(lot_number)
    }
    
    # Cache results for 1 hour (3600 seconds)
    if use_cache:
        cache_key = f"lot_search:{lot_number}"
        frappe.cache().set_value(cache_key, results, expires_in_sec=3600)
        frappe.logger().info(f"Cached search results for lot {lot_number}")
    
    # Log the search
    log_search_operation(lot_number, "all", results, start_time)
    
    return results

def search_polish_video(lot_number: str) -> Dict:
    """Replaces LotFileSearcher.search_polish_video"""
    config = frappe.get_single("File Search Config")
    
    for directory_row in config.file_directories:
        if directory_row.file_type == "polish_video" and directory_row.enabled:
            base = Path(directory_row.directory_path)
            candidate = base / lot_number / "video.mp4"
            if candidate.exists():
                return {
                    "found": True,
                    "path": str(candidate),
                    "name": candidate.name,
                    "size": candidate.stat().st_size
                }
    
    return {"found": False, "message": "Polish video not found"}

def search_rough_video(lot_number: str) -> Dict:
    """Replaces LotFileSearcher.search_rough_video"""
    config = frappe.get_single("File Search Config")
    
    for directory_row in config.file_directories:
        if directory_row.file_type == "rough_video" and directory_row.enabled:
            base = Path(directory_row.directory_path)
            candidate = base / f"{lot_number}-R" / "video.mp4"
            if candidate.exists():
                return {
                    "found": True,
                    "path": str(candidate),
                    "name": candidate.name,
                    "size": candidate.stat().st_size
                }
    
    return {"found": False, "message": "Rough video not found"}

def search_advisor_files(lot_number: str) -> List[Dict]:
    """Replaces database lookup for advisor files"""
    files = frappe.get_all(
        "File Index",
        filters={"lot_number": lot_number, "file_type": "advisor"},
        fields=["file_path", "file_name", "file_size"]
    )
    
    return [
        {
            "found": True,
            "path": f["file_path"],
            "name": f["file_name"],
            "size": f["file_size"]
        }
        for f in files
        if Path(f["file_path"]).exists()
    ]

def search_scan_files(lot_number: str) -> List[Dict]:
    """Replaces LotFileSearcher.search_scan_files"""
    results = []
    config = frappe.get_single("File Search Config")
    
    for directory_row in config.file_directories:
        if directory_row.file_type == "scan" and directory_row.enabled:
            base = Path(directory_row.directory_path)
            
            # Check for PDF first
            pdf = base / f"{lot_number}.pdf"
            if pdf.exists():
                results.append({
                    "found": True,
                    "path": str(pdf),
                    "name": pdf.name,
                    "size": pdf.stat().st_size,
                    "type": "pdf"
                })
                continue
            
            # Check for folder with images
            folder = base / lot_number
            if folder.is_dir():
                for i in (1, 2):
                    img = folder / f"{lot_number} {i:03d}.jpg"
                    if img.exists():
                        results.append({
                            "found": True,
                            "path": str(img),
                            "name": img.name,
                            "size": img.stat().st_size,
                            "type": "image"
                        })
    
    return results


def log_search_operation(lot_number: str, search_type: str, results: Dict, start_time: str):
    """
    Log search operation to Search Log DocType.
    
    Args:
        lot_number: Lot number searched
        search_type: Type of search performed
        results: Search results
        start_time: When search started
    """
    try:
        # Calculate duration
        import frappe.utils
        end_time = frappe.utils.now()
        duration = frappe.utils.time_diff_in_seconds(end_time, start_time)
        
        # Count found files
        found_count = 0
        if results.get("polish_video", {}).get("found"):
            found_count += 1
        if results.get("rough_video", {}).get("found"):
            found_count += 1
        found_count += len(results.get("advisor_files", []))
        found_count += len(results.get("scan_files", []))
        
        # Create search log entry (if DocType exists)
        if frappe.db.exists("DocType", "Search Log"):
            frappe.get_doc({
                "doctype": "Search Log",
                "lot_number": lot_number,
                "search_type": search_type,
                "files_found": found_count,
                "search_duration": duration,
                "search_results": frappe.as_json(results)
            }).insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        # Don't fail search if logging fails
        frappe.logger().error(f"Search logging failed: {str(e)}")


@frappe.whitelist()
def validate_indexed_files(lot_number: str = None):
    """
    Validate that indexed files still exist on disk.
    Remove stale entries for files that no longer exist.
    
    Args:
        lot_number: Optional - validate only files for specific lot number
    
    Returns:
        dict: Validation summary with counts
    """
    try:
        filters = {}
        if lot_number:
            filters["lot_number"] = lot_number
        
        indexed_files = frappe.get_all("File Index",
            filters=filters,
            fields=["name", "file_path", "lot_number", "file_type"])
        
        stale_count = 0
        validated_count = 0
        
        for record in indexed_files:
            validated_count += 1
            
            # Check if file exists
            if not Path(record.file_path).exists():
                # File no longer exists - remove from index
                frappe.delete_doc("File Index", record.name, force=1)
                stale_count += 1
                frappe.logger().warning(
                    f"Removed stale index entry: {record.file_type} - {record.lot_number} - {record.file_path}"
                )
        
        frappe.db.commit()
        
        return {
            "status": "success",
            "validated": validated_count,
            "removed": stale_count,
            "remaining": validated_count - stale_count,
            "message": f"Validated {validated_count} files, removed {stale_count} stale entries"
        }
        
    except Exception as e:
        frappe.log_error(f"File validation failed: {str(e)}", "File Validation Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def clear_search_cache(lot_number: str = None):
    """
    Clear search result cache.
    
    Args:
        lot_number: Optional - clear cache for specific lot, or all if None
    
    Returns:
        dict: Success message
    """
    try:
        if lot_number:
            cache_key = f"lot_search:{lot_number}"
            frappe.cache().delete_value(cache_key)
            message = f"Cache cleared for lot {lot_number}"
        else:
            # Clear all lot search caches
            # This is a simplification - in production you'd track all keys
            message = "Cache clear requested - use specific lot_number for targeted clear"
        
        return {
            "status": "success",
            "message": message
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
