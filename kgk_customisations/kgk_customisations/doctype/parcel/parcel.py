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


def _build_hierarchy_map(df, stone_name_col):
    """Build a map of all stones INCLUDING auto-generated parents needed for hierarchy"""
    hierarchy = {}
    all_parents = set()
    stones_found_in_excel = 0
    
    # STEP 1: Add all stones that exist in Excel
    for idx, row in df.iterrows():
        stone_name_raw = row[stone_name_col]
        
        if pd.isna(stone_name_raw):
            continue
        
        stone_name = str(stone_name_raw).strip()
        if not stone_name or stone_name.lower() in ['none', 'null', 'nan']:
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
            # Walk up the entire parent chain
            current = parent
            while current:
                if current not in hierarchy:
                    parents_to_add.add(current)
                current = _get_parent_stone(current)
    
    # Add all missing parents
    for parent_stone in parents_to_add:
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
    """Create stones level by level"""
    processed = 0
    errors = 0
    
    # Sort by level
    sorted_stones = sorted(hierarchy_map.items(), key=lambda x: x[1]["level"])
    total = len(sorted_stones)
    
    print(f"Starting hierarchical creation of {total} stones")
    
    for i, (stone_name, info) in enumerate(sorted_stones):
        try:
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
            
            # Prepare stone data
            if info["has_data"] and info["row_idx"] is not None:
                # Has Excel data
                row = df.iloc[info["row_idx"]]
                print(f"  Excel row data available: YES")
                print(f"  Row index in DataFrame: {info['row_idx']}")
                print(f"  Stone name in Excel: '{row[stone_name_col]}'")
                
                stone_data = _extract_stone_data(row, stone_name, parcel_name, info["parent"], info["level"])
                
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
            
            # Create stone
            stone_doc = frappe.get_doc(stone_data)
            stone_doc.insert(ignore_permissions=True, ignore_mandatory=True)
            processed += 1
            
            # Verify first stone was saved correctly
            if i < 3:
                saved_stone = frappe.get_doc("Stone", stone_name)
                print(f"Verification after save:")
                print(f"  org_weight: {saved_stone.org_weight}")
                print(f"  main_barcode: {saved_stone.main_barcode or 'EMPTY'}")
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
    
    print(f"Hierarchical creation complete: {processed} processed, {errors} errors")
    return {"processed": processed, "errors": errors}


