# File Indexing Implementation Plan for Frappe
## Translation from FileSearcher.py to Frappe Architecture

---

## Executive Summary

This document provides a comprehensive implementation plan to translate the **FileSearcher.py** lot-based file indexing logic into the **kgk_customisations** Frappe app. The goal is to replicate the file indexing, searching, and management capabilities for **video files, advisor files, and scan files** organized by lot numbers, while leveraging Frappe's architecture and existing infrastructure.

**IMPORTANT**: This is **completely independent** from the Cash Document system. The only shared component is the `network_storage.py` utility module (which will access different network folders).

### Current State Analysis

#### ✅ **Already Implemented** (file_management module)
1. **File Index DocType** - Replaces SQLite database
   - Fields: lot_number, file_type, file_path, file_name, file_size, indexed_on
   - Single table for all file types (advisor, polish_video, rough_video, scan)
   
2. **File Search Config DocType** - Settings management
   - Azure base URL configuration
   - Search timeout settings
   - File Directories child table (File Directory DocType)
   
3. **File Directory DocType** - Directory configuration
   - file_type (Select: Advisor, Polish Video, Rough Video, Scan)
   - directory_path, file_extension, enabled flag
   
4. **Lot Search DocType** - Web portal for searches
   - Web view enabled (has_web_view: 1)
   - lot_number (unique), published flag, search_results (JSON), route
   
5. **Search Log DocType** - Audit trail (assumed based on pattern)

6. **Utility Functions Implemented**:
   - `file_management/Utils/indexer.py`:
     - `start_advisor_indexing()` - Background job trigger
     - `index_advisor_files()` - Advisor file indexing logic
     - `extract_lot_number()` - 8-digit pattern extraction
   
   - `file_management/Utils/file_operations.py`:
     - `search_all_files(lot_number)` - Main search orchestrator
     - `search_polish_video(lot_number)` - Polish video lookup
     - `search_rough_video(lot_number)` - Rough video lookup
     - `search_advisor_files(lot_number)` - Advisor DB lookup
     - `search_scan_files(lot_number)` - Scan file discovery
     - `log_search_operation()` - Search logging (assumed)

7. **Network Storage Integration**:
   - `utils/network_storage.py`:
     - NetworkPath class with connect/disconnect
     - Year-based folder structure: `{mount_point}/{year}/{document_number}{suffix}.pdf`
     - Integration with Cash Management Settings
     - Context manager support

#### ❌ **NOT Implemented** (Gaps to Address)

1. **Missing Lot-Based File Indexing Features**:
   - Video file indexing (polish/rough) - only advisor implemented
   - Scan file indexing - only search implemented, not background indexing
   - Batch indexing jobs for all file types
   - Incremental indexing (index only new files)
   - Re-indexing functionality (rebuild entire index)

3. **GUI/Interface Components**:
   - No equivalent to Tkinter GUI (acceptable - will use Frappe Desk/Web views)
   - No thumbnail generation for scans (PDF → image conversion)
   - No "Open File" direct file system access (network paths)

4. **Configuration Gaps**:
   - FILE_CONFIG dictionary equivalent partially implemented
   - Skip rules (-F, -S folder exclusion) NOT implemented
   - File type detection logic (rough = -R folder) NOT implemented

---

## Implementation Phases

**NOTE**: All phases below relate to **lot-based file indexing** (videos, advisor files, scans) and are **independent of the Cash Document system**.

---

### **Phase 1: Complete File Indexing Infrastructure** (Priority: HIGH)

#### Tasks:

