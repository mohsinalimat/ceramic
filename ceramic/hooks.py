# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "ceramic"
app_title = "Ceramic"
app_publisher = "Finbyz"
app_description = "App for Ceramic Tiles"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@finbyz.tech"
app_license = "GPL 3.0"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ceramic/css/ceramic.css"
app_include_js = [
	"/assets/ceramic/js/restrict_access.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/ceramic/css/ceramic.css"
# web_include_js = "/assets/ceramic/js/ceramic.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "ceramic.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "ceramic.install.before_install"
# after_install = "ceramic.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ceramic.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ceramic.tasks.all"
# 	],
# 	"daily": [
# 		"ceramic.tasks.daily"
# 	],
# 	"hourly": [
# 		"ceramic.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ceramic.tasks.weekly"
# 	]
# 	"monthly": [
# 		"ceramic.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "ceramic.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ceramic.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ceramic.task.get_dashboard_data"
# }

doctype_js = {
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Sales Order": "public/js/doctype_js/sales_order.js",
	"Payment Entry": "public/js/doctype_js/payment_entry.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"BOM": "public/js/doctype_js/bom.js",
	"Work Order": "public/js/doctype_js/work_order.js",
	"Stock Entry": "public/js/doctype_js/stock_entry.js",
}

doc_events = {
	"BOM": {
		"before_naming": "ceramic.ceramic.doc_events.bom.before_naming",
		"before_validate": "ceramic.ceramic.doc_events.bom.before_validate",
		"before_cancel": "ceramic.ceramic.doc_events.bom.before_cancel",
		"before_submit": "ceramic.ceramic.doc_events.bom.before_submit",
		"before_update_after_submit": "ceramic.ceramic.doc_events.bom.before_update_after_submit"
	},
	"Work Order":{
		'before_submit': "ceramic.ceramic.doc_events.work_order.before_submit",
		'before_cancel': "ceramic.ceramic.doc_events.work_order.before_cancel",
	},
	"Sales Invoice": {
		"on_submit": "ceramic.ceramic.doc_events.sales_invoice.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.sales_invoice.on_cancel",
		"on_trash": "ceramic.ceramic.doc_events.sales_invoice.on_trash",
		"before_naming": "ceramic.api.before_naming",
	},
	"Delivery Note": {
		"on_submit": "ceramic.ceramic.doc_events.delivery_note.on_submit",
		"before_naming": "ceramic.api.before_naming",
	},
	"Sales Order": {
		"before_naming": "ceramic.api.before_naming",
	},
	"Payment Entry": {
		"on_submit": "ceramic.ceramic.doc_events.payment_entry.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.payment_entry.on_cancel",
		"on_trash": "ceramic.ceramic.doc_events.payment_entry.on_trash",
		"before_naming": "ceramic.api.before_naming",
	},
	"Purchase Invoice": {
		"on_submit": "ceramic.ceramic.doc_events.purchase_invoice.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.purchase_invoice.on_cancel",
		"on_trash": "ceramic.ceramic.doc_events.purchase_invoice.on_trash",
		# "before_naming": "ceramic.api.before_naming",
	},
	"Warehouse": {
		"validate": "ceramic.ceramic.doc_events.warehouse.before_save",
	},
	"Stock Entry":{
		"before_validate": "ceramic.ceramic.doc_events.stock_entry.before_validate",
		'before_submit': "ceramic.ceramic.doc_events.stock_entry.before_submit",
		'before_cancel': "ceramic.ceramic.doc_events.stock_entry.before_cancel",
		'before_save': "ceramic.ceramic.doc_events.stock_entry.before_save",
	},
	("Sales Invoice", "Purchase Invoice", "Payment Request", "Payment Entry", "Journal Entry", "Material Request", "Purchase Order", "Work Order", "Production Plan", "Stock Entry", "Quotation", "Sales Order", "Delivery Note", "Purchase Receipt", "Packing Slip"): {
		"before_naming": "ceramic.api.docs_before_naming",
	}
}

fixtures = ['Custom Field']	