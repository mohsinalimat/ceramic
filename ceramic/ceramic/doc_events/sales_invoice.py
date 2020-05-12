import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

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

def on_submit(self, test):
	"""On Submit Custom Function for Sales Invoice"""
	create_main_sales_invoice(self)

def on_cancel(self, test):
	"""On Cancel Custom Function for Sales Invoice"""
	cancel_main_sales_invoice(self)

def on_trash(self, test):
	delete_sales_invoice(self)

def change_delivery_authority(name):
	dn_status = frappe.get_value("Delivery Note", name, "status")
	if dn_status == 'Completed':
		frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
	else:
		frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
	
	frappe.db.commit()

# Create New Invouice on Submit
def create_main_sales_invoice(self):
	
	# Getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_target_values(source, target):
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.si_ref = self.name
			target.authority = "Unauthorized"

			if source.debit_to:
				target.debit_to = source.debit_to.replace(source_company_abbr, target_company_abbr)
			if source.taxes_and_charges:
				taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", taxes_and_charges):
					target.taxes_and_charges = taxes_and_charges
				else:
					target.taxes_and_charges = ''

			if source.taxes:
				for index, i in enumerate(source.taxes):
					target.taxes[index].charge_type = source.taxes[index].charge_type
					target.taxes[index].included_in_print_rate = source.taxes[index].included_in_print_rate
					if source.taxes[index].cost_center:
						target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)
					if source.taxes[index].account_head:
						target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
			if self.amended_from:
				name = frappe.db.get_value("Sales Invoice", {"si_ref": source.amended_from}, "name")
				target.amended_from = name

			target.set_missing_values()

		def account_details(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			target_doc.real_qty = source_doc.qty


			if source_doc.income_account:
				target_doc.income_account = source_doc.income_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Sales Invoice": {
				"doctype": "Sales Invoice",
				"field_map": {
					"si_ref": "name",
					"is_opening": "is_opening",
					"posting_date": "posting_date",
					"posting_time": "posting_time",
					"set_posting_time": "set_posting_time",
				},
				"field_no_map":{
					"authority",
					"update_stock"
				}
			},
			"Sales Invoice Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"item_design": "item_code",
					"item_code": "item_design",
					"full_rate": "rate",
					"full_qty": "qty",
					"rate": "discounted_rate",
					"qty": "real_qty",
					"delivery_docname": "delivery_note",
					"delivery_childname": "dn_detail",
					"so_childname": "so_detail",
					"so_docname": "sales_order",
					"real_batch_no": "batch_no",
					"is_opening": "is_opening"
				},
				"field_no_map": {
					"full_rate",
					"full_qty",
					"series",
					"real_batch_no"
				},
				"postprocess": account_details,
			}
		}

		doclist = get_mapped_doc(
			"Sales Invoice",
			source_name,
			fields,
			target_doc,
			set_target_values,
			ignore_permissions=ignore_permissions
		)

		return doclist

	# If company is authorized then only cancel another invoice
	if authority == "Authorized":
		si = get_sales_invoice_entry(self.name)
		si.naming_series = 'A' + si.naming_series
		si.series_value = self.series_value
		si.flags.ignore_permissions = True
		
		si.save(ignore_permissions = True)
		si.pay_amount_left = si.rounded_total - self.rounded_total
		if si.pay_amount_left < 0:
			si.pay_amount_left = 0.0
		si.save(ignore_permissions = True)
		self.db_set('si_ref', si.name)
		si.submit()
	
	if authority == "Unauthorized" and not self.si_ref:
		self.db_set('pay_amount_left', self.rounded_total)

def validate(self, method):
	update_discounted_net_total(self)

def update_discounted_net_total(self):
	self.discounted_total = sum(x.discounted_amount for x in self.items)
	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
	self.discounted_grand_total = self.discounted_net_total + self.total_taxes_and_charges
	self.discounted_rounded_total = round(self.discounted_grand_total)
	self.real_difference_amount = self.rounded_total - self.discounted_rounded_total


# Cancel Invoice on Cancel
def cancel_main_sales_invoice(self):
	if self.si_ref:
		si = frappe.get_doc("Sales Invoice", {'si_ref':self.name})
	else:
		si = None
	
	if si:
		if si.docstatus == 1:
			si.flags.ignore_permissions = True
			try:
				si.cancel()
				for i in self.items:
					change_delivery_authority(i.delivery_docname)
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)
	else:
		for i in self.items:
			change_delivery_authority(i.delivery_docname)

def delete_sales_invoice(self):
	ref_name = self.si_ref
	try:
		frappe.db.set_value("Sales Invoice", self.name, 'si_ref', '')    
		frappe.db.set_value("Sales Invoice", ref_name, 'si_ref', '') 
		frappe.delete_doc("Sales Invoice", ref_name, force = 1, ignore_permissions=True)  
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)
	else:
		frappe.db.commit()

@frappe.whitelist()
def submit_purchase_invoice(pi_number):
	pi = frappe.get_doc("Purchase Invoice", pi_number)
	pi.flags.ignore_permissions = True
	pi.submit()
	frappe.db.commit()