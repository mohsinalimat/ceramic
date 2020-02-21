# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, flt, cint
from erpnext.stock.utils import get_incoming_rate
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center, get_conversion_factor, get_reserved_qty_for_so
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from six import string_types
from datetime import datetime
from erpnext.stock.stock_ledger import get_valuation_rate

class WorkOrderFinish(Document):

	def before_save(self):
		self.get_required_items()
		self.set_valuation_rate()

	def on_submit(self):
		self.create_stock_entry()

	def on_cancel(self):
		self.cancel_stock_entry()
		
	def get_required_items(self):
		bom = frappe.get_doc("BOM",self.from_bom)
		self.required_items = []
		for row in bom.items:
			self.append('required_items',{
				'item_code': row.item_code,
				'qty': (flt(self.total_qty)*flt(row.qty))/bom.quantity,
				'uom': row.uom,
			})
		self.set_incoming_rate()


	def set_incoming_rate(self):
		amount = 0
		for d in self.required_items:
			if self.source_warehouse:
				args = self.get_args_for_incoming_rate(d)
				d.rate = get_incoming_rate(args)
			elif not self.source_warehouse:
				d.rate = 0.0
			elif self.target_warehouse and not d.rate:
				d.rate = get_valuation_rate(d.item_code, self.target_warehouse,
					self.doctype, d.name, 1,
					currency=erpnext.get_company_currency(self.company))
			
			d.amount = d.rate * d.qty
			amount += d.amount

		self.total_outgoing_value = amount
	
	def get_args_for_incoming_rate(self, item):
		warehouse = self.source_warehouse
		return frappe._dict({
			"item_code": item.item_code,
			"warehouse": warehouse,
			"posting_date": self.posting_date,
			"qty": item.qty,
			"posting_time": self.posting_time or nowtime(),
			"voucher_type": self.doctype,
			"voucher_no": item.name,
			"company": self.company,
			"allow_zero_valuation": 1
		})

	def set_valuation_rate(self):
		for row in self.items:
			row.basic_rate = flt(self.total_outgoing_value)/ flt(self.total_qty)
			row.basic_amount = flt(row.basic_rate)* flt(row.qty)
			row.additional_cost = (flt(self.total_additional_cost) / flt(self.total_qty)) * row.qty
			row.amount = row.basic_amount + row.additional_cost
			row.valuation_rate = row.amount * row.qty

	def create_stock_entry(self):	
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Manufacture"
		se.purpose = "Manufacture"
		se.work_order = self.work_order
		se.bom_no = self.from_bom
		se.set_posting_time = 1
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.reference_doctype = self.doctype
		se.reference_docname = self.name
		se.from_bom = 1
		se.company = self.company
		se.fg_completed_qty = self.total_qty
		se.from_warehouse = self.source_warehouse
		
		if self.required_items:
			for row in self.required_items:
				se.append("items",{
					'item_code': row.item_code,
					's_warehouse': self.source_warehouse,
					'qty': row.qty,
					'basic_rate': row.rate,
					'basic_amount': row.amount,
					'batch_no': row.batch_no
				})

		if self.items:
			for row in self.items:
				se.append("items",{
					'item_code': row.item_code,
					't_warehouse': self.target_warehouse,
					'qty': row.qty,
					'basic_rate': row.basic_rate,
					'basic_amount': row.basic_amount,
					'additional_cost': row.additional_cost,
					'amount': row.amount,
					'valuation_rate': row.valuation_rate
				})

		if self.additional_cost:
			for row in self.additional_cost:
				se.append("additional_costs",{
					'description': row.description,
					'amount': row.amount
				})
		try:
			se.save(ignore_permissions=True)
			se.submit()
		except Exception as e:
			raise e

	def cancel_stock_entry(self):
		se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
		se.flags.ignore_permissions = True
		try:
			se.cancel()
		except Exception as e:
			raise e
		
		se.db_set('reference_doctype','')
		se.db_set('reference_docname','')

	def get_item_details(self, args=None, for_update=False):
		item = frappe.db.sql("""select i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
				i.has_batch_no, i.sample_quantity, i.has_serial_no,
				id.expense_account, id.buying_cost_center
			from `tabItem` i LEFT JOIN `tabItem Default` id ON i.name=id.parent and id.company=%s
			where i.name=%s
				and i.disabled=0
				and (i.end_of_life is null or i.end_of_life='0000-00-00' or i.end_of_life > %s)""",
			(self.company, args.get('item_code'), nowdate()), as_dict = 1)

		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))

		item = item[0]
		item_group_defaults = get_item_group_defaults(item.name, self.company)
		brand_defaults = get_brand_defaults(item.name, self.company)

		ret = frappe._dict({
			'uom'			      	: item.stock_uom,
			'stock_uom'				: item.stock_uom,
			'description'		  	: item.description,
			'image'					: item.image,
			'item_name' 		  	: item.item_name,
			'cost_center'			: get_default_cost_center(args, item, item_group_defaults, brand_defaults, self.company),
			'qty'					: args.get("qty"),
			'transfer_qty'			: args.get('qty'),
			'conversion_factor'		: 1,
			'batch_no'				: '',
			'actual_qty'			: 0,
			'basic_rate'			: 0,
			'serial_no'				: '',
			'has_serial_no'			: item.has_serial_no,
			'has_batch_no'			: item.has_batch_no,
			'sample_quantity'		: item.sample_quantity
		})

		# update uom
		if args.get("uom") and for_update:
			ret.update(get_uom_details(args.get('item_code'), args.get('uom'), args.get('qty')))

		ret["expense_account"] = (item.get("expense_account") or
			item_group_defaults.get("expense_account") or
			frappe.get_cached_value('Company',  self.company,  "default_expense_account"))

		for company_field, field in {'stock_adjustment_account': 'expense_account',
			'cost_center': 'cost_center'}.items():
			if not ret.get(field):
				ret[field] = frappe.get_cached_value('Company',  self.company,  company_field)

		args['posting_date'] = self.posting_date
		args['posting_time'] = self.posting_time

		stock_and_rate = get_warehouse_details(args) if args.get('warehouse') else {}
		ret.update(stock_and_rate)

		# automatically select batch for outgoing item
		# if (args.get('s_warehouse', None) and args.get('qty') and
			# ret.get('has_batch_no') and not args.get('batch_no')):
			# args.batch_no = get_batch_no(args['item_code'], args['s_warehouse'], args['qty'])

		return ret