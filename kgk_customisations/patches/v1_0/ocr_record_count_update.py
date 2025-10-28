import frappe

def execute():
    """
    This patch updates the OCR total_records field for all OCR Record documents
    """
    
    records = frappe.get_all("OCR Data Upload", fields=["name"])
    for record in records:
        # count number of records in child table "items" linked to this OCR Data Upload
        count = frappe.db.count("OCR Data Upload Item", filters={"parent": record.name})
        frappe.db.set_value("OCR Data Upload", record.name, "total_records", count)

    frappe.db.commit()