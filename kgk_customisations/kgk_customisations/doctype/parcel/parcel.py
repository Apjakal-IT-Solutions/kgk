# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
import pandas as pd
from frappe.utils import cstr, flt
import os
from frappe.utils.file_manager import get_file_path
import time

class Parcel(Document):
    pass

# Column mapping - EXACT match to Stone DocType field names
COLUMN_MAP = {
    # Basic identification (matches DocType exactly)
    "Parcel Name": "stone_name",
    "Barcode": "barcode",
    "Main barcode": "main_barcode",
    "Seria ID": "seria_id",
    "Sight": "sight",
    "Article": "article",
    "Lab": "lab",
    "R_Size": "r_size",
    "S_PART": "s_part",
    
    # Basic measurements (matches DocType exactly)
    "Org Wght": "org_weight",
    "Prop. Cts": "prop_cts",
    "EST AMT": "est_amt",
    
    # Expected (E) measurements (matches DocType exactly)
    "Wght E": "weight_e",
    "Shape E": "shape_e",
    "Color E": "color_e",
    "Clarity E": "clarity_e",
    "Cut E": "cut_e",
    "Polish E": "polish_e",
    "Sym. E": "sym_e",
    "Fluro. E": "fluro_e",
    "List E": "list_e",
    "ESP % ": "esp_percent_e",  # Note: trailing space, no E suffix
    "ESP @": "esp_at_e",        # Note: no trailing space, no E suffix
    
    # Lab (L) measurements (matches DocType exactly)
    "Wght L": "weight_l",
    "Shape L": "shape_l",
    "Color L": "color_l",
    "Clarity L": "clarity_l",
    "Cut L": "cut_l",
    "Polish L": "polish_l",
    "Sym. L": "sym_l",
    "Fluro. L": "fluro_l",
    "List L": "list_l",
    "ESP % L": "esp_percent_l",
    "ESP @ L": "esp_at_l",
    "ESP Amt. L": "esp_amount_l",
    
    # Internal Grading (IG) measurements (matches DocType exactly)
    "Wght IG": "weight_ig",
    "Shape IG": "shape_ig",  # Added - was missing
    "Color IG": "color_ig",
    "Clarity IG": "clarity_ig",
    "Cut IG": "cut_ig",
    "Polish IG": "polish_ig",
    "Sym. IG": "sym_ig",
    "Fluro. IG": "fluro_ig",
    "ESP % IG": "esp_percent_ig",
    "ESP @ IG": "esp_at_ig",
    "ESP Amt. IG": "esp_amount_ig",
    "List IG": "list_ig",
}

@frappe.whitelist()
def import_from_file(parcel_name: str, file_url: str):
    """
    Import stones from Excel file with proper hierarchy and data mapping
    """
    function_start = time.time()
    
    try:
        frappe.publish_progress(0, "Stone Import", "Starting import...")
        
        # Validate inputs
        if not parcel_name or not file_url:
            frappe.throw("Parcel name and file URL are required")
        
        # Get and validate file
        file_path = frappe.get_site_path(file_url.strip("/"))
        if not os.path.exists(file_path):
            frappe.throw(f"File not found: {file_path}")
        
        frappe.publish_progress(5, "Stone Import", "Reading Excel file...")
        
        # Read Excel
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        
        if df.empty:
            frappe.throw("No data found in Excel file")
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        
        # EXCEL COLUMN ANALYSIS FOR DEBUGGING
        print("=" * 60)
        print("EXCEL COLUMN ANALYSIS")
        print(f"Total columns found: {len(df.columns)}")
        print("All columns with mapping status:")
        for i, col in enumerate(df.columns):
            mapped_field = COLUMN_MAP.get(col, "NOT_MAPPED")
            print(f"  {i+1:2d}. '{col}' -> {mapped_field}")
        
        # Check for barcode columns specifically
        barcode_cols = [col for col in df.columns if 'barcode' in col.lower()]
        main_barcode_cols = [col for col in df.columns if 'main' in col.lower() and 'barcode' in col.lower()]
        print(f"\nBarcode-related columns: {barcode_cols}")
        print(f"Main barcode columns: {main_barcode_cols}")
        
        # Check ESP columns
        esp_cols = [col for col in df.columns if 'ESP' in col]
        print(f"ESP columns: {esp_cols}")
        
        # SAMPLE DATA ANALYSIS - Show first 3 rows of barcode columns
        print("\nSAMPLE BARCODE DATA (first 3 rows):")
        for col in df.columns:
            if 'barcode' in col.lower():
                sample_values = df[col].head(3).tolist()
                print(f"  '{col}': {sample_values}")
        
        # CRITICAL VALIDATION: Check level distribution in Excel
        stone_name_col_temp = _find_name_column(df.columns)
        if stone_name_col_temp:
            level_counts = {}
            for idx, row in df.iterrows():
                stone_name_raw = row[stone_name_col_temp]
                if pd.isna(stone_name_raw):
                    continue
                stone_name = str(stone_name_raw).strip()
                level = stone_name.count("/")
                level_counts[level] = level_counts.get(level, 0) + 1
            
            print("\nEXCEL LEVEL DISTRIBUTION:")
            for level in sorted(level_counts.keys()):
                print(f"  Level {level}: {level_counts[level]} stones")
        
        print("=" * 60)
        
        frappe.publish_progress(10, "Stone Import", "Finding stone name column...")
        
        # Find stone name column
        stone_name_col = _find_name_column(df.columns)
        if not stone_name_col:
            frappe.throw(f"Could not find stone name column. Available: {list(df.columns)}")
        
        # Remove empty rows
        df = df.dropna(how='all').reset_index(drop=True)
        total_rows = len(df)
        
        frappe.publish_progress(15, "Stone Import", f"Processing {total_rows} rows...")
        
        # CRITICAL: Validate Excel data before processing
        validation_errors = _validate_excel_data(df, stone_name_col)
        if validation_errors:
            error_summary = f"Excel data validation failed with {len(validation_errors)} errors:"
            for i, error in enumerate(validation_errors[:5]):  # Show first 5 errors
                error_summary += f"\n{i+1}. {error}"
            if len(validation_errors) > 5:
                error_summary += f"\n... and {len(validation_errors) - 5} more errors"
            frappe.throw(error_summary)
        
        # Build hierarchy map
        hierarchy_map = _build_hierarchy_map(df, stone_name_col)
        
        frappe.publish_progress(20, "Stone Import", "Creating stones in hierarchical order...")
        
        # Create stones hierarchically
        result = _create_stones_hierarchically(df, stone_name_col, parcel_name, hierarchy_map)
        
        frappe.publish_progress(100, "Stone Import", "Import completed!")
        frappe.db.commit()
        
        message = f"Import completed! Created/Updated {result['processed']} stones"
        if result['errors'] > 0:
            message += f". {result['errors']} errors occurred (check Error Log)"
        
        frappe.msgprint(message)
        
        return {
            "status": "success",
            "message": message,
            "processed": result['processed'],
            "errors": result['errors'],
            "total_rows": total_rows,
            "execution_time": time.time() - function_start
        }
        
    except Exception as e:
        error_msg = f"Import failed: {str(e)}"
        frappe.log_error(frappe.get_traceback(), "Stone Import Error")
        frappe.throw(error_msg)


