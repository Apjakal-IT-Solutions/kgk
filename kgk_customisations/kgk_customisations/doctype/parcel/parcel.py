# Copyright (c) 2025, Apjakal IT Solutions and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
import pandas as pd
from frappe.utils import cstr, flt
import os
from frappe.utils.file_manager import get_file_path

class Parcel(Document):
	pass

@frappe.whitelist()
def import_from_file(parcel_name: str, file_url: str):
    """
    Import stones from Excel file into Stone doctype with hierarchy.
    Enhanced with progress tracking and proper parent-child relationship handling.
    """
    try:
        # Validate inputs
        if not parcel_name or not file_url:
            frappe.throw("Parcel name and file URL are required")
        
        # Initialize progress
        frappe.publish_progress(
            percent=0,
            title="Stone Import",
            description="Starting import process..."
        )
        
        # Get file path and validate existence
        file_path = frappe.get_site_path(file_url.strip("/"))
        if not os.path.exists(file_path):
            frappe.throw(f"File not found: {file_path}")
        
        frappe.publish_progress(
            percent=5,
            title="Stone Import",
            description="Reading Excel file..."
        )
        
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        
        if df.empty:
            frappe.throw("No data found in the Excel file")
        
        frappe.publish_progress(
            percent=10,
            title="Stone Import",
            description="Analyzing file structure..."
        )
        
        # Find the correct column name for stone/parcel name
        column_names = list(df.columns)
        parcel_name_column = _find_name_column(column_names)
        
        if not parcel_name_column:
            frappe.throw(f"Could not find a column for stone/parcel names. Available columns: {column_names}")
        
        # Clean dataframe - remove completely empty rows
        df = df.dropna(how='all').reset_index(drop=True)
        total_rows = len(df)
        
        frappe.publish_progress(
            percent=15,
            title="Stone Import",
            description=f"Found {total_rows} rows to process. Analyzing hierarchy..."
        )
        
        # CRITICAL: Create parent stones first based on hierarchy
        stones_hierarchy = _analyze_and_create_hierarchy(df, parcel_name_column, parcel_name)
        
        frappe.publish_progress(
            percent=25,
            title="Stone Import",
            description=f"Created {len(stones_hierarchy)} parent stones. Processing child stones..."
        )
        
        # Process remaining stones in batches
        batch_size = 100
        processed_count = len(stones_hierarchy)  # Start with already created parent stones
        skipped_count = 0
        error_count = 0
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_df = df.iloc[batch_start:batch_end]
            
            # Process current batch
            batch_processed, batch_skipped, batch_errors = _process_batch(
                batch_df, parcel_name_column, parcel_name, batch_start, stones_hierarchy
            )
            
            # Only count new stones (not already created parents)
            new_processed = batch_processed - len([s for s in stones_hierarchy if batch_start <= s < batch_end])
            processed_count += new_processed
            skipped_count += batch_skipped
            error_count += batch_errors
            
            # Update progress
            progress_percent = 25 + ((batch_end / total_rows) * 70)  # 25% to 95%
            frappe.publish_progress(
                percent=progress_percent,
                title="Stone Import",
                description=f"Processed {batch_end}/{total_rows} rows. Total created: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}"
            )
            
            # Commit after each batch to avoid timeout
            frappe.db.commit()
            
            # Add small delay to prevent overwhelming the system
            import time
            time.sleep(0.1)
        
        # Final progress update
        frappe.publish_progress(
            percent=100,
            title="Stone Import",
            description="Import completed successfully!"
        )
        
        # Prepare result message
        message_parts = [f"Import completed! Created {processed_count} stones for parcel {parcel_name}"]
        if skipped_count > 0:
            message_parts.append(f"Skipped {skipped_count} empty/invalid rows")
        if error_count > 0:
            message_parts.append(f"Failed to process {error_count} rows (check Error Log)")
        
        result_message = ". ".join(message_parts)
        frappe.msgprint(result_message)
        
        return {
            "status": "success",
            "message": result_message,
            "processed": processed_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total_rows": total_rows,
            "hierarchy_created": len(stones_hierarchy)
        }
        
    except Exception as e:
        frappe.publish_progress(
            percent=100,
            title="Stone Import",
            description=f"Import failed: {str(e)}"
        )
        frappe.log_error(frappe.get_traceback(), "Import From File Error")
        frappe.throw(f"Import failed: {str(e)}")


