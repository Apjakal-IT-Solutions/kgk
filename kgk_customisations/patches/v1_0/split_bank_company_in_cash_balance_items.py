# Migrate existing Cash Balance Item rows to use separate bank/company fields.
#
# Pass 1 — Bank-type rows: copy company → bank, clear company.
# Pass 2 — Cash-type rows: map short company alias → full Company record name.
#
# Uses frappe.db.set_value (no doc.save) to bypass all validation.
# Idempotent: each pass only touches rows not yet migrated.

import frappe

COMPANY_MAP = {
    "Agro": "KGK Agro",
    "Diamonds": "KGK Diamonds",
    "Jewellery": "KGK Jewelry",
    "Healthcare": "KGK Healthcare",
}


def execute():
    bank_updated = 0
    cash_updated = 0

    # ------------------------------------------------------------------
    # Pass 1: Bank-type rows — move company value into bank field
    # ------------------------------------------------------------------
    bank_rows = frappe.db.sql(
        """
        SELECT i.name, i.company
        FROM `tabCash Balance Item` i
        INNER JOIN `tabCash Balance` p ON p.name = i.parent
        WHERE p.balance_type = 'Bank'
          AND i.company IS NOT NULL AND i.company != ''
          AND (i.bank IS NULL OR i.bank = '')
        """,
        as_dict=True,
    )

    for row in bank_rows:
        bank_val = (row.company or "").strip()
        # Handle legacy compound key stored in company field: "ZAR@ABSA" → "ABSA"
        if "@" in bank_val:
            _, bank_val = bank_val.split("@", 1)
        frappe.db.set_value(
            "Cash Balance Item",
            row.name,
            {"bank": bank_val.strip(), "company": ""},
            update_modified=False,
        )
        bank_updated += 1

    if bank_updated:
        frappe.db.commit()

    # ------------------------------------------------------------------
    # Pass 2: Cash-type rows — map short alias to full Company name
    # ------------------------------------------------------------------
    cash_rows = frappe.db.sql(
        """
        SELECT i.name, i.company
        FROM `tabCash Balance Item` i
        INNER JOIN `tabCash Balance` p ON p.name = i.parent
        WHERE p.balance_type = 'Cash'
          AND i.company IS NOT NULL AND i.company != ''
        """,
        as_dict=True,
    )

    for row in cash_rows:
        short = (row.company or "").strip()
        full_name = COMPANY_MAP.get(short)
        if full_name and full_name != short:
            frappe.db.set_value(
                "Cash Balance Item",
                row.name,
                {"company": full_name},
                update_modified=False,
            )
            cash_updated += 1

    if cash_updated:
        frappe.db.commit()

    print(
        "split_bank_company_in_cash_balance_items: "
        "{} Bank rows migrated, {} Cash rows updated".format(bank_updated, cash_updated)
    )
