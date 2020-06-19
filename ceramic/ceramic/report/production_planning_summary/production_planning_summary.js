// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Production Planning Summary"] = {
	"filters": [
		{
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname:"item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname:"item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
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
		{
			fieldname:"order_priority",
			label: __("Order Priority"),
			fieldtype: "Int",
		}
	]
};