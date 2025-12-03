# Cash Management System - Data Migration Guide

## Overview
This guide covers migrating data from Django Cash Management System to Frappe ERPNext.

## Migration Components

### 1. Django to Frappe Migration (`django_to_frappe.py`)
Migrates Documents, Cash Balances, and Bank Entries from Django to Frappe.

#### Usage:
```bash
# Full migration (dry run first)
python django_to_frappe.py --site kgkerp.local --dry-run --type all

# Migrate only documents
python django_to_frappe.py --site kgkerp.local --type documents --limit 1000

# Migrate balances
python django_to_frappe.py --site kgkerp.local --type balances

# Migrate bank entries
python django_to_frappe.py --site kgkerp.local --type bank
```

#### Field Mapping:
- Django `unique_number` → Frappe `migration_reference`
- Django `main_type` → Frappe `main_document_type`
- Django `sub_type` → Frappe `sub_document_type`
- Django `file_name` → Frappe `primary_document_file`
- Django `status` → Frappe `status` (pending→Pending Review, final→Approved, etc.)

### 2. Bulk Import (`bulk_import.py`)
Import cash documents from CSV/Excel files.

#### Download Template:
```python
import frappe
from kgk_customisations.kgk_customisations.utils.bulk_import import CashDocumentBulkImport

# Generate template
template = CashDocumentBulkImport.get_import_template()
with open('import_template.csv', 'w') as f:
    f.write(template)
```

#### Import from File:
```python
importer = CashDocumentBulkImport()

# Validate first
results = importer.import_from_file('data.csv', validate_only=True)
print(f"Valid: {results['success']}, Invalid: {results['failed']}")

# Import if validation passed
if results['failed'] == 0:
    results = importer.import_from_file('data.csv', validate_only=False)
```

#### Via Frappe Desk:
1. Go to Cash Document list
2. Click Menu → Import
3. Download template
4. Fill data and upload
5. Validate and Import

### 3. Data Validation (`data_validator.py`)
Validates and cleans import data.

#### Validation Checks:
- Company exists in system
- Date format and range (not future, not before 2000)
- Amount is positive number
- Document type is valid (Receipt/Payment/Invoice/Petty Cash)
- Phone number format
- Party exists (if specified)

#### Usage:
```python
from kgk_customisations.kgk_customisations.utils.data_validator import DataValidator

record = {
    "company": "KGK",
    "transaction_date": "2025-01-15",
    "amount": 5000,
    "main_document_type": "Receipt"
}

result = DataValidator.validate_record(record)

if result["is_valid"]:
    # Use cleaned_data
    clean_data = result["cleaned_data"]
else:
    print("Errors:", result["errors"])
    print("Warnings:", result["warnings"])
```

### 4. Rollback Mechanism (`rollback.py`)
Safely rollback failed migrations.

#### Usage:
```bash
# Dry run first
python rollback.py --site kgkerp.local --log-file migration_log.json --dry-run --type all

# Rollback documents only
python rollback.py --site kgkerp.local --log-file migration_log.json --type documents

# Full rollback
python rollback.py --site kgkerp.local --log-file migration_log.json --type all
```

#### Features:
- Creates backup before rollback
- Uses migration log to identify documents
- Supports partial rollback (documents/balances/bank)
- Exports rollback log for audit

## Migration Workflow

### Pre-Migration Checklist
1. ✅ Backup Django database
2. ✅ Backup Frappe site: `bench --site kgkerp.local backup`
3. ✅ Test migration on staging environment
4. ✅ Verify all companies exist in Frappe
5. ✅ Set up Cash Management Settings in Frappe

### Step-by-Step Migration

#### Phase 1: Dry Run
```bash
# Test migration without saving
python django_to_frappe.py --site kgkerp.local --dry-run --type all
```
Review output for errors and warnings.

#### Phase 2: Migrate Documents
```bash
# Migrate in batches
python django_to_frappe.py --site kgkerp.local --type documents --limit 1000

# Review results
# If successful, continue with remaining documents
python django_to_frappe.py --site kgkerp.local --type documents
```

#### Phase 3: Migrate Balances
```bash
python django_to_frappe.py --site kgkerp.local --type balances
```

#### Phase 4: Migrate Bank Entries
```bash
python django_to_frappe.py --site kgkerp.local --type bank
```

#### Phase 5: Verification
1. Check migration_log.json for summary
2. Verify document counts match
3. Check for any error_log entries
4. Test document workflows
5. Verify balance calculations

### Post-Migration Tasks

1. **Data Reconciliation**
   - Compare Django vs Frappe counts
   - Verify key documents manually
   - Check balance totals

2. **User Training**
   - Train users on Frappe interface
   - Document workflow changes
   - Provide quick reference guides

3. **Cleanup**
   - Archive Django system (don't delete yet)
   - Keep migration logs for reference
   - Document any data transformations

## Troubleshooting

### Common Issues

#### Issue: Company not found
**Solution**: Create companies in Frappe first or update company mapping in migration script.

#### Issue: Date format errors
**Solution**: Ensure dates are in YYYY-MM-DD format. Use data validator to clean dates.

#### Issue: Large dataset timeout
**Solution**: Use `--limit` parameter to migrate in batches.

#### Issue: Migration partially failed
**Solution**: 
1. Check error_log in migration_log.json
2. Fix Django data issues
3. Re-run migration (it skips already migrated documents)
4. Or use rollback and retry

### Rollback Scenario
If migration fails or data issues found:
```bash
# 1. Stop using the system
# 2. Rollback migration
python rollback.py --site kgkerp.local --log-file migration_log.json --type all

# 3. Fix issues in Django data
# 4. Re-run migration
```

## Performance Tips

1. **Batch Processing**: Use `--limit` for large datasets
2. **Parallel Migration**: Run documents, balances, and bank in parallel (different terminals)
3. **Database Optimization**: Ensure indexes are created (frappe migrate handles this)
4. **Network**: Run migration on server directly to avoid network latency

## Data Validation Rules

### Required Fields
- Company
- Transaction Date
- Main Document Type
- Amount

### Optional Fields
- Sub Document Type
- Party Type / Party
- Contact Person / Contact Number
- Invoice Number
- Description

### Automatic Cleanup
- Whitespace trimming
- Phone number formatting
- Text length limits
- Date parsing

## Support

For migration issues:
1. Check migration_log.json and error_log
2. Review this guide
3. Contact system administrator
4. Consult Frappe documentation: https://docs.erpnext.com

## Appendix

### Migration Log Structure
```json
{
  "migration_log": [
    {
      "django_id": "DOC-2025-001",
      "frappe_name": "CD-KGK-2025-01-00001",
      "timestamp": "2025-01-15 10:30:00"
    }
  ],
  "error_log": [
    {
      "django_id": "DOC-2025-002",
      "error": "Company not found",
      "timestamp": "2025-01-15 10:30:05"
    }
  ]
}
```

### CSV Import Template Columns
1. Company
2. Transaction Date (YYYY-MM-DD)
3. Main Document Type
4. Sub Document Type
5. Amount
6. Currency
7. Description
8. Party Type
9. Party
10. Contact Person
11. Contact Number
12. Primary Document File
13. Invoice Number (optional)
14. Status (optional)
