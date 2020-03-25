# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today

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
			"fieldname": "actual_qty",
			"label": _("Actual Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "picked_qty",
			"label": _("Picked Qty"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "to_picked_qty",
			"label": _("TO Picked Qty"),
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

	data = frappe.db.sql(f"""
		SELECT
			soi.`item_code`, soi.`item_name`, i.`item_group`, SUM(soi.`qty`) as `ordered_qty`, 
			SUM(soi.`picked_qty`) as `picked_qty`, SUM(soi.`qty`) - SUM(soi.`picked_qty`) as `to_picked_qty`
		FROM
			`tabSales Order Item` as soi JOIN
			`tabSales Order` as so ON so.`name` = soi.`parent` AND so.`docstatus` = 1 JOIN
			`tabItem` as i on i.`name` = soi.`item_code`
		GROUP BY
			soi.`item_code`
	""", as_dict = True)

	for item in data:
		actual_qty = frappe.db.sql(f"""
		SELECT
			SUM(`actual_qty`) AS `actual_qty`
		FROM
			`tabStock Ledger Entry`
		WHERE
			`item_code`='{item['item_code']}'
			and `company` = '{filters['company']}'
		""")

		item['actual_qty'] = actual_qty[0][0] or 0.0
		item['to_manufacture'] = item['to_picked_qty'] - item['actual_qty'] if item['to_picked_qty'] > item['actual_qty'] else 0

	return data

def get_conditions(filters):
	conditions = ''
	if filters.get('company'):
		conditions += f""

	# if filters.get('item_group'):
	# 	conditions += f" AND sle.`item_group` = '{filters.get('item_group')}'"
	
	# if filters.get('item_code'):
	# 	conditions += f" AND sle.`item_code` = '{filters.get('item_code')}'"
	

	return conditions