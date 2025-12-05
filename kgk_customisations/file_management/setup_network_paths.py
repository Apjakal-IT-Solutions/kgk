"""
Setup network paths for File Search Config based on FileSearcher.py configuration
Run with: bench --site [sitename] execute kgk_customisations.file_management.setup_network_paths.setup_file_search_config
"""

import frappe


def setup_file_search_config():
    """Configure File Search Config with network paths from FileSearcher.py"""
    
    # Network path configurations from FileSearcher.py
    network_paths = [
        # Polish Video directories (skip -F, -S folders)
        {
            "file_type": "Polish Video",
            "directory_path": r"\\video-pc1\data",
            "file_extension": ".mp4",
            "enabled": 1
        },
        {
            "file_type": "Polish Video",
            "directory_path": r"\\video-pc1\Vision_data",
            "file_extension": ".mp4",
            "enabled": 1
        },
        {
            "file_type": "Polish Video",
            "directory_path": r"\\nas-gradding\POLISH-VIDEO",
            "file_extension": ".mp4",
            "enabled": 1
        },
        # Rough Video directories (only -R folders)
        {
            "file_type": "Rough Video",
            "directory_path": r"\\video-pc1\data",
            "file_extension": ".mp4",
            "enabled": 1
        },
        {
            "file_type": "Rough Video",
            "directory_path": r"\\video-pc1\Vision_data",
            "file_extension": ".mp4",
            "enabled": 1
        },
        {
            "file_type": "Rough Video",
            "directory_path": r"\\nas-gradding\POLISH-VIDEO",
            "file_extension": ".mp4",
            "enabled": 1
        },
        # Advisor files
        {
            "file_type": "Advisor",
            "directory_path": r"\\Nas-planning\stones",
            "file_extension": ".adv",
            "enabled": 1
        },
        # Scan files (multiple extensions)
        {
            "file_type": "Scan",
            "directory_path": r"\\roughvideo1\My Scans2",
            "file_extension": ".pdf",
            "enabled": 1
        },
        {
            "file_type": "Scan",
            "directory_path": r"\\roughvideo1\My Scans2",
            "file_extension": ".png",
            "enabled": 1
        },
        {
            "file_type": "Scan",
            "directory_path": r"\\roughvideo1\My Scans2",
            "file_extension": ".jpg",
            "enabled": 1
        },
        {
            "file_type": "Scan",
            "directory_path": r"\\roughvideo1\My Scans2",
            "file_extension": ".jpeg",
            "enabled": 1
        },
        {
            "file_type": "Scan",
            "directory_path": r"\\roughvideo1\My Scans2",
            "file_extension": ".tif",
            "enabled": 1
        }
    ]
    
    # Get or create File Search Config (Single DocType)
    if frappe.db.exists("File Search Config", "File Search Config"):
        config = frappe.get_doc("File Search Config", "File Search Config")
        # Clear existing directories
        config.file_directories = []
    else:
        config = frappe.new_doc("File Search Config")
    
    # Add all network paths
    for path_config in network_paths:
        config.append("file_directories", path_config)
    
    # Set default search timeout
    config.search_timeout = 180
    
    # Save configuration
    config.save()
    frappe.db.commit()
    
    print(f"✓ File Search Config updated with {len(network_paths)} directory entries")
    print("\nConfigured paths:")
    for entry in config.file_directories:
        print(f"  - {entry.file_type}: {entry.directory_path} ({entry.file_extension})")
    
    return config


def verify_network_paths():
    """Verify that network paths are accessible"""
    from pathlib import Path
    
    config = frappe.get_doc("File Search Config", "File Search Config")
    
    print("\n=== Network Path Verification ===")
    accessible = []
    inaccessible = []
    
    # Get unique paths
    unique_paths = set()
    for entry in config.file_directories:
        if entry.enabled:
            unique_paths.add(entry.directory_path)
    
    for path_str in unique_paths:
        path = Path(path_str)
        if path.exists():
            accessible.append(path_str)
            print(f"✓ Accessible: {path_str}")
        else:
            inaccessible.append(path_str)
            print(f"✗ NOT accessible: {path_str}")
    
    print(f"\nSummary: {len(accessible)} accessible, {len(inaccessible)} inaccessible")
    
    return {
        "accessible": accessible,
        "inaccessible": inaccessible
    }


if __name__ == "__main__":
    setup_file_search_config()
    verify_network_paths()
