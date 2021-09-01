# Copyright (c) 2013, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from six import iteritems
from collections import OrderedDict

import frappe
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions

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

def generate_data(filters, res):
	opening = get_opening(filters)[0]
	data = []
	total_debit_total = billed_debit_total = cash_debit_total = 0
	total_credit_total = billed_credit_total = cash_credit_total = 0
	total_balance_total = opening['total_balance']
	billed_balance_total = opening['billed_balance']
	cash_balance_total = opening['cash_balance']

	reference_doc_map = {(i.party, i.voucher_no): (i.credit, i.debit, i.balance) for i in res if i.company == filters.company and i.reference_doc}

	for d in res:
		flag = False
					
		if d.company != filters.company:
			flag = True
			d.billed_credit = d.credit
			d.billed_debit = d.debit
			d.billed_balance = d.balance
			
			if d.reference_doc:
				d.total_credit, d.total_debit, d.total_balance = reference_doc_map[(d.party, d.reference_doc)]
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

			d.voucher_no_trim = d.voucher_no[-4:]
			
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

def get_opening_query(primary_customer_select, company, from_date, conditions, group_by_having_conditions):
	data = frappe.db.sql(f"""
		SELECT 
			SUM(gle.debit) as debit, SUM(gle.credit) as credit, SUM(gle.debit - gle.credit) as balance{primary_customer_select}
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE 
			gle.is_cancelled = 0 and gle.`company` = '{company}' AND
			gle.`posting_date` < '{from_date}' {conditions} {group_by_having_conditions}
	""", as_dict = True)

	if not data:
		data = {'debit': 0, 'credit': 0, 'balance': 0, 'primary_customer': None}
	else:
		data = data[0]
	
	return data

def get_opening(filters):
	conditions = f" AND gle.`party_type` = '{filters.party_type}'" if filters.get('party_type') else f" AND gle.`party_type` in ('Customer', 'Supplier')"
	conditions += f" AND gle.`party` = '{filters.party}'" if filters.get('party') else ''
	
	alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')

	group_by_having_conditions = primary_customer_select = ''
	if filters.get('primary_customer'):
		primary_customer_select = ", IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer"
		group_by_having_conditions = f" GROUP BY primary_customer HAVING primary_customer = '{filters.primary_customer}'"
	
	total_data = get_opening_query(primary_customer_select, filters.company, filters.from_date, conditions, group_by_having_conditions)
	authorized_data = get_opening_query(primary_customer_select, alternate_company, filters.from_date, conditions, group_by_having_conditions)

	data = [{
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
	}]

	return data

def get_closing(data):
	debit = credit = balance = 0

	for item in data:
		debit += item.debit	 	
		credit += item.credit
		balance += item.balance
	
	return [{'account': 'Closing', 'debit': debit, 'credit': credit, 'balance': balance}]

def validate_filters(filters, account_details):
	if not filters.get('company'):
		frappe.throw(_('{0} is mandatory').format(_('Company')))

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
	alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')

	conditions = f" AND gle.`company` in ('{filters.company}', '{alternate_company}')"
	conditions += f" AND gle.`posting_date` >= '{filters.from_date}'"	
	conditions += f" AND gle.`posting_date` <= '{filters.to_date}'"
	conditions += f" AND gle.`party_type` = '{filters.party_type}'" if filters.get('party_type') else f" AND gle.`party_type` in ('Customer', 'Supplier')"
	conditions += f" AND gle.`party` = '{filters.party}'" if filters.get('party') else ''
	
	primary_customer_pe_fields = f", pe.reference_doctype as pe_ref_doctype, pe.reference_docname as pe_ref_doc" if filters.get('primary_customer') else ''
	
	data = frappe.db.sql(f"""
		SELECT 
			gle.name, gle.posting_date, gle.account, gle.party_type, gle.party, (gle.debit) as debit, (gle.credit) as credit,
			gle.voucher_type, gle.voucher_no, (gle.debit - gle.credit) AS balance, gle.cost_center, gle.company,gle.against_voucher as against_voucher, gle.against_voucher_type as against_voucher_type,
			IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer,
			IFNULL(pi.total_qty, IFNULL(si.total_qty, 0)) as qty,
			IFNULL(si.is_return, 0) as is_return,
			IFNULL(si.si_ref, IFNULL(pi.pi_ref, pe.pe_ref)) as reference_doc{primary_customer_pe_fields}
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE
			gle.is_cancelled = 0
			{conditions}
		ORDER BY
			gle.posting_date, gle.party
	""", as_dict = True)

	# if filters.get('primary_customer'):
	# 	data_map = {}
	# 	new_data = []
	# 	for i in data:
	# 		if i.voucher_type == "Payment Entry" and i.pe_ref_doctype == "Primary Customer Payment":
	# 			if not data_map.get(i.pe_ref_doc):
	# 				data_map[i.pe_ref_doc] = i
	# 			else:
	# 				data_map[i.pe_ref_doc]['debit'] = flt(data_map[i.pe_ref_doc].get('debit')) + flt(i.debit)
	# 				data_map[i.pe_ref_doc]['credit'] = flt(data_map[i.pe_ref_doc].get('credit')) + flt(i.credit)
	# 				data_map[i.pe_ref_doc]['balance'] = flt(data_map[i.pe_ref_doc].get('balance')) + flt(i.balance)
	# 		else:
	# 			new_data.append(i)
			
	# 	if data_map:
	# 		for key, value in data_map.items():
	# 			value.voucher_type = "Primary Customer Payment"
	# 			value.voucher_no = key
	# 			value.party = filters.get('primary_customer')
	# 			new_data.append(value)
		
	# 	data = sorted(new_data, key = lambda i: i['posting_date'])
	
	final_data = []
	for gle in data:
		if gle.against_voucher	and gle.against_voucher_type in ["Sales Invoice","Payment Entry","Journal Entry"]:
			gle['against_primary_customer']  = frappe.db.get_value(gle.against_voucher_type,gle.against_voucher,"primary_customer")
			if gle['against_primary_customer'] != gle.primary_customer:
				gle['error'] = "Error"
		final_data.append(gle)
	return final_data

def get_columns(filters):
	currency = get_company_currency(filters.company)

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
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 120
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
			"label": _("Party Type"),
			"fieldname": "party_type",
			"fieldtype": "Link",
			"options": "Party Type",
			"width": 100
		},
		{
			"label": _("GL Entry"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "GL Entry",
			"width": 100
		},
		{
			"label": _("Against Voucher Type"),
			"fieldname": "against_voucher_type",
			"width": 100
		},
		{
			"label": _("Against Voucher"),
			"fieldname": "against_voucher",
			"fieldtype": "Dynamic Link",
			"options": "against_voucher_type",
			"width": 100
		},
		{
			"label": _("Against Primary Customer"),
			"fieldname": "against_primary_customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120
		},
		{
			"label": _("Primary Customer"),
			"fieldname": "primary_customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120
		},
		{
			"label": _("Error"),
			"fieldname": "error",
			"fieldtype": "Data",
			"width": 100
		},
	]

	return columns
