import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

def on_submit(self, test):
	"""On Submit Custom Function for Sales Invoice"""
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

			if source.credit_to:
				target.credit_to = source.credit_to.replace(source_company_abbr, target_company_abbr)
			if source.taxes_and_charges:
				target.taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)

				for index, i in enumerate(source.taxes):
					target.taxes[index].charge_type = "Actual"
					target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)

			if self.amended_from:
				name = frappe.db.get_value("Sales Invoice", {"pi_ref": source.amended_from}, "name")
				target.amended_from = name

			target.set_missing_values()

		def account_details(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			target_doc.income_account = doc.default_income_account
			target_doc.expense_account = doc.default_expense_account
			target_doc.cost_center = doc.cost_center

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
	if authority == "Authorized":
		pi = get_purchase_invoice_entry(self.name)
		pi.naming_series = 'A' + pi.naming_series
		pi.company_series = self.company_series
		pi.flags.ignore_permissions = True
		try:
			pi.save(ignore_permissions= True)
			self.db_set('pi_ref', pi.name)
			frappe.db.commit()
			pi.submit()
		except Exception as e:
			frappe.db.rollback()
			frappe.throw(e)
	
	
def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = (item.discounted_rate or 0)  * (item.real_qty or 0)
		item.discounted_net_amount = item.discounted_amount
	
	if self.authority == "Unauthorized":
		for item in self.items:
			item.full_rate = 0
			item.full_qty = 0

def before_naming(self, method):
	if self.is_opening == "Yes":
		if not self.get('name'):
			self.naming_series = 'O' + self.naming_series

# Cancel Invoice on Cancel
def cancel_main_purchase_invoice(self):
	if self.pi_ref:
		pi = frappe.get_doc("Purchase Invoice", {'pi_ref':self.name})
	else:
		pi = None
	
	if pi:
		if pi.docstatus == 1:
			pi.flags.ignore_permissions = True
			try:
				pi.cancel()
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)


def delete_purchase_invoice(self):
	ref_name = self.pi_ref
	try:
		frappe.db.set_value("Purchase Invoice", self.name, 'pi_ref', '')    
		frappe.db.set_value("Purchase Invoice", ref_name, 'pi_ref', '') 
		frappe.delete_doc("Purchase Invoice", ref_name, force = 1, ignore_permissions=True)  
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)
	else:
		frappe.db.commit()