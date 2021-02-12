import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

def on_submit(self, test):
	"""On Submit Custom Function for Sales Invoice"""
	if self.authority == "Unauthorized":
		self.db_set("pay_amount_left", self.real_difference_amount)
	create_main_purchase_invoice(self)

def on_cancel(self, test):
	"""On Cancel Custom Function for Sales Invoice"""
	cancel_main_purchase_invoice(self)

def on_trash(self, test):
	delete_purchase_invoice(self)

def change_purchase_reciept_authority(name):
	pass

# Create New Invouice on Submit
def create_main_purchase_invoice(self):
	
	# Getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	def get_purchase_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_target_values(source, target):
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.pi_ref = self.name
			target.authority = "Unauthorized"
			target.update_stock = 0

			if source.cost_center:
				target.cost_center = source.cost_center.replace(source_company_abbr, target_company_abbr)	
			if source.credit_to:
				target.credit_to = source.credit_to.replace(source_company_abbr, target_company_abbr)
			if source.taxes_and_charges:
				target.taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)

			if source.taxes:
				for index, i in enumerate(source.taxes):
					# target.taxes[index].charge_type = "Actual"
					target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
					if source.taxes[index].cost_center:
						target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)
			if self.amended_from:
				name = frappe.db.get_value("Purchase Invoice", {"pi_ref": source.amended_from}, "name")
				target.amended_from = name

			target.set_missing_values()

		def account_details(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			# target_doc.income_account = doc.default_income_account
			# if source_doc.income_account:
			# 	target_doc.income_account = source_doc.income_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.deferred_expense_account:
				target_doc.deferred_expense_account = source_doc.deferred_expense_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)
			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
			if source_doc.rejected_warehouse:
				target_doc.rejected_warehouse = source_doc.rejected_warehouse.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Purchase Invoice": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"pi_ref": "name",
				},
				"field_no_map":{
					"authority",
					"set_warehouse",
					"rejected_warehouse"
				}
			},
			"Purchase Invoice Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"item_design": "item_code",
					"item_code": "item_design",
					# Rate
					"full_rate": "rate",
					"rate": "discounted_rate",
					# Quantity
					"full_qty": "qty",
					"received_full_qty": "received_qty",
					"rejected_full_qty": "rejected_qty",
					"qty": "real_qty",
					"received_real_qty": "received_full_qty",
					"rejected_real_qty": "rejected_full_qty",
					# Ref Links
					"purchase_receipt_docname": "purchase_receipt",
					"purchase_receipt_childname": "pr_detail",
					"po_docname": "purchase_order",
					"po_childname": "po_detail",
				},
				"field_no_map": {
					"full_rate",
					"full_qty",
					"series",
				},
				"postprocess": account_details,
			}
		}

		doclist = get_mapped_doc(
			"Purchase Invoice",
			source_name,
			fields,
			target_doc,
			set_target_values,
			ignore_permissions=ignore_permissions
		)

		return doclist

	# If company is authorized then only cancel another invoice
	if authority == "Authorized" and not self.dont_replicate:
		pi = get_purchase_invoice_entry(self.name)
		pi.naming_series = 'A' + str(self.company_series) + self.naming_series
		pi.company_series = self.company_series
		pi.flags.ignore_permissions = True

		pi.save(ignore_permissions= True)
		self.db_set('pi_ref', pi.name)
		pi.submit()
	
	
def before_validate(self, method):
	self.flags.ignore_permissions = True
		
	if self.authority == "Authorized":
		for item in self.items:
			if not item.po_docname:
				if not item.full_rate:
					item.full_rate = item.rate

				if not item.full_qty:
					item.full_qty = item.qty
	
	if self.authority == "Unauthorized" and not self.pi_ref:
		for item in self.items:
			item.discounted_rate = 0
			item.real_qty = 0

	for item in self.items:
		item.discounted_amount = (item.discounted_rate or 0)  * (item.real_qty or 0)
		item.discounted_net_amount = item.discounted_amount
	
	if self.authority == "Unauthorized":
		for item in self.items:
			item.full_rate = 0
			item.full_qty = 0

	update_discounted_net_total(self)

def update_discounted_net_total(self):
	self.discounted_total = sum(x.discounted_amount for x in self.items)
	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
	testing_only_tax = 0
	
	for tax in self.taxes:
		if tax.testing_only:
			testing_only_tax += tax.tax_amount
	
	self.discounted_grand_total = flt(self.discounted_net_total) + flt(self.total_taxes_and_charges) - flt(testing_only_tax)
	if self.rounded_total:
		self.discounted_rounded_total = round(self.discounted_grand_total)
	self.real_difference_amount = flt(self.rounded_total or self.grand_total) - (flt(self.discounted_rounded_total) or flt(self.discounted_grand_total))


def before_naming(self, method):
	if self.is_opening == "Yes":
		if not self.get('name'):
			self.naming_series = 'O' + self.naming_series

# Cancel Invoice on Cancel
def cancel_main_purchase_invoice(self):
	pi = None
	if self.pi_ref:
		pi = frappe.get_doc("Purchase Invoice", {'pi_ref':self.name})
	
	if pi:
		pi.flags.ignore_permissions = True
		if pi.docstatus == 1:
			pi.cancel()


def delete_purchase_invoice(self):
	ref_name = self.pi_ref
	try:
		frappe.db.set_value("Purchase Invoice", self.name, 'pi_ref', '')
		frappe.db.set_value("Purchase Invoice", ref_name, 'pi_ref', '')
		frappe.delete_doc("Purchase Invoice", ref_name, force = 1, ignore_permissions=True)  
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)