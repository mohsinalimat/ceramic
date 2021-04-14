// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Customer Details"] = {
	"filters": [
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": "80",
		},
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory",
			"width": "80",
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": "80",
		},
		{
			"fieldname": 'show_detail',
			"label": __('Show Detail'),
			"fieldtype": 'Check'
		},
		{
			"fieldname": 'show_contact',
			"label": __('Show Contact'),
			"fieldtype": 'Check'
		},
	]
};
