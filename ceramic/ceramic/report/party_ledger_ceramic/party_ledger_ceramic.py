# Copyright (c) 2013, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt


from __future__ import unicode_literals

import frappe, os, time, json, shutil
from frappe.utils import flt,now
from frappe import _, _dict
from frappe.utils import get_url_to_form
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file

from erpnext import get_company_currency

# Whatsapp Import Start:
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

# Whatapp Import End

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

	closing = get_party_wise_closing(filters)
	
	total = result[-1]
	opening = result[0]
	result += [{}]
	result += closing
	result += [{}]
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

	# if filters.get('print_with_item'):
	reference_doc_map = {(i.voucher_no): (i.credit, i.debit, i.balance,i.qty, i.si_details) for i in res if i.company == filters.company and i.reference_doc}
	# else:
	# 	reference_doc_map = {(i.party, i.voucher_no): (i.credit, i.debit, i.balance, i.qty) for i in res if i.company == filters.company and i.reference_doc}

	for d in res:
		if filters.get('show_only_unlinked_transactions') and (d.authority == 'Authorized' and d.reference_doc):
			continue
		elif filters.get('show_only_unlinked_transactions') and d.authority == 'Unauthorized':
			continue
		elif not filters.get('show_unlinked_transactions') and d.authority == 'Authorized' and not d.reference_doc:
			continue
		flag = False
					 
		if d.company != filters.company:
			flag = True
			d.billed_credit = d.credit
			d.billed_debit = d.debit
			d.billed_balance = d.balance
			
			if d.reference_doc:
				# if filters.get('print_with_item'):
				d.total_credit, d.total_debit, d.total_balance,d.qty, d.si_details = reference_doc_map[(d.reference_doc)]
				# else:
					# d.total_credit, d.total_debit, d.total_balance,d.qty = reference_doc_map[(d.party, d.reference_doc)]

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

			abbr, authority, alternate_company = frappe.db.get_value('Company',d.company,['abbr','authority','alternate_company'])
			alternate_abbr, alternate_authority = frappe.db.get_value('Company',alternate_company,['abbr','authority'])
			
			reconciled_amount = d.total_balance if authority == "Unauthorized" else d.billed_balance
			alternate_reconciled_amount  = d.total_balance if alternate_authority == "Unauthorized" else d.billed_balance
			account = d.account
			alternate_account = account.replace(abbr,alternate_abbr)
			d['create_account_reco_entry'] = f"""
					<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;' 
						type='button' posting_date='{d.posting_date}' company='{d.company}' alternate_company='{alternate_company}' account='{d.account}' alternate_account='{alternate_account}' reconciled_amount='{reconciled_amount}' alternate_reconciled_amount='{alternate_reconciled_amount}' party_type='{d.party_type}' party='{d.primary_customer if d.party_type == "Customer" else d.party}'
						onClick='create_account_reco(this.getAttribute("posting_date"),this.getAttribute("company"),this.getAttribute("alternate_company"),this.getAttribute("account"),this.getAttribute("alternate_account"),this.getAttribute("reconciled_amount"),this.getAttribute("alternate_reconciled_amount"),this.getAttribute("party_type"),this.getAttribute("party"))'>Clear Transactions</button>"""

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
			gle.`company` = '{company}' AND
			(gle.`posting_date` < '{from_date}' or gle.transaction_status = 'Old') {conditions} {group_by_having_conditions}
	""", as_dict = True)

	if not data:
		data = {'debit': 0, 'credit': 0, 'balance': 0, 'primary_customer': None}
	else:
		data = data[0]
	
	return data

def get_closing_query(primary_customer_select, company, to_date, conditions, group_by_having_conditions):
	data = frappe.db.sql(f"""
		SELECT 
			IFNULL(jv.primary_customer, IFNULL(si.customer, IFNULL(pe.party, gle.party))) as party, SUM(gle.debit) as debit, SUM(gle.credit) as credit, SUM(gle.debit - gle.credit) as balance{primary_customer_select}
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE 
			gle.`company` = '{company}' AND
			(gle.`posting_date` <= '{to_date}') {conditions} {group_by_having_conditions}
	""", as_dict = True)
	
	# if not data:
	# 	data = {'debit': 0, 'credit': 0, 'balance': 0, 'primary_customer': None,'party':None}
	if data:
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

def get_party_wise_closing(filters):
	conditions = f" AND gle.`party_type` = '{filters.party_type}'" if filters.get('party_type') else f" AND gle.`party_type` in ('Customer', 'Supplier')"
	conditions += f" AND gle.`party` = '{filters.party}'" if filters.get('party') else ''
	
	alternate_company = frappe.db.get_value("Company", filters.company, 'alternate_company')

	group_by_having_conditions = primary_customer_select = ''
	if filters.get('primary_customer'):
		primary_customer_select = ", IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) as primary_customer"
		group_by_having_conditions = f" AND IFNULL(jv.primary_customer, IFNULL(si.primary_customer, IFNULL(pe.primary_customer, gle.party))) = '{filters.primary_customer}' GROUP BY party"
	
	total_data_list = get_closing_query(primary_customer_select, filters.company, filters.to_date, conditions, group_by_having_conditions)
	authorized_data_list = get_closing_query(primary_customer_select, alternate_company, filters.to_date, conditions, group_by_having_conditions)
	authorized_data_map, total_data_map = {},{}

	party_list = []
	if authorized_data_list:
		for d in authorized_data_list:
			authorized_data_map[d['party']] = d
			if d['party'] not in party_list:
				party_list.append(d['party'])

	if total_data_list:
		for d in total_data_list:
			total_data_map[d['party']] = d
			if d['party'] not in party_list:
				party_list.append(d['party'])
	
	data = []

	for party in party_list:
		auth_debit = flt(authorized_data_map.get(party).get('debit'), 2) if authorized_data_map.get(party) else 0
		auth_credit = flt(authorized_data_map.get(party).get('credit'), 2) if authorized_data_map.get(party) else 0
		auth_balance = flt(authorized_data_map.get(party).get('balance'), 2) if authorized_data_map.get(party) else 0

		total_debit = flt(total_data_map.get(party).get('debit'), 2) if total_data_map.get(party) else 0
		total_credit = flt(total_data_map.get(party).get('credit'), 2) if total_data_map.get(party) else 0
		total_balance = flt(total_data_map.get(party).get('balance'), 2) if total_data_map.get(party) else 0

		data += [{
			"voucher_no": 'Closing',
			"party": party,
			"billed_debit": auth_debit,
			"cash_debit": total_debit - auth_debit,
			"total_debit": total_debit,
			"billed_credit": auth_credit,
			"cash_credit": total_credit - auth_credit,
			"total_credit": total_credit,
			"billed_balance": auth_balance,
			"cash_balance": total_balance - auth_balance,
			"total_balance": total_balance,
	}]

	return data

# def get_closing(data):
# 	debit = credit = balance = qty = 0

# 	for item in data:
# 		debit += item.debit	 	
# 		credit += item.credit
# 		balance += item.balance
# 		qty += item.qty
	
# 	return [{'account': 'Closing', 'debit': debit, 'credit': credit, 'balance': balance, 'qty':qty}]

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
			IFNULL(si.authority, IFNULL(pi.authority, IFNULL(pe.authority,jv.authority))) as authority,
			IFNULL(si.si_ref, IFNULL(pi.pi_ref, pe.pe_ref)) as reference_doc{primary_customer_pe_fields}
		FROM
			`tabGL Entry` as gle
			LEFT JOIN `tabJournal Entry` as jv on jv.name = gle.voucher_no
			LEFT JOIN `tabSales Invoice` as si on si.name = gle.voucher_no
			LEFT JOIN `tabPurchase Invoice` as pi on pi.name = gle.voucher_no
			LEFT JOIN `tabPayment Entry` as pe on pe.name = gle.voucher_no
		WHERE
			(gle.transaction_status = 'New' or gle.transaction_status IS NULL)
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
	conditions =""
	company_placeholder_list = []
	if filters.company:
		company_placeholder_list.append(filters.company)
		alternate_company = [x.name for x in frappe.get_list("Company", {'alternate_company': filters.company}, 'name')]
		company_placeholder_list += alternate_company

		company_placeholder= ', '.join(f"'{i}'" for i in company_placeholder_list)
		conditions += (f"gle.company in ({company_placeholder})")

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
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 180,
			"hidden": 1
		},
		{
			"label": _("Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 80
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
			"label": _("Primary Customer"),
			"fieldname": "primary_customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 120
		},	
		{
			"label": _("Remark"),
			"fieldname": "remark",
			"fieldtype": "data",
			"width": 120
		},
		{
			"label": _("Create Account Reco Entry"),
			"fieldname": "create_account_reco_entry",
			"fieldtype": "button",
			"width": 120
		},
		
	]
	return columns

# Whatsapp Manager Start:

@frappe.whitelist()
def get_report_data_pdf(filters):
	report = frappe.get_doc("Report","Party Ledger Ceramic")
	filters = frappe.parse_json(filters) if filters else {}

	columns, data = report.get_data(user = frappe.session.user,
		filters = filters, as_dict=True, ignore_prepared_report=True)

	return columns, data


@frappe.whitelist()
def generate_report_pdf(html,filters):
	filters = json.loads(filters)
	filecontent = get_pdf(html,{"orientation":"Landscape"})
	pdf_hash = frappe.utils.generate_hash(length=10)
	try:
		primary_customer = filters['primary_customer']
	except:
		primary_customer = None
	if not primary_customer:
		file_name = "party_ledger_ceramic" + pdf_hash + ".pdf"
	else:
		file_name = primary_customer + pdf_hash + ".pdf"
	file_data = save_file(file_name, filecontent, "Report","Party Ledger Ceramic",is_private=1)
	return {"file_name":file_name,"file_url":file_data.file_url,'filters':filters}

@frappe.whitelist()
def whatsapp_login_check():
	user = frappe.db.get_value("User",{'default_user':1},'name')

	profiledir = os.path.join("./profiles/", "{}".format(user))
	if not os.path.exists(profiledir):
		os.makedirs(profiledir)

	options = webdriver.ChromeOptions()
	options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36")
	options.add_argument("--headless")
	options.add_argument("user-data-dir={}".format(os.path.join("./profiles/", "{}".format(frappe.session.user))))
	options.add_argument("--disable-infobars")
	options.add_argument("--disable-extensions")
	options.add_argument("--disable-crash-reporter")
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-gpu')
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--no-default-browser-check")
	driver = webdriver.Chrome(options=options,executable_path="/usr/local/bin/chromedriver")
	driver.get('https://web.whatsapp.com/')
	loggedin = False


	try:
		WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.two' + ',' + 'canvas')))
	except:
		ss_name_first =  'whatsapp error ' + frappe.session.user + 'first' +  frappe.generate_hash(length=5) +'.png'
		f_first = save_file(ss_name_first, '', '','')
		driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ f_first.file_name)
		error_log_first = frappe.log_error(frappe.get_traceback(),"Unable to connect your whatsapp")
		f_first.db_set('attached_to_doctype','Error Log')
		f_first.db_set('attached_to_name',error_log_first.name)
		frappe.db.commit()
		driver.quit()
		return False

	try:
		driver.find_element_by_css_selector('.two')
		loggedin = True
	except NoSuchElementException:
		element = driver.find_element_by_css_selector('canvas')
	except:
		ss_name_second =  'whatsapp error ' + frappe.session.user + 'second' + frappe.generate_hash(length=5) + '.png'
		f_second = save_file(ss_name_second, '', '','')
		driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ f_second.file_name)
		error_log_second = frappe.log_error(frappe.get_traceback(),"Unable to connect your whatsapp")
		f_second.db_set('attached_to_doctype','Error Log')
		f_second.db_set('attached_to_name',error_log_second.name)
		frappe.db.commit()
		driver.quit()
		return False

	if not loggedin:
		qr_hash = frappe.generate_hash(length = 15)
		path_private_files = frappe.get_site_path('public','files') + '/{}.png'.format(user + qr_hash)
		try:
			driver.find_element_by_css_selector('._1a-np')
			driver.find_element_by_name('rememberMe').click()
		except:
			pass
		try:
			WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'canvas')))
		except:
			ss_name_third =  'whatsapp error ' + frappe.session.user + 'third' + frappe.generate_hash(length=5) +'.png'
			f_third = save_file(ss_name_third, '', '','')
			driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ f_third.file_name)
			error_log_third = frappe.log_error(frappe.get_traceback(),"Unable to generate QRCode")
			f_third.db_set('attached_to_doctype','Error Log')
			f_third.db_set('attached_to_name',error_log_third.name)
			frappe.db.commit()
			driver.quit()
			return False

		try:
			driver.find_element_by_css_selector("div[data-ref] > span > div").click()
		except:
			pass

		png = driver.get_screenshot_as_png()
		qr = Image.open(BytesIO(png))
		qr = qr.crop((element.location['x'], element.location['y'], element.location['x'] + element.size['width'], element.location['y'] + element.size['height']))
		qr.save(path_private_files)
		msg = "<img src='/files/{}.png' alt='No Image' data-pagespeed-no-transform>".format(frappe.session.user + qr_hash)
		event = str('Party Ledger Ceramic' + frappe.session.user)
		frappe.publish_realtime(event=event, message=msg,user=frappe.session.user)


		try:
			WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.two')))
			driver.quit()
			remove_qr_code(user,qr_hash)
			frappe.db.set_value("System Settings","System Settings","default_login",1)
			# return [driver,user,qr_hash]
		except:
			ss_name_fourth =  'whatsapp error ' + frappe.session.user + 'fourth' + frappe.generate_hash(length=5) + '.png'
			f_fourth = save_file(ss_name_fourth, '', '','')
			driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ f_fourth.file_name)
			error_log_fourth = frappe.log_error(frappe.get_traceback(),"Unable to Save Profile.")
			f_fourth.db_set('attached_to_doctype','Error Log')
			f_fourth.db_set('attached_to_name',error_log_fourth.name)
			frappe.db.commit()
			driver.quit()
			remove_qr_code(user,qr_hash)
			return False
	else:
		# return [driver,user]
		driver.quit()
		frappe.db.set_value("System Settings","System Settings","default_login",1)


@frappe.whitelist()
def get_report_pdf_whatsapp(mobile_number,content,file_url,file_name,filters):
	if mobile_number.find(" ") != -1:
		mobile_number = mobile_number.replace(" ","")
	if mobile_number.find("+") != -1:
		mobile_number = mobile_number.replace("+","")
	if mobile_number[0] == '9' and mobile_number[1] == '1':
		mobile_number = mobile_number[2:]
	if len(mobile_number) != 10:
		frappe.throw("Please Enter Only 10 Digit Contact Number.")

	# if frappe.db.get_value("System Settings","System Settings","default_login") == '0':
		# whatsapp_login_check()
	# send_msg_background(mobile_number, content, file_url,file_name,filters)
	frappe.enqueue(send_whatsapp_report,queue= "long",mobile_number = mobile_number, content = content, file_url = file_url, file_name = file_name, filters = filters)

def send_whatsapp_report(mobile_number, content, file_url,file_name,filters):
	filters = json.loads(filters)
	path = frappe.get_site_path('private','files') + "/" + file_name
	path_url = frappe.utils.get_bench_path() + "/sites" + path[1:]

	send_msg = send_media_whatsapp(mobile_number,content,path_url)

	if send_msg == True:
		comment_whatsapp = frappe.new_doc("Comment")
		comment_whatsapp.comment_type = "WhatsApp"
		comment_whatsapp.comment_email = frappe.session.user
		comment_whatsapp.reference_doctype = "Customer"
		comment_whatsapp.reference_name = filters.get('primary_customer')

		comment_whatsapp.content = "You Have Sent the Whatsapp Message To: " + str(mobile_number) + " At: " + now()

		comment_whatsapp.save(ignore_permissions=True)

		doc = frappe.get_doc("Whatsapp Comment")
		message_info = "You Have Sent the Whatsapp Message To: " + str(mobile_number) + " At: " + now()
		doc.append("whatsapp_details",{"company":filters.get('company'),"from_date":filters.get('from_date'),\
			"to_date":filters.get('to_date'),"primary_customer":filters.get('primary_customer'),\
			"message_info":message_info,"message":str(content)})
		doc.save(ignore_permissions=True)

	remove_file_from_os(path)

	frappe.db.sql("delete from `tabFile` where file_name='{}'".format(file_name))
	frappe.db.sql("delete from `tabComment` where reference_doctype='{}' and reference_name='{}' and comment_type='Attachment' and content LIKE '%{}%'"
		.format('Report','Party Ledger Ceramic',file_name))

	frappe.db.commit()
	if not send_msg == True and send_msg:
		return str(get_url_to_form("Error Log", str(send_msg)))

def send_media_whatsapp(mobile_number,content,path_url):
	user = frappe.db.get_value("User",{'default_user':1},'name')
	if len(mobile_number) == 10:
		mobile_number = "91" + mobile_number

	profiledir = os.path.join("./profiles/", "{}".format(user))
	if not os.path.exists(profiledir):
		os.makedirs(profiledir)

	options = webdriver.ChromeOptions()
	options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36")
	options.add_argument("--headless")
	options.add_argument("user-data-dir={}".format(os.path.join("./profiles/", "{}".format(user))))
	options.add_argument("--disable-infobars")
	options.add_argument("--disable-extensions")
	options.add_argument("--disable-crash-reporter")
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-gpu')
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--no-default-browser-check")
	driver = webdriver.Chrome(options=options,executable_path="/usr/local/bin/chromedriver")
	driver.get('https://web.whatsapp.com/')
	loggedin = False

	try:
		WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.two' + ',' + 'canvas')))
	except:
		ss_name_first =  'whatsapp error ' + frappe.session.user + 'first' +  frappe.generate_hash(length=5) +'.png'
		# f_first = save_file(ss_name_first, '', '','')
		driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_first)
		error_log_first = frappe.log_error(frappe.get_traceback(),"Unable to connect your whatsapp")
		f_first = frappe.new_doc("File")
		f_first.file_url = "/files/"+ss_name_first
		f_first.attached_to_doctype = 'Error Log'
		f_first.attached_to_name = error_log_first.name
		f_first.flags.ignore_permissions = True
		f_first.insert()
		frappe.db.set_value("System Settings","System Settings","default_login",0)
		frappe.db.commit()
		driver.quit()
		return error_log_first.name

	try:
		driver.find_element_by_css_selector('.two')
		loggedin = True
	except NoSuchElementException:
		element = driver.find_element_by_css_selector('canvas')
	except:
		ss_name_second =  'whatsapp error ' + frappe.session.user + 'second' + frappe.generate_hash(length=5) + '.png'
		# f_second = save_file(ss_name_second, '', '','')
		driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_second)
		error_log_second = frappe.log_error(frappe.get_traceback(),"Unable to connect your whatsapp")
		f_first = frappe.new_doc("File")
		f_first.file_url = "/files/"+ss_name_second
		f_first.attached_to_doctype = 'Error Log'
		f_first.attached_to_name = error_log_second.name
		f_first.flags.ignore_permissions = True
		f_first.insert()
		frappe.db.set_value("System Settings","System Settings","default_login",0)
		frappe.db.commit()
		driver.quit()
		return error_log_second.name
	
	if not loggedin:
		qr_hash = frappe.generate_hash(length = 15)
		path_private_files = frappe.get_site_path('public','files') + '/{}.png'.format(frappe.session.user + qr_hash)
		try:
			driver.find_element_by_css_selector('._1a-np')
			driver.find_element_by_name('rememberMe').click()
		except:
			pass
		try:
			WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'canvas')))
		except:
			ss_name_third =  'whatsapp error ' + frappe.session.user + 'third' + frappe.generate_hash(length=5) +'.png'
			# f_third = save_file(ss_name_third, '', '','')
			driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_third)
			error_log_third = frappe.log_error(frappe.get_traceback(),"Unable to generate QRCode in whatsapp.")
			f_first = frappe.new_doc("File")
			f_first.file_url = "/files/"+ss_name_third
			f_first.attached_to_doctype = 'Error Log'
			f_first.attached_to_name = error_log_third.name
			f_first.flags.ignore_permissions = True
			f_first.insert()
			frappe.db.commit()
			driver.quit()
			return error_log_third.name

		try:
			driver.find_element_by_css_selector("div[data-ref] > span > div").click()
		except:
			pass

		png = driver.get_screenshot_as_png()
		qr = Image.open(BytesIO(png))
		qr = qr.crop((element.location['x'], element.location['y'], element.location['x'] + element.size['width'], element.location['y'] + element.size['height']))
		qr.save(path_private_files)
		msg = "<img src='/files/{}.png' alt='No Image' data-pagespeed-no-transform>".format(frappe.session.user + qr_hash)
		event = str('Party Ledger Ceramic' + frappe.session.user)
		frappe.publish_realtime(event=event, message=msg,user=frappe.session.user)


		try:
			WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.two')))
			# driver.quit()
			# remove_qr_code(user,qr_hash)
			frappe.db.set_value("System Settings","System Settings","default_login",1)
			# return [driver,user,qr_hash]
		except:
			ss_name_fourth =  'whatsapp error ' + frappe.session.user + 'fourth' + frappe.generate_hash(length=5) + '.png'
			# f_fourth = save_file(ss_name_fourth, '', '','')
			driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_fourth)
			error_log_fourth = frappe.log_error(frappe.get_traceback(),"Unable to Save Profile in whatsapp.")
			f_first = frappe.new_doc("File")
			f_first.file_url = "/files/"+ss_name_fourth
			f_first.attached_to_doctype = 'Error Log'
			f_first.attached_to_name = error_log_fourth.name
			f_first.flags.ignore_permissions = True
			f_first.insert()
			frappe.db.commit()
			driver.quit()
			remove_qr_code(user,qr_hash)
			return error_log_fourth.name

	link = "https://web.whatsapp.com/send?phone='{}'&text&source&data&app_absent".format(mobile_number)
	driver.get(link)
	attach_list = []

	if content:
		try:
			WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '._1LbR4')))	
		except:
			ss_name_sixth_1 = 'whatsapp error ' + frappe.session.user + 'sixth 1' + frappe.generate_hash(length=5) +  '.png'
			# f_sixth_1 = save_file(ss_name_sixth_1, '', '','')
			driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_sixth_1)
			error_log_sixth_1 = frappe.log_error(frappe.get_traceback(),"Unable to send the whatsapp message")
			f_first = frappe.new_doc("File")
			f_first.file_url = "/files/"+ss_name_sixth_1
			f_first.attached_to_doctype = 'Error Log'
			f_first.attached_to_name = error_log_sixth_1.name
			f_first.flags.ignore_permissions = True
			f_first.insert()
			frappe.db.commit()
			driver.quit()
			return error_log_sixth_1.name
		# try:
		# 	WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main"]/footer/div[1]/div[2]/div/div[2]')))
		# except:
		# 	ss_name_sixth_1 = 'whatsapp error ' + frappe.session.user + 'sixth 1' + frappe.generate_hash(length=5) +  '.png'
		# 	f_sixth_1 = save_file(ss_name_sixth_1, '', '','')
		# 	driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ f_sixth_1.file_name)
		# 	error_log_sixth_1 = frappe.log_error(frappe.get_traceback(),"Unable to send the whatsapp message")
		# 	f_sixth_1.db_set('attached_to_doctype','Error Log')
		# 	f_sixth_1.db_set('attached_to_name',error_log_sixth_1.name)
		# 	frappe.db.commit()
		# 	driver.quit()
		# 	return False
		try:
			input_box = driver.find_element_by_css_selector('._1LbR4')
			input_box.send_keys(content)
			driver.find_element_by_css_selector('._1Ae7k').click()
		except:
			ss_name_sixth =  'whatsapp error ' + frappe.session.user + 'sixth' + frappe.generate_hash(length=5) +  '.png'
			# f_sixth = save_file(ss_name_sixth, '', '','')
			driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_sixth)
			error_log_sixth = frappe.log_error(frappe.get_traceback(),"Error while trying to send the media file in whatsapp.")
			f_first = frappe.new_doc("File")
			f_first.file_url = "/files/"+ss_name_sixth
			f_first.attached_to_doctype = 'Error Log'
			f_first.attached_to_name = error_log_sixth.name
			f_first.flags.ignore_permissions = True
			f_first.insert()
			frappe.db.commit()
			driver.quit()
			return error_log_sixth.name 
	try:
		WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'span[data-icon="clip"]')))
		WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'span[data-icon="clip"]')))
		driver.find_element_by_css_selector('span[data-icon="clip"]').click()
		attach=driver.find_element_by_css_selector('input[type="file"]')
		attach.send_keys(path_url)

		WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="app"]/div/div/div[2]/div[2]/span/div/span/div/div/div[2]/span/div/div')))
		whatsapp_send_button = driver.find_element_by_xpath('//*[@id="app"]/div/div/div[2]/div[2]/span/div/span/div/div/div[2]/span/div/div')
		whatsapp_send_button.click()
	except:
		ss_name_eight =  'whatsapp error ' + frappe.session.user + 'eight' + frappe.generate_hash(length=5) +  '.png'
		# f_eight = save_file(ss_name_eight, '', '','')
		driver.save_screenshot(frappe.get_site_path('public','files') + '/'+ ss_name_eight)
		error_log_eight = frappe.log_error(frappe.get_traceback(),"Error while trying to send the whatsapp message.")
		f_first = frappe.new_doc("File")
		f_first.file_url = "/files/"+ss_name_eight
		f_first.attached_to_doctype = 'Error Log'
		f_first.attached_to_name = error_log_eight.name
		f_first.flags.ignore_permissions = True
		f_first.insert()
		frappe.db.commit()
		driver.quit()
		return error_log_eight.name
	time.sleep(30)
	driver.quit()
	return True

def remove_file_from_os(path):
	if os.path.exists(path):
		os.remove(path)

def remove_qr_code(user,qr_hash):
	qr_path = frappe.get_site_path('public','files') + "/{}.png".format(user + qr_hash)
	remove_file_from_os(qr_path)

# Whatsapp Manager End

@frappe.whitelist()
def create_account_reco_entry(posting_date,company,alternate_company,alternate_account,account,reconciled_amount,alternate_reconciled_amount,party_type,party):
	doc = frappe.new_doc("Account Reco")
	doc.posting_date = posting_date
	doc.company = company
	doc.account = account
	doc.reconciled_amount = reconciled_amount
	doc.party_type = party_type
	doc.party = party
	doc.save(ignore_permissions=True)
	doc.submit()

	doc2 = frappe.new_doc("Account Reco")
	doc2.posting_date = posting_date
	doc2.company = alternate_company
	doc2.reconciled_amount = alternate_reconciled_amount
	doc2.account = alternate_account
	doc2.party_type = party_type
	doc2.party = party
	doc2.save(ignore_permissions=True)
	doc2.submit()

	frappe.msgprint('Transactions has been cancelled')
