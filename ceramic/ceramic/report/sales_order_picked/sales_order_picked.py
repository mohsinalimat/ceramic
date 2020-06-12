# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_conditions(filters):
	conditions = ""

	#conditions += " AND so.status not in ('Completed', 'Stopped', 'Closed', 'To Bill')"

	if filters.get('company'):
		conditions += " AND so.company = '%s'" % filters.get('company')

	if filters.get('sales_order'):
		conditions += " AND so.name = '%s'" % filters.get('sales_order')

	if filters.get('customer'):
		conditions += " AND so.customer = '%s'" % filters.get('customer')

	if filters.get('item_code'):
		conditions += " AND soi.item_code = '%s'" % filters.get('item_code')

	if filters.get('from_date'):
		conditions += " AND so.transaction_date >= '%s'" % filters.get('from_date')
	
	if filters.get('to_date'):
		conditions += " AND so.transaction_date <= '%s'" % filters.get('to_date')
	
	if filters.get('item_group'):
		conditions += "AND soi.item_group = '%s'" % filters.get('item_group')

	return conditions


def get_data(filters):

	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT 
			so.name as sales_order, so.transaction_date, so.customer, \
				soi.item_code, soi.qty, soi.picked_qty as picked_total, soi.delivered_qty as delivered, (soi.qty - soi.delivered_qty) as pending,\
				(soi.picked_qty - soi.delivered_qty - soi.wastage_qty) as picked_total, ((soi.qty- soi.delivered_qty) - (soi.picked_qty - soi.delivered_qty)) as to_pick, soi.base_rate, soi.base_amount, soi.name as sales_order_item, soi.item_group, \
				pni.name as plr_name, pni.parent as pick_list, pni.lot_no as picked_lot_no, pni.warehouse as picked_warehouse, pl.posting_date, (pni.qty -pni.delivered_qty - pni.wastage_qty) as picked_qty
		FROM 
			`tabSales Order Item` as soi 
		JOIN 
			`tabSales Order` as so ON so.name = soi.parent
		LEFT JOIN 
			`tabPick List Item` as pni on soi.name = pni.sales_order_item
		JOIN
			`tabPick List` as pl on (pni.parent = pl.name and pl.docstatus = 1)
		WHERE
			so.docstatus = 1%s
		Having
			pending > 0
		ORDER BY
			so.transaction_date, so.name, soi.name
		""" % conditions, as_dict = True)

	for idx in reversed(range(0, len(data))):
		if idx != 0:
			if data[idx].sales_order == data[idx-1].sales_order:
				#data[idx].sales_order = None
				data[idx].transaction_date = None
				#data[idx].customer = None
				if data[idx].sales_order_item == data[idx-1].sales_order_item:
					data[idx].qty = None
					data[idx].delivered = None
					data[idx].pending = None
					data[idx].picked_total = None
					data[idx].to_pick = None
					data[idx].item_code = None
					data[idx].item_group = None

	
	# for row in data_copy:
	# 	idx = insert_pick_list(data, row, idx + 1)

	return data


def get_columns():
	columns = [
		{
			"fieldname": "sales_order",
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 130
		},
		{
			"fieldname": "transaction_date",
			"label": _("SO Date"),
			"fieldtype": "Date",
			"width": 80
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 190
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 190
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 120
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "delivered",
			"label": _("Delivered"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "pending",
			"label": _("Pending Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "picked_total",
			"label": _("Picked Total"),
			"fieldtype": "Float",
			"width": 80
		},		
		{
			"fieldname": "to_pick",
			"label": _("To Pick"),
			"fieldtype": "Float",
			"width": 80
		},	
		{
			"fieldname": "pick_list",
			"label": _("Pick List"),
			"fieldtype": "Link",
			"options": "Pick List",
			"width": 100
		},
		{
			"fieldname": "picked_warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 140
		},
		{
			"fieldname": "picked_lot_no",
			"label": _("Lot No"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "posting_date",
			"label": _("Picked Date"),
			"fieldtype": "Date",
			"width": 90
		},
		{
			"fieldname": "picked_qty",
			"label": _("Picked Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "plr_name",
			"label": _("Picked Row"),
			"fieldtype": "data",
			"width": 80
		}		
	]

	return columns
