# File Indexing Architecture Comparison
## Lot-Based File Indexing System (Videos, Advisor Files, Scans)

**CRITICAL NOTE**: This document describes the **lot-based file indexing system** for video files, advisor files, and scan files. This is **completely independent** from the Cash Document system. The only shared component is the `network_storage.py` utility module, which will access **different network folders** for each system.

- **Lot Indexing System**: Indexes files by 8-digit lot numbers (videos, advisor, scans)
- **Cash Document System**: Separate system with its own file management (different network folders)
- **Shared**: `network_storage.py` utility class only

## FileSearcher.py Architecture (Desktop Application)

```
┌─────────────────────────────────────────────────────────────────┐
│                     FileSearcher.py (Tkinter GUI)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │   Search UI  │  │  Indexing UI │  │  Thumbnail Display │   │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘   │
│         │                 │                     │               │
│         └─────────────────┴─────────────────────┘               │
│                           │                                     │
│                           ▼                                     │
│         ┌─────────────────────────────────┐                    │
│         │   LotFileSearchGUI (Main Class) │                    │
│         └─────────────┬───────────────────┘                    │
│                       │                                         │
│         ┌─────────────┴───────────────┐                        │
│         │                             │                        │
│         ▼                             ▼                        │
│  ┌──────────────┐            ┌──────────────┐                 │
│  │ LotFileSearcher │        │   Indexer    │                  │
│  │  (Search Logic) │        │ (Index Logic) │                 │
│  └────────┬───────┘          └──────┬───────┘                 │
│           │                         │                          │
│           └────────────┬────────────┘                          │
│                        │                                       │
│                        ▼                                       │
│              ┌───────────────────┐                             │
│              │ DatabaseManager   │                             │
│              │   (SQLite ORM)    │                             │
│              └─────────┬─────────┘                             │
│                        │                                       │
│                        ▼                                       │
│              ┌───────────────────┐                             │
│              │  file_index.db    │                             │
│              │    (SQLite)       │                             │
│              └───────────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
              ▲                               ▲
              │                               │
              │    ┌──────────────────┐      │
              └────┤  FILE_CONFIG     │──────┘
                   │  (Hardcoded Dict)│
                   └──────────────────┘
                              │
                              ▼
           ┌──────────────────────────────────────┐
           │     Network Shares (UNC Paths)       │
           ├──────────────────────────────────────┤
           │ \\video-pc1\data                     │
           │ \\video-pc1\Vision_data              │
           │ \\nas-gradding\POLISH-VIDEO          │
           │ \\Nas-planning\stones                │
           │ \\roughvideo1\My Scans2              │
           └──────────────────────────────────────┘
```

---

