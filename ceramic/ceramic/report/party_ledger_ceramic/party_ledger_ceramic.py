# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe, erpnext
from erpnext import get_company_currency, get_default_company
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from six import iteritems
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from collections import OrderedDict

def execute(filters=None):
	if not filters:
		return [], []
	
	account_details = {}
	validate_filters(filters, account_details)
	columns = get_columns(filters)
	res = get_result(filters, account_details)
	data = process_data(filters, res)
	return columns, data

def process_data(filters, res):
	result = []
	result += get_opening(filters)

	result += generate_data(filters, res)
	
	total = result[-1]
	opening = result[0]
	result.append({
		"account": "Closing (Opening + Total)",
		"billed_debit": total['billed_debit'] + opening['billed_debit'],
		"billed_credit": total['billed_credit'] + opening['billed_credit'],
		"billed_balance": total['billed_balance'] + opening['billed_balance'],
		"cash_debit": total['cash_debit'] + opening['cash_debit'],
		"cash_credit": total['cash_credit'] + opening['cash_credit'],
		"cash_balance": total['cash_balance'] + opening['cash_balance'],
		"total_debit": total['total_debit'] + opening['total_debit'],
		"total_credit": total['total_credit'] + opening['total_credit'],
		"total_balance": total['total_balance'] + opening['total_balance'],
	})

	return result

def generate_data(filters, res):
	data = []
	total_debit_total = billed_debit_total = cash_debit_total = 0
	total_credit_total = billed_credit_total = cash_credit_total = 0
	total_balance_total = billed_balance_total = cash_balance_total = 0
	for d in res:
		d.reference_doc = None
		flag = False
		
		if d.voucher_type == "Sales Invoice":
			d.reference_doc = frappe.db.get_value("Sales Invoice", d['voucher_no'], 'si_ref')
		if d.voucher_type == "Purchase Invoice":
			d.reference_doc = frappe.db.get_value("Purchase Invoice", d['voucher_no'], 'pi_ref')
		if d.voucher_type == "Payment Entry":
			d.reference_doc = frappe.db.get_value("Payment Entry", d['voucher_no'], 'pe_ref')
		
		if d.company != filters.company:
			flag = True
			d.billed_credit = d.credit
			d.billed_debit = d.debit
			d.billed_balance = d.balance
			
			if d.reference_doc:
				if not frappe.db.exists(
					"GL Entry", 
					{
						"party": d.party,
						"voucher_type": d.voucher_type,
						"voucher_no": d.reference_doc,
					}
				):
					d.total_credit = 0
					d.total_debit = 0
				else:
					d.total_credit, d.total_debit = frappe.db.get_value(
						"GL Entry", 
						{
							"party": d.party,
							"voucher_type": d.voucher_type,
							"voucher_no": d.reference_doc,
						},
						['credit', 'debit']
					)
				d.total_balance = d.total_debit - d.total_credit
			else:
				d.total_credit = d.credit
				d.total_debit = d.debit
				d.total_balance = d.balance

			d.cash_debit = d.total_debit - d.billed_debit
			d.cash_credit = d.total_credit - d.billed_credit
			d.cash_balance = d.total_balance - d.billed_balance
			frappe.msgprint(str(d.name) + ' ' + str(d.cash_credit))
			data.append(d)
		elif d.company == filters.company and not d.reference_doc:
			flag = True
			d.cash_debit = d.total_debit = d.debit
			d.cash_credit = d.total_credit = d.credit
			d.cash_balance = d.total_balance = d.balance

			d.billed_debit = d.billed_credit = d.billed_balance = 0
			frappe.msgprint(str(d.name) + ' ' + str(d.cash_credit))
			data.append(d)

		if flag:
			billed_debit_total += d.billed_debit
			billed_credit_total += d.billed_credit
			billed_balance_total += d.billed_balance

			cash_debit_total += d.cash_debit
			cash_credit_total += d.cash_credit
			cash_balance_total += d.cash_balance

			total_debit_total += d.total_debit
			total_credit_total += d.total_credit
			total_balance_total += d.total_balance
			
	data += [{
		"account": "Total",
		"billed_debit": billed_debit_total,
		"billed_credit": billed_credit_total,
		"billed_balance": billed_balance_total,
		"cash_debit": cash_debit_total,
		"cash_credit": cash_credit_total,
		"cash_balance": cash_balance_total,
		"total_debit": total_debit_total,
		"total_credit": total_credit_total,
		"total_balance": total_balance_total
	}]
	return data
