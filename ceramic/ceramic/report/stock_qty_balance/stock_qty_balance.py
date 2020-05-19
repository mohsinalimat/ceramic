# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, now, date_diff
from erpnext.stock.utils import add_additional_uom_columns
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition

from erpnext.stock.report.stock_ageing.stock_ageing import get_fifo_queue, get_average_age

from six import iteritems

def execute(filters=None):
	if not filters: filters = {}

	from_date = filters.get('from_date')
	to_date = filters.get('to_date')

	include_uom = filters.get("include_uom")
	columns = get_columns(filters)
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	# if no stock ledger entry found return
	if not sle:
		return columns, []

	iwb_map = get_item_warehouse_map(filters, sle)
	item_map = get_item_details(items, sle, filters)
	# item_reorder_detail_map = get_item_reorder_details(item_map.keys())

	data = []
	conversion_factors = {}

	_func = lambda x: x[1]
	conditions = ''
	if filters.get("to_date"):
		conditions += " and pl.posting_date <= %s" % frappe.db.escape(filters.get("to_date"))

	for (company, item) in sorted(iwb_map):
		if item_map.get(item):
			qty_dict = iwb_map[(company, item)]
			item_reorder_level = 0
			item_reorder_qty = 0
			picked_qty = frappe.db.sql(f"""
				SELECT sum(pli.qty - (pli.wastage_qty + pli.delivered_qty)) FROM `tabPick List Item` as pli JOIN `tabPick List` as pl on pli.parent = pl.name
				WHERE pl.docstatus = 1 AND pli.item_code = '{item}' AND company = '{company}' {conditions}
			""")[0][0] or 0.0
			details_button = """
					<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;' 
						type='button' item-code='{}' company='{}' from-date='{}' to-date='{}' onClick='get_lot_wise_item_details(this.getAttribute("item-code"), this.getAttribute("company"), this.getAttribute("from-date"), this.getAttribute("to-date"))'>View</button>""".format(item, company, filters.get('from_date'), filters.get('to_date'))

			report_data = {
				'item_code': item,
				'punch_no': frappe.db.get_value("Item", item, 'punch_no') or '',
				'picked_qty': picked_qty,
				'company': company,
				'reorder_level': item_reorder_level,
				'reorder_qty': item_reorder_qty,
				"view": details_button
			}
			report_data.update(item_map[item])
			report_data.update(qty_dict)
			

			if include_uom:
				conversion_factors.setdefault(item, item_map[item].conversion_factor)
			
			report_data['remaining_qty'] = report_data['bal_qty'] - report_data['picked_qty']

			data.append(report_data)

	add_additional_uom_columns(columns, data, include_uom, conversion_factors)
	return columns, data

def get_columns(filters):
	"""return columns"""

	columns = [
		{"label": _("Item Code"), "fieldname": "item_code","fieldtype": "Link", "options": "Item", "width": 200},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 200},
		{"label": _("Punch No"), "fieldname": "punch_no", "fieldtype": "Data", "width": 100},
		{"label": _("Lot Wise Details"), "fieldname": "view", "fieldtype": "Data", "width": 100},
		{"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Picked Qty"), "fieldname": "picked_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Remaining Qty"), "fieldname": "remaining_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Opening Qty"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100}
	]

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and sle.posting_date <= %s" % frappe.db.escape(filters.get("to_date"))
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get('company'):
		conditions += " and sle.company = %s" % frappe.db.escape(filters.get("company"))

	return conditions

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = ' and sle.item_code in ({})'\
			.format(', '.join([frappe.db.escape(i, percent=False) for i in items]))

	conditions = get_conditions(filters)

	return frappe.db.sql("""
		select
			sle.item_code, sle.posting_date, sum(sle.actual_qty) as actual_qty,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference,
			sle.item_code as name, sle.voucher_no
		from
			`tabStock Ledger Entry` sle force index (posting_sort_index)
		where sle.docstatus < 2 %s %s
		group by sle.item_code
		""" % #nosec
		(item_conditions_sql, conditions), as_dict=1)

def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	for d in sle:
		key = (d.company, d.item_code)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"opening_qty": 0.0, "opening_val": 0.0,
				"in_qty": 0.0, "in_val": 0.0,
				"out_qty": 0.0, "out_val": 0.0,
				"bal_qty": 0.0, "bal_val": 0.0,
				"val_rate": 0.0
			})

		qty_dict = iwb_map[(d.company, d.item_code)]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date:
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if qty_diff > 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	iwb_map = filter_items_with_no_transactions(iwb_map)

	return iwb_map

def filter_items_with_no_transactions(iwb_map):
	for (company, item) in sorted(iwb_map):
		qty_dict = iwb_map[(company, item)]

		no_transactions = True
		float_precision = cint(frappe.db.get_default("float_precision")) or 3
		for key, val in iteritems(qty_dict):
			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			iwb_map.pop((company, item))

	return iwb_map

def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sle, filters):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sle]))

	if not items:
		return item_details

	cf_field = cf_join = ""
	if filters.get("include_uom"):
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(filters.get("include_uom"))

	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom %s
		from
			`tabItem` item
			%s
		where
			item.name in (%s)
	""" % (cf_field, cf_join, ','.join(['%s'] *len(items))), items, as_dict=1)

	for item in res:
		item_details.setdefault(item.name, item)

	return item_details

def get_variants_attributes():
	'''Return all item variant attributes.'''
	return [i.name for i in frappe.get_all('Item Attribute')]

def get_variant_values_for(items):
	'''Returns variant values for items.'''
	attribute_map = {}
	for attr in frappe.db.sql('''select parent, attribute, attribute_value
		from `tabItem Variant Attribute` where parent in (%s)
		''' % ", ".join(["%s"] * len(items)), tuple(items), as_dict=1):
			attribute_map.setdefault(attr['parent'], {})
			attribute_map[attr['parent']].update({attr['attribute']: attr['attribute_value']})

	return attribute_map