import frappe, erpnext, json
from frappe import _, scrub
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, comma_or, nowdate, getdate
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details #, get_negative_outstanding_invoices , get_orders_to_be_billed
from erpnext.setup.utils import get_exchange_rate
from erpnext.accounts.utils import update_reference_in_payment_entry
from erpnext.accounts.utils import reconcile_against_document,get_account_currency, get_held_invoices # ,get_outstanding_invoices
from erpnext.controllers.accounts_controller import AccountsController, get_supplier_block_status
from six import string_types, iteritems


def validate(self,method):
	if self.authority == "Unauthorized" and not self.pe_ref and self.mode_of_payment not in ['Shroff / Hawala', 'Cash']:
		frappe.throw(f"You can not select mode of payment other than Cash or Shroff / Hawala. for company {self.company}")
	get_sales_person(self)
	for item in self.references:
		if self.payment_type == "Pay":
			if item.reference_doctype == 'Purchase Invoice':
				item.ref_invoice = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pi_ref')
		
		if self.payment_type == "Receive":
			if item.reference_doctype == 'Sales Invoice':
				item.ref_invoice = frappe.db.get_value("Sales Invoice", item.reference_name, 'si_ref')
	
	if not self.primary_customer and self.party_type == "Customer":
		self.primary_customer = self.party

def on_update_after_submit(self, method):
	if self.pe_ref:
		frappe.db.set_value("Payment Entry", self.pe_ref, 'primary_customer', self.primary_customer)
	update_payment_entries(self)

	if self.authority == "Unauthorized":
		self.make_gl_entries(cancel=1)
		self.make_gl_entries(cancel=0)	
	
def update_payment_entries(self):
	authority = frappe.db.get_value("Company", self.company, 'authority')
	
	if authority == "Unauthorized" and not self.pe_ref:
		for item in self.references:
			if item.reference_doctype == "Sales Invoice":
				pay_amount_left = real_difference_amount = frappe.db.get_value("Sales Invoice", item.reference_name, 'real_difference_amount')
				allocated_amount = frappe.get_value("Payment Entry Reference", {'reference_name': item.reference_name, 'docstatus': 1}, "sum(allocated_amount)")
				diff_value = pay_amount_left - allocated_amount
				if diff_value > real_difference_amount:
					frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
				else:
					frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value)
			
			if item.reference_doctype == "Purchase Invoice":
				pay_amount_left = real_difference_amount = frappe.db.get_value("Purchase Invoice", item.reference_name, 'real_difference_amount')
				allocated_amount = frappe.get_value("Payment Entry Reference", {'reference_name': item.reference_name, 'docstatus': 1}, "sum(allocated_amount)")
				diff_value = pay_amount_left - allocated_amount
				
				if diff_value > real_difference_amount:
					frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
				else:
					frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value)


	if self.pe_ref and not self.get('dont_replicate'):
		payment_doc = frappe.get_doc("Payment Entry", self.pe_ref)
		payment_doc.dont_replicate = 1
		payment_doc.db_set('primary_customer',self.primary_customer)
		payment_doc_reference_list = [x.reference_name for x in payment_doc.references]

		for idx, row in enumerate(self.references):
			if row.reference_doctype != "Journal Entry" and self.paid_from_account_currency == 'INR' and self.paid_from_account_currency == 'INR':
				ref_field = "pi_ref" if row.reference_doctype == 'Purchase Invoice' else 'si_ref'
				row.against_voucher = frappe.db.get_value(row.reference_doctype, row.reference_name, ref_field)
				row.voucher_detail_no = None
				row.difference_amount = 0
				row.difference_account = None
				if row.against_voucher not in payment_doc_reference_list:
					row.against_voucher_type = row.reference_doctype
					row.grand_total = row.total_amount
					update_reference_in_payment_entry(row, payment_doc)
	


def on_submit(self, method):
	"""On Submit Custom Function for Payment Entry"""
	create_payment_entry(self)


def on_cancel(self, method):
	"""On Cancel Custom Function for Payment Entry"""
	cancel_payment_entry(self)
	validate_primary_customer_payment_entry(self)


def on_trash(self, method):
	"""On Delete Custom Function for Payment Entry"""
	delete_payment_entry(self)


