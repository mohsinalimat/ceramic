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
    },
    get_items: function (frm) {
        frappe.call({
            method: "ceramic.ceramic.doc_events.quotation.get_items_from_item_group",

            callback: function (r) {
                if (r.message) {
                    frm.doc.items = []
                        r.message.forEach(function (item) {
                            var row = frm.add_child("items");
                            frappe.model.set_value(row.doctype, row.name, 'item_group', item.name)
                            frappe.model.set_value(row.doctype, row.name, 'quotation_index', item.quotation_index)
                            frappe.model.set_value(row.doctype, row.name, 'tile_size', item.tile_size)
                            frappe.model.set_value(row.doctype, row.name, 'tile_thickness', item.tile_thickness)
                            frappe.model.set_value(row.doctype, row.name, 'net_weight_per_box', item.net_weight_per_box)
                            frappe.model.set_value(row.doctype, row.name, 'tile_per_box', item.tile_per_box)
                            frappe.model.set_value(row.doctype, row.name, 'uom', item.uom)
                    })
                    frm.refresh()
                }
            }
        });
    },
});
frappe.ui.form.on('Quotation Item', {
    tile_size: function (frm, cdt, cdn) {
        frm.events.filed_calulations(frm)
    },
    tile_per_box: function (frm, cdt, cdn) {
        frm.events.filed_calulations(frm)
    },
}); 