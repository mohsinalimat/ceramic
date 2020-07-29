# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class PaymentFollowupRemarks(Document):
	def validate(self):
		self.set_route()
	
	def set_route(self):
		'''Set route from category and title if missing'''
		if self.get('route_redirect'):
			self.route = '#query-report/Accounts Receivable Primary Customer'
