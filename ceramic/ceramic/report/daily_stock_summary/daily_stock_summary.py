# Copyright (c) 2013, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, flt
from frappe.utils.background_jobs import enqueue, get_jobs

from datetime import timedelta, date
import datetime
from itertools import zip_longest

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_dates(filters):
	# This Function will return list of date between given from date and to date
	date_list = []
	delta = timedelta(days=1)
	for date in daterange(getdate(filters.get('from_date')), getdate(filters.get('to_date'))):
		date_list.append(date)
	return date_list


def get_data(filters):
	# stop execution if Item group or Item is not selected
	if not filters.get("item_code") and not filters.get("item_group"):
		frappe.throw("Item code or Item group has to be selected to generate the report")

	# stop execution if company is not authorized
	if frappe.db.get_value("Company",filters.get('company'),'authority') != "Authorized":
		frappe.throw("Please Select Correct Company")

	date_list = get_dates(filters)
	opening_data = get_opening_data(filters,date_list)
	inward_data = get_inward_data(filters,date_list)
	outward_data = get_outward_data(filters,date_list)
	data = [{**u, **v, **m } for u, v, m in zip_longest(opening_data, inward_data, outward_data, fillvalue={})]

	for idx,row in enumerate(data):
		if idx != 0:
			row['opening'] = flt(str(data[idx-1].get('closing')))
		row['total_inward'] = flt(str(row.get('opening'))) + flt(row.get('production')) + flt(row.get('purchase'))
		row['closing'] = flt(str(row.get('total_inward'))) - flt(flt(str(row.get('outward'))) + flt(str(row.get('domestic'))) + flt(str(row.get('export'))))
	
		if filters.get('item_code'):
			row['stock_entry'] = """<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
						type='button' date='{date}' item_code='{item_code}' company='{company}' 
						onClick=create_production_entry(this.getAttribute('date'),this.getAttribute('item_code'),this.getAttribute('company'))>Production</button>
						""".format(date=row['date'],item_code=filters.get('item_code'),company=filters.get('company'))
	return data

