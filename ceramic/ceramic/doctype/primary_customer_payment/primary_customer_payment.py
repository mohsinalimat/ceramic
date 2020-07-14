# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe,erpnext,json
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate
from erpnext.accounts.utils import get_balance_on,get_account_currency
from erpnext.accounts.doctype.payment_entry.payment_entry import get_outstanding_reference_documents
from six import string_types
from collections import defaultdict
#from erpnext.controllers.accounts_controller import get_supplier_block_status
#from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
#from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account, get_bank_account_details
#from erpnext.setup.utils import get_exchange_rate


class PrimaryCustomerPayment(Document):
	def validate(self):
		self.clear_unallocated_reference_document_rows()
	
	def clear_unallocated_reference_document_rows(self):
		self.set("references", self.get("references", {"allocated_amount": ["not in", [0, None, ""]]}))
		frappe.db.sql("""delete from `tabPrimary Customer Payment Reference`
			where parent = %s and allocated_amount = 0""", self.name)

	def on_submit(self):
		self.create_primay_customer_payment_entry()

	def on_cancel(self):
		self.cancel_primay_customer_payment_entry()
	
	def create_primay_customer_payment_entry(self):
		reference_dict={}
		final_reference_dict = defaultdict(list)
		for reference in self.references:
			reference_dict=dict([(reference.customer,reference.name)])
			final_reference_dict[reference.customer].append(reference.name)
		
		for key,value in final_reference_dict.items():
			new_entry=frappe.new_doc("Payment Entry") #new payment entry(new_entry)
			new_entry.posting_date=nowdate()
			new_entry.payment_type="Receive"
			new_entry.company=self.company
			new_entry.mode_of_payment=self.mode_of_payment
			new_entry.party=key
			new_entry.party_type="Customer"
			new_entry.party_name=self.party_name
			new_entry.primary_customer=self.primary_customer
			new_entry.paid_from=self.paid_from
			new_entry.paid_to=self.paid_to
			new_entry.reference_doctype = self.doctype
			new_entry.reference_docname = self.name
			#new_entry.paid_from_account_currency = self.paid_from_account_currency
			#new_entry.paid_to_account_currency = self.paid_to_account_currency
			#new_entry.paid_to_account_balance=self.paid_to_account_balance
			new_entry.paid_amount=self.paid_amount
			new_entry.total_allocated_amount=self.total_allocated_amount
			new_entry.unallocated_amount=self.unallocated_amount


			for v in value:
				child_doc = frappe.get_doc("Primary Customer Payment Reference",v)
				new_entry.append("references",{
					'reference_doctype': v.reference_doctype,
					'reference_name':v.reference_name,
					'customer':v.customer,
					'total_amount':v.total_amount,
					'outstanding_amount':v.outstanding_amount,
					'allocated_amount':v.allocated_amount,
					'due_date':v.due_date
				})
			new_entry.save(ignore_permissions=True)
			new_entry.submit()
			
	def cancel_primay_customer_payment_entry(self):
		cancel_entry=frappe.get_list("Payment Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		for row in cancel_entry:
			pe_doc = frappe.get_doc("Payment Entry",row.name)
			pe_doc.flags.ignore_permissions = True
			try:
				pe_doc.cancel()
			except Exception as e:
				raise e
			pe_doc.db_set('reference_doctype','')
			pe_doc.db_set('reference_docname','')


@frappe.whitelist()
def get_account_details(account, date, cost_center=None):
	frappe.has_permission('Primary Customer Payment', throw=True)

	# to check if the passed account is accessible under reference doctype Payment Entry
	account_list = frappe.get_list('Account', {
		'name': account
	}, reference_doctype='Primary Customer Payment', limit=1)

	if not account_list:
		frappe.throw(_('Account: {0} is not permitted under Primary Customer Payment').format(account))

	account_balance = get_balance_on(account, date, cost_center=cost_center,
		ignore_account_permission=True)

	return frappe._dict({
		"account_currency": get_account_currency(account),
		"account_balance": account_balance,
		"account_type": frappe.db.get_value("Account", account, "account_type")
	})


@frappe.whitelist()
def get_primary_customer_reference_documents(args):
	if isinstance(args, string_types):
		args = json.loads(args)
	customer_list = frappe.get_list("Sales Invoice",{'primary_customer':args.get('primary_customer'),'company':args.get('company'),'outstanding_amount':('>',0)},'customer')
	#customer_list = set(customer_list)
	unique_customer_list = list(set(val for dic in customer_list for val in dic.values()))
	#frappe.msgprint(str(unique_customer_list))
	invoices = []
	for customer in unique_customer_list:
		args.update({'party': customer})
		data = get_outstanding_reference_documents(args)
		for invoice in data:
			invoice.update({'party': customer})
			invoices.append(invoice)
	#frappe.msgprint(str(invoices))
	return invoices