## Frappe Implementation Architecture (Web Application)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Frappe Desk (Web Interface)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────────┐     │
│  │  Lot Search    │  │ File Search  │  │  Cash Document Form    │     │
│  │  (Web Page)    │  │   Config     │  │  (DocType Form)        │     │
│  └────────┬───────┘  └──────┬───────┘  └─────────┬──────────────┘     │
│           │                 │                     │                     │
│           └─────────────────┴─────────────────────┘                     │
│                             │                                           │
│                             ▼                                           │
│           ┌──────────────────────────────────────┐                     │
│           │    Frappe API Layer (@frappe.whitelist) │                  │
│           └──────────────────┬───────────────────┘                     │
│                              │                                          │
│           ┌──────────────────┴────────────────────┐                    │
│           │                                       │                    │
│           ▼                                       ▼                    │
│  ┌───────────────────┐                  ┌──────────────────┐          │
│  │ file_operations.py │                │    indexer.py     │          │
│  │  (Search Logic)    │                │  (Index Logic)    │          │
│  ├────────────────────┤                ├──────────────────┤          │
│  │ • search_all_files │                │ • index_polish_*  │          │
│  │ • search_polish_*  │                │ • index_rough_*   │          │
│  │ • search_rough_*   │                │ • index_advisor_* │          │
│  │ • search_advisor_* │                │ • index_scan_*    │          │
│  │ • search_scan_*    │                │ • index_all_files │          │
│  └─────────┬──────────┘                └──────┬───────────┘          │
│            │                                   │                       │
│            │           ┌───────────────────────┘                       │
│            │           │                                               │
│            │           │     ┌──────────────────────┐                 │
│            └───────────┼─────┤  Frappe ORM Layer    │                 │
│                        │     └──────────┬───────────┘                 │
│                        │                │                              │
│                        │                ▼                              │
│                        │     ┌──────────────────────┐                 │
│                        │     │  File Index DocType  │                 │
│                        │     │   (frappe.get_doc)   │                 │
│                        │     └──────────┬───────────┘                 │
│                        │                │                              │
│                        │                ▼                              │
│                        │     ┌──────────────────────────┐             │
│                        │     │  tabFile Index (MariaDB) │             │
│                        │     └──────────────────────────┘             │
│                        │                                               │
│                        │     ┌──────────────────────────┐             │
│                        └─────┤  RQ Queue (Background)   │             │
│                              │  • frappe.enqueue()      │             │
│                              │  • Long-running jobs     │             │
│                              └──────────────────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
              ▲                                    ▲
              │                                    │
              │     ┌────────────────────────┐    │
              └─────┤ File Search Config     │────┘
                    │ (DocType - Database)   │
                    └────────┬───────────────┘
                             │
                             ├─ File Directory (Child Table)
                             ├─ Azure Base URL
                             └─ Search Timeout
                             
                             ▼
           ┌──────────────────────────────────────────────┐
           │        network_storage.py (NetworkPath)      │
           │        (Cash Management Settings)             │
           └─────────────────────┬────────────────────────┘
                                 │
                                 ▼
           ┌──────────────────────────────────────┐
           │     Network Shares (UNC/SMB)         │
           ├──────────────────────────────────────┤
           │ Configured via File Search Config    │
           │ • Polish Video Directories           │
           │ • Rough Video Directories            │
           │ • Advisor File Directories           │
           │ • Scan Directories                   │
           └──────────────────────────────────────┘
```

---

## Data Flow Comparison

### FileSearcher.py: Indexing Flow

```
User Clicks "Refresh Index" Button
        │
        ▼
LotFileSearchGUI._on_index_all()
        │
        ▼
Threading.Thread(target=Indexer.index_all)
        │
        ├─► Loop through video directories
        │   ├─ extract_lot_number(file)
        │   ├─ Skip -F, -S folders
        │   ├─ Detect -R (rough) vs polish
        │   └─ DatabaseManager.insert_file(lot, type, path)
        │
        ├─► Loop through scan directories
        │   ├─ Check extensions (.pdf, .png, .jpg, .tif)
        │   ├─ extract_lot_number(file)
        │   └─ DatabaseManager.insert_file(lot, "scan", path)
        │
        └─► Loop through advisor directories
            ├─ Find *.adv files
            ├─ extract_lot_number(file)
            └─ DatabaseManager.insert_file(lot, "advisor", path)
        
        ▼
DatabaseManager.commit()
        │
        ▼
SQLite: INSERT INTO file_index (lot, file_type, path) VALUES (?, ?, ?)
        │
        ▼
Create flag file: indexing.complete
        │
        ▼
GUI shows "Indexing Complete"
```

### Frappe Implementation: Indexing Flow

```
User Clicks "Reindex All Files" (File Search Config)
        │
        ▼
file_search_config.js: frappe.call("start_full_indexing")
        │
        ▼
indexer.start_full_indexing() → frappe.whitelist
        │
        ▼
frappe.enqueue("indexer.index_all_files", queue="long", timeout=7200)
        │
        ▼
RQ Worker picks up job from queue
        │
        ├─► index_polish_videos()
        │   ├─ frappe.db.delete("File Index", {"file_type": "polish_video"})
        │   ├─ frappe.get_single("File Search Config")
        │   ├─ Loop config.file_directories (Polish Video type)
        │   ├─ Path(directory_row.directory_path).rglob("*.mp4")
        │   ├─ Skip -F, -S, -R folders
        │   ├─ extract_lot_number(video_file)
        │   └─ frappe.get_doc({
        │       "doctype": "File Index",
        │       "lot_number": lot,
        │       "file_type": "polish_video",
        │       "file_path": str(video_file)
        │     }).insert()
        │   └─ frappe.publish_realtime("indexing_progress", {progress: 25})
        │
        ├─► index_rough_videos() [same pattern, check -R folders]
        │   └─ frappe.publish_realtime("indexing_progress", {progress: 50})
        │
        ├─► index_advisor_files() [existing implementation]
        │   └─ frappe.publish_realtime("indexing_progress", {progress: 75})
        │
        └─► index_scan_files() [PDF, PNG, JPG, TIF]
            └─ frappe.publish_realtime("indexing_progress", {progress: 100})
        
        ▼
