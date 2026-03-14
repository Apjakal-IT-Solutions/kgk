# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt
"""
Cash Management Data Migration: PostgreSQL (Django cashapp_db) → Frappe (MariaDB)

Run on test site:
    bench --site kgkerp-test.local execute \
        kgk_customisations.finance_management.migration.migrate_cashapp.run

Run on live site:
    bench --site kgkerp.local execute \
        kgk_customisations.finance_management.migration.migrate_cashapp.run

Flags (pass as --kwargs):
    dry_run=True        Print what would be inserted without touching MariaDB
    reset=True          DELETE all Frappe rows first (use only on test site!)
"""

import frappe
import psycopg2
from frappe.utils import flt

# ---------------------------------------------------------------------------
# PostgreSQL connection details
# ---------------------------------------------------------------------------
PG = dict(
    host="192.168.1.114",
    port=5432,
    dbname="cashapp_db",
    user="postgres",
    password="red61046",
)

# ---------------------------------------------------------------------------
# USERNAME MAP
# Maps Django plain-name → Frappe user email.
# Fill in once Frappe user accounts have been created.
# Keys are case-sensitive and must exactly match values in:
#   documents.created_by   and   cash_bankbasicentry.username
# ---------------------------------------------------------------------------
USERNAME_MAP = {
    "Cebo":    "tlhowec@kgkmail.com",
    "Obakeng": "khumom@kgkmail.com",
    "Lore":    "lore.matauso@kgkmail.com",
    "Harsh":   "harsh@kgkmail.com",
    "Dipak":   "dipak@kgkmail.com",
    "super":   "super@kgkmail.com",
    # Fallback to Administrator for unmapped legacy names:
    "Ireen":   "ireene@kgkmail.com",
    "bob":     "bob@kgkmail.com",
    "admin":   "kgkadmin@kgkmail.com",
    "Unknown": "kgkadmin@kgkmail.com",
}

FALLBACK_USER = "Administrator"

# ---------------------------------------------------------------------------
# Filters for CashBalance import
# Only import compound-key company names (containing "_" for Cash type,
# or "@" for Bank type). Simple names (Diamonds, Agro, Cebo, Lore, etc.)
# are legacy/derivative rows and are skipped.
# ---------------------------------------------------------------------------
def _is_compound_company(balance_type, company):
    if balance_type == "Cash":
        return "_" in company
    if balance_type == "Bank":
        return "@" in company
    return False


def _map_user(django_name):
    """Return Frappe user email, or FALLBACK_USER if not mapped yet."""
    return USERNAME_MAP.get(django_name, FALLBACK_USER)


