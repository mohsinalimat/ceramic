// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Warehouse Lot-wise Balance"] = {
	"filters": [
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		}
	]
};