frappe.db.commit()
        │
        ▼
MariaDB: INSERT INTO `tabFile Index` (lot_number, file_type, file_path, ...) VALUES (?, ?, ?, ...)
        │
        ▼
frappe.db.set_value("File Search Config", "File Search Config", "last_indexed_on", now())
        │
        ▼
frappe.publish_realtime("msgprint", "Indexing complete!")
```

---

## Search Flow Comparison

### FileSearcher.py: Search Flow

```
User enters Lot ID "12345678"
        │
        ▼
User clicks "Search All"
        │
        ▼
LotFileSearchGUI._on_search_all()
        │
        ├─► _on_search_polish() → Threading.Thread(_polish_thread)
        │   └─ LotFileSearcher.search_polish_video("12345678")
        │       └─ DatabaseManager.lookup("12345678", "polish_video")
        │           └─ SQLite: SELECT path FROM file_index WHERE lot=? AND file_type=?
        │               └─ Return Path or None
        │
        ├─► _on_search_rough() → Threading.Thread(_rough_thread)
        │   └─ LotFileSearcher.search_rough_video("12345678")
        │       └─ [same as polish]
        │
        ├─► _on_search_advisor()
        │   └─ LotFileSearcher.search_advisor_files("12345678")
        │       └─ [same lookup, returns List[Path]]
        │
        └─► _on_search_scans()
            └─ LotFileSearcher.search_scan_files("12345678")
                └─ [same lookup, returns List[Path]]
        
        ▼
Update GUI labels with results
        │
        ├─ polish_lbl.config(text="video.mp4")
        ├─ rough_lbl.config(text="video.mp4")
        ├─ advisor_lb.insert(tk.END, "file.adv")
        └─ Show thumbnails in thumb_frame
```

### Frappe Implementation: Search Flow

```
User enters Lot ID "12345678" in Lot Search web page
        │
        ▼
frappe.call("file_operations.search_all_files", {lot_number: "12345678"})
        │
        ▼
file_operations.search_all_files("12345678") → frappe.whitelist
        │
        ├─ Check cache: frappe.cache().get("lot_search:12345678")
        │   └─ If HIT: return cached results immediately
        │   └─ If MISS: continue ▼
        │
        ├─► search_polish_video("12345678")
        │   └─ frappe.get_single("File Search Config")
        │   └─ Loop config.file_directories (polish_video type)
        │   └─ Path(directory).rglob("*.mp4") for lot folder
        │   └─ Return {found: True/False, path: "...", size: ...}
        │
        ├─► search_rough_video("12345678")
        │   └─ [same pattern, check -R folders]
        │
        ├─► search_advisor_files("12345678")
        │   └─ frappe.get_all("File Index", 
        │       filters={"lot_number": "12345678", "file_type": "advisor"},
        │       fields=["file_path", "file_name", "file_size"])
        │   └─ Validate Path.exists() for each
        │   └─ Return List[{found: True, path: ..., size: ...}]
        │
        └─► search_scan_files("12345678")
            └─ [same as advisor, but file_type="scan"]
        
        ▼
results = {
    "polish_video": {...},
    "rough_video": {...},
    "advisor_files": [...],
    "scan_files": [...]
}
        │
        ▼
Cache results: frappe.cache().setex("lot_search:12345678", 3600, results)
        │
        ▼
log_search_operation(lot_number, "all", results, start_time)
        └─ INSERT INTO `tabSearch Log` (lot_number, search_type, results, ...)
        
        ▼
Return results to client (JSON)
        │
        ▼
JavaScript updates Lot Search page UI
        ├─ Display polish video link
        ├─ Display rough video link
        ├─ List advisor files
        └─ Show scan thumbnails (if implemented)