1. **Implement Video File Indexing**
   - Create `index_polish_videos()` in `indexer.py`:
     ```python
     def index_polish_videos():
         """Index polish video files from configured directories"""
         frappe.db.delete("File Index", {"file_type": "polish_video"})
         config = frappe.get_single("File Search Config")
         
         for directory_row in config.file_directories:
             if directory_row.file_type == "Polish Video" and directory_row.enabled:
                 base = Path(directory_row.directory_path)
                 if not base.exists():
                     continue
                 
                 for video_file in base.rglob("*.mp4"):
                     parent_folder = video_file.parent.name
                     
                     # Skip sparkle (-F) and fluorescence (-S)
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
                             "file_size": round(video_file.stat().st_size / (1024 * 1024), 2)
                         }).insert(ignore_permissions=True)
         
         frappe.db.commit()
     ```

2. **Implement Rough Video Indexing**
   - Create `index_rough_videos()` in `indexer.py`
   - Similar to polish videos but check `parent_folder.endswith("-R")`

3. **Implement Scan File Indexing**
   - Create `index_scan_files()` in `indexer.py`:
     ```python
     def index_scan_files():
         """Index scan files (PDF, PNG, JPG, JPEG, TIF)"""
         frappe.db.delete("File Index", {"file_type": "scan"})
         config = frappe.get_single("File Search Config")
         
         extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tif"}
         
         for directory_row in config.file_directories:
             if directory_row.file_type == "Scan" and directory_row.enabled:
                 base = Path(directory_row.directory_path)
                 if not base.exists():
                     continue
                 
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
                                 "file_size": round(scan_file.stat().st_size / (1024 * 1024), 2)
                             }).insert(ignore_permissions=True)
         
         frappe.db.commit()
     ```

4. **Create Unified Indexing Job**
   - Create `index_all_files()` in `indexer.py`:
     ```python
     @frappe.whitelist()
     def start_full_indexing():
         """Trigger background job to index ALL file types"""
         frappe.enqueue(
             'kgk_customisations.file_management.Utils.indexer.index_all_files',
             queue='long',
             timeout=7200,  # 2 hours
             job_name=f'full_indexing_{frappe.utils.now()}'
         )
         return {"status": "started", "message": "Full file indexing started"}
     
     def index_all_files():
         """Index all file types in sequence"""
         try:
             frappe.publish_realtime('indexing_progress', {'status': 'Starting', 'progress': 0})
             
             index_polish_videos()
             frappe.publish_realtime('indexing_progress', {'status': 'Polish videos indexed', 'progress': 25})
             
             index_rough_videos()
             frappe.publish_realtime('indexing_progress', {'status': 'Rough videos indexed', 'progress': 50})
             
             index_advisor_files()
             frappe.publish_realtime('indexing_progress', {'status': 'Advisor files indexed', 'progress': 75})
             
             index_scan_files()
             frappe.publish_realtime('indexing_progress', {'status': 'Complete', 'progress': 100})
             
             # Create indexing flag
             frappe.db.set_value("File Search Config", "File Search Config", "last_indexed_on", frappe.utils.now())
             
         except Exception as e:
             frappe.log_error(f"Full indexing failed: {str(e)}")
             raise
     ```

5. **Add Indexing Controls to File Search Config**
   - Add fields to `file_search_config.json`:
     ```json
     {
       "fieldname": "last_indexed_on",
       "fieldtype": "Datetime",
       "label": "Last Indexed On",
       "read_only": 1
     },
     {
       "fieldname": "indexing_status",
       "fieldtype": "Data",
       "label": "Indexing Status",
       "read_only": 1
     },
     {
       "fieldname": "index_all_button",
       "fieldtype": "Button",
       "label": "Reindex All Files"
     }
     ```

6. **Create Scheduled Job for Auto-Indexing**
   - Add to `hooks.py`:
     ```python
     scheduler_events = {
         "daily": [
             "kgk_customisations.file_management.Utils.indexer.index_all_files"
         ]
     }
     ```

---

### **Phase 2: Enhanced Search & Retrieval** (Priority: MEDIUM)

#### Tasks:

