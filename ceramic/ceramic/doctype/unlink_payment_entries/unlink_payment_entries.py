# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document
from frappe import _, scrub, utils
from frappe.utils import nowdate, flt
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
				"{voucher_type}" as voucher_type, name as voucher_no, {party_type} as party, grand_total, posting_date
			from 
				`tab{voucher_type}`
			where
				company = %s and docstatus = 1 
				{conditions}
			order by
				posting_date, name
			""".format(**{
				"conditions": conditions,
				"voucher_type": voucher_type,
				"party_type": party_type
			}),(company),as_dict= True)

@frappe.whitelist()
def unlink_all_invoices(company, invoice_type, invoice_number, grand_total,party_type,party):
	invoice_doc = frappe.get_doc(invoice_type, invoice_number)
	unlink_ref_doc_from_payment_entries(invoice_doc)
	invoice_doc.db_set("outstanding_amount",grand_total)
	related_inv = ""
	if invoice_doc.doctype == "Sales Invoice":
		related_inv = invoice_doc.si_ref
	elif invoice_doc.doctype == "Purchase Invoice":
		related_inv = invoice_doc.pi_ref
	
	if frappe.db.get_value("Company",company,"authority") == "Authorized" and related_inv:
		total = frappe.db.sql("""
			select sum(credit_in_account_currency-debit_in_account_currency)
			from `tabGL Entry`
			where 
				docstatus=1 and voucher_no ='{0}' and party_type ='{1}' and party='{2}' and (against_voucher is Null or against_voucher='{0}')
			""".format(invoice_number,party_type,party))
		if total:
			total_amount = total[0][0]
		else:
			total_amount = 0
		amount_against = frappe.db.get_value("GL Entry",{'against_voucher':invoice_number,'voucher_no':['not in', [invoice_number]]} ,['sum(credit_in_account_currency-debit_in_account_currency)'])
		difference_amount = abs(flt(total_amount))-abs(flt(amount_against)) 
		related_doc = frappe.get_doc(invoice_type, related_inv)
		related_doc.db_set("pay_amount_left",difference_amount)


	return "Unlinked All Invoices"


	
		
