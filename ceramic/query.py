import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from six import string_types
import json
from erpnext.controllers.queries import get_doctype_wise_filters
from frappe.desk.reportview import get_match_cond, get_filters_cond

# from frappe.utils import (add_days, getdate, formatdate, date_diff,
# 	add_years, get_timestamp, nowdate, flt, cstr, add_months, get_last_day)
# from frappe.contacts.doctype.address.address import (get_address_display,
# 	get_default_address, get_company_address)
# from frappe.contacts.doctype.contact.contact import get_contact_details, get_default_contact
# from erpnext import get_company_currency
# from erpnext.accounts.party import get_regional_address_details,set_account_and_due_date,set_address_details,set_contact_details,set_other_values,set_price_list,get_address_tax_category,set_taxes,get_pyt_term_template

def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	cond = ""

	meta = frappe.get_meta("Batch")
	searchfield = meta.get_search_fields()

	searchfields = " or ".join(["batch." + field + " like %(txt)s" for field in searchfield])

	if filters.get("posting_date"):
		cond = "and (batch.expiry_date is null or batch.expiry_date >= %(posting_date)s)"
		
	if filters.get("customer"):
		cond = "and (batch.customer = %(customer)s or ifnull(batch.customer, '') = '') "

	batch_nos = None
	args = {
		'item_code': filters.get("item_code"),
		'warehouse': filters.get("warehouse"),
		'posting_date': filters.get('posting_date'),
		'txt': "%{0}%".format(txt),
		"start": start,
		"page_len": page_len
	}

	if args.get('warehouse'):
		batch_nos = frappe.db.sql("""select sle.batch_no, batch.lot_no, batch.packing_type, round(sum(sle.actual_qty),2), sle.stock_uom
				from `tabStock Ledger Entry` sle
				    INNER JOIN `tabBatch` batch on sle.batch_no = batch.name
				where
					sle.item_code = %(item_code)s
					and sle.warehouse = %(warehouse)s
					and batch.docstatus < 2
					and (sle.batch_no like %(txt)s or {searchfields})
					{0}
					{match_conditions}
				group by batch_no having sum(sle.actual_qty) > 0
				order by batch.expiry_date, sle.batch_no desc
				limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype), searchfields=searchfields), args)

	if batch_nos:
		return batch_nos
	else:
		return frappe.db.sql("""select batch.name, batch.lot_no, batch.packing_type, batch.expiry_date, sle.batch_no, batch.lot_no, round(sum(sle.actual_qty),2), sle.stock_uom from `tabBatch` batch
			JOIN `tabStock Ledger Entry` sle on sle.batch_no = batch.name
			where batch.item = %(item_code)s
			and batch.docstatus < 2
			and (sle.batch_no like %(txt)s or {searchfields})
			{0}
			{match_conditions} AND
			sle.company = '{company}'
			group by sle.batch_no having sum(sle.actual_qty) > 0
			order by batch.expiry_date, batch.name desc
			limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype), company=filters.get('company'), searchfields=searchfields), args)

def set_batches(self, warehouse_field):
	if self._action == 'submit':
		for row in self.items:
			if not row.get(warehouse_field):
				continue

			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			
			if has_batch_no:
				if not row.get('lot_no'):
					frappe.throw(_("Please set Lot No in row {}".format(row.idx)))

				batch_no = get_batch(row.as_dict())

				if batch_no:
					row.batch_no = batch_no

			elif row.lot_no:
				frappe.throw(_("Please clear Lot No for Item {} as it is not batch wise item in row {}".format(row.item_code, row.idx)))

@frappe.whitelist()
def get_batch(args):
	"""
	Returns the batch according to Item Code, Merge and Grade
		args = {
			"item_code": "",
			"lot_no": "",
		}
	"""
	def process_args(args):
		if isinstance(args, string_types):
			args = json.loads(args)

		args = frappe._dict(args)
		return args

	def validate_args(args):
		if not args.item_code:
			frappe.throw(_("Please specify Item Code"))

		elif not args.lot_no:
			frappe.throw(_("Please specify Lot NO"))

	args = process_args(args)

	validate_args(args)

	batch_nos = frappe.db.sql_list(""" select name from `tabBatch` 
		where lot_no = %s and item = %s """, (args.lot_no, args.item_code))

	batch_no = None
	if batch_nos:
		batch_no = batch_nos[0]

	return batch_no
			