def _find_name_column(columns):
    """Find the stone name column"""
    possible = ["Parcel Name", "ParcelName", "Stone Name", "StoneName", "Name"]
    
    for col in possible:
        if col in columns:
            return col
    
    # Case insensitive fallback
    for col in columns:
        if any(p.lower() in col.lower() for p in ["parcel", "stone", "name"]):
            return col
    
    return None


def _validate_excel_data(df, stone_name_col):
    """Validate Excel data to catch potential issues early"""
    errors = []
    
    print("=== EXCEL DATA VALIDATION ===")
    
    for idx, row in df.iterrows():
        stone_name_raw = row[stone_name_col]
        
        # Check for completely missing stone names
        if pd.isna(stone_name_raw):
            errors.append(f"Row {idx+2}: Stone name is missing (NaN)")
            continue
        
        stone_name = str(stone_name_raw).strip()
        
        # Check for empty or invalid stone names
        if not stone_name:
            errors.append(f"Row {idx+2}: Stone name is empty")
            continue
            
        if stone_name.lower() in ['none', 'null', 'nan']:
            errors.append(f"Row {idx+2}: Stone name is invalid: '{stone_name}'")
            continue
            
        # Check for problematic characters that might cause issues
        if stone_name == "None":
            errors.append(f"Row {idx+2}: Stone name is literally 'None': '{stone_name}'")
            continue
            
        # Validate parent stone extraction if this is a hierarchical name
        if "/" in stone_name:
            parent = _get_parent_stone(stone_name)
            if not parent:
                errors.append(f"Row {idx+2}: Could not extract valid parent from stone name: '{stone_name}'")
                continue
    
    if errors:
        print(f"Found {len(errors)} validation errors")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
    else:
        print("Excel data validation passed - no critical errors found")
    
    return errors


def _build_hierarchy_map(df, stone_name_col):
    """Build a map of all stones INCLUDING auto-generated parents needed for hierarchy"""
    hierarchy = {}
    all_parents = set()
    stones_found_in_excel = 0
    
    # STEP 1: Add all stones that exist in Excel
    for idx, row in df.iterrows():
        stone_name_raw = row[stone_name_col]
        
        if pd.isna(stone_name_raw):
            print(f"SKIP: Row {idx} has NaN stone name")
            continue
        
        stone_name = str(stone_name_raw).strip()
        if not stone_name or stone_name.lower() in ['none', 'null', 'nan']:
            print(f"SKIP: Row {idx} has invalid stone name: '{stone_name}'")
            continue
        
        stones_found_in_excel += 1
        parent = _get_parent_stone(stone_name)
        level = stone_name.count("/")
        
        hierarchy[stone_name] = {
            "level": level,
            "parent": parent,
            "row_idx": idx,
            "has_data": True
        }
        
        # Track all parent references
        if parent:
            all_parents.add(parent)
        
        if stones_found_in_excel <= 3:  # Debug first 3 stones
            print(f"HIERARCHY DEBUG: Stone '{stone_name}' -> row {idx}, level {level}, parent '{parent}', has_data=True")
    
    # STEP 2: Add missing parent stones (they need to exist for tree structure)
    parents_to_add = set()
    for parent in all_parents:
        if parent not in hierarchy:
            # VALIDATION: Ensure parent name is valid before adding
            if not parent or parent == "None" or parent.lower() in ['none', 'null', 'nan', '']:
                print(f"ERROR: Skipping invalid parent stone name: '{parent}'")
                continue
                
            # Walk up the entire parent chain
            current = parent
            while current:
                # VALIDATION: Ensure current name is valid
                if not current or current == "None" or current.lower() in ['none', 'null', 'nan', '']:
                    print(f"ERROR: Stopping parent chain walk due to invalid name: '{current}'")
                    break
                    
                if current not in hierarchy:
                    parents_to_add.add(current)
                current = _get_parent_stone(current)
    
    # Add all missing parents with validation
    for parent_stone in parents_to_add:
        # VALIDATION: Double-check parent stone name is valid
        if not parent_stone or parent_stone == "None" or parent_stone.lower() in ['none', 'null', 'nan', '']:
            print(f"ERROR: Skipping addition of invalid parent stone: '{parent_stone}'")
            continue
            
        level = parent_stone.count("/")
        grandparent = _get_parent_stone(parent_stone)
        
        hierarchy[parent_stone] = {
            "level": level,
            "parent": grandparent,
            "row_idx": None,
            "has_data": False
        }
        print(f"HIERARCHY: Auto-generating parent stone '{parent_stone}' at level {level}")
    
    print(f"HIERARCHY BUILD FINAL:")
    print(f"  - {stones_found_in_excel} stones from Excel")
    print(f"  - {len(parents_to_add)} auto-generated parent stones")
    print(f"  - {len(hierarchy)} total stones in hierarchy")
    
    return hierarchy


