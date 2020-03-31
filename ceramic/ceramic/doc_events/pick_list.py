import frappe
from frappe import _
from frappe.utils import today
from frappe.model.mapper import get_mapped_doc, map_child_doc, map_doc, map_fields
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order
from erpnext.stock.doctype.pick_list.pick_list import get_items_with_location_and_quantity

def validate(self, method):
	check_item_qty(self)

def before_submit(self, method):
	update_available_qty(self)

def on_submit(self, method):
	check_item_qty(self)
	update_sales_order(self, "submit")

def on_cancel(self, method):
	update_sales_order(self, "cancel")

def check_item_qty(self):
	for item in self.available_qty:
		if item.remaining < 0:
			frappe.throw(f"Row {item.idx}: Remaining Qty Less than 0")

def update_available_qty(self):
	self.available_qty = []
	data = get_item_qty(self.company, self.item, self.customer)
	for item in data:
		self.append('available_qty',{
			'item_code': item.item_code,
			'warehouse': item.warehouse,
			'batch_no': item.batch_no,
			'lot_no': item.lot_no,
			'total_qty': item.total_qty,
			'picked_qty': item.picked_qty,
			'available_qty': item.available_qty,
			'remaining_qty': item.qty,
			'picked_in_current': 0,
		})
	
	for i in self.available_qty:
		qty = 0
		for j in self.locations:
			if i.item_code == j.item_code and i.batch_no == j.batch_no:
				qty += j.qty
		i.picked_in_current = qty
		i.remaining = i.total_qty - qty

def update_sales_order(self, method):
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

@frappe.whitelist()
def get_item_qty(company, item_code = None, customer = None):
	if not item_code and not customer:
		return

	batch_locations = frappe.db.sql("""
		SELECT
			sle.`item_code`,
			sle.`warehouse`,
			sle.`batch_no`,
			batch.`lot_no`,
			SUM(sle.`actual_qty`) AS `actual_qty`
		FROM
			`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.batch_no = batch.name
			and sle.`item_code`=%(item_code)s
			and sle.`company` = '{company}'
			and IFNULL(batch.`expiry_date`, '2200-01-01') > %(today)s
		GROUP BY
			`warehouse`,
			`batch_no`,
			`item_code`
		HAVING `actual_qty` > 0
		ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
	""".format(company=company), { #nosec
		'item_code': item_code,
		'today': today(),
	}, as_dict=1)

	item_name = frappe.db.get_value('Item', item_code, 'item_name')
	
	for item in batch_locations:
		item['item_name'] = item_name
		
		pick_list_available = frappe.db.sql(f"""
			SELECT SUM(pli.qty - pli.delivered_qty) FROM `tabPick List Item` as pli
			JOIN `tabPick List` AS pl ON pl.name = pli.parent
			WHERE pli.`item_code` = 'Bricola Brown-I-R-PRC-6060'
			AND pli.`warehouse` = '{item['warehouse']}'
			AND pli.`batch_no` = '{item['batch_no']}'
			AND pl.`docstatus` = 1
		""")

		item['picked_qty'] = (pick_list_available[0][0] or 0.0)
		item['to_pick_qty'] = item['available_qty'] = item['actual_qty'] - item['picked_qty']
		item['total_qty'] = item['actual_qty'] 

	return batch_locations

@frappe.whitelist()
def get_item_from_sales_order(company, item_code = None, customer = None):
	if not item_code and not customer:
		return
	
	sales_order_list = frappe.db.sql(f"""
		SELECT 
			so.name as sales_order, so.customer, so.transaction_date, so.delivery_date,
			soi.name as sales_order_item, soi.item_code, soi.picked_qty, soi.qty, soi.uom, soi.stock_qty, soi.stock_uom, soi.conversion_factor
		FROM
			`tabSales Order Item` as soi JOIN 
			`tabSales Order`as so ON soi.parent = so.name 
		WHERE
			soi.item_code = '{item_code}' AND
			so.company = '{company}' AND
			so.`docstatus` = 1
	""", as_dict = 1)

	return sales_order_list
