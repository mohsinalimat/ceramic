from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address

import math
import datetime

def before_validate(self, method):
	self.flags.ignore_permissions = True
	check_company(self)
	setting_rate_qty(self)
	calculate_order_priority(self)
	update_discounted_amount(self)

def on_submit(self, method):
	checking_rate(self)
	checking_real_qty(self)
	update_picked_percent(self)

def before_update_after_submit(self, method):
	setting_rate_qty(self)
	calculate_order_priority(self)
	update_discounted_amount(self)
	update_idx(self)

def on_update_after_submit(self, method):
	update_picked_percent(self)

def on_cancel(self, method):
	remove_pick_list(self)
	update_picked_percent(self)

def check_company(self):
	if self.authority == "Authorized":
		frappe.throw(_(f"You cannot make Sales Order in company {frappe.bold(self.company)}."))

def setting_rate_qty(self):
	for item in self.items:
		if not item.rate:
			item.rate = get_rate_discounted_rate(item.item_code, self.customer, self.company)['rate']

		if item.discounted_rate > item.rate:
			item.discounted_rate = item.rate

		if item.real_qty > item.qty:
			item.real_qty = item.qty

def calculate_order_priority(self):
	for item in self.items:
		try:
			days = ((datetime.date.today() - datetime.datetime.strptime(self.transaction_date, '%Y-%m-%d').date()) // datetime.timedelta(days = 1)) + 15
		except:
			days = ((datetime.date.today() - self.transaction_date) // datetime.timedelta(days = 1)) + 15
		days = 1 if days <= 0 else days
		item.order_item_priority = round(math.log(days, 1.1) * cint(self.order_priority))

def update_discounted_amount(self):
	for item in self.items:
		item.discounted_rate = item.discounted_rate if item.discounted_rate else 0
		item.real_qty = item.real_qty if item.real_qty else 0

		item.discounted_amount = item.discounted_rate * flt(item.real_qty)
		item.discounted_net_amount = item.discounted_amount

def checking_rate(self):
	flag = False
	for row in self.items:
		if not row.rate:
			flag = True
			frappe.msgprint(_(f"Row {row.idx}: Rate cannot be 0."))

		if not row.discounted_rate and row.real_qty:
			flag = True
			frappe.msgprint(_(f"Row {row.idx}: Discounted Rate cannot be 0."))

	if flag:
		frappe.throw(_("Did not Approved Sales Order"))

def checking_real_qty(self):
	alternate_company = frappe.db.get_value("Company", self.company, 'alternate_company')
	for item in self.items:
		if not item.real_qty:
			frappe.msgprint(_(f"Row {row.idx}:You will not able to make invoice in company {alternate_company}."))

def remove_pick_list(self):
	from ceramic.ceramic.doc_events.pick_list import update_delivered_percent
	parent_doc = []

	for item in self.items:
		if item.picked_qty:
			for picked_item in frappe.get_all("Pick List Item", {'sales_order': self.name, 'sales_order_item': item.name}):
				doc = frappe.get_doc("Pick List Item", picked_item.name)

				if doc.delivered_qty:
					frappe.throw(_("You can not cancel this Sales Order, Delivery Note already there for this Sales Order."))

				doc.cancel()
				doc.delete()

				parent_doc.append(doc.parent)
				item.db_set('picked_qty', 0)

	for item in set(parent_doc):
		update_delivered_percent(frappe.get_doc("Pick List", item))

def update_picked_percent(self):
	if self.items:
		picked_qty = 0
		qty = 0
		for item in self.items:
			picked_qty += item.picked_qty
			qty += item.qty

	self.db_set('per_picked', (picked_qty / qty) * 100)

def update_idx(self):
	for idx, item in enumerate(self.items):
		item.idx = idx + 1

@frappe.whitelist()
def get_rate_discounted_rate(item_code, customer, company):

	item_group, tile_quality = frappe.get_value("Item", item_code, ['item_group', 'tile_quality'])
	parent_item_group = frappe.get_value("Item Group", item_group, 'parent_item_group')

	count = frappe.db.sql(f"""
		SELECT COUNT(*) FROM `tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.`name` = soi.`parent`
		WHERE soi.`item_group` = '{item_group}' AND soi.`docstatus` = 1 AND so.customer = '{customer}' AND soi.`tile_quality` = '{tile_quality}' AND so.`company` = '{company}'
		LIMIT 1
	""")

	if count[0][0]:
		where_clause = f"soi.item_group = '{item_group}' AND "
	else:
		where_clause = f"soi.parent_item_group = '{parent_item_group}' AND"

	data = frappe.db.sql(f"""
		SELECT 
			soi.`rate` as `rate`, soi.`discounted_rate` as `discounted_rate`
		FROM 
			`tabSales Order Item` as soi JOIN
			`tabSales Order` as so ON soi.parent = so.name
		WHERE
			{where_clause}
			soi.`tile_quality` = '{tile_quality}' AND
			so.`customer` = '{customer}' AND
			so.`company` = '{company}' AND
			so.`docstatus` != 0
		ORDER BY
			so.`transaction_date` DESC
		LIMIT 
			1
	""", as_dict = True)

	return data[0] if data else {'rate': 0, 'discounted_rate': 0}

@frappe.whitelist()
def make_pick_list(source_name, target_doc=None):
	def update_item_quantity(source, target, source_parent):
		target.qty = flt(source.qty) - flt(source.picked_qty)
		target.so_qty = flt(source.qty)
		target.stock_qty = (flt(source.qty) - flt(source.picked_qty)) * flt(source.conversion_factor)
		target.picked_qty = source.picked_qty
		target.remaining_qty = target.so_qty - target.qty - target.picked_qty
		target.customer = source_parent.customer
		target.date = source_parent.transaction_date
		target.delivery_date = source.delivery_date

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

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", 'company_address', target.company_address))

	def update_item(source, target, source_parent):
		for i in source.items:
			real_delivered_qty = i.real_qty - i.delivered_real_qty
			for j in frappe.get_all("Pick List Item", filters={"sales_order": source.name, "sales_order_item": i.name, "docstatus": 1}):
				pick_doc = frappe.get_doc("Pick List Item", j.name)
				
				if real_delivered_qty <= 0:
					real_delivered_qty = 0
				
				if pick_doc.qty - pick_doc.delivered_qty:
					target.append('items',{
						'item_code': pick_doc.item_code,
						'qty': pick_doc.qty - pick_doc.delivered_qty,
						'real_qty': min(real_delivered_qty, pick_doc.qty - pick_doc.delivered_qty),
						'rate': i.rate,
						'discounted_rate': i.discounted_rate,
						'against_sales_order': source.name,
						'so_detail': i.name,
						'against_pick_list': pick_doc.parent,
						'pl_detail': pick_doc.name,
						'warehouse': pick_doc.warehouse,
						'batch_no': pick_doc.batch_no,
						'lot_no': pick_doc.lot_no,
						'item_series': i.item_series
					})

					real_delivered_qty = real_delivered_qty - min(real_delivered_qty, pick_doc.qty - pick_doc.delivered_qty)

	mapper = {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			},
			"postprocess": update_item
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}

	target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)
	return target_doc

@frappe.whitelist()
def calculate_order_item_priority():
	data = frappe.db.sql(f"""
		SELECT
			soi.`name`, so.`transaction_date`, so.`order_priority`
		FROM
			`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.`name` = soi.`parent`
		WHERE
			soi.`qty` > soi.`delivered_qty` AND
			so.`docstatus` = 1
	""", as_dict = 1)

	for soi in data:
		days = ((datetime.date.today() - soi.transaction_date) // datetime.timedelta(1)) + 15
		order_item_priority = round(math.log(days, 1.1) * cint(soi.order_priority))

		frappe.db.set_value("Sales Order Item", soi.name, 'order_item_priority', order_item_priority)

	frappe.db.commit()
