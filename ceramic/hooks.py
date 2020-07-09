# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

# import erpnext
from ceramic.override_default_class_method import raise_exceptions, set_actual_qty, set_item_locations, get_current_tax_amount, determine_exclusive_rate, calculate_taxes, actual_amt_check, create_payment_entry

from erpnext.stock.stock_ledger import update_entries_after
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.pick_list.pick_list import PickList
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockLedgerEntry
from erpnext.accounts.doctype.bank_statement_transaction_entry.bank_statement_transaction_entry import BankStatementTransactionEntry
BankStatementTransactionEntry.create_payment_entry = create_payment_entry

import erpnext
from ceramic.ceramic.doc_events.sales_order import make_delivery_note as so_mk_dn
from ceramic.ceramic.doc_events.sales_order import make_pick_list as so_mk_pl
erpnext.selling.doctype.sales_order.sales_order.make_delivery_note = so_mk_dn
erpnext.selling.doctype.sales_order.sales_order.create_pick_list = so_mk_pl

# naming series overrides
from erpnext.setup.doctype.naming_series.naming_series import NamingSeries
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import OpeningInvoiceCreationTool
from ceramic.ceramic.doc_events.opening_invoice_creation_tool import get_invoice_dict, make_invoices, get_opening_invoice_summary
from ceramic.override_default_class_method import get_transactions
NamingSeries.get_transactions = get_transactions
OpeningInvoiceCreationTool.get_invoice_dict = get_invoice_dict
OpeningInvoiceCreationTool.get_opening_invoice_summary = get_opening_invoice_summary
OpeningInvoiceCreationTool.make_invoices = make_invoices

# # override default class method
update_entries_after.raise_exceptions = raise_exceptions
StockEntry.set_actual_qty = set_actual_qty
PickList.set_item_locations = set_item_locations
calculate_taxes_and_totals.get_current_tax_amount = get_current_tax_amount
calculate_taxes_and_totals.determine_exclusive_rate = determine_exclusive_rate
calculate_taxes_and_totals.calculate_taxes = calculate_taxes
StockLedgerEntry.actual_amt_check = actual_amt_check

from erpnext.accounts.party import _get_party_details as party_detail
from ceramic.api import _get_party_details as my_party_detail
party_detail =my_party_detail

from erpnext.controllers.stock_controller import StockController
from ceramic.batch_creation import make_batches as my_make_batches
StockController.make_batches = my_make_batches

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
app_include_css = "/assets/css/ceramic.min.css"
app_include_js = "/assets/js/ceramic.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/ceramic/css/ceramic.css"
# web_include_js = "/assets/ceramic/js/ceramic.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_list_js = {
	"Pick List" : "public/js/doctype_js/pick_list_list.js",
	"Sales Order" : "public/js/doctype_js/sales_order_list.js"
}
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

scheduler_events = {
	"daily": [
		"ceramic.ceramic.doc_events.sales_order.shedule_so"
	]
}

# Testing
# -------

# before_tests = "ceramic.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.desk.notifications.get_open_count": "ceramic.api.get_open_count",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Sales Order": "ceramic.ceramic.dashboard.sales_order.get_data",
	"Pick List": "ceramic.ceramic.dashboard.pick_list.get_data",
	"Delivery Note": "ceramic.ceramic.dashboard.delivery_note.get_data",
	"Sales Invoice": "ceramic.ceramic.dashboard.sales_invoice.get_data",
}

app_include_css = [
	"/assets/css/ceramic.min.css",
]

doctype_js = {
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Sales Order": "public/js/doctype_js/sales_order.js",
	"Payment Entry": "public/js/doctype_js/payment_entry.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Purchase Invoice": "public/js/doctype_js/purchase_invoice.js",
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"Item": "public/js/doctype_js/item.js",
	"BOM": "public/js/doctype_js/bom.js",
	"Work Order": "public/js/doctype_js/work_order.js",
	"Stock Entry": "public/js/doctype_js/stock_entry.js",
	"Pick List": "public/js/doctype_js/pick_list.js",
	"Company": "public/js/doctype_js/company.js",
	"Quotation": "public/js/doctype_js/quotation.js",
}