def _analyze_and_create_hierarchy(df, parcel_name_column, parcel_name):
    """
    Analyze the stone hierarchy and create parent stones first.
    Returns a set of row indices that were already processed (parent stones).
    """
    stone_hierarchy = {}  # stone_name -> {"level": int, "parent": str, "row_idx": int}
    created_stones = set()  # Row indices of stones that were already created
    
    # First pass: analyze all stone names and build hierarchy map
    for idx, row in df.iterrows():
        try:
            raw_stone_name = row[parcel_name_column]
            if pd.isna(raw_stone_name):
                continue
                
            stone_name = str(raw_stone_name).strip()
            if not stone_name or stone_name.lower() in ['none', 'null', 'nan']:
                continue
            
            parent_stone = get_parent_stone(stone_name)
            level = stone_name.count("/")
            
            stone_hierarchy[stone_name] = {
                "level": level,
                "parent": parent_stone,
                "row_idx": idx,
                "row_data": row
            }
            
        except Exception:
            continue
    
    # Sort stones by hierarchy level (parents first)
    sorted_stones = sorted(stone_hierarchy.items(), key=lambda x: x[1]["level"])
    
    # Second pass: create stones in proper order (parents before children)
    for stone_name, stone_info in sorted_stones:
        try:
            # Skip if stone already exists
            if frappe.db.exists("Stone", stone_name):
                created_stones.add(stone_info["row_idx"])
                continue
            
            # Ensure parent exists before creating child
            parent_stone = stone_info["parent"]
            if parent_stone and not frappe.db.exists("Stone", parent_stone):
                # If parent doesn't exist but should, create a minimal parent stone
                _create_minimal_parent_stone(parent_stone, parcel_name)
            
            # Create the stone
            row = stone_info["row_data"]
            stone_data = _prepare_stone_data(row, stone_name, parcel_name, parent_stone, stone_info["level"])
            
            stone_doc = frappe.get_doc(stone_data)
            stone_doc.insert(ignore_permissions=True)
            created_stones.add(stone_info["row_idx"])
            
        except Exception as e:
            frappe.log_error(f"Error creating stone in hierarchy {stone_name}: {str(e)}", "Hierarchy Creation Error")
            continue
    
    return created_stones


def _create_minimal_parent_stone(parent_stone_name, parcel_name):
    """Create a minimal parent stone when it doesn't exist in the data"""
    try:
        parent_level = parent_stone_name.count("/")
        grandparent = get_parent_stone(parent_stone_name)
        
        # Ensure grandparent exists recursively
        if grandparent and not frappe.db.exists("Stone", grandparent):
            _create_minimal_parent_stone(grandparent, parcel_name)
        
        # Create minimal parent stone
        parent_data = {
            "doctype": "Stone",
            "stone_name": parent_stone_name,
            "parcel": parcel_name,
            "parent_stone": grandparent,
            "level": parent_level,
            "stone_type": "ROUGH",  # Default to ROUGH for parent stones
            "qty": 0,
            "carat_org": 0,
            "carat_exp": 0,
        }
        
        parent_doc = frappe.get_doc(parent_data)
        parent_doc.insert(ignore_permissions=True)
        
        frappe.log_error(f"Created minimal parent stone: {parent_stone_name}", "Parent Stone Creation")
        
    except Exception as e:
        frappe.log_error(f"Error creating minimal parent stone {parent_stone_name}: {str(e)}", "Parent Creation Error")


