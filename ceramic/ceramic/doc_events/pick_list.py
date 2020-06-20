import frappe
from frappe import _
from frappe.utils import today
from frappe.model.mapper import get_mapped_doc, map_child_doc, map_doc, map_fields
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order
from erpnext.stock.doctype.pick_list.pick_list import get_items_with_location_and_quantity
from frappe.utils import flt

def before_vaidate(self, method):
	remove_items_without_batch_no(self)
	update_remaining_qty(self)

def validate(self, method):
	check_item_qty(self)
	remove_items_without_batch_no(self)
	update_remaining_qty(self)

def before_submit(self, method):
	update_available_qty(self)
	update_remaining_qty(self)
	self.picked_sales_orders = []
	self.available_qty = []

def on_submit(self, method):
	check_item_qty(self)
	update_item_so_qty(self)
	update_sales_order(self, "submit")
	update_status_sales_order(self)

def before_update_after_submit(self,method):
	validate_item_qty(self)

from ceramic.update_item import update_child_qty_rate
import json
def update_item_so_qty(self):
	for item in self.locations:
		doc = frappe.get_doc("Sales Order Item", item.sales_order_item)
		parent_doc = frappe.get_doc("Sales Order", item.sales_order)
		data = []

		for row in parent_doc.items:
			if row.name != item.sales_order_item:
				data.append({
					'docname': row.name,
					'name': row.name,
					'item_code': row.item_code,
					'qty': row.qty,
					'rate': row.rate,
					'discounted_rate': row.discounted_rate,
					'real_qty': row.real_qty
				})
			else:
				data.append({
					'docname': row.name,
					'name': row.name,
					'item_code': row.item_code,
					'qty': item.so_qty,
					'rate': row.rate,
					'discounted_rate': row.discounted_rate,
					'real_qty': item.so_real_qty
				})

		update_child_qty_rate("Sales Order", json.dumps(data), doc.parent)

def on_cancel(self, method):
	update_sales_order(self, "cancel")
	update_status_sales_order(self)
	
def check_item_qty(self):
	for item in self.available_qty:
		if item.remaining < 0:
			frappe.throw(f"Row {item.idx}: Remaining Qty Less than 0")

def validate_item_qty(self):
	for row in self.locations:
		if row.qty < flt(row.delivered_qty + row.wastage_qty):
			frappe.throw(f"Row {row.idx}: Qty can not be Less than delivered qty {flt(row.delivered_qty + row.wastage_qty)}")
		if row.qty > row.so_qty:
			frappe.throw(f"Row {row.idx}: Qty can not be greater than sales order qty {row.so_qty}")

def remove_items_without_batch_no(self):
	if self.locations:
		locations = [item for item in self.locations if item.batch_no]
		self.locations = locations

def update_delivered_percent(self):
	qty = 0
	delivered_qty = 0
	if self.locations:
		for index, item in enumerate(self.locations):
			qty += item.qty
			delivered_qty += item.delivered_qty

			item.db_set('idx', index + 1)

		try:
			self.db_set('per_delivered', (delivered_qty / qty) * 100)
		except:
			self.db_set('per_delivered', 0)

