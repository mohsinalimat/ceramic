# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc

class CombineBatch(Document):
	def on_submit(self):
		if self.from_item_code != self.to_item_code:
			frappe.throw(_("Not allowed to combine batch with different item"))
		if self.from_batch == self.to_batch:
			frappe.throw(_("Please select another batch to rename."))
		try:
			rename_doc("Batch", self.from_batch, self.to_batch, merge=True, ignore_permissions=True)
			frappe.db.sql("""
					 update `tabStock Ledger Entry` set batch_no = %s where batch_no = %s;
					""",(self.to_batch,self.from_batch))
		except Exception as e:
					frappe.throw(str(e))

	def on_cancel(self):
		frappe.throw(_("Not allowed to cancel the document"))