# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and Contributors
# See license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
import unittest

class TestTileItemCreationTool(unittest.TestCase):
	pass
	# def before_save(self):
	# 	self.create_items()

	# def create_items(self):
	# 	categories = ['Premium','Golden','Economy','Classic']
	# 	frappe.msgprint("function called")
	# 	for category in categories:
	# 		if category != self.item_series[-1]:
	# 			item = frappe.new_doc("Item")
	# 			new_item_name = self.item_series.replace(self.item_series[-1],category)
	# 			item.item_name = new_item_name
	# 			item.item_group = self.item_group
	# 			item.tile_size = self.tile_size
	# 			item.tile_surface = self.tile_surface
	# 			item.stock_uom = self.uom
		
	# 		try:
	# 			item.save(ignore_permissions=True)
	# 			item.submit()

	# 		except Exception as e:
	# 			frappe.throw(str(e))