1. **Add Search Result Caching**
   - Modify `file_operations.py`:
     ```python
     def search_all_files(lot_number: str, use_cache=True):
         """Main search with caching support"""
         if use_cache:
             cached = frappe.cache().get(f"lot_search:{lot_number}")
             if cached:
                 return cached
         
         results = {
             "polish_video": search_polish_video(lot_number),
             "rough_video": search_rough_video(lot_number),
             "advisor_files": search_advisor_files(lot_number),
             "scan_files": search_scan_files(lot_number)
         }
         
         # Cache for 1 hour
         frappe.cache().setex(f"lot_search:{lot_number}", 3600, results)
         
         return results
     ```

2. **Implement File Existence Validation**
   - Add `validate_indexed_files()` function:
     ```python
     def validate_indexed_files(lot_number=None):
         """Check if indexed files still exist, remove stale entries"""
         filters = {"lot_number": lot_number} if lot_number else {}
         
         indexed_files = frappe.get_all("File Index", 
             filters=filters,
             fields=["name", "file_path", "lot_number", "file_type"])
         
         stale_count = 0
         for record in indexed_files:
             if not Path(record.file_path).exists():
                 frappe.delete_doc("File Index", record.name, force=1)
                 stale_count += 1
         
         return {
             "validated": len(indexed_files),
             "removed": stale_count,
             "message": f"Removed {stale_count} stale entries out of {len(indexed_files)}"
         }
     ```

3. **Add Batch File Opening Support**
   - Create `utils/file_opener.py`:
     ```python
     import subprocess
     import platform
     
     def open_file(file_path):
         """Open file using system default application"""
         try:
             if platform.system() == "Windows":
                 os.startfile(file_path)
             elif platform.system() == "Darwin":  # macOS
                 subprocess.run(["open", file_path])
             else:  # Linux
                 subprocess.run(["xdg-open", file_path])
             return True
         except Exception as e:
             frappe.log_error(f"Error opening file {file_path}: {str(e)}")
             return False
     
     @frappe.whitelist()
     def open_lot_files(lot_number, file_types=None):
         """Open all files for a lot number"""
         if isinstance(file_types, str):
             file_types = frappe.parse_json(file_types)
         
         results = search_all_files(lot_number)
         opened = []
         
         for file_type, data in results.items():
             if file_types and file_type not in file_types:
                 continue
             
             if isinstance(data, dict) and data.get("found"):
                 if open_file(data["path"]):
                     opened.append(data["path"])
             elif isinstance(data, list):
                 for file_data in data:
                     if open_file(file_data["path"]):
                         opened.append(file_data["path"])
         
         return {"opened": len(opened), "files": opened}
     ```

---

### **Phase 3: Web Interface & User Experience** (Priority: MEDIUM)

#### Tasks:

1. **Enhance Lot Search Web View**
   - Create template: `lot_search.html` in `file_management/doctype/lot_search/templates/`
   - Display search results with thumbnails
   - Add download/open buttons
   - Show file metadata (size, type, path)

2. **Create Dashboard for File Search Config**
   - Add custom dashboard to `file_search_config.py`:
     ```python
     def get_dashboard_data():
         return {
             "fieldname": "file_type",
             "transactions": [
                 {
                     "label": "Indexed Files",
                     "items": ["File Index"]
                 },
                 {
                     "label": "Searches",
                     "items": ["Lot Search", "Search Log"]
                 }
             ]
         }
     ```

3. **Add Search Stats Page**
   - Create custom page: `file_management/page/file_search_stats/`
   - Display:
     - Total indexed files by type
     - Last indexing date
     - Search frequency by lot number
     - Most searched lots
     - Stale file count

4. **Implement Real-time Search Progress**
   - Use `frappe.publish_realtime()` during search
   - Show progress bar in UI
   - Display "Searching..." status

---

### **Phase 4: Integration & Migration** (Priority: LOW)

#### Tasks:

1. **Migrate CashSQL.py Index Data**
   - Create migration script to import existing indexed data
   - Map file structure from old system to new File Index
   - Preserve historical search logs if available