# ---------------------------------------------------------------------------
# Phase 1: Cash Documents
# ---------------------------------------------------------------------------
def _migrate_documents(pg_cur, dry_run, reset):
    if reset:
        frappe.db.sql("DELETE FROM `tabCash Document`")
        frappe.db.commit()
        print("  [reset] Cleared tabCash Document")

    pg_cur.execute("""
        SELECT unique_number, date, doc_type, file_name,
               status, created_by, company, main_type, sub_type, final_status2
        FROM documents
        ORDER BY date, unique_number
    """)
    rows = pg_cur.fetchall()
    cols = ["unique_number", "date", "file_name", "status",
            "created_by", "company", "main_type", "sub_type",
            "final_status2", "doc_type"]

    total = len(rows)
    success = skipped = failed = 0
    unmapped_users = set()

    print(f"\n  Migrating {total} Cash Documents …")

    for row in rows:
        (unique_number, date, doc_type, file_name, status,
         created_by, company, main_type, sub_type, final_status2) = row

        # Skip if already migrated
        if frappe.db.exists("Cash Document", unique_number):
            skipped += 1
            continue

        # Normalise company
        company_val = company if company in (
            "Diamonds", "Jewellery", "Agro", "Healthcare"
        ) else "Unknown"

        # Normalise sub_type — reject values not in the Select options
        valid_sub_types = {"", "Payment", "Receipt", "Credit Card", "EFT", "JE"}
        sub_type_val = sub_type if sub_type in valid_sub_types else ""

        # Map created_by
        frappe_user = _map_user(created_by)
        if frappe_user == FALLBACK_USER and created_by not in USERNAME_MAP:
            unmapped_users.add(created_by)

        if dry_run:
            print(f"    DRY RUN: {unique_number} ({main_type}) {date} "
                  f"company={company_val} created_by={frappe_user}")
            success += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Cash Document",
                "name": unique_number,
                "date": str(date),
                "company": company_val,
                "main_type": main_type or "Cash",
                "sub_type": sub_type_val,
                "file_name": file_name or "",
                "status": status or "pending",
                "final_status2": final_status2 or "pending2",
                "created_by": frappe_user,
                "migration_reference": unique_number,
                "year": int(str(date)[:4]),
            })
            doc.flags.ignore_validate = True
            doc.flags.ignore_permissions = True
            # Force the name to the Django unique_number (bypass autoname)
            doc.flags.name_set = True
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            success += 1
        except Exception as e:
            print(f"    ERROR {unique_number}: {e}")
            failed += 1

        if (success + failed) % 500 == 0:
            frappe.db.commit()
            print(f"    … committed {success + failed} so far")

    frappe.db.commit()

    if unmapped_users:
        print(f"\n  ⚠  Unmapped users (fell back to Administrator): "
              f"{sorted(unmapped_users)}")
    print(f"  Documents: {success} ok, {skipped} skipped, {failed} failed")
    return success, skipped, failed


# ---------------------------------------------------------------------------
# Phase 2: Cash Balance
# Only compound-key company names are imported.
# ---------------------------------------------------------------------------
def _migrate_cash_balance(pg_cur, dry_run, reset):
    if reset:
        frappe.db.sql("DELETE FROM `tabCash Balance`")
        frappe.db.commit()
        print("  [reset] Cleared tabCash Balance")

    pg_cur.execute("""
        SELECT date, balance_type, company, basic, accountant
        FROM cash_cashbalance
        ORDER BY date, balance_type, company
    """)
    rows = pg_cur.fetchall()
    total = len(rows)
    success = skipped = failed = filtered = 0

    print(f"\n  Migrating {total} Cash Balance rows (compound-key only) …")

    for date, balance_type, company, basic, accountant in rows:
        if not _is_compound_company(balance_type, company):
            filtered += 1
            continue

        existing = frappe.db.get_value(
            "Cash Balance",
            {"date": str(date), "balance_type": balance_type, "company": company},
            "name",
        )
        if existing:
            skipped += 1
            continue

        if dry_run:
            print(f"    DRY RUN: {date} {balance_type} {company} "
                  f"basic={basic} accountant={accountant}")
            success += 1
            continue

        try:
            child_company = company
            child_currency = ""
            if balance_type == "Cash" and "_" in company:
                child_company, child_currency = company.rsplit("_", 1)
            elif balance_type == "Bank" and "@" in company:
                child_currency, child_company = company.split("@", 1)

            doc = frappe.get_doc({
                "doctype": "Cash Balance",
                "date": str(date),
                "balance_type": balance_type,
                "company": company,
                "basic": flt(basic),
                "accountant": flt(accountant),
                "balances_table": [
                    {
                        "company": child_company,
                        "currency": child_currency,
                        "basic": flt(basic),
                        "accountant": flt(accountant),
                    }
                ],
            })
            doc.flags.ignore_validate = True
            doc.flags.ignore_permissions = True
            doc.insert(ignore_permissions=True)
            success += 1
        except Exception as e:
            print(f"    ERROR {date} {company}: {e}")
            failed += 1

        if (success + failed) % 200 == 0:
            frappe.db.commit()

    frappe.db.commit()
    print(f"  Cash Balance: {success} ok, {skipped} skipped, "
          f"{filtered} filtered (simple names), {failed} failed")
    return success, skipped, failed


