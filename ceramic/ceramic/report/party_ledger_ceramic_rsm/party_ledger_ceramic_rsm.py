# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
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
	qty_total = 0

	if filters.get('print_with_item'):
		reference_doc_map = {(i.party, i.voucher_no): (i.credit, i.debit, i.balance,i.qty, i.si_details) for i in res if i.company == filters.company and i.reference_doc}
	else:
		reference_doc_map = {(i.party, i.voucher_no): (i.credit, i.debit, i.balance, i.qty) for i in res if i.company == filters.company and i.reference_doc}

	for d in res:
		flag = False
					
		if d.company != filters.company:
			flag = True
			d.billed_credit = d.credit
			d.billed_debit = d.debit
			d.billed_balance = d.balance
			
			if d.reference_doc:
				if filters.get('print_with_item'):
					d.total_credit, d.total_debit, d.total_balance,d.qty, d.si_details = reference_doc_map[(d.party, d.reference_doc)]
				else:
					d.total_credit, d.total_debit, d.total_balance,d.qty = reference_doc_map[(d.party, d.reference_doc)]

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
			qty_total += d.qty
			data.append(d)
			
	data += [{
		"voucher_no": "Total",
		"qty":qty_total,
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
			(gle.`posting_date` < '{from_date}' or gle.transaction_status = 'Old') {conditions} {group_by_having_conditions}
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
	debit = credit = balance = qty = 0

	for item in data:
		debit += item.debit	 	
		credit += item.credit
		balance += item.balance
		qty += item.qty
	
	return [{'account': 'Closing', 'debit': debit, 'credit': credit, 'balance': balance, 'qty':qty}]

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
	conditions =" AND "
	company_placeholder_list = []
	if filters.company:
		company_placeholder_list.append(filters.company)
		alternate_company = [x.name for x in frappe.get_list("Company", {'alternate_company': filters.company}, 'name')]
		company_placeholder_list += alternate_company

		company_placeholder= ', '.join(f"'{i}'" for i in company_placeholder_list)
		conditions += (f"gle.company in ({company_placeholder})")

	conditions += f" AND gle.`posting_date` >= '{filters.from_date}'"	
	conditions += f" AND gle.`posting_date` <= '{filters.to_date}'"
	conditions += f" AND gle.`party_type` = '{filters.party_type}'" if filters.get('party_type') else f" AND gle.`party_type` in ('Customer', 'Supplier')"
	conditions += f" AND gle.`party` = '{filters.party}'" if filters.get('party') else ''
	having_cond = f" HAVING primary_customer = '{filters.primary_customer}'" if filters.get('primary_customer') else ''
	primary_customer_pe_fields = f", pe.reference_doctype as pe_ref_doctype, pe.reference_docname as pe_ref_doc" if filters.get('primary_customer') else ''
	
	data = frappe.db.sql(f"""
		SELECT 
			gle.name, gle.posting_date, gle.account, gle.party_type, gle.party, sum(gle.debit) as debit, sum(gle.credit) as credit,
			gle.voucher_type, gle.voucher_no, SUM(gle.debit - gle.credit) AS balance, gle.cost_center, gle.company,
			IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer,
			IFNULL(pi.total_qty, IFNULL(si.total_qty, 0)) as qty,
			IFNULL(si.is_return, 0) as is_return, jv.user_remark as remark,
			IFNULL(si.si_ref, IFNULL(pi.pi_ref, pe.pe_ref)) as reference_doc{primary_customer_pe_fields}
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE
			gle.is_cancelled = 0 and gle.transaction_status = 'New'
			{conditions}
		GROUP BY
			gle.voucher_no, gle.party {having_cond}
		ORDER BY
			gle.posting_date, gle.party
	""", as_dict = True)

	if filters.get('primary_customer'):
		data_map = {}
		new_data = []
		for i in data:
			if i.voucher_type == "Payment Entry" and i.pe_ref_doctype == "Primary Customer Payment":
				if not data_map.get(i.pe_ref_doc):
					data_map[i.pe_ref_doc] = i
				else:
					data_map[i.pe_ref_doc]['debit'] = flt(data_map[i.pe_ref_doc].get('debit')) + flt(i.debit)
					data_map[i.pe_ref_doc]['credit'] = flt(data_map[i.pe_ref_doc].get('credit')) + flt(i.credit)
					data_map[i.pe_ref_doc]['balance'] = flt(data_map[i.pe_ref_doc].get('balance')) + flt(i.balance)
			else:
				new_data.append(i)
			
		if data_map:
			for key, value in data_map.items():
				value.voucher_type = "Primary Customer Payment"
				value.voucher_no = key
				value.party = filters.get('primary_customer')
				new_data.append(value)
		
		data = sorted(new_data, key = lambda i: i['posting_date'])
	if filters.get('print_with_item'):	
		sales_invoice_map,total_taxes_and_charges = get_sales_invoice_data(filters)
		for d in data:
			try:
				d.si_details = html_sales_invoice_data(sales_invoice_map[d.name],total_taxes_and_charges[d.name])
			except KeyError:
				d.si_details = ''
	return data

def html_sales_invoice_data(sales_invoice_map,total_taxes_and_charges):
	table = ""
	for item_group,value in sales_invoice_map.items():
		if item_group:
			if item_group.find('-'):
				i_group = item_group.split('-', 1)[0].strip()
			else:
				i_group = item_group

			table += f"""
				<p>
					<strong>{i_group}</strong>
				</p>
			"""
			for k,v in value.items():
				table+= f"""<p>
						{v["qty"]} x {k} = <span><strong>{frappe.format(v["qty"] * k,{'fieldtype': 'Currency'})}</strong></span>
					</p>	
				"""
	if total_taxes_and_charges:
		table += f"""<p>
			<span><strong>Taxes & Charges = {frappe.format(total_taxes_and_charges,{'fieldtype': 'Currency'})}</strong></span>
		</p>
	"""
	return table

def get_sales_invoice_data(filters):
	conditions ="gle.is_cancelled = 0"
	company_placeholder_list = []
	if filters.company:
		company_placeholder_list.append(filters.company)
		alternate_company = [x.name for x in frappe.get_list("Company", {'alternate_company': filters.company}, 'name')]
		company_placeholder_list += alternate_company

		company_placeholder= ', '.join(f"'{i}'" for i in company_placeholder_list)
		conditions += (f" AND gle.company in ({company_placeholder})")

	conditions += f" AND gle.`posting_date` >= '{filters.from_date}'"	
	conditions += f" AND gle.`posting_date` <= '{filters.to_date}'"
	conditions += " AND gle.voucher_type = 'Sales Invoice'"
	conditions += f" AND gle.`party_type` = '{filters.party_type}'" if filters.get('party_type') else f" AND gle.`party_type` in ('Customer', 'Supplier')"
	conditions += f" AND gle.`party` = '{filters.party}'" if filters.get('party') else ''
	
	si_data = frappe.db.sql(f"""
		SELECT 
			gle.name, sii.parent as si_name, si.total,si.rounded_total, sii.item_group, sii.rate, sii.qty
		FROM
			`tabGL Entry` as gle
			JOIN `tabSales Invoice Item` as sii ON sii.parent=gle.voucher_no
			JOIN `tabSales Invoice` as si ON si.name = gle.voucher_no
		WHERE
			{conditions}
	""", as_dict = True)
	
	sales_invoice_map = {}
	total_taxes_and_charges = {}
	for row in si_data:
		total_taxes_and_charges[row.name] = row.rounded_total - row.total
		sales_invoice_map.setdefault(row.name, {})\
			.setdefault(row.item_group, {})\
			.setdefault(row.rate, frappe._dict({
				"qty": 0.0,
			}))
		sales_invoice_dict = sales_invoice_map[row.name][row.item_group][row.rate]
		sales_invoice_dict.qty += row.qty

	return sales_invoice_map,total_taxes_and_charges

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
			"label": _("Link No"),
			"fieldname": "reference_doc",
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
		# {
		# 	"label": _("Account"),
		# 	"fieldname": "account",
		# 	"fieldtype": "Link",
		# 	"options": "Account",
		# 	"width": 180,
		# 	"hidden": 1,
		# 	"ignore_user_permission":1
		# },
		# {
		# 	"label": _("Qty".format(currency)),
		# 	"fieldname": "qty",
		# 	"fieldtype": "Float",
		# 	"width": 80
		# },
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
		# {
		# 	"label": _("GL Entry"),
		# 	"fieldname": "name",
		# 	"fieldtype": "Link",
		# 	"options": "GL Entry",
		# 	"width": 100,
		# 	"ignore_user_permission":1
		# },
		{
			"label": _("Primary Customer"),
			"fieldname": "primary_customer",
			"fieldtype": "Data",
			"options": "Customer",
			"width": 120
		},	
		{
			"label": _("Remark"),
			"fieldname": "remark",
			"fieldtype": "data",
			"width": 120
		},
	]
	return columns