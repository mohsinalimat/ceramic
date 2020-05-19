import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

def validate(self,method):
	get_sales_person(self)
	for item in self.references:
		if self.payment_type == "Pay":
			if item.reference_doctype == 'Purchase Invoice':
				item.ref_invoice = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pi_ref')
		
		if self.payment_type == "Receive":
			if item.reference_doctype == 'Sales Invoice':
				item.ref_invoice = frappe.db.get_value("Sales Invoice", item.reference_name, 'si_ref')

def on_submit(self, method):
	"""On Submit Custom Function for Payment Entry"""
	create_payment_entry(self)


def on_cancel(self, method):
	"""On Cancel Custom Function for Payment Entry"""
	cancel_payment_entry(self)


def on_trash(self, method):
	"""On Delete Custom Function for Payment Entry"""
	delete_payment_entry(self)


def create_payment_entry(self):
	"""Function to create Payment Entry

	This function is use to create Payment Entry from 
	one company to another company if company is authorized.

	Args:
		self (obj): The submited payment entry object
	"""

	def get_payment_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.paid_from = source.paid_from.replace(source_company_abbr, target_company_abbr)
			target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)

			if source.deductions:
				for index, i in enumerate(source.deductions):
					target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
			

		def payment_ref(source_doc, target_doc, source_parent):
			reference_name = source_doc.reference_name
			if source_parent.payment_type == 'Pay':
				if source_doc.reference_doctype == 'Purchase Invoice':
					target_doc.reference_name = frappe.db.get_value("Purchase Invoice", reference_name, 'pi_ref')
					target_doc.total_amount = frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'rounded_total') or frappe.db.get_value("Purchase Invoice", reference_name, 'total')
					target_doc.outstanding_amount = frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'outstanding_amount')

			if source_parent.payment_type == 'Receive':
				if source_doc.reference_doctype == 'Sales Invoice':
					target_doc.reference_name = frappe.db.get_value("Sales Invoice", reference_name, 'si_ref')
					target_doc.total_amount = frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'rounded_total') or frappe.db.get_value("Purchase Invoice", reference_name, 'total')
					target_doc.outstanding_amount = frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'outstanding_amount')
					target_doc.allocated_amount = min(target_doc.outstanding_amount - (frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'pay_amount_left')), source_doc.allocated_amount)

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
				},
			},
			"Payment Entry Reference": {
				"doctype": "Payment Entry Reference",
				"field_map": {},
				"field_no_map": {},
				"postprocess": payment_ref,
				"condition": lambda doc: doc.ref_invoice
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	# getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	if authority == "Authorized":
		pe = get_payment_entry(self.name)
		try:
			pe.naming_series = 'A' + pe.naming_series
			pe.series_value = self.series_value
			pe.save(ignore_permissions= True)
			self.db_set('pe_ref', pe.name)
			pe.submit()
		except Exception as e:
			frappe.db.rollback()
			frappe.throw(e)
	
	if authority == "Unauthorized":
		if not self.pe_ref:
			for item in self.references:
				if item.reference_doctype == "Sales Invoice":
					diff_value = frappe.db.get_value("Sales Invoice", item.reference_name, 'pay_amount_left')

					if item.allocated_amount > diff_value:
						frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
					else:
						frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value - item.allocated_amount)
				
				if item.reference_doctype == "Purchase Invoice":
					diff_value = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pay_amount_left')

					if item.allocated_amount > diff_value:
						frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
					else:
						frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value - item.allocated_amount)


# Cancel Invoice on Cancel
def cancel_payment_entry(self):
	if self.pe_ref:
		pe = frappe.get_doc("Payment Entry", {'pe_ref':self.name})
	else:
		pe = None
	authority = frappe.get_value("Company", self.company, 'authority')
	if authority == "Unauthorized":
		if not self.pe_ref:
			for item in self.references:
				if item.reference_doctype == "Sales Invoice":
					diff_value = frappe.db.get_value("Sales Invoice", item.reference_name, 'pay_amount_left')

					frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value + item.allocated_amount)
				
				if item.reference_doctype == "Purchase Invoice":
					diff_value = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pay_amount_left')

					frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value + item.allocated_amount)


	if pe:
		if pe.docstatus == 1:
			pe.flags.ignore_permissions = True
			try:
				pe.cancel()
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)
	
	

def delete_payment_entry(self):
	ref_name = self.pe_ref
	try:
		frappe.db.set_value("Payment Entry", self.name, 'pe_ref', '')    
		frappe.db.set_value("Payment Entry", ref_name, 'pe_ref', '')
		frappe.delete_doc("Payment Entry", ref_name, force = 1)
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)
	

def get_sales_person(self):
	for row in self.references:
		if row.reference_doctype == "Sales Invoice":
			row.sales_person = frappe.db.get_value(row.reference_doctype,row.reference_name,'sales_partner')
	