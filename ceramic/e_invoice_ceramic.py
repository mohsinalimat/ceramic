import frappe
import re
import jwt
from frappe import _
from frappe.utils.data import cstr, cint, flt
from frappe.utils import getdate
from erpnext.regional.india.e_invoice.utils import (GSPConnector,raise_document_name_too_long_error,read_json,get_transaction_details,\
	validate_mandatory_fields,get_doc_details,get_overseas_address_details,get_return_doc_reference,\
	get_eway_bill_details,validate_totals,show_link_to_error_log,santize_einvoice_fields,safe_json_load,get_payment_details,\
	validate_eligibility,update_item_taxes,get_invoice_value_details,get_party_details,update_other_charges)

from erpnext.regional.india.utils import get_gst_accounts,get_place_of_supply
import json

GST_INVOICE_NUMBER_FORMAT = re.compile(r"^[a-zA-Z0-9\-/]+$")   #alphanumeric and - /

def validate_einvoice_fields(doc):
	invoice_eligible = validate_eligibility(doc)

	if not invoice_eligible:
		return

	# Finbyz Changes Start: dont change posting date after irn generated
	if doc.irn and doc.docstatus == 0 and doc._action == 'save':
		if doc.posting_date != frappe.db.get_value("Sales Invoice",doc.name,"posting_date"):
			frappe.throw(_('You cannot edit the invoice after generating IRN'), title=_('Edit Not Allowed'))

	# Finbyz Changes End
	if doc.docstatus == 0 and doc._action == 'save':
		if doc.irn and not doc.eway_bill_cancelled and doc.grand_total != frappe.db.get_value("Sales Invoice",doc.name,"grand_total"):# Finbyz Changes:
			frappe.throw(_('You cannot edit the invoice after generating IRN'), title=_('Edit Not Allowed'))
		if len(doc.name) > 16 and doc.authority == 'Authorized':# Finbyz Changes
			raise_document_name_too_long_error()

	elif doc.docstatus == 1 and doc._action == 'submit' and not doc.irn and doc.irn_cancelled == 0: # finbyz 
		frappe.throw(_('You must generate IRN before submitting the document.'), title=_('Missing IRN'))

	elif doc.irn and doc.docstatus == 2 and doc._action == 'cancel' and not doc.irn_cancelled:
		frappe.throw(_('You must cancel IRN before cancelling the document.'), title=_('Cancel Not Allowed'))

def make_einvoice(invoice):
	validate_mandatory_fields(invoice)

	schema = read_json('einv_template')

	transaction_details = get_transaction_details(invoice)
	item_list = get_item_list(invoice)
	doc_details = get_doc_details(invoice)
	invoice_value_details = get_invoice_value_details(invoice)
	seller_details = get_party_details(invoice.company_address)

	if invoice.gst_category == 'Overseas':
		buyer_details = get_overseas_address_details(invoice.customer_address)
	else:
		buyer_details = get_party_details(invoice.customer_address)
		place_of_supply = get_place_of_supply(invoice, invoice.doctype)
		if place_of_supply:
			place_of_supply = place_of_supply.split('-')[0]
		else:
			place_of_supply = invoice.billing_address_gstin[:2]
		buyer_details.update(dict(place_of_supply=place_of_supply))

	seller_details.update(dict(legal_name=invoice.company))
	buyer_details.update(dict(legal_name=invoice.billing_address_title or invoice.customer_name or invoice.customer)) # finbyz change add billing address title
	
	shipping_details = payment_details = prev_doc_details = eway_bill_details = frappe._dict({})
	if invoice.shipping_address_name and invoice.customer_address != invoice.shipping_address_name:
		if invoice.gst_category == 'Overseas':
			shipping_details = get_overseas_address_details(invoice.shipping_address_name)
		else:
			shipping_details = get_party_details(invoice.shipping_address_name, is_shipping_address=True)
	
	if invoice.is_pos and invoice.base_paid_amount:
		payment_details = get_payment_details(invoice)
	
	if invoice.is_return and invoice.return_against:
		prev_doc_details = get_return_doc_reference(invoice)

	if invoice.transporter and flt(invoice.distance) and not invoice.is_return:
		eway_bill_details = get_eway_bill_details(invoice)

	# not yet implemented
	dispatch_details = period_details = export_details = frappe._dict({})

	einvoice = schema.format(
		transaction_details=transaction_details, doc_details=doc_details, dispatch_details=dispatch_details,
		seller_details=seller_details, buyer_details=buyer_details, shipping_details=shipping_details,
		item_list=item_list, invoice_value_details=invoice_value_details, payment_details=payment_details,
		period_details=period_details, prev_doc_details=prev_doc_details,
		export_details=export_details, eway_bill_details=eway_bill_details
	)
	
	try:
		einvoice = safe_json_load(einvoice)
		einvoice = santize_einvoice_fields(einvoice)
	except Exception:
		show_link_to_error_log(invoice, einvoice)

	validate_totals(einvoice)

	return einvoice


def get_item_list(invoice):
	item_list = []

	for d in invoice.items:
		einvoice_item_schema = read_json('einv_item_template')
		item = frappe._dict({})
		item.update(d.as_dict())

		item.sr_no = d.idx
		item.description = json.dumps(d.item_group or d.item_name)[1:-1] # finbyz change add item group

		item.qty = abs(item.qty)

		if invoice.apply_discount_on == 'Net Total' and invoice.discount_amount:
			item.discount_amount = abs(item.base_amount - item.base_net_amount)
		else:
			item.discount_amount = 0

		item.unit_rate = abs((abs(item.taxable_value) - item.discount_amount)/ item.qty)
		item.gross_amount = abs(item.taxable_value) + item.discount_amount
		item.taxable_value = abs(item.taxable_value)

		item.batch_expiry_date = frappe.db.get_value('Batch', d.batch_no, 'expiry_date') if d.batch_no else None
		item.batch_expiry_date = format_date(item.batch_expiry_date, 'dd/mm/yyyy') if item.batch_expiry_date else None
		#finbyz Changes
		if frappe.db.get_value('Item', d.item_code, 'is_stock_item') or frappe.db.get_value('Item', d.item_code, 'is_not_service_item'):
			item.is_service_item = 'N'  
		else:
			item.is_service_item = 'Y'
		#finbyz changes enditem.serial_no = ""

		item = update_item_taxes(invoice, item)
		
		item.total_value = abs(
			item.taxable_value + item.igst_amount + item.sgst_amount +
			item.cgst_amount + item.cess_amount + item.cess_nadv_amount + item.other_charges
		)
		einv_item = einvoice_item_schema.format(item=item)
		item_list.append(einv_item)

	return ', '.join(item_list)

# india utils.py

def validate_document_name(doc, method=None):
	"""Validate GST invoice number requirements."""
	country = frappe.get_cached_value("Company", doc.company, "country")

	# Date was chosen as start of next FY to avoid irritating current users.
	if country != "India" or getdate(doc.posting_date) < getdate("2021-04-01"):
		return

	if len(doc.name) > 16 and doc.authority == 'Authorized': #finbyz
		frappe.throw(_("Maximum length of document number should be 16 characters as per GST rules. Please change the naming series."))

	if not GST_INVOICE_NUMBER_FORMAT.match(doc.name):
		frappe.throw(_("Document name should only contain alphanumeric values, dash(-) and slash(/) characters as per GST rules. Please change the naming series."))