def _create_stones_hierarchically(df, stone_name_col, parcel_name, hierarchy_map):
    """Create stones level by level with enhanced barcode tracking and recovery"""
    processed = 0
    errors = 0
    barcode_recovery_needed = []
    
    # Create Excel data cache for barcode recovery
    excel_data_cache = {}
    for idx, row in df.iterrows():
        stone_name_raw = row[stone_name_col]
        if pd.isna(stone_name_raw):
            continue
        stone_name = str(stone_name_raw).strip()
        excel_data_cache[stone_name] = row.to_dict()
    
    print(f"Created Excel cache with {len(excel_data_cache)} entries for barcode recovery")
    
    # Sort by level
    sorted_stones = sorted(hierarchy_map.items(), key=lambda x: x[1]["level"])
    total = len(sorted_stones)
    
    print(f"Starting hierarchical creation of {total} stones")
    
    for i, (stone_name, info) in enumerate(sorted_stones):
        try:
            # CRITICAL: Validate stone name is not None or empty
            if not stone_name or stone_name == "None" or stone_name.lower() in ['none', 'null', 'nan', '']:
                print(f"ERROR: Invalid stone name detected at position {i}: '{stone_name}' - SKIPPING")
                errors += 1
                continue
                
            # Update progress
            if i % 50 == 0:
                progress = 20 + ((i / total) * 75)
                frappe.publish_progress(
                    progress,
                    "Stone Import",
                    f"Creating stone {i+1}/{total}: {stone_name[:40]}..."
                )
            
            # Skip if exists
            if frappe.db.exists("Stone", stone_name):
                processed += 1
                if i < 3:
                    print(f"Stone {i+1} already exists: {stone_name}")
                continue
            
            # CRITICAL DEBUG: Check stone data source
            print(f"\n=== STONE CREATION DEBUG {i+1}: {stone_name} ===")
            print(f"  has_data flag: {info['has_data']}")
            print(f"  row_idx: {info['row_idx']}")
            print(f"  parent: {info['parent']}")
            print(f"  level: {info['level']}")
            
            # Prepare stone data with enhanced barcode tracking
            barcode_extracted = False
            main_barcode_extracted = False
            barcode_extraction_details = {}
            
            if info["has_data"] and info["row_idx"] is not None:
                # Has Excel data
                row = df.iloc[info["row_idx"]]
                print(f"  Excel row data available: YES")
                print(f"  Row index in DataFrame: {info['row_idx']}")
                print(f"  Stone name in Excel: '{row[stone_name_col]}'")
                
                stone_data, barcode_extracted, main_barcode_extracted, barcode_extraction_details = _extract_stone_data(
                    row, stone_name, parcel_name, info["parent"], info["level"]
                )
                
                # Count actual populated fields
                populated_fields = {k: v for k, v in stone_data.items() if v not in [None, 0, '', 'POLISHED', 'Stone', stone_name, parcel_name, info["parent"], info["level"], 0]}
                print(f"  Fields populated from Excel: {len(populated_fields)}")
                if populated_fields:
                    print(f"  Sample populated fields: {dict(list(populated_fields.items())[:5])}")
                else:
                    print(f"  WARNING: NO FIELDS POPULATED FROM EXCEL!")
                    print(f"  Raw Excel data sample:")
                    for col in list(row.index)[:10]:  # Show first 10 columns
                        print(f"    '{col}': '{row[col]}'")
                        
            else:
                # Parent stone without data
                print(f"  Excel row data available: NO (creating minimal parent)")
                stone_data = _create_minimal_stone_data(stone_name, parcel_name, info["parent"], info["level"])
                barcode_extracted = True  # Minimal stones don't need barcodes from Excel
                main_barcode_extracted = True
            
            # Create stone
            stone_doc = frappe.get_doc(stone_data)
            stone_doc.insert(ignore_permissions=True, ignore_mandatory=True)
            processed += 1
            
            # Track barcode extraction failures for recovery
            if info["has_data"] and not barcode_extracted:
                recovery_entry = {
                    "stone_name": stone_name,
                    "excel_data": excel_data_cache.get(stone_name),
                    "extraction_details": barcode_extraction_details,
                    "row_idx": info["row_idx"]
                }
                barcode_recovery_needed.append(recovery_entry)
                print(f"  BARCODE RECOVERY NEEDED: Added {stone_name} to recovery list")
            
            # Verify first stone was saved correctly
            if i < 3:
                saved_stone = frappe.get_doc("Stone", stone_name)
                print(f"Verification after save:")
                print(f"  org_weight: {saved_stone.org_weight}")
                print(f"  main_barcode: {saved_stone.main_barcode or 'EMPTY'}")
                print(f"  barcode: {saved_stone.barcode or 'EMPTY'}")
                print(f"  weight_e: {saved_stone.weight_e}")
                print(f"  weight_l: {saved_stone.weight_l}")
                print(f"=== End Debug ===\n")
            
            # Periodic commit
            if i % 100 == 0:
                frappe.db.commit()
                time.sleep(0.02)
            
        except Exception as e:
            errors += 1
            error_msg = str(e)[:200]
            print(f"Error creating stone {stone_name}: {error_msg}")
            frappe.log_error(f"Error creating stone {stone_name}: {str(e)}", "Stone Creation Error")
            continue
    
    # Post-creation barcode recovery
    recovery_results = {"recovered": 0, "failed": 0}
    if barcode_recovery_needed:
        print(f"\n=== STARTING BARCODE RECOVERY ===")
        print(f"Attempting to recover barcodes for {len(barcode_recovery_needed)} stones")
        recovery_results = _recover_barcodes_from_cache(barcode_recovery_needed)
        print(f"Barcode recovery completed: {recovery_results['recovered']}/{len(barcode_recovery_needed)} recovered")
    
    print(f"Hierarchical creation complete: {processed} processed, {errors} errors")
    return {
        "processed": processed, 
        "errors": errors, 
        "barcode_recoveries": len(barcode_recovery_needed),
        "barcode_recovery_results": recovery_results
    }


