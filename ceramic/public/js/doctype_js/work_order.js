frappe.ui.form.on('Work Order', {
	setup: function(frm){
        frm.set_query("production_item", function() {
			return {
				filters: {
					"item_group": frm.doc.item_group
				}
			}
        });
        frm.set_query("finish_item", function () {
            return {
                filters: {
                    "item_group": frm.doc.item_group,
                    "item_series": frm.doc.production_item
                }
            }
        });
	},
	item_group: function(frm){
        frappe.db.get_value('BOM', {'item_group': frm.doc.item_group,'is_active':1,'is_default':1 },'name',function (r) {
            if (r.name) {
                frm.set_value('bom_no',r.name)
            }
        })
	},
});