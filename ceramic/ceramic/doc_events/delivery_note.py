import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values
from frappe.utils import flt
from ceramic.ceramic.doc_events.sales_order import update_sales_order_total_values
from ceramic.ceramic.doc_events.sales_invoice import validate_tax_template
from erpnext.stock.doctype.serial_no.serial_no import get_delivery_note_serial_no


def before_validate(self, method):
	if self.si_ref:
		if frappe.db.get_value("Sales Invoice",self.si_ref,"si_ref"):
			frappe.throw("Sales Invoice is already selected.please select correct invoice.")
	self.sales_team = []
	self.flags.ignore_permissions = True

	if self.invoice_company == self.company or not self.invoice_company:
		self.invoice_company = frappe.db.get_value("Company", self.company, "alternate_company")

	if self.si_ref:
		invoice_company, invoice_net_total = frappe.db.get_value("Sales Invoice",self.si_ref,["company","net_total"])

		for item in self.items:
			item.discounted_amount = invoice_net_total * item.net_amount / self.net_total
			item.discounted_net_amount = item.discounted_amount

		# if frappe.db.get_value("Item", item.item_code, 'is_stock_item') and (not item.against_sales_order or not item.against_pick_list):
			# frappe.throw(f"Row: {item.idx} No Sales Order or Pick List found for item {item.item_code}")
	for item in self.items:
		if (not item.rate) and (item.so_detail):
			item.rate = frappe.db.get_value("Sales Order Item", item.so_detail, 'rate')
		
		# if (not item.discounted_rate) and (item.so_detail):
		# 	item.discounted_rate = frappe.db.get_value("Sales Order Item", item.so_detail, 'discounted_rate')
	validate_item_from_so(self)
	sales_order_list = list(set([x.against_sales_order for x in self.items if x.against_sales_order]))

	for x in sales_order_list:
		so_doc = frappe.get_doc("Sales Order",x)
		so_doc.db_set("customer",self.customer)
		so_doc.db_set("title",self.customer)
		so_doc.db_set("customer_name",self.customer_name)

def validate(self, method):
	update_lock_qty(self)
	validate_item_from_picklist(self)
	if self._action == "submit":
		validate_tax_template(self)
	update_discounted_net_total(self)
	calculate_totals(self)

def update_lock_qty(self):
	if self.is_new():	
		if self.items[0].against_sales_order:
			so_doc = frappe.get_doc("Sales Order",self.items[0].against_sales_order)
			so_doc.db_set('lock_picked_qty',1)

def validate_item_from_so(self):
	for row in self.items:
		if frappe.db.exists("Sales Order Item",row.so_detail):
			so_item = frappe.db.get_value("Sales Order Item",row.so_detail,"item_code")
			if row.item_code != so_item:
				frappe.throw(_(f"Row: {row.idx}: Not allowed to change item {frappe.bold(row.item_code)}."))


def validate_item_from_picklist(self):
	for row in self.items:
		if row.pl_detail:
			if frappe.db.exists("Pick List Item",row.pl_detail):
				picked_qty = flt(frappe.db.get_value("Pick List Item",row.pl_detail,"qty"))
				if flt(row.qty) > picked_qty:
					frappe.throw(_(f"Row: {row.idx}: Delivered Qty {frappe.bold(row.qty)} can not be higher than picked Qty {frappe.bold(picked_qty)} for item {frappe.bold(row.item_code)}."))
			else:
				frappe.throw(_(f"Row: {row.idx}: The item {frappe.bold(row.item_code)} has been unpicked from picklist {frappe.bold(row.against_pick_list)}"))


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
		#d.wastage_qty = flt(d.picked_qty - d.qty)
		d.total_weight = flt(d.weight_per_unit * d.qty)
	self.total_qty = sum([row.qty for row in self.items])
	self.total_real_qty = sum([row.real_qty for row in self.items])
	self.total_net_weight = sum([row.total_weight for row in self.items])

def check_invoice_company(self):
	if self.invoice_company:
		if frappe.db.get_value("Company",self.invoice_company,'authority') == "Unauthorized":
			frappe.throw(_("Invoice company should be authoried company"))

