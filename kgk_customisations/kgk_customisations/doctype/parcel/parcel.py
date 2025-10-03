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
    "ESP % E": "esp_percent_e",  # Corrected to match DocType
    "ESP @ E": "esp_at_e",  # Corrected to match DocType
    
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
    """Build a map of all stones and their hierarchy"""
    hierarchy = {}
    all_parents = set()
    
    for idx, row in df.iterrows():
        stone_name_raw = row[stone_name_col]
        
        if pd.isna(stone_name_raw):
            continue
        
        stone_name = str(stone_name_raw).strip()
        if not stone_name or stone_name.lower() in ['none', 'null', 'nan']:
            continue
        
        parent = _get_parent_stone(stone_name)
        level = stone_name.count("/")
        
        hierarchy[stone_name] = {
            "level": level,
            "parent": parent,
            "row_idx": idx,
            "has_data": True
        }
        
        # Track all parents
        if parent:
            all_parents.add(parent)
    
    # Add missing parents to hierarchy
    for parent in all_parents:
        if parent not in hierarchy:
            current = parent
            while current:
                if current not in hierarchy:
                    hierarchy[current] = {
                        "level": current.count("/"),
                        "parent": _get_parent_stone(current),
                        "row_idx": None,
                        "has_data": False
                    }
                current = _get_parent_stone(current)
    
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
            
            # Prepare stone data
            if info["has_data"] and info["row_idx"] is not None:
                # Has Excel data
                row = df.iloc[info["row_idx"]]
                stone_data = _extract_stone_data(row, stone_name, parcel_name, info["parent"], info["level"])
                
                # Debug first stone with data
                if i < 3 and info["has_data"]:
                    print(f"\n=== Stone {i+1}: {stone_name} ===")
                    print(f"Has Excel data: Yes (row {info['row_idx']})")
                    print(f"Parent: {info['parent']}")
                    print(f"Level: {info['level']}")
                    print(f"Fields populated: {len([k for k, v in stone_data.items() if v not in [None, 0, '', 'POLISHED']])}")
                    print(f"Sample data:")
                    print(f"  org_weight: {stone_data.get('org_weight', 'NOT SET')}")
                    print(f"  main_barcode: {stone_data.get('main_barcode', 'NOT SET')}")
                    print(f"  weight_e: {stone_data.get('weight_e', 'NOT SET')}")
                    print(f"  weight_l: {stone_data.get('weight_l', 'NOT SET')}")
                    print(f"  weight_ig: {stone_data.get('weight_ig', 'NOT SET')}")
                    print(f"  shape_l: {stone_data.get('shape_l', 'NOT SET')}")
            else:
                # Parent stone without data
                stone_data = _create_minimal_stone_data(stone_name, parcel_name, info["parent"], info["level"])
                if i < 3:
                    print(f"\n=== Stone {i+1}: {stone_name} ===")
                    print(f"Has Excel data: No (auto-generated parent)")
                    print(f"Parent: {info['parent']}")
                    print(f"Level: {info['level']}")
            
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
    
    # Map all fields from Excel using COLUMN_MAP
    for excel_col, field_name in COLUMN_MAP.items():
        if excel_col not in row.index:
            continue
        
        value = row[excel_col]
        
        if pd.isna(value):
            continue
        
        # Type conversion based on field patterns and DocType field types
        if field_name in ['org_weight', 'prop_cts', 'weight_e', 'weight_l', 'weight_ig']:
            # Float fields with 3 decimal precision
            stone_data[field_name] = flt(value, 3)
        elif field_name in ['est_amt', 'list_e', 'esp_at_e', 'list_l', 'esp_at_l', 
                           'esp_amount_l', 'list_ig', 'esp_at_ig', 'esp_amount_ig']:
            # Currency fields
            stone_data[field_name] = flt(value)
        elif field_name in ['esp_percent_e', 'esp_percent_l', 'esp_percent_ig']:
            # Percent fields - handle both decimal (0.15) and whole number (15) formats
            val = flt(value)
            # If value is > 1, assume it's in percentage format (e.g., 15%), convert to decimal
            stone_data[field_name] = val / 100 if val > 1 else val
        elif field_name == 'level':
            # Integer field
            stone_data[field_name] = int(value)
        else:
            # String/Data fields
            str_val = cstr(value).strip()
            if str_val:
                stone_data[field_name] = str_val
    
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
    """Async import for large files"""
    frappe.enqueue(
        method="kgk_customisations.kgk_customisations.doctype.parcel.parcel.import_from_file",
        queue='long',
        timeout=7200,
        parcel_name=parcel_name,
        file_url=file_url,
        job_name=f"stone_import_{parcel_name}_{int(time.time())}"
    )
    
    return {
        "status": "queued",
        "message": f"Import queued for {parcel_name}. Check Background Jobs."
    }


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