import frappe
from frappe import _
from frappe.utils import today
from frappe.model.mapper import get_mapped_doc, map_child_doc
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order
from erpnext.stock.doctype.pick_list.pick_list import get_items_with_location_and_quantity

def on_submit(self, method):
	check_available_qty(self)
	update_delivery_note(self, "submit")

def check_available_qty(self):
	for item in self.locations:
		available_qty = get_avaliable_qty(self, item.item_code, item.warehouse, item.batch_no)
		
		if available_qty < 0:
			frappe.throw(f"Row {item.idx}: Lot {item.lot_no} for item {item.item_code} doesn't have sufficient unpicked qty")

def get_avaliable_qty(self, item_code, warehouse, batch_no):
	batch_locations = frappe.db.sql(f"""
		SELECT
			SUM(sle.`actual_qty`) AS `actual_qty`
		FROM
			`tabStock Ledger Entry` as  sle join `tabBatch` as batch on sle.batch_no = batch.name
		WHERE
			sle.batch_no = '{batch_no}'
			and sle.`item_code`='{item_code}'
			and sle.`company` = '{self.company}'
			and warehouse = '{warehouse}'
			and IFNULL(batch.`expiry_date`, '2200-01-01') > '{today()}'
	""")

	pick_list_available = frappe.db.sql(f"""
		SELECT SUM(pli.picked_qty - pli.delivered_qty) FROM `tabPick List Item` as pli
		JOIN `tabPick List` AS pl ON pl.name = pli.parent
		WHERE `item_code` = '{item_code}'
		AND warehouse = '{warehouse}'
		AND batch_no = '{batch_no}'
		AND pl.docstatus = 1
	""")
	
	return batch_locations[0][0] - pick_list_available[0][0]

def on_cancel(self, method):
	update_delivery_note(self, "cancel")

