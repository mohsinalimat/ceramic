# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe,erpnext,json
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.accounts.utils import get_outstanding_invoices,get_account_currency,get_allow_cost_center_in_entry_of_bs_account
from erpnext.controllers.accounts_controller import get_supplier_block_status
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.doctype.payment_entry.payment_entry import get_negative_outstanding_invoices,get_orders_to_be_billed, get_outstanding_reference_documents
from six import string_types

class PrimaryCustomerPayment(Document):
	def validate(self):
		self.clear_unallocated_reference_document_rows()
		self.set_amounts()
	
	def clear_unallocated_reference_document_rows(self):
		self.set("references", self.get("references", {"allocated_amount": ["not in", [0, None, ""]]}))
		frappe.db.sql("""delete from `tabPrimary Customer Payment Reference`
			where parent = %s and allocated_amount = 0""", self.name)
	
	def set_amounts(self):
		self.set_amounts_in_company_currency
		self.set_total_allocated_amount()
		self.set_unallocated_amount()
		self.set_difference_amount()
	
	def set_amounts_in_company_currency(self):
		self.base_paid_amount, self.base_received_amount, self.difference_amount = 0, 0, 0
		if self.paid_amount:
			self.base_paid_amount = flt(flt(self.paid_amount) * flt(self.source_exchange_rate),
				self.precision("base_paid_amount"))

		if self.received_amount:
			self.base_received_amount = flt(flt(self.received_amount) * flt(self.target_exchange_rate),
				self.precision("base_received_amount"))

	def set_total_allocated_amount(self):
		if self.payment_type == "Internal Transfer":
			return

		total_allocated_amount, base_total_allocated_amount = 0, 0
		for d in self.get("references"):
			if d.allocated_amount:
				total_allocated_amount += flt(d.allocated_amount)
				base_total_allocated_amount += flt(flt(d.allocated_amount) * flt(d.exchange_rate),
					self.precision("base_paid_amount"))

		self.total_allocated_amount = abs(total_allocated_amount)
		self.base_total_allocated_amount = abs(base_total_allocated_amount)

	def set_unallocated_amount(self):
		self.unallocated_amount = 0
		if self.primary_customer:
			frappe.msgprint('Primary Customer Called')
			if self.payment_type == "Receive" \
				and self.total_allocated_amount < self.paid_amount :
						frappe.msgprint('unallocated amount Called')
						self.unallocated_amount = (self.paid_amount -
						self.total_allocated_amount) 


	def set_difference_amount(self):
		base_unallocated_amount = flt(self.unallocated_amount) * (flt(self.source_exchange_rate)
		if self.payment_type == "Receive" else flt(self.target_exchange_rate))
		base_party_amount = flt(self.base_total_allocated_amount) + flt(base_unallocated_amount)
	
		if self.payment_type == "Receive":
			self.difference_amount = base_party_amount - self.base_received_amount
		else:
			self.difference_amount = self.base_paid_amount - flt(self.base_received_amount)

		self.difference_amount = flt(self.difference_amount ,
			self.precision("difference_amount"))



@frappe.whitelist()
def get_primary_customer_reference_documents(args):
	if isinstance(args, string_types):
		args = json.loads(args)
	customer_list = frappe.get_list("Sales Invoice",{'primary_customer':args.get('primary_customer'),'outstanding_amount':('>',0)},'customer')
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