```

---

## File Naming Convention Comparison

**NOTE**: This section compares FileSearcher.py (lot-based) with Frappe lot indexing. The Cash Document system uses a completely different file naming approach and is not part of this comparison.

### FileSearcher.py / CashSQL.py: File Naming (for reference only)

```
User indexes new document
        │
        ▼
CashSQL.MainWindow.index_document()
        │
        ├─ unique_no = generate_unique_number(date, type)
        │   └─ Format: "{date}-{type}-{sequence}"
        │       Example: "2025-01-15-Cash-00123"
        │
        └─ folder_path = STORAGE_FOLDER / unique_no
            └─ Create folder: e-dox/2025-01-15-Cash-00123/
        
        ▼
Copy main document:
    main_file_dest = folder_path / f"{unique_no}.pdf"
    shutil.copy2(scanned_main_file, main_file_dest)
        │
        ▼
Copy supporting files:
    for file in selected_files:
        suffix = get_next_suffix_letter(folder_path, unique_no)
        ├─ Scan existing files in folder
        ├─ Find max suffix (A, B, C, ..., Z, AA, AB, ...)
        └─ Return next available letter
        
        new_name = f"{unique_no}_{suffix}{file.suffix}"
        Example: "2025-01-15-Cash-00123_A.pdf"
        
        shutil.copy2(file, folder_path / new_name)
        
        ▼
Insert to database:
    payment_system.index_document(
        date_str,
        main_type,
        sub_type,
        username,
        company,
        predefined_unique=unique_no
    )
```

### Frappe Implementation: Lot-Based File Naming

**NOTE**: For lot-based files, the naming convention is determined by the source file structure, not by Frappe. Files are indexed as-is from network directories.

```
File exists on network share
        │
        ▼
Directory structure:
    \\video-pc1\data\12345678\video.mp4  (polish video)
    \\video-pc1\data\12345678-R\video.mp4  (rough video)
    \\Nas-planning\stones\12345678.adv  (advisor)
    \\roughvideo1\My Scans2\12345678.pdf  (scan)
        │
        ▼
Background indexing job runs:
    indexer.index_all_files()
        │
        ├─ index_polish_videos()
        ├─ index_rough_videos()
        ├─ index_advisor_files()
        └─ index_scan_files()
        
        ▼
For each file:
    lot = extract_lot_number(file_path)  # Extract 8-digit number
    
    frappe.get_doc({
        "doctype": "File Index",
        "lot_number": "12345678",
        "file_type": "polish_video",  # or rough_video, advisor, scan
        "file_path": str(file_path),
        "file_name": file_path.name,
        "file_size": file_size_mb
    }).insert()
        
        ▼
User searches for lot "12345678"
        │
        ▼
file_operations.search_all_files("12345678")
        │
        └─ Returns all indexed files for that lot number
```

**Key Difference**: Lot indexing discovers and indexes existing files; Cash Document creates new files with generated names.

---

## Key Architectural Differences

| Aspect | FileSearcher.py | Frappe Implementation |
|--------|----------------|----------------------|
| **Database** | SQLite (single file) | MariaDB (multi-user, ACID) |
| **Concurrency** | Threading (GIL-limited) | RQ Queue (distributed workers) |
| **Configuration** | Hardcoded FILE_CONFIG | Database-driven (File Search Config) |
| **UI** | Tkinter (desktop) | Web (HTML/JS/Bootstrap) |
| **File Suffix** | Letter-based (A, B, C) | Number-based (001, 002, 003) |
| **Suffix Scope** | Per folder | Per company + date |
| **Network Access** | Direct OS path | NetworkPath class with mount |
| **Caching** | None | frappe.cache() (Redis) |
| **Logging** | Print statements | frappe.log_error() + Search Log |
| **Background Jobs** | Threading | RQ (Redis Queue) |
| **Progress Updates** | GUI callbacks | frappe.publish_realtime() |
| **Error Handling** | Try/catch + messagebox | frappe.throw() + error log |

---

## Migration Path: SQLite → MariaDB

```
FileSearcher file_index.db
┌─────────────────────────────────────┐
│ id  │ lot      │ file_type  │ path  │
├─────┼──────────┼────────────┼───────┤
│ 1   │ 12345678 │ advisor    │ \\... │
│ 2   │ 12345678 │ scan       │ \\... │
│ 3   │ 87654321 │ polish_vid │ \\... │
└─────────────────────────────────────┘
        │
        │ Migration Script
        │ import sqlite3, frappe
        │
        ▼
