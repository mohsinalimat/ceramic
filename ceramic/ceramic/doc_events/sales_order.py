from __future__ import unicode_literals

import frappe
from frappe import _
from datetime import date,timedelta,datetime
from frappe.utils import flt, cint
from frappe.model.utils import get_fetch_values
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.accounts.party import get_party_details
import math
import datetime

def before_validate(self, method):
	ignore_permission(self)
	setting_real_qty(self)
	# update_transaction_status(self)
	
	if not self.primary_customer:
		self.primary_customer = self.customer

def validate(self, method):
	calculate_order_priority(self)
	calculate_rate(self)
	update_discounted_amount(self)
	update_discounted_net_total(self)
	# create_main_sales_order(self)

def on_submit(self, method):
	create_main_sales_order(self)
	checking_real_qty(self)
	update_sales_order_total_values(self)
	#check_qty_rate(self)
	update_order_rank(self)

#start
def on_trash(self, method):
	pass
	# delete_sales_order(self)

# def before_update_after_submit(self, method):
# 	"""On Update after Submit Custom Function for Sales Invoice"""
# 	update_linked_invoice(self)


# def on_cancel(self, test):
# 	"""On Cancel Custom Function for Sales Invoice"""
# 	cancel_main_sales_invoice(self)

#sales order status change
def cancel_on_sales_status():
	so_list = frappe.get_list("Sales Order", {'authority': 'Authorized'})
	for sale_order in so_list:
		st = None
		if frappe.db.exists("Sales Order",sale_order.name):
			so_ref = frappe.db.get_value("Sales Order",sale_order.name,'so_ref')
			if so_ref:
				st = frappe.db.get_value("Sales Order", so_ref , "status")
			
				if not st or st in ["Cancelled","Completed","Closed"]:
					so_doc = frappe.get_doc("Sales Order",sale_order.name)
					if so_doc.docstatus == 1:
						so_doc.so_ref = ''
						frappe.db.set_value("Sales Order",sale_order.so_ref,"so_ref",'')
						so_doc.cancel()
						so_doc.delete()

					elif so_doc.docstatus != 1:
						so_doc.delete()
		

	# for item in pick_list_list:
	# 	pl = frappe.get_doc("Pick List Item", item.name)
	# 	if not frappe.db.exists("Sales Order Item", pl.sales_order_item):
	# 		if pl.docstatus == 1:
	# 			pl.cancel()
	# 		pl.delete()

