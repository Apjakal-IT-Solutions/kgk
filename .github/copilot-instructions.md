# KGK Customisations - AI Coding Agent Instructions

## Project Overview
KGK Customisations is a **Frappe/ERPNext custom app** for diamond manufacturing and cash management. This is NOT a standalone Python project - it extends the Frappe framework with custom DocTypes, reports, and business logic.

**Key Business Domains:**
- **Cash Management**: Multi-company cash document tracking with audit trails and reconciliation
- **Stone Processing**: Diamond parcel management, predictions, and factory workflows
- **File Indexing**: Lot-based video/advisor/scan file management (independent from cash system)
- **OCR Integration**: Bulk data import from Excel/CSV with validation

---

## Critical Architecture Knowledge

### Frappe Framework Fundamentals
This app runs inside a **Frappe Bench** environment. Never suggest standalone Django/Flask patterns.

**Essential Commands (always use these):**
```bash
# Working directory: /opt/bench/frappe-bench
bench --site kgkerp-test.local migrate          # Apply schema changes
bench --site kgkerp-test.local clear-cache      # Reload Python/JS changes
bench restart                                    # Restart all services
bench --site kgkerp-test.local console          # Python REPL with Frappe context

# Development workflow (changes require cache clear or restart)
bench --site kgkerp-test.local execute <module.function>  # Run Python function once
```

**File Structure Convention:**
```
kgk_customisations/
├── kgk_customisations/         # Main module (YES, nested)
│   ├── doctype/               # DocTypes (ORM models)
│   │   └── cash_document/     # Example DocType
│   │       ├── cash_document.json          # Schema definition
│   │       ├── cash_document.py            # Controller class
│   │       └── cash_document.js            # Client-side logic
│   ├── report/                # Script/Query/Print reports
│   ├── hooks.py               # Event hooks and scheduler
│   ├── tasks.py               # Scheduled background jobs
│   └── utils/                 # Shared utilities
├── file_management/           # File indexing module (separate)
│   ├── doctype/
│   └── Utils/                 # Indexer, file operations
└── fixtures/                  # Role/permission fixtures
```

### DocType Development Pattern
**Every DocType has 3 core files:**
1. **`.json`** - Schema (fields, permissions, naming). Edit via Desk UI, export to version control
2. **`.py`** - Controller class with lifecycle hooks:
   ```python
   class CashDocument(Document):
       def before_insert(self):  # Before DB insert
       def before_save(self):    # Before every save
       def validate(self):       # Data validation
       def on_submit(self):      # When submitted (if submittable)
       def on_cancel(self):      # When cancelled
       
       @frappe.whitelist()       # Expose to JS via frappe.call()
       def custom_method(self):
   ```
3. **`.js`** - Client-side logic:
   ```javascript
   frappe.ui.form.on('Cash Document', {
       refresh(frm) {},           // Form load
       onload(frm) {},            // Once on first load
       field_name(frm) {},        // Field change trigger
       custom_button_click(frm) {} // Button handlers
   });
   ```

**Data Access Pattern (Python):**
```python
# Create
doc = frappe.get_doc({
    "doctype": "Cash Document",
    "company": "KGK",
    "amount": 1000
})
doc.insert(ignore_permissions=True)  # Skip permission checks
frappe.db.commit()  # Required after inserts

# Read
doc = frappe.get_doc("Cash Document", "CD-KGK-2025-12-00001")
docs = frappe.get_all("Cash Document", filters={"company": "KGK"}, fields=["name", "amount"])

# Update
doc.amount = 2000
doc.save()

# Delete
frappe.delete_doc("Cash Document", "CD-KGK-2025-12-00001")
```

**Data Access Pattern (JavaScript):**
```javascript
// Server call
frappe.call({
    method: 'kgk_customisations.kgk_customisations.doctype.cash_document.cash_document.custom_method',
    args: { doc_name: frm.doc.name },
    callback: (r) => {
        frm.set_value('field_name', r.message);
    }
});

// Database query
frappe.db.get_value('Company', frm.doc.company, 'abbr', (r) => {
    console.log(r.abbr);
});
```

---

## Project-Specific Patterns

### 1. Cash Document System Architecture
**Core Flow:** Draft → Submitted → Reconciled (with audit trail at every step)

**Key Files:**
- `doctype/cash_document/cash_document.py` - Main controller (582 lines)
- `doctype/daily_cash_balance/daily_cash_balance.py` - Auto-calculation
- `tasks.py` - Scheduled jobs (daily_balance_calculation, reconciliation)
- `audit_trail.py` - Change tracking utility

