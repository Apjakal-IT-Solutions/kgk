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
        {"fieldname": "laser_date",          "label": "Date",              "fieldtype": "Date",    "width": 100},
        {"fieldname": "name",                "label": "Document",          "fieldtype": "Link",    "options": "Laser Approval", "width": 160},
        {"fieldname": "org_lot_id",          "label": "ORG Lot ID",        "fieldtype": "Data",    "width": 130},
        {"fieldname": "polish_lot_id",       "label": "Polish Lot ID",     "fieldtype": "Data",    "width": 130},
        {"fieldname": "tension_type",        "label": "Tension",           "fieldtype": "Data",    "width": 75},
        {"fieldname": "plan_change_type",    "label": "Plan Change",       "fieldtype": "Data",    "width": 110},
        {"fieldname": "sawing_from",         "label": "Sawing From",       "fieldtype": "Data",    "width": 100},
        {"fieldname": "micron_safe",         "label": "Micron Safe",       "fieldtype": "Data",    "width": 90},
        {"fieldname": "org_plan_value",      "label": "Plan Value",        "fieldtype": "Float",   "width": 100, "precision": 2},
        {"fieldname": "safe_sawing_amount",  "label": "Safe Saw. Amnt.",   "fieldtype": "Float",   "width": 110, "precision": 2},
        {"fieldname": "safe_sawing_percent", "label": "Safe Saw. %",       "fieldtype": "Float",   "width": 90,  "precision": 2},
        {"fieldname": "nols_amount",         "label": "No LS Amnt.",       "fieldtype": "Float",   "width": 100, "precision": 2},
        {"fieldname": "nols_percent",        "label": "No LS %",           "fieldtype": "Float",   "width": 80,  "precision": 2},
        {"fieldname": "safe_sawing",         "label": "Safe Saw.",         "fieldtype": "Check",   "width": 80},
        {"fieldname": "no_ls",               "label": "No LS",             "fieldtype": "Check",   "width": 65},
        {"fieldname": "normal_sawing",       "label": "Normal Saw.",       "fieldtype": "Check",   "width": 90},
        {"fieldname": "result",              "label": "Result",            "fieldtype": "Data",    "width": 120},
        {"fieldname": "flag",                "label": "Flag",              "fieldtype": "Data",    "width": 80},
        {"fieldname": "checked_",            "label": "Checked",           "fieldtype": "Check",   "width": 75},
        {"fieldname": "docstatus",           "label": "Status",            "fieldtype": "Data",    "width": 80},
        {"fieldname": "users",               "label": "Users",             "fieldtype": "Data",    "width": 200},
        {"fieldname": "remarks",             "label": "Remarks",           "fieldtype": "Data",    "width": 200},
        {"fieldname": "_tally",              "label": "_tally",            "fieldtype": "Int",     "hidden": 1},
    ]


def _build_filters(filters):
    conditions = ["la.docstatus < 2"]
    values = {}

    if filters.get("date_from"):
        conditions.append("la.laser_date >= %(date_from)s")
        values["date_from"] = filters["date_from"]
    if filters.get("date_to"):
        conditions.append("la.laser_date <= %(date_to)s")
        values["date_to"] = filters["date_to"]
    if filters.get("tension_type"):
        conditions.append("la.tension_type = %(tension_type)s")
        values["tension_type"] = filters["tension_type"]
    if filters.get("plan_change_type"):
        conditions.append("la.plan_change_type = %(plan_change_type)s")
        values["plan_change_type"] = filters["plan_change_type"]
    if filters.get("sawing_from"):
        conditions.append("la.sawing_from = %(sawing_from)s")
        values["sawing_from"] = filters["sawing_from"]
    if filters.get("approval_type") == "Safe Sawing":
        conditions.append("la.safe_sawing = 1")
    elif filters.get("approval_type") == "No LS":
        conditions.append("la.no_ls = 1")
    elif filters.get("approval_type") == "Normal Sawing":
        conditions.append("la.normal_sawing = 1")
    elif filters.get("approval_type") == "Any Approved":
        conditions.append("(la.safe_sawing = 1 OR la.no_ls = 1 OR la.normal_sawing = 1)")
    elif filters.get("approval_type") == "Not Approved":
        conditions.append("la.safe_sawing = 0 AND la.no_ls = 0 AND la.normal_sawing = 0")
    if filters.get("flag"):
        conditions.append("la.flag LIKE %(flag)s")
        values["flag"] = "%{}%".format(filters["flag"])
    if filters.get("result"):
        conditions.append("la.result LIKE %(result)s")
        values["result"] = "%{}%".format(filters["result"])
    if filters.get("checked") == "Checked":
        conditions.append("la.checked_ = 1")
    elif filters.get("checked") == "Unchecked":
        conditions.append("la.checked_ = 0")
    if filters.get("docstatus") == "Draft":
        conditions.append("la.docstatus = 0")
    elif filters.get("docstatus") == "Submitted":
        conditions.append("la.docstatus = 1")
    if filters.get("min_safe_sawing_pct"):
        conditions.append("la.safe_sawing_percent >= %(min_ss_pct)s")
        values["min_ss_pct"] = flt(filters["min_safe_sawing_pct"])
    if filters.get("max_safe_sawing_pct"):
        conditions.append("la.safe_sawing_percent <= %(max_ss_pct)s")
        values["max_ss_pct"] = flt(filters["max_safe_sawing_pct"])

    return " AND ".join(conditions), values