def create_main_sales_order(self):
	
	# Getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")
	# so_list = frappe.get_list("Sales Order", {'authority': 'Authorized'})
	# for o in so_list:
	# 	st = frappe.db.get_value("Sales Order", o.name , "status")
	# 	frappe.msgprint(str(st))

	def get_sales_order_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_target_values(source, target):
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.so_ref = self.name
			target.authority = "Authorized"

			# if source.is_return:
			# 	target.is_return = source.is_return
			# 	target.return_against = frappe.db.get_value("Sales Order", source.return_against, 'so_ref')


			# if source.debit_to:
			# 	target.debit_to = source.debit_to.replace(source_company_abbr, target_company_abbr)
			if source.taxes_and_charges:
				taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", taxes_and_charges):
					target.taxes_and_charges = taxes_and_charges
				else:
					target.taxes_and_charges = ''

			if source.taxes:
				for index, i in enumerate(source.taxes):
					target.taxes[index].charge_type = source.taxes[index].charge_type
					target.taxes[index].included_in_print_rate = source.taxes[index].included_in_print_rate
					if source.taxes[index].cost_center:
						target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)
					if source.taxes[index].account_head:
						target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
			if self.amended_from:
				name = frappe.db.get_value("Sales Order", {"so_ref": source.amended_from}, "name")
				target.amended_from = name

			target.set_missing_values()

		def account_details(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			target_doc.real_qty = source_doc.qty


			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
			
			# for i in source_parent.items:
			# 	target_item = frappe.db.get_value("Item", i.item_code, "item_series")
			# 	target_doc.item_code = target_item


			# if source_doc.income_account:
			# 	target_doc.income_account = source_doc.income_account.replace(source_company_abbr, target_company_abbr)
			# if source_doc.expense_account:
			# 	target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
			# if source_doc.cost_center:
			# 	target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Sales Order": {
				"doctype": "Sales Order",
				"field_map": {
					"so_ref": "name",
				},
				"field_no_map":{
					"authority",
					"update_stock",
					"transaction_status"
				}
			},
			"Sales Order Item": {
				"doctype": "Sales Order Item",
				"field_map": {
					"item_name": "item_name",
					"item_code": "item_code",
					"rate": "discounted_rate",
					"qty": "real_qty",
					
					"warehouse":"warehouse",
					# "qty": "real_qty",
					# "delivery_docname": "delivery_note",
					# "delivery_childname": "dn_detail",
					# "so_childname": "so_detail",
					# "so_docname": "sales_order",
					# "real_batch_no": "batch_no",
					# "is_opening": "is_opening"
				},
				# "field_no_map": {
				# 	"full_rate",
				# 	"full_qty",
				# 	"series",
				# 	"real_batch_no"
				# },
				# "postprocess": account_details,
			    "postprocess": account_details,
			}
		}

		doclist = get_mapped_doc(
			"Sales Order",
			source_name,
			fields,
			target_doc,
			set_target_values,
			ignore_permissions=ignore_permissions
		)

		return doclist

		
	def make_si_from_dn(source_name, target_doc=None):
		doc = frappe.get_doc('Delivery Note', source_name)

		to_make_invoice_qty_map = {}
		returned_qty_map = get_returned_qty_map(source_name)
		invoiced_qty_map = get_invoiced_qty_map(source_name)

		def set_missing_values(source, target):
			target.ignore_pricing_rule = 1
			target.run_method("set_missing_values")
			target.run_method("set_po_nos")

			if len(target.get("items")) == 0:
				frappe.throw(_("All these items have already been invoiced"))

			target.run_method("calculate_taxes_and_totals")

			# set company address
			if source.company_address:
				target.update({'company_address': source.company_address})
			else:
				# set company address
				target.update(get_company_address(target.company))

			if target.company_address:
				target.update(get_fetch_values("Sales Order", 'company_address', target.company_address))

		def update_item(source_doc, target_doc, source_parent):
			target_company_income_account = frappe.db.get_value("Company", source_parent.company, "default_income_account")
			if target_company_income_account:
				target_doc.income_account = target_company_income_account

			target_doc.qty = to_make_invoice_qty_map[source_doc.name]
			
			# if source_doc.serial_no and source_parent.per_billed > 0 and not source_parent.is_return:
			# 	target_doc.serial_no = get_delivery_note_serial_no(source_doc.item_code,
			# 		target_doc.qty, source_parent.name)

		# def get_pending_qty(item_row):
		# 	pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		# 	returned_qty = 0
		# 	if returned_qty_map.get(item_row.item_code, 0) > 0:
		# 		returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
		# 		returned_qty_map[item_row.item_code] -= pending_qty

		# 	if returned_qty:
		# 		if returned_qty >= pending_qty:
		# 			pending_qty = 0
		# 			returned_qty -= pending_qty
		# 		else:
		# 			pending_qty -= returned_qty
		# 			returned_qty = 0

		# 	to_make_invoice_qty_map[item_row.name] = pending_qty

		# 	return pending_qty

		# doc = get_mapped_doc("Delivery Note", source_name, {
		# 	"Delivery Note": {
		# 		"doctype": "Sales Invoice",
		# 		"field_map": {
		# 			"is_return": "is_return"
		# 		},
		# 		"validation": {
		# 			"docstatus": ["=", 1]
		# 		}
		# 	},
		# 	"Delivery Note Item": {
		# 		"doctype": "Sales Invoice Item",
		# 		"field_map": {
		# 			"name": "dn_detail",
		# 			"parent": "delivery_note",
		# 			"so_detail": "so_detail",
		# 			"against_sales_order": "sales_order",
		# 			"serial_no": "serial_no",
		# 			"cost_center": "cost_center",
		# 		},
		# 		"postprocess": update_item,
		# 		"filter": lambda d: get_pending_qty(d) <= 0 if not doc.get("is_return") else get_pending_qty(d) > 0
		# 	},
		# 	"Sales Taxes and Charges": {
		# 		"doctype": "Sales Taxes and Charges",
		# 		"add_if_empty": True
		# 	},
		# 	"Sales Team": {
		# 		"doctype": "Sales Team",
		# 		"field_map": {
		# 			"incentives": "incentives"
		# 		},
		# 		"add_if_empty": True
		# 	}
		# }, target_doc, set_missing_values)

		# return doc

	# If company is authorized then only cancel another invoice
	# if self.items[0].delivery_docname:
	# 	delivery_doc = frappe.get_doc("Delivery Note", self.items[0].delivery_docname)
		
	if authority == "Unauthorized" and not self.dont_replicate:
		
		so = get_sales_order_entry(self.name)
		so.naming_series = self.naming_series
		# so.series_value = self.series_value
		so.flags.ignore_permissions = True
		so.so_ref = self.name
		so.delivery_date = self.delivery_date
		so.transaction_date = self.transaction_date
		if self.amended_from:
			so.amended_from = frappe.db.get_value("Sales Order", {"so_ref": self.amended_from}, "name")
		so.ignore_item_validate = True
		so.save(ignore_permissions = True)
		for tax in so.taxes:
			if tax.tax_exclusive and tax.charge_type != "Actual":
				tax.included_in_print_rate = 1
		so.save(ignore_permissions = True)
		so.pay_amount_left = so.rounded_total - self.rounded_total
		if so.pay_amount_left < 0:
			so.pay_amount_left = 0.0
		so.save(ignore_permissions = True)
		self.db_set('so_ref', so.name)
		so.submit()
	
	# if authority == "Unauthorized" and not self.so_ref:
	# 	self.db_set('pay_amount_left', self.rounded_total)

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

