// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Lot-Wise Balance"] = {
	"filters": [
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},
		// {
		// 	"fieldname": "item",
		// 	"label": __("Item"),
		// 	"fieldtype": "Link",
		// 	"options": "Item",
		// 	"width": "80"
		// },
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": "80",
			"default": frappe.defaults.get_user_default("Company"),
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
	]
}