# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe import _, scrub, utils
from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries

class UnlinkPaymentEntries(Document):
	pass

@frappe.whitelist()
def get_invoices_detail(company, party_type, from_date=None, to_date=None, party=None, primary_customer=None):
	conditions = ""
	if not party and not primary_customer:
		frappe.throw(_("Enter Either Party or Primary Customer"))
	voucher_type = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
	doc = frappe.get_doc({"doctype": voucher_type})
	if party:
		conditions += " and %s = '%s'" % (party_type,party)
	if primary_customer and hasattr(doc, 'primary_customer'):
		conditions += " and primary_customer = '%s'" % primary_customer
	
	if from_date:
		conditions += " and posting_date >= '%s'" % from_date
	if to_date:
		conditions += " and posting_date <= '%s'" % to_date 
	
	return frappe.db.sql("""
			select 
				"{voucher_type}" as voucher_type, name as voucher_no, grand_total, posting_date
			from 
				`tab{voucher_type}`
			where
				company = %s and docstatus = 1 
				{conditions}
			order by
				posting_date, name
			""".format(**{
				"conditions": conditions,
				"voucher_type": voucher_type
			}),(company),as_dict= True)

@frappe.whitelist()
def unlink_all_invoices(invoice_type, invoice_number):
	invoice_doc = frappe.get_doc(invoice_type, invoice_number)
	unlink_ref_doc_from_payment_entries(invoice_doc)
	return "Unlinked All Invoices"
	
		
