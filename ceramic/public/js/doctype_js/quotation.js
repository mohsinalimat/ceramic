frappe.ui.form.on('Quotation', {
	
	get_items: function(frm){[]
        frappe.call({
            method: "ceramic.ceramic.doc_events.quotation.get_items_from_item_group",
          
            callback: function (r) {
                let d;
                if (r.message) {
                    frm.doc.items = []
                    for (d of r.message) {
                        frappe.db.get_doc('Item Group', d.name).then(function (x) {
                            var row = frm.add_child("items");
                            frappe.model.set_value(row.doctype, row.name, 'item_group', x.name)
                            frappe.model.set_value(row.doctype, row.name, 'tile_size', x.tile_size)
                            frappe.model.set_value(row.doctype, row.name, 'tile_thickness', x.tile_thickness)
                            frappe.model.set_value(row.doctype, row.name, 'net_weight_per_box', x.net_weight_per_box)
                            frappe.model.set_value(row.doctype, row.name, 'tile_per_box', x.tile_per_box)
                            frappe.model.set_value(row.doctype, row.name, 'uom', x.uom)
                        });
                       
                    }
                    frm.refresh()
                }
            }
        });
	},
});