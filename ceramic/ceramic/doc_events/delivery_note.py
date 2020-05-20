import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from frappe.utils import flt

def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = item.discounted_rate * item.real_qty
		item.discounted_net_amount = item.discounted_amount

		if frappe.db.get_value("Item", item.item_code, 'is_stock_item') and (not item.against_sales_order or not item.against_pick_list):
			frappe.throw(f"Row: {item.idx} No Sales Order or Pick List found for item {item.item_code}")

	so_doc = frappe.get_doc("Sales Order",self.items[0].against_sales_order)
	so_doc.db_set("customer",self.customer)
	so_doc.db_set("title",self.customer)
	so_doc.db_set("customer_name",self.customer_name)

def validate(self, method):
	validate_item_from_so(self)
	update_discounted_net_total(self)
	calculate_totals(self)

def validate_item_from_so(self):
	so_doc = frappe.get_doc("Sales Order",self.items[0].against_sales_order)
	for row in self.items:
		for d in so_doc.items:
			if row.so_detail == d.name and d.item_code != row.item_code:
				frappe.throw(_(f"Row: {row.idx} : Not allowed to change item {frappe.bold(row.item_code)}."))

def update_discounted_net_total(self):
	self.discounted_total = sum(x.discounted_amount for x in self.items)
	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
	testing_only_tax = 0
	
	for tax in self.taxes:
		if tax.testing_only:
			testing_only_tax += tax.tax_amount
	
	self.discounted_grand_total = self.discounted_net_total + self.total_taxes_and_charges - testing_only_tax
	self.discounted_rounded_total = round(self.discounted_grand_total)
	self.real_difference_amount = self.rounded_total - self.discounted_rounded_total


def calculate_totals(self):
	for d in self.items:
		d.wastage_qty = flt(d.picked_qty - d.qty)
		d.total_weight = flt(d.weight_per_unit * d.qty)
	self.total_qty = sum([row.qty for row in self.items])
	self.total_real_qty = sum([row.real_qty for row in self.items])
	self.total_net_weight = sum([row.total_weight for row in self.items])

@frappe.whitelist()
def before_submit(self, method):
	for item in self.items:
		if item.against_pick_list:
			pick_list_item = frappe.get_doc("Pick List Item", item.pl_detail)
			delivered_qty = item.qty + pick_list_item.delivered_qty
			wastage_qty = item.wastage_qty + pick_list_item.wastage_qty
			if delivered_qty > pick_list_item.qty:
				frappe.throw(f"Row {item.idx}: You can not deliver more tha picked qty")
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'delivered_qty', flt(delivered_qty))
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'wastage_qty', flt(wastage_qty))

		if item.against_sales_order:
			sales_order_item = frappe.get_doc("Sales Order Item", item.so_detail)
			delivered_real_qty = item.real_qty + sales_order_item.delivered_real_qty

			frappe.db.set_value("Sales Order Item", sales_order_item.name, 'delivered_real_qty', flt(delivered_real_qty))
		
		if item.pl_detail:
			pick_list_batch_no = frappe.db.get_value("Pick List Item", item.pl_detail, 'batch_no')

			if item.batch_no != pick_list_batch_no:
				frappe.throw(_(f"Row: {item.idx} : Batch No {frappe.bold(item.batch_no)} is Not same as Pick List Batch No {frappe.bold(pick_list_batch_no)}."))
	update_status_pick_list(self)

def update_status_pick_list(self):
	pick_list = list(set([item.against_pick_list for item in self.items if item.against_pick_list]))

	for pick in pick_list:
		pl = frappe.get_doc("Pick List", pick)
		delivered_qty = 0
		picked_qty = 0
		wastage_qty = 0

		for item in pl.locations:
			delivered_qty += item.delivered_qty
			wastage_qty += item.wastage_qty
			picked_qty += item.qty

			frappe.db.set_value("Pick List", pick, 'per_delivered', flt((delivered_qty / picked_qty) * 100))

	change_delivery_authority(self.name)

def on_submit(self,method):
	wastage_stock_entry(self)

def on_cancel(self, method):
	for item in self.items:
		if item.against_pick_list:
			pick_list_item = frappe.get_doc("Pick List Item", item.pl_detail)
			delivered_qty = pick_list_item.delivered_qty - item.qty
			wastage_qty = pick_list_item.wastage_qty - item.qty
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'delivered_qty', flt(delivered_qty))
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'wastage_qty', flt(wastage_qty))
	
		if item.against_sales_order:
			sales_order_item = frappe.get_doc("Sales Order Item", item.so_detail)
			delivered_real_qty = sales_order_item.delivered_real_qty - item.real_qty

			frappe.db.set_value("Sales Order Item", sales_order_item.name, 'delivered_real_qty', flt(delivered_real_qty))
			
	update_status_pick_list(self)
	cancel_wastage_entry(self)

def before_save(self, method):
	for row in self.items:
		row.full_qty = max(row.qty,row.real_qty)

def change_delivery_authority(name):
	dn_status = frappe.get_value("Delivery Note", name, "status")
	if dn_status == 'Completed':
		frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
	else:
		frappe.db.set_value("Delivery Note",name, "authority", "Authorized")

