# utils/file_opener.py
import frappe
import subprocess
import platform
import os
from pathlib import Path
from typing import Union, List, Dict

@frappe.whitelist()
def open_file(file_path: str):
    """
    Open file using system default application.
    
    Args:
        file_path: Absolute path to file
        
    Returns:
        dict: Status and message
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
        
        system = platform.system()
        
        if system == "Windows":
            os.startfile(str(path))
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(path)], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(path)], check=True)
        
        frappe.logger().info(f"Opened file: {file_path}")
        
        return {
            "status": "success",
            "message": f"File opened: {path.name}"
        }
        
    except Exception as e:
        error_msg = f"Failed to open file: {str(e)}"
        frappe.log_error(error_msg, "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def open_multiple_files(file_paths: Union[str, List[str]]):
    """
    Open multiple files at once.
    
    Args:
        file_paths: JSON string or list of file paths
        
    Returns:
        dict: Status with counts
    """
    try:
        # Handle JSON string input from web request
        if isinstance(file_paths, str):
            import json
            file_paths = json.loads(file_paths)
        
        if not isinstance(file_paths, list):
            return {
                "status": "error",
                "message": "file_paths must be a list"
            }
        
        results = []
        success_count = 0
        failed_count = 0
        
        for file_path in file_paths:
            result = open_file(file_path)
            results.append({
                "file": file_path,
                "status": result["status"]
            })
            
            if result["status"] == "success":
                success_count += 1
            else:
                failed_count += 1
        
        return {
            "status": "success" if failed_count == 0 else "partial",
            "opened": success_count,
            "failed": failed_count,
            "total": len(file_paths),
            "results": results,
            "message": f"Opened {success_count} of {len(file_paths)} files"
        }
        
    except Exception as e:
        error_msg = f"Batch file opening failed: {str(e)}"
        frappe.log_error(error_msg, "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def open_lot_files(lot_number: str, file_types: Union[str, List[str]] = None):
    """
    Open all files associated with a lot number.
    
    Args:
        lot_number: 8-digit lot number
        file_types: Optional list of file types to open (polish_video, rough_video, advisor, scan)
                   If None, opens all file types. Can be JSON string or list.
        
    Returns:
        dict: Status with opened files
    """
    try:
        # Handle JSON string input
        if isinstance(file_types, str):
            import json
            file_types = json.loads(file_types)
        
        # Build filters
        filters = {"lot_number": lot_number}
        if file_types:
            filters["file_type"] = ["in", file_types]
        
        # Get all indexed files for this lot
        files = frappe.get_all(
            "File Index",
            filters=filters,
            fields=["file_path", "file_name", "file_type"]
        )
        
        if not files:
            return {
                "status": "info",
                "message": f"No files found for lot {lot_number}",
                "opened": 0
            }
        
        # Extract file paths
        file_paths = [f.file_path for f in files]
        
        # Open all files
        result = open_multiple_files(file_paths)
        result["lot_number"] = lot_number
        result["file_details"] = files
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to open lot files: {str(e)}"
        frappe.log_error(error_msg, "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def reveal_in_explorer(file_path: str):
    """
    Reveal file in system file explorer (Windows Explorer, macOS Finder, Linux file manager).
    
    Args:
        file_path: Absolute path to file
        
    Returns:
        dict: Status and message
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }
        
        system = platform.system()
        
        if system == "Windows":
            # Open Explorer and select the file
            subprocess.run(["explorer", "/select,", str(path)], check=True)
        elif system == "Darwin":  # macOS
            # Open Finder and select the file
            subprocess.run(["open", "-R", str(path)], check=True)
        else:  # Linux
            # Open file manager at parent directory (no standard way to select file)
            subprocess.run(["xdg-open", str(path.parent)], check=True)
        
        frappe.logger().info(f"Revealed in explorer: {file_path}")
        
        return {
            "status": "success",
            "message": f"File revealed in explorer: {path.name}"
        }
        
    except Exception as e:
        error_msg = f"Failed to reveal file: {str(e)}"
        frappe.log_error(error_msg, "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }
