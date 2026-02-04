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


@frappe.whitelist()
def validate_indexed_files(lot_number=None):
    """
    Check if indexed files still exist and remove stale entries.
    
    Args:
        lot_number: Optional lot number to validate specific lot files only
        
    Returns:
        dict: Validation summary with counts
    """
    try:
        filters = {}
        if lot_number:
            filters["lot_number"] = lot_number
        
        indexed_files = frappe.get_all(
            "File Index",
            filters=filters,
            fields=["name", "file_path", "lot_number", "file_type", "file_name"]
        )
        
        stale_count = 0
        stale_files = []
        
        for record in indexed_files:
            file_path = Path(record.file_path)
            if not file_path.exists():
                frappe.delete_doc("File Index", record.name, force=1)
                stale_count += 1
                stale_files.append({
                    "lot_number": record.lot_number,
                    "file_type": record.file_type,
                    "file_name": record.file_name,
                    "path": record.file_path
                })
                frappe.logger().info(f"Removed stale entry: {record.file_name} (lot: {record.lot_number})")
        
        frappe.db.commit()
        
        message = f"Validated {len(indexed_files)} files. Removed {stale_count} stale entries."
        frappe.logger().info(message)
        
        return {
            "status": "success",
            "validated": len(indexed_files),
            "removed": stale_count,
            "stale_files": stale_files,
            "message": message
        }
        
    except Exception as e:
        frappe.log_error(f"File validation failed: {str(e)}", "File Validation Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def index_new_files_only():
    """
    Incremental indexing - only index files added since last full index.
    Much faster than full re-indexing for large file sets.
    """
    try:
        config = frappe.get_single("File Search Config")
        last_indexed = config.last_indexed_on
        
        if not last_indexed:
            return {
                "status": "info",
                "message": "No previous index found. Run full indexing first."
            }
        
        frappe.publish_realtime('indexing_progress', {
            'status': 'Starting incremental indexing...',
            'progress': 0
        })
        
        new_files_count = 0
        
        # Index new polish videos
        for directory_row in config.file_directories:
            if directory_row.file_type == "Polish Video" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    continue
                
                for video_file in base.rglob("*.mp4"):
                    parent_folder = video_file.parent.name
                    
                    # Skip special folders
                    if parent_folder.endswith(("-F", "-S", "-R")):
                        continue
                    
                    # Check if file is newer than last index
                    if video_file.stat().st_mtime > last_indexed.timestamp():
                        lot = extract_lot_number(video_file)
                        if lot:
                            # Check if already indexed
                            exists = frappe.db.exists("File Index", {
                                "lot_number": lot,
                                "file_type": "polish_video",
                                "file_path": str(video_file)
                            })
                            
                            if not exists:
                                frappe.get_doc({
                                    "doctype": "File Index",
                                    "lot_number": lot,
                                    "file_type": "polish_video",
                                    "file_path": str(video_file),
                                    "file_name": video_file.name,
                                    "file_size": round(video_file.stat().st_size / (1024 * 1024), 2),
                                    "indexed_on": frappe.utils.now()
                                }).insert(ignore_permissions=True)
                                new_files_count += 1
        
        frappe.publish_realtime('indexing_progress', {
            'status': 'Polish videos checked',
            'progress': 25
        })
        
        # Index new rough videos
        for directory_row in config.file_directories:
            if directory_row.file_type == "Rough Video" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    continue
                
                for video_file in base.rglob("*.mp4"):
                    parent_folder = video_file.parent.name
                    
                    if not parent_folder.endswith("-R"):
                        continue
                    
                    if video_file.stat().st_mtime > last_indexed.timestamp():
                        lot = extract_lot_number(video_file)
                        if lot:
                            exists = frappe.db.exists("File Index", {
                                "lot_number": lot,
                                "file_type": "rough_video",
                                "file_path": str(video_file)
                            })
                            
                            if not exists:
                                frappe.get_doc({
                                    "doctype": "File Index",
                                    "lot_number": lot,
                                    "file_type": "rough_video",
                                    "file_path": str(video_file),
                                    "file_name": video_file.name,
                                    "file_size": round(video_file.stat().st_size / (1024 * 1024), 2),
                                    "indexed_on": frappe.utils.now()
                                }).insert(ignore_permissions=True)
                                new_files_count += 1
        
        frappe.publish_realtime('indexing_progress', {
            'status': 'Rough videos checked',
            'progress': 50
        })
        
        # Index new advisor files
        for directory_row in config.file_directories:
            if directory_row.file_type == "Advisor" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    continue
                
                for advisor_file in base.rglob("*.adv"):
                    if advisor_file.stat().st_mtime > last_indexed.timestamp():
                        lot = extract_lot_number(advisor_file)
                        if lot:
                            exists = frappe.db.exists("File Index", {
                                "lot_number": lot,
                                "file_type": "advisor",
                                "file_path": str(advisor_file)
                            })
                            
                            if not exists:
                                frappe.get_doc({
                                    "doctype": "File Index",
                                    "lot_number": lot,
                                    "file_type": "advisor",
                                    "file_path": str(advisor_file),
                                    "file_name": advisor_file.name,
                                    "file_size": round(advisor_file.stat().st_size / (1024 * 1024), 2),
                                    "indexed_on": frappe.utils.now()
                                }).insert(ignore_permissions=True)
                                new_files_count += 1
        
        frappe.publish_realtime('indexing_progress', {
            'status': 'Advisor files checked',
            'progress': 75
        })
        
        # Index new scan files
        extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tif"}
        for directory_row in config.file_directories:
            if directory_row.file_type == "Scan" and directory_row.enabled:
                base = Path(directory_row.directory_path)
                if not base.exists():
                    continue
                
                for scan_file in base.rglob("*"):
                    if scan_file.is_file() and scan_file.suffix.lower() in extensions:
                        if scan_file.stat().st_mtime > last_indexed.timestamp():
                            lot = extract_lot_number(scan_file)
                            if lot:
                                exists = frappe.db.exists("File Index", {
                                    "lot_number": lot,
                                    "file_type": "scan",
                                    "file_path": str(scan_file)
                                })
                                
                                if not exists:
                                    frappe.get_doc({
                                        "doctype": "File Index",
                                        "lot_number": lot,
                                        "file_type": "scan",
                                        "file_path": str(scan_file),
                                        "file_name": scan_file.name,
                                        "file_size": round(scan_file.stat().st_size / (1024 * 1024), 2),
                                        "indexed_on": frappe.utils.now()
                                    }).insert(ignore_permissions=True)
                                    new_files_count += 1
        
        frappe.db.commit()
        
        frappe.publish_realtime('indexing_progress', {
            'status': f'Incremental indexing complete! Added {new_files_count} new files.',
            'progress': 100
        })
        
        message = f"Incremental indexing complete. Added {new_files_count} new files since {last_indexed}."
        frappe.logger().info(message)
        
        return {
            "status": "success",
            "new_files": new_files_count,
            "last_indexed": last_indexed,
            "message": message
        }
        
    except Exception as e:
        frappe.log_error(f"Incremental indexing failed: {str(e)}", "Incremental Indexing Error")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_file_statistics():
    """
    Get comprehensive file indexing statistics for dashboard and reporting.
    
    Returns:
        dict: Statistics including file counts, storage usage, index health
    """
    try:
        # Get file counts and storage by type
        by_type = frappe.db.sql("""
            SELECT 
                file_type,
                COUNT(*) as count,
                SUM(file_size) as size_mb
            FROM `tabFile Index`
            GROUP BY file_type
            ORDER BY file_type
        """, as_dict=True)
        
        # Calculate totals
        total_files = sum(row['count'] for row in by_type)
        total_size_mb = sum(row['size_mb'] or 0 for row in by_type)
        total_size_gb = total_size_mb / 1024
        
        # Add size_gb to each type
        for row in by_type:
            row['size_gb'] = (row['size_mb'] or 0) / 1024
        
        # Get unique lot count
        unique_lots = frappe.db.sql("""
            SELECT COUNT(DISTINCT lot_number) as count
            FROM `tabFile Index`
        """)[0][0]
        
        # Get total search count
        total_searches = frappe.db.count("Lot Search")
        
        # Get recent searches (last 10)
        recent_searches = frappe.db.sql("""
            SELECT 
                lot_number,
                modified as searched_at
            FROM `tabLot Search`
            ORDER BY modified DESC
            LIMIT 10
        """, as_dict=True)
        
        # Add results count to recent searches (mock data - would need proper tracking)
        for search in recent_searches:
            search['results_count'] = frappe.db.count("File Index", {
                "lot_number": search['lot_number']
            })
        
        # Get last indexed timestamp
        config = frappe.get_single("File Search Config")
        last_indexed = config.last_indexed_on if config else None
        
        # Calculate index health
        index_health = calculate_index_health(last_indexed, total_files)
        
        return {
            "status": "success",
            "by_type": by_type,
            "total_files": total_files,
            "total_size_mb": round(total_size_mb, 2),
            "total_size_gb": round(total_size_gb, 2),
            "unique_lots": unique_lots,
            "total_searches": total_searches,
            "recent_searches": recent_searches,
            "last_indexed": last_indexed,
            "index_health": index_health
        }
        
    except Exception as e:
        frappe.log_error(f"Get file statistics failed: {str(e)}", "File Statistics Error")
        return {
            "status": "error",
            "message": str(e),
            "by_type": [],
            "total_files": 0,
            "total_size_gb": 0,
            "unique_lots": 0,
            "total_searches": 0,
            "recent_searches": [],
            "last_indexed": None,
            "index_health": "Unknown"
        }


def calculate_index_health(last_indexed, total_files):
    """
    Calculate index health status based on age and file count.
    
    Returns:
        str: Excellent, Good, Fair, Poor, or Unknown
    """
    if not last_indexed:
        return "Poor" if total_files > 0 else "Unknown"
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    indexed_dt = last_indexed if isinstance(last_indexed, datetime) else frappe.utils.get_datetime(last_indexed)
    age = now - indexed_dt
    
    # Health based on index age
    if age < timedelta(days=1):
        return "Excellent"
    elif age < timedelta(days=3):
        return "Good"
    elif age < timedelta(days=7):
        return "Fair"
    else:
        return "Poor"


@frappe.whitelist()
def get_index_health_report():
    """
    Get detailed index health report with recommendations.
    
    Returns:
        dict: Health report with actionable recommendations
    """
    try:
        stats = get_file_statistics()
        
        recommendations = []
        warnings = []
        
        # Check index age
        if stats['index_health'] == 'Poor':
            warnings.append("Index is outdated (>7 days old)")
            recommendations.append("Run full reindex or incremental index")
        elif stats['index_health'] == 'Fair':
            warnings.append("Index age is getting stale (3-7 days)")
            recommendations.append("Consider running incremental index")
        
        # Check for empty index
        if stats['total_files'] == 0:
            warnings.append("No files indexed")
            recommendations.append("Run initial indexing to populate File Index")
        
        # Check for imbalanced file types
        if stats['by_type']:
            type_counts = {row['file_type']: row['count'] for row in stats['by_type']}
            
            if type_counts.get('polish_video', 0) == 0:
                warnings.append("No polish videos indexed")
                recommendations.append("Check polish video directory configuration")
            
            if type_counts.get('rough_video', 0) == 0:
                warnings.append("No rough videos indexed")
                recommendations.append("Check rough video directory configuration")
        
        # Check storage usage
        if stats['total_size_gb'] > 1000:  # > 1TB
            warnings.append(f"Large storage footprint: {stats['total_size_gb']:.2f} GB")
            recommendations.append("Consider archiving old files or validating index")
        
        health_score = 100
        health_score -= len(warnings) * 15
        health_score = max(0, health_score)
        
        return {
            "status": "success",
            "health_score": health_score,
            "index_health": stats['index_health'],
            "warnings": warnings,
            "recommendations": recommendations,
            "last_indexed": stats['last_indexed'],
            "total_files": stats['total_files'],
            "message": f"Health Score: {health_score}/100"
        }
        
    except Exception as e:
        frappe.log_error(f"Health report failed: {str(e)}", "Index Health Error")
        return {
            "status": "error",
            "message": str(e)
        }