def create_payment_entry(self):
	"""Function to create Payment Entry

	This function is use to create Payment Entry from 
	one company to another company if company is authorized.

	Args:
		self (obj): The submited payment entry object
	"""
	
	def get_payment_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.set_posting_time = 1
			target.pe_ref = source.name
			if target.payment_type == "Pay":
				if target.mode_of_payment:
					target.paid_from = get_bank_cash_account(target.mode_of_payment, target.company)['account']
				else:
					target.paid_from = source.paid_to.replace(source_company_abbr, target_company_abbr)
				party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
				
				target.paid_to = party_details['party_account']
				target.paid_to_account_currency = party_details['party_account_currency']
				target.paid_to_account_balance = party_details['account_balance']
			
			elif target.payment_type == "Receive":
				if target.mode_of_payment:
					target.paid_to = get_bank_cash_account(target.mode_of_payment, target.company)['account']
				else:
					target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
				party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
				target.paid_from = party_details['party_account']
				target.paid_from_account_currency = party_details['party_account_currency']
				target.paid_from_account_balance = party_details['account_balance']
			else:
				target.paid_from = source.paid_from.replace(source_company_abbr, target_company_abbr)
				target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
			
			if source.deductions:
				for index, i in enumerate(source.deductions):
					# target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					# target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
					source_cost_center = target.deductions[index].cost_center
					target_cost_center = source_cost_center.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center = target_cost_center

					source_account = target.deductions[index].account
					target_account = source_account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].account = target_account

			if self.amended_from:
				target.amended_from = frappe.db.get_value("Payment Entry", self.amended_from, "pe_ref")			

		def payment_ref(source_doc, target_doc, source_parent):
			reference_name = source_doc.reference_name
			if source_parent.payment_type == 'Pay':
				if source_doc.reference_doctype == 'Purchase Invoice':
					target_doc.reference_name = frappe.db.get_value("Purchase Invoice", reference_name, 'pi_ref')
					target_doc.total_amount = frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'rounded_total') or frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'total')
					target_doc.outstanding_amount = frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'outstanding_amount')
					target_doc.allocated_amount = min(target_doc.outstanding_amount - (frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'pay_amount_left')), source_doc.allocated_amount)

			if source_parent.payment_type == 'Receive':
				if source_doc.reference_doctype == 'Sales Invoice':
					target_doc.reference_name = frappe.db.get_value("Sales Invoice", reference_name, 'si_ref')
					target_doc.total_amount = frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'rounded_total') or frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'total')
					target_doc.outstanding_amount = frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'outstanding_amount')
					target_doc.allocated_amount = min(target_doc.outstanding_amount - (frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'pay_amount_left')), source_doc.allocated_amount)

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {
					'series_value': 'series_value'
				},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
					"pe_ref"
				},
			},
			"Payment Entry Reference": {
				"doctype": "Payment Entry Reference",
				"field_map": {},
				"field_no_map": {},
				"postprocess": payment_ref,
				"condition": lambda doc: doc.ref_invoice
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)
		
		return doclist
	
	# getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	if authority == "Authorized":
		pe = get_payment_entry(self.name)
		pe.naming_series = 'A' + str(self.company_series) + pe.naming_series
		pe.series_value = self.series_value
		pe.save(ignore_permissions= True)
		self.db_set('pe_ref', pe.name)
		pe.submit()
	
	if authority == "Unauthorized":
		if not self.pe_ref:
			for item in self.references:
				if item.reference_doctype == "Sales Invoice":
					diff_value = frappe.db.get_value("Sales Invoice", item.reference_name, 'pay_amount_left')

					if item.allocated_amount > diff_value:
						frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
					else:
						frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value - item.allocated_amount)
				
				if item.reference_doctype == "Purchase Invoice":
					diff_value = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pay_amount_left')

					if item.allocated_amount > diff_value:
						frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
					else:
						frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value - item.allocated_amount)


def validate_primary_customer_payment_entry(self):
	if self.reference_doctype == "Primary Customer Payment" and self.reference_docname and not self.get('cancel_it'):
		frappe.throw(_("Please cancel {0} before cancelling the payment entry".format(self.reference_docname)))

