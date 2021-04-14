# Copyright (c) 2013, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import re

def execute(filters=None):
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters)
	
	return columns, data

def get_columns(filters):
	"""return columns"""
	columns = [
		{"label": _("Customer Name"), "fieldname": "name", "fieldtype": "Link","options":"Customer","width": 170},
		{"label": _("Customer Alias"), "fieldname": "customer_alias", "fieldtype": "Data","width": 120},
		{"label": _("Territory"), "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 100},
		{"label": _("Type"), "fieldname": "customer_type", "fieldtype": "Data", "width": 100},
		{"label": _("Customer Group"), "fieldname": "customer_group", "fieldtype": "Link", "options": "Customer Group","width": 100},
		{"label": _("Size of Business"), "fieldname": "size_of_business", "fieldtype": "Data", "width": 90},
		{"label": _("Payment Performance OR Relations"), "fieldname": "payment_performance_or_relations", "fieldtype": "Data", "width": 90},
		{"label": _("Cash And Carry"), "fieldname": "cash_and_carry", "fieldtype": "Check", "width": 90},
		{"label": _("Primary Customer"), "fieldname": "primary_customer", "fieldtype": "Link", "options": "Customer","width": 90},
		{"label": _("Reference, Reviews and Other Information"), "fieldname": "reference_reviews_and_other_information", "fieldtype": "Small Text", "width": 90},
	]
	if filters.get('show_detail'):
		columns += [
			{"label": _("Sales Head"), "fieldname": "sales_person", "fieldtype": "Link", "options": "Sales Person","width": 100},
			{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company","width": 100},
			{"label": _("Regional Sales Manager"), "fieldname": "regional_sales_manager", "fieldtype": "Link", "options": "Sales Person","width": 100},
			{"label": _("Dispatch Person"), "fieldname": "sales_manager", "fieldtype": "Link", "options": "Sales Person","width": 100},
		]
	if filters.get('show_contact'):
		columns += [
			{"label": _("Full Name"), "fieldname": "full_name", "fieldtype": "Data","width": 100},
			{"label": _("Mobile No"), "fieldname": "mobile_no", "fieldtype": "Data","width": 100},
			{"label": _("Email"), "fieldname": "email_id", "fieldtype": "Data","width": 100},
			{"label": _("Unsubscribed"), "fieldname": "unsubscribed", "fieldtype": "Check","width": 50}
		]
	return columns

def get_data(filters):
	conditions = ''

	if filters.get('customer'):
		conditions += " and c.name = '%s'" %(filters.get('customer'))

	if filters.get("territory"):
		territory_details = frappe.db.get_value("Territory",
			filters.get("territory"), ["lft", "rgt"], as_dict=1)
		if territory_details:
			conditions += " and exists (select name from `tabTerritory` t \
				where t.lft >= %s and t.rgt <= %s and c.territory = t.name)"%(territory_details.lft,
				territory_details.rgt)
				
	if filters.get("customer_group"):
		customer_group_details = frappe.db.get_value("Customer Group",
			filters.get("customer_group"), ["lft", "rgt"], as_dict=1)
		if customer_group_details:
			conditions += " and exists (select name from `tabCustomer_group` t \
				where t.lft >= %s and t.rgt <= %s and c.customer_group = t.name)"%(customer_group_details.lft,
				customer_group_details.rgt)

	data = frappe.db.sql("""
			SELECT c.name, c.customer_name, c.customer_alias, c.territory, c.customer_type, c.customer_group,
				c.size_of_business, c.payment_performance_or_relations, c.cash_and_carry, c.primary_customer, c.reference_reviews_and_other_information
				
			FROM `tabCustomer` as c 
			WHERE c.disabled = 0 %s
			""" %(conditions), as_dict=1)
	
	if filters.get('show_detail') and not filters.get('show_contact'):
		sales_data_map= get_sales_details()
		for row in data:
			if sales_data_map.get(row.name):
				row.update(sales_data_map[row.name])

	if filters.get('show_contact') and not filters.get('show_detail'):
		contact_data_map = get_contact_details()
		for row in data:
			if contact_data_map.get(row.name):
				row.update(contact_data_map[row.name])

	if filters.get('show_contact') and filters.get('show_detail'):
		sales_data_map= get_sales_details()
		contact_data_map = get_contact_details()
		for row in data:
			if sales_data_map.get(row.name):
				row.update(sales_data_map[row.name])
			if contact_data_map.get(row.name):
				row.update(contact_data_map[row.name])

	return data

def get_sales_details():
	sales_data = frappe.db.sql("""
		SELECT st.parent,st.sales_person, st.company, st.regional_sales_manager, st.sales_manager
		FROM `tabSales Team` as st where st.parenttype = "Customer"
	""",as_dict=1)
	sales_data_map = {}
	for row in sales_data:
		sales_data_map.setdefault(row.parent),frappe._dict({})
		sales_data_map[row.parent] = row

	return sales_data_map

def get_contact_details():
	contact_data = frappe.db.sql("""
		SELECT dl.link_name,CONCAT_WS(" ",contact.first_name, contact.middle_name, contact.last_name) as full_name ,contact.mobile_no, contact.email_id,contact.unsubscribed
		FROM `tabDynamic Link` as dl
		RIGHT JOIN `tabContact` as contact on (contact.name = dl.parent)
	""",as_dict=1)
	contact_data_map = {}
	for row in contact_data:
		contact_data_map.setdefault(row.link_name, row)
	
	return contact_data_map
