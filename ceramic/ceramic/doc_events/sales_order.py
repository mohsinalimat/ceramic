from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc

def validate(self, method):
	self.flags.ignore_permissions = True

	for item in self.items:
		if not item.rate:
			rate = get_rate_discounted_rate(item.item_code, self.customer, self.company)['rate']
			item.rate = rate

	if((str(self._action)) == "submit"):
		for row in self.items:
			if (row.rate == 0):
				frappe.throw(_("Rate can not be 0 in row {}".format(row.idx)))

def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = item.discounted_rate * flt(item.real_qty)
		item.discounted_net_amount = item.discounted_amount

def on_submit(self):
	"""On Submit Custom Function"""
	create_sales_order(self)

def create_sales_order(self):
	def get_sales_order_doc(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target.company = "Millennium Vitrified Tiles Pvt. Ltd."
		
		doclist = get_mapped_doc("Sales Order", source_name, {
			"Sales Order Item": {
				"doctype": "Sales Order",
				"field_map": {
					"rate": "dicounted_rate",
					"qty": "billing_qty",
				},
			}
		}, target_doc, set_missing_values, ignore_permissions=ignore_permissions)
	
		return doclist
	
	so = get_sales_order_doc(self.name)

	try:
		so.save(ignore_permissions = True)
		so.submit()
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)
	
@frappe.whitelist()
def get_rate_discounted_rate(item_code, customer, company):

	item_group, tile_quality = frappe.get_value("Item", item_code, ['item_group', 'tile_quality'])
	parent_item_group = frappe.get_value("Item Group", item_group, 'parent_item_group')
	
	data = frappe.db.sql(f"""
		SELECT 
			soi.`rate`, soi.`discounted_rate` 
		FROM 
			`tabSales Order Item` as soi JOIN
			`tabSales Order` as so ON soi.parent = so.name
		WHERE
			soi.`item_group` = '{item_group}' AND
			soi.`tile_quality` = '{tile_quality}' AND
			so.`customer` = '{customer}' AND
			so.`company` = '{company}' AND
			so.`docstatus` != 0
		ORDER BY
			so.`transaction_date` DESC
		LIMIT 
			1
	""", as_dict = True)

	if not data:
		data = frappe.db.sql(f"""
		SELECT 
			soi.`rate`, soi.`discounted_rate` 
		FROM 
			`tabSales Order Item` as soi JOIN
			`tabSales Order` as so ON soi.parent = so.name
		WHERE
			soi.`parent_item_group` = '{parent_item_group}' AND
			soi.`tile_quality` = '{tile_quality}' AND
			so.`customer` = '{customer}' AND
			so.`company` = '{company}' AND
			so.`docstatus` = 1
		ORDER BY
			so.`transaction_date` DESC
		LIMIT 
			1
	""", as_dict = True)
	
	return data[0] if data else {'rate': 0, 'discounted_rate': 0}


@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
	def update_item_quantity(source, target, source_parent):
		target.qty = flt(source.qty) - flt(source.picked_qty)
		target.stock_qty = (flt(source.qty) - flt(source.picked_qty)) * flt(source.conversion_factor)
		target.picked_qty = 0
		target.actual_qty = 0
		target.available_qty = 0
		
	doc = get_mapped_doc('Sales Order', source_name, {
		'Sales Order': {
			'doctype': 'Pick List',
			'validation': {
				'docstatus': ['=', 1]
			}
		},
		'Sales Order Item': {
			'doctype': 'Pick List Item',
			'field_map': {
				'parent': 'sales_order',
				'name': 'sales_order_item'
			},
			'field_no_map': [
				'warehouse'
			],
			'postprocess': update_item_quantity,
			'condition': lambda doc: abs(doc.picked_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		},
	}, target_doc)

	doc.purpose = 'Delivery against Sales Order'

	doc.set_item_locations()

	return doc