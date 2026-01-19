# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, now_datetime
from kgk_customisations.kgk_customisations.utils.query_builder import SafeQueryBuilder


def execute(filters=None):
	"""
	Audit Trail Report - Comprehensive compliance and activity tracking
	"""
	if not filters:
		filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def get_columns():
	"""Define audit trail report columns"""
	return [
		{
			"fieldname": "timestamp",
			"label": _("Timestamp"),
			"fieldtype": "Datetime",
			"width": 160
		},
		{
			"fieldname": "activity_type",
			"label": _("Activity Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150
		},
		{
			"fieldname": "document_type",
			"label": _("Document Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "document_name",
			"label": _("Document"),
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 150
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 130
		},
		{
			"fieldname": "old_value",
			"label": _("Old Value"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "new_value",
			"label": _("New Value"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "details",
			"label": _("Details"),
			"fieldtype": "Text",
			"width": 250
		},
		{
			"fieldname": "ip_address",
			"label": _("IP Address"),
			"fieldtype": "Data",
			"width": 120
		}
	]


def get_data(filters):
	"""Fetch audit trail data from Cash Document Audit Trail"""
	query = """
		SELECT
			cat.timestamp,
			cat.activity_type,
			cat.user,
			cat.document_type,
			cat.document_name,
			cat.company,
			cat.old_value,
			cat.new_value,
			cat.details,
			cat.ip_address
		FROM `tabCash Document Audit Trail` cat
	"""
	
	# Build WHERE conditions safely
	conditions = []
	params = {}
	
	if filters.get("from_date"):
		conditions.append("DATE(cat.timestamp) >= %(from_date)s")
		params["from_date"] = filters.get("from_date")
	
	if filters.get("to_date"):
		conditions.append("DATE(cat.timestamp) <= %(to_date)s")
		params["to_date"] = filters.get("to_date")
	
	if filters.get("activity_type") and filters.get("activity_type") != "All":
		conditions.append("cat.activity_type = %(activity_type)s")
		params["activity_type"] = filters.get("activity_type")
	
	if filters.get("user"):
		conditions.append("cat.user = %(user)s")
		params["user"] = filters.get("user")
	
	if filters.get("document_type") and filters.get("document_type") != "All":
		conditions.append("cat.document_type = %(document_type)s")
		params["document_type"] = filters.get("document_type")
	
	if filters.get("company"):
		conditions.append("cat.company = %(company)s")
		params["company"] = filters.get("company")
	
	if conditions:
		query += " WHERE " + " AND ".join(conditions)
	
	query += " ORDER BY cat.timestamp DESC"
	
	data = frappe.db.sql(query, params, as_dict=1)
	
	# Apply text search filter if provided
	search_text = filters.get("search_text")
	if search_text:
		search_text = search_text.lower()
		data = [
			row for row in data
			if search_text in (row.get("details") or "").lower()
			or search_text in (row.get("old_value") or "").lower()
			or search_text in (row.get("new_value") or "").lower()
		]
	
	return data


def get_conditions(filters):
	"""Build SQL WHERE conditions"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("DATE(cat.timestamp) >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("DATE(cat.timestamp) <= %(to_date)s")
	
	if filters.get("activity_type") and filters.get("activity_type") != "All":
		conditions.append("cat.activity_type = %(activity_type)s")
	
	if filters.get("user"):
		conditions.append("cat.user = %(user)s")
	
	if filters.get("document_type") and filters.get("document_type") != "All":
		conditions.append("cat.document_type = %(document_type)s")
	
	if filters.get("company"):
		conditions.append("cat.company = %(company)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


@frappe.whitelist()
def export_audit_report(filters):
	"""
	Export comprehensive audit report for external auditors
	Includes additional metadata and formatting
	"""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
	
	columns, data = execute(filters)
	
	# Add summary statistics
	summary = {
		"total_activities": len(data),
		"unique_users": len(set(row.get("user") for row in data if row.get("user"))),
		"date_range": f"{filters.get('from_date')} to {filters.get('to_date')}",
		"activity_breakdown": {}
	}
	
	# Count by activity type
	for row in data:
		activity = row.get("activity_type", "Unknown")
		summary["activity_breakdown"][activity] = summary["activity_breakdown"].get(activity, 0) + 1
	
	return {
		"summary": summary,
		"data": data,
		"columns": columns
	}


@frappe.whitelist()
def get_user_activity_stats(user, from_date=None, to_date=None):
	"""Get detailed activity statistics for a specific user"""
	query = """
		SELECT
			cat.activity_type,
			COUNT(*) as count,
			MIN(cat.timestamp) as first_activity,
			MAX(cat.timestamp) as last_activity,
			COUNT(DISTINCT cat.document_name) as unique_documents
		FROM `tabCash Document Audit Trail` cat
		WHERE cat.user = %(user)s
	"""
	
	params = {"user": user}
	
	if from_date:
		query += " AND DATE(cat.timestamp) >= %(from_date)s"
		params["from_date"] = from_date
	
	if to_date:
		query += " AND DATE(cat.timestamp) <= %(to_date)s"
		params["to_date"] = to_date
	
	query += """
		GROUP BY cat.activity_type
		ORDER BY count DESC
	"""
	
	stats = frappe.db.sql(query, params, as_dict=1)
	
	return stats


@frappe.whitelist()
def check_compliance_issues(from_date, to_date, company=None):
	"""
	Run automated compliance checks on audit trail
	Returns list of potential compliance issues
	"""
	issues = []
	
	filters = {
		"from_date": from_date,
		"to_date": to_date
	}
	
	if company:
		filters["company"] = company
	
	columns, data = execute(filters)
	
	# Check 1: Documents modified after verification
	verified_docs = {}
	for row in data:
		if row.get("activity_type") in ["Manual Verification", "ERP Verification", "Final Verification"]:
			doc_key = f"{row.get('document_type')}::{row.get('document_name')}"
			if doc_key not in verified_docs or row.get("timestamp") > verified_docs[doc_key]:
				verified_docs[doc_key] = row.get("timestamp")
	
	for row in data:
		if row.get("activity_type") == "Document Modification":
			doc_key = f"{row.get('document_type')}::{row.get('document_name')}"
			if doc_key in verified_docs and row.get("timestamp") > verified_docs[doc_key]:
				issues.append({
					"type": "Modification After Verification",
					"severity": "High",
					"document": row.get("document_name"),
					"details": f"Document modified at {row.get('timestamp')} after verification at {verified_docs[doc_key]}",
					"user": row.get("user")
				})
	
	# Check 2: Excessive cancellations by single user
	cancellation_count = {}
	for row in data:
		if row.get("activity_type") == "Document Cancellation":
			user = row.get("user", "Unknown")
			cancellation_count[user] = cancellation_count.get(user, 0) + 1
	
	for user, count in cancellation_count.items():
		if count > 10:  # Threshold
			issues.append({
				"type": "Excessive Cancellations",
				"severity": "Medium",
				"user": user,
				"details": f"User has {count} document cancellations in the period",
				"document": None
			})
	
	# Check 3: Balance updates without subsequent verification
	balance_updates = [row for row in data if row.get("activity_type") == "Balance Update"]
	verifications = [row for row in data if "Verification" in row.get("activity_type", "")]
	
	if len(balance_updates) > 0:
		verification_ratio = len(verifications) / len(balance_updates)
		if verification_ratio < 0.5:  # Less than 50% verified
			issues.append({
				"type": "Low Verification Rate",
				"severity": "High",
				"details": f"Only {verification_ratio*100:.1f}% of balance updates are verified ({len(verifications)}/{len(balance_updates)})",
				"user": None,
				"document": None
			})
	
	# Check 4: Activities outside business hours
	for row in data:
		timestamp = get_datetime(row.get("timestamp"))
		hour = timestamp.hour
		
		if hour < 6 or hour > 22:  # Outside 6 AM - 10 PM
			issues.append({
				"type": "Off-Hours Activity",
				"severity": "Low",
				"document": row.get("document_name"),
				"details": f"Activity at {timestamp.strftime('%Y-%m-%d %H:%M:%S')} (hour: {hour})",
				"user": row.get("user")
			})
	
	return issues
