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
	
	data = []
	for item in sorted(iwb_map):
		if not filters.get("item") or filters.get("item") == item:
			for batch in sorted(iwb_map[item]):
				qty_dict = iwb_map[item][batch]
				lot_no = frappe.db.get_value("Batch", batch, 'lot_no')
				picked_qty = frappe.db.sql(f"""
				SELECT sum(pli.qty - (pli.wastage_qty + pli.delivered_qty)) FROM `tabPick List Item` as pli JOIN `tabPick List` as pl on pli.parent = pl.name 
				WHERE pli.item_code = '{item}' AND pli.batch_no='{batch}' and pl.docstatus = 1 {conditions} AND pl.company = '{filters.get('company')}'
				""")[0][0] or 0.0
				detail_button = """
					<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;' 
						type='button' item-code='{}' batch-no='{}' company='{}' from-date='{}' to-date='{}' bal-qty='{}', total-picked-qty = '{}' total-remaining-qty='{}' lot-no='{}'
						onClick='get_picked_item_details(this.getAttribute("item-code"), this.getAttribute("batch-no"), this.getAttribute("company"), this.getAttribute("from-date"), this.getAttribute("to-date"), this.getAttribute("bal-qty"), this.getAttribute("total-picked-qty"), this.getAttribute("total-remaining-qty"), this.getAttribute("lot-no"))'>View</button>""".format(item, batch, filters.get('company'), filters.get('from_date'), filters.get('to_date'), flt(qty_dict.bal_qty, float_precision), picked_qty, flt(qty_dict.bal_qty, float_precision) - picked_qty, lot_no)
				# frappe.throw(str(detail_button))
				if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
					data.append([
						item,
						lot_no,
						flt(qty_dict.bal_qty, float_precision),
						picked_qty,
						flt(qty_dict.bal_qty, float_precision) - picked_qty,
						detail_button,
						flt(qty_dict.opening_qty, float_precision),
						flt(qty_dict.in_qty, float_precision),
						flt(qty_dict.out_qty, float_precision), 
						batch,
					])

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [_("Item Code") + ":Link/Item:200"] + \
		[_("Lot No") + "::100"] + \
		[_("Balance Qty") + ":Float:80"] + \
		[_("Picked Qty") + ":Float:80"] + \
		[_("Remaining Qty") + ":Float:80"] + \
		[_("Picked Details") + ":Data:80"] + \
		[_("Opening Qty") + ":Float:90"] + \
		[_("In Qty") + ":Float:80"] + \
		[_("Out Qty") + ":Float:80"] + \
		[_("Batch") + ":Link/Batch:150"]

	return columns


def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and sle.posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))
	
	if filters.get("item_group"):
		conditions += " and i.item_group = '%s'" % filters["item_group"]
	
	if filters.get("item_code"):
		conditions += " and sle.item_code = '%s'" % filters["item_code"]
	
	if filters.get("tile_quality"):
		conditions += f" and i.tile_quality = '{filters.tile_quality}'"
	
	conditions += f" and company = '{filters.get('company')}'"

	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sle.item_code, sle.batch_no, sle.posting_date, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry` as sle JOIN `tabItem` as i on i.item_code = sle.item_code
		where sle.docstatus < 2 and ifnull(sle.batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code
		order by item_code""" %
		conditions, as_dict=1)


def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {})\
			.setdefault(d.batch_no, frappe._dict({
				"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
			}))
		qty_dict = iwb_map[d.item_code][d.batch_no]
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