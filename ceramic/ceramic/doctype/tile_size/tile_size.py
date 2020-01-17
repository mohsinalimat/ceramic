# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class TileSize(Document):
	def before_naming(self):
		self.tile_size = str(self.length) + "x" + str(self.width)

		
