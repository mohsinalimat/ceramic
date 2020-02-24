# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TileItemCreationTool(Document):

	def on_submit(self):
		self.create_items()
	
	def create_items(self):
		# Last changed
		categories = ['Premium','Golden','Economy','Classic']
		for category in categories:
			item = frappe.new_doc("Item")
			item.item_group = self.item_group
			item.tile_size = self.tile_size
			item.tile_surface = self.tile_surface
			item.stock_uom = self.uom
			item.item_code = self.item_name + "-" + category
			#item.item_code = self.item_name + "-" + self.tile_surface or '' + "-" + self.tile_size or '' + "-" + category
			if self.item_series:
				each_series = self.item_series.replace(self.item_series.split("-")[-1], category)
				item.item_series = each_series
			# frappe.msgprint(each_series)
			if self.maintain_stock == True:
				item.has_batch_no = True
				item.create_new_batch = True
				item.batch_number_series = "BTH-.posting_date.-.###"
				# frappe.msgprint(item.item_series)
			try:
				item.save(ignore_permissions=True)

			except Exception as e:
				frappe.throw(str(e))
