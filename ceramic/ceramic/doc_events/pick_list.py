import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc, map_child_doc
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order


def on_submit(self, method):
	"""On Submit Custom Function for Payment Entry"""
	update_delivery_note(self, "submit")

def on_cancel(self, method):
	update_delivery_note(self, "cancel")

def update_delivery_note(self, method):
	if method == "submit":
		for item in self.locations:
			tile = frappe.get_doc("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order})
			picked_qty = tile.picked_qty + item.qty
			tile.db_set('picked_qty', picked_qty)
	
	if method == "cancel":
		for item in self.locations:
			tile = frappe.get_doc("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order})
			picked_qty = tile.picked_qty - item.qty
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