def get_opening(filters):
	conditions = ""
	if filters.get('party_type'):
		conditions = f" AND gle.`party_type` = '{filters.party_type}'"
	
	if filters.get('party'):
		conditions += f" AND gle.`party` = '{filters.party}'"
	else:
		conditions += " AND party_type in ('Customer', 'Supplier')"
	
	alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')
	
	total_data = frappe.db.sql(f"""
		SELECT 
			SUM(gle.debit) as debit, SUM(gle.credit) as credit, (SUM(gle.debit) - SUM(gle.credit)) as balance
		FROM
			`tabGL Entry` as gle 
		WHERE 
			gle.`company` = '{filters.company}' AND
			gle.`posting_date` < '{filters.from_date}' {conditions}
	""", as_dict = True)[0]
	
	authorized_data =  frappe.db.sql(f"""
		SELECT 
			SUM(gle.debit) as debit, SUM(gle.credit) as credit, (SUM(gle.debit) - SUM(gle.credit)) as balance
		FROM
			`tabGL Entry` as gle 
		WHERE 
			gle.`company` = '{alternate_company}' AND
			gle.`posting_date` < '{filters.from_date}' {conditions}
	""", as_dict = True)[0]

	data = []

	data.append({
		"account": 'Opening',
		"billed_debit": flt(authorized_data['debit'], 2),
		"cash_debit": flt(total_data['debit'], 2) - flt(authorized_data['debit'], 2),
		"total_debit": flt(total_data['debit'], 2),
		"billed_credit": flt(authorized_data['credit'], 2),
		"cash_credit": flt(total_data['credit'], 2) - flt(authorized_data['credit'], 2),
		"total_credit": flt(total_data['credit'], 2),
		"billed_balance": flt(authorized_data['balance'], 2),
		"cash_balance": flt(total_data['balance'], 2) - flt(authorized_data['balance'], 2),
		"total_balance": flt(total_data['balance'], 2),
	})

	return data

def get_closing(data):
	closing = []

	debit = 0
	credit = 0
	balance = 0

	for item in data:
		debit += item.debit	 	
		credit += item.credit
		balance += item.balance
	
	return [{'account': 'Closing', 'debit': debit, 'credit': credit, 'balance': balance}]

def validate_filters(filters, account_details):
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))
	
	# frappe.throw(str(filters.party))


def validate_party(filters):
	party_type, party = filters.get("party_type"), filters.get("party")

	if party:
		if not party_type:
			frappe.throw(_("To filter based on Party, select Party Type first"))
		else:
			for d in party:
				if not frappe.db.exists(party_type, d):
					frappe.throw(_("Invalid {0}: {1}").format(party_type, d))

def get_result(filters, account_details):
	conditions = ''
	alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')

	if filters.get('company'):
		conditions += f" AND gle.`company` in ('{filters.company}', '{alternate_company}')"

	if filters.get('from_date'):
		conditions = f" gle.`posting_date` >= '{filters.from_date}'"
	
	if filters.get('to_date'):
		conditions += f" AND gle.`posting_date` <= '{filters.to_date}'"
	
	if filters.get('party_type'):
		conditions += f" AND gle.`party_type` = '{filters.party_type}'"
	else:
		conditions += f" AND gle.`party_type` in ('Customer', 'Supplier')"
	
	if filters.get('party'):
		conditions += f" AND gle.`party` = '{filters.party}'"
	
	return frappe.db.sql(f"""
		SELECT 
			gle.name, gle.posting_date, gle.account, gle.party_type, gle.party, gle.debit, gle.credit, gle.voucher_type, gle.voucher_no, gle.debit - gle.credit AS balance, gle.cost_center, gle.company
		FROM 
			`tabGL Entry` as gle
		WHERE
			{conditions}
		ORDER BY
			gle.party
	""", as_dict = True)

def date_conditions(filters):
	conditions = ''

	if filters.get('from_date'):
		conditions += f" AND gle.posting_date >= '{filters.from_date}'"
	
	if filters.get('to_date'):
		conditions += f" AND gle.posting_date <= '{filters.to_date}'"

	return conditions

def open_date_conditions(filters):
	conditions = ''

	if filters.get('from_date'):
		conditions += f" AND gle.posting_date < '{filters.from_date}'"

	return conditions

def get_conditions(filters):
	conditions = ''
	
	if filters.company:
		alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')
		conditions += f" gle.company IN ('{filters.company}', '{alternate_company}')"
	
	if filters.get("party_type"):
		conditions += f" AND party_type='{filters.party_type}'"
	else:
		conditions += " AND party_type in ('Customer', 'Supplier')"
	
	if filters.get('party'):
		# frappe.throw(filters.party)
		conditions += f" AND party='{filters.party}'"

	return conditions

def get_columns(filters):
	if filters.get("presentation_currency"):
		currency = filters["presentation_currency"]
	else:
		if filters.get("company"):
			currency = get_company_currency(filters["company"])
		else:
			company = get_default_company()
			currency = get_company_currency(company)

	columns = [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 90
		},
		{
			"label": _("Name"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "GL Entry",
			"width": 180
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 180
		},
		{
			"label": _("Billed Debit ({0})".format(currency)),
			"fieldname": "billed_debit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Cash Debit ({0})".format(currency)),
			"fieldname": "cash_debit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Total Debit ({0})".format(currency)),
			"fieldname": "total_debit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Billed Credit ({0})".format(currency)),
			"fieldname": "billed_credit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Cash Credit ({0})".format(currency)),
			"fieldname": "cash_credit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Total Credit ({0})".format(currency)),
			"fieldname": "total_credit",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Billed Balance ({0})".format(currency)),
			"fieldname": "billed_balance",
			"fieldtype": "Float",
			"width": 130
		},
		{
			"label": _("Cash Balance ({0})".format(currency)),
			"fieldname": "cash_balance",
			"fieldtype": "Float",
			"width": 130
		},
		{
			"label": _("Total Balance ({0})".format(currency)),
			"fieldname": "total_balance",
			"fieldtype": "Float",
			"width": 130
		}
	]

	columns.extend([
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 120
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"width": 100
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"width": 100
		},
	])

	return columns
