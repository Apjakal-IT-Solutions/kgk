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
def search_all_files(lot_number: str):
    """Main search function - replaces your _refresh_thread"""
    start_time = frappe.utils.now()
    
    results = {
        "polish_video": search_polish_video(lot_number),
        "rough_video": search_rough_video(lot_number), 
        "advisor_files": search_advisor_files(lot_number),
        "scan_files": search_scan_files(lot_number)
    }
    
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