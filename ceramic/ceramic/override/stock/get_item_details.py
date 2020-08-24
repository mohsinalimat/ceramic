import frappe
from frappe.utils import flt, cint
import json
from erpnext.stock.get_item_details import get_party_item_code, set_valuation_rate, update_party_blanket_order, get_price_list_rate, get_pos_profile_item_details, get_bin_details, get_gross_profit, get_batch_qty, get_so_reservation_for_item, get_serial_no, process_args, validate_item_details, get_basic_details, get_item_tax_template, get_item_tax_map
from erpnext.accounts.doctype.pricing_rule.pricing_rule import get_pricing_rule_for_item

from ceramic.ceramic.override.stock.batch import get_batch_no
from six import string_types, iteritems

@frappe.whitelist()
def get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
	"""
		args = {
			"item_code": "",
			"warehouse": None,
			"customer": "",
			"conversion_rate": 1.0,
			"selling_price_list": None,
			"price_list_currency": None,
			"plc_conversion_rate": 1.0,
			"doctype": "",
			"name": "",
			"supplier": None,
			"transaction_date": None,
			"conversion_rate": 1.0,
			"buying_price_list": None,
			"is_subcontracted": "Yes" / "No",
			"ignore_pricing_rule": 0/1
			"project": ""
			"set_warehouse": ""
		}
	"""

	args = process_args(args)
	item = frappe.get_cached_doc("Item", args.item_code)
	validate_item_details(args, item)

	out = get_basic_details(args, item, overwrite_warehouse)

	if isinstance(doc, string_types):
		doc = json.loads(doc)

	if doc and doc.get('doctype') == 'Purchase Invoice':
		args['bill_date'] = doc.get('bill_date')

	if doc:
		args['posting_date'] = doc.get('posting_date')
		args['transaction_date'] = doc.get('transaction_date')

	get_item_tax_template(args, item, out)
	out["item_tax_rate"] = get_item_tax_map(args.company, args.get("item_tax_template") if out.get("item_tax_template") is None \
		else out.get("item_tax_template"), as_json=True)

	get_party_item_code(args, item, out)

	set_valuation_rate(out, args)

	update_party_blanket_order(args, out)

	get_price_list_rate(args, item, out)

	if args.customer and cint(args.is_pos):
		out.update(get_pos_profile_item_details(args.company, args))

	if out.get("warehouse"):
		out.update(get_bin_details(args.item_code, out.warehouse))

	# update args with out, if key or value not exists
	for key, value in iteritems(out):
		if args.get(key) is None:
			args[key] = value

	data = get_pricing_rule_for_item(args, out.price_list_rate,
		doc, for_validate=for_validate)

	out.update(data)

	update_stock(args, out)

	if args.transaction_date and item.lead_time_days:
		out.schedule_date = out.lead_time_date = add_days(args.transaction_date,
			item.lead_time_days)

	if args.get("is_subcontracted") == "Yes":
		out.bom = args.get('bom') or get_default_bom(args.item_code)

	get_gross_profit(out)
	if args.doctype == 'Material Request':
		out.rate = args.rate or out.price_list_rate
		out.amount = flt(args.qty * out.rate)

	return out

def update_stock(args, out):
	if (args.get("doctype") == "Delivery Note" or
		(args.get("doctype") == "Sales Invoice" and args.get('update_stock'))) \
		and out.warehouse and out.stock_qty > 0:

		if out.has_batch_no and not args.get("batch_no"):
			out.batch_no = get_batch_no(out.item_code, out.warehouse, out.qty)
			actual_batch_qty = get_batch_qty(out.batch_no, out.warehouse, out.item_code)
			if actual_batch_qty:
				out.update(actual_batch_qty)

		if out.has_serial_no and args.get('batch_no'):
			reserved_so = get_so_reservation_for_item(args)
			out.batch_no = args.get('batch_no')
			out.serial_no = get_serial_no(out, args.serial_no, sales_order=reserved_so)

		elif out.has_serial_no:
			reserved_so = get_so_reservation_for_item(args)
			out.serial_no = get_serial_no(out, args.serial_no, sales_order=reserved_so)

