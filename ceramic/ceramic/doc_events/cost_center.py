# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.rename_doc import rename_doc


def validate(self, method):
	""" Custom Validate Function """
	pass
	#update_cost_center(self)

def on_trash(self, method):
	""" Custom Trash Function """

	delete_cost_center(self)

def after_rename(self, method, old, new, merge=False):
	""" After Rename Function to Rename the Alternate Company cost center With Same Name """

	# getting name of alternate company in target_company
	target_company = frappe.db.get_value("Company", self.company, "alternate_company")

	if target_company:
		# getting abbreviation of current and target company
		source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
		
		# setting target cost center old and new name
		cc_old = old.replace("- " + source_company_abbr, "- " + target_company_abbr)
		cc_new = new.replace("- " + source_company_abbr, "- " + target_company_abbr)

		# renaming target cost center
		if frappe.db.exists("Cost Center", cc_old):
			if merge:
				if not self.merge_status:
					self.db_set('merge_status', 1)
					
					if not frappe.db.exists("Cost Center", cc_new):
						frappe.throw(_("Please create Cost Center {} and merge.".format(frappe.bold(cc_new))))
					
					rename_doc("Cost Center", cc_old, cc_new, merge=merge)
			else:
				rename_doc("Cost Center", cc_old, cc_new, merge=merge)
			
		self.db_set('merge_status', 0)

def update_cost_center(self):
	# Getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	if authority == "Authorized":
		target_company = frappe.db.get_value("Company", self.company, "alternate_company")
		
		if target_company:

			# if warehouse exists in alternate company then update that warehouse or create new warehouse
			if frappe.db.exists("Cost Center", {"company": target_company, "cost_center_name": self.cost_center_name}):
				cc = frappe.get_doc("Warehouse", {"company": target_company, "cost_center_name": self.cost_center_name})
			else:
				cc = frappe.new_doc("Cost Center")
				cc.company = target_company

			cc.cost_center_name = self.cost_center_name

			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")

			if self.parent_cost_center:
				cc.parent_cost_center = self.parent_cost_center.replace(self.company, cc.company).replace("- " + source_company_abbr, "- " + target_company_abbr)
			
			if self.is_group:
				cc.is_group = self.is_group

			if self.disabled:
				cc.disabled = s.disabled
		
			try:
				cc.save()
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)

def delete_cost_center(self):
	""" Function to delete cost center in alternate company """

	# getting name of alternate company in target_company
	target_company = frappe.db.get_value("Company", self.company, "alternate_company")

	if target_company:
		# if cost center exists in alternate company then update that cost center or create new cost center
		if frappe.db.exists("Cost Center", {"company": target_company, "cost_center_name": self.cost_center_name}):
			
			cost_center = frappe.get_doc("Cost Center", {"company": target_company, "cost_center_name": self.cost_center_name})
			cost_center_name = self.cost_center_name + "Deleted"
			self.db_set("cost_center_name", cost_center_name)

			try:
				cost_center.flags.ignore_permissions = True
				cost_center.delete()
			except Exception as e:
				frappe.throw(_(e))