2. **Create Import Tool for FileSearcher.db**
   - Read SQLite database: `file_index.db`
   - Bulk insert to File Index DocType
   - Validate lot numbers
   - Script:
     ```python
     import sqlite3
     
     def migrate_from_sqlite(db_path):
         """Import data from FileSearcher SQLite DB"""
         conn = sqlite3.connect(db_path)
         cursor = conn.execute("SELECT lot, file_type, path FROM file_index")
         
         count = 0
         for row in cursor:
             lot, file_type, path = row
             if Path(path).exists():
                 frappe.get_doc({
                     "doctype": "File Index",
                     "lot_number": lot,
                     "file_type": file_type,
                     "file_path": path,
                     "file_name": Path(path).name,
                     "file_size": round(Path(path).stat().st_size / (1024 * 1024), 2)
                 }).insert(ignore_permissions=True)
                 count += 1
         
         frappe.db.commit()
         return f"Migrated {count} records"
     ```

3. **Network Path Configuration Wizard**
   - Create Page: `cash_management/page/network_setup_wizard/`
   - Test connection to network shares
   - Auto-detect available paths
   - Validate read/write permissions

---

## Technical Architecture Comparison

### FileSearcher.py → Frappe Translation Map

| FileSearcher Component | Frappe Equivalent | Status |
|------------------------|-------------------|--------|
| `DatabaseManager` | File Index DocType | ✅ Implemented |
| `SQLite database` | MariaDB table | ✅ Implemented |
| `Indexer.index_all()` | `indexer.py` functions | ⚠️ Partial (advisor only) |
| `LotFileSearcher` | `file_operations.py` | ✅ Implemented |
| `FILE_CONFIG` | File Search Config + File Directory | ✅ Implemented |
| `extract_lot_number()` | `file_operations.py` | ✅ Implemented |
| `LotFileSearchGUI` | Frappe Desk + Web View | ⚠️ Partial (no thumbnails) |
| `NetworkPath` (FileSearcher) | `network_storage.py` | ✅ Implemented |
| File suffix assignment | Cash Document suffix | ❌ NOT Implemented |
| Thumbnail generation | N/A | ❌ NOT Implemented |
| Background indexing | Frappe Queue | ✅ Implemented (advisor) |

---

## File Structure Summary

### Existing Files:
```
kgk_customisations/
├── file_management/
│   ├── doctype/
│   │   ├── file_index/
│   │   │   ├── file_index.json          ✅ Complete
│   │   │   ├── file_index.py            ✅ Skeleton only
│   │   │   ├── file_index.js            ✅ Empty
│   │   │   └── test_file_index.py       ✅ Empty
│   │   ├── file_search_config/
│   │   │   ├── file_search_config.json  ✅ Complete
│   │   │   └── file_search_config.py    ❌ Missing dashboard
│   │   ├── file_directory/
│   │   │   └── file_directory.json      ✅ Complete (child table)
│   │   ├── lot_search/
│   │   │   ├── lot_search.json          ✅ Complete (web view enabled)
│   │   │   └── lot_search.py            ✅ Skeleton only
│   │   └── search_log/                  ❓ Assumed to exist
│   └── Utils/
│       ├── indexer.py                   ⚠️ Advisor only
│       └── file_operations.py           ✅ Search functions complete
├── utils/
│   ├── network_storage.py               ✅ Complete
│   └── file_utils.py                    ✅ Complete
└── kgk_customisations/
    └── doctype/
        └── cash_document/
            ├── cash_document.json       ❌ Missing file_suffix field
            ├── cash_document.py         ❌ Missing suffix assignment
            └── test_cash_document.py    ⚠️ Test exists but incomplete
```

### Files to Create/Modify:

#### Phase 1 (Cash Document):
1. **Modify**: `cash_document.json` - Add file_suffix field
2. **Modify**: `cash_document.py` - Add suffix assignment methods
3. **Modify**: `network_storage.py` - Add cash_document_path() method
4. **Modify**: `test_cash_document.py` - Complete suffix tests

