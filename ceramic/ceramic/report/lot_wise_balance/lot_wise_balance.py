# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def execute(filters=None):
	if not filters: filters = {}
	
	if filters.get("item_group"):
		filters.item_group = tuple(filters.get("item_group"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	item_pick_map = get_picked_qty(filters,float_precision)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)
	conditions = ''
	if filters.get("to_date"):
		conditions += " AND pl.posting_date <= '%s'" % filters["to_date"]
	
	data = []
	for item in iwb_map:
		if not filters.get("item") or filters.get("item") == item:
			for batch in sorted(iwb_map[item]):
				qty_dict = iwb_map[item][batch]
				try:
					picked_qty = item_pick_map[item][batch].pickedqty
				except KeyError:
					picked_qty = 0.0
				# frappe.db.sql(f"""
				# SELECT sum(pli.qty - (pli.wastage_qty + pli.delivered_qty)) FROM `tabPick List Item` as pli JOIN `tabPick List` as pl on pli.parent = pl.name 
				# WHERE pli.item_code = '{item}' AND pli.batch_no='{batch}' and pl.docstatus = 1 {conditions} AND pl.company = '{filters.get('company')}'
				# """)[0][0] or 0.0
				detail_button = """
					<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;' 
						type='button' item-code='{}' batch-no='{}' company='{}' from-date='{}' to-date='{}' bal-qty='{}', total-picked-qty = '{}' total-remaining-qty='{}' lot-no='{}'
						onClick='get_picked_item_details(this.getAttribute("item-code"), this.getAttribute("batch-no"), this.getAttribute("company"), this.getAttribute("from-date"), this.getAttribute("to-date"), this.getAttribute("bal-qty"), this.getAttribute("total-picked-qty"), this.getAttribute("total-remaining-qty"), this.getAttribute("lot-no"))'>View</button>""".format(item, batch, filters.get('company'), filters.get('from_date'), filters.get('to_date'), flt(qty_dict.bal_qty, float_precision), picked_qty, flt(qty_dict.bal_qty, float_precision) - picked_qty, qty_dict.lot_no)
				# # frappe.throw(str(detail_button))
				if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
					data.append({
						'item_code': item,
						'lot_no': qty_dict.lot_no,
						'packing_type': qty_dict.packing_type,
						'balance_qty': flt(qty_dict.bal_qty, float_precision),
						'picked_qty': picked_qty,
						'remaining_qty': flt(qty_dict.bal_qty, float_precision) - picked_qty,
						'picked_detail': detail_button,
						'opening_qty': flt(qty_dict.opening_qty, float_precision),
						'in_qty': flt(qty_dict.in_qty, float_precision),
						'out_qty': flt(qty_dict.out_qty, float_precision), 
						'batch_no': batch,
						'item_group': qty_dict.item_group,
						'tile_quality': qty_dict.tile_quality,
						'item_design': qty_dict.item_design,
						'image': qty_dict.image
					})

	return columns, data

def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "link",
			"options": "Item",
			"width": 180
		},
		{
			"label": _("Lot No"),
			"fieldname": "lot_no",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Packing Type"),
			"fieldname": "packing_type",
			"fieldtype": "link",
			"options": "Packing Type",			
			"width": 80
		},		
		{
			"label": _("Balance Qty"),
			"fieldname": "balance_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Picked Qty"),
			"fieldname": "picked_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Remaining Qty"),
			"fieldname": "remaining_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Details"),
			"fieldname": "picked_detail",
			"fieldtype": "Data",
			"width": 70
		},
		{
			"label": _("Batch"),
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 100
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 180
		},
		{
			"label": _("Quality"),
			"fieldname": "tile_quality",
			"fieldtype": "Data",
			"width": 70
		},
		{
			"label": _("Item Design"),
			"fieldname": "item_design",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Opening Qty"),
			"fieldname": "opening_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("In Qty"),
			"fieldname": "in_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("Out Qty"),
			"fieldname": "out_qty",
			"fieldtype": "Float",
			"width": 80
		},
		{
			"label": _("image"),
			"fieldname": "image",
			"fieldtype": "data",
			"width": 80
		},
	]

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
		conditions += " and i.item_group = '%s'" % filters['item_group']
	
	if filters.get("item_code"):
		conditions += " and sle.item_code = '%s'" % filters["item_code"]
	
	if filters.get("tile_quality"):
		conditions += " and i.tile_quality = '%s'" % filters["tile_quality"]
	
	if filters.get("company"):
		conditions += " and sle.company = '%s'" % filters["company"]

	frappe.msgprint(f'Get condition: {conditions}')
	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sle.item_code, i.item_group, i.tile_quality, i.item_design, i.website_image as image, batch.lot_no, batch.packing_type, sle.batch_no, sle.posting_date, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry` as sle 
		JOIN `tabItem` as i on i.item_code = sle.item_code
		JOIN `tabBatch` as batch on batch.name = sle.batch_no
		where sle.docstatus < 2 and ifnull(sle.batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code
		order by i.item_group, i.item_code""" %
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
		qty_dict.lot_no = d.lot_no
		qty_dict.item_group = d.item_group
		qty_dict.tile_quality = d.tile_quality
		qty_dict.item_design = d.item_design
		qty_dict.packing_type = d.packing_type
		qty_dict.image = d.image
	return iwb_map


def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_group, item_name, description, stock_uom from tabItem", as_dict=1):
		item_map.setdefault(d.name, d)
	return item_map

def get_picked_qty(filters,float_precision):
	picked = get_picked_items(filters)
	picked_map = {}
	for d in picked:
		picked_map.setdefault(d.item_code, {})\
			.setdefault(d.batch_no, frappe._dict({
				"pickedqty": 0.0
			}))
		picked_dict = picked_map[d.item_code][d.batch_no]
		picked_dict.pickedqty = flt(picked_dict.pickedqty, float_precision) + flt(d.pickedqty, float_precision)

	return picked_map

def get_picked_items(filters):
	conditions = get_picked_conditions(filters)
	return frappe.db.sql(f"""
				SELECT pli.item_code, pli.batch_no, pli.warehouse, (pli.qty - (pli.wastage_qty + pli.delivered_qty)) as pickedqty
				FROM `tabPick List Item` as pli 
				JOIN `tabPick List` as pl on pli.parent = pl.name 
				JOIN `tabItem` as i on i.item_code = pli.item_code
				WHERE pl.docstatus = 1 {conditions}
				""", as_dict=1)
	
def get_picked_conditions(filters):
	conditions = ""

	if filters.get("to_date"):
		conditions += " and pl.posting_date <= '%s'" % filters["to_date"]
	else:
		frappe.throw(_("'To Date' is required"))
	
	if filters.get("item_group"):
		conditions += " and pli.item_group in '%s'" % filters["item_group"]
	
	if filters.get("item_code"):
		conditions += " and pli.item_code = '%s'" % filters["item_code"]
	
	if filters.get("tile_quality"):
		conditions += " and i.tile_quality = '%s'" % filters["tile_quality"]
	
	if filters.get("company"):
		conditions += " and pl.company = '%s'" % filters["company"]

	frappe.msgprint(conditions)
	return conditions