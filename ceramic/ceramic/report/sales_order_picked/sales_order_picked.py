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

	# if filters.get('pending_so'):
	# 	conditions += " AND so.status not in ('Completed', 'Stopped', 'Closed')"

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
		conditions += "AND i.item_group = '%s'" % filters.get('item_group')

	return conditions


def get_data(filters):

	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT 
			so.name as sales_order, so.transaction_date, so.customer, soi.item_code, soi.item_name, soi.qty, soi.base_rate, soi.base_amount, soi.name as sales_order_item, i.item_group
		FROM 
			`tabSales Order` as so LEFT JOIN `tabSales Order Item` as soi ON (so.name = soi.parent)
			JOIN `tabItem` as i on soi.item_code = i.name
		WHERE
			so.docstatus = 1 %s
		ORDER BY
			so.transaction_date
		""" % conditions, as_dict = True)

	data_copy = data[:]
	idx = 0

	for row in data_copy:
		idx = insert_pick_list(data, row, idx + 1)

	return data

def insert_pick_list(data, row, idx):

	dn_data = frappe.db.sql("""
		SELECT pni.parent as pick_list, pl.posting_date, pni.qty as picked_qty
		FROM `tabPick List` as pl LEFT JOIN `tabPick List Item` as pni ON (pl.name = pni.parent)
		WHERE 
			pl.docstatus = 1
			AND pni.sales_order_item = '%s'
		ORDER BY
			pl.posting_date
		""" % row.sales_order_item, as_dict = 1)

	total_qty_picked = 0.0
	if dn_data:
		row.pick_list = dn_data[0].pick_list
		row.posting_date = dn_data[0].posting_date
		row.picked_qty = dn_data[0].picked_qty
		total_qty_picked += dn_data[0].picked_qty

	for i in dn_data[1:]:
		data.insert(idx, i)
		total_qty_picked += i.picked_qty
		idx += 1

	row.picked_total = total_qty_picked
	row.pending_qty = row.qty - total_qty_picked

	return idx


def get_columns():
	columns = [
		{
			"fieldname": "sales_order",
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 100
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
			"width": 150
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 150
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "base_rate",
			"label": _("Rate"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "base_amount",
			"label": _("Amount"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "picked_total",
			"label": _("Picked Total"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "pending_qty",
			"label": _("Pending Qty"),
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
		}
	]

	return columns

def _get_columns():
	return [
		_("Sales Order") + ":Link/Sales Order:100",
		_("Date") + ":Date:100",
		_("Customer") + ":Link/Customer:100",
		_("Item Code") + ":Link/Item:100",
		_("Item Name") + ":Data:100",
		_("Qty") + ":Float:100",
		_("Rate") + ":Currency:100",
		_("Amount") + ":Currency:100",
		_("Delivered Qty") + ":Float:100",
		_("Pending Qty") + ":Float:100",
		_("Pick List") + ":Link/Pick List:100",
		_("Picked Date") + ":Date:100",
		_("Picked Qty") + ":Float:100",
	]