@frappe.whitelist()
def warehouse_query(doctype, txt, searchfield, start, page_len, filters):
	# Should be used when item code is passed in filters.
	conditions, bin_conditions = [], []
	filter_dict = get_doctype_wise_filters(filters)

	sub_query = """ select round(`tabBin`.actual_qty, 2) from `tabBin`
		where `tabBin`.warehouse = `tabWarehouse`.name
		{bin_conditions} """.format(
		bin_conditions=get_filters_cond(doctype, filter_dict.get("Bin"),
			bin_conditions, ignore_permissions=True))

	query = """select `tabWarehouse`.name,
		CONCAT_WS(" : ", "Actual Qty", ifnull( ({sub_query}), 0) ) as actual_qty
			from `tabWarehouse`
		where
		   `tabWarehouse`.`{key}` like {txt}
			{fcond} {mcond}
		having
			ifnull( ({sub_query}), 0) > 0.0
		order by
			`tabWarehouse`.name desc
		
		limit
			{start}, {page_len}
		""".format(
			sub_query=sub_query,
			key=searchfield,
			fcond=get_filters_cond(doctype, filter_dict.get("Warehouse"), conditions),
			mcond=get_match_cond(doctype),
			start=start,
			page_len=page_len,
			txt=frappe.db.escape('%{0}%'.format(txt))
		)

	return frappe.db.sql(query)

# @frappe.whitelist()
# def get_party_details(party=None, account=None, party_type="Customer", company=None, posting_date=None,
# 	bill_date=None, price_list=None, currency=None, doctype=None, ignore_permissions=False, fetch_payment_terms_template=True,
# 	party_address=None, company_address=None, shipping_address=None, pos_profile=None):

# 	if not party:
# 		return {}
# 	if not frappe.db.exists(party_type, party):
# 		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))
# 	return _get_party_details(party, account, party_type,
# 		company, posting_date, bill_date, price_list, currency, doctype, ignore_permissions,
# 		fetch_payment_terms_template, party_address, company_address, shipping_address, pos_profile)

# def _get_party_details(party=None, account=None, party_type="Customer", company=None, posting_date=None,
# 	bill_date=None, price_list=None, currency=None, doctype=None, ignore_permissions=False,
# 	fetch_payment_terms_template=True, party_address=None, company_address=None,shipping_address=None, pos_profile=None):

# 	party_details = frappe._dict(set_account_and_due_date(party, account, party_type, company, posting_date, bill_date, doctype))
# 	party = party_details[party_type.lower()]

# 	if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
# 		frappe.throw(_("Not permitted for {0}").format(party), frappe.PermissionError)

# 	party = frappe.get_doc(party_type, party)
# 	currency = party.default_currency if party.get("default_currency") else get_company_currency(company)

# 	party_address, shipping_address = set_address_details(party_details, party, party_type, doctype, company, party_address, company_address, shipping_address)
# 	set_contact_details(party_details, party, party_type)
# 	set_other_values(party_details, party, party_type)
# 	set_price_list(party_details, party, party_type, price_list, pos_profile)

# 	party_details["tax_category"] = get_address_tax_category(party.get("tax_category"),
# 		party_address, shipping_address if party_type != "Supplier" else party_address)

# 	if not party_details.get("taxes_and_charges"):
# 		party_details["taxes_and_charges"] = set_taxes(party.name, party_type, posting_date, company,
# 			customer_group=party_details.customer_group, supplier_group=party_details.supplier_group, tax_category=party_details.tax_category,
# 			billing_address=party_address, shipping_address=shipping_address)

# 	if fetch_payment_terms_template:
# 		party_details["payment_terms_template"] = get_pyt_term_template(party.name, party_type, company)

# 	if not party_details.get("currency"):
# 		party_details["currency"] = currency

# 	# sales team
# 	if party_type=="Customer":
# 		party_details["sales_team"] = [{
# 			"sales_person": d.sales_person,
# 			"allocated_percentage": d.allocated_percentage or None,
# 			'regional_sales_manager': d.regional_sales_manager,
# 			'sales_manager': d.sales_manager
# 		} for d in party.get("sales_team")]

# 	# supplier tax withholding category
# 	if party_type == "Supplier" and party:
# 		party_details["supplier_tds"] = frappe.get_value(party_type, party.name, "tax_withholding_category")

# 	return party_details