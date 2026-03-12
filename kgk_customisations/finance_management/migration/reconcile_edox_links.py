"""
reconcile_edox_links.py
-----------------------
Idempotent script to reconcile Cash Document `main_file` against the e-dox
network mount, and to populate supporting file child-table rows + Frappe File
records for any _A/_B/… variant files found on the mount.

Safe to run on any site (test or live) at any time.  Both functions are fully
idempotent — they skip documents that are already correctly linked.

Run with (replace <site> with your site name):
    bench --site <site> execute \
        kgk_customisations.finance_management.migration.reconcile_edox_links.run

    bench --site <site> execute \
        kgk_customisations.finance_management.migration.reconcile_edox_links.run_supporting
"""

import os
import frappe

MOUNT_BASE = "/mnt/share/e-dox/Documents"


def _find_pdf(doc_name):
    """Return (filename, is_fallback) for the best available PDF on the mount,
    or (None, False) if the directory is empty or missing."""
    doc_dir = os.path.join(MOUNT_BASE, doc_name)
    if not os.path.isdir(doc_dir):
        return None, False

    # 1. Canonical name
    canonical = doc_name + ".pdf"
    if os.path.isfile(os.path.join(doc_dir, canonical)):
        return canonical, False

    # 2. Any PDF in the directory (sorted for determinism)
    pdfs = sorted(f for f in os.listdir(doc_dir) if f.lower().endswith(".pdf"))
    if pdfs:
        return pdfs[0], True  # fallback — not the canonical name

    return None, False


def run():
    # Process all docs that are not yet linked to the mount
    rows = frappe.db.sql(
        """
        SELECT name, file_name
        FROM `tabCash Document`
        WHERE (main_file IS NULL OR main_file = '' OR main_file NOT LIKE '/edox/%')
          AND file_name IS NOT NULL
          AND file_name != ''
        ORDER BY name
        """,
        as_dict=True,
    )

    linked    = []   # (doc_name, filename, is_fallback)
    missing   = []   # (doc_name, reason)

    for row in rows:
        doc_name = row["name"]
        filename, is_fallback = _find_pdf(doc_name)

        if filename:
            linked.append((doc_name, filename, is_fallback))
        else:
            dir_exists = os.path.isdir(os.path.join(MOUNT_BASE, doc_name))
            reason = "empty directory" if dir_exists else "no directory on mount"
            missing.append((doc_name, reason))

    # Apply updates
    for doc_name, filename, _ in linked:
        edox_url = f"/edox/{doc_name}/{filename}"
        frappe.db.set_value(
            "Cash Document", doc_name,
            {"main_file": edox_url, "file_name": filename},
            update_modified=False,
        )
    if linked:
        frappe.db.commit()

    canonical_count = sum(1 for _, _, fb in linked if not fb)
    fallback_count  = sum(1 for _, _, fb in linked if fb)

    print(f"\n=== e-dox reconciliation complete ===")
    print(f"  Checked         : {len(rows)}")
    print(f"  Linked (exact)  : {canonical_count}  ({doc_name}.pdf found)")
    print(f"  Linked (fallback): {fallback_count}  (first PDF in directory used)")
    print(f"  No file found   : {len(missing)}")

    if missing:
        print(f"\nDocuments with no PDF on mount ({len(missing)}):")
        for doc_name, reason in missing:
            print(f"  {doc_name:15s}  ({reason})")

    if fallback_count:
        print(f"\nFallback links (no canonical {{name}}.pdf — first PDF used):")
        for doc_name, filename, is_fallback in linked:
            if is_fallback:
                print(f"  {doc_name:15s}  -> {filename}")


def run_supporting():
    """Populate child-table rows and Frappe File records for every supporting file
    ({name}_A.pdf, {name}_B.pdf, …) found on the mount.

    Idempotent: skips rows / File records that already exist.
    """
    import re
    # suffix pattern: {name}_A.pdf, {name}_B.pdf, etc. (single uppercase letter)
    suffix_re = re.compile(r"^(.+)_([A-Z])\.pdf$", re.IGNORECASE)

    all_docs = frappe.db.sql(
        "SELECT name FROM `tabCash Document` ORDER BY name",
        as_dict=True,
    )

    child_created  = 0
    file_created   = 0
    docs_with_sups = 0

    for doc_row in all_docs:
        doc_name = doc_row["name"]
        doc_dir  = os.path.join(MOUNT_BASE, doc_name)
        if not os.path.isdir(doc_dir):
            continue

        # Find supporting files (exclude canonical {name}.pdf)
        try:
            all_files = sorted(os.listdir(doc_dir))
        except PermissionError:
            continue

        supporting = [
            f for f in all_files
            if suffix_re.match(f) and f.lower() != f"{doc_name.lower()}.pdf"
        ]
        if not supporting:
            continue

        docs_with_sups += 1

        # Existing child rows for this parent
        existing_child_names = {
            r.file_name
            for r in frappe.get_all(
                "Cash Document Supporting File",
                filters={"parent": doc_name},
                fields=["file_name"],
            )
        }

        # Existing Frappe File URLs linked to this Cash Document
        existing_file_urls = {
            r.file_url
            for r in frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": "Cash Document",
                    "attached_to_name": doc_name,
                },
                fields=["file_url"],
            )
        }

        for filename in supporting:
            m = suffix_re.match(filename)
            suffix = m.group(2).upper() if m else ""
            edox_url = f"/edox/{doc_name}/{filename}"

            # Create child table row if missing
            if filename not in existing_child_names:
                frappe.get_doc({
                    "doctype":    "Cash Document Supporting File",
                    "parenttype": "Cash Document",
                    "parentfield":"supporting_files",
                    "parent":     doc_name,
                    "file_suffix": suffix,
                    "file_name":   filename,
                    "file_attachment": edox_url,
                }).insert(ignore_permissions=True)
                existing_child_names.add(filename)
                child_created += 1

            # Create Frappe File record (sidebar) if missing
            if edox_url not in existing_file_urls:
                frappe.db.sql(
                    """INSERT INTO `tabFile`
                        (name, file_name, file_url, attached_to_doctype, attached_to_name,
                         is_private, creation, modified, owner, modified_by, docstatus)
                       VALUES (%s, %s, %s, 'Cash Document', %s, 0,
                               NOW(), NOW(), 'Administrator', 'Administrator', 0)""",
                    (frappe.generate_hash(length=10), filename, edox_url, doc_name),
                )
                existing_file_urls.add(edox_url)
                file_created += 1

    frappe.db.commit()

    print(f"\n=== Supporting files reconciliation complete ===")
    print(f"  Documents with supporting files : {docs_with_sups}")
    print(f"  Child table rows created        : {child_created}")
    print(f"  Sidebar File records created    : {file_created}")
