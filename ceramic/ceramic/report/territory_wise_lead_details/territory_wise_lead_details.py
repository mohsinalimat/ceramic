# Copyright (c) 2013, Finbyz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters)
	
	return columns, data

def get_columns(filters):
	"""return columns"""
	columns = [
		{"label": _("Name"), "fieldname": "name", "fieldtype": "Link","options":"Lead","width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data","width": 100},
		{"label": _("Person Name"), "fieldname": "lead_name", "fieldtype": "Data","width": 170},
		{"label": _("Territory"), "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 100},
		{"label": _("Parent Territory"), "fieldname": "parent_territory", "fieldtype": "Link", "options": "Territory", "width": 100},
		{"label": _("State"), "fieldname": "state", "fieldtype": "Data", "width": 100},
		{"label": _("Customer Group"), "fieldname": "customer_group", "fieldtype": "Link", "options": "Customer Group","width": 100},
		{"label": _("Size of Business"), "fieldname": "size_of_business", "fieldtype": "Data", "width": 90},
		{"label": _("Cash And Carry"), "fieldname": "cash_and_carry", "fieldtype": "Check", "width": 90},
		{"label": _("Reference, Reviews and Other Information"), "fieldname": "reference_reviews_and_other_information", "fieldtype": "Small Text", "width": 90},
		{"label": _("Payment Performance OR Relations"), "fieldname": "payment_performance_or_relations", "fieldtype": "Data", "width": 90},
		{"label": _("Source"), "fieldname": "source", "fieldtype": "Link", "options": "Lead Source", "width": 100},
		{"label": _("Current/Previously worked with Company"), "fieldname": "previously_worked_with", "fieldtype": "Link", "options": "Previous Details Item", "width": 100},
		{"label": _("Lead Owner"), "fieldname": "lead_owner", "fieldtype": "Link", "options": "User","width": 90},
		{"label": _("Mobile No (Whatsapp)"), "fieldname": "phone", "fieldtype": "Data", "width": 110},
		{"label": _("Mobile No 1"), "fieldname": "mobile_no", "fieldtype": "Data", "width": 110},
		{"label": _("Phone/Mobile No 2"), "fieldname": "fax", "fieldtype": "Data", "width": 110},
	]
	if filters.get('show_product'):
		columns += [{"label": _("Products Looking For"), "fieldname": "products_looking_for", "fieldtype": "Link", "options": "Product Looking For Details","width": 100}]

	return columns

def get_data(filters):
	conditions = ''

	if filters.get("lead_owner"):
		lead_owner_placeholder= ', '.join(f"'{i}'" for i in filters["lead_owner"])
		conditions += " and l.lead_owner in (%s)" % lead_owner_placeholder

	if filters.get("size_of_business"):
		conditions +=  " and l.size_of_business = '%s'" %(filters.get('size_of_business'))

	if filters.get("territory"):
		territory_details = frappe.db.get_value("Territory",
			filters.get("territory"), ["lft", "rgt"], as_dict=1)
		if territory_details:
			conditions += " and exists (select name from `tabTerritory` t \
				where t.lft >= %s and t.rgt <= %s and l.territory = t.name)"%(territory_details.lft,
				territory_details.rgt)
		
	if filters.get("customer_group"):
		customer_group_details = frappe.db.get_value("Customer Group",
			filters.get("customer_group"), ["lft", "rgt"], as_dict=1)
		if customer_group_details:
			conditions += " and exists (select name from `tabCustomer_group` t \
				where t.lft >= %s and t.rgt <= %s and l.customer_group = t.name)"%(customer_group_details.lft,
				customer_group_details.rgt)
	
	if filters.get('show_product'):
		data = frappe.db.sql("""
			select l.name, l.status, l.lead_name, l.territory, t.parent_territory, l.state, l.customer_group, 
			l.size_of_business, pl.product_looking_for_details as products_looking_for, l.cash_and_carry, l.reference_reviews_and_other_information, 
			l.payment_performance_or_relations, l.source, pd.previous_details_item as previously_worked_with, l.lead_owner, l.phone, l.mobile_no, l.fax
			from `tabLead` as l 
			JOIN `tabTerritory` as t ON (t.name = l.territory)
			LEFT JOIN `tabProduct Looking For Details` as pl ON (pl.parent = l.name)
			LEFT JOIN `tabPrevious Details Item` as pd ON (pd.parent = l.name)
			where l.docstatus = 0 {}
		""".format(conditions), as_dict= True)
	else:
		data = frappe.db.sql("""
			select l.name, l.status, l.lead_name, l.territory, t.parent_territory, l.state, l.customer_group, 
			l.size_of_business, l.cash_and_carry, l.reference_reviews_and_other_information, 
			l.payment_performance_or_relations, l.source, pd.previous_details_item as previously_worked_with, l.lead_owner, l.phone, l.mobile_no, l.fax
			from `tabLead` as l 
			JOIN `tabTerritory` as t ON (t.name = l.territory)
			LEFT JOIN `tabPrevious Details Item` as pd ON (pd.parent = l.name)
			where l.docstatus = 0 {}
		""".format(conditions), as_dict= True)

	return data