def _extract_stone_data(row, stone_name, parcel_name, parent_stone, level):
    """Extract all stone data from Excel row using centralized column map with enhanced barcode validation"""
    
    # CRITICAL VALIDATION: Ensure stone_name is valid
    if not stone_name or stone_name == "None" or stone_name.lower() in ['none', 'null', 'nan', '']:
        raise ValueError(f"Invalid stone name provided: '{stone_name}' - cannot create stone with empty or None name")
    
    stone_data = {
        "doctype": "Stone",
        "stone_name": stone_name,
        "parcel": parcel_name,
        "parcel_name": stone_name,  # Set parcel_name to stone_name as per DocType
        "parent_stone": parent_stone,
        "level": level,
        "stone_type": "POLISHED",  # Default
        "is_group": 0  # Default to not a group
    }
    
    # Track if critical fields are missing
    missing_critical = []
    fields_processed = 0
    fields_populated = 0
    
    # ENHANCED BARCODE TRACKING
    barcode_extracted = False
    main_barcode_extracted = False
    barcode_extraction_details = {
        "barcode_status": "not_found",
        "main_barcode_status": "not_found",
        "fallback_used": False,
        "extraction_errors": []
    }
        
    # PHASE 1: Enhanced barcode extraction with validation
    for excel_col, field_name in COLUMN_MAP.items():
        if field_name not in ['barcode', 'main_barcode']:
            continue
            
        if excel_col not in row.index:
            barcode_extraction_details["extraction_errors"].append(f"Column '{excel_col}' not found for {field_name}")
            continue
        
        value = row[excel_col]
        
        # Enhanced barcode debugging
        print(f"ENHANCED BARCODE DEBUG {stone_name}: Field={field_name}, Excel_Col='{excel_col}', Raw_Value='{value}', Type={type(value)}, IsNA={pd.isna(value)}")
        
        if pd.isna(value):
            barcode_extraction_details["extraction_errors"].append(f"{field_name} is NaN/None")
            continue
        
        # Convert to string and validate
        str_val = str(value).strip()
        
        # Enhanced validation for barcode formats
        if not str_val or str_val.lower() in ['none', 'null', 'nan', '']:
            barcode_extraction_details["extraction_errors"].append(f"{field_name} is empty or invalid: '{str_val}'")
            continue
        
        # Check for numeric barcode (most common format)
        if str_val.replace('.', '').replace('-', '').replace('_', '').isdigit():
            # Clean up numeric barcodes - remove decimal points for integer barcodes
            if '.' in str_val and str_val.endswith('.0'):
                str_val = str_val[:-2]
            
            stone_data[field_name] = str_val
            
            if field_name == 'barcode':
                barcode_extracted = True
                barcode_extraction_details["barcode_status"] = "extracted"
                print(f"SUCCESS: Extracted barcode '{str_val}' for {stone_name}")
            else:
                main_barcode_extracted = True
                barcode_extraction_details["main_barcode_status"] = "extracted"
                print(f"SUCCESS: Extracted main_barcode '{str_val}' for {stone_name}")
        
        elif len(str_val) >= 3:  # Accept non-numeric barcodes if reasonable length
            stone_data[field_name] = str_val
            
            if field_name == 'barcode':
                barcode_extracted = True
                barcode_extraction_details["barcode_status"] = "extracted_non_numeric"
            else:
                main_barcode_extracted = True
                barcode_extraction_details["main_barcode_status"] = "extracted_non_numeric"
                
            print(f"SUCCESS: Extracted non-numeric {field_name} '{str_val}' for {stone_name}")
        else:
            barcode_extraction_details["extraction_errors"].append(f"{field_name} too short or invalid format: '{str_val}'")
    
    # FALLBACK BARCODE EXTRACTION if primary extraction failed
    if not barcode_extracted:
        print(f"CRITICAL: Primary barcode extraction failed for {stone_name}")
        print(f"Available columns: {list(row.index)}")
        
        # Try alternative column names
        alternative_barcode_cols = ['barcode', 'Barcode', 'BARCODE', 'Bar Code', 'Stone Barcode', 'Code']
        for alt_col in alternative_barcode_cols:
            if alt_col in row.index and not pd.isna(row[alt_col]):
                fallback_val = str(row[alt_col]).strip()
                if fallback_val and fallback_val.lower() not in ['none', 'null', 'nan', ''] and len(fallback_val) >= 3:
                    # Clean numeric barcodes
                    if '.' in fallback_val and fallback_val.endswith('.0'):
                        fallback_val = fallback_val[:-2]
                    
                    stone_data['barcode'] = fallback_val
                    barcode_extracted = True
                    barcode_extraction_details["barcode_status"] = "fallback_extracted"
                    barcode_extraction_details["fallback_used"] = True
                    print(f"FALLBACK SUCCESS: Used alternative column '{alt_col}' for barcode: '{fallback_val}'")
                    break
    
    # PHASE 2: Process all other fields using existing logic
    for excel_col, field_name in COLUMN_MAP.items():
        if field_name in ['barcode', 'main_barcode']:
            continue  # Already processed in Phase 1
            
        fields_processed += 1
        if excel_col not in row.index:
            continue
        
        value = row[excel_col]
        
        if pd.isna(value):
            continue
        
        # Type conversion based on field patterns and DocType field types
        if field_name in ['org_weight', 'prop_cts', 'weight_e', 'weight_l', 'weight_ig']:
            # Float fields with 3 decimal precision
            converted_value = flt(value, 3)
            if converted_value != 0:  # Only set if non-zero
                stone_data[field_name] = converted_value
                fields_populated += 1
        elif field_name in ['est_amt', 'list_e', 'esp_at_e', 'list_l', 'esp_at_l', 
                           'esp_amount_l', 'list_ig', 'esp_at_ig', 'esp_amount_ig']:
            # Currency fields
            converted_value = flt(value)
            if converted_value != 0:  # Only set if non-zero
                stone_data[field_name] = converted_value
                fields_populated += 1
        elif field_name in ['esp_percent_e', 'esp_percent_l', 'esp_percent_ig']:
            # Percent fields - handle both decimal (0.15) and whole number (15) formats
            val = flt(value)
            # If value is > 1, assume it's in percentage format (e.g., 15%), convert to decimal
            stone_data[field_name] = val / 100 if val > 1 else val
            fields_populated += 1
        elif field_name == 'level':
            # Integer field
            stone_data[field_name] = int(value)
            fields_populated += 1
        else:
            # String/Data fields - explicit string conversion and validation
            str_val = cstr(value).strip()
            if str_val and str_val.lower() not in ['none', 'null', 'nan', '']:
                stone_data[field_name] = str_val
                fields_populated += 1
    
    # DATA EXTRACTION SUMMARY
    print(f"EXTRACTION SUMMARY {stone_name}:")
    print(f"  Processed {fields_processed} column mappings")
    print(f"  Successfully populated {fields_populated} fields")
    print(f"  Barcode extracted: {barcode_extracted}")
    print(f"  Main barcode extracted: {main_barcode_extracted}")
    
    # ENHANCED BARCODE INHERITANCE for main_barcode
    if not main_barcode_extracted:
        print(f"WARNING: Stone {stone_name} has no main_barcode from Excel data")
        
        # Strategy 1: Try to inherit from parent
        if parent_stone:
            try:
                parent_barcode = frappe.db.get_value("Stone", parent_stone, "main_barcode")
                if parent_barcode and parent_barcode.strip():
                    stone_data['main_barcode'] = parent_barcode
                    main_barcode_extracted = True
                    barcode_extraction_details["main_barcode_status"] = "inherited_from_parent"
                    print(f"SUCCESS: Inherited main_barcode '{parent_barcode}' from parent {parent_stone}")
            except:
                print(f"FAILED: Could not inherit main_barcode from parent {parent_stone}")
        
        # Strategy 2: Use regular barcode if main_barcode is missing
        if not main_barcode_extracted and barcode_extracted:
            stone_data['main_barcode'] = stone_data['barcode']
            main_barcode_extracted = True
            barcode_extraction_details["main_barcode_status"] = "copied_from_barcode"
            print(f"FALLBACK: Used barcode '{stone_data['barcode']}' as main_barcode")
        
        # Strategy 3: Extract from stone name as last resort
        if not main_barcode_extracted:
            import re
            barcode_match = re.search(r'\d{7,}', stone_name)  # 7+ digit numbers
            if barcode_match:
                extracted_barcode = barcode_match.group()
                stone_data['main_barcode'] = extracted_barcode
                main_barcode_extracted = True
                barcode_extraction_details["main_barcode_status"] = "extracted_from_name"
                print(f"EXTRACTED: Used barcode '{extracted_barcode}' from stone name pattern")
    
    # Critical analysis
    if fields_populated == 0:
        print(f"CRITICAL ERROR: NO FIELDS POPULATED for {stone_name}!")
        print(f"  First 10 Excel columns and values:")
        for i, col in enumerate(list(row.index)[:10]):
            print(f"    {i+1}. '{col}' = '{row[col]}' (mapped to: {COLUMN_MAP.get(col, 'NOT MAPPED')})")
    
    return stone_data, barcode_extracted, main_barcode_extracted, barcode_extraction_details


