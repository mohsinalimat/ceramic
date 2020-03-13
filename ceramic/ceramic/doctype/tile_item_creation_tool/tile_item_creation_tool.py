# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TileItemCreationTool(Document):

	def on_cancel(self):
		frappe.throw("You Can not cancel Item")

	def on_submit(self):
		self.create_items()
	
	def create_items(self):
		categories = [item.tile_quality for item in self.tile_quality]

		tile_size_code = '-' + frappe.db.get_value('Tile Size', self.tile_size, 'size_code')
		tile_type_code = '-' + frappe.db.get_value('Tile Type', self.tile_type, 'type_code')
		tile_surface_code = '-' + frappe.db.get_value('Tile Surface', self.tile_surface, 'surface_code')

		if self.item_series:
			for tile in self.tile_quality:
				category = '-' + tile.tile_quality
				tile_grade = '-' + frappe.db.get_value("Tile Quality", tile.tile_quality, 'tile_grade')
				
				item = frappe.new_doc("Item")
				item.item_code = self.item_design + tile_grade + tile_surface_code + tile_type_code + tile_size_code
				item.item_name = self.item_name + category
				item.item_series = self.item_series
				item.item_creation_tool = self.name
				item.item_group = self.item_group
				item.stock_uom = self.uom

				item.is_tile = 1
				item.tile_body_composition = self.tile_body_composition
				item.tile_use = self.tile_use
				item.tile_size = self.tile_size
				item.tile_type = self.tile_type
				item.tile_surface = self.tile_surface
				item.tile_texture = self.tile_texture
				item.tile_technical = self.tile_technical
				item.tile_color = self.tile_color
				item.tile_shape = self.tile_shape
				item.tile_price = self.tile_price
				item.tile_thickness = self.tile_thickness
				item.tile_anti_slip_properties = self.tile_anti_slip_properties
				item.tile_quality = tile.tile_quality
				item.cover_image = self.cover_image
				item.image = self.image

				if self.show_in_website:
					if frappe.db.get_value("Tile Quality", tile.tile_quality, 'show_in_website'):
						item.show_in_website = self.show_in_website
						item.weightage = self.weightage
						item.website_image = self.website_image
						item.website_warehouse = self.website_warehouse

				if not self.is_item_series and self.maintain_stock == True:
					item.has_batch_no = True
					item.create_new_batch = True
					item.batch_number_series = "BTH-.YY.MM.DD.-.###"

				tile.db_set('item', item.item_code)
				item.item_defaults = self.item_defaults
				item.save(ignore_permissions=True)
		else:
			item = frappe.new_doc("Item")
			item.item_name = self.item_name
			item.item_creation_tool = self.name
			item.item_group = self.item_group
			item.stock_uom = self.uom

			item.is_tile = 1
			item.tile_body_composition = self.tile_body_composition
			item.tile_use = self.tile_use
			item.tile_size = self.tile_size
			item.tile_type = self.tile_type
			item.tile_surface = self.tile_surface
			item.tile_texture = self.tile_texture
			item.tile_technical = self.tile_technical
			item.tile_color = self.tile_color
			item.tile_shape = self.tile_shape
			item.tile_price = self.tile_price
			item.tile_thickness = self.tile_thickness
			item.tile_anti_slip_properties = self.tile_anti_slip_properties
			item.tile_quality = tile.tile_quality

@frappe.whitelist()
def get_tile_quality():
	return [item.name for item in frappe.get_all('Tile Quality')]
