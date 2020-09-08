# Copyright (c) 2020, Finbyz Tech Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from six import iteritems
import json

import frappe
from frappe import _, scrub
from frappe.utils import flt, cint

from ceramic.ceramic.report.accounts_receivable_ceramic.accounts_receivable_ceramic import ReceivablePayableReport


def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivablePrimaryCustomer(filters).run(args)


class AccountsReceivablePrimaryCustomer(ReceivablePayableReport):
	def run(self, args):
		self.party_type = args.get('party_type')
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		self.get_columns()
		self.get_data(args)
		
		return self.columns, self.data

	def get_data(self, args):
		filter_company = self.filters.company[0] if self.filters.company else None

		self.data = []
		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]
		self.get_party_total(args)

		for party, party_dict in iteritems(self.party_total):
			if party_dict.outstanding == 0 and party_dict.bank_outstanding == 0 and party_dict.cash_outstanding ==0:
				continue

			row = frappe._dict()

			if self.party_naming_by == "Naming Series":
				row.party_name = frappe.get_cached_value(self.party_type, party, scrub(self.party_type) + "_name")

			row.update(party_dict)
			
			self.data.append(row)
			self.data = sorted(self.data, key = lambda i: (i['primary_customer'], i['party']))
		
		remark_map_data = self.remark_map()

		for row in self.data:
			filters = json.dumps({
				'primary_customer': row.primary_customer,
				'from_date': self.filters.get('from_date'),
				'to_date': self.filters.get('to_date'),
				'customer': self.filters.get('customer'),
				'company': self.filters.get('company'),
				'range1': self.filters.get('range1'),
				'range2': self.filters.get('range2'),
				'range3': self.filters.get('range3'),
				'range4': self.filters.get('range4'),
			})

			row.view_receivable = f"""<a style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
			type='button' target='_blank' primary-customer='{row.primary_customer}' company='{filter_company}' 
			onClick=view_receivable_report(this.getAttribute('primary-customer'),this.getAttribute('company'))>View Receivable</a>"""

			row.add_remark = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
			type='button' primary-customer='{row.primary_customer}'
			onClick=new_remark(this.getAttribute('primary-customer'))>Add Remark</button>"""

			row.view_remark = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
			type='button' primary-customer='{row.primary_customer}'
			onClick=view_remark(this.getAttribute('primary-customer'))>View Remark</button>"""

			row.view_details = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;' 
			type='button' filters='{filters}'
			onClick='get_payment_remark_details(this.getAttribute("filters"))'>View Details</button>"""
			
			if remark_map_data.get(row.primary_customer):
				row.remark_date = remark_map_data[row.primary_customer].date
				row.remark = remark_map_data[row.primary_customer].remark
				row.follow_up_by = remark_map_data[row.primary_customer].follow_up_by
				row.next_follow_up_date = remark_map_data[row.primary_customer].next_follow_up_date
	
	def remark_map(self):
		data = frappe.db.sql("""SELECT DISTINCT customer, remark, next_follow_up_date, follow_up_by, date FROM `tabPayment Followup Remarks` ORDER BY date ASC""", as_dict = True)

		remark_map = {}

		for row in data:
			remark_map[row.customer] = row
		
		return remark_map

	def get_party_total(self, args):
		self.party_total = frappe._dict()

		for d in self.receivables:
			self.init_party_total(d)

			# Add all amount columns
			for k in list(self.party_total[d.primary_customer]):
				if k not in ["currency", "sales_person", "party", "primary_customer"]:

					self.party_total[d.primary_customer][k] += d.get(k, 0.0)

			# set territory, customer_group, sales person etc
			self.set_party_details(d)

	def init_party_total(self, row):
		self.party_total.setdefault(row.primary_customer, frappe._dict({
			"party": row.party,
			"primary_customer": row.primary_customer or '',
			"invoiced": 0.0,
			"billed_amount": 0.0,
			"cash_amount": 0.0,
			"paid": 0.0,
			"cash_paid": 0.0,
			"bank_paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 0.0,
			"bank_outstanding": 0.0,
			"cash_outstanding": 0.0,
			"range1": 0.0,
			"range2": 0.0,
			"range3": 0.0,
			"range4": 0.0,
			"range5": 0.0,
			"sales_person": []
		}))

	def set_party_details(self, row):
		self.party_total[row.primary_customer].currency = row.currency

		for key in ('territory', 'customer_group', 'supplier_group'):
			if row.get(key):
				self.party_total[row.primary_customer][key] = row.get(key)

		if row.sales_person:
			self.party_total[row.primary_customer].sales_person.append(row.sales_person)

	def get_columns(self):
		self.columns = []
		self.add_column(_('Primary Customer'), fieldname='primary_customer', fieldtype='Data')
		self.add_column(_('Bank Outstanding Amoun'), fieldname='bank_outstanding')
		self.add_column(_('Cash Outstanding Amount'), fieldname='cash_outstanding')
		self.add_column(_('Total Outstanding Amount'), fieldname='outstanding')

		if self.party_naming_by == "Naming Series":
			self.add_column(_('{0} Name').format(self.party_type),
				fieldname = 'party_name', fieldtype='Data')

		credit_debit_label = "Credit Note" if self.party_type == 'Customer' else "Debit Note"

		self.setup_ageing_columns()

		self.add_column(label=_('Currency'), fieldname='currency', fieldtype='Link', options='Currency', width=80)
		self.add_column(label=_('Remark'), fieldname='remark', fieldtype='Small Text', width=100)
		self.add_column(label=_('Remark Date'), fieldname='remark_date', fieldtype='Date', width=100)
		self.add_column(label=_('Next Followup Date'), fieldname='next_follow_up_date', fieldtype='Date', width=100)
		self.add_column(label=_('Follow up By'), fieldname='follow_up_by', fieldtype='button', width=100)
		self.add_column(label=_('View Receivable'), fieldname='view_receivable', fieldtype='button', width=110)
		self.add_column(label=_('Add Remark'), fieldname='add_remark', fieldtype='button', width=100)
		self.add_column(label=_('View Remark'), fieldname='view_remark', fieldtype='button', width=100)
		self.add_column(label=_('View Details'), fieldname='view_details', fieldtype='button', width=100)

	def setup_ageing_columns(self):
		for i, label in enumerate(["0-{range1}".format(range1=self.filters["range1"]),
			"{range1}-{range2}".format(range1=cint(self.filters["range1"])+ 1, range2=self.filters["range2"]),
			"{range2}-{range3}".format(range2=cint(self.filters["range2"])+ 1, range3=self.filters["range3"]),
			"{range3}-{range4}".format(range3=cint(self.filters["range3"])+ 1, range4=self.filters["range4"]),
			"{range4}-{above}".format(range4=cint(self.filters["range4"])+ 1, above=_("Above"))]):
				self.add_column(label=label, fieldname='range' + str(i+1))