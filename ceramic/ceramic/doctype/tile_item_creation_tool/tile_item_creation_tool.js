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
			'is_item_series': 1,
		}
	}
};

frappe.ui.form.on('Tile Item Creation Tool', {
	refresh: function(frm){
		if (frm.doc.__islocal){
			frappe.call({
				method: "ceramic.ceramic.doctype.tile_item_creation_tool.tile_item_creation_tool.get_tile_quality",
				callback: function(r){
					if (r.message) {
						frm.doc.tile_quality = [];

						$.each(r.message, function(index, value){
							var row = frm.add_child('tile_quality');

							frappe.model.set_value(row.doctype, row.name, 'tile_quality', value);
						});

						frm.refresh_field('tile_quality');
					}
				}
			});
		}

		if (!frm.doc.is_item_series) {
			
		}
	},
	before_save: function(frm){
		if (frm.doc.__islocal){
			frm.doc.item_name = frm.doc.item_design + '-' + frm.doc.tile_surface + '-' + frm.doc.tile_type + '-' + frm.doc.tile_size
		}
		if (frm.doc.is_item_series) {
			frm.doc.item_series = ''
		} else {
			if (!frm.doc.item_series) {
				msgprint("Please Select Item Series");
				validated = false;
			}
		}
	}
});