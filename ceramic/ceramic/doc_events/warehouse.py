# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.rename_doc import rename_doc


def validate(self, method):
	""" Custom Validate Function """

	update_warehouse(self)

def on_trash(self, method):
	""" Custom Trash Function """

	delete_warehouse(self)

def after_rename(self, method, old, new, merge=False):
	""" After Rename Function to Rename the Alternate Company Warehouse With Same Name """

	# getting name of alternate company in target_company
	target_company = frappe.db.get_value("Company", self.company, "alternate_company")

	if target_company:
		# getting abbreviation of current and target company
		source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
		
		# setting target warehouse old and new name
		w_old = old.replace(source_company_abbr, target_company_abbr)
		w_new = new.replace(source_company_abbr, target_company_abbr)

		# renaming target warehouse
		if frappe.db.exists("Warehouse", w_old):
			if merge:
				if not self.merge_status:
					self.db_set('merge_status', 1)
					
					if not frappe.db.exists("Warehouse", w_new):
						frappe.throw(_("Please create warehouse {} and merge.".format(frappe.bold(w_new))))
					
					rename_doc("Warehouse", w_old, w_new, merge=merge)
			else:
				rename_doc("Warehouse", w_old, w_new, merge=merge)
			
		self.db_set('merge_status', 0)

def update_warehouse(self):
	""" Function to create or update warehouse in alternate company """

	# Getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	# if company is authorized than only create copy or update wareouse of alternate company
	if authority == "Authorized":

		# getting name of alternate company in target_company
		target_company = frappe.db.get_value("Company", self.company, "alternate_company")

		if target_company:
			# getting abbreviation of current and target company
			source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")

			# if warehouse exists in alternate company then update that warehouse or create new warehouse
			if frappe.db.exists("Warehouse", {"company": target_company, "warehouse_name": self.warehouse_name}):
				w = frappe.get_doc("Warehouse", {"company": target_company, "warehouse_name": self.warehouse_name})
			else:
				w = frappe.new_doc("Warehouse")
				w.company = target_company

			w.warehouse_name = self.warehouse_name
			w.is_group = self.is_group
			w.disabled = self.disabled

			if self.parent_warehouse:
				w.parent_warehouse = self.parent_warehouse.replace(source_company_abbr, target_company_abbr)
			
			if self.account:
				w.account = self.account.replace(source_company_abbr, target_company_abbr)

			try:
				w.save()
			except Exception as e:
				frappe.throw(_(e))

def delete_warehouse(self):
	""" Function to delete warehouse in alternate company """

	# getting name of alternate company in target_company
	target_company = frappe.db.get_value("Company", self.company, "alternate_company")

	if target_company:
		# if warehouse exists in alternate company then update that warehouse or create new warehouse
		if frappe.db.exists("Warehouse", {"company": target_company, "warehouse_name": self.warehouse_name}):
			
			warehouse = frappe.get_doc("Warehouse", {"company": target_company, "warehouse_name": self.warehouse_name})
			warehouse_name = self.warehouse_name + "Deleted"
			self.db_set("warehouse_name", warehouse_name)

			try:
				warehouse.flags.ignore_permissions = True
				warehouse.delete()
			except Exception as e:
				frappe.throw(_(e))