**Critical Conventions:**
- **Autoname pattern:** `CD-{company_abbr}-.YYYY.-.MM.-.#####.` (defined in autoname() method)
- **Audit fields auto-populate:** created_by_user, last_modified_by, last_modified_date
- **Child table cleanup required:** Call `self.clean_child_tables()` in `before_save()` to prevent framework issues
- **File attachments:** Primary document + supporting files with auto-assigned suffix letters (A, B, C...)
- **Workflow states:** Draft (editable) → Submitted (locked) → Cancelled (invalidated)

**Example validate() pattern:**
```python
def validate(self):
    if not self.company:
        frappe.throw("Company is required")
    
    if self.status != "Draft" and not self.primary_document_file:
        frappe.throw("Primary Document File is required for non-Draft documents")
    
    self.validate_file_attachments()
```

### 2. File Indexing System (Lot-Based)
**IMPORTANT:** Completely independent from Cash Documents - separate network folders.

**Architecture:**
```
File Search Config (DocType)
    ├── File Directory (Child Table) - 12 network paths configured
    └── File Index (DocType) - Indexed file records by lot_number

indexer.py (Utils/indexer.py) - Background indexing jobs
    ├── extract_lot_number() - 8-digit pattern from path
    ├── index_polish_videos() - *.mp4, skip -F/-S/-R folders
    ├── index_rough_videos() - *.mp4, only -R folders
    ├── index_advisor_files() - *.adv files
    └── index_scan_files() - *.pdf, *.png, *.jpg, *.tif

Scheduler (hooks.py):
    daily: index_all_files()
    weekly: validate_indexed_files()
```

**Network Path Convention:**
- Polish/Rough Videos: `\\video-pc1\data`, `\\nas-gradding\POLISH-VIDEO`
- Advisor Files: `\\Nas-planning\stones\*.adv`
- Scans: `\\roughvideo1\My Scans2\*.{pdf,png,jpg,tif}`
- **Folder Exclusions:** Skip -F (sparkle), -S (fluorescence) for polish; only -R for rough

**Lot Number Extraction Pattern:**
```python
def extract_lot_number(path) -> Optional[str]:
    """Extract 8-digit lot number from path"""
    for text in (path.parent.name, path.name):
        m = re.search(r"(\d{8})", text)
        if m:
            return m.group(1)
    return None
```

### 3. Report Development
**Report Types:** Script Report (Python), Query Report (SQL), Print Format

**Stone Prediction Analysis Example (`report/stone_prediction_analysis/`):**
```python
def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    message = None
    chart = get_chart_data(data, filters)
    summary = get_report_summary(data, filters)
    report_summary = get_summary_data_for_excel(data, filters)  # Separate Excel sheet
    return columns, data, message, chart, summary, report_summary
```

**Filter Pattern (JavaScript):**
```javascript
frappe.query_reports["Stone Prediction Analysis"] = {
    filters: [
        { fieldname: "serial_number", label: "Serial Number", fieldtype: "Data" },
        { fieldname: "from_date", label: "From Date", fieldtype: "Date" }  // No default = show all
    ]
};
```

**SQL Query Pattern (Python):**
```python
def get_data(filters):
    conditions = get_conditions(filters)
    return frappe.db.sql(f"""
        SELECT sp.name, sp.lot_id, sp.serial_number
        FROM `tabStone Prediction` sp
        WHERE {conditions}
    """, filters, as_dict=1)

def get_conditions(filters):
    conditions = ["1=1"]  # Always true base condition
    if filters.get("serial_number"):
        conditions.append("sp.serial_number = %(serial_number)s")  # Exact match only
    return " AND ".join(conditions)
```

### 4. Parcel/Stone Import System
**Pattern:** Excel → pandas → validation → bulk insert

**Key File:** `doctype/parcel/parcel.py` (1516 lines)

**Column Mapping Convention:**
```python
COLUMN_MAP = {
    "Parcel Name": "stone_name",       # Exact Excel header → DocType field
    "Org Wght": "org_weight",
    "Wght E": "weight_e",              # E suffix = Expected
    "Wght L": "weight_l",              # L suffix = Lab results
}
```

**Validation Pattern:**
```python
def validate_excel_before_import(file_url: str):
    file_path = get_file_path(file_url)
    df = pd.read_excel(file_path)
    
    # Validate required columns
    required = ["Parcel Name", "Org Wght"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        frappe.throw(f"Missing columns: {', '.join(missing)}")
```

### 5. Scheduled Tasks Pattern
**File:** `kgk_customisations/tasks.py` (296 lines)

**Registration in hooks.py:**
```python
scheduler_events = {
    "daily": ["kgk_customisations.kgk_customisations.tasks.daily_balance_calculation"],
    "hourly": ["kgk_customisations.kgk_customisations.tasks.check_pending_verifications"],
    "weekly": ["kgk_customisations.file_management.Utils.file_operations.validate_indexed_files"]
}
```

