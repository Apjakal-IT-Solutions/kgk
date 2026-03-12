# Copyright (c) 2026, Apjakal IT Solutions and contributors
# For license information, please see license.txt

import io
import os
import shutil
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate, cint

_MOUNT_BASE = "/mnt/share/e-dox/Documents"


def _url_to_path(url):
	"""Resolve any file URL stored in a Cash Document field to an absolute path.

	Handles three origins:
	  /edox/...          → network mount (legacy migrated documents)
	  /private/files/... → Frappe private upload (new documents)
	  /files/...         → Frappe public upload (new documents)

	Returns None if the URL does not match a known scheme.
	"""
	if not url:
		return None
	if url.startswith("/edox/"):
		return os.path.join(_MOUNT_BASE, url[len("/edox/"):])
	if url.startswith("/private/files/"):
		return frappe.get_site_path("private", "files", url[len("/private/files/"):])
	if url.startswith("/files/"):
		return frappe.get_site_path("public", "files", url[len("/files/"):])
	return None

# Counter field names in the Cash Voucher Series Single DocType
_COUNTER_MAP = {
	"Cash":   "cash_counter",
	"Bank":   "bank_counter",
	"Cash-2": "cash_2_counter",
	"Bank-2": "bank_2_counter",
	"JE":     "je_counter",
}

# Name format strings (one positional placeholder for the counter)
_FORMAT_MAP = {
	"Cash":   "25-{}",
	"Bank":   "B{}",
	"Cash-2": "C2-25-{}",
	"Bank-2": "B2-{}",
	"JE":     "JE{}",
}

# Allowed sub_type values per main_type (empty string means no sub_type is OK)
_VALID_SUB_TYPES = {
	"Cash":   {"Payment", "Receipt"},
	"Bank":   {"Credit Card", "EFT"},
	"Cash-2": {""},
	"Bank-2": {""},
	"JE":     {"JE"},
}

