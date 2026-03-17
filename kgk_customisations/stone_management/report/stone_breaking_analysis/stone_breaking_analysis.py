# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = _get_columns()
    data, summary = _get_data(filters)
    return columns, data, None, None, summary


def _get_columns():
    return [
        {"fieldname": "date",             "label": "Date",           "fieldtype": "Date",    "width": 100},
        {"fieldname": "name",             "label": "Document",       "fieldtype": "Link",    "options": "Stone Breaking Report", "width": 160},
        {"fieldname": "org_lot_id",       "label": "ORG Lot ID",     "fieldtype": "Data",    "width": 130},
        {"fieldname": "polish_lot_id",    "label": "Polish Lot ID",  "fieldtype": "Data",    "width": 130},
        {"fieldname": "department",       "label": "Department",     "fieldtype": "Link",    "options": "Department", "width": 140},
        {"fieldname": "tension_type",     "label": "Tension",        "fieldtype": "Data",    "width": 70},
        {"fieldname": "org_plan_value",   "label": "Plan Value",     "fieldtype": "Float",   "width": 100, "precision": 2},
        {"fieldname": "breaking_amount",  "label": "Breaking Amnt.", "fieldtype": "Float",   "width": 110, "precision": 2},
        {"fieldname": "breaking_percent", "label": "Breaking %",     "fieldtype": "Float",   "width": 90,  "precision": 2},
        {"fieldname": "stone_fault",      "label": "Stone Fault",    "fieldtype": "Check",   "width": 85},
        {"fieldname": "worker_fault",     "label": "Worker Fault",   "fieldtype": "Check",   "width": 90},
        {"fieldname": "result",           "label": "Result",         "fieldtype": "Data",    "width": 120},
        {"fieldname": "checked",          "label": "Checked",        "fieldtype": "Check",   "width": 75},
        {"fieldname": "reported_by",      "label": "Reported By",    "fieldtype": "Data",    "width": 120},
        {"fieldname": "workers",          "label": "Workers",        "fieldtype": "Data",    "width": 200},
        {"fieldname": "tally",            "label": "_tally",         "fieldtype": "Int",     "hidden": 1},
    ]


