# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, cint

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 165
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 164
		},
		{
			"label": _("Punch No"),
			"fieldname": "punch_no",
			"fieldtype": "Data",			
			"width": 80
		},
		{
			"fieldname": "so_no",
			"label": _("No of Sales Order"),
			"fieldtype": "Int",
			"width": 164
		},	
		{
			"fieldname": "packing_type",
			"label": _("Packing Type"),
			"fieldtype": "Link",
			"options": "Packing Type",
			"width": 164
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 170
		},
		{
			"fieldname": "ordered_qty",
			"label": _("Ordered Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "delivered_qty",
			"label": _("Delivered Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "pending_qty",
			"label": _("Pending Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "total_pending_qty",
			"label": _("Total Pending Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "to_pick",
			"label": _("To Pick Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "total_to_pick",
			"label": _("Total To Pick Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "picked_total",
			"label": _("Picked Total"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "actual_qty",
			"label": _("Actual Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "to_manufacture",
			"label": _("To Manufacture"),
			"fieldtype": "Float",
			"width": 120
		}
	]

	return columns

def get_data(filters):
	conditions = get_conditions(filters)
	total_qty_data_conditions = get_conditions_total_qty(filters)
	data = frappe.db.sql(f"""
		SELECT
			so.lock_picked_qty, soi.`item_code`, SUM(soi.delivered_qty) as delivered_qty, i.`item_name`, i.`item_group`, SUM(soi.`qty`) as `ordered_qty`, SUM(soi.`qty` - soi.delivered_qty) as `pending_qty`,
			SUM(soi.picked_qty - soi.delivered_qty - soi.wastage_qty) as picked_total, SUM(soi.qty - soi.picked_qty) as to_pick,
			SUM(soi.`picked_qty`) as `picked_qty`, soi.packing_type as packing_type, i.punch_no, COUNT(DISTINCT soi.parent) as so_no
		FROM
			`tabSales Order Item` as soi JOIN
			`tabSales Order` as so ON so.`name` = soi.`parent` AND so.`docstatus` = 1 JOIN
			`tabItem` as i on i.`name` = soi.`item_code`
		WHERE
			{conditions}
			AND so.docstatus = 1
			AND soi.`qty` != soi.delivered_qty
		GROUP BY
			soi.`item_code`, soi.packing_type
	""", as_dict = True)

	total_qty_data = frappe.db.sql(f"""
		SELECT
			so.lock_picked_qty, soi.`item_code`, SUM(soi.`qty` - soi.delivered_qty) as `total_pending_qty`, SUM(soi.qty - soi.picked_qty) as total_to_pick,
			soi.packing_type as packing_type
		FROM
			`tabSales Order Item` as soi JOIN
			`tabSales Order` as so ON so.`name` = soi.`parent` AND so.`docstatus` = 1 JOIN
			`tabItem` as i on i.`name` = soi.`item_code`
		WHERE
			{total_qty_data_conditions}
			AND so.docstatus = 1
			AND soi.`qty` != soi.delivered_qty
		GROUP BY
			soi.`item_code`, soi.packing_type
	""", as_dict = True)

	
	total_qty_data_map = {}
	for row in total_qty_data:
		total_qty_data_map[row.item_code,row.packing_type] = row

	for item in data:
		actual_qty = frappe.db.sql(f"""
		SELECT
			SUM(sle.`actual_qty`) AS `actual_qty`
		FROM
			`tabStock Ledger Entry` as sle
			JOIN `tabBatch` as batch on batch.name = sle.batch_no
		WHERE
			sle.`item_code`='{item['item_code']}'
			and sle.`company` = '{filters['company']}'
			and batch.`packing_type` = '{item['packing_type']}'
		""")

		item['actual_qty'] = actual_qty[0][0] or 0.0
		item['to_manufacture'] = item['pending_qty'] - item['actual_qty'] if item['pending_qty'] > item['actual_qty'] else 0

		item['total_pending_qty'] = total_qty_data_map[item.item_code,item.packing_type].total_pending_qty
		item['total_to_pick'] = total_qty_data_map[item.item_code,item.packing_type].total_to_pick

	return data

def get_conditions(filters):
	conditions = ''
	if filters.get('company'):
		conditions += f"so.`company` = '{filters.get('company')}'"

	if filters.get('item_group'):
		conditions += f" AND i.`item_group` = '{filters.get('item_group')}'"

	if filters.get('show_locked_qty'):
		conditions += f" AND so.`lock_picked_qty` = '{filters.get('show_locked_qty')}'"

	if filters.get('item_code'):
		conditions += f" AND soi.`item_code` = '{filters.get('item_code')}'"
	
	if filters.get('order_priority'):
		conditions += f" AND soi.`order_item_priority` >= '{cint(filters.get('order_priority'))}'"
	
	conditions += " AND so.status not in ('On Hold', 'Completed' , 'Closed')"
	
	return conditions

def get_conditions_total_qty(filters):
	conditions = ''
	if filters.get('company'):
		conditions += f"so.`company` = '{filters.get('company')}'"
	
	if filters.get('item_group'):
		conditions += f" AND i.`item_group` = '{filters.get('item_group')}'"
	
	if filters.get('item_code'):
		conditions += f" AND soi.`item_code` = '{filters.get('item_code')}'"
	
	if filters.get('show_locked_qty'):
		conditions += f" AND so.`lock_picked_qty` = '{filters.get('show_locked_qty')}'"
	
	conditions += " AND so.status not in ('On Hold', 'Completed' , 'Closed')"
	
	return conditions
