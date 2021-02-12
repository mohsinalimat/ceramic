# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Sample"),
			"items": [
				{
					"type": "doctype",
					"name": "Item",
				},
				{
					"type": "doctype",
					"name": "Customer",
				},
				{
					"type": "doctype",
					"name": "Lead",
				}
			]
		},
		{
			"label": _("RSM"),
			"items": [
				{
					"type": "doctype",
					"name": "Sales Order",
				},
				{
					"type": "report",
					"name": "Sales Person Accounts Receivable",
					"doctype":"Sales Invoice",
					"is_query_report": True
				},
			]
		},			
	]