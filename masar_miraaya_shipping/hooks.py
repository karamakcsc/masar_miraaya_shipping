app_name = "masar_miraaya_shipping"
app_title = "Masar Miraaya Shipping"
app_publisher = "KCSC"
app_description = "Masar Miraaya Shipping"
app_email = "info@kcsc.com.jo"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "masar_miraaya_shipping",
# 		"logo": "/assets/masar_miraaya_shipping/logo.png",
# 		"title": "Masar Miraaya Shipping",
# 		"route": "/masar_miraaya_shipping",
# 		"has_permission": "masar_miraaya_shipping.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/masar_miraaya_shipping/css/masar_miraaya_shipping.css"
# app_include_js = "/assets/masar_miraaya_shipping/js/masar_miraaya_shipping.js"

# include js, css files in header of web template
# web_include_css = "/assets/masar_miraaya_shipping/css/masar_miraaya_shipping.css"
# web_include_js = "/assets/masar_miraaya_shipping/js/masar_miraaya_shipping.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "masar_miraaya_shipping/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
   "Pick List": "custom/pick_list/pick_list.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "masar_miraaya_shipping/public/icons.svg"

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
# 	"methods": "masar_miraaya_shipping.utils.jinja_methods",
# 	"filters": "masar_miraaya_shipping.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "masar_miraaya_shipping.install.before_install"
# after_install = "masar_miraaya_shipping.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "masar_miraaya_shipping.uninstall.before_uninstall"
# after_uninstall = "masar_miraaya_shipping.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "masar_miraaya_shipping.utils.before_app_install"
# after_app_install = "masar_miraaya_shipping.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "masar_miraaya_shipping.utils.before_app_uninstall"
# after_app_uninstall = "masar_miraaya_shipping.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "masar_miraaya_shipping.notifications.get_notification_config"

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
	"Pick List": {
		"validate": "masar_miraaya_shipping.custom.pick_list.pick_list.validate",
		"on_submit": "masar_miraaya_shipping.custom.pick_list.pick_list.on_submit"
	}
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"masar_miraaya_shipping.tasks.all"
# 	],
# 	"daily": [
# 		"masar_miraaya_shipping.tasks.daily"
# 	],
# 	"hourly": [
# 		"masar_miraaya_shipping.tasks.hourly"
# 	],
# 	"weekly": [
# 		"masar_miraaya_shipping.tasks.weekly"
# 	],
# 	"monthly": [
# 		"masar_miraaya_shipping.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "masar_miraaya_shipping.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "masar_miraaya_shipping.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "masar_miraaya_shipping.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["masar_miraaya_shipping.utils.before_request"]
# after_request = ["masar_miraaya_shipping.utils.after_request"]

# Job Events
# ----------
# before_job = ["masar_miraaya_shipping.utils.before_job"]
# after_job = ["masar_miraaya_shipping.utils.after_job"]

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
# 	"masar_miraaya_shipping.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

fixtures = [
    {"dt": "Custom Field", "filters": [
        [
            "name", "in", [
                "Pick List-custom_section_break_l95fh",
                "Pick List-custom_picking_duration",
                "Pick List-custom_column_break_gh0gy",
                "Pick List-custom_packing_duration",
                "Pick List-custom_section_break_gwriy",
                "Pick List-custom_delivery_zone",
                "Pick List-custom_section_break_rzfqg",
                "Pick List-custom_delivery_company",
                "Pick List-custom_delivery_company_name",
                "Pick List-custom_column_break_ygsjn",
                "Pick List-custom_driver",
                "Pick List-custom_driver_name",
                "Pick List-custom_packaging_items",
                "Pick List-custom_column_break_skt6f",
                "Pick List-custom_district"
            ]
        ]
    ]}
]