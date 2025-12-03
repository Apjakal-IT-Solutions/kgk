# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Migration Rollback Mechanism
Provides safe rollback for failed migrations
"""

import frappe
from frappe.utils import now_datetime
import json
import os


class MigrationRollback:
	"""Handle migration rollback operations"""
	
	def __init__(self, migration_log_file=None):
		"""
		Initialize rollback manager
		
		Args:
			migration_log_file: Path to migration log JSON file
		"""
		self.migration_log_file = migration_log_file
		self.migration_data = None
		self.rollback_log = []
	
	def load_migration_log(self):
		"""Load migration log from file"""
		if not self.migration_log_file or not os.path.exists(self.migration_log_file):
			raise FileNotFoundError(f"Migration log file not found: {self.migration_log_file}")
		
		with open(self.migration_log_file, 'r') as f:
			self.migration_data = json.load(f)
		
		return self.migration_data
	
	def create_backup(self, doctype, filters=None):
		"""
		Create backup of documents before rollback
		
		Args:
			doctype: DocType to backup
			filters: Optional filters for backup
			
		Returns:
			str: Backup file path
		"""
		timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
		backup_file = f"migration_backup_{doctype.replace(' ', '_')}_{timestamp}.json"
		
		# Get documents
		docs = frappe.get_all(
			doctype,
			filters=filters or {},
			fields=["*"]
		)
		
		# Save to file
		with open(backup_file, 'w') as f:
			json.dump(docs, f, indent=2, default=str)
		
		print(f"Backup created: {backup_file} ({len(docs)} documents)")
		return backup_file
	
	def rollback_documents(self, dry_run=False):
		"""
		Rollback migrated Cash Documents
		
		Args:
			dry_run: If True, simulate rollback
			
		Returns:
			dict: Rollback statistics
		"""
		if not self.migration_data:
			self.load_migration_log()
		
		migration_log = self.migration_data.get("migration_log", [])
		
		stats = {
			"total": len(migration_log),
			"success": 0,
			"failed": 0,
			"skipped": 0
		}
		
		print(f"\n{'='*60}")
		print(f"Starting rollback of {stats['total']} documents")
		print(f"Dry run: {dry_run}")
		print(f"{'='*60}\n")
		
		# Create backup before rollback
		if not dry_run:
			backup_file = self.create_backup(
				"Cash Document",
				{"migration_reference": ["!=", ""]}
			)
			print(f"Backup created: {backup_file}\n")
		
		for idx, entry in enumerate(migration_log, 1):
			frappe_name = entry.get("frappe_name")
			django_id = entry.get("django_id")
			
			try:
				# Check if document exists
				if not frappe.db.exists("Cash Document", frappe_name):
					print(f"[{idx}/{stats['total']}] SKIP: {frappe_name} (not found)")
					stats["skipped"] += 1
					continue
				
				if dry_run:
					print(f"[{idx}/{stats['total']}] DRY RUN: Would delete {frappe_name}")
					stats["success"] += 1
				else:
					# Delete document
					frappe.delete_doc("Cash Document", frappe_name, force=True, ignore_permissions=True)
					print(f"[{idx}/{stats['total']}] DELETED: {frappe_name} (Django ID: {django_id})")
					stats["success"] += 1
					
					self.rollback_log.append({
						"frappe_name": frappe_name,
						"django_id": django_id,
						"action": "deleted",
						"timestamp": now_datetime()
					})
					
					# Commit every 100 records
					if idx % 100 == 0:
						frappe.db.commit()
						print(f"\n--- Committed {idx} deletions ---\n")
			
			except Exception as e:
				print(f"[{idx}/{stats['total']}] ERROR: {frappe_name} - {str(e)}")
				stats["failed"] += 1
		
		# Final commit
		if not dry_run:
			frappe.db.commit()
		
		print(f"\n{'='*60}")
		print(f"Rollback Summary:")
		print(f"  Total:   {stats['total']}")
		print(f"  Deleted: {stats['success']}")
		print(f"  Failed:  {stats['failed']}")
		print(f"  Skipped: {stats['skipped']}")
		print(f"{'='*60}\n")
		
		return stats
	
	def rollback_balances(self, dry_run=False):
		"""
		Rollback migrated Daily Cash Balances
		
		Args:
			dry_run: If True, simulate rollback
			
		Returns:
			dict: Rollback statistics
		"""
		stats = {
			"total": 0,
			"success": 0,
			"failed": 0
		}
		
		print(f"\n{'='*60}")
		print(f"Rolling back Daily Cash Balances")
		print(f"{'='*60}\n")
		
		# Create backup
		if not dry_run:
			backup_file = self.create_backup(
				"Daily Cash Balance",
				{"status": "Migrated"}
			)
		
		# Get migrated balances
		migrated_balances = frappe.get_all(
			"Daily Cash Balance",
			filters={"status": "Migrated"},
			fields=["name"]
		)
		
		stats["total"] = len(migrated_balances)
		
		for idx, balance in enumerate(migrated_balances, 1):
			try:
				if dry_run:
					print(f"[{idx}/{stats['total']}] DRY RUN: Would delete {balance.name}")
					stats["success"] += 1
				else:
					frappe.delete_doc("Daily Cash Balance", balance.name, force=True, ignore_permissions=True)
					print(f"[{idx}/{stats['total']}] DELETED: {balance.name}")
					stats["success"] += 1
					
					if idx % 50 == 0:
						frappe.db.commit()
			
			except Exception as e:
				print(f"[{idx}/{stats['total']}] ERROR: {balance.name} - {str(e)}")
				stats["failed"] += 1
		
		if not dry_run:
			frappe.db.commit()
		
		print(f"\nBalance Rollback Summary: Deleted={stats['success']}, Failed={stats['failed']}\n")
		return stats
	
	def rollback_bank_entries(self, dry_run=False):
		"""
		Rollback migrated Bank Basic Entries
		
		Args:
			dry_run: If True, simulate rollback
			
		Returns:
			dict: Rollback statistics
		"""
		stats = {
			"total": 0,
			"success": 0,
			"failed": 0
		}
		
		print(f"\n{'='*60}")
		print(f"Rolling back Bank Basic Entries")
		print(f"{'='*60}\n")
		
		# Create backup
		if not dry_run:
			backup_file = self.create_backup(
				"Bank Basic Entry",
				{"verified": 0}  # Unverified entries are likely migrated
			)
		
		# Get unverified entries (assumed to be migrated)
		migrated_entries = frappe.get_all(
			"Bank Basic Entry",
			filters={"verified": 0},
			fields=["name"]
		)
		
		stats["total"] = len(migrated_entries)
		
		for idx, entry in enumerate(migrated_entries, 1):
			try:
				if dry_run:
					print(f"[{idx}/{stats['total']}] DRY RUN: Would delete {entry.name}")
					stats["success"] += 1
				else:
					frappe.delete_doc("Bank Basic Entry", entry.name, force=True, ignore_permissions=True)
					print(f"[{idx}/{stats['total']}] DELETED: {entry.name}")
					stats["success"] += 1
					
					if idx % 50 == 0:
						frappe.db.commit()
			
			except Exception as e:
				print(f"[{idx}/{stats['total']}] ERROR: {entry.name} - {str(e)}")
				stats["failed"] += 1
		
		if not dry_run:
			frappe.db.commit()
		
		print(f"\nBank Entry Rollback Summary: Deleted={stats['success']}, Failed={stats['failed']}\n")
		return stats
	
	def rollback_all(self, dry_run=False):
		"""
		Rollback all migrated data
		
		Args:
			dry_run: If True, simulate rollback
			
		Returns:
			dict: Combined rollback statistics
		"""
		print(f"\n{'='*60}")
		print(f"FULL MIGRATION ROLLBACK")
		print(f"{'='*60}\n")
		
		results = {}
		
		# Rollback documents
		results["documents"] = self.rollback_documents(dry_run)
		
		# Rollback balances
		results["balances"] = self.rollback_balances(dry_run)
		
		# Rollback bank entries
		results["bank_entries"] = self.rollback_bank_entries(dry_run)
		
		# Export rollback log
		if not dry_run:
			self.export_rollback_log()
		
		return results
	
	def export_rollback_log(self, filepath="rollback_log.json"):
		"""Export rollback log to file"""
		with open(filepath, 'w') as f:
			json.dump({
				"rollback_log": self.rollback_log,
				"timestamp": str(now_datetime())
			}, f, indent=2, default=str)
		
		print(f"\nRollback log exported to: {filepath}")


def main():
	"""Main rollback entry point"""
	import argparse
	
	parser = argparse.ArgumentParser(description="Rollback cash management migration")
	parser.add_argument("--site", required=True, help="Frappe site name")
	parser.add_argument("--log-file", required=True, help="Path to migration_log.json")
	parser.add_argument("--dry-run", action="store_true", help="Simulate rollback")
	parser.add_argument("--type", choices=["documents", "balances", "bank", "all"], default="all",
	                   help="Type of data to rollback")
	
	args = parser.parse_args()
	
	# Initialize Frappe
	frappe.init(site=args.site)
	frappe.connect()
	
	# Initialize rollback
	rollback = MigrationRollback(migration_log_file=args.log_file)
	
	# Perform rollback
	if args.type == "documents":
		rollback.rollback_documents(dry_run=args.dry_run)
	elif args.type == "balances":
		rollback.rollback_balances(dry_run=args.dry_run)
	elif args.type == "bank":
		rollback.rollback_bank_entries(dry_run=args.dry_run)
	elif args.type == "all":
		rollback.rollback_all(dry_run=args.dry_run)


if __name__ == "__main__":
	main()