# ---------------------------------------------------------------------------
# Phase 3: Bank Balance Entry
# ---------------------------------------------------------------------------
def _migrate_bank_balance_entry(pg_cur, dry_run, reset):
    if reset:
        frappe.db.sql("DELETE FROM `tabBank Balance Entry`")
        frappe.db.commit()
        print("  [reset] Cleared tabBank Balance Entry")

    pg_cur.execute("""
        SELECT date, company, username, balance
        FROM cash_bankbasicentry
        ORDER BY date, company, username
    """)
    rows = pg_cur.fetchall()
    total = len(rows)
    success = skipped = failed = 0
    unmapped_users = set()

    print(f"\n  Migrating {total} Bank Balance Entry rows …")

    for date, company, username, balance in rows:
        frappe_user = _map_user(username)
        if frappe_user == FALLBACK_USER and username not in USERNAME_MAP:
            unmapped_users.add(username)

        existing = frappe.db.get_value(
            "Bank Balance Entry",
            {"date": str(date), "company": company, "username": frappe_user},
            "name",
        )
        if existing:
            skipped += 1
            continue

        if dry_run:
            print(f"    DRY RUN: {date} {company} {frappe_user} balance={balance}")
            success += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Bank Balance Entry",
                "date": str(date),
                "company": company,
                "username": frappe_user,
                "balance": flt(balance),
            })
            doc.flags.ignore_validate = True
            doc.flags.ignore_permissions = True
            doc.insert(ignore_permissions=True)
            success += 1
        except Exception as e:
            print(f"    ERROR {date} {company} {username}: {e}")
            failed += 1

        if (success + failed) % 100 == 0:
            frappe.db.commit()

    frappe.db.commit()

    if unmapped_users:
        print(f"\n  ⚠  Unmapped users (fell back to Administrator): "
              f"{sorted(unmapped_users)}")
    print(f"  Bank Balance Entry: {success} ok, {skipped} skipped, {failed} failed")
    return success, skipped, failed


# ---------------------------------------------------------------------------
# Phase 4: Resync counters
# ---------------------------------------------------------------------------
def _resync_counters():
    from kgk_customisations.finance_management.doctype.cash_document.cash_document import (
        resync_counters,
    )
    resync_counters()
    print("\n  Counters resynced.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run(dry_run=False, reset=False):
    """
    Main migration entry point.

    Args:
        dry_run (bool): If True, print actions without writing to Frappe DB.
        reset   (bool): If True, truncate Frappe tables before importing.
                        Only use on the test site.
    """
    dry_run = frappe.utils.sbool(dry_run)
    reset = frappe.utils.sbool(reset)

    if reset and frappe.conf.get("host_name", "").find("kgkerp.local") >= 0:
        frappe.throw("reset=True is not allowed on the live site.")

    unmapped = [k for k in USERNAME_MAP if not USERNAME_MAP[k]]
    if unmapped:
        print(f"⚠  USERNAME_MAP has empty values for: {unmapped}")
        print("   Fill in the map before running on production data.")

    print("=" * 60)
    print(f"Cash Migration  |  dry_run={dry_run}  reset={reset}")
    print("=" * 60)

    pg_conn = psycopg2.connect(**PG)
    pg_cur = pg_conn.cursor()

    try:
        d_ok, d_skip, d_fail = _migrate_documents(pg_cur, dry_run, reset)
        cb_ok, cb_skip, cb_fail = _migrate_cash_balance(pg_cur, dry_run, reset)
        bb_ok, bb_skip, bb_fail = _migrate_bank_balance_entry(pg_cur, dry_run, reset)

        if not dry_run:
            _resync_counters()

    finally:
        pg_cur.close()
        pg_conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Cash Documents:      {d_ok} ok, {d_skip} skipped, {d_fail} failed")
    print(f"  Cash Balances:       {cb_ok} ok, {cb_skip} skipped, {cb_fail} failed")
    print(f"  Bank Balance Entry:  {bb_ok} ok, {bb_skip} skipped, {bb_fail} failed")
    print("=" * 60)
