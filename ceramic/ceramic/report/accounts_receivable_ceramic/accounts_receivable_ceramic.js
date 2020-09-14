// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Accounts Receivable Ceramic"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "MultiSelectList",
			"default": [frappe.defaults.get_user_default("Company")],
			"get_data": function (text) {
				return frappe.db.get_link_options('Company', text, {
					authority : 'Unauthorized'
				})
			},
			"change": function () {
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname":"ageing_based_on",
			"label": __("Ageing Based On"),
			"fieldtype": "Select",
			"options": 'Posting Date\nDue Date',
			"default": "Posting Date"
		},
		{
			"fieldname":"report_date",
			"label": __("As on Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"range1",
			"label": __("Ageing Range 1"),
			"fieldtype": "Int",
			"default": "30",
			"reqd": 1
		},
		{
			"fieldname":"range2",
			"label": __("Ageing Range 2"),
			"fieldtype": "Int",
			"default": "60",
			"reqd": 1
		},
		{
			"fieldname":"range3",
			"label": __("Ageing Range 3"),
			"fieldtype": "Int",
			"default": "90",
			"reqd": 1
		},
		{
			"fieldname":"range4",
			"label": __("Ageing Range 4"),
			"fieldtype": "Int",
			"default": "120",
			"reqd": 1
		},
		{
			"fieldname":"finance_book",
			"label": __("Finance Book"),
			"fieldtype": "Link",
			"options": "Finance Book"
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'company': company
					}
				}
			}
		},
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			// on_change: () => {
			// 	var customer = frappe.query_report.get_filter_value('customer');
			// 	if (customer) {
			// 		frappe.db.get_value('Customer', customer, ["tax_id", "customer_name", "payment_terms"], function(value) {
			// 			frappe.query_report.set_filter_value('tax_id', value["tax_id"]);
			// 			frappe.query_report.set_filter_value('customer_name', value["customer_name"]);
			// 		});

			// 	} else {
			// 		frappe.query_report.set_filter_value('tax_id', "");
			// 		frappe.query_report.set_filter_value('customer_name', "");
			// 	}
			// }
		},
		{
			"fieldname":"customer_group",
			"label": __("Customer Group"),
			"fieldtype": "Link",
			"options": "Customer Group"
		},
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory"
		},
		{
			"fieldname":"primary_customer",
			"label": __("Primary Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			get_query: () => {
				
				return {
					query: "ceramic.controllers.queries.new_customer_query",
				}
			}

		},
		{
			"fieldname":"sales_person",
			"label": __("Sales Head"),
			"fieldtype": "Link",
			"options": "Sales Person"
		},
		{
			"fieldname":"regional_sales_manager",
			"label": __("RSM"),
			"fieldtype": "Link",
			"options": "Sales Person"
		},
		{
			"fieldname":"based_on_payment_terms",
			"label": __("Based On Payment Terms"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"show_future_payments",
			"label": __("Show Future Payments"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"show_delivery_notes",
			"label": __("Show Delivery Notes"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"show_sales_person",
			"label": __("Show Sales Person"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"tax_id",
			"label": __("Tax Id"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"customer_name",
			"label": __("Customer Name"),
			"fieldtype": "Data",
			"hidden": 1
		},
		{
			"fieldname":"payment_terms",
			"label": __("Payment Tems"),
			"fieldtype": "Data",
			"hidden": 1
		},
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();

		}
		return value;
	},

	onload: function(report) {
		report.page.add_inner_button(__("Accounts Receivable Ceramic Summary"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Accounts Receivable Ceramic Summary', {company: filters.company});
		});
	}
}

erpnext.dimension_filters.forEach((dimension) => {
	frappe.query_reports["Accounts Receivable"].filters.splice(9, 0 ,{
		"fieldname": dimension["fieldname"],
		"label": __(dimension["label"]),
		"fieldtype": "Link",
		"options": dimension["document_type"]
	});
});
