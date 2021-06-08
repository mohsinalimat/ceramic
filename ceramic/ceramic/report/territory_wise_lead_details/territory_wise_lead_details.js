// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Territory wise Lead Details"] = {
	"filters": [
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory",
			"width": "80"
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": "80",
		},
		// {
		// 	"fieldname":"products_looking_for",
		// 	"label": __("Products Looking For"),
		// 	"fieldtype": "Link",
		// 	"options": "Product Looking For Details",
		// 	"width": "80",
		// },
		{
			"fieldname":"lead_owner",
			"label": __("Lead Owner"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('User', txt);
			},
			"width": "80"
		},
	]
};
