#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django to Frappe Migration Script for Cash Management System
Migrates data from Django cash.models to Frappe Cash Document
"""

import os
import sys
import django
import frappe
from frappe.utils import getdate, now_datetime
from datetime import datetime
import json

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cashproject.settings")
django.setup()

from cash.models import Document, CashBalance, BankBasicEntry, Flag, InvoiceNumber


class DjangoToFrappeMigration:
	"""Handles migration from Django to Frappe"""
	
	def __init__(self, frappe_site=None):
		"""
		Initialize migration
		
		Args:
			frappe_site: Site name for Frappe (e.g., 'kgkerp.local')
		"""
		self.frappe_site = frappe_site
		self.migration_log = []
		self.error_log = []
		
	def connect_frappe(self):
		"""Connect to Frappe site"""
		if self.frappe_site:
			frappe.init(site=self.frappe_site)
			frappe.connect()
			return True
		return False
	
	def field_mapping(self, django_doc):
		"""
		Map Django Document fields to Frappe Cash Document fields
		
		Args:
			django_doc: Django Document object
			
		Returns:
			dict: Mapped fields for Frappe
		"""
		# Map main_type to main_document_type
		main_type_mapping = {
			"Payment": "Payment",
			"Receipt": "Receipt",
			"Invoice": "Invoice",
			"Petty Cash": "Petty Cash"
		}
		
		# Map status
		status_mapping = {
			"pending": "Pending Review",
			"final": "Approved",
			"final2": "Processed",
			"draft": "Draft"
		}
		
		return {
			"doctype": "Cash Document",
			"company": django_doc.company or "KGK",
			"transaction_date": getdate(django_doc.date) if django_doc.date else getdate(),
			"year": int(django_doc.year) if django_doc.year else datetime.now().year,
			"main_document_type": main_type_mapping.get(django_doc.main_type, "Receipt"),
			"sub_document_type": django_doc.sub_type or "",
			"primary_document_file": django_doc.file_name or "",
			"amount": 0,  # Django doesn't store amount separately
			"status": status_mapping.get(django_doc.status, "Draft"),
			"created_by_user": django_doc.created_by or "Administrator",
			"description": f"Migrated from Django - Original unique_number: {django_doc.unique_number}",
			"migration_reference": django_doc.unique_number,  # Store original ID
		}
	
	def migrate_documents(self, limit=None, dry_run=False):
		"""
		Migrate Django Documents to Frappe Cash Documents
		
		Args:
			limit: Maximum number of documents to migrate (None for all)
			dry_run: If True, simulate migration without saving
			
		Returns:
			dict: Migration statistics
		"""
		stats = {
			"total": 0,
			"success": 0,
			"failed": 0,
			"skipped": 0
		}
		
		# Get Django documents
		django_docs = Document.objects.all()
		if limit:
			django_docs = django_docs[:limit]
		
		stats["total"] = django_docs.count()
		
		print(f"\n{'='*60}")
		print(f"Starting migration of {stats['total']} documents")
		print(f"Dry run: {dry_run}")
		print(f"{'='*60}\n")
		
		for idx, django_doc in enumerate(django_docs, 1):
			try:
				# Check if already migrated
				existing = frappe.db.exists(
					"Cash Document",
					{"migration_reference": django_doc.unique_number}
				)
				
				if existing:
					print(f"[{idx}/{stats['total']}] SKIP: {django_doc.unique_number} (already migrated)")
					stats["skipped"] += 1
					continue
				
				# Map fields
				frappe_data = self.field_mapping(django_doc)
				
				if dry_run:
					print(f"[{idx}/{stats['total']}] DRY RUN: Would migrate {django_doc.unique_number}")
					print(f"  → {json.dumps(frappe_data, indent=2, default=str)}")
					stats["success"] += 1
				else:
					# Create Frappe document
					frappe_doc = frappe.get_doc(frappe_data)
					frappe_doc.flags.ignore_validate = True  # Skip validation for migration
					frappe_doc.insert(ignore_permissions=True)
					
					print(f"[{idx}/{stats['total']}] SUCCESS: {django_doc.unique_number} → {frappe_doc.name}")
					stats["success"] += 1
					
					self.migration_log.append({
						"django_id": django_doc.unique_number,
						"frappe_name": frappe_doc.name,
						"timestamp": now_datetime()
					})
					
					# Commit every 100 records
					if idx % 100 == 0:
						frappe.db.commit()
						print(f"\n--- Committed {idx} records ---\n")
			
			except Exception as e:
				print(f"[{idx}/{stats['total']}] ERROR: {django_doc.unique_number} - {str(e)}")
				stats["failed"] += 1
				
				self.error_log.append({
					"django_id": django_doc.unique_number,
					"error": str(e),
					"timestamp": now_datetime()
				})
		
		# Final commit
		if not dry_run:
			frappe.db.commit()
		
		print(f"\n{'='*60}")
		print(f"Migration Summary:")
		print(f"  Total:   {stats['total']}")
		print(f"  Success: {stats['success']}")
		print(f"  Failed:  {stats['failed']}")
		print(f"  Skipped: {stats['skipped']}")
		print(f"{'='*60}\n")
		
		return stats
	
	def migrate_cash_balances(self, limit=None, dry_run=False):
		"""
		Migrate Django CashBalance to Frappe Daily Cash Balance
		
		Args:
			limit: Maximum number of balances to migrate
			dry_run: If True, simulate migration
			
		Returns:
			dict: Migration statistics
		"""
		stats = {
			"total": 0,
			"success": 0,
			"failed": 0,
			"skipped": 0
		}
		
		# Get Django cash balances
		django_balances = CashBalance.objects.all()
		if limit:
			django_balances = django_balances[:limit]
		
		stats["total"] = django_balances.count()
		
		print(f"\n{'='*60}")
		print(f"Starting migration of {stats['total']} cash balances")
		print(f"{'='*60}\n")
		
		for idx, django_bal in enumerate(django_balances, 1):
			try:
				# Check if already exists
				existing = frappe.db.exists(
					"Daily Cash Balance",
					{
						"balance_date": getdate(django_bal.date),
						"company": django_bal.company
					}
				)
				
				if existing:
					print(f"[{idx}/{stats['total']}] SKIP: {django_bal.date} - {django_bal.company}")
					stats["skipped"] += 1
					continue
				
				if dry_run:
					print(f"[{idx}/{stats['total']}] DRY RUN: Would migrate {django_bal.date} - {django_bal.company}")
					stats["success"] += 1
				else:
					# Create Daily Cash Balance
					balance_doc = frappe.get_doc({
						"doctype": "Daily Cash Balance",
						"balance_date": getdate(django_bal.date),
						"company": django_bal.company,
						"basic_user_balance": django_bal.basic or 0,
						"accountant_balance": django_bal.accountant or 0,
						"status": "Migrated"
					})
					
					balance_doc.insert(ignore_permissions=True)
					print(f"[{idx}/{stats['total']}] SUCCESS: {django_bal.date} - {django_bal.company} → {balance_doc.name}")
					stats["success"] += 1
					
					if idx % 50 == 0:
						frappe.db.commit()
			
			except Exception as e:
				print(f"[{idx}/{stats['total']}] ERROR: {django_bal.date} - {str(e)}")
				stats["failed"] += 1
		
		if not dry_run:
			frappe.db.commit()
		
		print(f"\nBalance Migration Summary: Success={stats['success']}, Failed={stats['failed']}, Skipped={stats['skipped']}\n")
		return stats
	
	def migrate_bank_entries(self, limit=None, dry_run=False):
		"""
		Migrate Django BankBasicEntry to Frappe Bank Basic Entry
		
		Args:
			limit: Maximum number of entries to migrate
			dry_run: If True, simulate migration
			
		Returns:
			dict: Migration statistics
		"""
		stats = {
			"total": 0,
			"success": 0,
			"failed": 0,
			"skipped": 0
		}
		
		# Get Django bank entries
		django_entries = BankBasicEntry.objects.all()
		if limit:
			django_entries = django_entries[:limit]
		
		stats["total"] = django_entries.count()
		
		print(f"\n{'='*60}")
		print(f"Starting migration of {stats['total']} bank entries")
		print(f"{'='*60}\n")
		
		for idx, django_entry in enumerate(django_entries, 1):
			try:
				# Check if already exists
				existing = frappe.db.exists(
					"Bank Basic Entry",
					{
						"entry_date": getdate(django_entry.date),
						"company": django_entry.company,
						"username": django_entry.username
					}
				)
				
				if existing:
					print(f"[{idx}/{stats['total']}] SKIP: {django_entry.date} - {django_entry.company}")
					stats["skipped"] += 1
					continue
				
				if dry_run:
					print(f"[{idx}/{stats['total']}] DRY RUN: Would migrate {django_entry.date}")
					stats["success"] += 1
				else:
					# Create Bank Basic Entry
					bank_doc = frappe.get_doc({
						"doctype": "Bank Basic Entry",
						"entry_date": getdate(django_entry.date),
						"company": django_entry.company,
						"username": django_entry.username,
						"balance": django_entry.balance or 0,
						"verified": 0
					})
					
					bank_doc.insert(ignore_permissions=True)
					print(f"[{idx}/{stats['total']}] SUCCESS: {django_entry.date} → {bank_doc.name}")
					stats["success"] += 1
					
					if idx % 50 == 0:
						frappe.db.commit()
			
			except Exception as e:
				print(f"[{idx}/{stats['total']}] ERROR: {django_entry.date} - {str(e)}")
				stats["failed"] += 1
		
		if not dry_run:
			frappe.db.commit()
		
		print(f"\nBank Entry Migration Summary: Success={stats['success']}, Failed={stats['failed']}, Skipped={stats['skipped']}\n")
		return stats
	
	def export_migration_log(self, filepath="migration_log.json"):
		"""Export migration log to file"""
		with open(filepath, 'w') as f:
			json.dump({
				"migration_log": self.migration_log,
				"error_log": self.error_log,
				"timestamp": str(now_datetime())
			}, f, indent=2, default=str)
		
		print(f"\nMigration log exported to: {filepath}")


def main():
	"""Main migration entry point"""
	import argparse
	
	parser = argparse.ArgumentParser(description="Migrate Django cash management data to Frappe")
	parser.add_argument("--site", required=True, help="Frappe site name (e.g., kgkerp.local)")
	parser.add_argument("--limit", type=int, help="Limit number of records to migrate")
	parser.add_argument("--dry-run", action="store_true", help="Simulate migration without saving")
	parser.add_argument("--type", choices=["documents", "balances", "bank", "all"], default="all", 
	                   help="Type of data to migrate")
	
	args = parser.parse_args()
	
	# Initialize migration
	migration = DjangoToFrappeMigration(frappe_site=args.site)
	migration.connect_frappe()
	
	# Run migrations based on type
	if args.type in ["documents", "all"]:
		migration.migrate_documents(limit=args.limit, dry_run=args.dry_run)
	
	if args.type in ["balances", "all"]:
		migration.migrate_cash_balances(limit=args.limit, dry_run=args.dry_run)
	
	if args.type in ["bank", "all"]:
		migration.migrate_bank_entries(limit=args.limit, dry_run=args.dry_run)
	
	# Export log
	if not args.dry_run:
		migration.export_migration_log()


if __name__ == "__main__":
	main()
