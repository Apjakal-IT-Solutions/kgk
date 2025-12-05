# File Indexing - Quick Reference Guide
## Lot-Based File Indexing for Videos, Advisor Files, and Scans

**IMPORTANT**: This system is **completely independent** from the Cash Document system. They are separate implementations that only share the `network_storage.py` utility (accessing different network folders).

---

## Current State: What's Already Done ✅

### 1. File Management Module (Exists)
- **File Index DocType**: Stores indexed file records (lot_number, file_type, file_path)
- **File Search Config**: Configuration settings for directories and search
- **File Directory**: Child table for configuring multiple search paths
- **Lot Search**: Web-enabled search interface
- **indexer.py**: Background indexing for advisor files only
- **file_operations.py**: Search functions for all file types
- **network_storage.py**: Network share integration (connect, read, write)

### 2. What Works Right Now
- ✅ Advisor file indexing (background job)
- ✅ Search all file types (polish_video, rough_video, advisor, scan)
- ✅ Network storage connection
- ✅ Lot number extraction (8-digit pattern)
- ✅ Search result caching

---

## What's Missing ❌

### HIGH PRIORITY: Complete Lot-Based File Indexing
**Problem**: Only advisor files are indexed; videos and scans are searched on-the-fly without indexing

**Current State**:
- Video file indexing NOT implemented (only search exists)
- Scan file indexing NOT implemented (only search exists)
- Batch indexing jobs missing
- Re-indexing functionality missing

**Impact**: Slower searches, no offline index, manual file discovery

---

## Implementation Priority

### 🟡 **PHASE 1: HIGH** (Complete Indexing)
**Timeline**: 1-2 weeks  
**Files to Modify**: 3 files

1. Add `index_polish_videos()` to `indexer.py`
2. Add `index_rough_videos()` to `indexer.py`
3. Add `index_scan_files()` to `indexer.py`
4. Create `index_all_files()` unified function
5. Add scheduled job to `hooks.py`

**Quick Win**: Full background indexing for all file types

---

### 🟢 **PHASE 2: MEDIUM** (Search Enhancement)
**Timeline**: 1 week  
**Files to Create**: 2 new files

1. Add search result caching
2. Create `validate_indexed_files()` for stale file cleanup
3. Create `file_opener.py` for direct file opening

**Quick Win**: Faster searches, cleaner data

---

### 🔵 **PHASE 3: LOW** (Web UI)
**Timeline**: 1-2 weeks  
**Files to Create**: 3 new files

1. Create `lot_search.html` template
2. Create `file_search_stats` page
3. Add dashboard to `file_search_config.py`

**Quick Win**: Better user experience

---

## Code Snippets for Quick Implementation

### Snippet 1: Video Indexing (indexer.py)
```python
def index_polish_videos():
    """Index polish video files"""
    frappe.db.delete("File Index", {"file_type": "polish_video"})
    config = frappe.get_single("File Search Config")
    
    for directory_row in config.file_directories:
        if directory_row.file_type == "Polish Video" and directory_row.enabled:
            base = Path(directory_row.directory_path)
            for video_file in base.rglob("*.mp4"):
                parent_folder = video_file.parent.name
                
                # Skip sparkle (-F), fluorescence (-S), rough (-R)
                if parent_folder.endswith(("-F", "-S", "-R")):
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

---

## File Structure Map

### Where Everything Lives:
```
kgk_customisations/
├── file_management/              # LOT-BASED file indexing module
│   ├── doctype/
│   │   ├── file_index/          # ✅ Stores indexed lot files
│   │   ├── file_search_config/  # ✅ Configuration
│   │   ├── file_directory/      # ✅ Directory paths
│   │   └── lot_search/          # ✅ Web search interface
│   └── Utils/
│       ├── indexer.py           # ⚠️ Partial (advisor only)
│       └── file_operations.py   # ✅ Search functions
│
├── utils/
│   ├── network_storage.py       # ✅ SHARED utility (different folders)
│   └── file_utils.py            # ✅ File utilities
│
└── kgk_customisations/          # SEPARATE Cash Document system
    └── doctype/
        └── cash_document/       # (Independent implementation)
