# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def execute(filters=None):
	if not filters: filters = {}

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)
	conditions = ''
	if filters.get("to_date"):
		conditions += " AND pl.posting_date <= '%s'" % filters["to_date"]
	if filters.get("warehouse"):
		conditions += f" AND pli.warehouse = '{filters['warehouse']}'"
	
	data = []
	for item in sorted(iwb_map):
		if not filters.get("item") or filters.get("item") == item:
			for wh in sorted(iwb_map[item]):
				for batch in sorted(iwb_map[item][wh]):
					qty_dict = iwb_map[item][wh][batch]
					picked_qty = frappe.db.sql(f"""
					SELECT sum(pli.qty - pli.delivered_qty) FROM `tabPick List Item` as pli JOIN `tabPick List` as pl on pli.parent = pl.name 
					WHERE pli.item_code = '{item}' AND pli.warehouse='{wh}' AND pli.batch_no='{batch}' and pl.docstatus = 1 {conditions} AND pl.company = '{filters.get('company')}'
					""")[0][0] or 0.0
					lot_no = frappe.db.get_value("Batch", batch, 'lot_no')
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						data.append([
							item,
							lot_no,
							flt(qty_dict.bal_qty, float_precision),
							picked_qty,
							flt(qty_dict.bal_qty, float_precision) - picked_qty,
							flt(qty_dict.opening_qty, float_precision),
							flt(qty_dict.in_qty, float_precision),
							flt(qty_dict.out_qty, float_precision), 
							wh,
						])

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item Code") + ":Link/Item:200"] + \
		[_("Lot No") + "::100"] + \
		[_("Balance Qty") + ":Float:80"] + \
		[_("Picked Qty") + ":Float:80"] + \
		[_("Remaining Qty") + ":Float:80"] + \
		[_("Opening Qty") + ":Float:90"] + \
		[_("In Qty") + ":Float:80"] + \
		[_("Out Qty") + ":Float:80"] + \
		[_("Warehouse") + ":Link/Item:150"]

	return columns


def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))
	
	conditions += f" and company = '{filters.get('company')}'"

	if filters.get("warehouse"):
		conditions += f" and warehouse = '{filters.get('warehouse')}'"

	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select item_code, batch_no, warehouse, posting_date, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry`
		where docstatus < 2 and ifnull(batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code, warehouse
		order by item_code, warehouse""" %
		conditions, as_dict=1)


def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
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
	return iwb_map


def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map