def _get_data(filters):
    where, values = _build_filters(filters)

    # Employee sub-filter via child table join
    user_join = ""
    if filters.get("employee") or filters.get("employee_status"):
        user_join = (
            "INNER JOIN `tabLaser Approval User` lau "
            "ON lau.parent = la.name AND lau.parenttype = 'Laser Approval'"
        )
        if filters.get("employee"):
            where += " AND lau.employee_name LIKE %(employee)s"
            values["employee"] = "%{}%".format(filters["employee"])
        if filters.get("employee_status"):
            where += " AND lau.status = %(emp_status)s"
            values["emp_status"] = filters["employee_status"]

    rows = frappe.db.sql(
        """
        SELECT DISTINCT
            la.name,
            la.laser_date,
            la.org_lot_id,
            la.polish_lot_id,
            la.tension_type,
            la.plan_change_type,
            la.sawing_from,
            la.micron_safe,
            la.org_plan_value,
            la.safe_sawing_amount,
            la.safe_sawing_percent,
            la.nols_amount,
            la.nols_percent,
            la.safe_sawing,
            la.no_ls,
            la.normal_sawing,
            la.result,
            la.flag,
            la.checked_,
            la.docstatus
        FROM `tabLaser Approval` la
        {user_join}
        WHERE {where}
        ORDER BY la.laser_date DESC, la.name DESC
        """.format(user_join=user_join, where=where),
        values,
        as_dict=True,
    )

    if not rows:
        return [], []

    doc_names = [r.name for r in rows]

    # Fetch users in one query
    user_rows = frappe.db.sql(
        """
        SELECT parent, employee_name, status
        FROM `tabLaser Approval User`
        WHERE parent IN %(names)s AND parenttype = 'Laser Approval'
        ORDER BY parent, idx
        """,
        {"names": tuple(doc_names)},
        as_dict=True,
    )
    users_by_doc = {}
    for u in user_rows:
        users_by_doc.setdefault(u.parent, []).append(u)

    # Fetch remarks in one query
    remark_rows = frappe.db.sql(
        """
        SELECT parent, auto_remark, manual_remark
        FROM `tabLaser Approval Remark`
        WHERE parent IN %(names)s AND parenttype = 'Laser Approval'
        ORDER BY parent, idx
        """,
        {"names": tuple(doc_names)},
        as_dict=True,
    )
    remarks_by_doc = {}
    for rm in remark_rows:
        remarks_by_doc.setdefault(rm.parent, []).append(rm)

    _status_label = {0: "Draft", 1: "Submitted", 2: "Cancelled"}

    data = []
    total_docs     = len(rows)
    submitted      = 0
    safe_saw_count = 0
    nols_count     = 0
    normal_count   = 0
    total_ss_pct   = 0.0

    for r in rows:
        doc_users = users_by_doc.get(r.name, [])
        user_summary = ", ".join(
            "{} ({})".format(u.employee_name, u.status or "-") for u in doc_users
        )

        doc_remarks = remarks_by_doc.get(r.name, [])
        remark_parts = []
        for rm in doc_remarks:
            parts = [p for p in [rm.auto_remark, rm.manual_remark] if p]
            if parts:
                remark_parts.append(" / ".join(parts))
        remark_summary = "; ".join(remark_parts)

        ss_pct = flt(r.safe_sawing_percent)
        high_loss = ss_pct >= 5.0

        if r.docstatus == 1:
            submitted += 1
        if r.safe_sawing:
            safe_saw_count += 1
        if r.no_ls:
            nols_count += 1
        if r.normal_sawing:
            normal_count += 1
        total_ss_pct += ss_pct

        data.append({
            "laser_date":          str(r.laser_date),
            "name":                r.name,
            "org_lot_id":          r.org_lot_id or "",
            "polish_lot_id":       r.polish_lot_id or "",
            "tension_type":        r.tension_type or "",
            "plan_change_type":    r.plan_change_type or "",
            "sawing_from":         r.sawing_from or "",
            "micron_safe":         r.micron_safe or "",
            "org_plan_value":      flt(r.org_plan_value),
            "safe_sawing_amount":  flt(r.safe_sawing_amount),
            "safe_sawing_percent": ss_pct,
            "nols_amount":         flt(r.nols_amount),
            "nols_percent":        flt(r.nols_percent),
            "safe_sawing":         int(r.safe_sawing or 0),
            "no_ls":               int(r.no_ls or 0),
            "normal_sawing":       int(r.normal_sawing or 0),
            "result":              r.result or "",
            "flag":                r.flag or "",
            "checked_":            int(r.checked_ or 0),
            "docstatus":           _status_label.get(r.docstatus, ""),
            "users":               user_summary,
            "remarks":             remark_summary,
            "_tally":              0 if high_loss else 1,
        })

    avg_ss_pct = total_ss_pct / total_docs if total_docs else 0.0

    summary = [
        {"value": total_docs,               "label": "Total Records",     "datatype": "Int",     "color": "blue"},
        {"value": submitted,                "label": "Submitted",         "datatype": "Int",     "color": "green"},
        {"value": safe_saw_count,           "label": "Safe Sawing",       "datatype": "Int",     "color": "#1565c0"},
        {"value": nols_count,               "label": "No LS",             "datatype": "Int",     "color": "#6a1571"},
        {"value": normal_count,             "label": "Normal Sawing",     "datatype": "Int",     "color": "#e65100"},
        {"value": round(avg_ss_pct, 2),     "label": "Avg Safe Saw. %",   "datatype": "Percent", "color": "red" if avg_ss_pct >= 5 else "green"},
    ]

    return data, summary
