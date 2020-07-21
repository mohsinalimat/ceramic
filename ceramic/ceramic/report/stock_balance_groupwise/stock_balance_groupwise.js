// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Stock Balance Groupwise"] = {
		"filters": [
			{
				"fieldname": "company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
		],
		"tree": true,
		"name_field": "item_group",
		"parent_field": "parent_item_group",
		"initial_depth": 1,
		"formatter": function(value, row, column, data, default_formatter) {
			if (column.fieldname=="item_group") {
				value = data.item_group || value;
	
				column.link_onclick =
					"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
				column.is_tree = true;
			}
	
			value = default_formatter(value, row, column, data);
	
			if (!data.parent_item_group) {
				value = $(`<span>${value}</span>`);
	
				var $value = $(value).css("font-weight", "bold");
				if (data.warn_if_negative && data[column.fieldname] < 0) {
					$value.addClass("text-danger");
				}
	
				value = $value.wrap("<p></p>").parent().html();
			}
	
			return value;
		},
	}
});