class CashDocument(Document):

	def autoname(self):
		"""Assign a name derived from an atomic per-type counter."""
		main_type = self.main_type
		if main_type not in _COUNTER_MAP:
			frappe.throw(frappe._("Select a Document Type before saving."))

		field = _COUNTER_MAP[main_type]

		# Atomic increment using UPDATE.  tabSingles has no UNIQUE constraint, so
		# INSERT ... ON DUPLICATE KEY UPDATE creates duplicate rows and cannot be used.
		# The counter row is guaranteed to exist (seeded at install time by the patch).
		# InnoDB row-level locking on the UPDATE makes this safe under concurrent access.
		frappe.db.sql(
			"""
			UPDATE `tabSingles`
			SET value = CAST(COALESCE(CAST(value AS UNSIGNED), 0) + 1 AS CHAR)
			WHERE doctype = 'Cash Voucher Series' AND field = %(field)s
			""",
			{"field": field},
		)

		# Read back via raw SQL to bypass Frappe's Single-doctype in-memory cache.
		# InnoDB read-your-own-writes guarantee means we see the updated value
		# within the same transaction.
		result = frappe.db.sql(
			"SELECT value FROM `tabSingles` WHERE doctype='Cash Voucher Series' AND field=%s",
			[field],
		)
		next_num = cint(result[0][0]) if result else 1
		self.name = _FORMAT_MAP[main_type].format(next_num)

	def before_insert(self):
		if not self.system_date:
			self.system_date = now_datetime()
		if self.date:
			self.year = getdate(self.date).year
		if not self.created_by:
			self.created_by = frappe.session.user
		# Set default file_name only when no file is being uploaded at creation time.
		# If main_file is already set (upload at creation), after_save will set the
		# real filename after copying to the mount.
		if self.name and not self.main_file:
			self.file_name = self.name + ".pdf"

	def after_save(self):
		self._move_file_to_mount()
		self._sync_supporting_file_attachments()

	def _sync_supporting_file_attachments(self):
		"""Ensure every supporting file row that has a file_attachment URL also
		has a corresponding Frappe File record linked to the *parent* Cash Document
		(not the child row), so it appears in the sidebar attachment list."""
		if not self.supporting_files:
			return

		existing_urls = {
			r.file_url
			for r in frappe.get_all(
				"File",
				filters={
					"attached_to_doctype": "Cash Document",
					"attached_to_name": self.name,
				},
				fields=["file_url"],
			)
		}

		for row in self.supporting_files:
			url = row.get("file_attachment")
			if not url or url in existing_urls:
				continue
			fname = row.get("file_name") or url.rsplit("/", 1)[-1]
			frappe.db.sql(
				"""INSERT INTO `tabFile`
				    (name, file_name, file_url, attached_to_doctype, attached_to_name,
				     is_private, creation, modified, owner, modified_by, docstatus)
				   VALUES (%s, %s, %s, 'Cash Document', %s, 0,
				           NOW(), NOW(), %s, %s, 0)""",
				(
					frappe.generate_hash(length=10),
					fname, url, self.name,
					frappe.session.user, frappe.session.user,
				),
			)
			existing_urls.add(url)

	def _move_file_to_mount(self):
		"""If main_file points to a Frappe-local file, copy it to the shared
		network mount and update main_file / file_name to the /edox/ URL.

		Frappe uploads the file in a separate request before the document is
		saved, so at after_save time the File record's attached_to_name may
		not yet be committed.  We therefore resolve the disk path directly
		from the URL (via _url_to_path) instead of relying on a File-record
		lookup by attached_to_name.
		"""
		if not self.main_file:
			return
		# Already on the mount — nothing to do.
		if self.main_file.startswith("/edox/"):
			return
		# Only handle Frappe-managed file URLs.
		if not (self.main_file.startswith("/files/") or self.main_file.startswith("/private/files/")):
			return

		try:
			src_path = _url_to_path(self.main_file)
			if not src_path or not os.path.exists(src_path):
				frappe.log_error(
					f"Source not found: {src_path!r} (main_file={self.main_file!r})",
					"Cash Document — file move to mount failed",
				)
				return

			# Always store as {doc.name}.pdf on the mount to match legacy naming.
			filename = self.name + ".pdf"
			dest_dir = os.path.join(_MOUNT_BASE, self.name)
			dest_path = os.path.join(dest_dir, filename)
			os.makedirs(dest_dir, exist_ok=True)
			shutil.copy2(src_path, dest_path)

			original_url = self.main_file   # capture before we overwrite self.main_file
			edox_url = f"/edox/{self.name}/{filename}"
			frappe.db.set_value("Cash Document", self.name, {
				"main_file": edox_url,
				"file_name": filename,
			}, update_modified=False)
			self.main_file = edox_url
			self.file_name = filename

			# Update the Frappe File record URL so the sidebar points to /edox/.
			# Look up by file_url only — attached_to_name may not be committed yet.
			frappe.db.sql(
				"UPDATE `tabFile` SET file_url=%s, file_name=%s WHERE file_url=%s",
				(edox_url, filename, original_url),
			)
			# Remove the local copy — canonical location is now the mount.
			try:
				os.remove(src_path)
			except OSError:
				pass

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Cash Document — file move to mount failed")

	def validate(self):
		# Prevent file attachment if main_type has not been chosen yet.
		# (The attachment widget saves immediately, before the user fills other fields.)
		if self.main_file and self.main_file.startswith(("/files/", "/private/files/")) and not self.main_type:
			frappe.throw(frappe._("Please set the Document Type before attaching a file."))

		if self.main_type:
			valid = _VALID_SUB_TYPES.get(self.main_type, set())
			sub = self.sub_type or ""

			if self.main_type in ("Cash", "Bank") and not sub:
				frappe.throw(
					frappe._("Sub Type is required for {0} documents.").format(self.main_type)
				)
			elif sub and sub not in valid:
				frappe.throw(
					frappe._("Sub Type '{0}' is not valid for {1} documents.").format(
						sub, self.main_type
					)
				)

		if self.date:
			self.year = getdate(self.date).year


# Whitelisted server functions