def _prepare_stone_data(row, stone_name, parcel_name, parent_stone, level):
    """Prepare stone data dictionary from row"""
    return {
        "doctype": "Stone",
        "stone_name": stone_name,
        "parcel": parcel_name,
        "parent_stone": parent_stone,
        "level": level,
        "stone_type": "ROUGH" if not pd.isna(row.get("Qty")) and flt(row.get("Qty")) > 0 else "POLISHED",
        "qty": flt(row.get("Qty", 0)) if not pd.isna(row.get("Qty")) else 0,
        "carat_org": flt(row.get("Carat Org", 0)) if not pd.isna(row.get("Carat Org")) else 0,
        "carat_exp": flt(row.get("Carat Exp", 0)) if not pd.isna(row.get("Carat Exp")) else 0,
        "shape": cstr(row.get("Shape", "")).strip() or None,
        "color": cstr(row.get("Color", "")).strip() or None,
        "clarity": cstr(row.get("Clarity", "")).strip() or None,
        "quality": cstr(row.get("Quality", "")).strip() or None,
        "rapaport_price": flt(row.get("Rapaport Price", 0)) if not pd.isna(row.get("Rapaport Price")) else 0,
        "back_percent": flt(row.get("Back Percent", 0)) if not pd.isna(row.get("Back Percent")) else 0,
        "amount": flt(row.get("Amount", 0)) if not pd.isna(row.get("Amount")) else 0,
        "remark": cstr(row.get("Remark", "")).strip() or None
    }


def _find_name_column(column_names):
    """Find the correct column name for stone/parcel names"""
    possible_names = ["Parcel Name", "ParcelName", "Parcel_Name", "Stone Name", "StoneName", "Stone_Name", "Name"]
    
    # Try exact matches first
    for col_name in possible_names:
        if col_name in column_names:
            return col_name
    
    # Try case-insensitive search
    for col_name in column_names:
        if any(possible.lower() in col_name.lower() for possible in ["parcel", "stone", "name"]):
            return col_name
    
    return None


def _process_batch(batch_df, parcel_name_column, parcel_name, batch_start_idx, already_created_stones):
    """Process a batch of rows and return counts. Skip stones already created in hierarchy phase."""
    processed = 0
    skipped = 0
    errors = 0
    
    for idx, row in batch_df.iterrows():
        try:
            # Skip if this stone was already created in hierarchy phase
            if idx in already_created_stones:
                continue
            
            # Get stone name using the discovered column
            raw_stone_name = row[parcel_name_column]
            
            # Skip if stone name is None, NaN, empty, or just whitespace
            if pd.isna(raw_stone_name):
                skipped += 1
                continue
            
            stone_name = str(raw_stone_name).strip()
            
            # Only skip if actually empty after conversion
            if not stone_name or stone_name.lower() in ['none', 'null', 'nan']:
                skipped += 1
                continue
            
            # Skip if stone already exists (might have been created in hierarchy phase)
            if frappe.db.exists("Stone", stone_name):
                processed += 1  # Count as processed since it exists
                continue
            
            # Determine parent stone and level
            parent_stone = get_parent_stone(stone_name)
            level = stone_name.count("/")
            
            # Ensure parent exists (should have been created in hierarchy phase, but double-check)
            if parent_stone and not frappe.db.exists("Stone", parent_stone):
                _create_minimal_parent_stone(parent_stone, parcel_name)
            
            # Prepare stone data
            stone_data = _prepare_stone_data(row, stone_name, parcel_name, parent_stone, level)
            
            # Create the stone
            try:
                stone_doc = frappe.get_doc(stone_data)
                stone_doc.insert(ignore_permissions=True)
                processed += 1
            except Exception as insert_error:
                frappe.log_error(f"Error inserting stone {stone_name}: {str(insert_error)}", "Stone Insert Error")
                errors += 1
            
        except Exception as row_error:
            frappe.log_error(f"Error processing row {batch_start_idx + idx + 1}: {str(row_error)}", "Row Processing Error")
            errors += 1
            continue
    
    return processed, skipped, errors