def update_available_qty(self):
	self.available_qty = []
	data = get_item_qty(self.company, self.item, self.customer, self.sales_order)
	for item in data:
		self.append('available_qty',{
			'item_code': item.item_code,
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

def update_remaining_qty(self):
	sales_order_item_list = list(set([row.sales_order_item for row in self.locations]))

	for sales_order_item in sales_order_item_list:
		qty = 0
		for item in self.locations:
			if sales_order_item == item.sales_order_item:
				qty += flt(item.qty)
				item.remaining_qty = flt(item.so_qty) - flt(item.picked_qty) - flt(qty)

				if item.remaining_qty < 0:
					frappe.throw(_(f"ROW: {item.idx} : Remaining Qty Cannot be less than 0."))

def update_sales_order(self, method):
	if method == "submit":
		for item in self.locations:
			if frappe.db.exists("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order}):
				tile = frappe.get_doc("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order})
				picked_qty = tile.picked_qty + item.qty
				if picked_qty > tile.qty:
					frappe.throw("Can not pick item {} in row {} more than {}".format(item.item_code, item.idx, item.qty - item.picked_qty))

				tile.db_set('picked_qty', picked_qty)
			if item.sales_order:
				so = frappe.get_doc("Sales Order",item.sales_order)
				total_picked_qty = 0.0
				total_picked_weight = 0.0
				for row in so.items:
					row.db_set('picked_weight',flt(row.weight_per_unit * row.picked_qty))
					total_picked_qty += row.picked_qty
					total_picked_weight += row.picked_weight
				
				so.db_set('total_picked_qty', total_picked_qty)
				so.db_set('total_picked_weight', total_picked_weight)
	
	if method == "cancel":
		for item in self.locations:
			if frappe.db.exists("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order}):
				tile = frappe.get_doc("Sales Order Item", {'name': item.sales_order_item, 'parent': item.sales_order})
				picked_qty = tile.picked_qty - item.qty

				if tile.picked_qty < 0:
					frappe.throw("Row {}: All Item Already Canclled".format(item.idx))

				tile.db_set('picked_qty', picked_qty)

			if item.sales_order:
				so = frappe.get_doc("Sales Order",item.sales_order)
				total_picked_qty = 0.0
				total_picked_weight = 0.0
				for row in so.items:
					row.db_set('picked_weight',flt(row.weight_per_unit * row.picked_qty))
					total_picked_qty = row.picked_qty
					total_picked_weight += row.picked_weight
				
				so.db_set('total_picked_qty', total_picked_qty)
				so.db_set('total_picked_weight', total_picked_weight)
	
def update_status_sales_order(self):
	sales_order_list = list(set([item.sales_order for item in self.locations if item.sales_order]))

	for sales_order in sales_order_list:
		so = frappe.get_doc("Sales Order", sales_order)
		qty = 0
		picked_qty = 0

		for item in so.items:
			qty += item.qty
			picked_qty += item.picked_qty

		so.db_set('per_picked', (picked_qty / qty) * 100)

@frappe.whitelist()
def get_item_qty(company, item_code = None, customer = None, sales_order = None):
	if not item_code and not customer and not sales_order:
		return
	
	batch_locations = []

	where_cond = ''
	if sales_order:
		where_cond = f" and soi.parent = '{sales_order}'"
	
	if customer:
		item_code_list = frappe.db.sql(f"""
			SELECT 
				DISTINCT soi.item_code
			FROM 
				`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.name = soi.parent
			WHERE
				so.docstatus = 1 AND
				so.customer = '{customer}' AND
				soi.qty != soi.picked_qty {where_cond} AND
				so.status != 'Closed'
		""")
		item_codes = [item[0] for item in item_code_list]
	
	if item_code and customer:
		if item_code not in item_codes:
			frappe.throw(_(f"Item {item_code} is not in sales order for Customer {customer}"))
	if sales_order:
		item_code_list = frappe.db.sql(f"""
			SELECT 
				DISTINCT soi.item_code
			FROM 
				`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.name = soi.parent
			WHERE
				so.docstatus = 1 AND
				soi.qty != soi.picked_qty {where_cond} AND
				so.status != 'Closed'
		""")
		# where_clause += f" AND so.name = '{sales_order}'"
		item_codes = [item[0] for item in item_code_list]
	
	if item_code:
		item_codes = [item_code]

	for item in item_codes:
		batch_locations += frappe.db.sql("""
			SELECT
				sle.`item_code`,
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
				`batch_no`,
				`item_code`
			HAVING `actual_qty` > 0
			ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
		""".format(company=company), { #nosec
			'item_code': item,
			'today': today(),
		}, as_dict=1)
	
	for item in batch_locations:
		item['item_name'] = frappe.db.get_value('Item', item['item_code'], 'item_name')
		
		pick_list_available = frappe.db.sql(f"""
			SELECT SUM(pli.qty - (pli.delivered_qty + pli.wastage_qty)) FROM `tabPick List Item` as pli
			JOIN `tabPick List` AS pl ON pl.name = pli.parent
			WHERE pli.`item_code` = '{item['item_code']}'
			AND pli.`batch_no` = '{item['batch_no']}'
			AND pl.`docstatus` = 1
		""")

		item['picked_qty'] = (pick_list_available[0][0] or 0.0)
		item['to_pick_qty'] = item['available_qty'] = item['actual_qty'] - item['picked_qty']
		item['total_qty'] = item['actual_qty'] 

	return batch_locations

@frappe.whitelist()
def get_item_from_sales_order(company, item_code = None, customer = None, sales_order = None):
	if not item_code and not customer and not sales_order:
		return
	where_clause = ''
	where_cond = ''
	if sales_order:
		where_cond = f" and soi.parent = '{sales_order}'"
	sales_order_list = []

	if customer:
		item_code_list = frappe.db.sql(f"""
			SELECT 
				DISTINCT soi.item_code
			FROM 
				`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.name = soi.parent
			WHERE
				so.docstatus = 1 AND
				so.customer = '{customer}' AND
				soi.qty != soi.picked_qty {where_cond} AND
				so.status != 'Closed'
		""")
		where_clause += f" AND so.customer = '{customer}'"
		item_codes = [item[0] for item in item_code_list]
	
	if item_code and customer:
		if item_code not in item_codes:
			frappe.throw(_(f"Item {item_code} is not in sales order for Customer {customer}"))
	
	if sales_order:
		item_code_list = frappe.db.sql(f"""
			SELECT 
				DISTINCT soi.item_code
			FROM 
				`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.name = soi.parent
			WHERE
				so.docstatus = 1 AND
				soi.qty != soi.picked_qty {where_cond} AND
				so.status != 'Closed'
		""")
		where_clause += f" AND so.name = '{sales_order}'"
		item_codes = [item[0] for item in item_code_list]
	# frappe.throw(str(item_codes))
	
	if item_code and sales_order:
		if item_code not in item_codes:
			frappe.throw(_(f"Item {item_code} is not in sales order {sales_order}"))
	
	if item_code:
		item_codes = [item_code]
	
	for item in item_codes:
		sales_order_list += frappe.db.sql(f"""
			SELECT 
				so.name as sales_order, so.customer, so.transaction_date, so.delivery_date, soi.packing_type as packing_type, so.per_picked,
				soi.name as sales_order_item, soi.item_code, soi.picked_qty, soi.qty, soi.real_qty, soi.uom, soi.stock_qty, soi.stock_uom, soi.conversion_factor
			FROM
				`tabSales Order Item` as soi JOIN 
				`tabSales Order`as so ON soi.parent = so.name 
			WHERE
				soi.item_code = '{item}' AND
				so.company = '{company}' AND
				so.`docstatus` = 1 {where_clause} AND
				soi.qty > soi.picked_qty AND
				so.status != 'Closed'
			ORDER BY
				soi.order_item_priority DESC
		""", as_dict = 1)

	return sales_order_list

@frappe.whitelist()
def get_picked_items(company, item_code = None, customer = None, sales_order = None):
	if not item_code and not customer and not sales_order:
		return
	
	where_clause = ''
	pick_list_list = []
	where_cond = ''
	if sales_order:
		where_cond = f" and so.name = '{sales_order}'"


	if customer:
		item_code_list = frappe.db.sql(f"""
			SELECT 
				DISTINCT soi.item_code, so.per_picked
			FROM 
				`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.name = soi.parent
			WHERE
				so.docstatus = 1 AND
				so.customer = '{customer}' AND
				soi.qty != soi.picked_qty {where_cond} AND
				so.status != 'Closed'
			ORDER BY
				soi.order_item_priority DESC
		""")
		item_codes = [item[0] for item in item_code_list]
	

	if sales_order and not customer:
		item_code_list = frappe.db.sql(f"""
			SELECT 
				DISTINCT soi.item_code, so.per_picked
			FROM 
				`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.name = soi.parent
			WHERE
				so.docstatus = 1 AND
				soi.qty != soi.picked_qty {where_cond} AND
				so.status != 'Closed'
			ORDER BY
				soi.order_item_priority DESC
		""")
		# where_clause += f" AND so.name = '{sales_order}'"
		item_codes = [item[0] for item in item_code_list]

	if item_code and customer:
		if item_code not in item_codes:
			frappe.throw(_(f"Item {item_code} is not in sales order for Customer {customer}"))
	
	
	if item_code:
		item_codes = [item_code]
		
	for item in item_codes:
		pick_list_list += frappe.db.sql(f"""
			SELECT 
				pli.sales_order, pli.sales_order_item, pli.customer,
				pli.date, pli.item_code, pli.qty, pli.picked_qty,
				pli.delivered_qty, pli.batch_no,
				pli.lot_no, pli.uom, pli.stock_qty, pli.stock_uom,
				pli.conversion_factor, pli.name, pli.parent, so.per_picked
			FROM
				`tabPick List Item` as pli JOIN 
				`tabPick List`as pl ON pli.parent = pl.name JOIN
				`tabSales Order` as so ON pli.sales_order = so.name
			WHERE
				pli.delivered_qty = 0 AND
				pli.item_code = '{item}' AND
				pl.company = '{company}' AND
				pl.`docstatus` = 1
		""", as_dict = 1)
	
	return pick_list_list
from ceramic.ceramic.doc_events.sales_order import update_picked_percent

@frappe.whitelist()
def unpick_item(sales_order, sales_order_item = None, pick_list = None, pick_list_item = None, unpick_qty = None):
	if pick_list_item and pick_list:
		unpick_qty = flt(unpick_qty)
		doc = frappe.get_doc("Pick List Item", pick_list_item)
		if not unpick_qty:
			diff_qty = doc.qty - doc.delivered_qty - flt(doc.wastage_qty)
			doc.db_set('qty', doc.qty - diff_qty)

			if diff_qty == 0:
				frappe.throw(_("You can not cancel this Sales Order, Delivery Note already there for this Sales Order."))

			picked_qty = frappe.db.get_value("Sales Order Item", doc.sales_order_item, 'picked_qty')
			frappe.db.set_value("Sales Order Item", doc.sales_order_item, 'picked_qty', (flt(picked_qty)- flt(diff_qty)))
		
			if not doc.delivered_qty and not doc.wastage_qty:
				doc.cancel()
				doc.delete()
		else:
			if unpick_qty > doc.qty - doc.wastage_qty - doc.delivered_qty:
				frappe.throw(f"You can not unpick qty {unpick_qty} higher than remaining pick qty { doc.qty - doc.wastage_qty - doc.delivered_qty }")
			else:
				doc.db_set('qty', doc.qty - unpick_qty)

				soi_doc = frappe.get_doc("Sales Order Item", sales_order_item)
				soi_doc.db_set('picked_qty', soi_doc.picked_qty - unpick_qty)

		update_delivered_percent(frappe.get_doc("Pick List", doc.parent))
		update_picked_percent(frappe.get_doc("Sales Order", doc.sales_order))
		return "Pick List to this Sales Order Have Been Deleted."
	elif sales_order and sales_order_item:
		data = frappe.get_all("Pick List Item", {'sales_order': sales_order, 'sales_order_item': sales_order_item}, ['name'])
		
		for pl in data:
			
			doc = frappe.get_doc("Pick List Item", pl.name)
			diff_qty = flt(doc.qty) - flt(doc.delivered_qty) - flt(doc.wastage_qty)
			doc.db_set('qty', doc.qty - diff_qty)

			picked_qty = frappe.db.get_value("Sales Order Item", doc.sales_order_item, 'picked_qty')
			frappe.db.set_value("Sales Order Item", doc.sales_order_item, 'picked_qty', flt(picked_qty) - flt(diff_qty))
			
			if not unpick_qty:
				if not doc.delivered_qty and not doc.wastage_qty:
					if doc.docstatus == 1:
						doc.cancel()
					doc.delete()
			
			update_delivered_percent(frappe.get_doc("Pick List", doc.parent))
			update_picked_percent(frappe.get_doc("Sales Order", doc.sales_order))
		
		return "Pick List to this Sales Order Have Been Deleted."
	else:
		data = frappe.get_all("Pick List Item", {'sales_order': sales_order}, ['name'])
		
		for pl in data:
			doc = frappe.get_doc("Pick List Item", pl.name)
			diff_qty = doc.qty - doc.delivered_qty - flt(doc.wastage_qty)
			doc.db_set('qty', doc.qty - diff_qty)

			picked_qty = frappe.db.get_value("Sales Order Item", doc.sales_order_item, 'picked_qty')
			frappe.db.set_value("Sales Order Item", doc.sales_order_item, 'picked_qty', flt(picked_qty) - flt(diff_qty))

			if not unpick_qty:
				if not doc.delivered_qty and not doc.wastage_qty:
					if doc.docstatus == 1:
						doc.cancel()
					
					doc.delete()
			
			update_delivered_percent(frappe.get_doc("Pick List", doc.parent))
		
		update_picked_percent(frappe.get_doc("Sales Order", sales_order))
		return "Pick List to this Sales Order Have Been Deleted."


@frappe.whitelist()
def get_items(filters):
	from six import string_types
	import json

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	batch_locations = frappe.db.sql("""
		SELECT
			sle.`item_code`,
			sle.`batch_no`,
			batch.lot_no,
			batch.packing_type,
			SUM(sle.`actual_qty`) AS `actual_qty`
		FROM
			`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.batch_no = batch.name
			and sle.`item_code`=%(item_code)s
			and sle.`company` = '{company}'
			and IFNULL(batch.`expiry_date`, '2200-01-01') > %(today)s
		GROUP BY
			`batch_no`,
			`item_code`
		HAVING `actual_qty` > 0
		ORDER BY IFNULL(batch.`expiry_date`, '2200-01-01'), batch.`creation`
	""".format(company=filters['company']), { #nosec
		'item_code': filters['item_code'],
		'today': today(),
	}, as_dict=1)

	item_name = frappe.db.get_value('Item', filters['item_code'], 'item_name')
	
	data = []
	for item in batch_locations:
		item['item_name'] = item_name
		
		pick_list_available = frappe.db.sql(f"""
			SELECT SUM(pli.qty - (pli.delivered_qty + pli.wastage_qty)) FROM `tabPick List Item` as pli
			JOIN `tabPick List` AS pl ON pl.name = pli.parent
			WHERE `item_code` = '{filters['item_code']}'
			AND batch_no = '{item['batch_no']}'
			AND pl.docstatus = 1
		""")
		
		item['picked_qty'] = flt(pick_list_available[0][0] or 0.0)
		item['available_qty'] = flt(item['actual_qty'] - (pick_list_available[0][0] or 0.0))
		item['to_pick_qty'] = str(min(item['available_qty'], filters['to_pick_qty']))
		if item['available_qty'] <= 0.0:
			item = None

		if item:
			data.append(item)
	# frappe.msgprint(str(data))
	return data