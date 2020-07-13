import json

import frappe
from frappe import _
from frappe.utils import flt, today
from frappe.model.mapper import get_mapped_doc, map_child_doc, map_doc, map_fields

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as create_delivery_note_from_sales_order
from erpnext.stock.doctype.pick_list.pick_list import get_items_with_location_and_quantity

from ceramic.ceramic.doc_events.sales_order import update_sales_order_total_values
from ceramic.update_item import update_child_qty_rate

def validate(self, method):
	remove_items_without_batch_no(self)
	check_available_item_remaining_qty(self)
	update_remaining_qty(self)
	check_qty(self)

def before_submit(self, method):
	update_available_qty(self)
	update_remaining_qty(self)
	check_available_item_remaining_qty(self)
	removing_remaining_value(self)

def removing_remaining_value(self):
	self.picked_sales_orders = []
	self.available_qty = []
	self.sales_order_item = []

def on_submit(self, method):
	update_item_so_qty(self)
	update_sales_order(self, "submit")

def before_update_after_submit(self,method):
	validate_item_qty(self)

def remove_items_without_batch_no(self):
	""" This function is used to Removed all item from table location which dosen't have batch number  """

	if self.locations:
		locations = [item for item in self.locations if item.batch_no]
		self.locations = locations

def update_remaining_qty(self):
	""" This function is use to update remaining qty in all all sales order """
	
	# getting unique list from sales_order_item from table locations
	sales_order_item_list = set([row.sales_order_item for row in self.locations])

	# updating remaining qty and validating if remaining qty is less than 0
	for sales_order_item in sales_order_item_list:
		qty = 0
		for item in self.locations:
			if sales_order_item == item.sales_order_item:
				qty += flt(item.qty)
				item.remaining_qty = flt(item.so_qty) - flt(item.picked_qty) - flt(qty)

				if item.remaining_qty < 0:
					frappe.throw(_(f"ROW: {item.idx} : Remaining Qty Cannot be negative."))

def check_qty(self):
	for item in self.locations:
		if item.qty < 0:
			frappe.throw(f"Row: {item.idx} Quantity can not be negative.")

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
			'remaining': item.available_qty,
			'picked_in_current': 0,
		})
	
	for i in self.available_qty:
		qty = 0
		for j in self.locations:
			if i.item_code == j.item_code and i.batch_no == j.batch_no:
				qty += j.qty
		i.picked_in_current = qty
		i.remaining -= qty

		if i.remaining < 0:
			frappe.throw(_(f"Remaining Qty Cannot be less than 0 ({i.remaining}) for item {i.item_code} and lot {i.lot_no}"))

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
	
def check_available_item_remaining_qty(self):
	for item in self.available_qty:
		if item.remaining < 0:
			frappe.throw(f"Row {item.idx}: Remaining Qty Less than 0")

def validate_item_qty(self):
	for row in self.locations:
		if row.qty < flt(row.delivered_qty + row.wastage_qty):
			frappe.throw(f"Row {row.idx}: Qty can not be Less than delivered qty {flt(row.delivered_qty + row.wastage_qty)}")
		if row.qty > row.so_qty:
			frappe.throw(f"Row {row.idx}: Qty can not be greater than sales order qty {row.so_qty}")

def update_delivered_percent(self):
	qty = 0
	delivered_qty = 0
	if self.locations:
		for index, item in enumerate(self.locations):
			qty += item.qty
			delivered_qty += item.delivered_qty

			item.db_set('idx', index + 1)

		if qty:
			self.db_set('per_delivered', (delivered_qty / qty) * 100)
		else:
			self.db_set('per_delivered', 0)