# Cancel Invoice on Cancel
def cancel_payment_entry(self):
	if self.pe_ref:
		pe = frappe.get_doc("Payment Entry", {'pe_ref':self.name})
	else:
		pe = None
	authority = frappe.get_value("Company", self.company, 'authority')
	if authority == "Unauthorized":
		if not self.pe_ref:
			for item in self.references:
				if item.reference_doctype == "Sales Invoice":
					diff_value = frappe.db.get_value("Sales Invoice", item.reference_name, 'pay_amount_left')

					frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value + item.allocated_amount)
				
				if item.reference_doctype == "Purchase Invoice":
					diff_value = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pay_amount_left')

					frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value + item.allocated_amount)


	if pe:
		if pe.docstatus == 1:
			pe.flags.ignore_permissions = True
			try:
				pe.cancel()
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)
	
	

def delete_payment_entry(self):
	ref_name = self.pe_ref
	try:
		frappe.db.set_value("Payment Entry", self.name, 'pe_ref', '')    
		frappe.db.set_value("Payment Entry", ref_name, 'pe_ref', '')
		frappe.delete_doc("Payment Entry", ref_name, force = 1)
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)
	

def get_sales_person(self):
	for row in self.references:
		if row.reference_doctype == "Sales Invoice":
			row.sales_person = frappe.db.get_value(row.reference_doctype,row.reference_name,'sales_partner')

@frappe.whitelist()
def get_outstanding_reference_document(args):

	if isinstance(args, string_types):
		args = json.loads(args)

	if args.get('party_type') == 'Member':
		return

	# confirm that Supplier is not blocked
	if args.get('party_type') == 'Supplier':
		supplier_status = get_supplier_block_status(args['party'])
		if supplier_status['on_hold']:
			if supplier_status['hold_type'] == 'All':
				return []
			elif supplier_status['hold_type'] == 'Payments':
				if not supplier_status['release_date'] or getdate(nowdate()) <= supplier_status['release_date']:
					return []

	party_account_currency = get_account_currency(args.get("party_account"))
	company_currency = frappe.get_cached_value('Company',  args.get("company"),  "default_currency")

	# Get negative outstanding sales /purchase invoices
	negative_outstanding_invoices = []
	if args.get("party_type") not in ["Student", "Employee"] and not args.get("voucher_no"):
		negative_outstanding_invoices = get_negative_outstanding_invoices(args.get("party_type"), args.get("party"),
			args.get("party_account"), args.get("company"), party_account_currency, company_currency, args.get("primary_customer"))

	# Get positive outstanding sales /purchase invoices/ Fees
	condition = ""
	if args.get("voucher_type") and args.get("voucher_no"):
		condition = " and voucher_type={0} and voucher_no={1}"\
			.format(frappe.db.escape(args["voucher_type"]), frappe.db.escape(args["voucher_no"]))

	# Add cost center condition
	if args.get("cost_center"):
		condition += " and cost_center='%s'" % args.get("cost_center")

	date_fields_dict = {
		'posting_date': ['from_posting_date', 'to_posting_date'],
		'due_date': ['from_due_date', 'to_due_date']
	}

	for fieldname, date_fields in date_fields_dict.items():
		if args.get(date_fields[0]) and args.get(date_fields[1]):
			condition += " and {0} between '{1}' and '{2}'".format(fieldname,
				args.get(date_fields[0]), args.get(date_fields[1]))

	if args.get("company"):
		condition += " and company = {0}".format(frappe.db.escape(args.get("company")))

	outstanding_invoices = get_outstanding_invoices(args.get("party_type"), args.get("party"),
		args.get("party_account"), args.get("primary_customer"), filters=args, condition=condition)
	
	for d in outstanding_invoices:
		d["exchange_rate"] = 1
		if party_account_currency != company_currency:
			if d.voucher_type in ("Sales Invoice", "Purchase Invoice", "Expense Claim"):
				d["exchange_rate"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "conversion_rate")
			elif d.voucher_type == "Journal Entry":
				d["exchange_rate"] = get_exchange_rate(
					party_account_currency,	company_currency, d.posting_date
				)
		if d.voucher_type in ("Purchase Invoice"):
			d["bill_no"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "bill_no")

	# Get all SO / PO which are not fully billed or aginst which full advance not paid
	orders_to_be_billed = []
	if (args.get("party_type") != "Student"):
		orders_to_be_billed =  get_orders_to_be_billed(args.get("posting_date"),args.get("party_type"),
			args.get("party"), args.get("company"), party_account_currency, company_currency, args.get("primary_customer"), filters=args)

	data = negative_outstanding_invoices + outstanding_invoices + orders_to_be_billed

	if not data:
		frappe.msgprint(_("No outstanding invoices found for the {0} {1} which qualify the filters you have specified.")
			.format(args.get("party_type").lower(), frappe.bold(args.get("party"))))

	return data