@frappe.whitelist()
def create_invoice(source_name, target_doc=None):
	doc = frappe.get_doc('Delivery Note', source_name)

	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		alternate_company = frappe.db.get_value("Company", source.company, "alternate_company")
		target.expense_account = ""

		target.update_stock = 1
		# target_doc.delivery_note = "T"

		if alternate_company:
			target.company = alternate_company

		if len(target.get("items")) == 0:
			frappe.throw(_(f"You can not create invoice in company {target.company}"))

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

		target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")
		
		if source.set_warehouse:
			target.set_warehouse = source.set_warehouse.replace(source_company_abbr, target_company_abbr)
		
		if source.taxes_and_charges:
			target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
			if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
				target.taxes_and_charges = target_taxes_and_charges
			
		# target.taxes = source.taxes
		# if source.taxes:
		# 	for index, value in enumerate(source.taxes):
		# 		if not source.taxes[index].testing_only:
		# 			if source.taxes[index].tax_exclusive:
		# 				source.taxes[index].included_in_print_rate = 0
		# 			if source.taxes[index].cost_center:
		# 				target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)

		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		returned_qty = 0
		if returned_qty_map.get(item_row.item_code, 0) > 0:
			returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
			returned_qty_map[item_row.item_code] -= pending_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		to_make_invoice_qty_map[item_row.name] = pending_qty

		return pending_qty
	
	def update_taxes(source_doc, target_doc, source_parent):
		target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")
		# item_code = frappe.db.get_value("Item", source_doc.item_code, "item_series")
		doc = frappe.get_doc("Company", target_company)
		target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
		
		target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)

		if source_doc.tax_exclusive:
			target_doc.included_in_print_rate = 0
		
		if source_doc.cost_center:
			target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

	
	def update_item(source_doc, target_doc, source_parent):
		target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")
		# item_code = frappe.db.get_value("Item", source_doc.item_code, "item_series")
		doc = frappe.get_doc("Company", target_company)
		target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
		# frappe.msgprint(item_code)
		# target_doc.item_code = item_code
		# target_doc.name = item_code
		target_doc.income_account = doc.default_income_account
		target_doc.expense_account = doc.default_expense_account
		target_doc.cost_center = doc.cost_center
		target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)


	doc = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Sales Invoice",
			"field_map": {
				"is_return": "is_return"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"item_code": "item_design",
				"item_series": "item_code",
				"parent": "delivery_docname",
				"name":"delivery_childname",
				"so_detail": "so_childname" ,
				"against_sales_order": "so_docname",
				"serial_no": "serial_no",
				"real_qty": "qty",
				"discounted_rate": "rate",
				"qty": "full_qty",
				"rate":"full_rate",
				"batch_no": "real_batch_no",
				"stock_uom": "stock_uom",
				"conversation_factor": "conversation_factor"
			},
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse",
				"batch_no",
				"lot_no",
				"discounted_rate",
				"real_qty"
			],
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.real_qty) > 0 and abs(doc.discounted_rate) != 0,
			"filter": lambda d: get_pending_qty(d) <= 0 if not doc.get("is_return") else get_pending_qty(d) > 0
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True,
			"condition": lambda doc: abs(doc.testing_only) == 0,
			"postprocess": update_taxes,
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values, ignore_permissions = True)

	if len(doc.items) == 0:
		alternate_company = frappe.db.get_value("Company", self.company, 'alternate_company')
		frappe.throw(f"All item has already been invoiced in company {alternate_company}")

	return doc

@frappe.whitelist()
def on_update_after_submit(self, method):
	change_authority(self)

def change_authority(self):
	if self.status == 'Completed':
		self.db_set("authority", "Unauthorized")
	else:
		self.db_set("authority", "Authorized")

def get_returned_qty_map(delivery_note):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(frappe.db.sql("""select dn_item.item_code, sum(abs(dn_item.qty)) as qty
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name = dn_item.parent
			and dn.docstatus = 1
			and dn.is_return = 1
			and dn.return_against = %s
		group by dn_item.item_code
	""", delivery_note))

	return returned_qty_map

def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""", delivery_note):
			if not invoiced_qty_map.get(dn_detail):
				invoiced_qty_map[dn_detail] = 0
			invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map

@frappe.whitelist()
def create_delivery_note_from_pick_list(source_name, target_doc = None):
	def update_item_quantity(source, target, source_parent):
		target.qty = flt(source.qty) - flt(source.delivered_qty)
		target.stock_qty = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.conversion_factor)
	
	doc = get_mapped_doc('Pick List', source_name, {
		'Pick List': {
			'doctype': 'Delivery Note',
			'validation': {
				'docstatus': ['=', 1]
			}
		},
		'Sales Order Item': {
			'doctype': 'Delivery Note Item',
			'field_map': {
				'parent': 'sales_order',
				'name': 'sales_order_item'
			},
			'postprocess': update_item_quantity,
			'condition': lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		},
	}, target_doc)

	return doc

def wastage_stock_entry(self):
	flag = 0
	for row in self.items:
		if row.wastage_qty > 0:
			flag = 1
			break
	if flag == 1:
		abbr = frappe.db.get_value('Company',self.company,'abbr')
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Issue"
		se.purpose = "Material Issue"
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.set_posting_time = 1
		se.company = self.company
		se.reference_doctype = self.doctype
		se.reference_docname = self.name
		se.wastage = 1
	
		for row in self.items:
			if row.wastage_qty > 0:
				se.append("items",{
					'item_code': row.item_code,
					'qty': row.wastage_qty,
					'basic_rate': row.rate,
					'batch_no': row.batch_no,
					's_warehouse': row.warehouse
				})
		try:
			se.save(ignore_permissions=True)
			se.submit()
		except Exception as e:
			frappe.throw(str(e))

def cancel_wastage_entry(self):
	if frappe.db.exists("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name}):
		se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		se.flags.ignore_permissions = True
		try:
			se.cancel()
		except Exception as e:
			raise e
		se.db_set('reference_doctype','')
		se.db_set('reference_docname','')