def update_sales_order(self, method):
	""" This function is used to update sales order data during pick list submit and cancel """

	# Looping through locations table
	for row in self.locations:
		if row.sales_order_item and frappe.db.exists("Sales Order Item", row.sales_order_item):
			soi_picked_qty = flt(frappe.db.get_value("Sales Order Item", row.sales_order_item, 'picked_qty') or 0)
			soi_qty = flt(frappe.db.get_value("Sales Order Item", row.sales_order_item, 'qty') or 0)
			
			if method == "submit":
				picked_qty = soi_picked_qty + row.qty
				if picked_qty > soi_qty:
					frappe.throw("Can not pick item {} in row {} more than {}".format(row.item_code, row.idx, row.qty - row.picked_qty))
	
			elif method == "cancel":	
				picked_qty = soi_picked_qty - row.qty

			frappe.db.set_value("Sales Order Item", row.sales_order_item, 'picked_qty', picked_qty)
	
	sales_order_list = set([row.sales_order for row in self.locations if row.sales_order])

	for row in sales_order_list:
		so = frappe.get_doc("Sales Order", row)
		update_sales_order_total_values(so)

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
	
	if item_code and sales_order:
		if item_code not in item_codes:
			frappe.throw(_(f"Item {item_code} is not in sales order {sales_order}"))
	
	if item_code:
		item_codes = [item_code]
	
	for item in item_codes:
		sales_order_list += frappe.db.sql(f"""
			SELECT 
				so.name as sales_order, so.customer, so.transaction_date, so.delivery_date, soi.packing_type as packing_type, so.per_picked, so.order_rank as order_item_priority,
				soi.name as sales_order_item, soi.item_code, soi.picked_qty, soi.qty - soi.picked_qty as qty, soi.qty as so_qty, soi.real_qty, soi.uom, soi.stock_qty, soi.stock_uom, soi.conversion_factor
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
def get_pick_list_so(sales_order, item_code, sales_order_item):
	pick_list_list = frappe.db.sql(f"""
		SELECT 
			pli.sales_order, pli.sales_order_item, pli.customer, pli.name as pick_list_item, batch.packing_type,
			pli.date, pli.item_code, pli.qty, pli.qty - pli.delivered_qty - pli.wastage_qty as picked_qty, pli.delivered_qty, pli.wastage_qty,
			pli.delivered_qty, pli.batch_no,
			pli.lot_no, pli.uom, pli.stock_qty, pli.stock_uom,
			pli.conversion_factor, pli.name, pli.parent
		FROM
			`tabPick List Item` as pli
			JOIN `tabBatch` as batch on batch.name = pli.batch_no
		WHERE
			pli.item_code = '{item_code}' AND
			pli.sales_order = '{sales_order}' AND
			pli.sales_order_item = '{sales_order_item}' AND
			pli.`docstatus` = 1
	""", as_dict = 1)

	for item in pick_list_list:
		actual_qty = frappe.db.sql(f"""
			SELECT
				SUM(sle.`actual_qty`) AS `actual_qty`
			FROM
				`tabStock Ledger Entry` sle, `tabBatch` batch
			WHERE
				sle.batch_no = batch.name
				and sle.`item_code` = '{item_code}'
				and sle.batch_no = '{item.batch_no}'
			GROUP BY
				`batch_no`
			HAVING `actual_qty` > 0
		""")[0][0]

		pick_list_available = frappe.db.sql(f"""
			SELECT SUM(pli.qty - (pli.delivered_qty + pli.wastage_qty)) FROM `tabPick List Item` as pli
			JOIN `tabPick List` AS pl ON pl.name = pli.parent
			WHERE `item_code` = '{item_code}'
			AND batch_no = '{item.batch_no}'
			AND pl.docstatus = 1
		""")[0][0] or 0

		# current_picked = item.picked_qty - item.delivered_qty - item.wastage_qty

		item.available_qty = actual_qty - pick_list_available + item.qty
		item.actual_qty = actual_qty
	
	return pick_list_list

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
				pli.conversion_factor, pli.name, pli.parent, so.per_picked, so.order_rank
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


@frappe.whitelist()
def unpick_item(sales_order, sales_order_item = None, pick_list = None, pick_list_item = None, unpick_qty = None):
	if pick_list_item and pick_list:
		unpick_qty = flt(unpick_qty)
		doc = frappe.get_doc("Pick List Item", pick_list_item)
		soi_doc = frappe.get_doc("Sales Order Item", sales_order_item)
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
			if unpick_qty > 0 and unpick_qty > doc.qty - doc.wastage_qty - doc.delivered_qty:
				frappe.throw(f"You can not unpick qty {unpick_qty} higher than remaining pick qty { doc.qty - doc.wastage_qty - doc.delivered_qty }")
			elif unpick_qty < 0:
				actual_qty = frappe.db.sql(f"""
					SELECT
						SUM(sle.`actual_qty`) AS `actual_qty`
					FROM
						`tabStock Ledger Entry` sle, `tabBatch` batch
					WHERE
						sle.batch_no = batch.name
						and sle.`item_code` = '{soi_doc.item_code}'
						and sle.batch_no = '{doc.batch_no}'
					GROUP BY
						`batch_no`
					HAVING `actual_qty` > 0
				""")[0][0]

				pick_list_available = frappe.db.sql(f"""
					SELECT SUM(pli.qty - (pli.delivered_qty + pli.wastage_qty)) FROM `tabPick List Item` as pli
					JOIN `tabPick List` AS pl ON pl.name = pli.parent
					WHERE `item_code` = '{soi_doc.item_code}'
					AND batch_no = '{doc.batch_no}'
					AND pl.docstatus = 1
				""")[0][0] or 0
				
				available_qty = actual_qty - pick_list_available + (doc.qty - doc.delivered_qty - doc.wastage_qty)
				if available_qty < doc.qty - unpick_qty:
					frappe.throw(f"Qty can not be greater than available qty {available_qty} in Lot {doc.lot_no}")
				
				doc.db_set('qty', doc.qty - unpick_qty)
				soi_doc.db_set('picked_qty', flt(soi_doc.picked_qty) - flt(unpick_qty))
			else:
				doc.db_set('qty', doc.qty - unpick_qty)
				soi_doc.db_set('picked_qty', flt(soi_doc.picked_qty) - flt(unpick_qty))

		update_delivered_percent(frappe.get_doc("Pick List", doc.parent))
		update_sales_order_total_values(frappe.get_doc("Sales Order", doc.sales_order))
	elif sales_order and sales_order_item:
		data = frappe.get_all("Pick List Item", {'sales_order': sales_order, 'sales_order_item': sales_order_item, 'docstatus': 1}, ['name'])
		
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
			update_sales_order_total_values(frappe.get_doc("Sales Order", doc.sales_order))
		
	else:
		data = frappe.get_all("Pick List Item", {'sales_order': sales_order, 'docstatus': 1}, ['name'])
		
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
		
		update_sales_order_total_values(frappe.get_doc("Sales Order", sales_order))
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
	
	return data

@frappe.whitelist()
def get_sales_order_items(sales_order):
	doc = frappe.get_doc("Sales Order", sales_order)

	items = []
	for item in doc.items:
		items.append({
			'sales_order': doc.name,
			'sales_order_item': item.name,
			'qty': item.qty - item.wastage_qty - item.delivered_qty,
			'real_qty': item.real_qty - item.delivered_real_qty,
			'item_code': item.item_code,
			'rate': item.rate,
			'discounted_rate': item.discounted_rate,
			'picked_qty': item.picked_qty - item.delivered_qty,
			'delivered_qty': item.delivered_qty,
			'wastage_qty': item.wastage_qty,
			'delivered_real_qty': item.delivered_real_qty,
			'packing_type': item.packing_type,
			'order_rank': doc.order_rank
		})
	return items

@frappe.whitelist()
def update_pick_list(items):
	picked_items = json.loads(items)
	for item in picked_items:
		pick_list_item_doc = frappe.get_doc("Pick List Item", item['pick_list_item'])

		picked_qty_old = pick_list_item_doc.qty
		diff_qty = picked_qty_old - flt(item['picked_qty'])

		if diff_qty:
			unpick_item(pick_list_item_doc.sales_order, sales_order_item = pick_list_item_doc.sales_order_item, pick_list = pick_list_item_doc.parent, pick_list_item = pick_list_item_doc.name, unpick_qty = diff_qty)

	return 'success'