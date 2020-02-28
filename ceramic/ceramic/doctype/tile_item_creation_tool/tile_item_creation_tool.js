// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.item_defaults.grid.get_field("default_warehouse").get_query = function(doc,cdt,cdn) {
    let d = locals[cdt][cdn];

	return {
		filters: {
            "is_group": 0,
            "company":d.company,           
		}
	}
};

cur_frm.fields_dict.item_series.get_query = function(doc) {
	return {
		filters: {
			"item_name": ["LIKE", "%Premium%"],
			"authority": "Authorized",
		}
	}
};

frappe.ui.form.on('Tile Item Creation Tool', {
	// refresh: function(frm) {

	// }
	item_series: function (frm) {
		// frm.set_value("maintain_stock",0)
		if (frm.doc.item_series){
			frm.set_value("maintain_stock",1)
		}
		else{
			frm.set_value("maintain_stock",0)
		}
	}
});