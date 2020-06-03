frappe.ui.form.on('Quotation', {

    validate: function (frm) {
        frm.trigger('filed_calulations')
    },
    filed_calulations: function (frm) {
        frm.doc.items.forEach(function (d) {
            frappe.db.get_value("Tile Size", d.tile_size, ['width', 'length'], function (r) {
                d.area_cover_per_box = r.length * r.width * d.tile_per_box / 92903
            })
        })
    }
});
frappe.ui.form.on('Quotation Item', {
    tile_size: function (frm, cdt, cdn) {
        frm.events.filed_calulations(frm)
    },
    tile_per_box: function (frm, cdt, cdn) {
        frm.events.filed_calulations(frm)
    },
});

cur_frm.fields_dict.items.grid.get_field("Tablefied_name").get_query = function (doc) {
	return {
		filters: {
			'is_group': 0,
		}
	}
};