def get_parent_stone(stone_name: str):
    """
    Extract parent stone from stone_name based on hierarchy markers.
    """
    if not stone_name:
        return None
        
    try:
        if "/" in stone_name:
            parent = stone_name.rsplit("/", 1)[0]
            return parent if parent else None
        elif "-" in stone_name and stone_name.count("-") > 2:
            parent = "-".join(stone_name.split("-")[:-1])
            return parent if parent else None
        return None
    except Exception:
        return None


# Additional utility functions for better error handling

@frappe.whitelist()
def get_import_progress():
    """
    Get current import progress - can be called from frontend
    """
    # This function can be used to check if an import is still running
    # You can enhance this based on your needs
    return {"status": "running", "message": "Check console for progress updates"}


@frappe.whitelist()
def import_from_file_async(parcel_name: str, file_url: str):
    """
    Async version that can be called without blocking the UI
    """
    try:
        # Queue the import job in background
        frappe.enqueue(
            method=import_from_file,
            queue='long',
            timeout=3600,  # 1 hour timeout
            parcel_name=parcel_name,
            file_url=file_url,
            is_async=True,
            job_name=f"stone_import_{parcel_name}"
        )
        
        return {
            "status": "queued",
            "message": f"Import queued for parcel {parcel_name}. Check progress in background jobs."
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def inspect_excel_file(file_url: str):
    """
    Inspect Excel file structure without importing - for debugging
    """
    try:
        file_path = frappe.get_site_path(file_url.strip("/"))
        
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        
        # Find name column
        column_names = list(df.columns)
        name_column = _find_name_column(column_names)
        
        # Get file info
        info = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_names": column_names,
            "name_column": name_column,
            "sample_data": {}
        }
        
        # Get sample data for each column (first 3 non-null values)
        for col in df.columns:
            sample_values = df[col].dropna().head(3).tolist()
            info["sample_data"][col] = sample_values
        
        # If name column found, show some stats
        if name_column:
            valid_names = df[name_column].dropna().astype(str).str.strip()
            valid_names = valid_names[valid_names != '']
            info["valid_stone_names"] = len(valid_names)
            info["sample_stone_names"] = valid_names.head(5).tolist()
        
        return info
        
    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def validate_import_file(file_url: str):
    """
    Validate the Excel file before importing
    """
    try:
        file_path = frappe.get_site_path(file_url.strip("/"))
        
        if not os.path.exists(file_path):
            return {"valid": False, "message": "File not found"}
        
        # Try to read the file
        df = pd.read_excel(file_path, sheet_name="Single Stone", engine="pyxlsb")
        
        if df.empty:
            return {"valid": False, "message": "File contains no data"}
        
        # Find the name column
        possible_name_columns = ["Parcel Name", "ParcelName", "Parcel_Name", "Stone Name", "StoneName", "Stone_Name", "Name"]
        name_column = None
        
        for col_name in possible_name_columns:
            if col_name in df.columns:
                name_column = col_name
                break
        
        if not name_column:
            # Try case-insensitive search
            for col_name in df.columns:
                if any(possible.lower() in col_name.lower() for possible in ["parcel", "stone", "name"]):
                    name_column = col_name
                    break
        
        if not name_column:
            return {
                "valid": False, 
                "message": f"Could not find name column. Available columns: {list(df.columns)}"
            }
        
        # Count valid rows
        valid_rows = df[name_column].dropna().astype(str).str.strip().ne('').sum()
        
        return {
            "valid": True,
            "message": f"File is valid. Found {valid_rows} valid rows out of {len(df)} total rows",
            "total_rows": len(df),
            "valid_rows": valid_rows,
            "name_column": name_column,
            "columns": list(df.columns),
            "sample_names": df[name_column].dropna().head(5).tolist()
        }
        
    except Exception as e:
        return {"valid": False, "message": f"Error reading file: {str(e)}"}