doc_events = {
	"Account": {
		"validate": "ceramic.ceramic.doc_events.account.validate",
		"on_trash": "ceramic.ceramic.doc_events.account.on_trash",
	},
	"Cost Center": {
		"after_rename": "ceramic.ceramic.doc_events.warehouse.after_rename",
		"validate": "ceramic.ceramic.doc_events.cost_center.validate",
		"on_trash": "ceramic.ceramic.doc_events.warehouse.on_trash",
	},
	"Warehouse": {
		"after_rename": "ceramic.ceramic.doc_events.warehouse.after_rename",
		"validate": "ceramic.ceramic.doc_events.warehouse.validate",
		"on_trash": "ceramic.ceramic.doc_events.warehouse.on_trash",
	},
	"Sales Order": {
		#"before_save": "ceramic.api.before_save",
		#"before_naming": "ceramic.api.before_naming",
		"before_validate": [
			"ceramic.ceramic.doc_events.sales_order.before_validate"
			#"ceramic.api.naming_series_validate"
		],
		"validate": [
			"ceramic.controllers.item_validation.validate_item_authority", 
			"ceramic.ceramic.doc_events.sales_order.validate"
		],
		"on_submit": "ceramic.ceramic.doc_events.sales_order.on_submit",
		"before_validate_after_submit": "ceramic.ceramic.doc_events.sales_order.before_validate_after_submit",
		"validate_after_submit": "ceramic.ceramic.doc_events.sales_order.validate_after_submit",
		"before_update_after_submit": "ceramic.ceramic.doc_events.sales_order.before_update_after_submit",
		"on_update_after_submit": "ceramic.ceramic.doc_events.sales_order.on_update_after_submit",
		"on_cancel": "ceramic.ceramic.doc_events.sales_order.on_cancel",
	},
	"Pick List": {
		#"before_naming": "ceramic.api.before_naming",
		"before_validate": [
			"ceramic.ceramic.doc_events.pick_list.validate", 
			"ceramic.api.naming_series_validate"
		],
		"before_submit": "ceramic.ceramic.doc_events.pick_list.before_submit",
		"on_submit": "ceramic.ceramic.doc_events.pick_list.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.pick_list.on_cancel",
		"before_update_after_submit": "ceramic.ceramic.doc_events.pick_list.before_update_after_submit"
	},
	"Delivery Note": {
		#"before_naming": "ceramic.api.before_naming",
		"before_validate": [
			"ceramic.ceramic.doc_events.delivery_note.before_validate", 
			"ceramic.api.naming_series_validate"
		],
		"validate": [
			"ceramic.controllers.item_validation.validate_item_authority", 
			"ceramic.ceramic.doc_events.delivery_note.validate"
		],
		"before_save": "ceramic.ceramic.doc_events.delivery_note.before_save",
		"before_submit": "ceramic.ceramic.doc_events.delivery_note.before_submit",
		"on_submit": "ceramic.ceramic.doc_events.delivery_note.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.delivery_note.on_cancel",
	},
	"Sales Invoice": {
		"before_naming": [
			"ceramic.ceramic.doc_events.sales_invoice.before_naming",
			#"ceramic.api.before_naming"
		],
		"before_validate": [
			"ceramic.ceramic.doc_events.sales_invoice.before_validate", 
			"ceramic.ceramic.doc_events.purchase_order.before_validate"
		],
		"validate": [
			"ceramic.ceramic.doc_events.sales_invoice.validate",
			"ceramic.controllers.item_validation.validate_item_authority",
		],
		"on_submit": "ceramic.ceramic.doc_events.sales_invoice.on_submit",
		"before_update_after_submit": "ceramic.ceramic.doc_events.sales_invoice.before_update_after_submit",
		"on_cancel": "ceramic.ceramic.doc_events.sales_invoice.on_cancel",
		"on_trash": "ceramic.ceramic.doc_events.sales_invoice.on_trash",
	},
	"Purchase Order": {
		#"before_naming": "ceramic.api.before_naming",
		"before_validate": [
			"ceramic.api.naming_series_validate", 
			"ceramic.ceramic.doc_events.purchase_order.before_validate"
		],
		"validate": "ceramic.controllers.item_validation.validate_item_authority",
		"on_submit": "ceramic.ceramic.doc_events.purchase_order.on_submit",
	},
	"Purchase Receipt":{
		#"before_naming": "ceramic.api.before_naming",
		"before_validate": [
			"ceramic.api.naming_series_validate",
			"ceramic.ceramic.doc_events.purchase_receipt.before_validate",
		],
		"validate": "ceramic.controllers.item_validation.validate_item_authority"
	},
	"Purchase Invoice": {
		"before_naming": [
			"ceramic.ceramic.doc_events.purchase_invoice.before_naming",
			#"ceramic.api.before_naming",
		],
		"before_validate": [
			"ceramic.ceramic.doc_events.purchase_invoice.before_validate", 
			"ceramic.api.naming_series_validate"
		],
		"validate": "ceramic.controllers.item_validation.validate_item_authority",
		"on_submit": "ceramic.ceramic.doc_events.purchase_invoice.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.purchase_invoice.on_cancel",
		"on_trash": "ceramic.ceramic.doc_events.purchase_invoice.on_trash",
	},
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
	"Payment Entry": {
		#"before_naming": "ceramic.api.before_naming",
		"before_validate": "ceramic.api.naming_series_validate",
		"validate": "ceramic.ceramic.doc_events.payment_entry.validate",
		"on_submit": "ceramic.ceramic.doc_events.payment_entry.on_submit",
		"on_cancel": "ceramic.ceramic.doc_events.payment_entry.on_cancel",
		"on_trash": "ceramic.ceramic.doc_events.payment_entry.on_trash",
		"on_update_after_submit": "ceramic.ceramic.doc_events.payment_entry.on_update_after_submit",
	},	
	"Stock Entry":{
		"before_validate": "ceramic.ceramic.doc_events.stock_entry.before_validate",
		'before_submit': "ceramic.ceramic.doc_events.stock_entry.before_submit",
		'on_submit':"ceramic.batch_creation.stock_entry_on_sumbit",
		'before_cancel': "ceramic.ceramic.doc_events.stock_entry.before_cancel",
		# 'on_cancel': "ceramic.ceramic.doc_events.stock_entry.on_cancel",
		'before_save': "ceramic.ceramic.doc_events.stock_entry.before_save",
		'validate': [
			"ceramic.ceramic.doc_events.stock_entry.validate",
			"ceramic.controllers.item_validation.validate_item_authority"
		],
	},
	"Fiscal Year": {
		'before_save': 'ceramic.ceramic.doc_events.fiscal_year.before_save'
	},
	"Batch":{
		"before_naming": "ceramic.ceramic.doc_events.batch.batch_before_name",
	},
	"Customer": {
		"before_validate": "ceramic.ceramic.doc_events.customer.before_validate",
		'validate':"ceramic.ceramic.doc_events.customer.validate",
	},
	"Lead": {
		'validate':"ceramic.ceramic.doc_events.lead.validate",
	},
}

