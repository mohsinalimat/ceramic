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
		"voucher_no": "Closing (Opening + Total)",
		"total_debit": total['total_debit'] + opening['total_debit'],
		"total_credit": total['total_credit'] + opening['total_credit'],
		"total_balance": total['total_balance'],
		"billed_debit": total['billed_debit'] + opening['billed_debit'],
		"billed_credit": total['billed_credit'] + opening['billed_credit'],
		"billed_balance": total['billed_balance'],
		"cash_debit": total['cash_debit'] + opening['cash_debit'],
		"cash_credit": total['cash_credit'] + opening['cash_credit'],
		"cash_balance": total['cash_balance'],
	})

	return result

def reference_doc_details(filters):
	conditions = ''

	if filters.get('company'):
		alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')
		conditions += f"`company` in ('{alternate_company}', '{filters.company}')"

	if filters.get('from_date'):
		conditions += f" AND posting_date >= '{filters.from_date}'"
	
	if filters.get('to_date'):
		conditions += f" AND posting_date <= '{filters.to_date}'"
	
	pe_cond = ''
	si_cond = ''
	pi_cond = ''
	
	if filters.get('party'):
		pe_cond = f" AND `party` = '{filters.party}'"
		si_cond = f" AND `customer` = '{filters.party}'"
		pi_cond = f" AND `supplier` = '{filters.party}'"
	
	ref_si = frappe.db.sql(f"""
		SELECT name, si_ref as ref_doc from `tabSales Invoice` 
		WHERE {conditions} {si_cond}
	""", as_dict = True)

	ref_pi = frappe.db.sql(f"""
		SELECT name, pi_ref as ref_doc from `tabPurchase Invoice` 
		WHERE {conditions} {pi_cond}
	""", as_dict = True)

	ref_pe = frappe.db.sql(f"""
		SELECT name, pe_ref as ref_doc from `tabPayment Entry` 
		WHERE {conditions} {pe_cond}
	""", as_dict = True)

	reference_doc_dict = ref_si + ref_pi + ref_pe
	reference_doc_dict = {x['name']:x['ref_doc'] for x in reference_doc_dict}
	return reference_doc_dict