def update_linked_order(self):
	self.flags.ignore_validate_update_after_submit = True
	if self.so_ref:
		so = frappe.get_doc("Sales Order",self.so_ref)
		so.db_set('sales_partner',self.sales_partner)
		so.db_set('primary_customer',self.primary_customer)
		if self.sales_team:
			for row in self.sales_team:
				so.append('sales_team',{
					'sales_person': row.sales_person,
					'contact_no': row.contact_no,
					'allocated_percentage': row.allocated_percentage,
					'allocated_amount': row.allocated_amount,
					'commission_rate': row.commission_rate,
					'incentives': row.incentives,
					'company': row.company,
					'regional_sales_manager': row.regional_sales_manager,
					'sales_manager': row.sales_manager
				})

def cancel_main_sales_order(self):
	company_auth = frappe.db.get_value("Company", self.company,'authority')
	if company_auth == "Authorized":
		if self.so_ref:
			so_ref = frappe.get_doc("Sales Order",self.so_ref)
			so_ref.db_set('so_ref','')
			so_ref.db_update()
		self.db_set('so_ref','')
		self.db_update()
		so = None
	# else:
	# 	if self.so_ref:
	# 		so = frappe.get_doc("Sales Order", {'so_ref':self.name})
	# 	else:
	# 		so = None
	# if so:
	# 	if so.docstatus == 1:
	# 		so.flags.ignore_permissions = True
	# 		try:
	# 			so.cancel()
	# 		except Exception as e:
	# 			frappe.db.rollback()
	# 			frappe.throw(e)
	

def delete_sales_order(self):
	ref_name = self.so_ref
	frappe.db.set_value("Sales Order", self.name, 'so_ref', '')    
	frappe.db.set_value("Sales Order", ref_name, 'so_ref', '') 
	frappe.delete_doc("Sales Order", ref_name, force = 1, ignore_permissions=True)  

#end

def update_order_rank(self):
	order_rank = frappe.db.sql(f"select order_rank, ABS(order_item_priority - {self.order_item_priority}) as difference from `tabSales Order` WHERE status not in ('Completed', 'Draft', 'Cancelled') AND order_rank > 0 HAVING difference > 0 order by difference LIMIT 1;")[0][0] or 0
	self.db_set('order_rank', order_rank)

def ignore_permission(self):
	""" This function is use to ignore save permission while saving sales order """

	self.flags.ignore_permissions = True
	if not self.order_priority:
		self.order_priority = frappe.db.get_value("Customer", self.customer, 'customer_priority')
	if self._action == "update_after_submit":
		self.flags.ignore_validate_update_after_submit = True

def setting_real_qty(self):
	""" This function is use to set real qty on save """

	for item in self.items:
		if not item.real_qty:
			item.real_qty = item.qty

