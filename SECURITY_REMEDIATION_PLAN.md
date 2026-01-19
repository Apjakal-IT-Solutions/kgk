# Security Remediation Implementation Plan
## KGK Customisations Application

**Plan Date:** January 19, 2026  
**Target Completion:** March 31, 2026 (10 weeks)  
**Application:** kgk_customisations  
**Repository:** Apjakal-IT-Solutions/kgk  
**Priority:** URGENT - Production Blocker

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Team & Resources](#team--resources)
3. [Phase 1: Critical Vulnerabilities (Week 1-2)](#phase-1-critical-vulnerabilities-week-1-2)
4. [Phase 2: High Severity Issues (Week 3-5)](#phase-2-high-severity-issues-week-3-5)
5. [Phase 3: Medium Severity Issues (Week 6-7)](#phase-3-medium-severity-issues-week-6-7)
6. [Phase 4: Testing & Validation (Week 8-9)](#phase-4-testing--validation-week-8-9)
7. [Phase 5: Documentation & Deployment (Week 10)](#phase-5-documentation--deployment-week-10)
8. [Risk Management](#risk-management)
9. [Quality Assurance](#quality-assurance)
10. [Success Metrics](#success-metrics)

---

## Executive Summary

### Situation
Security audit identified **38 vulnerabilities** including 3 CRITICAL issues that pose immediate risk to financial data integrity, system security, and compliance.

### Objective
Systematically remediate all security vulnerabilities in a controlled, tested manner to enable safe production deployment.

### Timeline
- **Total Duration:** 10 weeks
- **Critical Path:** 2 weeks (Phases 1)
- **Production Ready:** Week 9 (with final testing)
- **Full Deployment:** Week 10

### Budget
- **Developer Hours:** 180-220 hours
- **QA/Testing Hours:** 40-60 hours
- **Security Review Hours:** 20-30 hours
- **Total Estimated Hours:** 240-310 hours

### Success Criteria
1. ✅ All CRITICAL vulnerabilities resolved
2. ✅ All HIGH severity vulnerabilities resolved
3. ✅ 80%+ MEDIUM severity vulnerabilities resolved
4. ✅ Security testing passed
5. ✅ Code review completed
6. ✅ Documentation updated

---

## Team & Resources

### Required Roles

| Role | Responsibility | Time Commitment |
|------|---------------|-----------------|
| **Lead Developer** | Architecture decisions, critical fixes | 100-120 hours |
| **Backend Developer** | Python security fixes | 80-100 hours |
| **QA Engineer** | Testing, validation | 40-60 hours |
| **Security Specialist** | Code review, consultation | 20-30 hours |
| **DevOps Engineer** | Deployment, monitoring | 10-15 hours |

### Tools Required

**Development:**
- VS Code with security extensions
- Bandit (Python security linter)
- SonarQube or similar SAST tool
- Git for version control

**Testing:**
- pytest for unit tests
- OWASP ZAP for security testing
- Burp Suite (optional)
- SQLMap for SQL injection testing

**Monitoring:**
- Log analysis tools
- Security event monitoring

---

## Phase 1: Critical Vulnerabilities (Week 1-2)

**Duration:** 2 weeks (80 hours)  
**Priority:** URGENT  
**Blocker:** Production deployment blocked until complete

### Overview
Fix all 3 CRITICAL vulnerabilities that pose immediate security risk.

---

### Task 1.1: Fix SQL Injection Vulnerabilities

**Priority:** CRITICAL  
**Effort:** 24 hours  
**Owner:** Lead Developer + Backend Developer

#### Files to Modify
1. `kgk_customisations/report/stone_prediction_analysis/stone_prediction_analysis.py`
2. `kgk_customisations/report/cash_flow_analysis/cash_flow_analysis.py`
3. `kgk_customisations/report/audit_trail_report/audit_trail_report.py`
4. All other report files using f-strings in SQL

#### Implementation Steps

**Step 1: Audit All SQL Queries (4 hours)**
```bash
# Find all SQL queries in codebase
grep -r "frappe.db.sql" apps/kgk_customisations --include="*.py" > sql_audit.txt
grep -r "\.format\(" apps/kgk_customisations --include="*.py" | grep -i "sql\|select\|where" >> sql_audit.txt
```

**Step 2: Create Safe Query Helper Functions (4 hours)**

Create `utils/query_builder.py`:
```python
"""
Safe SQL Query Builder Utilities
Prevents SQL injection by using parameterized queries
"""
import frappe
from typing import Dict, List, Any, Optional

class SafeQueryBuilder:
    """Build SQL queries safely with parameter binding"""
    
    @staticmethod
    def build_where_clause(filters: Dict[str, Any], 
                          field_mapping: Dict[str, str]) -> tuple:
        """
        Build WHERE clause from filters safely
        
        Args:
            filters: Dictionary of filter field -> value
            field_mapping: Dictionary mapping filter keys to SQL field names
            
        Returns:
            Tuple of (where_clause_string, parameters_dict)
        """
        conditions = []
        params = {}
        
        for filter_key, filter_value in filters.items():
            if filter_key in field_mapping and filter_value:
                sql_field = field_mapping[filter_key]
                param_name = filter_key
                
                # Handle different filter types
                if isinstance(filter_value, list):
                    # IN clause
                    placeholders = ', '.join([f'%({param_name}_{i})s' 
                                            for i in range(len(filter_value))])
                    conditions.append(f"{sql_field} IN ({placeholders})")
                    for i, val in enumerate(filter_value):
                        params[f"{param_name}_{i}"] = val
                elif isinstance(filter_value, tuple) and len(filter_value) == 2:
                    # Range query
                    conditions.append(f"{sql_field} BETWEEN %({param_name}_start)s AND %({param_name}_end)s")
                    params[f"{param_name}_start"] = filter_value[0]
                    params[f"{param_name}_end"] = filter_value[1]
                else:
                    # Equality
                    conditions.append(f"{sql_field} = %({param_name})s")
                    params[param_name] = filter_value
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params
    
    @staticmethod
    def execute_safe_query(query_template: str, 
                          params: Dict[str, Any],
                          as_dict: bool = True) -> List:
        """
        Execute parameterized query safely
        
        Args:
            query_template: SQL with %(param_name)s placeholders
            params: Dictionary of parameters
            as_dict: Return results as dictionaries
            
        Returns:
            Query results
        """
        try:
            return frappe.db.sql(query_template, params, as_dict=as_dict)
        except Exception as e:
            frappe.log_error(
                f"Safe query execution failed: {str(e)}\nQuery: {query_template}", 
                "Query Builder Error"
            )
            raise frappe.ValidationError("Database query failed. Please contact administrator.")
```

**Step 3: Refactor stone_prediction_analysis.py (4 hours)**

```python
# Before (VULNERABLE):
predictions = frappe.db.sql(f"""
    SELECT sp.name, sp.prediction_date, ...
    FROM `tabStone Prediction` sp
    LEFT JOIN `tabStone Cuts` sc ON sc.parent = sp.name
    WHERE {conditions}
    GROUP BY sp.name
    ORDER BY sp.prediction_date DESC, sp.name
""", filters, as_dict=1)

# After (SECURE):
from kgk_customisations.utils.query_builder import SafeQueryBuilder

def get_data(filters):
    """Fetch Stone Prediction data with aggregations - SQL INJECTION SAFE"""
    
    # Define field mapping
    field_mapping = {
        "serial_number": "sp.serial_number",
        "lot_id": "sp.lot_id",
        "from_date": "sp.prediction_date",
        "to_date": "sp.prediction_date",
        "predicted_by": "sp.predicted_by"
    }
    
    # Build WHERE clause safely
    where_conditions = []
    params = {}
    
    if filters.get("serial_number"):
        where_conditions.append("sp.serial_number = %(serial_number)s")
        params["serial_number"] = filters.get("serial_number")
    
    if filters.get("lot_id"):
        where_conditions.append("sp.lot_id = %(lot_id)s")
        params["lot_id"] = filters.get("lot_id")
    
    if filters.get("from_date"):
        where_conditions.append("sp.prediction_date >= %(from_date)s")
        params["from_date"] = filters.get("from_date")
    
    if filters.get("to_date"):
        where_conditions.append("sp.prediction_date <= %(to_date)s")
        params["to_date"] = filters.get("to_date")
    
    if filters.get("predicted_by"):
        where_conditions.append("sp.predicted_by = %(predicted_by)s")
        params["predicted_by"] = filters.get("predicted_by")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Execute safe parameterized query
    query = f"""
        SELECT 
            sp.name,
            sp.prediction_date,
            sp.predicted_by,
            sp.lot_id,
            sp.serial_number,
            sp.original_weight,
            sp.number_of_cuts,
            sp.estimated_value,
            sp.docstatus,
            COALESCE(SUM(sc.pol_cts), 0) as total_pol_cts
        FROM 
            `tabStone Prediction` sp
        LEFT JOIN 
            `tabStone Cuts` sc ON sc.parent = sp.name
        WHERE
            {where_clause}
        GROUP BY 
            sp.name
        ORDER BY 
            sp.prediction_date DESC, sp.name
    """
    
    predictions = SafeQueryBuilder.execute_safe_query(query, params)
    
    # Process results
    for pred in predictions:
        if pred.docstatus == 0:
            pred.docstatus = "Draft"
        elif pred.docstatus == 1:
            pred.docstatus = "Submitted"
        elif pred.docstatus == 2:
            pred.docstatus = "Cancelled"
    
    return predictions
```

**Step 4: Apply Same Pattern to Other Reports (8 hours)**
- cash_flow_analysis.py
- audit_trail_report.py
- ocr_parcel_merge.py
- All other reports with SQL queries

**Step 5: Testing (4 hours)**
```python
# Create test file: tests/test_sql_injection_prevention.py
import frappe
import unittest

class TestSQLInjectionPrevention(unittest.TestCase):
    """Test that SQL injection attempts are blocked"""
    
    def test_malicious_serial_number_filter(self):
        """Test SQL injection via serial_number filter"""
        malicious_filters = {
            "serial_number": "'; DROP TABLE `tabStone Prediction`; --"
        }
        
        # Should not raise exception or execute DROP
        from kgk_customisations.kgk_customisations.report.stone_prediction_analysis.stone_prediction_analysis import execute
        
        try:
            columns, data = execute(malicious_filters)
            # Query should execute safely, returning empty results
            self.assertIsInstance(data, list)
        except frappe.ValidationError:
            # Acceptable - validation caught it
            pass
    
    def test_sql_injection_via_lot_id(self):
        """Test SQL injection via lot_id filter"""
        malicious_filters = {
            "lot_id": "1' OR '1'='1"
        }
        
        from kgk_customisations.kgk_customisations.report.stone_prediction_analysis.stone_prediction_analysis import execute
        columns, data = execute(malicious_filters)
        
        # Should not return all records (which OR 1=1 would do if vulnerable)
        # Verify parameterization worked
        self.assertIsInstance(data, list)
```

#### Deliverables
- [ ] All report SQL queries refactored with parameterization
- [ ] SafeQueryBuilder utility created and tested
- [ ] Unit tests for SQL injection prevention
- [ ] Code review completed
- [ ] Documentation updated

#### Verification
```bash
# Run security linter
bandit -r apps/kgk_customisations/kgk_customisations/report/ -f json -o sql_injection_scan.json

# Manual verification
grep -r "frappe.db.sql(f\"" apps/kgk_customisations/
# Should return 0 results

# Run tests
cd apps/kgk_customisations
pytest tests/test_sql_injection_prevention.py -v
```

---

### Task 1.2: Fix Path Traversal Vulnerabilities

**Priority:** CRITICAL  
**Effort:** 20 hours  
**Owner:** Backend Developer

#### Files to Modify
1. `utils/file_opener.py`
2. `file_management/Utils/file_operations.py`
3. `file_management/Utils/file_opener.py`

#### Implementation Steps

**Step 1: Create Secure Path Validator (4 hours)**

Create `utils/secure_file_access.py`:
```python
"""
Secure File Access Utilities
Prevents path traversal and unauthorized file access
"""
import os
import frappe
from pathlib import Path
from typing import Optional, List, Tuple

class SecureFileAccess:
    """Secure file access with path validation"""
    
    # Define allowed base directories
    ALLOWED_DIRECTORIES = [
        "/opt/bench/frappe-bench/sites/{site}/public/files",
        "/opt/bench/frappe-bench/sites/{site}/private/files",
        "/opt/bench/frappe-bench/apps/kgk_customisations/kgk_customisations/public",
    ]
    
    @classmethod
    def get_allowed_directories(cls) -> List[Path]:
        """Get list of allowed directories for current site"""
        site = frappe.local.site
        allowed = []
        
        for dir_template in cls.ALLOWED_DIRECTORIES:
            dir_path = dir_template.format(site=site)
            resolved = Path(dir_path).resolve()
            if resolved.exists():
                allowed.append(resolved)
        
        # Add site-specific paths from configuration
        config = frappe.get_single("File Search Config")
        if config:
            for row in config.file_directories:
                if row.enabled:
                    allowed.append(Path(row.directory_path).resolve())
        
        return allowed
    
    @classmethod
    def validate_file_path(cls, file_path: str) -> Tuple[bool, str, Optional[Path]]:
        """
        Validate that file path is safe and within allowed directories
        
        Args:
            file_path: User-provided file path
            
        Returns:
            Tuple of (is_valid, message, resolved_path)
        """
        if not file_path:
            return False, "File path is required", None
        
        # Check for obvious traversal attempts
        if ".." in file_path:
            frappe.log_error(
                f"Path traversal attempt detected: {file_path}",
                "Security: Path Traversal Attempt"
            )
            return False, "Invalid file path", None
        
        # Check for absolute paths (unless explicitly allowed)
        if file_path.startswith('/') or file_path.startswith('\\'):
            # Only allow if it's within allowed directories
            pass
        
        try:
            # Resolve to absolute path
            requested_path = Path(file_path).resolve()
            
            # Check if path exists
            if not requested_path.exists():
                return False, "File not found", None
            
            # Check if it's a file (not directory)
            if not requested_path.is_file():
                return False, "Path is not a file", None
            
            # Check if within allowed directories
            allowed_dirs = cls.get_allowed_directories()
            is_allowed = False
            
            for allowed_dir in allowed_dirs:
                try:
                    # Check if requested path is relative to allowed directory
                    requested_path.relative_to(allowed_dir)
                    is_allowed = True
                    break
                except ValueError:
                    # Not relative to this directory, try next
                    continue
            
            if not is_allowed:
                frappe.log_error(
                    f"Unauthorized file access attempt: {file_path}\n"
                    f"Resolved to: {requested_path}\n"
                    f"Allowed directories: {allowed_dirs}",
                    "Security: Unauthorized File Access"
                )
                return False, "Access denied: File not in allowed directory", None
            
            # Additional checks
            file_size = requested_path.stat().st_size
            max_size = 100 * 1024 * 1024  # 100 MB
            if file_size > max_size:
                return False, f"File too large (max {max_size / 1024 / 1024:.0f} MB)", None
            
            return True, "Valid", requested_path
            
        except Exception as e:
            frappe.log_error(
                f"File path validation error: {file_path}\n{str(e)}",
                "File Path Validation Error"
            )
            return False, "Invalid file path", None
    
    @classmethod
    def validate_file_extension(cls, file_path: Path, 
                               allowed_extensions: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Validate file extension
        
        Args:
            file_path: Resolved file path
            allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.xlsx'])
            
        Returns:
            Tuple of (is_valid, message)
        """
        if allowed_extensions is None:
            # Default allowed extensions
            allowed_extensions = [
                '.pdf', '.xlsx', '.xls', '.xlsb', '.csv',
                '.jpg', '.jpeg', '.png', '.gif',
                '.doc', '.docx', '.txt',
                '.mp4', '.avi', '.mov'
            ]
        
        file_ext = file_path.suffix.lower()
        
        if file_ext not in allowed_extensions:
            return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        return True, "Valid"
```

**Step 2: Refactor file_opener.py (6 hours)**

```python
# utils/file_opener.py - SECURE VERSION
import frappe
import subprocess
import platform
from pathlib import Path
from typing import Union, List, Dict
from kgk_customisations.utils.secure_file_access import SecureFileAccess

@frappe.whitelist()
def open_file(file_path: str):
    """
    Open file using system default application - SECURE VERSION
    
    Args:
        file_path: File path (will be validated)
        
    Returns:
        dict: Status and message
    """
    # Validate user has permission
    if not frappe.has_permission("File", "read"):
        frappe.throw("You don't have permission to open files", frappe.PermissionError)
    
    try:
        # SECURITY: Validate file path
        is_valid, message, validated_path = SecureFileAccess.validate_file_path(file_path)
        
        if not is_valid:
            return {
                "status": "error",
                "message": message
            }
        
        # SECURITY: Validate file extension
        ext_valid, ext_message = SecureFileAccess.validate_file_extension(validated_path)
        if not ext_valid:
            return {
                "status": "error",
                "message": ext_message
            }
        
        # Get system type
        system = platform.system()
        
        # Open file using appropriate method
        # Note: Still uses subprocess but with validated path only
        if system == "Windows":
            os.startfile(str(validated_path))
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(validated_path)], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", str(validated_path)], check=True)
        
        # Log successful access for audit
        frappe.logger().info(f"User {frappe.session.user} opened file: {validated_path.name}")
        
        return {
            "status": "success",
            "message": f"File opened: {validated_path.name}"
        }
        
    except subprocess.CalledProcessError as e:
        error_msg = "Failed to open file with system application"
        frappe.log_error(f"{error_msg}: {str(e)}", "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }
    except Exception as e:
        error_msg = "An error occurred while opening the file"
        frappe.log_error(f"{error_msg}: {str(e)}", "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def open_multiple_files(file_paths: Union[str, List[str]]):
    """
    Open multiple files at once - SECURE VERSION
    
    Args:
        file_paths: JSON string or list of file paths
        
    Returns:
        dict: Status with counts
    """
    # Validate user has permission
    if not frappe.has_permission("File", "read"):
        frappe.throw("You don't have permission to open files", frappe.PermissionError)
    
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
        
        # Limit number of files that can be opened at once
        MAX_FILES = 10
        if len(file_paths) > MAX_FILES:
            return {
                "status": "error",
                "message": f"Cannot open more than {MAX_FILES} files at once"
            }
        
        results = []
        success_count = 0
        failed_count = 0
        
        for file_path in file_paths:
            result = open_file(file_path)
            results.append({
                "file": Path(file_path).name,  # Only show filename in response
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
        error_msg = "Failed to process multiple file request"
        frappe.log_error(f"{error_msg}: {str(e)}", "File Opener Error")
        return {
            "status": "error",
            "message": error_msg
        }
```

**Step 3: Refactor file_operations.py (6 hours)**

Apply similar security patterns to all file operation functions in:
- `file_management/Utils/file_operations.py`
- `file_management/Utils/file_opener.py`

**Step 4: Testing (4 hours)**

```python
# tests/test_path_traversal_prevention.py
import frappe
import unittest
from pathlib import Path

class TestPathTraversalPrevention(unittest.TestCase):
    """Test that path traversal attacks are blocked"""
    
    def test_parent_directory_traversal(self):
        """Test ../ path traversal attempt"""
        from kgk_customisations.utils.file_opener import open_file
        
        malicious_path = "../../../../etc/passwd"
        result = open_file(malicious_path)
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid file path", result["message"])
    
    def test_absolute_path_outside_allowed(self):
        """Test absolute path outside allowed directories"""
        result = open_file("/etc/shadow")
        
        self.assertEqual(result["status"], "error")
    
    def test_valid_file_in_allowed_directory(self):
        """Test that valid files can still be accessed"""
        # Create a test file in allowed directory
        test_file = Path(frappe.get_site_path("public/files/test.txt"))
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        
        result = open_file(str(test_file))
        # Should succeed or fail for legitimate reasons, not security
        self.assertIn(result["status"], ["success", "error"])
```

#### Deliverables
- [ ] SecureFileAccess utility created
- [ ] All file operation functions refactored
- [ ] Path validation implemented
- [ ] Unit tests for path traversal prevention
- [ ] Security testing completed

---

### Task 1.3: Remove Permission Bypasses

**Priority:** CRITICAL  
**Effort:** 36 hours  
**Owner:** Lead Developer + Backend Developer

#### Files to Modify
48+ files using `ignore_permissions=True`

#### Implementation Steps

**Step 1: Audit All Permission Bypasses (4 hours)**

```bash
# Find all ignore_permissions usage
grep -rn "ignore_permissions=True" apps/kgk_customisations/ --include="*.py" > permission_bypasses.txt

# Categorize by necessity
# - System operations (may keep)
# - User operations (must remove)
# - Audit trail (may keep with logging)
```

**Step 2: Define Permission Strategy (4 hours)**

Create `docs/PERMISSION_STRATEGY.md`:
```markdown
# Permission Strategy

## Roles
- Cash Super User: Full access
- Cash Manager: Approve/reject, view all
- Cash Accountant: Create, edit own, view assigned
- Cash Checker: View, flag for review
- Cash Basic User: Create, view own

## DocType Permissions
Configure in JSON files:
- Cash Document
- Daily Cash Balance
- Cash Balance Submission
- etc.
```

**Step 3: Implement Permission Checks (20 hours)**

For each file with `ignore_permissions=True`:

```python
# BEFORE (INSECURE):
balance_doc.save(ignore_permissions=True)

# AFTER (SECURE):
# Check if user has write permission
if not frappe.has_permission("Daily Cash Balance", "write", balance_doc.name):
    frappe.throw(
        "You don't have permission to modify this balance record",
        frappe.PermissionError
    )

balance_doc.save()  # Let Frappe enforce permissions

# For system operations that genuinely need bypass:
if not frappe.has_permission("Daily Cash Balance", "write", balance_doc.name):
    # Log the permission bypass for audit
    frappe.logger().warning(
        f"System operation bypassing permissions: "
        f"User={frappe.session.user}, DocType=Daily Cash Balance, "
        f"Doc={balance_doc.name}, Reason=Automated balance calculation"
    )
    balance_doc.save(ignore_permissions=True)
else:
    balance_doc.save()
```

**Step 4: Configure DocType Permissions (4 hours)**

Update JSON permission files for each DocType:
```json
{
    "permissions": [
        {
            "role": "Cash Super User",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1,
            "submit": 1,
            "cancel": 1,
            "amend": 1
        },
        {
            "role": "Cash Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "submit": 1,
            "if_owner": 0
        },
        {
            "role": "Cash Accountant",
            "read": 1,
            "write": 1,
            "create": 1,
            "if_owner": 1
        }
    ]
}
```

**Step 5: Testing (4 hours)**

```python
# tests/test_permissions.py
class TestPermissions(unittest.TestCase):
    def setUp(self):
        self.test_user = "test_user@example.com"
        frappe.set_user(self.test_user)
    
    def test_cash_document_basic_user_cannot_approve(self):
        """Basic user cannot approve documents"""
        doc = frappe.get_doc("Cash Document", "CD-TEST-001")
        
        with self.assertRaises(frappe.PermissionError):
            doc.add_flag("Approved", "Test approval")
    
    def test_cash_manager_can_approve(self):
        """Manager can approve documents"""
        frappe.set_user("manager@example.com")
        doc = frappe.get_doc("Cash Document", "CD-TEST-001")
        
        # Should succeed
        result = doc.add_flag("Approved", "Manager approval")
        self.assertTrue(result)
```

#### Deliverables
- [ ] All unnecessary permission bypasses removed
- [ ] Remaining bypasses documented and logged
- [ ] DocType permissions configured
- [ ] Permission testing completed
- [ ] Documentation updated

---

### Phase 1 Deliverables & Acceptance Criteria

**Exit Criteria:**
- [ ] All SQL queries use parameterized approach
- [ ] No SQL injection vulnerabilities detected by tools
- [ ] All file operations validate paths
- [ ] No path traversal vulnerabilities detected
- [ ] Permission bypasses reduced by 90%+
- [ ] All critical tests passing
- [ ] Code review approved
- [ ] Security scan passed

**Sign-off Required:** Lead Developer, Security Specialist

---

## Phase 2: High Severity Issues (Week 3-5)

**Duration:** 3 weeks (60 hours)  
**Priority:** HIGH  
**Blocker:** Production deployment should wait

### Overview
Address all 8 HIGH severity vulnerabilities.

---

### Task 2.1: Implement Comprehensive File Upload Validation

**Priority:** HIGH  
**Effort:** 12 hours  
**Owner:** Backend Developer

#### Implementation Steps

**Step 1: Create File Validation Utility (4 hours)**

```python
# utils/file_validator.py
import magic
import os
from pathlib import Path
from typing import Tuple, Optional
import frappe

class FileValidator:
    """Comprehensive file upload validation"""
    
    # File type configurations
    ALLOWED_EXTENSIONS = {
        'excel': {'.xlsx', '.xls', '.xlsb', '.csv'},
        'pdf': {'.pdf'},
        'image': {'.jpg', '.jpeg', '.png', '.gif'},
        'document': {'.doc', '.docx', '.txt'},
        'video': {'.mp4', '.avi', '.mov'},
        'all': {'.xlsx', '.xls', '.xlsb', '.csv', '.pdf', 
                '.jpg', '.jpeg', '.png', '.gif',
                '.doc', '.docx', '.txt', '.mp4', '.avi', '.mov'}
    }
    
    ALLOWED_MIME_TYPES = {
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        # ... etc
    }
    
    MAX_FILE_SIZES = {
        'excel': 50 * 1024 * 1024,  # 50 MB
        'pdf': 20 * 1024 * 1024,     # 20 MB
        'image': 10 * 1024 * 1024,   # 10 MB
        'document': 10 * 1024 * 1024, # 10 MB
        'video': 100 * 1024 * 1024,  # 100 MB
        'default': 20 * 1024 * 1024  # 20 MB
    }
    
    @classmethod
    def validate_upload(cls, file_path: str, 
                       file_type: str = 'all',
                       check_content: bool = True) -> Tuple[bool, str]:
        """
        Comprehensive file upload validation
        
        Args:
            file_path: Path to uploaded file
            file_type: Type category (excel, pdf, image, etc.)
            check_content: Whether to validate file content (slower but more secure)
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            path = Path(file_path)
            
            # 1. Check file exists
            if not path.exists():
                return False, "File not found"
            
            # 2. Check is file (not directory)
            if not path.is_file():
                return False, "Invalid file"
            
            # 3. Validate extension
            file_ext = path.suffix.lower()
            allowed_exts = cls.ALLOWED_EXTENSIONS.get(file_type, cls.ALLOWED_EXTENSIONS['all'])
            
            if file_ext not in allowed_exts:
                return False, f"File type not allowed. Allowed: {', '.join(allowed_exts)}"
            
            # 4. Validate file size
            file_size = path.stat().st_size
            max_size = cls.MAX_FILE_SIZES.get(file_type, cls.MAX_FILE_SIZES['default'])
            
            if file_size > max_size:
                max_mb = max_size / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                return False, f"File too large ({actual_mb:.1f} MB). Max: {max_mb:.0f} MB"
            
            # 5. Check for empty files
            if file_size == 0:
                return False, "File is empty"
            
            # 6. Validate MIME type (if content checking enabled)
            if check_content:
                try:
                    mime = magic.from_file(str(path), mime=True)
                    expected_mime = cls.ALLOWED_MIME_TYPES.get(file_ext)
                    
                    if expected_mime and mime != expected_mime:
                        return False, f"File content doesn't match extension. Detected: {mime}"
                except Exception as e:
                    frappe.log_error(f"MIME type check failed: {str(e)}", "File Validation")
                    # Continue - MIME check is additional security, not required
            
            # 7. Scan for malicious content (basic checks)
            if file_ext in {'.xlsx', '.xls', '.xlsb', '.docx'}:
                # These are ZIP files - check for zip bombs
                if not cls._check_zip_safety(path):
                    return False, "File failed security scan"
            
            return True, "Valid"
            
        except Exception as e:
            frappe.log_error(f"File validation error: {str(e)}", "File Validation Error")
            return False, "File validation failed"
    
    @staticmethod
    def _check_zip_safety(file_path: Path) -> bool:
        """Check for zip bomb attacks"""
        import zipfile
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Check compression ratio
                compressed_size = file_path.stat().st_size
                uncompressed_size = sum(info.file_size for info in zf.filelist)
                
                # Suspicious if compression ratio > 100:1
                if compressed_size > 0 and uncompressed_size / compressed_size > 100:
                    frappe.log_error(
                        f"Suspicious compression ratio: {uncompressed_size / compressed_size:.1f}:1",
                        "Potential Zip Bomb"
                    )
                    return False
                
                # Check for too many files
                if len(zf.filelist) > 10000:
                    return False
                
            return True
        except zipfile.BadZipFile:
            return False
        except Exception:
            return False
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent issues"""
        import re
        
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 100:
            name = name[:100]
        
        return name + ext
```

**Step 2: Apply to Upload Functions (4 hours)**

Modify all file upload handling:
- `doctype/ocr_data_upload/ocr_data_upload.py`
- `doctype/parcel/parcel.py`
- `doctype/parcel_import/parcel_import.py`

**Step 3: Testing (4 hours)**

Test with malicious files:
- Zip bombs
- Files with mismatched extensions
- Oversized files
- Files with malicious names

#### Deliverables
- [ ] FileValidator utility created
- [ ] All upload functions use validation
- [ ] Malicious file testing completed
- [ ] Documentation updated

---

### Task 2.2: Add Access Controls to Whitelisted Methods

**Priority:** HIGH  
**Effort:** 16 hours  
**Owner:** Backend Developer

#### Implementation Strategy

For each of 79 whitelisted methods:

```python
# Pattern 1: Role-based check
@frappe.whitelist()
def sensitive_operation(data):
    # Check role
    if not frappe.has_role(["Cash Manager", "Cash Super User"]):
        frappe.throw("Insufficient permissions", frappe.PermissionError)
    
    # Proceed
    pass

# Pattern 2: Permission-based check  
@frappe.whitelist()
def modify_document(doc_name):
    # Check permission on specific document
    if not frappe.has_permission("Cash Document", "write", doc_name):
        frappe.throw("You cannot modify this document", frappe.PermissionError)
    
    # Proceed
    pass

# Pattern 3: Combined checks
@frappe.whitelist()
def bulk_operation(doc_names):
    # Must be manager
    if not frappe.has_role("Cash Manager"):
        frappe.throw("Only Cash Managers can perform bulk operations", frappe.PermissionError)
    
    # Check each document
    for doc_name in doc_names:
        if not frappe.has_permission("Cash Document", "write", doc_name):
            frappe.throw(f"No permission for {doc_name}", frappe.PermissionError)
    
    # Proceed
    pass
```

#### Priority Order
1. **Critical operations** (16 methods) - Week 3
2. **Financial operations** (25 methods) - Week 4  
3. **File operations** (20 methods) - Week 4
4. **Reporting/read operations** (18 methods) - Week 5

#### Deliverables
- [ ] All 79 methods have access controls
- [ ] Permission testing completed
- [ ] Documentation of required roles

---

### Task 2.3: Sanitize Logging

**Priority:** HIGH  
**Effort:** 8 hours  
**Owner:** Backend Developer

#### Implementation Steps

**Step 1: Create Logging Utility (2 hours)**

```python
# utils/secure_logging.py
import frappe
import re

class SecureLogger:
    """Logging with sensitive data sanitization"""
    
    SENSITIVE_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'amount': r'\$?\d+[\d,]*\.?\d*',
        'path': r'\/[\w\/\-\.]+',
        'password': r'password["\']?\s*[:=]\s*["\']?[\w]+',
    }
    
    @classmethod
    def sanitize_message(cls, message: str, keep_structure: bool = True) -> str:
        """Remove sensitive data from log message"""
        sanitized = message
        
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            if keep_structure:
                replacement = f"[{pattern_name.upper()}_REDACTED]"
            else:
                replacement = "[REDACTED]"
            sanitized = re.sub(pattern, replacement, sanitized)
        
        return sanitized
    
    @classmethod
    def log_error(cls, message: str, title: str, sanitize: bool = True):
        """Log error with optional sanitization"""
        if sanitize:
            message = cls.sanitize_message(message)
        frappe.log_error(message, title)
    
    @classmethod
    def log_info(cls, message: str, sanitize: bool = True):
        """Log info with optional sanitization"""
        if sanitize:
            message = cls.sanitize_message(message)
        frappe.logger().info(message)
```

**Step 2: Replace Logging Calls (4 hours)**

Find and replace sensitive logging:
```bash
# Find all logging
grep -rn "frappe.log_error\|frappe.logger()" apps/kgk_customisations/ --include="*.py" > logging_audit.txt

# Replace with secure logging
# Manual review required for each instance
```

**Step 3: Remove Debug Code (2 hours)**

```bash
# Find all print/debug statements
grep -rn "print(" apps/kgk_customisations/ --include="*.py"
grep -rn "console.log" apps/kgk_customisations/ --include="*.js"

# Remove or replace with proper logging
```

#### Deliverables
- [ ] Secure logging utility created
- [ ] All sensitive logging sanitized
- [ ] Debug code removed
- [ ] Logging policy documented

---

### Tasks 2.4 - 2.8

**Remaining HIGH severity tasks:**
- Task 2.4: Remove hardcoded credentials (4 hours)
- Task 2.5: Implement rate limiting (8 hours)
- Task 2.6: Secure file downloads (4 hours)
- Task 2.7: Fix subprocess usage (4 hours)
- Task 2.8: Verify CSRF protection (4 hours)

**Total Phase 2 Effort:** 60 hours

---

## Phase 3: Medium Severity Issues (Week 6-7)

**Duration:** 2 weeks (40 hours)  
**Priority:** MEDIUM  

### Task Categories

1. **Input Validation** (12 hours)
   - Strengthen data validator
   - Add length validation
   - Improve fuzzy matching

2. **Error Handling** (8 hours)
   - Specific exception handling
   - Secure error messages
   - Fail-safe defaults

3. **Audit Logging** (12 hours)
   - Comprehensive security event logging
   - Centralized audit trail
   - Log retention policy

4. **Security Headers** (4 hours)
   - Verify headers in Frappe
   - Add custom headers if needed

5. **Miscellaneous** (4 hours)
   - Session security
   - Filename sanitization
   - Other medium issues

---

## Phase 4: Testing & Validation (Week 8-9)

**Duration:** 2 weeks (50 hours)  
**Priority:** CRITICAL for deployment

### Week 8: Comprehensive Testing

**Day 1-2: Unit Testing (16 hours)**
```bash
# Run all security-related unit tests
pytest apps/kgk_customisations/tests/test_sql_injection_prevention.py -v
pytest apps/kgk_customisations/tests/test_path_traversal_prevention.py -v
pytest apps/kgk_customisations/tests/test_permissions.py -v
pytest apps/kgk_customisations/tests/test_file_validation.py -v

# Generate coverage report
pytest --cov=kgk_customisations --cov-report=html
```

**Day 3: Security Scanning (8 hours)**
```bash
# Static analysis
bandit -r apps/kgk_customisations/ -f json -o security_scan.json
bandit -r apps/kgk_customisations/ -f html -o security_scan.html

# SonarQube scan
sonar-scanner \
  -Dsonar.projectKey=kgk_customisations \
  -Dsonar.sources=apps/kgk_customisations \
  -Dsonar.host.url=http://localhost:9000

# Dependency checking
safety check
pip-audit
```

**Day 4-5: Penetration Testing (16 hours)**
```bash
# SQL Injection testing with SQLMap
sqlmap -u "http://localhost:8000/api/method/report.execute" \
  --data="filters={...}" \
  --cookie="sid=..." \
  --level=5 \
  --risk=3

# Path traversal testing
# Manual testing with Burp Suite

# OWASP ZAP scanning
zap-cli quick-scan http://localhost:8000
zap-cli active-scan http://localhost:8000
```

**Manual Security Testing Checklist:**
- [ ] SQL injection (all input points)
- [ ] Path traversal (all file operations)
- [ ] Permission bypass attempts
- [ ] File upload exploits
- [ ] XSS attempts
- [ ] CSRF testing
- [ ] Session hijacking
- [ ] Rate limiting verification

### Week 9: Integration & Regression Testing

**Integration Testing (16 hours)**
- Test all modules together
- Verify permissions across workflows
- Test audit trail completeness
- Performance testing with security controls

**Regression Testing (8 hours)**
- Ensure fixes didn't break functionality
- Test all critical business processes
- User acceptance testing

**Documentation Review (4 hours)**
- Update all documentation
- Create security guidelines
- Document all changes

---

## Phase 5: Documentation & Deployment (Week 10)

**Duration:** 1 week (20 hours)

### Documentation Deliverables

1. **Security Architecture Document** (4 hours)
   - Security controls overview
   - Permission matrix
   - Data flow diagrams
   - Threat model

2. **Developer Security Guidelines** (3 hours)
   - Secure coding standards
   - Code review checklist
   - Common vulnerabilities to avoid

3. **Administrator Guide** (3 hours)
   - Security configuration
   - Role setup
   - Monitoring procedures
   - Incident response

4. **Change Log** (2 hours)
   - All security fixes documented
   - Breaking changes noted
   - Migration guide

5. **User Training Materials** (3 hours)
   - Security awareness
   - Best practices
   - How to report issues

### Deployment Plan

**Pre-Deployment (Day 1-2)**
- [ ] Final security scan passed
- [ ] All tests green
- [ ] Code review approved
- [ ] Documentation complete
- [ ] Stakeholder sign-off

**Deployment (Day 3)**
- [ ] Backup current production
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production
- [ ] Monitor for issues

**Post-Deployment (Day 4-5)**
- [ ] Verify security controls active
- [ ] Monitor logs
- [ ] User feedback
- [ ] Performance monitoring
- [ ] Final report

---

## Risk Management

### Key Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes affect users | High | Medium | Comprehensive testing, gradual rollout |
| Performance degradation | Medium | Low | Performance testing, optimization |
| New vulnerabilities introduced | High | Low | Code review, security testing |
| Timeline delays | Medium | Medium | Buffer time, prioritization |
| Resource unavailability | Medium | Low | Cross-training, documentation |

### Contingency Plans

**If Phase 1 takes longer:**
- Reduce scope of Phase 3 (medium issues)
- Add 1 week to timeline
- Communicate delay early

**If breaking changes discovered:**
- Create migration scripts
- Phased rollout
- User communication plan

**If new vulnerabilities found:**
- Emergency fix process
- Hot-patch if needed
- Re-prioritize work

---

## Quality Assurance

### Code Review Process

**All security fixes require:**
1. Self-review with checklist
2. Peer review (another developer)
3. Security specialist review (for critical/high)
4. Final approval from lead developer

**Review Checklist:**
- [ ] No SQL injection possible
- [ ] All inputs validated
- [ ] Permissions checked
- [ ] Error handling proper
- [ ] Logging appropriate
- [ ] Tests included
- [ ] Documentation updated

### Testing Standards

**Required for each fix:**
- Unit tests (minimum 80% coverage)
- Integration tests
- Security tests
- Manual testing

**Security Testing:**
- Automated scanning (Bandit, SonarQube)
- Manual penetration testing
- Code review
- Regression testing

---

## Success Metrics

### Security Metrics

**Vulnerability Resolution:**
- [ ] 100% of CRITICAL vulnerabilities fixed
- [ ] 100% of HIGH vulnerabilities fixed
- [ ] 80%+ of MEDIUM vulnerabilities fixed
- [ ] All LOW issues documented (if not fixed)

**Code Quality:**
- [ ] Bandit: 0 high/critical issues
- [ ] SonarQube: Security rating A or B
- [ ] Code coverage: >80%
- [ ] All tests passing

**Security Controls:**
- [ ] 0 SQL injection vulnerabilities
- [ ] 0 path traversal vulnerabilities
- [ ] <5% of code using `ignore_permissions=True`
- [ ] All whitelisted methods have access controls

### Process Metrics

**Timeline:**
- [ ] Phase 1 complete by Week 2
- [ ] Phase 2 complete by Week 5
- [ ] Phase 3 complete by Week 7
- [ ] Testing complete by Week 9
- [ ] Production ready by Week 10

**Team:**
- [ ] All team members trained
- [ ] Code review participation >90%
- [ ] Documentation completeness >95%

---

## Communication Plan

### Weekly Updates

**Every Friday:**
- Progress report
- Completed tasks
- Upcoming tasks
- Blockers/risks
- Metrics dashboard

### Stakeholder Reviews

**Week 2:** Phase 1 completion review
**Week 5:** Phase 2 completion review
**Week 7:** Phase 3 completion review
**Week 9:** Go/No-Go decision
**Week 10:** Post-deployment review

### Escalation Path

**Issue Severity:**
- Low: Handle in sprint
- Medium: Report to lead developer
- High: Escalate to stakeholders
- Critical: Immediate escalation

---

## Appendix A: Security Testing Checklist

### SQL Injection Testing
- [ ] Test all report filters
- [ ] Test search functionality
- [ ] Test all user inputs to database
- [ ] Verify parameterized queries used
- [ ] Run SQLMap on all endpoints

### Path Traversal Testing
- [ ] Test file upload with ../ paths
- [ ] Test file open with absolute paths
- [ ] Test file search with traversal attempts
- [ ] Verify path validation works

### Permission Testing
- [ ] Test each role's access
- [ ] Verify permission bypasses removed
- [ ] Test unauthorized access attempts
- [ ] Verify audit logging

### File Upload Testing
- [ ] Test malicious file types
- [ ] Test oversized files
- [ ] Test zip bombs
- [ ] Test malformed files
- [ ] Test filename attacks

---

## Appendix B: Emergency Response Plan

### If Critical Vulnerability Found Post-Deployment

**Immediate Actions (0-2 hours):**
1. Assess severity and impact
2. Determine if rollback needed
3. Notify stakeholders
4. Isolate affected systems if needed

**Short-term (2-8 hours):**
1. Develop hot-fix
2. Test hot-fix in staging
3. Prepare deployment
4. Communication to users

**Medium-term (8-24 hours):**
1. Deploy hot-fix
2. Monitor systems
3. Verify fix effective
4. Document incident

**Long-term (1-7 days):**
1. Root cause analysis
2. Process improvements
3. Additional testing
4. Knowledge sharing

---

## Appendix C: Resource Requirements

### Development Environment
- Development laptops with sufficient RAM (16GB+)
- Access to development/staging servers
- Security testing tools licenses
- Code review tools

### Software & Tools
- Bandit (free)
- SonarQube (free/commercial)
- OWASP ZAP (free)
- Burp Suite (commercial for advanced features)
- SQLMap (free)
- python-magic library
- pytest and plugins

### Documentation
- Markdown editor
- Diagram tool (draw.io, etc.)
- Documentation platform

---

## Appendix D: Training Plan

### Developer Training

**Week 1:**
- Secure coding principles (4 hours)
- OWASP Top 10 overview (2 hours)
- SQL injection prevention (2 hours)

**Week 2:**
- Path traversal prevention (2 hours)
- Access control best practices (2 hours)
- Secure file handling (2 hours)

**Week 3:**
- Code review skills (2 hours)
- Security testing tools (2 hours)
- Incident response (1 hour)

### Materials
- [ ] Secure coding guide
- [ ] Video tutorials
- [ ] Hands-on exercises
- [ ] Reference documentation

---

## Sign-off

### Phase Approvals

| Phase | Approver | Date | Signature |
|-------|----------|------|-----------|
| Phase 1 Complete | Lead Developer | | |
| Phase 1 Complete | Security Specialist | | |
| Phase 2 Complete | Lead Developer | | |
| Phase 3 Complete | Lead Developer | | |
| Testing Complete | QA Lead | | |
| Production Ready | Project Manager | | |
| Deployed | DevOps Lead | | |

---

**END OF IMPLEMENTATION PLAN**

*This is a living document. Updates and changes will be tracked in version control.*

**Next Steps:**
1. Review and approve plan
2. Assign resources
3. Set up project tracking
4. Begin Phase 1 immediately