def check_item_without_pick(self):
	
	item_without_pick_list_dict = {}
	for row in self.items:
		if not row.pl_detail and row.so_detail:
			if not item_without_pick_list_dict.get(row.so_detail):
				item_without_pick_list_dict[row.so_detail] = 0
			
			item_without_pick_list_dict[row.so_detail] += row.qty

	for key, row in item_without_pick_list_dict.items():
		item_code, parent, so_qty, so_picked_qty, so_delivered_qty, so_delivered_without_pick = frappe.db.get_value("Sales Order Item", key, ['item_code', 'parent', 'qty', 'picked_qty', 'delivered_qty', 'delivered_without_pick'])
		
		allowed_qty = so_qty - so_picked_qty - so_delivered_without_pick
		
		if allowed_qty < row:
			frappe.throw(f"You can not deliver more than {allowed_qty} without Pick List for Item {item_code} for Sales Order {parent}.")

def update_status_pick_list_and_sales_order(self):
	for item in self.items:
		if item.against_pick_list:
			pick_list_item = frappe.get_doc("Pick List Item", item.pl_detail)
			if item.batch_no != pick_list_item.batch_no:
				frappe.throw(f"Row: {item.idx} You can not change batch as pick list is already made.")
			
			delivered_qty = item.qty + pick_list_item.delivered_qty
			wastage_qty = item.wastage_qty + pick_list_item.wastage_qty
			
			if delivered_qty + wastage_qty > pick_list_item.qty:
				frappe.throw(f"Row {item.idx}: You can not deliver more than picked qty")
			
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'delivered_qty', flt(delivered_qty))
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'wastage_qty', flt(wastage_qty))

		if item.against_sales_order:
			sales_order_item = frappe.get_doc("Sales Order Item", item.so_detail)
			wastage_qty = item.wastage_qty + sales_order_item.wastage_qty
			delivered_real_qty = item.real_qty + sales_order_item.delivered_real_qty
			delivered_qty = item.qty + sales_order_item.delivered_qty


			if delivered_qty + wastage_qty > sales_order_item.qty:
				frappe.throw(f"Row {item.idx}: You can not deliver more than sales order qty")
			
			frappe.db.set_value("Sales Order Item", sales_order_item.name, 'delivered_real_qty', flt(delivered_real_qty))
			frappe.db.set_value("Sales Order Item", sales_order_item.name, 'wastage_qty', flt(wastage_qty))

			if item.against_pick_list:
				frappe.db.set_value("Sales Order Item", sales_order_item.name, 'picked_qty', flt(sales_order_item.picked_qty - wastage_qty))

			update_sales_order_total_values(frappe.get_doc("Sales Order", item.against_sales_order))
		
		if not item.against_pick_list and item.against_sales_order:
			so_delivered_without_pick = frappe.db.get_value("Sales Order Item", item.so_detail, 'delivered_without_pick')
			frappe.db.set_value("Sales Order Item", item.so_detail, 'delivered_without_pick', so_delivered_without_pick + item.qty)
		
		if item.pl_detail:
			pick_list_batch_no = frappe.db.get_value("Pick List Item", item.pl_detail, 'batch_no')

			if item.batch_no != pick_list_batch_no:
				frappe.throw(_(f"Row: {item.idx} : Batch No {frappe.bold(item.batch_no)} is Not same as Pick List Batch No {frappe.bold(pick_list_batch_no)}."))

def before_submit(self, method):
	check_invoice_company(self)
	check_item_without_pick(self)
	update_status_pick_list_and_sales_order(self)


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

		if picked_qty == 0:
			per_delivered = 100.0
		else:
			per_delivered = flt((delivered_qty / picked_qty) * 100)
		frappe.db.set_value("Pick List", pick, 'per_delivered', per_delivered)

	change_delivery_authority(self.name)

def on_submit(self,method):
	validate_addresses(self)
	wastage_stock_entry(self)
	check_rate_qty(self)
	if self.si_ref:
		frappe.db.set_value("Sales Invoice",self.si_ref,"dn_ref",self.name)
	for item in self.items:
		if item.against_sales_order:
			update_sales_order_total_values(frappe.get_doc("Sales Order", item.against_sales_order))
	

def validate_addresses(self):
	if not self.shipping_address_name:
		frappe.throw(_("Shipping Address is mandatory"))
	if not self.customer_address:
		frappe.throw(_("Billing Address is mandatory"))



