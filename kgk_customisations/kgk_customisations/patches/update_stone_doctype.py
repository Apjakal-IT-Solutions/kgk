# Create file: apps/kgk_customisations/kgk_customisations/patches/add_stone_fields.py

import frappe

def execute():
    """Add new fields to Stone DocType"""
    
    stone_meta = frappe.get_meta("Stone")
    
    new_fields = [
        {"fieldname": "shape_l", "fieldtype": "Data", "label": "Shape L", "insert_after": "shape"},
        {"fieldname": "color_l", "fieldtype": "Data", "label": "Color L", "insert_after": "color"},
        {"fieldname": "clarity_l", "fieldtype": "Data", "label": "Clarity L", "insert_after": "clarity"},
        {"fieldname": "polish_l", "fieldtype": "Data", "label": "Polish L", "insert_after": "clarity_l"},
        {"fieldname": "sym_l", "fieldtype": "Data", "label": "Sym. L", "insert_after": "polish_l"},
        {"fieldname": "fluro_l", "fieldtype": "Data", "label": "Fluro. L", "insert_after": "sym_l"},
        {"fieldname": "list_l", "fieldtype": "Currency", "label": "List L", "insert_after": "fluro_l"},
        {"fieldname": "esp_percent_l", "fieldtype": "Percent", "label": "ESP % L", "insert_after": "list_l"},
        {"fieldname": "esp_l", "fieldtype": "Currency", "label": "ESP @ L", "insert_after": "esp_percent_l"},
        {"fieldname": "esp_amount_l", "fieldtype": "Currency", "label": "ESP Amount L", "insert_after": "esp_l"},
        {"fieldname": "main_barcode", "fieldtype": "Data", "label": "Main Barcode", "insert_after": "stone_type"},
        {"fieldname": "barcode", "fieldtype": "Data", "label": "Barcode", "insert_after": "main_barcode"},
        {"fieldname": "org_wght", "fieldtype": "Float", "label": "Org Weight", "insert_after": "barcode"},
        {"fieldname": "prop_cts", "fieldtype": "Float", "label": "Prop. Cts", "insert_after": "org_wght"},
        {"fieldname": "lab", "fieldtype": "Data", "label": "Lab", "insert_after": "prop_cts"},
        {"fieldname": "wght_l", "fieldtype": "Float", "label": "Weight L", "insert_after": "lab"}
    ]
    
    for field_dict in new_fields:
        if not frappe.db.has_column("tabStone", field_dict["fieldname"]):
            # Add field to DocType
            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Stone",
                **field_dict
            }).insert()