Frappe tabFile Index
┌─────────────────────────────────────────────────────────────────┐
│ name │ lot_number │ file_type │ file_path │ file_name │ file_size │
├──────┼────────────┼───────────┼───────────┼───────────┼───────────┤
│ FI-1 │ 12345678   │ advisor   │ \\...     │ file.adv  │ 0.5       │
│ FI-2 │ 12345678   │ scan      │ \\...     │ scan.pdf  │ 1.2       │
│ FI-3 │ 87654321   │ polish_v  │ \\...     │ video.mp4 │ 150.0     │
└─────────────────────────────────────────────────────────────────┘
        │
        ├─ Auto-name: "FI-.#####"
        ├─ indexed_on: Datetime
        ├─ Audit fields (owner, creation, modified)
        └─ Permissions (System Manager)
```

---

## Performance Comparison

### FileSearcher.py
- **Indexing**: ~1000 files/second (SQLite insert speed)
- **Search**: ~50-100ms (SQLite SELECT with index)
- **Concurrency**: Limited (threading + GIL)
- **Scalability**: Single machine only

### Frappe Implementation
- **Indexing**: ~500-1000 files/second (MariaDB insert + ORM overhead)
- **Search**: ~10-50ms (MariaDB SELECT + cache hit)
- **Concurrency**: Unlimited (RQ workers + web workers)
- **Scalability**: Horizontal (add more app/DB servers)

---

## Deployment Topology

### FileSearcher.py
```
┌─────────────────────┐
│   User's Desktop    │
│  ┌───────────────┐  │
│  │ FileSearcher  │  │
│  │   (Python)    │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │  file_index   │  │
│  │    .db        │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │
           │ UNC Path
           ▼
┌─────────────────────┐
│  Network Share      │
│  (\\nas\edox)       │
└─────────────────────┘
```

### Frappe Implementation
```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼──────┐
│  Frappe App 1  │   │ Frappe App 2  │
│   (Gunicorn)   │   │  (Gunicorn)   │
└───────┬────────┘   └────────┬──────┘
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼───────────┐
        │   MariaDB Cluster    │
        │  (tabFile Index)     │
        └──────────────────────┘
                   │
        ┌──────────▼───────────┐
        │   Redis (Cache/Queue)│
        └──────────────────────┘
                   │
        ┌──────────▼───────────┐
        │    RQ Workers x4     │
        │   (Background Jobs)  │
        └──────────┬───────────┘
                   │
                   │ SMB/CIFS
                   ▼
        ┌──────────────────────┐
        │   Network Share      │
        │   (\\nas\edox)       │
        └──────────────────────┘
```

---

## Summary: Why Frappe Implementation is Superior

### ✅ **Advantages**
1. **Multi-user**: Web-based, concurrent access
2. **Scalable**: Add more workers/servers as needed
3. **Reliable**: ACID database, queue-based jobs
4. **Auditable**: Full change tracking, search logs
5. **Maintainable**: Configuration-driven, no code changes
6. **Secure**: Role-based permissions, SSL/TLS
7. **Remote**: Access from anywhere, mobile-friendly
8. **Integrated**: Ties into Cash Document workflow

### ⚠️ **Trade-offs**
1. **Setup complexity**: Requires Frappe stack (vs standalone .exe)
2. **ORM overhead**: Slightly slower inserts (500-1000/s vs 1000/s)
3. **Learning curve**: Developers need Frappe knowledge
4. **Infrastructure**: Needs servers, not just desktop app

### 🎯 **Recommendation**
**Use Frappe implementation** for production system due to superior:
- Scalability (multi-user, distributed)
- Reliability (queue-based background jobs)
- Integration (native to Cash Document workflow)
- Auditability (search logs, change tracking)

**FileSearcher.py remains useful** for:
- Quick desktop utility for ad-hoc searches
- Offline access when server unavailable
- Migration/import tool for existing data