def _create_minimal_stone_data(stone_name, parcel_name, parent_stone, level):
    """Create minimal data for parent stones without Excel data"""
    
    # CRITICAL VALIDATION: Ensure stone_name is valid
    if not stone_name or stone_name == "None" or stone_name.lower() in ['none', 'null', 'nan', '']:
        raise ValueError(f"Invalid stone name provided: '{stone_name}' - cannot create stone with empty or None name")
    
    return {
        "doctype": "Stone",
        "stone_name": stone_name,
        "parcel": parcel_name,
        "parcel_name": stone_name,  # Set parcel_name to stone_name
        "parent_stone": parent_stone,
        "level": level,
        "stone_type": "ROUGH",  # Parent stones default to ROUGH
        "is_group": 1,  # Parent stones are groups
        "org_weight": 0.0,
        "prop_cts": 0.0
    }


def _get_parent_stone(stone_name):
    """Extract parent stone from name with validation"""
    if not stone_name or stone_name == "None" or stone_name.lower() in ['none', 'null', 'nan', ''] or "/" not in stone_name:
        return None
    
    parent = stone_name.rsplit("/", 1)[0]
    
    # Validate the extracted parent name
    if not parent or parent == "None" or parent.lower() in ['none', 'null', 'nan', '']:
        print(f"WARNING: Invalid parent extracted from '{stone_name}': '{parent}'")
        return None
        
    return parent


@frappe.whitelist()
def import_from_file_async(parcel_name: str, file_url: str):
    """Async import for large files with main_barcode inheritance fix"""
    frappe.enqueue(
        method="kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file",
        queue='long',
        timeout=7200,
        parcel_name=parcel_name,
        file_url=file_url,
        job_name=f"stone_import_{parcel_name}_{int(time.time())}",
        now=False  # Ensure proper queueing
    )
    
    return {
        "status": "queued",
        "message": f"Import queued for {parcel_name}. Check Background Jobs."
    }


@frappe.whitelist()
def backfill_codes_async(parcel_name: str):
    """Async backfill for missing main_barcodes and child_stones population"""
    frappe.enqueue(
        method="kgk_customisations.kgk_customisations.doctype.parcel.parcel.backfill_missing_main_barcodes",
        queue='long',
        timeout=28800,
        parcel_name=parcel_name,
        job_name=f"backfill_barcodes_{parcel_name}_{int(time.time())}",
        now=False
    )
    
    return {
        "status": "queued",
        "message": f"Backfill queued for {parcel_name}. Check Background Jobs."
    }