def _extract_stone_data(row, stone_name, parcel_name, parent_stone, level):
    """Extract all stone data from Excel row using centralized column map"""
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
    
    print(f"DATA EXTRACTION DEBUG for {stone_name}:")
    print(f"  Available Excel columns: {len(row.index)}")
    print(f"  COLUMN_MAP entries: {len(COLUMN_MAP)}")
    
    # Map all fields from Excel using COLUMN_MAP
    for excel_col, field_name in COLUMN_MAP.items():
        fields_processed += 1
        if excel_col not in row.index:
            # Column doesn't exist in Excel
            continue
        
        value = row[excel_col]
        
        # ENHANCED BARCODE DEBUGGING
        if field_name in ['main_barcode', 'barcode']:
            print(f"BARCODE DEBUG {stone_name}: Field={field_name}, Excel_Col='{excel_col}', Raw_Value='{value}', Type={type(value)}, IsNA={pd.isna(value)}")
            if pd.isna(value):
                print(f"  -> Value is NaN/None for {field_name}")
            elif str(value).strip() == '':
                print(f"  -> Value is empty string for {field_name}")
            else:
                print(f"  -> Value looks valid: '{str(value).strip()}'")
        
        # Check for critical missing values
        if field_name in ['main_barcode', 'barcode'] and pd.isna(value):
            missing_critical.append(field_name)
        
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
            # String/Data fields - CRITICAL: explicit string conversion and validation
            str_val = cstr(value).strip()
            if str_val and str_val.lower() not in ['none', 'null', 'nan', '']:
                stone_data[field_name] = str_val
                fields_populated += 1
            elif field_name in ['main_barcode', 'barcode']:
                # Log if critical barcode fields are empty strings
                missing_critical.append(f"{field_name}_empty_string")
    
    # DATA EXTRACTION SUMMARY
    print(f"EXTRACTION SUMMARY {stone_name}:")
    print(f"  Processed {fields_processed} column mappings")
    print(f"  Successfully populated {fields_populated} fields")
    
    # COMPREHENSIVE BARCODE FINAL ANALYSIS
    has_main_barcode = 'main_barcode' in stone_data and stone_data.get('main_barcode')
    has_barcode = 'barcode' in stone_data and stone_data.get('barcode')
    
    print(f"BARCODE FINAL {stone_name}: has_main_barcode={has_main_barcode}, has_barcode={has_barcode}")
    if has_main_barcode:
        print(f"  main_barcode = '{stone_data['main_barcode']}'")
    if has_barcode:
        print(f"  barcode = '{stone_data['barcode']}'")
    
    # Critical analysis: if NO fields populated, something is wrong
    if fields_populated == 0:
        print(f"CRITICAL ERROR: NO FIELDS POPULATED for {stone_name}!")
        print(f"  This suggests column name mismatch or data format issues")
        print(f"  First 10 Excel columns and values:")
        for i, col in enumerate(list(row.index)[:10]):
            print(f"    {i+1}. '{col}' = '{row[col]}' (mapped to: {COLUMN_MAP.get(col, 'NOT MAPPED')})")
    
    # ENHANCED BARCODE INHERITANCE - Only for genuine Excel stones
    if not has_main_barcode:
        print(f"WARNING: Stone {stone_name} has no main_barcode from Excel data")
        
        # Strategy 1: Try to inherit from parent (only if parent exists in database with barcode)
        if parent_stone:
            try:
                parent_barcode = frappe.db.get_value("Stone", parent_stone, "main_barcode")
                if parent_barcode and parent_barcode.strip():
                    stone_data['main_barcode'] = parent_barcode
                    print(f"SUCCESS: Inherited main_barcode '{parent_barcode}' from parent {parent_stone}")
                else:
                    print(f"FAILED: Parent {parent_stone} has no valid main_barcode to inherit")
            except:
                print(f"FAILED: Parent {parent_stone} does not exist in database")
        
        # Strategy 2: Try to use regular barcode if main_barcode is missing
        if not stone_data.get('main_barcode') and has_barcode:
            stone_data['main_barcode'] = stone_data['barcode']
            print(f"FALLBACK: Used barcode '{stone_data['barcode']}' as main_barcode")
        
        # Strategy 3: Extract barcode from stone name as last resort
        if not stone_data.get('main_barcode'):
            # Look for numeric patterns in stone name that might be barcodes
            import re
            barcode_match = re.search(r'\d{7,}', stone_name)  # 7+ digit numbers
            if barcode_match:
                extracted_barcode = barcode_match.group()
                stone_data['main_barcode'] = extracted_barcode
                print(f"EXTRACTED: Used barcode '{extracted_barcode}' from stone name pattern")
            else:
                print(f"CRITICAL: No barcode available for stone {stone_name} - this should not happen with good Excel data")
    
    # Set is_group based on whether this stone has children (if parent stone)
    # For now, we'll set it to 0 and let Frappe's tree logic handle it
    
    return stone_data


def _create_minimal_stone_data(stone_name, parcel_name, parent_stone, level):
    """Create minimal data for parent stones without Excel data"""
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
    """Extract parent stone from name"""
    if not stone_name or "/" not in stone_name:
        return None
    
    return stone_name.rsplit("/", 1)[0]


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
def backfill_missing_main_barcodes(parcel_name: str):
    """
    Fix stones with missing main_barcodes by inheriting from parent or siblings
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
        
        fixed_count = 0
        
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
                fixed_count += 1
        
        frappe.db.commit()
        
        message = f"Backfill complete: Fixed {fixed_count} out of {len(stones_without_barcode)} stones"
        frappe.msgprint(message)
        
        return {
            "status": "success",
            "message": message,
            "fixed": fixed_count,
            "total_without_barcode": len(stones_without_barcode)
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Barcode Backfill Error")
        frappe.throw(f"Backfill failed: {str(e)}")


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