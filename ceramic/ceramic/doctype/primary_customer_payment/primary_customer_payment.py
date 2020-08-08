# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe,erpnext,json
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, flt
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
		self.set_amounts()
	
	# it will clear Primary Customer Payment Reference entries where allocated_amount is 0
	def clear_unallocated_reference_document_rows(self):
		self.set("references", self.get("references", {"allocated_amount": ["not in", [0, None, ""]]}))
		frappe.db.sql("""delete from `tabPrimary Customer Payment Reference`
			where parent = %s and allocated_amount = 0""", self.name)

	def on_submit(self):
		self.create_primay_customer_payment_entry()

	def before_cancel(self):
		self.cancel_primay_customer_payment_entry()
	
	def create_primay_customer_payment_entry(self):
		reference_dict={}
		final_reference_dict = defaultdict(list)
		references_has_primary_customer = False
		for reference in self.references:
			#reference_dict=dict([(reference.customer,reference.name)])
			#final_reference_dict[reference.customer].append(reference.name)

			#it will create dict for Primary Customer Payment Reference Entries
			reference_dict=dict(([(reference.customer,[{reference.reference_doctype,reference.reference_name,reference.due_date,reference.total_amount,reference.outstanding_amount,reference.allocated_amount}])]))
			# if primary customer is equal to customer selected from Primary Customer Payment Reference then it will append all values with unallocated amount
			if reference.customer == self.primary_customer and references_has_primary_customer==False:
				references_has_primary_customer = True
				# if reference_dict have 1 customer with multiple invoices than create a dict with key = customer and values = multiple values
				# example
				# first entry: Type= Sales Invoice, Name = OAOSI20212100129, Customer = A J Enterprise Bihpuria Assam, Total Amount = 50000, Outstanding Amount = 1000
				# second entry: Type= Sales Invoice, Name = SI20212100129, Customer = A J Enterprise Bihpuria Assam, Total Amount = 10000, Outstanding Amount = 500
				# dict : {key:A J Enterprise Bihpuria Assam, values: {Name = OAOSI20212100129,Total Amount = 50000, Outstanding Amount = 1000},{Type= Sales Invoice, Name = SI20212100129, Total Amount = 10000, Outstanding Amount = 500}
				final_reference_dict[reference.customer].append({'reference_doctype':reference.reference_doctype,'reference_name':reference.reference_name,'due_date':reference.due_date,'total_amount':reference.total_amount,'outstanding_amount':reference.outstanding_amount,'allocated_amount':reference.allocated_amount,'unallocated_amount':self.unallocated_amount})	
			# if not primary customer selected then unallocated amount will be 0
			else:
				final_reference_dict[reference.customer].append({'reference_doctype':reference.reference_doctype,'reference_name':reference.reference_name,'due_date':reference.due_date,'total_amount':reference.total_amount,'outstanding_amount':reference.outstanding_amount,'allocated_amount':reference.allocated_amount,'unallocated_amount':0.0})
		if references_has_primary_customer == False:
			if self.unallocated_amount>0:
				final_reference_dict[self.primary_customer].append({'allocated_amount':0.0,'unallocated_amount':self.unallocated_amount})

		
		# iterate loop over dict created from Primary Customer Payment Reference Entries and create new Payment Entry
		for key,invoices in final_reference_dict.items():
			payment_entry=frappe.new_doc("Payment Entry") #create new payment entry(payment_entry)
			payment_entry.posting_date = self.posting_date
			payment_entry.payment_type="Receive"
			payment_entry.company=self.company
			payment_entry.mode_of_payment=self.mode_of_payment
			payment_entry.party=key # key = Name of the Customer
			payment_entry.party_type="Customer"
			payment_entry.party_name=key
			payment_entry.primary_customer=self.primary_customer
			payment_entry.received_amount = 1
			payment_entry.paid_to=self.paid_to
			payment_entry.reference_doctype = self.doctype
			payment_entry.reference_docname = self.name
			payment_entry.reference_no = self.reference_no
			payment_entry.reference_date = self.reference_date
			
			#payment_entry.paid_from_account_currency = self.paid_from_account_currency
			#payment_entry.paid_to_account_currency = self.paid_to_account_currency
			#payment_entry.paid_to_account_balance=self.paid_to_account_balance
			#payment_entry.paid_amount=self.paid_amount
			#payment_entry.total_allocated_amount=self.total_allocated_amount
			#payment_entry.unallocated_amount=self.unallocated_amount
			paid_amount = 0.0
			unallocated_amount = 0.0
			# iterate loop over multiple invoices where there are multiple customers available
			for invoice in invoices:
				# paid amount should be allocated amount + unallocated amount
				paid_amount += invoice['allocated_amount'] + invoice['unallocated_amount']
				unallocated_amount += invoice['unallocated_amount']
				if invoice['allocated_amount']:
					payment_entry.append("references",{
						'reference_doctype': invoice['reference_doctype'],
						'reference_name':invoice['reference_name'],
						'total_amount':invoice['total_amount'],
						'outstanding_amount':invoice['outstanding_amount'],
						'allocated_amount':invoice['allocated_amount'],
						'due_date':invoice['due_date']
					})
				
			for deduction in self.deductions:
				paid_amount -= deduction.amount
				payment_entry.append("deductions",{
						"account": deduction.account,
						"cost_center": deduction.cost_center,
						"amount": deduction.amount
					})
			payment_entry.unallocated_amount = unallocated_amount
			payment_entry.paid_amount = paid_amount
			payment_entry.received_amount = payment_entry.paid_amount
			payment_entry.save(ignore_permissions=True)
			payment_entry.submit()
	
	def set_amounts(self):
		self.set_total_allocated_amount()
		self.set_unallocated_amount()
		self.set_difference_amount() 
	
	def set_total_allocated_amount(self):
		total_allocated_amount= 0
		for d in self.get("references"):
			if d.allocated_amount:
				total_allocated_amount += flt(d.allocated_amount)

		self.total_allocated_amount = abs(total_allocated_amount)
	

	def set_unallocated_amount(self):
		self.unallocated_amount = 0
		if self.primary_customer:
			total_deductions = sum([flt(d.amount) for d in self.get("deductions")])
			if self.payment_type == "Receive" \
				and self.total_allocated_amount < self.paid_amount + total_deductions:
					self.unallocated_amount = (self.received_amount + total_deductions - 
						self.total_allocated_amount)
	
	def set_difference_amount(self):
		party_amount = flt(self.total_allocated_amount) + flt(self.unallocated_amount)

		if self.payment_type == "Receive":
			self.difference_amount = party_amount - flt(self.received_amount)

		total_deductions = sum([flt(d.amount) for d in self.get("deductions")])

		self.difference_amount = flt(self.difference_amount - total_deductions,
			self.precision("difference_amount"))
		


	# it will cancel created primary customer payment entry using reference docytype and reference docname
	def cancel_primay_customer_payment_entry(self):
		cancel_entry=frappe.get_list("Payment Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		for row in cancel_entry:
			pe_doc = frappe.get_doc("Payment Entry",row.name)
			pe_doc.flags.ignore_permissions = True
			if pe_doc.docstatus == 1:
				pe_doc.cancel_it = True
				pe_doc.cancel()
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
	
	# customer_list- get list of the customer those are primary customer with current company and outstanding amount > 0 
	customer_list = frappe.get_list("Sales Invoice",{'primary_customer':args.get('primary_customer'),'company':args.get('company'),'outstanding_amount':('>',0)},'customer')
	#customer_list = set(customer_list)
	# unique_customer_list- it will remove duplicate entries in the customer_list
	unique_customer_list = list(set(val for dic in customer_list for val in dic.values()))
	#frappe.msgprint(str(unique_customer_list))
	invoices = []
	
	# iterate loop over every customer from the unique_customer_list and check that diff amount > 0
	for customer in unique_customer_list:
		args.update({'party': customer})
		data = get_outstanding_reference_documents(args)
		for invoice in data:
			diff_amt= frappe.db.get_value("Sales Invoice",invoice.voucher_no,"pay_amount_left")
			if diff_amt > 0:
				invoice.update({'party': customer})
				invoice.update({'diff_amt':diff_amt})
				invoices.append(invoice)
	#frappe.msgprint(str(invoices))
	return invoices