def calculate_order_priority(self):
	""" This function is use to calculate priority of order with logic """

	for item in self.items:
		try:
			days = ((datetime.date.today() - datetime.datetime.strptime(self.transaction_date, '%Y-%m-%d').date()) // datetime.timedelta(days = 1)) + 1
		except:
			days = ((datetime.date.today() - self.transaction_date) // datetime.timedelta(days = 1)) + 1
		days = 1 if days <= 0 else days
		base_factor = 4
		item.order_item_priority = cint((days * (base_factor ** (cint(self.order_priority) - 1))) + cint(self.order_priority))
	if self.items[0]:
		self.order_item_priority = self.items[0].order_item_priority

# def update_transaction_status(self):
# 	# old_list=['Cancelled', 'Closed', 'Completed']
# 	days = (datetime.date.today() - datetime.datetime.strptime(self.transaction_date, '%Y-%m-%d').date())
# 	frappe.msgprint(days)



def update_discounted_amount(self):
	""" This function is use to update discounted amonunt and net amount in sales order item """

	for item in self.items:
		item.discounted_rate = item.discounted_rate if item.discounted_rate else 0
		item.real_qty = item.real_qty if item.real_qty else 0

		item.discounted_amount = item.discounted_rate * flt(item.real_qty)
		item.discounted_net_amount = item.discounted_amount

# def update_discounted_net_total(self):
# 	""" This function is use to update discounted total amount in sales order """

# 	self.discounted_total = sum(x.discounted_amount for x in self.items)
# 	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
# 	testing_only_tax = 0
	
# 	for tax in self.taxes:
# 		if tax.testing_only:
# 			testing_only_tax += tax.tax_amount
	
# 	self.discounted_grand_total = self.discounted_net_total + self.total_taxes_and_charges - testing_only_tax
# 	self.discounted_rounded_total = round(self.discounted_grand_total)
# 	self.real_difference_amount = self.rounded_total - self.discounted_rounded_total

def check_qty_rate(self):
	""" Checking rate and qty is not 0 """
	pass

	# for item in self.items:
	# 	if not item.discounted_rate:
	# 		frappe.msgprint(f"Row {item.idx}: Discounted rate is 0, you will not be able to create invoice in {frappe.db.get_value('Company', self.company, 'alternate_company')}")
	# 	if not item.real_qty:
	# 		frappe.msgprint(f"Row {item.idx}: Real qty is 0, you will not be able to create invoice in {frappe.db.get_value('Company', self.company, 'alternate_company')}")

def checking_real_qty(self):
	""" This function will show alert on submit if real qty is 0 """

	alternate_company = frappe.db.get_value("Company", self.company, 'alternate_company')
	for item in self.items:
		if not item.real_qty:
			frappe.msgprint(_(f"Row {item.idx}:You will not be able to make invoice in company {alternate_company}."))

	
def before_validate_after_submit(self, method):
	setting_real_qty(self)
	calculate_order_priority(self)
	update_discounted_amount(self)
	update_idx(self)

def validate_after_submit(self, method):
	update_discounted_net_total(self)

def before_update_after_submit(self, method):
	setting_real_qty(self)
	calculate_order_priority(self)
	self.calculate_taxes_and_totals()
	update_discounted_amount(self)
	update_idx(self)
	update_discounted_net_total(self)
	update_order_rank(self)
	update_linked_order(self)

def on_update_after_submit(self, method):
	calculate_rate(self)
	delete_pick_list(self)
	update_sales_order_total_values(self)
	update_order_rank(self)
	update_item_series(self)

def update_item_series(self):
	for item in self.items:
		item_series = frappe.db.get_value("Item",item.item_code,"item_series")
		if item_series != item.item_series:
			frappe.db.set_value("Sales Order Item",item.name,"item_series",item_series)

#from ceramic.ceramic.doc_events.pick_list import unpick_qty_comment
def delete_pick_list(self):
	pick_list_list = frappe.get_list("Pick List Item", {'sales_order': self.name,'docstatus':1})
	for item in pick_list_list:
		pl = frappe.get_doc("Pick List Item", item.name)
		if not frappe.db.exists("Sales Order Item", pl.sales_order_item):
			user = frappe.get_doc("User",frappe.session.user)
			role_list = [r.role for r in user.roles]
			if frappe.db.get_value("Sales Order",self.name,'lock_picked_qty'):
				dispatch_person_user = frappe.db.get_value("Sales Person",frappe.db.get_value("Sales Order",self.name,'dispatch_person'),'user')
				if dispatch_person_user:
					if user.name != dispatch_person_user and 'Local Admin' not in role_list and 'Sales Head' not in role_list:
						frappe.throw("Only {} is allowed to unpick".format(dispatch_person_user))
			if pl.docstatus == 1:
				pl.cancel()
				unpick_qty_comment(pl.parent,self.name, f"Unpicked full Qty from item {pl.item_code}")
			pl.delete()

def unpick_qty_comment(reference_name, sales_order, data):
	comment_pl_doc = frappe.new_doc("Comment")
	comment_pl_doc.comment_type = "Updated"
	comment_pl_doc.comment_email = frappe.session.user
	comment_pl_doc.reference_doctype = "Pick List"
	comment_pl_doc.reference_name = reference_name

	comment_pl_doc.content = data

	comment_pl_doc.save()

	comment_so_doc = frappe.new_doc("Comment")
	comment_so_doc.comment_type = "Updated"
	comment_so_doc.comment_email = frappe.session.user
	comment_so_doc.reference_doctype = "Sales Order"
	comment_so_doc.reference_name = sales_order

	comment_so_doc.content = data

	comment_so_doc.save()

def before_cancel(self,method):
	# pass
	cancel_main_sales_order(self)

def on_cancel(self, method):
	remove_pick_list(self)
	update_sales_order_total_values(self)

def ignore_permission(self):
	""" This function is use to ignore save permission while saving sales order """

	self.flags.ignore_permissions = True
	if not self.order_priority:
		self.order_priority = frappe.db.get_value("Customer", self.customer, 'customer_priority')
	if self._action == "update_after_submit":
		self.flags.ignore_validate_update_after_submit = True

def checking_rate(self):
	""" This function is use to calculate rate is not 0 if status is apporved """

	if self.workflow_state == 'Approved':
		for row in self.items:
			if not row.rate:
				frappe.throw(_(f"Row {row.idx}: {row.item_code} Rate cannot be 0 in Approved Sales Order {self.name}."))

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

				for dn in frappe.get_all("Delivery Note Item", {'against_pick_list': doc.name}):
					dn_doc = frappe.get_doc("Delivery Note Item", dn.name)
					frappe.throw(dn_doc.name)

					dn_doc.db_set('against_pick_list', None)
					dn_doc.db_set('pl_detail', None)

				parent_doc.append(doc.parent)
				item.db_set('picked_qty', 0)

	for pl in frappe.get_all("Pick List", {'sales_order': self.name}):
		frappe.db.set_value("Pick List", pl.name, 'sales_order', None)

	for item in set(parent_doc):
		update_delivered_percent(frappe.get_doc("Pick List", item))

def update_idx(self):
	for idx, item in enumerate(self.items):
		item.idx = idx + 1

def update_sales_order_total_values(self):
	""" This function is use to change total value on submit and cancel of sales order, pick list and delivery note """
	
	if self.status == "Close":
		frappe.throw("Can not create pick list against close sales order.")
		
	qty = 0
	total_picked_qty = 0.0
	total_picked_weight = 0.0
	total_delivered_qty = 0.0
	total_wastage_qty = 0.0
	total_deliverd_weight = 0.0
	total_qty = 0.0
	total_real_qty = 0.0
	total_net_weight = 0.0


	for row in self.items:
		qty += row.qty
		row.db_set('picked_weight',flt(row.weight_per_unit * row.picked_qty))
		total_picked_qty += row.picked_qty
		total_picked_weight += row.picked_weight
		total_delivered_qty += row.delivered_qty
		total_wastage_qty += row.wastage_qty
		total_deliverd_weight += flt(row.weight_per_unit * row.delivered_qty)
		total_qty += row.qty
		total_real_qty += row.real_qty
		row.db_set('total_weight',flt(row.weight_per_unit * row.qty))
		total_net_weight += row.total_weight

	if qty:
		per_picked = (total_picked_qty / qty) * 100
	else:
		per_picked = 0

	self.db_set('total_qty', total_qty)
	self.db_set('total_real_qty', total_real_qty)
	self.db_set('total_net_weight', total_net_weight)
	self.db_set('per_picked', per_picked)
	self.db_set('total_picked_qty', flt(total_picked_qty))
	self.db_set('total_picked_weight', total_picked_weight)
	self.db_set('total_delivered_qty', total_delivered_qty)
	self.db_set('picked_to_be_delivered_qty', self.total_picked_qty - flt(total_delivered_qty - flt(total_wastage_qty)))
	self.db_set('picked_to_be_delivered_weight', flt(total_picked_weight) - total_deliverd_weight)

# All whitelisted method bellow

@frappe.whitelist()
def change_customer(customer, doc):
	""" This function is use to change customer on submited document """

	so = frappe.get_doc("Sales Order",doc)
	customer_data = get_party_details(customer, "Customer")

	so.db_set('customer', customer)
	so.db_set('title', customer)
	so.db_set('customer_name', frappe.db.get_value("Customer",customer,'customer_name'))
	so.db_set('order_priority', frappe.db.get_value("Customer",customer,'customer_priority'))	
	so.db_set('customer_address', customer_data['customer_address'])
	so.db_set('address_display', customer_data['address_display'])
	so.db_set('shipping_address_name', customer_data['shipping_address_name'])
	so.db_set('shipping_address', customer_data['shipping_address'])
	so.db_set('contact_person', customer_data['contact_person'])
	so.db_set('contact_display', customer_data['contact_display'])
	so.db_set('contact_email', customer_data['contact_email'])
	so.db_set('contact_mobile', customer_data['contact_mobile'])
	so.db_set('contact_phone', customer_data['contact_phone'])
	so.db_set('customer_group', customer_data['customer_group'])

	return "Customer Changed Successfully."

@frappe.whitelist()
def get_tax_template(tax_category, company, tax_paid=0):
	if not tax_category:
		frappe.throw("Please Select Tax Category")
	if frappe.db.exists("Sales Taxes and Charges Template",{'tax_paid':tax_paid,'tax_category':tax_category,'company':company}):
		return frappe.db.get_value("Sales Taxes and Charges Template",{'tax_paid':tax_paid,'tax_category':tax_category,'company':company},'name')

@frappe.whitelist()
def make_pick_list(source_name, target_doc=None):
	def update_item_quantity(source, target, source_parent):
		target.qty = flt(source.qty) - flt(source.picked_qty) - flt(source.delivered_without_pick)
		target.so_qty = flt(source.qty)
		target.so_real_qty = flt(source.real_qty)
		target.stock_qty = (flt(source.qty) - flt(source.picked_qty)) * flt(source.conversion_factor)
		target.picked_qty = source.picked_qty
		target.remaining_qty = target.so_qty - target.qty - target.picked_qty
		target.customer = source_parent.customer
		target.date = source_parent.transaction_date
		target.delivery_date = source.delivery_date
		target.so_picked_percent = source_parent.per_picked
		target.warehouse = None
		target.order_item_priority = source.order_item_priority
		target.so_delivered_without_pick = source.delivered_without_pick

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

	doc.purpose = 'Delivery'
	doc.set_item_locations()
	return doc

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	""" This function is use to make delivery note from create button replacing the original erpnext function """

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
			if frappe.db.get_value("Item", i.item_code, 'is_stock_item'):
				real_delivered_qty = i.real_qty - i.delivered_real_qty
				for j in frappe.get_all("Pick List Item", filters={"sales_order": source.name, "sales_order_item": i.name, "docstatus": 1}):
					pick_doc = frappe.get_doc("Pick List Item", j.name)
					
					warehouse_query = frappe.db.sql(f"""
					SELECT
						sle.warehouse
					FROM 
						`tabStock Ledger Entry` sle
					INNER JOIN
						`tabBatch` batch on sle.batch_no = batch.name
					WHERE
						sle.item_code = '{pick_doc.item_code}' AND
						batch.docstatus < 2 AND
						sle.batch_no = '{pick_doc.batch_no}'
					GROUP BY 
						warehouse having sum(sle.actual_qty) > 0
					ORDER BY 
						sum(sle.actual_qty) desc
					limit 1""")

					warehouse = None
					if warehouse_query:
						warehouse = warehouse_query[0][0]
					
					if real_delivered_qty <= 0:
						real_delivered_qty = 0
					
					if pick_doc.qty - pick_doc.delivered_qty:
						target.append('items',{
							'item_code': pick_doc.item_code,
							'qty': pick_doc.qty - pick_doc.delivered_qty,
							'real_qty': real_delivered_qty if i.qty != i.real_qty else pick_doc.qty - pick_doc.delivered_qty,
							'rate': i.rate,
							'discounted_rate': i.discounted_rate,
							'against_sales_order': source.name,
							'so_detail': i.name,
							'against_pick_list': pick_doc.parent,
							'pl_detail': pick_doc.name,
							'warehouse': warehouse,
							'batch_no': pick_doc.batch_no,
							'lot_no': pick_doc.lot_no,
							'item_series': i.item_series,
							'picked_qty': pick_doc.qty - pick_doc.delivered_qty
						})

						real_delivered_qty = 0
			else:
				target.append('items',{
					'item_code': i.item_code,
					'qty': i.qty - i.delivered_qty,
					'real_qty': i.qty - i.delivered_real_qty if i.qty != i.real_qty else i.qty - i.delivered_qty,
					'rate': i.rate,
					'discounted_rate': i.discounted_rate,
					'against_sales_order': source.name,
					'so_detail': i.name,
					'warehouse': i.warehouse,
					'item_series': i.item_series,
					'batch_no': ''
				})
			
		target_items = []
		target_item_dict = {}

		if not target.get('items'):
			target.items = []

		for i in target.items:
			if not target_item_dict.get(i.so_detail):
				target_item_dict[i.so_detail] = 0
			
			target_item_dict[i.so_detail] += i.qty

		
		for i in source.items:
			if target_item_dict.get(i.name):
				if i.qty > target_item_dict.get(i.name):
					target.append('items',{
					'item_code': i.item_code,
					'qty': i.qty - i.delivered_qty - target_item_dict[i.name],
					'real_qty': i.qty - i.delivered_real_qty if i.qty != i.real_qty else i.qty - i.delivered_qty - target_item_dict[i.name],
					'rate': i.rate,
					'discounted_rate': i.discounted_rate,
					'against_sales_order': source.name,
					'so_detail': i.name,
					'warehouse': i.warehouse,
					'item_series': i.item_series,
					'batch_no': ''
				})
			else:
				target.append('items',{
					'item_code': i.item_code,
					'qty': i.qty - i.delivered_qty,
					'real_qty': i.qty - i.delivered_real_qty,
					'rate': i.rate,
					'discounted_rate': i.discounted_rate,
					'against_sales_order': source.name,
					'so_detail': i.name,
					'warehouse': i.warehouse,
					'item_series': i.item_series,
					'batch_no': ''
				})
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

# shedule function
def schedule_daily():
	calculate_order_item_priority()
	calculate_order_rank()
	set_transaction_status()
	cancel_on_sales_status()

def set_transaction_status():
	frappe.db.sql(f"update `tabSales Order` set transaction_status = 'Old' WHERE status in ('Cancelled', 'Closed', 'Completed') AND transaction_status != 'Old' AND modified < '{datetime.datetime.today()-datetime.timedelta(7)}'")
	frappe.db.sql(f"update `tabSales Order` set transaction_status = 'New' WHERE status in ('Cancelled', 'Closed', 'Completed') AND transaction_status != 'New' AND modified >= '{datetime.datetime.today()-datetime.timedelta(7)}'")

	frappe.db.sql(f"update `tabDelivery Note` set transaction_status = 'Old' WHERE transaction_status != 'Old' AND modified < '{datetime.datetime.today()-datetime.timedelta(7)}'")
	frappe.db.sql(f"update `tabDelivery Note` set transaction_status = 'New' WHERE transaction_status != 'New' AND modified >= '{datetime.datetime.today()-datetime.timedelta(7)}'")

	frappe.db.commit()

def calculate_order_item_priority():
	data = frappe.db.sql(f"""
		SELECT
			soi.`name`, so.`transaction_date`, so.`order_priority`
		FROM
			`tabSales Order Item` as soi JOIN `tabSales Order` as so ON so.`name` = soi.`parent`
		WHERE
			soi.`qty` > soi.`delivered_qty` AND
			so.`docstatus` = 1
			AND so.status not in ('Completed', 'Stopped', 'Hold', 'Closed')
	""", as_dict = 1)

	for soi in data:
		days = ((datetime.date.today() - soi.transaction_date) // datetime.timedelta(1)) + 1
		base_factor = 4
		order_item_priority = cint((days * (base_factor ** (cint(soi.order_priority) - 1))) + cint(soi.order_priority))

		frappe.db.set_value("Sales Order Item", soi.name, 'order_item_priority', order_item_priority, update_modified = True)

	frappe.db.commit()

def calculate_order_rank():
	companies_list = frappe.get_list("Company", {'authority': 'Unauthorized'})

	
	data = frappe.db.sql(f"""
		SELECT
			so.name as so_name From `tabSales Order` as so
		WHERE
			so.`per_delivered` < 100 AND
			so.`docstatus` = 1
			AND so.status not in ('Completed', 'Stopped', 'Hold', 'Closed')
	""", as_dict = 1)

	for soi in data:
		doc = frappe.get_doc("Sales Order", soi.so_name)
		doc.db_set('order_item_priority', doc.items[0].order_item_priority, update_modified = False)
	
	for i in companies_list:
		print(i.name)
		priority = frappe.db.sql(f"""
			select 
				name, row_number() over(order by order_item_priority desc, transaction_date desc) as rank
			from
				`tabSales Order` 
			WHERE
				docstatus = 1 and 
				status not in ('Closed', 'Stoped', 'Completed', 'Hold') and 
				per_delivered < 100 
				AND company = '{i.name}'
			order by 
				order_item_priority desc
		""", as_dict = True)

		for item in priority:
			print(item.name, item.rank)
			frappe.db.set_value("Sales Order", item.name, 'order_rank', item.rank, update_modified = False)

	frappe.db.commit()

@frappe.whitelist()
def update_order_rank_(date, order_priority, company):
	try:
		days = ((datetime.date.today() - datetime.datetime.strptime(date, '%Y-%m-%d').date()) // datetime.timedelta(days = 1)) + 1
	except:
		days = ((datetime.date.today() - date) // datetime.timedelta(days = 1)) + 1
	days = 1 if days <= 0 else days
	base_factor = 4
	order_item_priority = cint((days * (base_factor ** (cint(order_priority) - 1))) + cint(order_priority))

	order_rank_tuple = frappe.db.sql(f"""
	select 
		order_rank, ABS(order_item_priority - {order_item_priority}) as difference
	from
		`tabSales Order` 
	WHERE
		status not in ('Completed', 'Draft', 'Cancelled', 'Hold') 
		AND order_rank > 0
		AND company = '{company}'
	HAVING
		difference > 0 
	ORDER BY
		difference LIMIT 1
	""")
	if order_rank_tuple:
		order_rank = order_rank_tuple[0][0] or 0
	else:
		order_rank = 0

	return {'order_item_priority': order_item_priority, 'order_rank': order_rank}

@frappe.whitelist()
def get_rate_discounted_rate(item_code, customer, company, so_number = None):
	""" This function is use to get discounted rate and rate """
	# item_group, tile_quality = frappe.get_value("Item", item_code, ['item_group', 'tile_quality'])
	# parent_item_group = frappe.get_value("Item Group", item_group, 'parent_item_group')

	# count = frappe.db.sql(f"""
	# 	SELECT 
	# 		COUNT(*) 
	# 	FROM 
	# 		`tabSales Order Item` as soi 
	# 	JOIN 
	# 		`tabSales Order` as so ON so.`name` = soi.`parent`
	# 	WHERE 
	# 		soi.`item_group` = '{item_group}' AND
	# 		soi.`docstatus` = 1 AND
	# 		so.customer = '{customer}' AND
	# 		soi.`tile_quality` = '{tile_quality}' AND
	# 		so.`company` = '{company}'
	# 	LIMIT 1
	# """)

	# if count[0][0]:
	# 	where_clause = f"soi.item_group = '{item_group}' AND"
	# else:
	# 	where_clause = f"soi.parent_item_group = '{parent_item_group}' AND"
	# data = None

	# if so_number:
	# 	data = frappe.db.sql(f"""
	# 		SELECT 
	# 			soi.`rate` as `rate`, soi.`discounted_rate` as `discounted_rate`
	# 		FROM 
	# 			`tabSales Order Item` as soi 
	# 		JOIN
	# 			`tabSales Order` as so ON soi.parent = so.name
	# 		WHERE
	# 			{where_clause}
	# 			soi.`tile_quality` = '{tile_quality}' AND
	# 			so.`customer` = '{customer}' AND
	# 			so.`company` = '{company}' AND
	# 			so.`docstatus` != 2 AND
	# 			so.`name` = '{so_number}'
	# 		ORDER BY
	# 			soi.`creation` DESC
	# 		LIMIT 
	# 			1
	# 	""", as_dict = True)

	# if not data:
	# 	data = frappe.db.sql(f"""
	# 		SELECT 
	# 			soi.`rate` as `rate`, soi.`discounted_rate` as `discounted_rate`
	# 		FROM 
	# 			`tabSales Order Item` as soi JOIN
	# 			`tabSales Order` as so ON soi.parent = so.name
	# 		WHERE
	# 			{where_clause}
	# 			soi.`tile_quality` = '{tile_quality}' AND
	# 			so.`customer` = '{customer}' AND
	# 			so.`company` = '{company}' AND
	# 			so.`docstatus` != 2
	# 		ORDER BY
	# 			soi.`creation` DESC
	# 		LIMIT 
	# 			1
	# 	""", as_dict = True)

	# return data[0] if data else {'rate': 0, 'discounted_rate': 0}
	pass

			
def calculate_rate(self):
	for row in self.items:
		if row.sqf_rate:
			row.rate = flt(row.sqf_rate*15.5)