@frappe.whitelist()
def finalise(doc_name):
	"""Set status to final. Restricted to Cash Accountant / Cash Super User."""
	_require_role(["Cash Accountant", "Cash Super User", "Administrator"])
	doc = frappe.get_doc("Cash Document", doc_name)
	if doc.docstatus != 0:
		frappe.throw(frappe._("Finalise is only allowed on draft (pre-submit) documents."))
	if doc.status == "final":
		frappe.throw(frappe._("Document is already finalised."))
	frappe.db.set_value("Cash Document", doc_name, "status", "final")
	return "final"


@frappe.whitelist()
def finalise2(doc_name):
	"""Set final_status2 to final2. Restricted to Cash Checker / Cash Super User.

	Requires Status 1 to already be 'final' — enforces the two-step approval sequence.
	"""
	_require_role(["Cash Checker", "Cash Super User", "Administrator"])
	doc = frappe.get_doc("Cash Document", doc_name)
	if doc.docstatus != 0:
		frappe.throw(frappe._("Finalise 2 is only allowed on draft (pre-submit) documents."))
	if doc.status != "final":
		frappe.throw(frappe._("Status 1 must be finalised before Status 2 can be set."))
	if doc.final_status2 == "final2":
		frappe.throw(frappe._("Document is already finalised (Status 2)."))
	frappe.db.set_value("Cash Document", doc_name, "final_status2", "final2")
	return "final2"


@frappe.whitelist()
def unfinalise(doc_name):
	"""Reset status back to pending. Restricted to Cash Super User.

	Blocked if Status 2 is already final — must unfinalise Status 2 first.
	"""
	_require_role(["Cash Super User", "Administrator"])
	doc = frappe.get_doc("Cash Document", doc_name)
	if doc.status != "final":
		frappe.throw(frappe._("Document is not finalised."))
	if doc.final_status2 == "final2":
		frappe.throw(frappe._("Status 2 is already final — unfinalise Status 2 first."))
	frappe.db.set_value("Cash Document", doc_name, "status", "pending")
	return "pending"


@frappe.whitelist()
def unfinalise2(doc_name):
	"""Reset final_status2 back to pending2. Restricted to Cash Super User."""
	_require_role(["Cash Super User", "Administrator"])
	doc = frappe.get_doc("Cash Document", doc_name)
	if doc.final_status2 != "final2":
		frappe.throw(frappe._("Status 2 is not finalised."))
	frappe.db.set_value("Cash Document", doc_name, "final_status2", "pending2")
	return "pending2"


@frappe.whitelist()
def add_flag(doc_name, flag_type, comment):
	"""Append a review flag row to document_flags."""
	comment = (comment or "").strip()
	if not comment:
		frappe.throw(frappe._("Flag comment cannot be empty."))

	valid_types = {
		"Review Required", "Approved", "Rejected",
		"Query", "Hold", "Priority", "Revision Needed",
	}
	if flag_type not in valid_types:
		frappe.throw(frappe._("Invalid flag type: {0}").format(flag_type))

	doc = frappe.get_doc("Cash Document", doc_name)
	doc.append("document_flags", {
		"flag_type":      flag_type,
		"flag_date":      now_datetime(),
		"flagged_by":     frappe.session.user,
		"flagged_by_role": _primary_cash_role(),
		"comments":       comment,
	})
	doc.save(ignore_permissions=True)
	return len(doc.document_flags)


@frappe.whitelist()
def clear_flags(doc_name):
	"""Remove all review flags. Restricted to Cash Super User."""
	_require_role(["Cash Super User", "Administrator"])
	frappe.db.delete("Cash Document Flag", {"parent": doc_name})
	return 0


@frappe.whitelist()
def resync_counters():
	"""
	Resync Cash Voucher Series counters to MAX(numeric suffix) across all
	existing Cash Document records.  Call this after any bulk import of
	legacy data to prevent numbering collisions.

	Restricted to Cash Super User / Administrator.
	"""
	_require_role(["Cash Super User", "Administrator"])
	from kgk_customisations.patches.v1_0.resync_cash_voucher_series import (
		resync_counters as _resync,
	)
	return _resync()


