app_name = "kgk_customisations"
app_title = "Kgk Customisations"
app_publisher = "Apjakal IT Solutions"
app_description = "Custom features for KGK business processes"
app_email = "erpsupport@apjakal.co.bw"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "kgk_customisations",
# 		"logo": "/assets/kgk_customisations/logo.png",
# 		"title": "Kgk Customisations",
# 		"route": "/kgk_customisations",
# 		"has_permission": "kgk_customisations.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kgk_customisations/css/kgk_customisations.css"
# app_include_js = "/assets/kgk_customisations/js/kgk_customisations.js"

# include js, css files in header of web template
# web_include_css = "/assets/kgk_customisations/css/kgk_customisations.css"
# web_include_js = "/assets/kgk_customisations/js/kgk_customisations.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kgk_customisations/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "kgk_customisations/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "kgk_customisations.utils.jinja_methods",
# 	"filters": "kgk_customisations.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "kgk_customisations.install.before_install"
# after_install = "kgk_customisations.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "kgk_customisations.uninstall.before_uninstall"
# after_uninstall = "kgk_customisations.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "kgk_customisations.utils.before_app_install"
# after_app_install = "kgk_customisations.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "kgk_customisations.utils.before_app_uninstall"
# after_app_uninstall = "kgk_customisations.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kgk_customisations.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Employee": {
		"on_update": "kgk_customisations.kgk_customisations.doc_events.employee.update_employee_targets"
	},
	"Invoice Processing": {
		"after_insert": "kgk_customisations.kgk_customisations.doctype.invoice_processing.invoice_processing.fix_date_after_insert"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"kgk_customisations.kgk_customisations.tasks.daily_balance_calculation",
		"kgk_customisations.kgk_customisations.tasks.auto_reconcile_balances",
		"kgk_customisations.kgk_customisations.tasks.send_daily_balance_reminder",
		"kgk_customisations.file_management.Utils.indexer.index_all_files"
	],
	"hourly": [
		"kgk_customisations.kgk_customisations.tasks.check_pending_verifications"
	],
	"weekly": [
		"kgk_customisations.kgk_customisations.tasks.weekly_reconciliation_report",
		"kgk_customisations.file_management.Utils.file_operations.validate_indexed_files"
	]
}

# Testing
# -------

# before_tests = "kgk_customisations.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "kgk_customisations.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "kgk_customisations.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["kgk_customisations.utils.before_request"]
# after_request = ["kgk_customisations.utils.after_request"]

# Job Events
# ----------
# before_job = ["kgk_customisations.utils.before_job"]
# after_job = ["kgk_customisations.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"kgk_customisations.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Fixtures
# --------
# Installed during app installation
fixtures = [
	{
		"doctype": "Role",
		"filters": [
			["name", "in", ["Cash Basic User", "Cash Checker", "Cash Accountant", "Cash Super User"]]
		]
	},
	{
		"doctype": "DocPerm",
		"filters": [
			["parent", "in", ["Page", "Data Import Log"]],
			["role", "in", ["Fulfillment User", "Report Manager"]]
		]
	}
]

# Installation hooks
# ------------------
# after_install = "kgk_customisations.kgk_customisations.setup.cash_management_setup.execute"