def generate_data(filters, res):
	opening = get_opening(filters)[0]
	data = []
	total_debit_total = billed_debit_total = cash_debit_total = 0
	total_credit_total = billed_credit_total = cash_credit_total = 0
	total_balance_total = opening['total_balance']
	billed_balance_total = opening['billed_balance']
	cash_balance_total = opening['cash_balance']

	ref_doc_map = reference_doc_details(filters)
	for d in res:
		flag = False
		
		d.reference_doc = ref_doc_map.get(d.voucher_no)
			
		if d.company != filters.company:
			flag = True
			d.billed_credit = d.credit
			d.billed_debit = d.debit
			d.billed_balance = d.balance
			
			if d.reference_doc:
				d.total_credit, d.total_debit = frappe.db.get_value(
					"GL Entry", 
					{
						"party": d.party,
						"voucher_type": d.voucher_type,
						"voucher_no": d.reference_doc,
					},
					['sum(credit)', 'sum(debit)']
				)
				d.total_balance = d.total_debit - d.total_credit
			else:
				d.total_credit = d.total_debit = d.total_balance = 0

		elif d.company == filters.company and not d.reference_doc:
			flag = True
			d.total_debit = d.debit
			d.total_credit = d.credit
			d.total_balance = d.balance

			d.billed_debit = d.billed_credit = d.billed_balance = 0

		if flag:
			d.cash_debit = d.total_debit - d.billed_debit
			d.cash_credit = d.total_credit - d.billed_credit
			d.cash_balance = d.total_balance - d.billed_balance
	
			cash_debit_total += d.cash_debit
			cash_credit_total += d.cash_credit

			total_debit_total += d.total_debit
			total_credit_total += d.total_credit
			
			billed_debit_total += d.billed_debit
			billed_credit_total += d.billed_credit
			
			total_balance_total = d.total_balance = flt(d.total_balance) + flt(total_balance_total)
			cash_balance_total = d.cash_balance = flt(d.cash_balance) + flt(cash_balance_total)
			billed_balance_total = d.billed_balance = flt(d.billed_balance) + flt(billed_balance_total)
			data.append(d)
			
	data += [{
		"voucher_no": "Total",
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
	else:
		conditions = f" AND gle.`party_type` in ('Customer', 'Supplier')"
	
	if filters.get('party'):
		conditions += f" AND gle.`party` = '{filters.party}'"
	
	alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')

	having_cond = ''
	if filters.get('primary_customer'):
		having_cond = f" HAVING primary_customer = '{filters.primary_customer}'"
	
	total_data = frappe.db.sql(f"""
		SELECT 
			SUM(gle.debit) as debit, SUM(gle.credit) as credit, SUM(gle.debit - gle.credit) as balance,
			IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE 
			gle.`company` = '{filters.company}' AND
			gle.`posting_date` < '{filters.from_date}' {conditions} {having_cond}
	""", as_dict = True)

	authorized_data =  frappe.db.sql(f"""
		SELECT 
			SUM(gle.debit) as debit, SUM(gle.credit) as credit, SUM(gle.debit - gle.credit) as balance,
			IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE 
			gle.`company` = '{alternate_company}' AND
			gle.`posting_date` < '{filters.from_date}' {conditions} {having_cond}
	""", as_dict = True)

	if not total_data:
		total_data = {'debit': 0, 'credit': 0, 'balance': 0, 'primary_customer': None}
	else:
		total_data = total_data[0]

	if not authorized_data:
		authorized_data = {'debit': 0, 'credit': 0, 'balance': 0, 'primary_customer': None}
	else:
		authorized_data = authorized_data[0]

	data = []

	data.append({
		"voucher_no": 'Opening',
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
	
	if filters.get('company'):
		alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')
		conditions += f" gle.`company` in ('{filters.company}', '{alternate_company}')"

	if filters.get('from_date'):
		conditions += f" AND gle.`posting_date` >= '{filters.from_date}'"
	
	if filters.get('to_date'):
		conditions += f" AND gle.`posting_date` <= '{filters.to_date}'"
	
	if filters.get('party_type'):
		conditions += f" AND gle.`party_type` = '{filters.party_type}'"
	else:
		conditions += f" AND gle.`party_type` in ('Customer', 'Supplier')"
	
	if filters.get('party'):
		conditions += f" AND gle.`party` = '{filters.party}'"
	
	having_cond = ''
	if filters.get('primary_customer'):
		having_cond = f" HAVING primary_customer = '{filters.primary_customer}'"
	
	return frappe.db.sql(f"""
		SELECT 
			gle.name, gle.posting_date, gle.account, gle.party_type, gle.party, sum(gle.debit) as debit, sum(gle.credit) as credit, gle.voucher_type, gle.voucher_no, SUM(gle.debit - gle.credit) AS balance, gle.cost_center, gle.company,
			IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer, IFNULL(pi.total_qty, IFNULL(si.total_qty, 0)) as qty
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE
			{conditions}
		GROUP BY
			gle.voucher_no, gle.party {having_cond}
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
		conditions += f" AND gle.party_type='{filters.party_type}'"
	else:
		conditions += " AND gle.party_type in ('Customer', 'Supplier')"
	
	if filters.get('party'):
		# frappe.throw(filters.party)
		conditions += f" AND gle.party='{filters.party}'"

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
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 100
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 120
		},
		{
			"label": _("Party Type"),
			"fieldname": "party_type",
			"Link": "Party Type",
			"width": 100
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 180,
			"hidden": 1
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
		},
		{
			"label": _("Party"),
			"fieldname": "party",
			"field_type": "Dynamic Link",
			"options": "party_type",
			"width": 150
		},
	]

	return columns