@frappe.whitelist()
def import_je_details(file_url):
	"""Read an uploaded XLS/XLSX Fantasy Export file and populate Transaction
	Details fields on all Cash Documents that have a JEID set.
	The uploaded Frappe File doc is deleted after processing."""

	# Resolve the uploaded file
	file_docs = frappe.get_all(
		"File",
		filters={"file_url": file_url},
		fields=["name", "file_name"],
		limit=1,
	)
	if not file_docs:
		frappe.throw(frappe._("Uploaded file not found: {0}").format(file_url))

	file_doc = frappe.get_doc("File", file_docs[0].name)
	ext = os.path.splitext(file_doc.file_name)[1].lower()

	if ext not in (".xls", ".xlsx"):
		frappe.throw(frappe._("Only .xls and .xlsx files are supported."))

	disk_path = file_doc.get_full_path()

	def _iter_rows():
		"""Yield raw row value lists from the spreadsheet, skipping the header."""
		if ext == ".xlsx":
			import openpyxl
			wb = openpyxl.load_workbook(disk_path, read_only=True, data_only=True)
			sh = wb.active
			first = True
			for row in sh.iter_rows(values_only=True):
				if first:
					first = False
					continue
				yield list(row)
			wb.close()
		else:
			try:
				import xlrd
			except ImportError:
				frappe.throw(frappe._("xlrd is required for .xls files. Install with: pip install xlrd"))
			wb = xlrd.open_workbook(disk_path)
			sh = wb.sheets()[0]
			for i in range(1, sh.nrows):
				yield sh.row_values(i)

	def _to_date(val):
		"""Convert a cell value to an ISO date string regardless of source format."""
		if val is None or val == "":
			return None
		if hasattr(val, "isoformat"):  # openpyxl returns date/datetime objects
			return val.date().isoformat() if hasattr(val, "date") else val.isoformat()
		if isinstance(val, str):
			return val.strip() or None
		try:  # xlrd float serial date
			import xlrd
			wb2 = xlrd.open_workbook(disk_path)
			return xlrd.xldate_as_datetime(val, wb2.datemode).date().isoformat()
		except Exception:
			return None

	# Build {jeid: field_dict} — one entry per JEID (first data row wins).
	# Group header rows have a non-empty value in col 0; data rows have col 0 empty/None.
	xls_index = {}
	for row in _iter_rows():
		if row[0]:  # group header — skip
			continue
		jeid = str(row[3]).strip() if row[3] else ""
		if not jeid or jeid in xls_index:
			continue
		xls_index[jeid] = {
			"account_id":          str(int(row[1])) if row[1] else "",
			"contra_account_id":   str(int(row[2])) if row[2] else "",
			"je_doc_date":         _to_date(row[4]),
			"je_line_date":        _to_date(row[5]),
			"account_name":        str(row[6]).strip() if row[6] else "",
			"contra_account_name": str(row[7]).strip() if row[7] else "",
			"je_details":          str(row[8]).strip() if row[8] else "",
			"je_currency":         str(row[9]).strip() if row[9] else "",
			"main_debit":          row[10] or 0,
			"main_credit":         row[11] or 0,
			"sec_debit":           row[13] or 0,
			"sec_credit":          row[14] or 0,
			"je_audit":            str(row[16]).strip() if row[16] else "",
			"je_supplier":         str(row[18]).strip() if row[18] else "",
			"je_user":             str(row[19]).strip() if row[19] else "",
		}

	# Done reading — delete the uploaded file immediately
	file_doc.delete(ignore_permissions=True)

	# Find all Cash Documents with a JEID set
	docs = frappe.db.sql(
		"SELECT name, jeid FROM `tabCash Document` WHERE jeid IS NOT NULL AND jeid != ''",
		as_dict=True,
	)

	matched = []
	not_found = []

	for doc in docs:
		jeid = str(doc["jeid"]).strip()
		if jeid not in xls_index:
			not_found.append(doc["name"])
			continue
		frappe.db.set_value(
			"Cash Document", doc["name"],
			xls_index[jeid],
			update_modified=False,
		)
		matched.append(doc["name"])

	if matched:
		frappe.db.commit()

	return {
		"matched":   len(matched),
		"not_found": not_found,
		"xls_rows":  len(xls_index),
	}