```

---

## Key Differences: FileSearcher.py vs Frappe

| Feature | FileSearcher.py | Frappe Implementation |
|---------|----------------|----------------------|
| **Database** | SQLite (file_index.db) | MariaDB (File Index DocType) |
| **GUI** | Tkinter desktop | Web-based (Frappe Desk) |
| **Background Jobs** | Threading | RQ Queue (frappe.enqueue) |
| **Configuration** | Hardcoded FILE_CONFIG | DocType (File Search Config) |
| **File Suffix** | Sequential letters (A, B, C) | Sequential numbers (001, 002, 003) |
| **Network Access** | Direct OS path | NetworkPath class with connect/disconnect |

---

## Testing Checklist

### Phase 1 (Lot Indexing):
- [ ] Run `index_polish_videos()` → check File Index records
- [ ] Run `index_rough_videos()` → verify -R folders only
- [ ] Run `index_scan_files()` → verify PDF/PNG/JPG indexed
- [ ] Run `index_all_files()` → verify all types indexed
- [ ] Check scheduled job runs daily

### Phase 2 (Search):
- [ ] Search lot number → verify results cached
- [ ] Search again → verify cache hit
- [ ] Run `validate_indexed_files()` → verify stale cleanup
- [ ] Open file → verify opens in default app

---

## Quick Commands

### Frappe Console:
```python
# Trigger full lot indexing
from kgk_customisations.file_management.Utils.indexer import start_full_indexing
start_full_indexing()

# Search for lot
from kgk_customisations.file_management.Utils.file_operations import search_all_files
results = search_all_files("12345678")
print(results)

# Test network path
from kgk_customisations.utils.network_storage import get_network_storage
ns = get_network_storage()
ns.connect()
print(ns.mount_point)
```

### Bench Commands:
```bash
# Run indexing manually
bench --site kgkerp.local execute kgk_customisations.file_management.Utils.indexer.index_all_files

# Check scheduled jobs
bench --site kgkerp.local doctor

# Clear cache
bench --site kgkerp.local clear-cache

# Run tests
bench --site kgkerp.local run-tests --app kgk_customisations --module test_cash_document
```

---

## Migration from FileSearcher.py

### Step 1: Export SQLite Data
```bash
sqlite3 file_index.db "SELECT lot, file_type, path FROM file_index" > export.csv
```

### Step 2: Import to Frappe
```python
import csv
from pathlib import Path

def import_from_csv(csv_path):
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        for lot, file_type, path in reader:
            if Path(path).exists():
                frappe.get_doc({
                    "doctype": "File Index",
                    "lot_number": lot,
                    "file_type": file_type,
                    "file_path": path,
                    "file_name": Path(path).name,
                    "file_size": round(Path(path).stat().st_size / (1024 * 1024), 2)
                }).insert(ignore_permissions=True)
    frappe.db.commit()
```

---

## Troubleshooting

### Problem: File suffix duplicates
**Solution**: Check database sequence, verify unique constraint on (company, transaction_date, file_suffix)

### Problem: Network share not accessible
**Solution**: Check `network_storage.py` mount_point, verify credentials in Cash Management Settings

### Problem: Indexing job timeout
**Solution**: Increase timeout in `hooks.py` or split by file type

### Problem: Search returns no results
**Solution**: Verify indexing completed, check File Index records exist, validate file paths

### Problem: Stale file entries
**Solution**: Run `validate_indexed_files()` to cleanup

---

## Performance Tips

1. **Batch Indexing**: Index 1000 files at a time, commit per batch
2. **Cache Results**: Use `frappe.cache()` for frequent searches
3. **Database Indexes**: Add index on (lot_number, file_type) in File Index
4. **Parallel Processing**: Use multiple RQ workers for indexing
5. **Incremental Updates**: Index only new files, not full re-index

---

## Next Immediate Action

**Start with Phase 1** (3 file changes, ~150 lines of code):

1. Open `indexer.py` → Add `index_polish_videos()` and `index_rough_videos()`
2. Open `indexer.py` → Add `index_scan_files()`
3. Open `indexer.py` → Add `index_all_files()` unified function
4. Open `hooks.py` → Add scheduled job for daily indexing
5. Run test: `bench execute kgk_customisations.file_management.Utils.indexer.index_all_files`

**Expected Result**: All lot-based files (videos, advisor, scans) indexed in File Index DocType

---

## Support & Documentation

- **Full Plan**: See `FILE_INDEXING_IMPLEMENTATION_PLAN.md`
- **FileSearcher.py**: Reference implementation at `/opt/bench/frappe-bench/FileSearcher.py`
- **Test Data**: Use `test_data_generator.py` for sample data
- **Error Logs**: Check `logs/frappe.log.*` for indexing errors
