// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Warehouse Lot-wise Balance"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
			"change": function (r) {
				frappe.query_report.set_filter_value('to_date', frappe.query_report.get_filter_value('from_date'));
			}
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
			"hidden": 1
		}
	]
};