def validate_addresses(self):
	if not self.shipping_address_name:
		frappe.throw(_("Shipping Address is mandatory"))
	if not self.customer_address:
		frappe.throw(_("Billing Address is mandatory"))

def check_rate_qty(self):
	for item in self.items:
		if not item.rate or item.rate <= 0:
			frappe.throw(f"Row: {item.idx} Rate cannot be 0")
		if not item.qty or item.qty == 0:
			frappe.throw(f"Row: {item.idx} Quantity can not be 0 ")

def check_qty_rate(self):
	for item in self.items:
		if not item.discounted_rate:
			frappe.msgprint(f"Row {item.idx}: Discounted rate is 0, you will not be able to create invoice in {frappe.db.get_value('Company', self.company, 'alternate_company')}")
		if not item.real_qty:
			frappe.msgprint(f"Row {item.idx}: Real qty is 0, you will not be able to create invoice in {frappe.db.get_value('Company', self.company, 'alternate_company')}")


def on_cancel(self, method):		
	for item in self.items:
		if item.against_pick_list:
			pick_list_item = frappe.get_doc("Pick List Item", item.pl_detail)
			delivered_qty = pick_list_item.delivered_qty - item.qty
			wastage_qty = pick_list_item.wastage_qty - item.wastage_qty
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'delivered_qty', flt(delivered_qty))
			frappe.db.set_value("Pick List Item", pick_list_item.name, 'wastage_qty', flt(wastage_qty))
	
		if item.against_sales_order:
			sales_order_item = frappe.get_doc("Sales Order Item", item.so_detail)
			delivered_real_qty = sales_order_item.delivered_real_qty - item.real_qty
			wastage_qty = sales_order_item.wastage_qty - item.wastage_qty
			frappe.db.set_value("Sales Order Item", sales_order_item.name, 'delivered_real_qty', flt(delivered_real_qty))
			frappe.db.set_value("Sales Order Item", sales_order_item.name, 'wastage_qty', flt(wastage_qty))
			if item.against_pick_list:
				if sales_order_item.picked_qty + wastage_qty > sales_order_item.qty:
					frappe.throw(f"Please Unpick {sales_order_item.picked_qty + wastage_qty - sales_order_item.qty} for Sales Order {sales_order_item.parent} Row: {sales_order_item.idx}")
				
				frappe.db.set_value("Sales Order Item", sales_order_item.name, 'picked_qty', flt(sales_order_item.picked_qty + item.wastage_qty))
			update_sales_order_total_values(frappe.get_doc("Sales Order", item.against_sales_order))
		
		if not item.against_pick_list and item.against_sales_order:
			so_delivered_without_pick = frappe.db.get_value("Sales Order Item", item.so_detail, 'delivered_without_pick')
			frappe.db.set_value("Sales Order Item", item.so_detail, 'delivered_without_pick', item.qty - so_delivered_without_pick)
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
	from erpnext.stock.doctype.delivery_note.delivery_note import get_returned_qty_map, get_invoiced_qty_map
	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		alternate_company = source.invoice_company or frappe.db.get_value("Company", source.company, "alternate_company")
		target.expense_account = ""

		target.update_stock = 1
		# target_doc.delivery_note = "T"

		if alternate_company:
			target.company = alternate_company
			target.authority = frappe.db.get_value("Company",alternate_company,'authority')

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
		target_company = source_parent.invoice_company or frappe.db.get_value("Company", source_parent.company, "alternate_company")
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
		target_company = source_parent.invoice_company or frappe.db.get_value("Company", source_parent.company, "alternate_company")
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
		if source_doc.warehouse:
			target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)


	doc = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Sales Invoice",
			"field_map": {
				"is_return": "is_return",
				"posting_date":"posting_date",
				"posting_time":"posting_time",
				"set_posting_time":"set_posting_time"
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
				"real_qty",
				"authority"
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
def create_invoice_test(source_name, target_doc=None):
	doc = frappe.get_doc('Delivery Note', source_name)

	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been Invoiced/Returned"))

		target.run_method("calculate_taxes_and_totals")

		# set company address
		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = to_make_invoice_qty_map[source_doc.name]

		if source_doc.serial_no and source_parent.per_billed > 0:
			target_doc.serial_no = get_delivery_note_serial_no(source_doc.item_code,
				target_doc.qty, source_parent.name)

	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		returned_qty = 0
		if returned_qty_map.get(item_row.name, 0) > 0:
			returned_qty = flt(returned_qty_map.get(item_row.name, 0))
			returned_qty_map[item_row.name] -= pending_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		to_make_invoice_qty_map[item_row.name] = pending_qty

		return pending_qty

	doc = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Sales Invoice",
			"field_map": {
				"is_return": "is_return",
				"posting_date":"posting_date",
				"posting_time":"posting_time",
				"set_posting_time":"set_posting_time",
				"si_ref":"si_ref",
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"name": "dn_detail",
				"parent": "delivery_note",
				"so_detail": "so_detail",
				"against_sales_order": "sales_order",
				"serial_no": "serial_no",
				"cost_center": "cost_center"
			},
			"postprocess": update_item,
			"filter": lambda d: get_pending_qty(d) <= 0 if not doc.get("is_return") else get_pending_qty(d) > 0
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	if doc.si_ref:
		si_company_series, si_naming_series, si_series_value = frappe.db.get_value("Sales Invoice",doc.si_ref,["company_series","naming_series","series_value"])
		doc.naming_series =  'A' + str(si_company_series) + si_naming_series
		doc.series_value = si_series_value
		doc.save(ignore_permissions=True)
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
		if row.wastage_qty < 0:
			frappe.throw("Row {}: Please Don't Enter Negative Value in Wastage Qty".format(row.idx))
		elif row.wastage_qty > 0:
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

		se.save(ignore_permissions=True)
		se.submit()

def cancel_wastage_entry(self):
	if frappe.db.exists("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name}):
		se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		se.flags.ignore_permissions = True
		if se.docstatus == 1:
			se.cancel()
		se.db_set('reference_doctype','')
		se.db_set('reference_docname','')
		se.delete()

@frappe.whitelist()
def get_rate_discounted_rate(item_code, customer, company, so_number = None):
	""" This function is use to get discounted rate and rate """
	item_group, tile_quality = frappe.get_value("Item", item_code, ['item_group', 'tile_quality'])
	# parent_item_group = frappe.get_value("Item Group", item_group, 'parent_item_group')

	count = frappe.db.sql(f"""
		SELECT 
			COUNT(*) 
		FROM 
			`tabDelivery Note Item` as soi 
		JOIN 
			`tabDelivery Note` as so ON so.`name` = soi.`parent`
		WHERE 
			soi.`item_group` = '{item_group}' AND
			soi.`docstatus` = 1 AND
			so.customer = '{customer}' AND
			soi.`tile_quality` = '{tile_quality}' AND
			so.`company` = '{company}'
		LIMIT 1
	""")
	where_clause = ''
	if count[0][0]:
		where_clause = f"soi.item_group = '{item_group}' AND"
	
	data = None

	if so_number:
		data = frappe.db.sql(f"""
			SELECT 
				soi.`rate` as `rate`, soi.`discounted_rate` as `discounted_rate`
			FROM 
				`tabDelivery Note Item` as soi 
			JOIN
				`tabDelivery Note` as so ON soi.parent = so.name
			WHERE
				{where_clause}
				soi.`tile_quality` = '{tile_quality}' AND
				so.`customer` = '{customer}' AND
				so.`company` = '{company}' AND
				so.`docstatus` != 2 AND
				so.`name` = '{so_number}'
			ORDER BY
				soi.`creation` DESC
			LIMIT 
				1
		""", as_dict = True)

	if not data:
		data = frappe.db.sql(f"""
			SELECT 
				soi.`rate` as `rate`, soi.`discounted_rate` as `discounted_rate`
			FROM 
				`tabDelivery Note Item` as soi JOIN
				`tabDelivery Note` as so ON soi.parent = so.name
			WHERE
				{where_clause}
				soi.`tile_quality` = '{tile_quality}' AND
				so.`customer` = '{customer}' AND
				so.`company` = '{company}' AND
				so.`docstatus` != 2
			ORDER BY
				soi.`creation` DESC
			LIMIT 
				1
		""", as_dict = True)

	return data[0] if data else {'rate': 0, 'discounted_rate': 0}
