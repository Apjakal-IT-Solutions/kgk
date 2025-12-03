# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Scheduled tasks for Cash Management System
"""

import frappe
from frappe.utils import getdate, add_days, now_datetime, get_datetime
from frappe.utils.data import flt


def daily_balance_calculation():
	"""
	Daily task to calculate cash balances for all companies
	Runs at midnight to process previous day's transactions
	"""
	try:
		# Get yesterday's date
		yesterday = add_days(getdate(), -1)
		
		# Get all active companies
		companies = frappe.get_all("Company", filters={"disabled": 0}, pluck="name")
		
		for company in companies:
			# Check if Daily Cash Balance already exists
			existing = frappe.db.exists(
				"Daily Cash Balance",
				{
					"balance_date": yesterday,
					"company": company
				}
			)
			
			if not existing:
				# Create new Daily Cash Balance entry
				balance_doc = frappe.get_doc({
					"doctype": "Daily Cash Balance",
					"balance_date": yesterday,
					"company": company
				})
				
				# Calculate balances from Cash Documents
				balance_doc.calculate_erp_balance()
				balance_doc.calculate_variance()
				balance_doc.check_reconciliation_required()
				
				balance_doc.insert(ignore_permissions=True)
				frappe.db.commit()
				
				frappe.logger().info(f"Created Daily Cash Balance for {company} on {yesterday}")
		
		frappe.logger().info(f"Daily balance calculation completed for {len(companies)} companies")
		
	except Exception as e:
		frappe.log_error(f"Daily balance calculation failed: {str(e)}", "Daily Balance Calculation Error")


def auto_reconcile_balances():
	"""
	Auto-reconcile balances that are within the acceptable threshold
	Runs daily after balance calculation
	"""
	try:
		# Get variance threshold from settings
		settings = frappe.get_single("Cash Management Settings")
		
		if not settings.auto_reconcile:
			return
		
		variance_threshold = settings.variance_threshold or 5
		
		# Get all unreconciled balances from yesterday
		yesterday = add_days(getdate(), -1)
		
		balances = frappe.get_all(
			"Daily Cash Balance",
			filters={
				"balance_date": yesterday,
				"status": ["in", ["Pending Review", "Variance Identified"]],
				"reconciliation_required": 0
			},
			fields=["name", "variance_percentage"]
		)
		
		reconciled_count = 0
		
		for balance in balances:
			# Check if variance is within threshold
			if abs(flt(balance.variance_percentage)) <= variance_threshold:
				balance_doc = frappe.get_doc("Daily Cash Balance", balance.name)
				balance_doc.mark_reconciled(
					reconciliation_notes=f"Auto-reconciled: variance {balance.variance_percentage}% within threshold {variance_threshold}%"
				)
				reconciled_count += 1
		
		if reconciled_count > 0:
			frappe.db.commit()
			frappe.logger().info(f"Auto-reconciled {reconciled_count} balances within threshold")
	
	except Exception as e:
		frappe.log_error(f"Auto-reconciliation failed: {str(e)}", "Auto Reconciliation Error")


def send_daily_balance_reminder():
	"""
	Send reminder emails to users to submit daily balances
	Runs at 4 PM daily
	"""
	try:
		today = getdate()
		
		# Get all companies
		companies = frappe.get_all("Company", filters={"disabled": 0}, pluck="name")
		
		for company in companies:
			# Check if balance submission exists for today
			existing = frappe.db.exists(
				"Cash Balance Submission",
				{
					"submission_date": today,
					"company": company,
					"verification_status": ["!=", "Draft"]
				}
			)
			
			if not existing:
				# Get users with Accounts User role for this company
				users = frappe.get_all(
					"Has Role",
					filters={"role": "Accounts User"},
					pluck="parent"
				)
				
				for user in users:
					# Send reminder email
					frappe.sendmail(
						recipients=[user],
						subject=f"Daily Balance Submission Reminder - {company}",
						message=f"""
						<h3>Daily Balance Submission Reminder</h3>
						<p>Please submit your daily cash balance for {company} for {today}.</p>
						<p><a href="{frappe.utils.get_url()}/app/cash-balance-submission/new">Submit Balance Now</a></p>
						""",
						delayed=False
					)
				
				frappe.logger().info(f"Sent balance reminder for {company} to {len(users)} users")
	
	except Exception as e:
		frappe.log_error(f"Daily reminder failed: {str(e)}", "Daily Reminder Error")


def check_pending_verifications():
	"""
	Check for pending verifications and send notifications
	Runs hourly during business hours
	"""
	try:
		# Check Cash Balance Submissions pending verification
		pending_submissions = frappe.get_all(
			"Cash Balance Submission",
			filters={
				"verification_status": ["in", ["Basic Submitted", "Checker Verified"]],
				"modified": ["<", add_days(now_datetime(), -1)]  # Pending for more than 1 day
			},
			fields=["name", "company", "verification_status", "submission_date"]
		)
		
		if pending_submissions:
			# Get Accounts Managers
			managers = frappe.get_all(
				"Has Role",
				filters={"role": "Accounts Manager"},
				pluck="parent"
			)
			
			# Send notification
			message = f"""
			<h3>Pending Balance Verifications Alert</h3>
			<p>{len(pending_submissions)} balance submissions are pending verification for more than 1 day:</p>
			<ul>
			"""
			
			for submission in pending_submissions:
				message += f"""
				<li><strong>{submission.name}</strong> - {submission.company} - {submission.verification_status} - {submission.submission_date}</li>
				"""
			
			message += """
			</ul>
			<p>Please review and verify these submissions.</p>
			"""
			
			for manager in managers:
				frappe.sendmail(
					recipients=[manager],
					subject=f"Pending Balance Verifications - {len(pending_submissions)} items",
					message=message,
					delayed=False
				)
			
			frappe.logger().info(f"Sent pending verification alerts for {len(pending_submissions)} submissions")
	
	except Exception as e:
		frappe.log_error(f"Pending verification check failed: {str(e)}", "Pending Verification Check Error")


def weekly_reconciliation_report():
	"""
	Generate and send weekly reconciliation report
	Runs every Monday morning
	"""
	try:
		# Get date range for last week
		today = getdate()
		week_start = add_days(today, -7)
		week_end = add_days(today, -1)
		
		# Get all companies
		companies = frappe.get_all("Company", filters={"disabled": 0}, pluck="name")
		
		report_data = []
		
		for company in companies:
			# Get balances for the week
			balances = frappe.get_all(
				"Daily Cash Balance",
				filters={
					"balance_date": ["between", [week_start, week_end]],
					"company": company
				},
				fields=["balance_date", "status", "variance_amount", "variance_percentage", "reconciliation_required"]
			)
			
			if balances:
				reconciled = len([b for b in balances if b.status == "Reconciled"])
				pending = len([b for b in balances if b.status != "Reconciled"])
				total_variance = sum([flt(b.variance_amount) for b in balances])
				
				report_data.append({
					"company": company,
					"total_days": len(balances),
					"reconciled": reconciled,
					"pending": pending,
					"total_variance": total_variance
				})
		
		# Generate HTML report
		html_report = f"""
		<h2>Weekly Cash Reconciliation Report</h2>
		<h4>Period: {week_start} to {week_end}</h4>
		<table border="1" cellpadding="5" cellspacing="0">
			<tr>
				<th>Company</th>
				<th>Total Days</th>
				<th>Reconciled</th>
				<th>Pending</th>
				<th>Total Variance</th>
			</tr>
		"""
		
		for data in report_data:
			html_report += f"""
			<tr>
				<td>{data['company']}</td>
				<td>{data['total_days']}</td>
				<td>{data['reconciled']}</td>
				<td>{data['pending']}</td>
				<td>{data['total_variance']:.2f}</td>
			</tr>
			"""
		
		html_report += "</table>"
		
		# Send to Accounts Managers and System Managers
		managers = frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["Accounts Manager", "System Manager"]]},
			pluck="parent",
			distinct=True
		)
		
		if managers:
			frappe.sendmail(
				recipients=managers,
				subject=f"Weekly Cash Reconciliation Report - {week_start} to {week_end}",
				message=html_report,
				delayed=False
			)
			
			frappe.logger().info(f"Sent weekly reconciliation report to {len(managers)} managers")
	
	except Exception as e:
		frappe.log_error(f"Weekly report generation failed: {str(e)}", "Weekly Report Error")
