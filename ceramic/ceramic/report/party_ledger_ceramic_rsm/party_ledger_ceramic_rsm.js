// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Party Ledger Ceramic RSM"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'authority': 'Unauthorized'
					}
				}
			}
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -3),
			"reqd": 1,
			"width": "40px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "40px"
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type",
			"default": "Customer",
			get_query: () => {
				return {
					filters: {
						name : ['in', ['Customer', 'Supplier']]
					}
				}
			}
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": "80px"
		},
		{
			"fieldname":"primary_customer",
			"label": __("Primary Customer"),
			"fieldtype": "Data",
			"options": "Customer",
			"reqd": 1,
			"width": "80px",
			"ignore_user_permission":1,
			get_query: () => {
				return { query: "ceramic.controllers.queries.new_customer_query" }
			}
		},
		{
			"label": __("Print With Item"),
			"fieldname": "print_with_item",
			"fieldtype": "Check"
		},	
	]
}