#### Phase 2 (Indexing):
1. **Modify**: `indexer.py` - Add video and scan indexing
2. **Modify**: `file_search_config.json` - Add indexing control fields
3. **Modify**: `file_search_config.py` - Add dashboard and button handlers
4. **Modify**: `hooks.py` - Add scheduled jobs

#### Phase 3 (Search Enhancement):
1. **Modify**: `file_operations.py` - Add caching and validation
2. **Create**: `file_opener.py` - File opening utilities

#### Phase 4 (Web UI):
1. **Create**: `lot_search.html` - Web template
2. **Create**: `file_search_stats` page
3. **Modify**: `lot_search.py` - Add web view logic

#### Phase 5 (Migration):
1. **Create**: `migrate_file_index.py` - Migration script
2. **Create**: `network_setup_wizard` page

---

## Key Differences from FileSearcher.py

### 1. **Storage Backend**
- **FileSearcher**: SQLite database (file_index.db)
- **Frappe**: MariaDB/PostgreSQL (File Index DocType)
- **Advantage**: Multi-user support, ACID compliance, built-in caching

### 2. **Background Processing**
- **FileSearcher**: Threading (`threading.Thread`)
- **Frappe**: RQ Queue (`frappe.enqueue()`)
- **Advantage**: Distributed processing, progress tracking, failure recovery

### 3. **GUI Framework**
- **FileSearcher**: Tkinter desktop application
- **Frappe**: Web-based (Frappe Desk + Web views)
- **Advantage**: Remote access, mobile support, multi-user

### 4. **File Suffix Logic**
- **FileSearcher**: Sequential suffix per folder (`get_next_suffix_letter()`)
- **Frappe**: Sequential numeric per company/date (001, 002, 003)
- **Difference**: More structured, database-backed uniqueness

### 5. **Configuration Management**
- **FileSearcher**: Hardcoded `FILE_CONFIG` dictionary
- **Frappe**: DocType-based (File Search Config)
- **Advantage**: Runtime changes, no code deployment needed

---

## Dependencies & Prerequisites

### Python Packages Required:
```
# Already in Frappe:
- pathlib
- re
- threading (not used - replaced with RQ)

# May need to add:
- Pillow (for thumbnail generation)
- pdf2image (for PDF thumbnails)
- poppler-utils (system package for pdf2image)
```

### System Requirements:
- Network share access (SMB/CIFS)
- Sufficient permissions for file operations
- Background worker enabled (`bench start` or supervisor)

### Frappe Configuration:
```python
# site_config.json additions:
{
    "background_workers": 1,
    "rq_queue_workers": {"long": 2, "default": 4},
    "allow_network_storage": true
}
```

---

## Testing Strategy

### Unit Tests:
1. **File Suffix Assignment** (Cash Document)
   - Test sequential assignment
   - Test company/date isolation
   - Test rollover scenarios

2. **Indexing Functions**
   - Test lot number extraction
   - Test file type detection
   - Test duplicate handling
   - Test stale file cleanup

3. **Search Operations**
   - Test exact match
   - Test partial match
   - Test cache hit/miss
   - Test performance with large datasets

### Integration Tests:
1. **End-to-End Workflow**:
   - Create Cash Document → Assign suffix → Save to network → Index → Search → Retrieve

2. **Network Storage**:
   - Test connect/disconnect
   - Test file read/write
   - Test permission errors

3. **Background Jobs**:
   - Test indexing job completion
   - Test progress updates
   - Test error handling

### Performance Tests:
1. **Indexing Performance**:
   - Benchmark indexing 10,000 files
   - Measure DB insert rate
   - Test parallel indexing

2. **Search Performance**:
   - Test search with 100,000+ indexed files
   - Measure cache effectiveness
   - Test concurrent searches

---

## Rollout Plan