@frappe.whitelist()
def backfill_missing_main_barcodes(parcel_name: str):
    """
    Fix stones with missing main_barcodes by inheriting from parent or siblings
    AND populate the child_stones child table for all stones
    """
    try:
        # Get all stones for this parcel without main_barcode
        stones_without_barcode = frappe.get_all(
            "Stone",
            filters={
                "parcel": parcel_name,
                "main_barcode": ["in", [None, ""]]
            },
            fields=["name", "parent_stone", "stone_name"],
            order_by="level asc"
        )
        
        fixed_barcode_count = 0
        
        # PART 1: Fix missing barcodes
        for stone in stones_without_barcode:
            stone_name = stone.name
            parent_stone = stone.parent_stone
            
            main_barcode = None
            
            # Strategy 1: Get from parent
            if parent_stone:
                main_barcode = frappe.db.get_value("Stone", parent_stone, "main_barcode")
            
            # Strategy 2: Get from siblings (stones with same parent)
            if not main_barcode and parent_stone:
                sibling_barcode = frappe.db.get_value(
                    "Stone",
                    {
                        "parent_stone": parent_stone,
                        "main_barcode": ["!=", ""]
                    },
                    "main_barcode"
                )
                if sibling_barcode:
                    main_barcode = sibling_barcode
            
            # Strategy 3: Get from any child stone
            if not main_barcode:
                child_barcode = frappe.db.get_value(
                    "Stone",
                    {
                        "parent_stone": stone_name,
                        "main_barcode": ["!=", ""]
                    },
                    "main_barcode"
                )
                if child_barcode:
                    main_barcode = child_barcode
            
            # Update if found
            if main_barcode:
                frappe.db.set_value("Stone", stone_name, "main_barcode", main_barcode)
                fixed_barcode_count += 1
        
        frappe.db.commit()
        
        # PART 2: Populate child_stones child table for all stones in parcel
        child_table_populated_count = _populate_child_stones_table(parcel_name)
        
        message = f"Backfill complete: Fixed {fixed_barcode_count}/{len(stones_without_barcode)} barcodes. Populated child table for {child_table_populated_count} stones."
        frappe.msgprint(message)
        
        return {
            "status": "success",
            "message": message,
            "fixed_barcodes": fixed_barcode_count,
            "total_without_barcode": len(stones_without_barcode),
            "child_tables_populated": child_table_populated_count
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Barcode Backfill Error")
        frappe.throw(f"Backfill failed: {str(e)}")


def _populate_child_stones_table(parcel_name: str):
    """
    Populate the child_stones child table for all stones in a parcel
    """
    # Get all stones in this parcel
    all_stones = frappe.get_all(
        "Stone",
        filters={"parcel": parcel_name},
        fields=["name", "stone_name", "barcode", "main_barcode"],
        order_by="level asc"
    )
    
    populated_count = 0
    
    for stone in all_stones:
        stone_name = stone.name
        
        # Get all child stones (stones where parent_stone = this stone)
        child_stones = frappe.get_all(
            "Stone",
            filters={"parent_stone": stone_name},
            fields=["name", "stone_name", "barcode", "main_barcode"],
            order_by="stone_name asc"
        )
        
        # Skip if no children
        if not child_stones:
            continue
        
        # Get the stone document
        stone_doc = frappe.get_doc("Stone", stone_name)
        
        # Clear existing child_stones entries to avoid duplicates
        stone_doc.child_stones = []
        
        # Add each child stone to the child table
        for child in child_stones:
            stone_doc.append("child_stones", {
                "stone_name": child.name,
                "barcode": child.barcode or "",
                "main_barcode": child.main_barcode or ""
            })
        
        # Save the document
        stone_doc.save(ignore_permissions=True)
        populated_count += 1
        
        # Periodic commit for performance
        if populated_count % 50 == 0:
            frappe.db.commit()
    
    # Final commit
    frappe.db.commit()
    
    print(f"Populated child_stones table for {populated_count} parent stones")
    return populated_count


@frappe.whitelist()
def populate_child_stones_async(parcel_name: str):
    """Async populate child_stones table for all stones in parcel"""
    frappe.enqueue(
        method="kgk_customisations.kgk_customisations.doctype.parcel.parcel.populate_child_stones_only",
        queue='long',
        timeout=7200,
        parcel_name=parcel_name,
        job_name=f"populate_child_stones_{parcel_name}_{int(time.time())}",
        now=False
    )
    
    return {
        "status": "queued",
        "message": f"Child stone population queued for {parcel_name}. Check Background Jobs."
    }

@frappe.whitelist()
def populate_child_stones_only(parcel_name: str):
    """
    Standalone function to only populate child_stones tables without barcode fixing
    Useful if you just want to refresh the child stone relationships
    """
    try:
        populated_count = _populate_child_stones_table(parcel_name)
        
        message = f"Child stone tables populated for {populated_count} stones in parcel {parcel_name}"
        frappe.msgprint(message)
        
        return {
            "status": "success",
            "message": message,
            "populated": populated_count
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Child Stone Population Error")
        frappe.throw(f"Population failed: {str(e)}")


@frappe.whitelist()
def rebuild_all_child_tables(parcel_name: str = None):
    """
    Rebuild child_stones tables for all stones, optionally filtered by parcel
    More comprehensive - useful after major data changes
    """
    try:
        filters = {}
        if parcel_name:
            filters["parcel"] = parcel_name
        
        # Get all stones that have children
        all_parent_stones = frappe.db.sql("""
            SELECT DISTINCT parent_stone 
            FROM `tabStone` 
            WHERE parent_stone IS NOT NULL 
            AND parent_stone != ''
            {parcel_filter}
        """.format(
            parcel_filter=f"AND parcel = '{parcel_name}'" if parcel_name else ""
        ), as_dict=True)
        
        parent_stone_names = [s.parent_stone for s in all_parent_stones]
        
        updated_count = 0
        
        for parent_stone_name in parent_stone_names:
            try:
                # Get all children of this parent
                children = frappe.get_all(
                    "Stone",
                    filters={"parent_stone": parent_stone_name},
                    fields=["name", "stone_name", "barcode", "main_barcode"],
                    order_by="stone_name asc"
                )
                
                if not children:
                    continue
                
                # Update parent stone's child table
                parent_doc = frappe.get_doc("Stone", parent_stone_name)
                parent_doc.child_stones = []
                
                for child in children:
                    parent_doc.append("child_stones", {
                        "stone_name": child.name,
                        "barcode": child.barcode or "",
                        "main_barcode": child.main_barcode or ""
                    })
                
                parent_doc.save(ignore_permissions=True)
                updated_count += 1
                
                if updated_count % 50 == 0:
                    frappe.db.commit()
                    print(f"Progress: {updated_count}/{len(parent_stone_names)} parent stones updated")
                
            except Exception as e:
                print(f"Error updating {parent_stone_name}: {str(e)}")
                continue
        
        frappe.db.commit()
        
        message = f"Rebuilt child_stones tables for {updated_count} parent stones"
        if parcel_name:
            message += f" in parcel {parcel_name}"
        
        frappe.msgprint(message)
        
        return {
            "status": "success",
            "message": message,
            "updated": updated_count
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Rebuild Child Tables Error")
        frappe.throw(f"Rebuild failed: {str(e)}")


@frappe.whitelist()
def inspect_excel_file(file_url: str):
    """Inspect Excel file structure"""
    try:
        file_path = frappe.get_site_path(file_url.strip("/"))
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        df.columns = [str(c).strip() for c in df.columns]
        
        stone_name_col = _find_name_column(df.columns)
        
        # Find recognized columns
        recognized = []
        unrecognized = []
        
        for col in df.columns:
            if col in COLUMN_MAP:
                recognized.append(col)
            else:
                unrecognized.append(col)
        
        return {
            "success": True,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "stone_name_column": stone_name_col,
            "recognized_columns": recognized,
            "unrecognized_columns": unrecognized,
            "column_mapping": COLUMN_MAP,
            "sample_stones": df[stone_name_col].dropna().head(5).tolist() if stone_name_col else []
        }
        
    except Exception as e:
        return {"error": str(e)}


def _recover_barcodes_from_cache(recovery_list):
    """Recover barcodes using cached Excel data during import process"""
    recovered = 0
    failed = 0
    
    print(f"Starting cache-based barcode recovery for {len(recovery_list)} stones")
    
    for item in recovery_list:
        stone_name = item["stone_name"]
        excel_data = item["excel_data"]
        extraction_details = item.get("extraction_details", {})
        
        if not excel_data:
            failed += 1
            print(f"CACHE RECOVERY FAILED: No Excel data for {stone_name}")
            continue
        
        # Try to extract barcode from cached Excel data with enhanced methods
        barcode_value = None
        recovery_method = "unknown"
        
        # Method 1: Direct barcode column
        if 'Barcode' in excel_data and not pd.isna(excel_data['Barcode']):
            barcode_raw = excel_data['Barcode']
            barcode_str = str(barcode_raw).strip()
            if barcode_str and barcode_str.lower() not in ['none', 'null', 'nan', '']:
                # Clean numeric barcodes
                if '.' in barcode_str and barcode_str.endswith('.0'):
                    barcode_str = barcode_str[:-2]
                barcode_value = barcode_str
                recovery_method = "direct_barcode_column"
        
        # Method 2: Try alternative column names
        if not barcode_value:
            alternative_cols = ['barcode', 'BARCODE', 'Bar Code', 'Stone Barcode', 'Code']
            for alt_col in alternative_cols:
                if alt_col in excel_data and not pd.isna(excel_data[alt_col]):
                    barcode_raw = excel_data[alt_col]
                    barcode_str = str(barcode_raw).strip()
                    if barcode_str and barcode_str.lower() not in ['none', 'null', 'nan', ''] and len(barcode_str) >= 3:
                        if '.' in barcode_str and barcode_str.endswith('.0'):
                            barcode_str = barcode_str[:-2]
                        barcode_value = barcode_str
                        recovery_method = f"alternative_column_{alt_col}"
                        break
        
        # Method 3: Extract from stone name pattern
        if not barcode_value:
            import re
            barcode_match = re.search(r'\d{7,}', stone_name)  # 7+ digit numbers
            if barcode_match:
                barcode_value = barcode_match.group()
                recovery_method = "extracted_from_stone_name"
        
        # Apply the recovered barcode
        if barcode_value:
            try:
                frappe.db.set_value("Stone", stone_name, "barcode", barcode_value)
                recovered += 1
                print(f"CACHE RECOVERY SUCCESS: Stone {stone_name} barcode = '{barcode_value}' (method: {recovery_method})")
            except Exception as e:
                failed += 1
                print(f"CACHE RECOVERY DATABASE ERROR: Failed to save barcode for {stone_name}: {str(e)}")
        else:
            failed += 1
            print(f"CACHE RECOVERY FAILED: No valid barcode found for {stone_name}")
            # Debug: Show available Excel columns
            available_cols = [k for k in excel_data.keys() if not pd.isna(excel_data[k])][:10]
            print(f"  Available Excel columns: {available_cols}")
    
    if recovered > 0:
        frappe.db.commit()
        print(f"Cache recovery completed: {recovered} barcodes recovered, {failed} failed")
    
    return {"recovered": recovered, "failed": failed}


@frappe.whitelist()
def recover_missing_barcodes(parcel_name: str, file_url: str):
    """
    Backup recovery mechanism: Re-read Excel file to recover missing barcodes
    This function can be called manually after import to fix any stones with missing barcodes
    """
    try:
        # Validate inputs
        if not parcel_name or not file_url:
            frappe.throw("Parcel name and file URL are required")
        
        # Load the original Excel file
        file_path = frappe.get_site_path(file_url.strip("/"))
        if not os.path.exists(file_path):
            frappe.throw(f"Original Excel file not found: {file_path}")
        
        print(f"=== ENHANCED BARCODE RECOVERY DEBUG ===")
        print(f"Starting barcode recovery for parcel: {parcel_name}")
        print(f"Using Excel file: {file_path}")
        
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        df.columns = [str(c).strip() for c in df.columns]
        
        print(f"Excel file loaded: {len(df)} rows, {len(df.columns)} columns")
        print(f"Available columns: {list(df.columns)}")
        
        stone_name_col = _find_name_column(df.columns)
        if not stone_name_col:
            frappe.throw("Could not find stone name column in Excel file")
        
        print(f"Found stone name column: '{stone_name_col}'")
        
        # ENHANCED DEBUGGING: Check barcode column availability
        barcode_columns_found = []
        for col in df.columns:
            if 'barcode' in col.lower() or 'bar code' in col.lower():
                barcode_columns_found.append(col)
        
        print(f"Barcode-related columns found: {barcode_columns_found}")
        
        # Check if primary barcode column exists and has data
        if 'Barcode' in df.columns:
            barcode_col_stats = {
                'total_entries': len(df),
                'non_null_entries': df['Barcode'].notna().sum(),
                'null_entries': df['Barcode'].isna().sum(),
                'sample_values': df['Barcode'].dropna().head(10).tolist()
            }
            print(f"Primary 'Barcode' column statistics: {barcode_col_stats}")
        else:
            print(f"WARNING: No 'Barcode' column found in Excel file!")
        
        # Create a lookup dictionary from Excel with enhanced barcode extraction
        excel_barcode_lookup = {}
        barcode_extraction_stats = {"found": 0, "missing": 0, "invalid": 0}
        excel_stone_names = []
        
        print(f"\n=== EXCEL DATA EXTRACTION ===")
        for idx, row in df.iterrows():
            if idx < 5:  # Debug first 5 rows
                print(f"Row {idx} debug:")
                print(f"  Stone name raw: '{row[stone_name_col]}'")
                print(f"  Barcode raw: '{row.get('Barcode', 'COLUMN_NOT_FOUND')}'")
            
            stone_name_raw = row[stone_name_col]
            if pd.isna(stone_name_raw):
                continue
            
            stone_name = str(stone_name_raw).strip()
            excel_stone_names.append(stone_name)
            barcode_value = None
            
            # Primary barcode extraction with detailed debugging
            if 'Barcode' in row.index and not pd.isna(row['Barcode']):
                barcode_raw = row['Barcode']
                barcode_str = str(barcode_raw).strip()
                
                if idx < 5:  # Debug first 5 rows
                    print(f"  Barcode processed: '{barcode_str}'")
                    print(f"  Barcode length: {len(barcode_str)}")
                    print(f"  Barcode is valid: {barcode_str and barcode_str.lower() not in ['none', 'null', 'nan', '']}")
                
                if barcode_str and barcode_str.lower() not in ['none', 'null', 'nan', '']:
                    # Clean up numeric barcodes
                    if '.' in barcode_str and barcode_str.endswith('.0'):
                        barcode_str = barcode_str[:-2]
                        if idx < 5:
                            print(f"  Barcode cleaned: '{barcode_str}'")
                    
                    if len(barcode_str) >= 3:  # Reasonable barcode length
                        barcode_value = barcode_str
                        barcode_extraction_stats["found"] += 1
                    else:
                        barcode_extraction_stats["invalid"] += 1
                        if idx < 5:
                            print(f"  Barcode rejected (too short): '{barcode_str}'")
                else:
                    barcode_extraction_stats["missing"] += 1
            else:
                barcode_extraction_stats["missing"] += 1
            
            # Fallback barcode extraction with debugging
            if not barcode_value:
                if idx < 5:
                    print(f"  Trying fallback barcode extraction...")
                
                alternative_cols = ['barcode', 'BARCODE', 'Bar Code', 'Stone Barcode']
                for alt_col in alternative_cols:
                    if alt_col in row.index and not pd.isna(row[alt_col]):
                        fallback_val = str(row[alt_col]).strip()
                        if idx < 5:
                            print(f"    Checking '{alt_col}': '{fallback_val}'")
                        
                        if fallback_val and fallback_val.lower() not in ['none', 'null', 'nan', ''] and len(fallback_val) >= 3:
                            if '.' in fallback_val and fallback_val.endswith('.0'):
                                fallback_val = fallback_val[:-2]
                            barcode_value = fallback_val
                            barcode_extraction_stats["found"] += 1
                            if idx < 5:
                                print(f"    Fallback success: '{fallback_val}'")
                            break
            
            if barcode_value:
                excel_barcode_lookup[stone_name] = barcode_value
                if idx < 5:
                    print(f"  Final barcode stored: '{barcode_value}'")
            else:
                if idx < 5:
                    print(f"  No valid barcode found for this stone")
        
        print(f"\nExcel barcode extraction stats: {barcode_extraction_stats}")
        print(f"Created lookup table with {len(excel_barcode_lookup)} barcode entries")
        print(f"Total stone names in Excel: {len(excel_stone_names)}")
        print(f"Sample Excel stone names: {excel_stone_names[:10]}")
        
        # Find stones with missing barcodes in database - ONLY check leaf stones (is_group = 0)
        stones_missing_barcode = frappe.get_all(
            "Stone",
            filters={
                "parcel": parcel_name,
                "barcode": ["in", [None, ""]],
                "is_group": 0  # Only check leaf stones, not hierarchy parents
            },
            fields=["name", "stone_name"]
        )
        
        print(f"\n=== DATABASE ANALYSIS ===")
        print(f"Found {len(stones_missing_barcode)} stones with missing barcodes in database")
        
        if stones_missing_barcode:
            db_stone_names = [stone.name for stone in stones_missing_barcode]
            print(f"Sample database stone names: {db_stone_names[:10]}")
            
            # Check for exact matches
            exact_matches = set(db_stone_names) & set(excel_stone_names)
            print(f"Exact name matches between DB and Excel: {len(exact_matches)}")
            
            if len(exact_matches) < 10:
                print(f"Sample exact matches: {list(exact_matches)[:10]}")
            
            # Check for pattern differences
            if len(exact_matches) == 0 and len(db_stone_names) > 0 and len(excel_stone_names) > 0:
                print(f"\n=== NAME PATTERN ANALYSIS ===")
                print(f"DB stone name example: '{db_stone_names[0]}'")
                print(f"Excel stone name example: '{excel_stone_names[0]}'")
                
                # Check for case differences
                db_lower = [name.lower() for name in db_stone_names[:100]]
                excel_lower = [name.lower() for name in excel_stone_names[:100]]
                case_matches = set(db_lower) & set(excel_lower)
                print(f"Case-insensitive matches (first 100): {len(case_matches)}")
                
                # Check for whitespace differences
                db_stripped = [name.strip() for name in db_stone_names[:100]]
                excel_stripped = [name.strip() for name in excel_stone_names[:100]]
                stripped_matches = set(db_stripped) & set(excel_stripped)
                print(f"Whitespace-stripped matches (first 100): {len(stripped_matches)}")
        
        if not stones_missing_barcode:
            message = "No stones found with missing barcodes"
            frappe.msgprint(message)
            return {"status": "success", "message": message, "recovered": 0, "total_missing": 0}
        
        # Recovery process with enhanced debugging
        print(f"\n=== RECOVERY PROCESS ===")
        recovered_count = 0
        not_found_count = 0
        error_count = 0
        
        for i, stone in enumerate(stones_missing_barcode):
            stone_name = stone.name
            
            if i < 10:  # Debug first 10 stones
                print(f"Processing stone {i+1}: '{stone_name}'")
                print(f"  Looking for barcode in lookup table...")
            
            try:
                if stone_name in excel_barcode_lookup:
                    barcode_value = excel_barcode_lookup[stone_name]
                    frappe.db.set_value("Stone", stone_name, "barcode", barcode_value)
                    recovered_count += 1
                    if i < 10:
                        print(f"  SUCCESS: Recovered barcode '{barcode_value}'")
                else:
                    not_found_count += 1
                    if i < 10:
                        print(f"  NOT FOUND: Stone not in Excel lookup")
                        # Check for similar names
                        similar_names = [name for name in excel_stone_names if stone_name.lower() in name.lower() or name.lower() in stone_name.lower()][:3]
                        if similar_names:
                            print(f"    Similar names in Excel: {similar_names}")
            except Exception as e:
                error_count += 1
                print(f"ERROR: Failed to update barcode for {stone_name}: {str(e)}")
        
        # Commit changes
        if recovered_count > 0:
            frappe.db.commit()
        
        # Prepare result message
        message = f"Barcode recovery complete: {recovered_count} recovered, {not_found_count} not found in Excel, {error_count} errors"
        frappe.msgprint(message)
        
        print(f"\n=== RECOVERY SUMMARY ===")
        print(f"  - Total missing: {len(stones_missing_barcode)}")
        print(f"  - Recovered: {recovered_count}")
        print(f"  - Not found in Excel: {not_found_count}")
        print(f"  - Errors: {error_count}")
        print(f"=== END ENHANCED DEBUG ===")
        
        return {
            "status": "success",
            "message": message,
            "recovered": recovered_count,
            "total_missing": len(stones_missing_barcode),
            "not_found": not_found_count,
            "errors": error_count,
            "excel_stats": barcode_extraction_stats,
            "debug_info": {
                "excel_barcode_entries": len(excel_barcode_lookup),
                "excel_stone_count": len(excel_stone_names),
                "exact_matches": len(set([stone.name for stone in stones_missing_barcode]) & set(excel_stone_names)) if stones_missing_barcode else 0,
                "barcode_columns_found": barcode_columns_found
            }
        }
        
    except Exception as e:
        error_msg = f"Barcode recovery failed: {str(e)}"
        frappe.log_error(frappe.get_traceback(), "Barcode Recovery Error")
        frappe.throw(error_msg)


@frappe.whitelist()
def validate_excel_before_import(file_url: str):
    """
    Pre-import validation: Check Excel file for potential barcode issues
    This helps identify problems before starting the import process
    """
    try:
        file_path = frappe.get_site_path(file_url.strip("/"))
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        df.columns = [str(c).strip() for c in df.columns]
        
        stone_name_col = _find_name_column(df.columns)
        if not stone_name_col:
            return {"error": "Could not find stone name column"}
        
        validation_report = {
            "total_rows": len(df),
            "stones_with_barcode": 0,
            "stones_without_barcode": 0,
            "barcode_format_issues": [],
            "missing_barcode_stones": [],
            "column_analysis": {
                "barcode_column_found": 'Barcode' in df.columns,
                "main_barcode_column_found": 'Main barcode' in df.columns,
                "available_columns": df.columns.tolist()
            }
        }
        
        for idx, row in df.iterrows():
            stone_name_raw = row[stone_name_col]
            if pd.isna(stone_name_raw):
                continue
                
            stone_name = str(stone_name_raw).strip()
            barcode_value = row.get('Barcode')
            
            if pd.isna(barcode_value):
                validation_report["stones_without_barcode"] += 1
                validation_report["missing_barcode_stones"].append(stone_name)
            else:
                barcode_str = str(barcode_value).strip()
                if not barcode_str or barcode_str.lower() in ['none', 'null', 'nan']:
                    validation_report["stones_without_barcode"] += 1
                    validation_report["missing_barcode_stones"].append(stone_name)
                else:
                    validation_report["stones_with_barcode"] += 1
                    
                    # Check for format issues
                    if len(barcode_str) < 3:
                        validation_report["barcode_format_issues"].append({
                            "stone": stone_name,
                            "barcode": barcode_str,
                            "issue": "Barcode too short (less than 3 characters)"
                        })
                    elif not barcode_str.replace('.', '').replace('-', '').replace('_', '').isalnum():
                        validation_report["barcode_format_issues"].append({
                            "stone": stone_name,
                            "barcode": barcode_str,
                            "issue": "Non-alphanumeric barcode format"
                        })
        
        return validation_report
        
    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def clear_stones_data(parcel_name: str):
    """
    Clear all stones data for a specific parcel
    This is useful for testing and re-importing
    """
    try:
        if not parcel_name:
            frappe.throw("Parcel name is required")
        
        # Get count before deletion
        stone_count = frappe.db.count("Stone", {"parcel": parcel_name})
        
        if stone_count == 0:
            message = f"No stones found for parcel '{parcel_name}'"
            frappe.msgprint(message)
            return {"status": "success", "message": message, "deleted": 0}
        
        print(f"Found {stone_count} stones to delete for parcel '{parcel_name}'")
        
        # Delete all stones for this parcel
        frappe.db.delete("Stone", {"parcel": parcel_name})
        frappe.db.commit()
        
        # Verify deletion
        remaining_count = frappe.db.count("Stone", {"parcel": parcel_name})
        
        message = f"Successfully deleted {stone_count} stones for parcel '{parcel_name}'. Remaining: {remaining_count}"
        frappe.msgprint(message)
        
        print(f"Stone deletion complete: {stone_count} deleted, {remaining_count} remaining")
        
        return {
            "status": "success",
            "message": message,
            "deleted": stone_count,
            "remaining": remaining_count
        }
        
    except Exception as e:
        error_msg = f"Failed to clear stones data: {str(e)}"
        frappe.log_error(frappe.get_traceback(), "Clear Stones Error")
        frappe.throw(error_msg)