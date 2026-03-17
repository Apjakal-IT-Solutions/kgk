COMPANY_MAP = {
    "Agro": "KGK Agro",
    "Diamonds": "KGK Diamonds",
    "Jewellery": "KGK Jewelry",
    "Healthcare": "KGK Healthcare",
}
import frappe
from frappe.utils import flt


def _parse_company_key(balance_type, company_key):
    key = (company_key or "").strip()
    if not key:
        return "", ""

    if balance_type == "Cash" and "_" in key:
        company, currency = key.rsplit("_", 1)
        return company.strip(), currency.strip()

    if balance_type == "Bank" and "@" in key:
        currency, bank = key.split("@", 1)
        return bank.strip(), currency.strip()

    return key, ""


def execute():
    parent_rows = frappe.db.get_all(
        "Cash Balance",
        fields=["name", "balance_type", "company", "basic", "accountant"],
    )

    updated = 0
    for row in parent_rows:
        doc = frappe.get_doc("Cash Balance", row.name)

        child_entity, child_currency = _parse_company_key(row.balance_type, row.company)

        # Build the target key for duplicate detection
        if row.balance_type == "Bank":
            target_key = (row.balance_type, "", child_entity, child_currency)
        else:
            target_key = (row.balance_type, child_entity, "", child_currency)

        found = False
        child_rows = doc.get("balances_table") or doc.get("table_dwal") or []
        for item in child_rows:
            if row.balance_type == "Bank":
                item_key = (row.balance_type, "", (item.bank or "").strip(), (item.currency or "").strip())
            else:
                item_key = (row.balance_type, (item.company or "").strip(), "", (item.currency or "").strip())
            if item_key == target_key:
                found = True
                break

        if found:
            continue

        if abs(flt(row.basic)) < 1e-6 and abs(flt(row.accountant)) < 1e-6:
            continue

        if child_currency and not frappe.db.exists("Currency", child_currency):
            print(f"Skipping: Currency '{child_currency}' does not exist")
            continue

        if row.balance_type == "Bank":
            doc.append(
                "balances_table",
                {
                    "bank": child_entity,
                    "company": "",
                    "currency": child_currency,
                    "basic": flt(row.basic),
                    "accountant": flt(row.accountant),
                },
            )
        else:
            mapped_company = COMPANY_MAP.get(child_entity, child_entity)
            if not frappe.db.exists("Company", mapped_company):
                print(f"Skipping: Company '{mapped_company}' does not exist")
                continue
            doc.append(
                "balances_table",
                {
                    "company": mapped_company,
                    "bank": "",
                    "currency": child_currency,
                    "basic": flt(row.basic),
                    "accountant": flt(row.accountant),
                },
            )

        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        updated += 1

    if updated:
        frappe.db.commit()
        print("Cash Balance child amount backfill completed: {} updated".format(updated))
    else:
        print("Cash Balance child amount backfill: no changes needed")