### Phase 1: Development (Week 1-2)
- Implement Cash Document suffix system
- Complete video/scan indexing
- Unit testing

### Phase 2: Testing (Week 3)
- Integration testing
- Performance testing
- User acceptance testing

### Phase 3: Staged Rollout (Week 4)
- Deploy to test environment
- Index existing files
- Train users

### Phase 4: Production (Week 5)
- Deploy to production
- Monitor performance
- Collect feedback

---

## Risk Mitigation

### Risk 1: Network Share Accessibility
- **Mitigation**: Implement connection retry logic, fallback to local cache
- **Monitoring**: Log connection failures, alert on threshold

### Risk 2: Large File Count Performance
- **Mitigation**: Batch processing, pagination, indexing throttling
- **Monitoring**: Track indexing duration, optimize queries

### Risk 3: Data Migration Errors
- **Mitigation**: Dry-run mode, rollback capability, validation checks
- **Monitoring**: Log migration errors, validate record counts

### Risk 4: Concurrent Access Conflicts
- **Mitigation**: Database locking, transaction isolation
- **Monitoring**: Log lock waits, deadlocks

---

## Success Metrics

1. **Indexing Coverage**: >95% of files indexed successfully
2. **Search Speed**: <2 seconds for lot search
3. **Uptime**: >99% indexing service availability
4. **User Adoption**: >80% of users use search feature within 1 month
5. **Error Rate**: <1% file retrieval failures

---

## Maintenance & Monitoring

### Daily Tasks:
- Monitor indexing job completion
- Check stale file count
- Review error logs

### Weekly Tasks:
- Validate index integrity
- Clean up orphaned records
- Review search patterns

### Monthly Tasks:
- Performance optimization review
- Capacity planning
- User feedback analysis

---

## Future Enhancements

1. **AI-Powered Search**: OCR text extraction, semantic search
2. **File Versioning**: Track file changes over time
3. **Advanced Filtering**: Date ranges, file size, file type combinations
4. **Mobile App**: Native mobile access to file search
5. **Automated Categorization**: ML-based file type detection
6. **Duplicate Detection**: Identify duplicate files across network
7. **Preview Generation**: Inline file previews without download

---

## Appendix A: Field Mapping

### Cash Document Fields for File Management:

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `file_suffix` | Data | Sequential suffix | "001" |
| `company` | Link | Company reference | "KGK Ltd" |
| `transaction_date` | Date | Document date | "2025-01-15" |
| `document_number` | Data | Auto-generated ID | "CD-2025-01-00123" |

**Computed File Name**: `{company_abbr}-{transaction_date}-{file_suffix}.pdf`
**Example**: `KGK-2025-01-15-001.pdf`

---

## Appendix B: Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `FI-001` | Network share not accessible | Check network connectivity |
| `FI-002` | Lot number extraction failed | Verify file naming convention |
| `FI-003` | Duplicate file suffix | Check database sequence |
| `FI-004` | Indexing job timeout | Increase timeout or split job |
| `FI-005` | File not found during validation | Remove stale index entry |
| `FI-006` | Permission denied | Check file/folder permissions |

---

## Conclusion

This implementation plan provides a comprehensive roadmap to translate **FileSearcher.py** functionality into the **kgk_customisations** Frappe app. The existing infrastructure (File Index, File Search Config, network_storage.py) provides a solid foundation. The critical missing piece is the **Cash Document file suffix assignment**, which should be prioritized as Phase 1.

By following this phased approach, the system will achieve:
- ✅ **Scalability**: Database-backed indexing vs. SQLite
- ✅ **Reliability**: Frappe queue vs. threading
- ✅ **Accessibility**: Web-based vs. desktop GUI
- ✅ **Maintainability**: Configuration-driven vs. hardcoded
- ✅ **Auditability**: Full search/access logging

**Next Steps**:
1. Review and approve implementation plan
2. Prioritize phases based on business needs
3. Allocate development resources
4. Begin Phase 1 implementation
