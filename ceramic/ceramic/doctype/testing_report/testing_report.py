# -*- coding: utf-8 -*-
# Copyright (c) 2021, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TestingReport(Document):
	
	def validate(self):
		for report in self.reports:
			doc = frappe.get_doc("Report",report.report)
			frappe.db.sql("delete from `tabHas Role` where parent = %s ",doc.name)
			doc.append("roles",{
				'role': 'System Manager'
			})
			doc.save(ignore_permissions=True)