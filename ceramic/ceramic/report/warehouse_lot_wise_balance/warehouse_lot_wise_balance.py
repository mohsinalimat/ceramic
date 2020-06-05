# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate

def execute(filters=None):
	if not filters: filters = {}

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []
	for item in sorted(iwb_map):
		for wh in sorted(iwb_map[item]):
			for batch in sorted(iwb_map[item][wh]):
				qty_dict = iwb_map[item][wh][batch]
				if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
					data.append([item, wh, batch, qty_dict.lot_no, flt(qty_dict.bal_qty, float_precision),
						 item_map[item]["stock_uom"]
					])

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item") + ":Link/Item:190"] + \
	[_("Warehouse") + ":Link/Warehouse:190"] + [_("Batch") + ":Link/Batch:150"] +  [_("Lot No") + "::100"] + \
	[_("Balance Qty") + ":Float:120"] + [_("UOM") + "::90"] \
	
	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))

	return conditions

#get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sle.item_code, sle.batch_no, sle.warehouse, sle.posting_date, sle.actual_qty, bt.lot_no
		from `tabStock Ledger Entry` sle join `tabBatch` bt on (sle.batch_no = bt.name)
		where sle.docstatus < 2 and ifnull(sle.batch_no, '') != '' %s
		group by sle.voucher_no, sle.batch_no, sle.item_code, sle.warehouse
		order by sle.item_code, sle.warehouse""" %
		conditions, as_dict=1)

def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0,
				"lot_no": ''
			}))
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.actual_qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.actual_qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
		qty_dict.lot_no = d.lot_no

	return iwb_map

def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map