def update_delivery_note(self, method):
	if method == "submit":
		for item in self.locations:
			tile = frappe.get_doc("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order})
			picked_qty = tile.picked_qty + item.qty
			if picked_qty > tile.qty:
				frappe.throw("Can not pick item {} in row {} more than {}".format(item.item_code, item.idx, item.qty - item.picked_qty))

			tile.db_set('picked_qty', picked_qty)
	
	if method == "cancel":
		for item in self.locations:
			tile = frappe.get_doc("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order})
			picked_qty = tile.picked_qty - item.qty

			if tile.picked_qty < 0:
				frappe.throw("Row {}: All Item Already Canclled".format(item.idx))

			tile.db_set('picked_qty', picked_qty)

def set_delivery_note_missing_values(target):
	target.run_method('set_missing_values')
	target.run_method('set_po_nos')
	target.run_method('calculate_taxes_and_totals')

def get_cost_center(for_item, from_doctype, company):
	'''Returns Cost Center for Item or Item Group'''
	return frappe.db.get_value('Item Default',
		fieldname=['buying_cost_center'],
		filters={
			'parent': for_item,
			'parenttype': from_doctype,
			'company': company
		})

def update_delivery_note_item(source, target, delivery_note):
	cost_center = frappe.db.get_value('Project', delivery_note.project, 'cost_center')
	if not cost_center:
		cost_center = get_cost_center(source.item_code, 'Item', delivery_note.company)

	if not cost_center:
		cost_center = get_cost_center(source.item_group, 'Item Group', delivery_note.company)

	target.cost_center = cost_center

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	
	mapper = {
		'doctype': 'Delivery Note Item',
		'field_map': {
			'rate': 'rate',
			'name': 'so_detail',
			'parent': 'against_sales_order',
		},
	}
	def set_missing_values(source, target):
		pass
	
	def get_item_details(source_doc, target_doc, source_parent):
		pass
	
	doc = get_mapped_doc("Pick List",
		source_name,
		{
			"Pick List": {
				"doctype": "Delivery Note",
				"field_map": {

				},
				"field_no_map": [
					'customer',
					'transaction_date'
				]
			},
			"Pick List Item": {
				"doctype": "Delivery Note Item",
				"field_map": {
					"item_code": "item_code",
				},
				"postprocess": get_item_details,
			}
		},
		target_doc,
		set_missing_values
	)
	# frappe.throw(dir(doc))
	return doc

def make_delivery_note2(source_name, target_doc=None, skip_item_mapping=False):
	pick_list = frappe.get_doc('Pick List', source_name)
	sales_orders = [d.sales_order for d in pick_list.locations]
	sales_orders = set(sales_orders)
	
	delivery_note = None

	for sales_order in sales_orders:
		delivery_note = create_delivery_note_from_sales_order(sales_order,
			delivery_note, skip_item_mapping=True)

	item_table_mapper = {
		'doctype': 'Delivery Note Item',
		'field_map': {
			'rate': 'rate',
			'name': 'so_detail',
			'parent': 'against_sales_order',
		},
		'condition': lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
	}

	for location in pick_list.locations:
		sales_order_item = frappe.get_cached_doc('Sales Order Item', location.sales_order_item)
		dn_item = map_child_doc(sales_order_item, delivery_note, item_table_mapper)

		if dn_item:
			dn_item.warehouse = location.warehouse
			dn_item.qty = location.picked_qty
			dn_item.batch_no = location.batch_no
			dn_item.serial_no = location.serial_no

			update_delivery_note_item(sales_order_item, dn_item, delivery_note)

	set_delivery_note_missing_values(delivery_note)

	delivery_note.pick_list = pick_list.name
	delivery_note.item_code = 'Perla Brown-I-P-PRC-6060'
	return delivery_note

def get_available_item_locations(item_code, from_warehouses, required_qty):
	locations = []
	if frappe.get_cached_value('Item', item_code, 'has_serial_no'):
		locations = get_available_item_locations_for_serialized_item(item_code, from_warehouses, required_qty)
	elif frappe.get_cached_value('Item', item_code, 'has_batch_no'):
		locations = get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty)
	else:
		locations = get_available_item_locations_for_other_item(item_code, from_warehouses, required_qty)

	total_qty_available = sum(location.get('qty') for location in locations)

	remaining_qty = required_qty - total_qty_available

	if remaining_qty > 0:
		frappe.msgprint(_('{0} units of {1} is not available.')
			.format(remaining_qty, frappe.get_desk_link('Item', item_code)))

	return locations

def get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty):
	warehouse_condition = 'and warehouse in %(warehouses)s' if from_warehouses else ''
	batch_locations = frappe.db.sql("""
		SELECT
			sle.`warehouse`,
			sle.`batch_no`,
			SUM(sle.`actual_qty`) AS `qty`
		FROM
			`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.batch_no = batch.name
			and sle.`item_code`=%(item_code)s
			and IFNULL(batch.`expiry_date`, '2200-01-01') > %(today)s
			{warehouse_condition}
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `qty` > 0
		ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
	""".format(warehouse_condition=warehouse_condition), { #nosec
		'item_code': item_code,
		'today': today(),
		'warehouses': from_warehouses
	}, as_dict=1)

	return batch_locations

@frappe.whitelist()
def get_items(filters):
	from six import string_types
	import json

	if isinstance(filters, string_types):
		filters = json.loads(filters)
		
	warehouse_condition = ''
	batch_locations = frappe.db.sql("""
		SELECT
			sle.`item_code`,
			sle.`warehouse`,
			sle.`batch_no`,
			SUM(sle.`actual_qty`) AS `actual_qty`
		FROM
			`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.batch_no = batch.name
			and sle.`item_code`=%(item_code)s
			and sle.`company` = '{company}'
			and IFNULL(batch.`expiry_date`, '2200-01-01') > %(today)s
			{warehouse_condition}
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `actual_qty` > 0
		ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
	""".format(warehouse_condition=warehouse_condition, company=filters['company']), { #nosec
		'item_code': filters['item_code'],
		'today': today(),
	}, as_dict=1)

	item_name = frappe.db.get_value('Item', filters['item_code'], 'item_name')
	
	data = []
	for item in batch_locations:
		item['item_name'] = item_name
		
		pick_list_available = frappe.db.sql(f"""
			SELECT SUM(pli.picked_qty - pli.delivered_qty) FROM `tabPick List Item` as pli
			JOIN `tabPick List` AS pl ON pl.name = pli.parent
			WHERE `item_code` = '{filters['item_code']}'
			AND warehouse = '{item['warehouse']}'
			AND batch_no = '{item['batch_no']}'
			AND pl.docstatus = 1
		""")

		item['available_qty'] = item['actual_qty'] - (pick_list_available[0][0] or 0.0)
		if item['available_qty'] <= 0.0:
			item = None
		del item['actual_qty']
		item['picked_qty'] = item['available_qty']

		if item:
			data.append(item)
	
	return data