def _build_filters(filters):
    conditions = ["sbr.docstatus < 2"]
    values = {}

    if filters.get("date_from"):
        conditions.append("sbr.date >= %(date_from)s")
        values["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("sbr.date <= %(date_to)s")
        values["date_to"] = filters["date_to"]
    if filters.get("department"):
        conditions.append("sbr.department = %(department)s")
        values["department"] = filters["department"]
    if filters.get("tension_type"):
        conditions.append("sbr.tension_type_data_field = %(tension_type)s")
        values["tension_type"] = filters["tension_type"]
    if filters.get("result"):
        conditions.append("sbr.result LIKE %(result)s")
        values["result"] = "%{}%".format(filters["result"])
    if filters.get("checked") == "Checked":
        conditions.append("sbr.checked = 1")
    elif filters.get("checked") == "Unchecked":
        conditions.append("sbr.checked = 0")
    if filters.get("fault_type") == "Stone Fault":
        conditions.append("sbr.stone_fault = 1")
    elif filters.get("fault_type") == "Worker Fault":
        conditions.append("sbr.worker_fault = 1")
    elif filters.get("fault_type") == "Both Faults":
        conditions.append("sbr.stone_fault = 1 AND sbr.worker_fault = 1")
    elif filters.get("fault_type") == "Any Fault":
        conditions.append("(sbr.stone_fault = 1 OR sbr.worker_fault = 1)")
    if filters.get("min_breaking_pct"):
        conditions.append("sbr.breaking_percent >= %(min_breaking_pct)s")
        values["min_breaking_pct"] = flt(filters["min_breaking_pct"])
    if filters.get("max_breaking_pct"):
        conditions.append("sbr.breaking_percent <= %(max_breaking_pct)s")
        values["max_breaking_pct"] = flt(filters["max_breaking_pct"])

    return " AND ".join(conditions), values


def _get_data(filters):
    where, values = _build_filters(filters)

    # Worker sub-filter: needs a sub-query join when worker name/type is specified
    worker_join = ""
    if filters.get("worker") or filters.get("worker_type"):
        worker_join = (
            "INNER JOIN `tabStone Breaking Worker` sbw "
            "ON sbw.parent = sbr.name AND sbw.parenttype = 'Stone Breaking Report'"
        )
        if filters.get("worker"):
            where += " AND sbw.worker_name LIKE %(worker)s"
            values["worker"] = "%{}%".format(filters["worker"])
        if filters.get("worker_type"):
            where += " AND sbw.worker_type = %(worker_type)s"
            values["worker_type"] = filters["worker_type"]

    rows = frappe.db.sql(
        """
        SELECT DISTINCT
            sbr.name,
            sbr.date,
            sbr.org_lot_id,
            sbr.polish_lot_id,
            sbr.department,
            sbr.tension_type_data_field  AS tension_type,
            sbr.org_plan_value,
            sbr.breaking_amount,
            sbr.breaking_percent,
            sbr.stone_fault,
            sbr.worker_fault,
            sbr.result,
            sbr.checked,
            sbr.reported_by
        FROM `tabStone Breaking Report` sbr
        {worker_join}
        WHERE {where}
        ORDER BY sbr.date DESC, sbr.name DESC
        """.format(worker_join=worker_join, where=where),
        values,
        as_dict=True,
    )

    if not rows:
        return [], []

    # Fetch worker names for each document in one query
    doc_names = [r.name for r in rows]
    worker_rows = frappe.db.sql(
        """
        SELECT parent, worker_name, worker_type, breaking_amount
        FROM `tabStone Breaking Worker`
        WHERE parent IN %(names)s AND parenttype = 'Stone Breaking Report'
        ORDER BY parent, idx
        """,
        {"names": tuple(doc_names)},
        as_dict=True,
    )
    workers_by_doc = {}
    for w in worker_rows:
        workers_by_doc.setdefault(w.parent, []).append(w)

    # Assemble report rows
    data = []
    total_breaking = 0.0
    total_plan = 0.0
    incident_count = len(rows)
    stone_fault_count = 0
    worker_fault_count = 0

    for r in rows:
        doc_workers = workers_by_doc.get(r.name, [])
        worker_summary = ", ".join(
            "{} ({})".format(w.worker_name, w.worker_type) for w in doc_workers
        )
        high_pct = flt(r.breaking_percent) >= 10.0
        data.append({
            "date":             str(r.date),
            "name":             r.name,
            "org_lot_id":       r.org_lot_id or "",
            "polish_lot_id":    r.polish_lot_id or "",
            "department":       r.department or "",
            "tension_type":     (r.tension_type or "").upper(),
            "org_plan_value":   flt(r.org_plan_value),
            "breaking_amount":  flt(r.breaking_amount),
            "breaking_percent": flt(r.breaking_percent),
            "stone_fault":      int(r.stone_fault or 0),
            "worker_fault":     int(r.worker_fault or 0),
            "result":           r.result or "",
            "checked":          int(r.checked or 0),
            "reported_by":      r.reported_by or "",
            "workers":          worker_summary,
            "tally":            0 if high_pct else 1,
        })
        total_breaking += flt(r.breaking_amount)
        total_plan     += flt(r.org_plan_value)
        if r.stone_fault:
            stone_fault_count += 1
        if r.worker_fault:
            worker_fault_count += 1

    avg_pct = (total_breaking / total_plan * 100) if total_plan else 0.0

    summary = [
        {"value": incident_count,              "label": "Incidents",          "datatype": "Int",      "color": "blue"},
        {"value": round(total_breaking, 2),    "label": "Total Breaking Amnt","datatype": "Float",    "color": "orange"},
        {"value": round(avg_pct, 2),           "label": "Avg Breaking %",     "datatype": "Percent",  "color": "red" if avg_pct >= 10 else "green"},
        {"value": stone_fault_count,           "label": "Stone Faults",       "datatype": "Int",      "color": "purple"},
        {"value": worker_fault_count,          "label": "Worker Faults",      "datatype": "Int",      "color": "purple"},
    ]

    return data, summary
