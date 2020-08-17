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
					data.append(sub_data = {
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
		}
	]

	if filters.get('sales_order'):
		columns += [
		{
			"label": _("Sales Order Picked Qty"),
			"fieldname": "so_picked_qty",
			"fieldtype": "Float",
			"width": 70,
			"default": 0
		}
	]

	columns += [
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
		}
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
		group_placeholder = ', '.join(f"'{i}'" for i in filters["item_group"])
		conditions += " and i.item_group in (%s)" % group_placeholder
	
	if filters.get("item_code"):
		item_placeholder= ', '.join(f"'{i}'" for i in filters["item_code"])
		conditions += " and sle.item_code in (%s)" % item_placeholder

	if filters.get("not_in_item_code"):
		not_in_item_placeholder= ', '.join(f"'{i}'" for i in filters["not_in_item_code"])
		conditions += " and sle.item_code not in (%s)" % not_in_item_placeholder
	
	if filters.get("tile_quality"):
		tile_quality_placeholder = ', '.join(f"'{i}'" for i in filters["tile_quality"])
		conditions += " and i.tile_quality in (%s)" % tile_quality_placeholder
	
	if filters.get("packing_type"):
		packing_type_placeholder = ', '.join(f"'{i}'" for i in filters["packing_type"])
		conditions += " and batch.packing_type in (%s)" % packing_type_placeholder

	if filters.get("company"):
		conditions += " and sle.company = '%s'" % filters["company"]
	
	if filters.get("sales_order"):
		so_doc = frappe.get_doc("Sales Order", filters.sales_order)
		so_item_list = [row.item_code for row in so_doc.items]

		so_item_list_placeholder = ', '.join(f"'{i}'" for i in so_item_list)
		conditions += " and sle.item_code in (%s)" % so_item_list_placeholder

	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select sle.item_code, i.item_group, i.tile_quality, i.item_design, i.image as image, batch.lot_no, batch.packing_type, sle.batch_no, sle.posting_date, sum(actual_qty) as actual_qty
		from `tabStock Ledger Entry` as sle 
		JOIN `tabItem` as i on i.item_code = sle.item_code
		JOIN `tabBatch` as batch on batch.name = sle.batch_no
		where sle.docstatus < 2 and ifnull(sle.batch_no, '') != '' %s
		group by voucher_no, batch_no, item_code
		order by i.item_group, sle.item_code""" %
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
				SELECT pli.item_code, pli.batch_no, (pli.qty - (pli.wastage_qty + pli.delivered_qty)) as pickedqty
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
		group_placeholder= ', '.join(f"'{i}'" for i in filters["item_group"])
		conditions += " and pli.item_group in (%s)" % group_placeholder
	
	if filters.get("item_code"):
		item_placeholder= ', '.join(f"'{i}'" for i in filters["item_code"])
		conditions += " and pli.item_code in (%s)" % item_placeholder
	
	if filters.get("not_in_item_code"):
		not_in_item_placeholder= ', '.join(f"'{i}'" for i in filters["not_in_item_code"])
		conditions += " and pli.item_code not in (%s)" % not_in_item_placeholder
	
	
	if filters.get("tile_quality"):
		tile_quality_placeholder = ', '.join(f"'{i}'" for i in filters["tile_quality"])
		conditions += " and i.tile_quality in (%s)" % tile_quality_placeholder
	
	if filters.get("company"):
		conditions += " and pl.company = '%s'" % filters["company"]
	
	if filters.get("sales_order"):
		so_doc = frappe.get_doc("Sales Order", filters.sales_order)
		so_item_list = [row.item_code for row in so_doc.items]

		so_item_list_placeholder = ', '.join(f"'{i}'" for i in so_item_list)
		
		conditions += " and i.item_code in (%s)" % so_item_list_placeholder

	return conditions