# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccountReco(Document):
	def on_submit(self):
		frappe.db.sql("""update `tabGL Entry` SET transaction_status = 'Old' where name!='a'
			and company = '{company}' and account = '{account}' and party_type = '{party_type}'
			and party = '{party}' and posting_date <= '{posting_date}'
			""".format(company=self.company, account=self.account, party_type=self.party_type, \
					party=self.party, posting_date=self.posting_date))
	
		data = frappe.db.sql("""select voucher_type,voucher_no from `tabGL Entry` where name!='a'
			and company = '{company}' and account = '{account}' and party_type = '{party_type}'
			and party = '{party}' and posting_date <= '{posting_date}'
			""".format(company=self.company, account=self.account, party_type=self.party_type, \
					party=self.party, posting_date=self.posting_date),as_dict=1)

		if data:
			for row in data:
				frappe.db.sql("""update `tab{voucher_type}` SET transaction_status='Old' where name = '{voucher_no}'
				""".format(voucher_type = row.voucher_type,voucher_no = row.voucher_no))
		
		if self.party_type == "Customer":
			doc = frappe.get_doc("Customer",self.party)
			if doc.sales_team:
				for sales in doc.sales_team:
					if sales.company == self.company:
						sales.db_set('account_reco_date', self.posting_date)
						sales.db_set('reconciled_amount', self.reconciled_amount)
						sales.db_update()

	def on_cancel(self):
		frappe.db.sql("""update `tabGL Entry` SET transaction_status = 'New' where name!='a'
			and company = '{company}' and account = '{account}' and party_type = '{party_type}'
			and party = '{party}' and posting_date <= '{posting_date}'
			""".format(company=self.company, account=self.account, party_type=self.party_type, \
					party=self.party, posting_date=self.posting_date))		

		data = frappe.db.sql("""select voucher_type,voucher_no from `tabGL Entry` where name!='a'
			and company = '{company}' and account = '{account}' and party_type = '{party_type}'
			and party = '{party}' and posting_date <= '{posting_date}'
			""".format(company=self.company, account=self.account, party_type=self.party_type, \
					party=self.party, posting_date=self.posting_date),as_dict=1)

		if data:
			for row in data:
				frappe.db.sql("""update `tab{voucher_type}` SET transaction_status='New' where name = '{voucher_no}'
				""".format(voucher_type = row.voucher_type,voucher_no = row.voucher_no))

		if self.party_type == "Customer":
			doc = frappe.get_doc("Customer",self.party)
			if doc.sales_team:
				for sales in doc.sales_team:
					if sales.company == self.company:
						if sales.account_reco_date == self.posting_date:
							sales.db_set('account_reco_date', None)
						if sales.reconciled_amount == self.reconciled_amount:
							sales.db_set('reconciled_amount', 0)
						sales.db_update()