# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt, cint
from erpnext.accounts.party import get_partywise_advanced_payment_amount
from ceramic.ceramic.report.accounts_receivable_ceramic.accounts_receivable_ceramic import ReceivablePayableReport
from six import iteritems

def execute(filters=None):
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}

	return AccountsReceivableSummary(filters).run(args)

class AccountsReceivableSummary(ReceivablePayableReport):
	def run(self, args):
		self.party_type = args.get('party_type')
		self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
		self.get_columns()
		self.get_data(args)
		return self.columns, self.data

	def get_data(self, args):
		self.data = []

		self.receivables = ReceivablePayableReport(self.filters).run(args)[1]

		self.get_party_total(args)

		party_advance_amount = get_partywise_advanced_payment_amount(self.party_type,
			self.filters.report_date, self.filters.company) or {}

		for party, party_dict in iteritems(self.party_total):
			if party_dict.outstanding == 0:
				continue

			row = frappe._dict()

			# row.party = party
			# row.primary_customer = primary_customer
			# row.primary_customer = frappe.db.get_value("Customer", row.party, 'primary_customer')
			if self.party_naming_by == "Naming Series":
				row.party_name = frappe.get_cached_value(self.party_type, party, scrub(self.party_type) + "_name")

			row.update(party_dict)
			
			# Advance against party
			row.advance = party_advance_amount.get(party, 0)

			# In AR/AP, advance shown in paid columns,
			# but in summary report advance shown in separate column
			row.paid -= row.advance
			
			self.data.append(row)
			self.data = sorted(self.data, key = lambda i: (i['primary_customer'], i['party'])) 

	def get_party_total(self, args):
		self.party_total = frappe._dict()

		for d in self.receivables:
			self.init_party_total(d)

			# Add all amount columns
			for k in list(self.party_total[d.party+(d.primary_customer or '')]):
				if k not in ["currency", "sales_person", "party", "primary_customer"]:

					self.party_total[d.party+(d.primary_customer or '')][k] += d.get(k, 0.0)

			# set territory, customer_group, sales person etc
			self.set_party_details(d)

	def init_party_total(self, row):
		self.party_total.setdefault(row.party+(row.primary_customer or ''), frappe._dict({
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
		self.party_total[row.party+(row.primary_customer or '')].currency = row.currency

		for key in ('territory', 'customer_group', 'supplier_group'):
			if row.get(key):
				self.party_total[row.party+(row.primary_customer or '')][key] = row.get(key)

		if row.sales_person:
			self.party_total[row.party+(row.primary_customer or '')].sales_person.append(row.sales_person)

	def get_columns(self):
		self.columns = []
		self.add_column(label=_(self.party_type), fieldname='party',
			fieldtype='Link', options=self.party_type, width=180)
		self.add_column(_('Primary Customer'), fieldname='primary_customer', fieldtype='Data')
		self.add_column(_('Billed Amount'), fieldname='billed_amount')
		self.add_column(_('Cash Amount'), fieldname='cash_amount')
		self.add_column(_('Invoiced Amount'), fieldname='invoiced')
		# if self.party_type == "Customer":
		# 	self.add_column(_('Credit Note'), fieldname='credit_note')
		# else:
		# 	# note: fieldname is still `credit_note`
		# 	self.add_column(_('Debit Note'), fieldname='credit_note')
		self.add_column(_('Bank Paid Amount'), fieldname='bank_paid')
		self.add_column(_('Cash Paid Amount'), fieldname='cash_paid')
		self.add_column(_('Total Paid Amount'), fieldname='paid')
		self.add_column(_('Bank Outstanding Amoun'), fieldname='bank_outstanding')
		self.add_column(_('Cash Outstanding Amount'), fieldname='cash_outstanding')
		self.add_column(_('Total Outstanding Amount'), fieldname='outstanding')

		if self.party_naming_by == "Naming Series":
			self.add_column(_('{0} Name').format(self.party_type),
				fieldname = 'party_name', fieldtype='Data')

		credit_debit_label = "Credit Note" if self.party_type == 'Customer' else "Debit Note"

		# self.add_column(_(credit_debit_label), fieldname='credit_note')

		self.setup_ageing_columns()

		if self.party_type == "Customer":
			self.add_column(label=_('Territory'), fieldname='territory', fieldtype='Link',
				options='Territory')
			self.add_column(label=_('Customer Group'), fieldname='customer_group', fieldtype='Link',
				options='Customer Group')
			if self.filters.show_sales_person:
				self.add_column(label=_('Sales Person'), fieldname='sales_person', fieldtype='Data')
		else:
			self.add_column(label=_('Supplier Group'), fieldname='supplier_group', fieldtype='Link',
				options='Supplier Group')

		self.add_column(label=_('Currency'), fieldname='currency', fieldtype='Link',
			options='Currency', width=80)

	def setup_ageing_columns(self):
		for i, label in enumerate(["0-{range1}".format(range1=self.filters["range1"]),
			"{range1}-{range2}".format(range1=cint(self.filters["range1"])+ 1, range2=self.filters["range2"]),
			"{range2}-{range3}".format(range2=cint(self.filters["range2"])+ 1, range3=self.filters["range3"]),
			"{range3}-{range4}".format(range3=cint(self.filters["range3"])+ 1, range4=self.filters["range4"]),
			"{range4}-{above}".format(range4=cint(self.filters["range4"])+ 1, above=_("Above"))]):
				self.add_column(label=label, fieldname='range' + str(i+1))