@frappe.whitelist()
def download_merged_pdf(doc_name):
	"""Generate a merged PDF: cover sheet (print format) + main file + supporting files.

	Returns the PDF as a file download response.
	Steps:
	  1. Render 'Cash Document Print' → PDF bytes via frappe.get_print (server-side HTML, no network needed)
	  2. Read the main PDF from the e-dox mount (if set)
	  3. Read each supporting _A/_B/… PDF from the mount
	  4. Merge all into one PDF with pypdf
	  5. Stream back as a file download
	"""
	from pypdf import PdfWriter, PdfReader

	doc = frappe.get_doc("Cash Document", doc_name)

	# --- 1. Cover sheet PDF via frappe.get_print ---
	cover_bytes = frappe.get_print(
		doctype="Cash Document",
		name=doc_name,
		print_format="Cash Document Print",
		as_pdf=True,
		no_letterhead=1,
	)

	writer = PdfWriter()
	skipped = []

	def _append_file(path, label):
		"""Append all pages from a PDF file on disk into the writer.

		Read the entire file into a BytesIO buffer first so that the
		PdfReader always has access to the stream even after the OS file
		handle is closed — pypdf defers content-stream reads until
		writer.write(), so a closed file handle causes silent data loss.
		"""
		try:
			with open(path, "rb") as fh:
				buf = io.BytesIO(fh.read())          # fully buffer in memory
			reader = PdfReader(buf)                  # reader holds BytesIO, stays open
			for page in reader.pages:
				writer.add_page(page)
		except FileNotFoundError:
			skipped.append(f"{label}: file not found at {path}")
		except Exception as exc:
			skipped.append(f"{label}: {exc}")

	# Cover sheet (in-memory bytes — already a BytesIO-compatible source)
	try:
		reader = PdfReader(io.BytesIO(cover_bytes))
		for page in reader.pages:
			writer.add_page(page)
	except Exception as exc:
		frappe.throw(frappe._("Could not read generated cover sheet: {0}").format(exc))

	# --- 2. Main file ---
	if doc.main_file:
		main_path = _url_to_path(doc.main_file)
		if main_path:
			_append_file(main_path, f"main file ({doc.main_file})")
		else:
			skipped.append(f"main file: unrecognised URL scheme ({doc.main_file!r})")

	# --- 3. Supporting files ---
	for row in doc.supporting_files:
		url = row.file_attachment or ""
		if not url:
			continue
		supp_path = _url_to_path(url)
		if supp_path:
			_append_file(supp_path, f"supporting {row.file_suffix or ''} ({url})")
		else:
			skipped.append(f"supporting {row.file_suffix or ''}: unrecognised URL scheme ({url!r})")

	# Log any skipped files for the user to see (non-fatal)
	if skipped:
		frappe.log_error("\n".join(skipped), f"download_merged_pdf: {doc_name} — skipped files")
		frappe.msgprint(
			frappe._("Some attachments could not be included (logged to Error Log):<br>")
			+ "<br>".join(skipped),
			alert=True,
			indicator="orange",
		)

	# --- 4. Stream result ---
	output_buf = io.BytesIO()
	writer.write(output_buf)
	pdf_bytes = output_buf.getvalue()

	# Log page count for diagnostics
	frappe.log_error(
		f"pages={len(writer.pages)}, size={len(pdf_bytes)}, skipped={skipped}",
		f"download_merged_pdf OK: {doc_name}",
	)

	# Use type="pdf" to match Frappe's own print download path (as_pdf handler)
	frappe.local.response.filename = f"{doc_name}.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"


# Internal helpers

def _require_role(roles):
	user_roles = set(frappe.get_roles(frappe.session.user))
	if not user_roles.intersection(roles):
		frappe.throw(
			frappe._("You do not have permission to perform this action."),
			frappe.PermissionError,
		)


def _primary_cash_role():
	"""Return the highest Cash role the current user holds, for audit logging."""
	priority = ["Cash Super User", "Cash Accountant", "Cash Checker", "Cash Basic User"]
	user_roles = set(frappe.get_roles(frappe.session.user))
	for role in priority:
		if role in user_roles:
			return role
	return "User"
