// Copyright (c) 2016, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Order Picked Detailed"] = {
	"filters": [
		{
			"fieldname":"sales_order",
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
			"reqd": 1
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			get_query: function() {
				var item_group = frappe.query_report.get_filter_value('item_group')
				if (item_group){
					return {
						doctype: "Item",
						filters: {
							"item_group": item_group,
							"is_item_series": 0
						}
					}
				} else {
					return {
						doctype: "Item",
						filters: {
							"is_item_series": 0
						}
					}
				}
			}
		},
		// {
		// 	"fieldname":"pending_so",
		// 	"label": __("Pending Sales Orders"),
		// 	"fieldtype": "Check",
		// 	"default": 1,
		// },
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
	]
};
