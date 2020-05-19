import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from ceramic.query import set_batches

def before_save(self, method):	
	abbr = frappe.db.get_value('Company',self.company,'abbr')
	if self.is_opening == 'Yes':
		for row in self.items:
			row.expense_account = f"Temporary Opening - {abbr}"

def validate(self,method):
	calculate_totals(self)
	if self._action == 'submit':
		set_batches(self, 't_warehouse')
		
def calculate_totals(self):
	premium_qty = 0.0
	golden_qty = 0.0
	classic_qty = 0.0
	economy_qty = 0.0
	total_qty = 0.0
	
	for d in self.items:
		total_qty += d.qty
		if d.tile_quality == "Premium":
			premium_qty += d.qty
		if d.tile_quality == "Golden":
			golden_qty += d.qty
		if d.tile_quality == "Classic":
			classic_qty += d.qty
		if d.tile_quality == "Economy":
			economy_qty += d.qty
	self.total_qty = total_qty
	self.premium_qty = premium_qty
	self.golden_qty = golden_qty
	self.classic_qty = classic_qty
	self.economy_qty = economy_qty
	self.premium_percentage = flt(premium_qty/total_qty*100)

def before_validate(self,method):
	StockEntry.validate_finished_goods = validate_finished_goods
	
	to_list = []
	for row in self.items:
		if row.qty == 0:
			to_list.append(row)	
	[self.remove(row) for row in to_list]

def before_submit(self,method):
	StockEntry.update_work_order = update_work_order

def before_cancel(self,method):
	StockEntry.update_work_order = update_work_order  
	StockEntry.delete_auto_created_batches = delete_auto_created_batches
	
def delete_auto_created_batches(self):
	pass

def validate_finished_goods(self):
	"""validation: finished good quantity should be same as manufacturing quantity"""
	if not self.work_order: return

	items_with_target_warehouse = []
	allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
		"overproduction_percentage_for_work_order"))

	production_item, wo_qty = frappe.db.get_value("Work Order",
		self.work_order, ["production_item", "qty"])

	for d in self.get('items'):
		if (self.purpose != "Send to Subcontractor" and d.bom_no
			and flt(d.transfer_qty) > flt(self.fg_completed_qty) and d.item_code == production_item):
			frappe.throw(_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}"). \
				format(d.idx, d.transfer_qty, self.fg_completed_qty))

		if self.work_order and self.purpose == "Manufacture" and d.t_warehouse:
			items_with_target_warehouse.append(d.item_code)

	if self.work_order and self.purpose == "Manufacture":
		allowed_qty = wo_qty + (allowance_percentage/100 * wo_qty)
		if self.fg_completed_qty > allowed_qty:
			frappe.throw(_("For quantity {0} should not be greater than work order quantity {1}")
				.format(flt(self.fg_completed_qty), wo_qty))

		# if production_item not in items_with_target_warehouse:
		# 	frappe.throw(_("Finished Item {0} must be entered for Manufacture type entry")
		# 		.format(production_item))

def update_work_order(self):
		def _validate_work_order(pro_doc):
			if flt(pro_doc.docstatus) != 1:
				frappe.throw(_("Work Order {0} must be submitted").format(self.work_order))

			if pro_doc.status == 'Stopped':
				frappe.throw(_("Transaction not allowed against stopped Work Order {0}").format(self.work_order))

		if self.job_card:
			job_doc = frappe.get_doc('Job Card', self.job_card)
			job_doc.set_transferred_qty(update_status=True)

		if self.work_order:
			pro_doc = frappe.get_doc("Work Order", self.work_order)
			_validate_work_order(pro_doc)
			pro_doc.run_method("update_status")
			if self.fg_completed_qty:
				pro_doc.run_method("update_work_order_qty")
				# if self.purpose == "Manufacture":
				# 	pro_doc.run_method("update_planned_qty")

# @frappe.whitelist()
# def get_product_price(item_code,price_list):
# 	rate = frappe.db.get_value("Item Price",{'price_list':price_list,'buying':1,'item_code':item_code},'price_list_rate')
	
# 	if not rate:
# 		frappe.throw(_("Price not found for item <b>{}</b> in Price list <b>{}/b>").format(item_code,price_list))
# 	else:
# 		return rate

@frappe.whitelist()
def get_product_price(item_code, item_group = None):
	if not item_group:
		item_group = frappe.db.get_value("Item",item_code,'item_group')
	rate = frappe.db.get_value("Item Group",item_group,'production_price')
	if not rate:
		frappe.throw(_("Price not found for item <b>{}</b> in item group <b>{}/b>").format(item_code,item_group))
	else:
		return rate
