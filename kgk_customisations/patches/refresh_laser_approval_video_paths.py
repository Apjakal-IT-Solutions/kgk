# Copyright (c) 2026, Apjakal IT Solutions and contributors
# Patch to refresh video mount paths for all Laser Approval documents
# Only updates rough_video, polish_video, tension_video fields if changed

import frappe

def execute():
    updated = 0
    docs = frappe.get_all("Laser Approval", fields=["name"])
    for d in docs:
        doc = frappe.get_doc("Laser Approval", d.name)
        old_paths = {
            "rough_video": doc.rough_video,
            "polish_video": doc.polish_video,
            "tension_video": doc.tension_video,
        }
        # Call the methods that refresh the video paths (adjust if your DocType uses different method names)
        if hasattr(doc, "get_video_indexes"):
            doc.get_video_indexes()
        # Only save if any path changed
        changed = (
            doc.rough_video != old_paths["rough_video"] or
            doc.polish_video != old_paths["polish_video"] or
            doc.tension_video != old_paths["tension_video"]
        )
        if changed:
            doc.save(ignore_permissions=True)
            updated += 1
    frappe.db.commit()
    print(f"Laser Approval video paths refreshed for {updated} documents.")