**Task Implementation Pattern:**
```python
def daily_balance_calculation():
    try:
        yesterday = add_days(getdate(), -1)
        companies = frappe.get_all("Company", filters={"disabled": 0}, pluck="name")
        
        for company in companies:
            if not frappe.db.exists("Daily Cash Balance", {"balance_date": yesterday, "company": company}):
                balance_doc = frappe.get_doc({...})
                balance_doc.insert(ignore_permissions=True)
                frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "Daily Balance Calculation Failed")
```

---

## Common Pitfalls & Solutions

### Problem: Changes Not Reflecting
**Solution:** Always clear cache or restart after Python/JS changes:
```bash
bench --site kgkerp-test.local clear-cache && bench restart
```

### Problem: Permission Denied
**Solution:** Use `ignore_permissions=True` in scheduled tasks:
```python
doc.insert(ignore_permissions=True)
```

### Problem: Child Table Errors
**Solution:** Call `self.clean_child_tables()` early in `before_save()`:
```python
def before_save(self):
    self.clean_child_tables()  # Must be first
    # ... rest of logic
```

### Problem: Filter Returns All Records
**Solution:** Avoid "OR field IS NULL" logic - use exact matches:
```python
# ❌ WRONG - matches everything
if filters.get("serial_number"):
    conditions.append("(sp.serial_number = %(serial_number)s OR sp.serial_number IS NULL)")

# ✅ CORRECT - exact match only
if filters.get("serial_number"):
    conditions.append("sp.serial_number = %(serial_number)s")
```

### Problem: Network Paths Not Accessible
**Context:** Windows UNC paths (`\\server\share`) don't work directly on Linux
**Solution:** Mount network drives or store paths in File Search Config for reference

---

## Testing & Debugging

**Run specific test:**
```bash
bench --site kgkerp-test.local run-tests --app kgk_customisations --doctype "Cash Document"
```

**Interactive debugging:**
```bash
bench --site kgkerp-test.local console
>>> doc = frappe.get_doc("Cash Document", "CD-KGK-2025-12-00001")
>>> doc.calculate_totals()
```

**View logs:**
```bash
tail -f /opt/bench/frappe-bench/logs/frappe.log
```

---

## Key Integration Points

**ERPNext Dependencies:**
- Company (mandatory for all transactions)
- User (for audit trails and permissions)
- File (for document attachments)
- Role (Cash Basic User, Cash Checker, Cash Accountant, Cash Super User)

**External Systems:**
- Network storage (Windows file shares)
- OCR data imports (Excel/CSV)
- Redis (search result caching)

---

## Development Workflow Checklist

When creating new DocTypes:
1. Create via Desk UI → Export JSON to version control
2. Add Python controller with validate(), before_save() methods
3. Add JavaScript form scripts with refresh(), onload() handlers
4. Update hooks.py if scheduler/events needed
5. Add to fixtures if roles/permissions required
6. Run migrate + clear-cache
7. Test with real data, check logs for errors

When modifying reports:
1. Edit Python execute() function for data/columns
2. Edit JavaScript filters array for UI
3. Clear cache (Python changes) or hard refresh browser (JS changes)
4. Test with various filter combinations
5. Verify Excel export includes summary sheet if applicable

---

## Quick Reference Commands

```bash
# Development cycle
cd /opt/bench/frappe-bench
bench --site kgkerp-test.local migrate
bench --site kgkerp-test.local clear-cache
bench restart

# Background job testing
bench --site kgkerp-test.local execute kgk_customisations.file_management.Utils.indexer.index_all_files

# Database queries
bench --site kgkerp-test.local mariadb
> SELECT name, company, amount FROM `tabCash Document` LIMIT 10;

# Git workflow (current branch: stonetracking)
git status
git add .
git commit -m "feat: add stone prediction summary export"
git push origin stonetracking
```

---

## When You're Stuck

1. **Check existing patterns first** - Search codebase for similar DocTypes/reports
2. **Read Frappe docs** - https://frappeframework.com/docs/
3. **Use frappe.log_error()** - Errors appear in Error Log DocType
4. **Test in console** - `bench console` for interactive debugging
5. **Check logs** - `tail -f logs/frappe.log` for real-time errors

---

## Final Notes

- **This is a Frappe app** - Don't suggest Flask/Django/FastAPI patterns
- **Always commit after bulk operations** - `frappe.db.commit()`
- **Use type hints** - `from typing import Optional, List, Dict`
- **Follow pre-commit rules** - ruff, eslint, prettier, pyupgrade
- **Test before committing** - Run migrations and clear cache
- **Document complex logic** - Future maintainers will thank you
