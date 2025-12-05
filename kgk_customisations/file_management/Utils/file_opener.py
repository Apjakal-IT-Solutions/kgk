# file_management/utils/file_opener.py
"""
File opener utility for opening files from network shares.
Provides cross-platform file opening support.
"""

import frappe
import subprocess
import platform
import os
from pathlib import Path
from typing import List, Dict


def open_file(file_path: str) -> bool:
    """
    Open file using system default application.
    
    Args:
        file_path: Full path to file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            frappe.logger().error(f"File does not exist: {file_path}")
            return False
        
        system = platform.system()
        
        if system == "Windows":
            os.startfile(str(path))
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(path)], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(path)], check=True)
        
        frappe.logger().info(f"Opened file: {file_path}")
        return True
        
    except Exception as e:
        frappe.log_error(f"Error opening file {file_path}: {str(e)}", "File Opener Error")
        return False


@frappe.whitelist()
def open_lot_files(lot_number: str, file_types: str = None):
    """
    Open all files for a lot number.
    
    Args:
        lot_number: 8-digit lot number
        file_types: Comma-separated file types to open (e.g., "polish_video,scan")
                   If None, opens all file types
    
    Returns:
        dict: Summary of opened files
    """
    try:
        # Import here to avoid circular dependency
        from kgk_customisations.file_management.Utils.file_operations import search_all_files
        
        # Parse file_types
        if file_types:
            if isinstance(file_types, str):
                file_types = [ft.strip() for ft in file_types.split(",")]
        else:
            file_types = None
        
        # Get all files for lot
        results = search_all_files(lot_number, use_cache=1)
        
        opened = []
        failed = []
        
        # Open polish video
        if (not file_types or "polish_video" in file_types):
            if results.get("polish_video", {}).get("found"):
                path = results["polish_video"]["path"]
                if open_file(path):
                    opened.append({"type": "polish_video", "path": path})
                else:
                    failed.append({"type": "polish_video", "path": path})
        
        # Open rough video
        if (not file_types or "rough_video" in file_types):
            if results.get("rough_video", {}).get("found"):
                path = results["rough_video"]["path"]
                if open_file(path):
                    opened.append({"type": "rough_video", "path": path})
                else:
                    failed.append({"type": "rough_video", "path": path})
        
        # Open advisor files
        if (not file_types or "advisor" in file_types):
            for file_data in results.get("advisor_files", []):
                path = file_data["path"]
                if open_file(path):
                    opened.append({"type": "advisor", "path": path})
                else:
                    failed.append({"type": "advisor", "path": path})
        
        # Open scan files
        if (not file_types or "scan" in file_types):
            for file_data in results.get("scan_files", []):
                path = file_data["path"]
                if open_file(path):
                    opened.append({"type": "scan", "path": path})
                else:
                    failed.append({"type": "scan", "path": path})
        
        return {
            "status": "success",
            "lot_number": lot_number,
            "opened": len(opened),
            "failed": len(failed),
            "files_opened": opened,
            "files_failed": failed,
            "message": f"Opened {len(opened)} files for lot {lot_number}"
        }
        
    except Exception as e:
        frappe.log_error(f"Error opening files for lot {lot_number}: {str(e)}", "File Opener Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def open_file_by_path(file_path: str):
    """
    Open a single file by path.
    
    Args:
        file_path: Full path to file
        
    Returns:
        dict: Success/failure status
    """
    try:
        if open_file(file_path):
            return {
                "status": "success",
                "message": f"Opened file: {file_path}"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to open file: {file_path}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_file_info(file_path: str):
    """
    Get detailed information about a file.
    
    Args:
        file_path: Full path to file
        
    Returns:
        dict: File information
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return {
                "status": "error",
                "message": "File does not exist"
            }
        
        stat = path.stat()
        
        return {
            "status": "success",
            "file_name": path.name,
            "file_path": str(path),
            "file_size": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_time": frappe.utils.get_datetime(stat.st_mtime),
            "created_time": frappe.utils.get_datetime(stat.st_ctime),
            "extension": path.suffix,
            "is_file": path.is_file(),
            "is_dir": path.is_dir()
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting file info for {file_path}: {str(e)}", "File Info Error")
        return {
            "status": "error",
            "message": str(e)
        }