def get_orders_to_be_billed(posting_date, party_type, party,
	company, party_account_currency, company_currency, primary_customer=None, cost_center=None, filters=None):
	if party_type == "Customer":
		voucher_type = 'Sales Order'
	elif party_type == "Supplier":
		voucher_type = 'Purchase Order'
	elif party_type == "Employee":
		voucher_type = None

	# Add cost center condition
	if voucher_type:
		doc = frappe.get_doc({"doctype": voucher_type})
		condition = ""
		select_condition = ""
		if doc and hasattr(doc, 'cost_center'):
			condition += " and cost_center='%s'" % cost_center
		if primary_customer and hasattr(doc, 'primary_customer'):
			select_condition += ", primary_customer"
			condition += " and primary_customer='%s'" % primary_customer

	orders = []
	if voucher_type:
		if party_account_currency == company_currency:
			grand_total_field = "base_grand_total"
			rounded_total_field = "base_rounded_total"
		else:
			grand_total_field = "grand_total"
			rounded_total_field = "rounded_total"

		orders = frappe.db.sql("""
			select
				name as voucher_no,
				if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) as invoice_amount,
				(if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) - advance_paid) as outstanding_amount,
				transaction_date as posting_date {select_condition}
			from
				`tab{voucher_type}`
			where
				{party_type} = %s
				and docstatus = 1
				and company = %s
				and ifnull(status, "") != "Closed"
				and if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) > advance_paid
				and abs(100 - per_billed) > 0.01
				{condition}
			order by
				transaction_date, name
		""".format(**{
			"select_condition": select_condition,
			"rounded_total_field": rounded_total_field,
			"grand_total_field": grand_total_field,
			"voucher_type": voucher_type,
			"party_type": scrub(party_type),
			"condition": condition
		}), (party, company), as_dict=True)

	order_list = []
	for d in orders:
		if not (flt(d.outstanding_amount) >= flt(filters.get("outstanding_amt_greater_than"))
			and flt(d.outstanding_amount) <= flt(filters.get("outstanding_amt_less_than"))):
			continue

		d["voucher_type"] = voucher_type
		# This assumes that the exchange rate required is the one in the SO
		d["exchange_rate"] = get_exchange_rate(party_account_currency, company_currency, posting_date)
		order_list.append(d)

	return order_list

def get_negative_outstanding_invoices(party_type, party, party_account,
	company, party_account_currency, company_currency, primary_customer=None, cost_center=None):
	voucher_type = "Sales Invoice" if party_type == "Customer" else "Purchase Invoice"
	supplier_condition = ""
	if voucher_type:
		doc = frappe.get_doc({"doctype": voucher_type})
		select_condition = ""
		if primary_customer and hasattr(doc, 'primary_customer'):
			select_condition += ", primary_customer"
			supplier_condition += " and primary_customer='%s'" % primary_customer

	if voucher_type == "Purchase Invoice":
		supplier_condition += "and (release_date is null or release_date <= CURDATE())"
	if party_account_currency == company_currency:
		grand_total_field = "base_grand_total"
		rounded_total_field = "base_rounded_total"
	else:
		grand_total_field = "grand_total"
		rounded_total_field = "rounded_total"

	return frappe.db.sql("""
		select
			"{voucher_type}" as voucher_type, name as voucher_no,
			if({rounded_total_field}, {rounded_total_field}, {grand_total_field}) as invoice_amount,
			outstanding_amount, posting_date,
			due_date, conversion_rate as exchange_rate {select_condition}
		from
			`tab{voucher_type}`
		where
			{party_type} = %s and {party_account} = %s and docstatus = 1 and
			company = %s and outstanding_amount < 0
			{supplier_condition}
		order by
			posting_date, name
		""".format(**{
			"select_condition":select_condition,
			"supplier_condition": supplier_condition,
			"rounded_total_field": rounded_total_field,
			"grand_total_field": grand_total_field,
			"voucher_type": voucher_type,
			"party_type": scrub(party_type),
			"party_account": "debit_to" if party_type == "Customer" else "credit_to",
			"cost_center": cost_center
		}), (party, party_account, company), as_dict=True)