def get_opening_data(filters,date_list):
	conditions, groupby_cond = get_sle_conditions(filters)

	opening_query = frappe.db.sql("""
		select 
			sum(sle.actual_qty) as opening_qty
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
		where 
			sle.is_cancelled = 0 and sle.company = '{company}' and sle.posting_date < '{from_date}' {conditions}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),
			conditions=conditions),as_dict=1)

	opening_map = {}
	for opening in opening_query:
		if filters.get('from_date') not in opening_map:
			opening_map[filters.get('from_date')] = flt(opening.opening_qty)

	opening_data = []
	for date in date_list[:1]:
			opening_data.append({"date":date,"opening":opening_query[0]['opening_qty']})
	return opening_data

def get_inward_data(filters,date_list):
	# This Function will give Inward Data From Stock Entry(purpose - 'Material Receipt') and Purchase Receipt and Purchase Invoice

	conditions, groupby_cond = get_sle_conditions(filters)

	production_query = frappe.db.sql("""
		select 
			sum(sle.actual_qty) as actual_qty, sle.posting_date
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabStock Entry` as se on se.name = sle.voucher_no
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
		where 
			sle.is_cancelled = 0 and sle.actual_qty > 0 and se.stock_entry_type = 'Production' and
			sle.company = '{company}' and sle.posting_date between '{from_date}' and '{to_date}' {conditions}
		group by sle.posting_date{groupby_cond}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),to_date=filters.get('to_date'),
			conditions=conditions,groupby_cond=groupby_cond),as_dict=1)


	se_receipt_query = frappe.db.sql("""
		select 
			sum(sle.actual_qty) as actual_qty, sle.posting_date
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabStock Entry` as se on se.name = sle.voucher_no
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
		where 
			sle.is_cancelled = 0 and sle.actual_qty > 0 and se.purpose = 'Material Receipt' and se.stock_entry_type != 'Production' and
			sle.company = '{company}' and sle.posting_date between '{from_date}' and '{to_date}' {conditions}
		group by sle.posting_date{groupby_cond}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),to_date=filters.get('to_date'),
			conditions=conditions,groupby_cond=groupby_cond),as_dict=1)

	purchase_query = frappe.db.sql("""
		select 
			sum(sle.actual_qty) as actual_qty, sle.posting_date
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
		where 
			sle.is_cancelled = 0 and sle.actual_qty > 0 and sle.voucher_type in ('Purchase Receipt','Purchase Invoice') and
			sle.company = '{company}' and sle.posting_date between '{from_date}' and '{to_date}' {conditions}
		group by sle.posting_date{groupby_cond}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),to_date=filters.get('to_date'),
			conditions=conditions,groupby_cond=groupby_cond),as_dict=1)


	inward_production_map, inward_purchase_map, inward_se_receipt_map= {},{},{}
	for sle in production_query:
		if sle.posting_date not in inward_production_map:
			inward_production_map[sle.posting_date] = flt(sle.actual_qty)
		else:
			inward_production_map[sle.posting_date] += flt(sle.actual_qty)

	for sle in se_receipt_query:
		if sle.posting_date not in inward_se_receipt_map:
			inward_se_receipt_map[sle.posting_date] = flt(sle.actual_qty)
		else:
			inward_se_receipt_map[sle.posting_date] += flt(sle.actual_qty)

	for sle in purchase_query:
		if sle.posting_date not in inward_purchase_map:
			inward_purchase_map[sle.posting_date] = flt(sle.actual_qty)
		else:
			inward_purchase_map[sle.posting_date] += flt(sle.actual_qty)

	inward_data = []
	for date in date_list:
		qty_map = {}

		if inward_production_map.get(date):
			qty_map.update({"production":inward_production_map[date]})
		else:
			qty_map.update({"production":0})

		if inward_se_receipt_map.get(date):
			qty_map.update({"se_receipt":inward_se_receipt_map[date]})
		else:
			qty_map.update({"se_receipt":0})

		if inward_purchase_map.get(date):
			qty_map.update({"purchase":inward_purchase_map[date]})
		else:
			qty_map.update({"purchase":0})
		inward_data.append({"date":date,"production":qty_map['production'],"inward":qty_map['purchase']+qty_map['se_receipt']})

	return inward_data


def get_outward_data(filters,date_list):
	# This Function will give Outward Data From Stock Entry(purpose - 'Material Issue') and
	# 		 Sales Invoice(there will be 2 queries in first it will fetch data where invoice doesnt considered as export type of invoice
	# 							and in second it will fetch data where invoice considered as export type of invoice)

	conditions, groupby_cond = get_sle_conditions(filters)

	outward_se_query = frappe.db.sql("""
		select 
			sum(ABS(sle.actual_qty)) as actual_qty, sle.posting_date
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabStock Entry` as se on se.name = sle.voucher_no
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
		where 
			sle.is_cancelled = 0 and sle.actual_qty < 0 and se.purpose = 'Material Issue' and
			sle.company = '{company}' and sle.posting_date between '{from_date}' and '{to_date}' {conditions}
		group by sle.posting_date{groupby_cond}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),to_date=filters.get('to_date'),
			conditions=conditions,groupby_cond=groupby_cond),as_dict=1)


	outward_sell_query = frappe.db.sql("""
		select 
			sum(ABS(sle.actual_qty)) as actual_qty, sle.posting_date, sum(sii.net_amount) as taxable_value
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
			LEFT JOIN `tabSales Invoice` as si on si.name = sle.voucher_no
			LEFT JOIN `tabSales Invoice Item` as sii on sii.name = sle.voucher_detail_no
		where 
			sle.is_cancelled = 0 and sle.actual_qty < 0 and (si.gst_category not in ('Deemed Export','Overseas')
			or (si.gst_category in ('Deemed Export','Overseas') and si.export_type = 'Without Payment of Tax')
			or (si.gst_category is null or si.gst_category = '')) and
			sle.company = '{company}' and sle.posting_date between '{from_date}' and '{to_date}' {conditions}
		group by sle.posting_date{groupby_cond}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),to_date=filters.get('to_date'),
			conditions=conditions,groupby_cond=groupby_cond),as_dict=1)

	outward_sell_export_query = frappe.db.sql("""
		select 
			sum(ABS(sle.actual_qty)) as actual_qty, sle.posting_date, sum(sii.net_amount) as taxable_value
		from 
			`tabStock Ledger Entry` as sle
			LEFT JOIN `tabItem` as i on i.name = sle.item_code
			LEFT JOIN `tabSales Invoice` as si on si.name = sle.voucher_no
			LEFT JOIN `tabSales Invoice Item` as sii on sii.name = sle.voucher_detail_no
		where 
			sle.is_cancelled = 0 and sle.actual_qty < 0 and si.gst_category in ('Deemed Export','Overseas') and si.export_type = 'With Payment of Tax' and
			sle.company = '{company}' and sle.posting_date between '{from_date}' and '{to_date}' {conditions}
		group by sle.posting_date{groupby_cond}
	""".format(company = filters.get('company'),from_date=filters.get('from_date'),to_date=filters.get('to_date'),
			conditions=conditions,groupby_cond=groupby_cond),as_dict=1)

	outward_se_map, outward_sell_map, outward_sell_export_map,taxable_value_map= {},{},{},{}
	for sle in outward_se_query:
		if sle.posting_date not in outward_se_map:
			outward_se_map[sle.posting_date] = flt(sle.actual_qty)
		else:
			outward_se_map[sle.posting_date] += flt(sle.actual_qty)

	for sle in outward_sell_query:
		if sle.posting_date not in outward_sell_map:
			outward_sell_map[sle.posting_date] = flt(sle.actual_qty)
		else:
			outward_sell_map[sle.posting_date] += flt(sle.actual_qty)

		if sle.posting_date not in taxable_value_map:
			taxable_value_map[sle.posting_date] = flt(sle.taxable_value)
		else:
			taxable_value_map[sle.posting_date] += flt(sle.taxable_value)

	for sle in outward_sell_export_query:
		if sle.posting_date not in outward_sell_export_map:
			outward_sell_export_map[sle.posting_date] = flt(sle.actual_qty)
		else:
			outward_sell_export_map[sle.posting_date] += flt(sle.actual_qty)

		if sle.posting_date not in taxable_value_map:
			taxable_value_map[sle.posting_date] = flt(sle.taxable_value)
		else:
			taxable_value_map[sle.posting_date] += flt(sle.taxable_value)

	outward_data = []
	for date in date_list:
		qty_map = {}

		if outward_se_map.get(date):
			qty_map.update({"outward":outward_se_map[date]})
		else:
			qty_map.update({"outward":0})

		if outward_sell_map.get(date):
			qty_map.update({"domestic":outward_sell_map[date]})
		else:
			qty_map.update({"domestic":0})

		if outward_sell_export_map.get(date):
			qty_map.update({"export":outward_sell_export_map[date]})
		else:
			qty_map.update({"export":0})

		if taxable_value_map.get(date):
			qty_map.update({"taxable_value":taxable_value_map[date]})
		else:
			qty_map.update({"taxable_value":0})


		outward_data.append({"date":date,"outward":qty_map['outward'],"domestic":qty_map['domestic'],"export":qty_map['export'],
			"taxable_value":qty_map['taxable_value'],"gst_percent":18,"gst_amount":18*qty_map['taxable_value']})

	return outward_data

def get_sle_conditions(filters):
	conditions = ''
	groupby_cond = ', i.item_group'
	if filters.get("item_group"):
		conditions += " and i.item_group = '{}'".format(filters.get("item_group"))
		
	if filters.get("item_code"):
		conditions += " and sle.item_code = '{}'".format(filters.get("item_code"))
		groupby_cond = ', sle.item_code'
	return conditions, groupby_cond

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def get_columns(filters):
	columns = [
	{
		"fieldname": "date",
		"label": ("Date"),
		"fieldtype": "Date",
		"width": 100
	},
	{
		"fieldname": "opening",
		"label": ("Opening"),
		"fieldtype": "Float",
		"width": 120
	},
	{
		"fieldname": "production",
		"label": ("Production"),
		"fieldtype": "Float",
		"width": 120
	},
	{
		"fieldname": "stock_entry",
		"label": ("Stock Entry"),
		"fieldtype": "Button",
		"width": 100
	},
	{
		"fieldname": "inward",
		"label": ("Inward"),
		"fieldtype": "Float",
		"width": 100
	},
	{
		"fieldname": "total_inward",
		"label": ("Total"),
		"fieldtype": "Float",
		"width": 120
	},
	{
		"fieldname": "outward",
		"label": ("Outward"),
		"fieldtype": "Float",
		"width": 100
	},
	{
		"fieldname": "domestic",
		"label": ("Domestic"),
		"fieldtype": "Float",
		"width": 100
	},
	{
		"fieldname": "export",
		"label": ("Export"),
		"fieldtype": "Float",
		"width": 100
	},
	{
		"fieldname": "closing",
		"label": ("Closing"),
		"fieldtype": "Float",
		"width": 120
	},
	{
		"fieldname": "taxable_value",
		"label": ("Taxable Value"),
		"fieldtype": "Float",
		"width": 120
	},
	{
		"fieldname": "gst_percent",
		"label": ("GST%"),
		"fieldtype": "Float",
		"width": 80
	},
	{
		"fieldname": "gst_amount",
		"label": ("GSR Rs."),
		"fieldtype": "Float",
		"width": 120
	},
	]
	return columns

@frappe.whitelist()
def _create_stock_entry(date,item_code,company,se_qty):
	# this function is used to enqueue creation of stock entry
	warehouse = frappe.db.get_value("Company",company,"default_warehouse_for_production")
	if not warehouse:
		frappe.throw("Please Enter Default Warehouse for Production in this Company: {}".format(frappe.bold(company)))

	item_group = frappe.db.get_value("Item", item_code,'item_group')
	rate = frappe.db.get_value("Item Group",item_group,'production_price')
	if not rate:
		frappe.throw("Please Enter Rate in this Item group:{}".format(frappe.bold(item_group)))

	queued_jobs = get_jobs(site = frappe.local.site,key='job_name')[frappe.local.site]
	job = "Production Stock Entry" + company + " " + item_code + " " + se_qty
	if job not in queued_jobs:
		frappe.msgprint(_(" The Stock Entry has been queued in background jobs."),title=_(' Stock Entry creation job is in Queue '),indicator="green")
		enqueue(create_stock_entry,queue= "default", timeout= 300, job_name= job, date= date, company= company, item_code= item_code, warehouse= warehouse,se_qty=se_qty,rate=rate)
	else:
		frappe.msgprint(_(" Stock Entry Creation is already in queue."),title=_(' Stock Entry creation job is Already in Queue '),indicator="green")			
	
def create_stock_entry(date,company,item_code,warehouse,se_qty,rate):
	# If any production entry is exists for given date then delete all entries if that date
	stock_exists = frappe.db.sql("""
		select se.name from `tabStock Entry` as se
		JOIN `tabStock Entry Detail` as see on see.parent = se.name
		where se.stock_entry_type = 'Production' and se.posting_date = '{}' and see.item_code = '{}' and se.company = '{}'
	""".format(date,item_code,company),as_dict=1)

	if stock_exists:
		# doc_list = frappe.db.get_list("Stock Entry",fields=["name"],filters={"stock_entry_type":"Production","posting_date":date})
		for se_doc in stock_exists:
			doc = frappe.get_doc("Stock Entry",se_doc.name)
			doc.flags.ignore_permissions = True
			if doc.docstatus == 1:
				try:
					doc.cancel()
					doc.delete()
				except Exception as e:
					frappe.throw(_(str(e)))
			else:
				doc.delete()	

	# Create New Production Entry on given date
	se = frappe.new_doc('Stock Entry')
	se.stock_entry_type = 'Production'
	se.company = company
	expense_account, cost_center = frappe.db.get_value("Company",company,["stock_adjustment_account","cost_center"])
	se.posting_date = date
	se.set_posting_time = 1
	se.append('items',{
		"t_warehouse":warehouse,
		"item_code":item_code,
		"qty":se_qty,
		"basic_rate":rate,
		"expense_account":expense_account,
		"cost_center":cost_center
	})
	se.save(ignore_permissions=True)
	se.submit()