def get_outstanding_invoices(party_type, party, account, primary_customer=None, condition=None, filters=None):
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

	if account:
		root_type, account_type = frappe.get_cached_value("Account", account, ["root_type", "account_type"])
		party_account_type = "Receivable" if root_type == "Asset" else "Payable"
		party_account_type = account_type or party_account_type
	else:
		party_account_type = erpnext.get_party_account_type(party_type)

	if party_account_type == 'Receivable':
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		payment_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		payment_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	held_invoices = get_held_invoices(party_type, party)

	invoice_list = frappe.db.sql("""
		select
			voucher_no, voucher_type, posting_date, due_date,
			ifnull(sum({dr_or_cr}), 0) as invoice_amount,
			account_currency as currency
		from
			`tabGL Entry`
		where
			party_type = %(party_type)s and party = %(party)s
			and account = %(account)s and {dr_or_cr} > 0
			{condition}
			and ((voucher_type = 'Journal Entry'
					and (against_voucher = '' or against_voucher is null))
				or (voucher_type not in ('Journal Entry', 'Payment Entry')))
		group by voucher_type, voucher_no
		order by posting_date, name""".format(
			dr_or_cr=dr_or_cr,
			condition=condition or ""
		), {
			"party_type": party_type,
			"party": party,
			"account": account,
		}, as_dict=True)

	payment_entries = frappe.db.sql("""
		select against_voucher_type, against_voucher,
			ifnull(sum({payment_dr_or_cr}), 0) as payment_amount
		from `tabGL Entry`
		where party_type = %(party_type)s and party = %(party)s
			and account = %(account)s
			and {payment_dr_or_cr} > 0
			and against_voucher is not null and against_voucher != ''
		group by against_voucher_type, against_voucher
	""".format(payment_dr_or_cr=payment_dr_or_cr), {
		"party_type": party_type,
		"party": party,
		"account": account
	}, as_dict=True)

	pe_map = frappe._dict()
	for d in payment_entries:
			pe_map.setdefault((d.against_voucher_type, d.against_voucher), d.payment_amount)

	for d in invoice_list:
		doc = frappe.get_doc({"doctype": d.voucher_type})
		if hasattr(doc, 'primary_customer'):
			primary_customer_value = frappe.db.get_value(d.voucher_type,d.voucher_no,"primary_customer")
		else:
			primary_customer_value = ''
		payment_amount = pe_map.get((d.voucher_type, d.voucher_no), 0)
		outstanding_amount = flt(d.invoice_amount - payment_amount, precision)
		if outstanding_amount > 0.5 / (10**precision):
			if (filters and filters.get("outstanding_amt_greater_than") and
				not (outstanding_amount >= filters.get("outstanding_amt_greater_than") and
				outstanding_amount <= filters.get("outstanding_amt_less_than"))):
				continue

			if not d.voucher_type == "Purchase Invoice" or d.voucher_no not in held_invoices:
				doc = frappe.get_doc(d.voucher_type,d.voucher_no)
				if not hasattr(doc, 'primary_customer') or not primary_customer:
					outstanding_invoices.append(
						frappe._dict({
							'voucher_no': d.voucher_no,
							'voucher_type': d.voucher_type,
							'posting_date': d.posting_date,
							'primary_customer': primary_customer_value,
							'invoice_amount': flt(d.invoice_amount),
							'payment_amount': payment_amount,
							'outstanding_amount': outstanding_amount,
							'due_date': d.due_date,
							'currency': d.currency
						})
					)
				elif primary_customer == primary_customer_value:
					outstanding_invoices.append(
						frappe._dict({
							'voucher_no': d.voucher_no,
							'voucher_type': d.voucher_type,
							'posting_date': d.posting_date,
							'primary_customer': primary_customer_value,
							'invoice_amount': flt(d.invoice_amount),
							'payment_amount': payment_amount,
							'outstanding_amount': outstanding_amount,
							'due_date': d.due_date,
							'currency': d.currency
						})
					)
	outstanding_invoices = sorted(outstanding_invoices, key=lambda k: k['due_date'] or getdate(nowdate()))
	return outstanding_invoices
